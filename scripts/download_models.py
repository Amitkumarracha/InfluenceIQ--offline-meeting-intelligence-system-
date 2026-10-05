"""One-time online provisioning. Meeting inference never downloads models."""
import argparse
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['HF_HUB_OFFLINE'] = '0'
os.environ['TRANSFORMERS_OFFLINE'] = '0'
os.environ['HF_HUB_DISABLE_XET'] = '1'
from src.utils.config import get


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asr-model', choices=['tiny', 'base', 'small', 'medium', 'large-v3', 'large-v3-turbo'])
    parser.add_argument('--diarization', action='store_true')
    parser.add_argument('--slides', action='store_true')
    args = parser.parse_args()
    if args.asr_model:
        os.environ["MAI_ASR_MODEL"] = args.asr_model
    from faster_whisper import WhisperModel
    print('Provisioning multilingual ASR:', get('asr.model_size'), flush=True)
    WhisperModel(get('asr.model_size'), device='cpu', compute_type='int8')
    if args.slides:
        from sentence_transformers import SentenceTransformer
        SentenceTransformer(get('ppt.embeddings.model'))
    if args.diarization:
        from src.audio.diarization import _load_pipeline
        if not os.environ.get('HF_TOKEN'):
            raise SystemExit('Set HF_TOKEN in .env and accept the pyannote model terms first.')
        _load_pipeline(os.environ['HF_TOKEN'])
    print('Selected models are ready for offline use.')


if __name__ == '__main__':
    main()
