"""Voice Activity Detection using Silero VAD."""

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from src.utils.config import get
from src.utils.logging import get_logger
from src.utils.paths import get_processed_audio_dir

logger = get_logger(__name__)


@dataclass
class SpeechSegment:
    segment_id: int
    start: float
    end: float


def _load_silero_vad():
    """Load Silero VAD model and utilities from torch.hub (cached locally)."""
    model, utils = torch.hub.load(
        repo_or_dir="snakers4/silero-vad",
        model="silero_vad",
        force_reload=False,
        trust_repo=True,
    )
    return model, utils


def run_vad(
    audio_path: str | Path,
    meeting_id: str | None = None,
) -> tuple[list[SpeechSegment], Path]:
    """
    Run Silero VAD on a preprocessed 16 kHz mono audio file.

    Args:
        audio_path: Path to the processed WAV file (16 kHz mono).
        meeting_id: Identifier used for the output JSON filename.

    Returns:
        Tuple of (list of SpeechSegment, path to saved JSON).
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Processed audio not found: {audio_path}")

    if meeting_id is None:
        meeting_id = audio_path.stem.replace("_processed", "")

    threshold: float = get("vad.threshold", 0.5)
    min_speech_ms: int = get("vad.min_speech_duration_ms", 250)
    min_silence_ms: int = get("vad.min_silence_duration_ms", 100)

    logger.info("Running VAD on: %s", audio_path)
    logger.info(
        "VAD params — threshold=%.2f, min_speech_ms=%d, min_silence_ms=%d",
        threshold, min_speech_ms, min_silence_ms,
    )
    t_start = time.time()

    # Load with soundfile — shape [T, C]
    waveform_np, sr = sf.read(str(audio_path), dtype="float32", always_2d=True)
    if sr != 16000:
        raise ValueError(f"Expected 16000 Hz audio, got {sr} Hz. Run preprocess first.")

    # Average to mono if needed, then convert to 1-D torch tensor
    if waveform_np.shape[1] > 1:
        waveform_np = waveform_np.mean(axis=1)
    else:
        waveform_np = waveform_np[:, 0]

    wav_1d = torch.from_numpy(waveform_np)
    duration = len(waveform_np) / sr

    logger.info("Audio duration: %.2fs", duration)

    model, utils = _load_silero_vad()
    get_speech_timestamps = utils[0]

    raw_segments = get_speech_timestamps(
        wav_1d,
        model,
        threshold=threshold,
        min_speech_duration_ms=min_speech_ms,
        min_silence_duration_ms=min_silence_ms,
        return_seconds=True,
    )

    segments: list[SpeechSegment] = [
        SpeechSegment(
            segment_id=i + 1,
            start=round(float(seg["start"]), 3),
            end=round(float(seg["end"]), 3),
        )
        for i, seg in enumerate(raw_segments)
    ]

    total_speech = sum(s.end - s.start for s in segments)
    elapsed = time.time() - t_start

    logger.info(
        "VAD complete: %d segments, total_speech=%.2fs, elapsed=%.2fs",
        len(segments), total_speech, elapsed,
    )

    out_dir = get_processed_audio_dir()
    out_path = out_dir / f"{meeting_id}_vad.json"

    output = {
        "meeting_id": meeting_id,
        "audio_file": str(audio_path),
        "duration": round(duration, 3),
        "num_segments": len(segments),
        "total_speech_duration": round(total_speech, 3),
        "segments": [asdict(s) for s in segments],
    }

    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    logger.info("VAD results saved: %s", out_path)
    return segments, out_path
