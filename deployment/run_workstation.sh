#!/usr/bin/env bash
# Serve the built website and serialized local pipeline on a workstation.
# Inference remains offline on the server; clients need connectivity to it.
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
if [[ "${1:-}" == "--help" ]]; then
  echo 'Build frontend/dist and provision models first. Set MAI_ASR_DEVICE=cpu|cuda and MAI_ASR_COMPUTE_TYPE=int8|float16. Serves 127.0.0.1:8000; use a VPN/SSH tunnel or configured TLS reverse proxy for remote access.'
  exit 0
fi
[ -f frontend/dist/index.html ] || { echo 'Run npm --prefix frontend run build first.' >&2; exit 1; }
export MAI_ASR_DEVICE="${MAI_ASR_DEVICE:-cpu}"
export MAI_ASR_COMPUTE_TYPE="${MAI_ASR_COMPUTE_TYPE:-int8}"
export MAI_HOST="${MAI_HOST:-127.0.0.1}"
export MAI_ALLOW_REGISTRATION="${MAI_ALLOW_REGISTRATION:-0}"
if [ "$MAI_ASR_DEVICE" = cuda ]; then
  .venv/bin/python - <<'PY'
import ctranslate2, os
if ctranslate2.get_cuda_device_count() < 1:
    raise SystemExit('No compatible CUDA GPU detected. Use CPU mode or install the documented CUDA runtime first.')
requested = os.environ['MAI_ASR_COMPUTE_TYPE']
if requested not in ctranslate2.get_supported_compute_types('cuda'):
    raise SystemExit('Unsupported GPU compute type: ' + requested)
PY
fi
exec .venv/bin/python -m backend.api
