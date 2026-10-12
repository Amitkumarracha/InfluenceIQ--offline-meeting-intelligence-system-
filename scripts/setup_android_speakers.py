#!/usr/bin/env python3
"""Explicit one-time provisioning for Android; inference never downloads."""
import hashlib
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.runtime' / 'sherpa-android'
VENDOR = ROOT / 'android/vendor/sherpa-onnx'
ASSETS = ROOT / 'android/app/src/main/assets/speaker-models'
BASE = 'https://github.com/k2-fsa/sherpa-onnx/releases/download/v1.13.8/'
FILES = {
    'release.tar.bz2': (BASE + 'sherpa-onnx-v1.13.8-android.tar.bz2', '2ff63469a71cb6009aa2e3ed5f4a670f8abdcbe4bb9ffd23776afc792a6b4f44'),
    'c-api.h': ('https://raw.githubusercontent.com/k2-fsa/sherpa-onnx/v1.13.8/sherpa-onnx/c-api/c-api.h', '2a1b95084be8fd1deb3228fcad2fd3f7f0258b64582f7402281ec174c7b7f4ce'),
}

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    for name, (url, expected) in FILES.items():
        target = CACHE / name
        if not target.is_file() or digest(target) != expected:
            temporary = target.with_suffix('.partial')
            try:
                with urllib.request.urlopen(url, timeout=60) as source, temporary.open('wb') as out:
                    total = 0
                    while block := source.read(65536):
                        total += len(block)
                        if total > 60 * 1024**2:
                            raise ValueError('Dependency exceeds supported size')
                        out.write(block)
                if digest(temporary) != expected:
                    raise ValueError('Android speaker dependency failed SHA-256 verification')
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
    (VENDOR / 'include').mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CACHE / 'c-api.h', VENDOR / 'include/c-api.h')
    # Only the two linked libraries are needed. Reject unrelated archive paths.
    with tarfile.open(CACHE / 'release.tar.bz2') as archive:
        for abi in ('arm64-v8a', 'x86_64'):
            destination = VENDOR / 'jniLibs' / abi
            destination.mkdir(parents=True, exist_ok=True)
            for name in ('libsherpa-onnx-c-api.so', 'libonnxruntime.so'):
                member = archive.getmember(f'./jniLibs/{abi}/{name}')
                if not member.isfile() or member.size > 40 * 1024**2:
                    raise ValueError('Invalid native library archive member')
                with archive.extractfile(member) as source, (destination / name).open('wb') as out:
                    shutil.copyfileobj(source, out)
    models = ROOT / 'models/diarization'
    expected_models = {
        'segmentation.onnx': '220ad67ca923bef2fa91f2390c786097bf305bceb5e261d4af67b38e938e1079',
        'embedding.onnx': '1a331345f04805badbb495c775a6ddffcdd1a732567d5ec8b3d5749e3c7a5e4b',
    }
    if not all((models / name).is_file() for name in expected_models):
        subprocess.run([sys.executable, str(ROOT / 'scripts/download_speaker_models.py')], check=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    for name, expected in expected_models.items():
        if digest(models / name) != expected:
            raise ValueError(f'Invalid speaker model: {name}')
        shutil.copyfile(models / name, ASSETS / name)
    print('Android speaker runtime 1.13.8 and verified model assets prepared.')

if __name__ == '__main__':
    main()
