#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
if [ ! -x .venv/bin/python ]; then echo 'Run bash scripts/setup.sh first.'; exit 1; fi
if .venv/bin/python - <<'PYBUILD'
from pathlib import Path
entry = Path('frontend/dist/index.html')
inputs = [Path('frontend/package.json'), Path('frontend/package-lock.json'), Path('frontend/index.html')]
inputs += list(Path('frontend/src').rglob('*')) + list(Path('frontend/public').rglob('*'))
inputs += list(Path('frontend').glob('vite.config.*'))
raise SystemExit(0 if not entry.exists() or any(p.is_file() and p.stat().st_mtime > entry.stat().st_mtime for p in inputs) else 1)
PYBUILD
then
    npm --prefix frontend run build
fi
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=4
printf '%s\n' 'Meet IQ: http://127.0.0.1:8000 — local models, no internet needed.'
exec .venv/bin/python -m backend.api
