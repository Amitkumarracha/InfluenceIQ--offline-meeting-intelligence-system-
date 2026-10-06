"""Speaker diarization using pyannote.audio."""

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from src.utils.config import get, load_env
from src.utils.logging import get_logger
from src.utils.paths import get_processed_audio_dir

logger = get_logger(__name__)


@dataclass
class DiarizationSegment:
    segment_id: int
    start: float
    end: float
    speaker: str


@dataclass
class DiarizationResult:
    meeting_id: str
    num_speakers: int
    speakers: list[str]
    segments: list[DiarizationSegment]


def _load_pipeline(hf_token: str):
    """Load pyannote diarization pipeline (model weights cached locally after first run)."""
    model_name: str = get("diarization.model", "pyannote/speaker-diarization-3.1")
    if os.environ.get("HF_HUB_OFFLINE", "1") == "1":
        from huggingface_hub import snapshot_download
        try:
            snapshot_download(model_name, local_files_only=True)
        except Exception as exc:
            raise RuntimeError("Local pyannote model missing. Provision it manually or use diarization off/ONNX.") from exc
    import torch
    from pyannote.audio import Pipeline
    logger.info("Loading diarization pipeline: %s", model_name)
    try:
        pipeline = Pipeline.from_pretrained(model_name, use_auth_token=hf_token)
    except TypeError:
        pipeline = Pipeline.from_pretrained(model_name, token=hf_token)

    if pipeline is None:
        raise RuntimeError("Diarization model unavailable. Run scripts/download_models.py --diarization first.")

    if get("diarization.device", "cpu") == "cuda" and torch.cuda.is_available():
        pipeline.to(torch.device("cuda"))
        logger.info("Diarization pipeline successfully moved to CUDA device")
    else:
        logger.info("CUDA not available; running diarization on CPU")

    return pipeline


def merge_adjacent_segments(
    segments: list[tuple[float, float, str]],
    max_gap: float = 0.5,
) -> list[tuple[float, float, str]]:
    """
    Merge consecutive segments belonging to the same speaker if the gap
    between them is less than or equal to max_gap seconds.

    Args:
        segments: List of (start, end, speaker) tuples.
        max_gap: Maximum allowable gap in seconds to merge same-speaker segments.

    Returns:
        Merged list of (start, end, speaker) tuples.
    """
    if not segments:
        return []

    sorted_segs = sorted(segments, key=lambda s: (s[0], s[1]))
    merged: list[tuple[float, float, str]] = []

    for start, end, speaker in sorted_segs:
        if not merged:
            merged.append((start, end, speaker))
            continue

        prev_start, prev_end, prev_speaker = merged[-1]
        if speaker == prev_speaker and start <= prev_end + max_gap:
            merged[-1] = (prev_start, max(prev_end, end), prev_speaker)
        else:
            merged.append((start, end, speaker))

    return merged


def normalize_speaker_labels(
    segments: list[tuple[float, float, str]],
) -> tuple[list[tuple[float, float, str]], list[str]]:
    """
    Map speaker cluster IDs to standard SPEAKER_00, SPEAKER_01, etc.,
    based on order of first appearance.

    Args:
        segments: List of (start, end, raw_speaker) tuples.

    Returns:
        Tuple of (normalized_segments, list of unique speaker IDs in order).
    """
    speaker_map: dict[str, str] = {}
    normalized: list[tuple[float, float, str]] = []

    for start, end, raw_speaker in segments:
        if raw_speaker not in speaker_map:
            idx = len(speaker_map)
            speaker_map[raw_speaker] = f"SPEAKER_{idx:02d}"
        normalized.append((start, end, speaker_map[raw_speaker]))

    speakers = list(speaker_map.values())
    return normalized, speakers


def run_diarization(
    audio_path: str | Path,
    meeting_id: str | None = None,
    output_dir: Path | None = None,
    num_speakers: int | None = None,
) -> tuple[DiarizationResult, Path]:
    """
    Run speaker diarization on a preprocessed 16 kHz mono WAV file.

    The default pyannote backend requires authorized cached weights and
    an HF_TOKEN with access to:
      https://huggingface.co/pyannote/speaker-diarization-3.1

    Args:
        audio_path: Path to the processed WAV file (16 kHz mono).
        meeting_id: Identifier used for the output JSON filename.
        output_dir: Optional custom output directory for the diarization JSON.

    Returns:
        Tuple of (DiarizationResult, path to saved JSON).
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if meeting_id is None:
        meeting_id = audio_path.stem.replace("_processed", "")

    out_dir = output_dir or get_processed_audio_dir()
    out_path = out_dir / f"{meeting_id}_diarization.json"

    from src.utils.cache import fingerprint, read_cache, atomic_json
    backend = get("diarization.backend", "pyannote")
    if backend not in {"pyannote", "sherpa-onnx"}:
        raise ValueError("diarization.backend must be pyannote or sherpa-onnx")
    if num_speakers is not None and not 1 <= num_speakers <= 50:
        raise ValueError("Speaker count must be between 1 and 50")
    models = []
    if backend == "sherpa-onnx":
        from src.audio.onnx_diarization import model_paths
        models = model_paths()
    key = fingerprint([audio_path, *models], {**get("diarization"), "num_speakers": num_speakers})
    cached = read_cache(out_path, key)
    if cached is not None:
        logger.info("Cached diarization found; loading from %s", out_path)
        cached_segments = [
            DiarizationSegment(
                segment_id=s["segment_id"],
                start=s["start"],
                end=s["end"],
                speaker=s["speaker"],
            )
            for s in cached.get("segments", [])
        ]
        cached_result = DiarizationResult(
            meeting_id=cached.get("meeting_id", meeting_id),
            num_speakers=cached.get("num_speakers", len(cached.get("speakers", []))),
            speakers=cached.get("speakers", []),
            segments=cached_segments,
        )
        return cached_result, out_path

    merge_gap_s = float(get("diarization.merge_gap_s", 0.5))
    t_start = time.time()
    if backend == "sherpa-onnx":
        from src.audio.onnx_diarization import diarize
        raw_segments = diarize(audio_path, num_speakers)
        elapsed = time.time() - t_start
    else:
        # Ensure .env is loaded
        load_env()
        hf_token = os.environ.get("HF_TOKEN", "").strip()
        if not hf_token:
            raise EnvironmentError(
                "HF_TOKEN environment variable is not set. "
                "Set it to your HuggingFace token to use pyannote.audio. "
                "See .env.example for details."
            )

        # Speaker-count constraints and merge tolerance from config
        min_speakers = get("diarization.min_speakers", None)
        max_speakers = get("diarization.max_speakers", None)

        logger.info("Starting diarization: meeting_id=%s, audio=%s", meeting_id, audio_path)
        t_start = time.time()

        pipeline = _load_pipeline(hf_token)

        # Build kwargs — only pass constraints when they are explicitly set
        pipeline_kwargs: dict = {}
        if num_speakers is not None:
            if not 1 <= num_speakers <= 50:
                raise ValueError("Speaker count must be between 1 and 50")
            pipeline_kwargs["num_speakers"] = num_speakers
        elif min_speakers is not None:
            pipeline_kwargs["min_speakers"] = int(min_speakers)
        if num_speakers is None and max_speakers is not None:
            pipeline_kwargs["max_speakers"] = int(max_speakers)

        # Run pipeline — pyannote handles long audio internally via sliding window
        diarization = pipeline(str(audio_path), **pipeline_kwargs)

        elapsed = time.time() - t_start
        logger.info("Diarization model finished in %.2fs", elapsed)

        # Extract pyannote Annotation object (handles DiarizeOutput in pyannote 3.3+)
        if isinstance(diarization, tuple):
            annotation = diarization[0]
        else:
            annotation = diarization
            speaker_diarization = getattr(diarization, "__dict__", {}).get("speaker_diarization")
            if speaker_diarization is not None:
                annotation = speaker_diarization
            elif hasattr(type(diarization), "speaker_diarization"):
                annotation = diarization.speaker_diarization

        if not hasattr(annotation, "itertracks"):
            raise TypeError(
                "Unsupported diarization output type: expected pyannote Annotation or diarize output."
            )

        # Convert pyannote Annotation tracks to raw tuples
        raw_segments: list[tuple[float, float, str]] = [
            (turn.start, turn.end, speaker)
            for turn, _, speaker in annotation.itertracks(yield_label=True)
        ]
        raw_segments.sort(key=lambda x: (x[0], x[1]))

    # Merge adjacent same-speaker segments within tolerance
    merged_segments = merge_adjacent_segments(raw_segments, max_gap=merge_gap_s)

    # Normalize speaker IDs to SPEAKER_00, SPEAKER_01, etc.
    norm_segments, speakers = normalize_speaker_labels(merged_segments)

    # Build typed DiarizationSegment list
    segments: list[DiarizationSegment] = [
        DiarizationSegment(
            segment_id=i + 1,
            start=round(start, 3),
            end=round(end, 3),
            speaker=speaker,
        )
        for i, (start, end, speaker) in enumerate(norm_segments)
    ]

    num_speakers = len(speakers)

    logger.info(
        "Diarization complete: %d speakers, %d segments, elapsed=%.2fs",
        num_speakers,
        len(segments),
        elapsed,
    )

    result = DiarizationResult(
        meeting_id=meeting_id,
        num_speakers=num_speakers,
        speakers=speakers,
        segments=segments,
    )

    # Save structured JSON
    out_dir = output_dir or get_processed_audio_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{meeting_id}_diarization.json"

    output = {
        "meeting_id": result.meeting_id,
        "backend": backend,
        "num_speakers": result.num_speakers,
        "speakers": result.speakers,
        "segments": [asdict(s) for s in result.segments],
    }

    output["cache_key"] = key
    atomic_json(out_path, output)

    logger.info("Diarization results saved: %s", out_path)
    return result, out_path
