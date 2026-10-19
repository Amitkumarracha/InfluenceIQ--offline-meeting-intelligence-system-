"""Evaluate the frozen public Hindi/Hinglish pilot manifests, entirely local inference."""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.audio.asr import run_asr
from src.audio.live import decode_preview, transcribe_preview
from src.evaluation.metrics import calculate_wer
from src.utils.cache import atomic_json
from src.utils.config import PROJECT_ROOT
from src.utils.text import words


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-size", choices=["small", "medium"], default="small")
    model_size = parser.parse_args().model_size
    root = PROJECT_ROOT
    out = root / 'professor_guidelines/evaluation'
    manifests = out
    if model_size != 'small':
        out = out / model_size
        out.mkdir(exist_ok=True)
    work = root / '.runtime/research-evaluation' / ('indic' if model_size == 'small' else 'indic_' + model_size)
    work.mkdir(parents=True, exist_ok=True)
    empty = work / 'unknown.json'; atomic_json(empty, {'segments': []})
    rows = []
    for language in ('hindi', 'hinglish'):
        manifest = json.loads((manifests / (language + '_manifest.json')).read_text())
        for index, sample in enumerate(manifest['samples']):
            source = root / sample['path']
            assert hashlib.sha256(source.read_bytes()).hexdigest() == sample['sha256']
            audio = work / f'{language}_{index}.wav'
            subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-y', '-i', str(source), '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', str(audio)], check=True)
            started = time.perf_counter()
            result, _, _ = run_asr(audio, empty, audio.stem, work, options={'model_size': model_size, 'language': None})
            elapsed = time.perf_counter() - started
            reference = ' '.join(words(sample['reference']))
            hypothesis = ' '.join(words(' '.join(s.text for s in result.segments)))
            row = {'language': language, 'sample': index, 'id': sample['id'], 'reference': reference,
                   'hypothesis': hypothesis, 'wer': calculate_wer(reference, hypothesis),
                   'cer': calculate_wer(' '.join(reference.replace(' ', '')), ' '.join(hypothesis.replace(' ', ''))),
                   'detected_languages': result.detected_languages, 'duration_seconds': result.duration,
                   'elapsed_seconds': elapsed, 'rtf': elapsed / result.duration}
            rows.append(row); atomic_json(out / f'{language}_{index}_result.json', row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    summary = {}
    for language in ('hindi', 'hinglish'):
        chosen = [r for r in rows if r['language'] == language]
        summary[language] = {'n': len(chosen), 'seconds': sum(r['duration_seconds'] for r in chosen)}
        for metric in ('wer', 'cer'):
            errors = sum(sum(r[metric][k] for k in ('substitutions', 'deletions', 'insertions')) for r in chosen)
            count = sum(r[metric]['reference_length'] for r in chosen)
            summary[language][metric] = errors / count
            summary[language][metric + '_errors'] = errors
            summary[language][metric + '_reference_length'] = count
    # Real model smoke check for the new preview path, distinct from mocked browser tests.
    payload = (work / 'hinglish_0.wav').read_bytes()
    started = time.perf_counter(); preview = transcribe_preview(decode_preview(payload), model_size, 'auto', '')
    preview['elapsed_seconds'] = time.perf_counter() - started
    atomic_json(out / 'live_preview_real_model.json', preview)
    atomic_json(out / 'indic_summary.json', {'summary': summary, 'rows': rows, 'model': model_size,
        'device': 'cpu', 'compute_type': 'int8', 'language_setting': 'auto',
        'normalization': 'NFKC, casefold, Unicode letter/number/mark words; no transliteration or number expansion. CER excludes spaces.',
        'limits': ['Eight samples per corpus, selected before inference; exploratory pilot, not a full test-set benchmark.',
                   'Hinglish consecutive technical lecture segments are correlated; not multi-speaker meetings.',
                   'Script and spelling variation count as errors; no manual reference corrections.',
                   'Timing may include concurrent long-recording diarization; not an isolated speed benchmark.',
                   'No model training or fine-tuning performed; pretraining overlap is unknown.']})


if __name__ == '__main__':
    main()
