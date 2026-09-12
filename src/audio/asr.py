"""Automatic Speech Recognition (ASR) and speaker-attributed transcript generation.

Uses faster-whisper for offline transcription and matches each ASR segment
against diarization segments via temporal overlap to assign speaker IDs.

Phase 5 of the Multimodal Meeting Intelligence Pipeline.
"""

import json
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.utils.config import get
from src.utils.logging import get_logger
from src.utils.paths import get_processed_audio_dir

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class TranscriptSegment:
    """One ASR segment attributed to a single speaker."""

    segment_id: int
    start: float
    end: float
    speaker: str
    text: str
    confidence: float | None = None


@dataclass
class TranscriptResult:
    """Complete speaker-attributed transcript for a meeting."""

    meeting_id: str
    language: str | None
    duration: float
    num_speakers: int
    speakers: list[str]
    segments: list[TranscriptSegment] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------


def _load_whisper_model():
    """Load the faster-whisper WhisperModel per config.yaml settings."""
    from faster_whisper import WhisperModel  # type: ignore[import-untyped]

    model_size: str = get("asr.model_size", "base")
    device: str = get("asr.device", "cpu")
    compute_type: str = get("asr.compute_type", "int8")

    logger.info(
        "Loading faster-whisper model: size=%s device=%s compute_type=%s",
        model_size, device, compute_type,
    )
    return WhisperModel(model_size, device=device, compute_type=compute_type)


# ---------------------------------------------------------------------------
# Overlap-based attribution helpers
# ---------------------------------------------------------------------------


def compute_overlap(
    asr_start: float,
    asr_end: float,
    diar_start: float,
    diar_end: float,
) -> float:
    """Return the overlap duration (seconds) between two intervals."""
    return max(0.0, min(asr_end, diar_end) - max(asr_start, diar_start))


def attribute_speaker(
    asr_start: float,
    asr_end: float,
    diar_segments: list[dict[str, Any]],
    min_overlap_ratio: float = 0.3,
) -> str:
    """Assign the speaker whose diarization segment has the greatest overlap.

    Returns "UNKNOWN" when no segment covers at least *min_overlap_ratio*
    of the ASR segment duration.
    """
    asr_duration = max(asr_end - asr_start, 1e-6)
    best_overlap = 0.0
    best_speaker = "UNKNOWN"

    for seg in diar_segments:
        overlap = compute_overlap(asr_start, asr_end, seg["start"], seg["end"])
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = seg["speaker"]

    if best_overlap / asr_duration < min_overlap_ratio:
        return "UNKNOWN"

    return best_speaker


# ---------------------------------------------------------------------------
# Core ASR + attribution
# ---------------------------------------------------------------------------


def _load_diarization_json(path: Path) -> list[dict[str, Any]]:
    """Load diarization segments from a Phase 4 JSON file."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("segments", [])


def run_asr(
    audio_path: str | Path,
    diarization_path: str | Path | None = None,
    meeting_id: str | None = None,
    output_dir: Path | None = None,
) -> tuple["TranscriptResult", Path, Path]:
    """Transcribe meeting audio and attribute segments to speakers.

    Args:
        audio_path: Path to the 16 kHz mono WAV file.
        diarization_path: Path to the Phase 4 diarization JSON.  When None,
            looks for <audio_dir>/<meeting_id>_diarization.json.
        meeting_id: Identifier used for output filenames.
        output_dir: Output directory; defaults to the configured
            processed-audio directory.

    Returns:
        Tuple of (TranscriptResult, path-to-JSON, path-to-TXT).

    Raises:
        FileNotFoundError: If audio or diarization file is missing.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if meeting_id is None:
        meeting_id = audio_path.stem.replace("_processed", "")

    if diarization_path is None:
        diarization_path = audio_path.parent / f"{meeting_id}_diarization.json"
    diarization_path = Path(diarization_path)
    if not diarization_path.exists():
        raise FileNotFoundError(
            f"Diarization JSON not found: {diarization_path}\n"
            "Run Phase 4 (diarization) first, or pass diarization_path explicitly."
        )

    language: str | None = get("asr.language", None)
    beam_size: int = int(get("asr.beam_size", 5))
    min_overlap_ratio: float = float(get("asr.min_overlap_ratio", 0.3))

    diar_segments = _load_diarization_json(diarization_path)
    diar_speakers = sorted({seg["speaker"] for seg in diar_segments if seg.get("speaker")})
    logger.info(
        "Loaded %d diarization segments (%d speakers)",
        len(diar_segments), len(diar_speakers),
    )

    out_dir = output_dir or get_processed_audio_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{meeting_id}_transcript.json"
    txt_path = out_dir / f"{meeting_id}_transcript.txt"

    # Return cached result if available
    if json_path.exists():
        logger.info("Cached ASR result found; loading from %s", json_path)
        with open(json_path, encoding="utf-8") as f:
            cached = json.load(f)
        return _deserialise_result(cached), json_path, txt_path

    model = _load_whisper_model()
    logger.info("Transcribing: %s", audio_path)
    t_start = time.time()

    transcribe_kwargs: dict[str, Any] = {
        "beam_size": beam_size,
        "word_timestamps": False,
    }
    if language:
        transcribe_kwargs["language"] = language

    segments_iter, info = model.transcribe(str(audio_path), **transcribe_kwargs)
    detected_language: str | None = getattr(info, "language", None)
    duration: float = getattr(info, "duration", 0.0)
    logger.info("Language: %s  Duration: %.2fs", detected_language, duration)

    raw_segments = list(segments_iter)
    elapsed = time.time() - t_start
    logger.info("Transcription done in %.2fs — %d raw segments", elapsed, len(raw_segments))

    transcript_segments: list[TranscriptSegment] = []
    for idx, seg in enumerate(raw_segments):
        seg_start = round(float(seg.start), 3)
        seg_end = round(float(seg.end), 3)
        text = (seg.text or "").strip()

        speaker = attribute_speaker(
            seg_start, seg_end, diar_segments, min_overlap_ratio=min_overlap_ratio
        )

        confidence: float | None = None
        if hasattr(seg, "avg_logprob") and seg.avg_logprob is not None:
            confidence = round(min(1.0, max(0.0, math.exp(float(seg.avg_logprob)))), 4)

        transcript_segments.append(TranscriptSegment(
            segment_id=idx + 1,
            start=seg_start,
            end=seg_end,
            speaker=speaker,
            text=text,
            confidence=confidence,
        ))

    transcript_speakers = sorted(
        {s.speaker for s in transcript_segments if s.speaker != "UNKNOWN"}
    )

    result = TranscriptResult(
        meeting_id=meeting_id,
        language=detected_language,
        duration=round(duration, 3),
        num_speakers=len(transcript_speakers),
        speakers=transcript_speakers,
        segments=transcript_segments,
    )

    _save_json(result, json_path)
    _save_txt(result, txt_path)
    logger.info(
        "Transcript saved: %d segments, %d speakers — %s",
        len(transcript_segments), len(transcript_speakers), json_path,
    )
    return result, json_path, txt_path


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _save_json(result: TranscriptResult, path: Path) -> None:
    """Serialise TranscriptResult to a JSON file."""
    payload = {
        "meeting_id": result.meeting_id,
        "language": result.language,
        "duration": result.duration,
        "num_speakers": result.num_speakers,
        "speakers": result.speakers,
        "segments": [asdict(s) for s in result.segments],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def _save_txt(result: TranscriptResult, path: Path) -> None:
    """Write a human-readable transcript to plain text."""
    speakers_str = ", ".join(result.speakers) if result.speakers else "none"
    lines = [
        f"Meeting ID  : {result.meeting_id}",
        f"Language    : {result.language or 'unknown'}",
        f"Duration    : {result.duration:.2f}s",
        f"Speakers    : {speakers_str}",
        "",
        "-" * 72,
        "",
    ]
    for seg in result.segments:
        ts = f"[{_fmt_ts(seg.start)} -> {_fmt_ts(seg.end)}]"
        conf = f" (conf={seg.confidence:.2f})" if seg.confidence is not None else ""
        lines.append(f"{ts}  {seg.speaker}{conf}")
        lines.append(f"  {seg.text}")
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _fmt_ts(seconds: float) -> str:
    """Format seconds as MM:SS.mmm."""
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m:02d}:{s:06.3f}"


def _deserialise_result(data: dict[str, Any]) -> TranscriptResult:
    """Reconstruct a TranscriptResult from a saved JSON dict."""
    segments = [
        TranscriptSegment(
            segment_id=s["segment_id"],
            start=s["start"],
            end=s["end"],
            speaker=s["speaker"],
            text=s["text"],
            confidence=s.get("confidence"),
        )
        for s in data.get("segments", [])
    ]
    return TranscriptResult(
        meeting_id=data["meeting_id"],
        language=data.get("language"),
        duration=data.get("duration", 0.0),
        num_speakers=data.get("num_speakers", 0),
        speakers=data.get("speakers", []),
        segments=segments,
    )
