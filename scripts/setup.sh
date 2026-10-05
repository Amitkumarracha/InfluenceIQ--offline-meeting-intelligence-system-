#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
for TOOL in python3 ffmpeg ffprobe node npm; do
    command -v "$TOOL" >/dev/null || { echo "Install $TOOL first."; exit 1; }
done
if [ ! -x .bootstrap/bin/uv ]; then
    python3 -m venv .bootstrap
    .bootstrap/bin/pip install uv
fi
.bootstrap/bin/uv python install 3.11
if [ ! -x .venv/bin/python ]; then .bootstrap/bin/uv venv --python 3.11 .venv; fi
.bootstrap/bin/uv pip install --python .venv/bin/python torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu
.bootstrap/bin/uv pip install --python .venv/bin/python -r requirements-lock.txt
(cd frontend && npm ci --no-audit --no-fund && npm run build)
echo 'Environment ready. Provision models with .venv/bin/python scripts/download_models.py --slides --diarization'
