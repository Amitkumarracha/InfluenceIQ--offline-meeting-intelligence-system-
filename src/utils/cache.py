"""Content-addressed caches and atomic JSON writes for resumable local jobs."""
import hashlib
import json
import os
import tempfile
from pathlib import Path


def fingerprint(paths, settings=None):
    digest = hashlib.sha256(json.dumps(settings, sort_keys=True).encode())
    for path in paths:
        with Path(path).open('rb') as stream:
            while block := stream.read(1024 * 1024):
                digest.update(block)
    return digest.hexdigest()


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def read_cache(path, key):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        return data if data.get('cache_key') == key else None
    except (OSError, ValueError):
        return None
