#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
if [ ! -x .venv/bin/python ]; then echo 'Run bash scripts/setup.sh first.'; exit 1; fi
if [ ! -f frontend/dist/index.html ]; then (cd frontend && npm run build); fi
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=4
printf '%s\n' 'Meet IQ: http://127.0.0.1:8000 — local models, no internet needed.'
exec .venv/bin/python api.py
