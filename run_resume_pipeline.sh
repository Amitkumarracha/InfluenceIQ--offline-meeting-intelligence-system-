#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Load project venv and environment variables
if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

# Create standard project folders for model checkpoints and outputs
mkdir -p \
  models/audio/asr \
  models/audio/diarization \
  models/audio/vad \
  models/checkpoints/training \
  models/checkpoints/inference \
  models/checkpoints/per_meeting \
  data/checkpoints/per_meeting \
  data/checkpoints/stage_logs \
  logs/pipeline_runs \
  outputs/reports \
  outputs/evaluation \
  outputs/exports \
  outputs/visualizations

# Allow user to override meeting id at runtime
MEETING_ID="${1:-TS3012d}"
AUDIO_PATH="data/raw/audio/${MEETING_ID}.wav"

if [ ! -f "$AUDIO_PATH" ]; then
  echo "Audio file not found: $AUDIO_PATH"
  echo "Available audio files:"
  ls -1 data/raw/audio | head
  exit 1
fi

# Set ASR config automatically to CPU if CUDA is unavailable.
python - <<'PY'
from pathlib import Path
import importlib.util

cfg_path = Path('config.yaml')
text = cfg_path.read_text(encoding='utf-8')

# Check if torch is installed and CUDA is available.
torch_spec = importlib.util.find_spec('torch')
if torch_spec is not None:
    import torch
    has_cuda = torch.cuda.is_available()
else:
    has_cuda = False

if not has_cuda:
    text = text.replace('device: cuda', 'device: cpu')
    text = text.replace('compute_type: float16', 'compute_type: int8')
    cfg_path.write_text(text, encoding='utf-8')
    print('CUDA not available; switched ASR config to CPU fallback.')
else:
    print('CUDA available; leaving config as-is.')
PY

echo "=================================================="
echo "Running pipeline for meeting: $MEETING_ID"
echo "=================================================="

python scripts/run_pipeline.py --audio "$AUDIO_PATH" --meeting-id "$MEETING_ID"

echo "=================================================="
echo "Pipeline run completed for $MEETING_ID"
echo "Checkpoint state is under: data/checkpoints/per_meeting/$MEETING_ID"
echo "Model artifacts are under: models/"
echo "=================================================="
