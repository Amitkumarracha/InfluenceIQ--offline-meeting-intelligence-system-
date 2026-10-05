"""Inspect local readiness without downloading models or exposing credentials."""
import importlib.metadata
import json
import os
import shutil
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.utils.config import PROJECT_ROOT, get


def main():
    packages = {}
    for name in ['torch', 'torchaudio', 'faster-whisper', 'pyannote.audio', 'silero-vad',
                 'sentence-transformers', 'fastapi', 'uvicorn', 'SQLAlchemy', 'python-multipart']:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    ready = {}
    try:
        from huggingface_hub import snapshot_download
        from faster_whisper.utils import _MODELS
        models = {'asr': _MODELS.get(get('asr.model_size'), get('asr.model_size')),
                  'slides': 'sentence-transformers/' + get('ppt.embeddings.model'),
                  'diarization': get('diarization.model')}
        for purpose, model in models.items():
            try:
                path = Path(snapshot_download(model, local_files_only=True))
                required = 'model.bin' if purpose == 'asr' else 'config.yaml' if purpose == 'diarization' else 'modules.json'
                ready[purpose] = (path / required).is_file()
            except Exception:
                ready[purpose] = False
    except ImportError:
        ready['asr'] = False
    result = {'python': sys.version.split()[0], 'environment': sys.prefix,
              'cpu_threads_available': os.cpu_count(),
              'free_disk_gb': round(shutil.disk_usage(PROJECT_ROOT).free / 1024**3, 1),
              'ffmpeg': bool(shutil.which('ffmpeg')), 'ffprobe': bool(shutil.which('ffprobe')),
              'packages': packages, 'local_models': ready, 'asr_model': get('asr.model_size'),
              'allowed_languages': get('asr.allowed_languages'),
              'frontend_built': (PROJECT_ROOT / 'frontend/dist/index.html').exists(),
              'android_apk_built': (PROJECT_ROOT / 'android/build/meet-iq-debug.apk').exists(),
              'notes': ['Diarization readiness also requires its nested segmentation/embedding weights.',
                        'Missing diarization does not prevent UNKNOWN-speaker transcription.',
                        'Model presence is not an accuracy measurement.']}
    print(json.dumps(result, indent=2))
    return 0 if all(packages.values()) and ready.get('asr') and result['ffmpeg'] and result['ffprobe'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
