#!/usr/bin/env bash
# One-time native build provisioning. The installed app does not use the network.
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
mkdir -p android/vendor .runtime models
if [ ! -d android/vendor/whisper.cpp ]; then
  git clone --depth 1 --branch v1.7.6 https://github.com/ggml-org/whisper.cpp.git android/vendor/whisper.cpp
fi
EXPECTED=a8d002cfd879315632a579e73f0148d06959de36
[ "$(git -C android/vendor/whisper.cpp rev-parse HEAD)" = "$EXPECTED" ] || { echo 'Unexpected whisper.cpp revision'; exit 1; }
.bootstrap/bin/uv pip install --python .venv/bin/python cmake==4.4.4 ninja==1.13.2
if [ ! -d .runtime/android-ndk-r26d ]; then
  curl -fL --retry 2 -o .runtime/android-ndk-r26d-linux.zip https://dl.google.com/android/repository/android-ndk-r26d-linux.zip
  python3 - <<'PY'
import os, stat, zipfile
from pathlib import Path
root = Path('.runtime').resolve()
with zipfile.ZipFile(root / 'android-ndk-r26d-linux.zip') as archive:
    for item in archive.infolist():
        target = root / item.filename
        if not target.resolve().is_relative_to(root):
            raise ValueError('Unsafe archive entry')
        mode = item.external_attr >> 16
        if stat.S_ISLNK(mode):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(archive.read(item).decode())
        else:
            archive.extract(item, root)
            if mode: target.chmod(mode & 0o777)
PY
fi
if [ ! -f models/ggml-base.bin ]; then
  curl -fL --retry 2 -o models/ggml-base.bin.partial https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin
  mv models/ggml-base.bin.partial models/ggml-base.bin
fi
echo 'Install an Android SDK platform/build-tools and a JDK, then run bash android/build.sh.'
