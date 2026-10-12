#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
exec .venv/bin/python -m pytest --rootdir="$PROJECT_DIR" -c config/pytest.ini tests "$@"
