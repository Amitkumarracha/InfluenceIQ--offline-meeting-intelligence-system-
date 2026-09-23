#!/usr/bin/env python3
"""Run a small chunk of meetings with checkpointing and ETA reporting."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parent


def ensure_env():
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))

    # Ensure CUDA 12 libraries are discoverable by faster-whisper
    cuda12_path = "/usr/local/lib/ollama/cuda_v12"
    if Path(cuda12_path).exists():
        current_ld = os.environ.get("LD_LIBRARY_PATH", "")
        if cuda12_path not in current_ld:
            os.environ["LD_LIBRARY_PATH"] = f"{cuda12_path}:{current_ld}".rstrip(":")


def list_meeting_ids(chunks: list[str]) -> list[str]:
    if not chunks:
        return []
    ids: list[str] = []
    for item in chunks:
        if item.endswith(".wav"):
            ids.append(Path(item).stem)
        else:
            ids.append(item)
    return ids


def run_meeting(meeting_id: str) -> None:
    audio_path = PROJECT_ROOT / "data" / "raw" / "audio" / f"{meeting_id}.wav"
    if not audio_path.exists():
        raise FileNotFoundError(f"Missing audio file: {audio_path}")

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "run_pipeline.py"),
        "--audio",
        str(audio_path),
        "--meeting-id",
        meeting_id,
    ]
    subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=True)


def main() -> None:
    ensure_env()

    if len(sys.argv) < 2:
        print("Usage: python run_small_chunk.py <meeting_id_1> <meeting_id_2> ...")
        print("Example: python run_small_chunk.py TS3012d TS3012c EN2001a")
        sys.exit(1)

    meeting_ids = list_meeting_ids(sys.argv[1:])
    if not meeting_ids:
        print("No meeting IDs provided.")
        sys.exit(1)

    print(f"Starting small chunk run for {len(meeting_ids)} meetings")
    start_time = time.time()

    for idx, mid in enumerate(tqdm(meeting_ids, desc="Meetings", unit="meeting"), start=1):
        loop_start = time.time()
        run_meeting(mid)
        elapsed = time.time() - loop_start
        remaining = (len(meeting_ids) - idx) * elapsed
        print(f"[{idx}/{len(meeting_ids)}] {mid} finished in {elapsed:.1f}s; ETA remaining: {remaining:.1f}s")

    total_elapsed = time.time() - start_time
    print(f"Small chunk complete in {total_elapsed:.1f}s")


if __name__ == "__main__":
    main()
