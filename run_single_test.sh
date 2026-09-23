#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

MEETING_ID="${1:-TS3012d}"
AUDIO_PATH="data/raw/audio/${MEETING_ID}.wav"

if [ ! -f "$AUDIO_PATH" ]; then
  echo "Missing audio: $AUDIO_PATH"
  exit 1
fi

echo "=== Testing single meeting: $MEETING_ID ==="
python scripts/run_pipeline.py --audio "$AUDIO_PATH" --meeting-id "$MEETING_ID"
