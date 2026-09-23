"""Resolve project paths from config."""

from pathlib import Path

from src.utils.config import get

# Project root is three levels up from this file (src/utils/paths.py)
PROJECT_ROOT = Path(__file__).parent.parent.parent


def get_processed_audio_dir() -> Path:
    rel = get("paths.audio.processed", "data/processed/audio")
    path = PROJECT_ROOT / rel
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_raw_audio_dir() -> Path:
    rel = get("paths.audio.raw", "data/raw/audio")
    path = PROJECT_ROOT / rel
    path.mkdir(parents=True, exist_ok=True)
    return path
