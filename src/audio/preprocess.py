"""Audio preprocessing: load, mono conversion, resampling to 16 kHz."""

import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from math import gcd

from src.utils.config import get
from src.utils.logging import get_logger
from src.utils.paths import get_processed_audio_dir

logger = get_logger(__name__)


@dataclass
class AudioMetadata:
    file_name: str
    original_duration: float
    processed_duration: float
    original_sample_rate: int
    processed_sample_rate: int
    original_channels: int


def preprocess_audio(input_path: str | Path) -> tuple[Path, AudioMetadata]:
    """
    Load an audio file, convert to mono, resample to 16 kHz, and save.

    Args:
        input_path: Path to the source audio file.

    Returns:
        Tuple of (processed_audio_path, AudioMetadata).
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Audio file not found: {input_path}")

    target_sr: int = get("audio.sample_rate", 16000)
    force_mono: bool = get("audio.mono", True)

    logger.info("Preprocessing audio: %s", input_path)
    t_start = time.time()

    # Load audio — soundfile returns (samples [T, C] or [T], samplerate)
    waveform, orig_sr = sf.read(str(input_path), dtype="float32", always_2d=True)
    # waveform shape: [T, C]
    orig_channels = waveform.shape[1]
    orig_duration = waveform.shape[0] / orig_sr

    logger.info(
        "Loaded: duration=%.2fs, sample_rate=%d, channels=%d",
        orig_duration,
        orig_sr,
        orig_channels,
    )

    # Convert to mono by averaging channels
    if force_mono and orig_channels > 1:
        waveform = waveform.mean(axis=1, keepdims=True)
        logger.info("Converted to mono.")

    # Resample if needed using polyphase filter (high quality, memory-efficient)
    if orig_sr != target_sr:
        divisor = gcd(target_sr, orig_sr)
        up = target_sr // divisor
        down = orig_sr // divisor
        waveform = resample_poly(waveform, up, down, axis=0).astype(np.float32)
        logger.info("Resampled %d Hz -> %d Hz.", orig_sr, target_sr)

    processed_duration = waveform.shape[0] / target_sr

    # Save as 16-bit PCM WAV
    out_dir = get_processed_audio_dir()
    out_path = out_dir / (input_path.stem + "_processed.wav")
    sf.write(str(out_path), waveform, target_sr, subtype="PCM_16")

    elapsed = time.time() - t_start
    logger.info(
        "Preprocessing complete: output=%s, duration=%.2fs, elapsed=%.2fs",
        out_path,
        processed_duration,
        elapsed,
    )

    metadata = AudioMetadata(
        file_name=input_path.name,
        original_duration=orig_duration,
        processed_duration=processed_duration,
        original_sample_rate=orig_sr,
        processed_sample_rate=target_sr,
        original_channels=orig_channels,
    )
    return out_path, metadata
