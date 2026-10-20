"""Compare cached local speech models on the fixed AMI development excerpts."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.evaluate_research_audio import reference, clip
from scripts.improve_decision_discussions import sha256
from src.audio.asr import run_asr
from src.evaluation.metrics import calculate_wer
from src.utils.cache import atomic_json
from src.utils.config import PROJECT_ROOT, get
from src.utils.text import words

OUT = PROJECT_ROOT/'professor_guidelines/evaluation/asr_quality'
WORK = PROJECT_ROOT/'.runtime/asr-quality'


def pooled(rows, metric):
    errors = sum(sum(row[metric][key] for key in ['substitutions', 'deletions', 'insertions']) for row in rows)
    count = sum(row[metric]['reference_length'] for row in rows)
    return {'rate': errors/count, 'errors': errors, 'reference_length': count}


def main():
    OUT.mkdir(parents=True, exist_ok=True); WORK.mkdir(parents=True, exist_ok=True)
    meetings, models = ['ES2002a', 'ES2003a'], ['small', 'medium']
    atomic_json(OUT/'protocol.json', {'cohort': 'Two existing AMI development excerpts, Array1-01, seconds 60-180',
        'meetings': meetings, 'models': models, 'language': 'auto', 'device': 'cpu', 'compute_type': 'int8',
        'beam_size': get('asr.beam_size'), 'normalization': 'NFKC/casefold Unicode words; no reference hints; CER excludes spaces',
        'selection': 'Minimum pooled development WER; CER and per-meeting errors reported; fixed tie order',
        'script_sha256': sha256(Path(__file__)),
        'limits': ['Exploratory two-meeting development comparison; no fresh final test.',
                   'Overlapping reference words ordered by time; segmentation/reference effects remain.',
                   'Concurrent NLP training; elapsed times cannot establish relative inference speed.',
                   'English cohort; Indic model differences remain separately reported.']})
    diar = WORK/'unknown.json'; atomic_json(diar, {'segments': []})
    results = []
    for model in models:
        for meeting in meetings:
            output = OUT/f'{model}_{meeting}.json'
            truth, _ = reference(meeting)
            audio = clip(meeting)
            source_hash = sha256(audio)
            if output.exists():
                saved = json.loads(output.read_text())
                assert saved['audio_sha256'] == source_hash
                results.append(saved)
                continue
            started = time.perf_counter()
            transcript, _, _ = run_asr(audio, diar, model+'_'+meeting, WORK,
                options={'model_size': model, 'language': None})
            truth = ' '.join(words(truth))
            hypothesis = ' '.join(words(' '.join(s.text for s in transcript.segments)))
            row = {'model': model, 'meeting': meeting, 'audio_sha256': source_hash,
                'wer': calculate_wer(truth, hypothesis),
                'cer': calculate_wer(' '.join(truth.replace(' ', '')), ' '.join(hypothesis.replace(' ', ''))),
                'reference': truth, 'hypothesis': hypothesis, 'elapsed_seconds': time.perf_counter()-started,
                'detected_languages': transcript.detected_languages}
            atomic_json(output, row); results.append(row)
            print(model, meeting, 'WER', row['wer']['wer'], 'CER', row['cer']['wer'], flush=True)
    summary = [{'model': model, 'wer': pooled([r for r in results if r['model']==model], 'wer'),
                'cer': pooled([r for r in results if r['model']==model], 'cer')} for model in models]
    assert summary[0]['wer']['reference_length'] == summary[1]['wer']['reference_length']
    atomic_json(OUT/'summary.json', {'models': summary, 'selected_model': min(summary, key=lambda r:r['wer']['rate'])['model'],
        'status': 'Exploratory English development ASR comparison; recognition models not fine-tuned'})
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__': main()
