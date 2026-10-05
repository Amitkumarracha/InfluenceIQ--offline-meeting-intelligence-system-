#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
if [ "$#" -lt 2 ]; then
  echo 'Usage: scripts/process_new_meeting.sh MEETING_ID AUDIO [PPTX]'
  exit 2
fi
exec "$PROJECT_DIR/.venv/bin/python" scripts/process_meeting.py --meeting-id "$1" --audio "$2" ${3:+--ppt "$3"}
