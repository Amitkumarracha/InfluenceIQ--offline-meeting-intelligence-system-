"""Evaluate manually transcribed phone excerpts, grouped as Hindi/English/Hinglish.

JSONL rows: {"id":"room1", "audio":"room1.wav", "reference":"human transcript",
             "group":"hinglish", "language":"auto"}
Use short consented excerpts from held-out meetings/speakers. No downloads/training.
"""
import argparse
import json
import hashlib
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.evaluation.metrics import calculate_wer
from src.pipeline.orchestrator import run_meeting
from src.utils.cache import atomic_json
from src.utils.text import words
from src.utils.config import get


def normalized(text):
    # Preserve Hindi spelling/marks and English/Hinglish as spoken. No translation.
    return ' '.join(words(text))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model', default=get('asr.model_size'))
    args = parser.parse_args()
    entries = [json.loads(line) for line in args.manifest.read_text(encoding='utf-8').splitlines() if line.strip()]
    if not entries:
        parser.error('Manifest has no recordings')
    dataset_key = hashlib.sha256(args.manifest.read_bytes()).hexdigest()[:10]
    model_key = hashlib.sha256(args.model.encode()).hexdigest()[:8]
    ids = set()
    for row in entries:
        if not isinstance(row, dict):
            parser.error('Each manifest row must be a JSON object')
        identifier = row.get('id', '')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,60}', identifier) or identifier in ids:
            parser.error('Each recording needs a unique id of letters, digits, underscore or hyphen')
        ids.add(identifier)
        if row.get('group') not in {'hindi', 'english', 'hinglish'} or row.get('language', 'auto') not in {'auto', 'hi', 'en'}:
            parser.error('Invalid group/language')
        if not isinstance(row.get('reference'), str) or not normalized(row['reference']):
            parser.error('Supply a nonempty human transcript for every recording')
        path = Path(row['audio'])
        row['path'] = path if path.is_absolute() else args.manifest.parent / path
        if not row['path'].is_file():
            parser.error('Recording missing: ' + str(row['path']))
    recordings, groups = [], {}
    for row in entries:
        language = row.get('language', 'auto')
        path = run_meeting(row['path'], f'eval_{dataset_key}_{model_key}_' + row['id'], diarization='off',
            options={'model_size': args.model, 'language': None if language == 'auto' else language})
        report = json.loads(path.read_text())
        hypothesis = ' '.join(s['text'] for s in report['transcript_segments'])
        metrics = calculate_wer(normalized(row['reference']), normalized(hypothesis))
        recordings.append({'id': row['id'], 'group': row['group'], 'wer': metrics,
                           'report': str(path), 'duration_s': report['meeting_overview']['duration_s']})
        totals = groups.setdefault(row['group'], {'errors': 0, 'reference_words': 0, 'recordings': 0})
        totals['errors'] += sum(metrics[key] for key in ('substitutions', 'deletions', 'insertions'))
        totals['reference_words'] += metrics['reference_length']
        totals['recordings'] += 1
        totals['wer'] = round(totals['errors'] / totals['reference_words'], 6)
        atomic_json(args.output, {'model': args.model, 'normalization': 'NFKC/casefold/Unicode words, no transliteration',
            'recordings': recordings, 'groups': groups, 'complete': len(recordings) == len(entries),
            'limitations': ['WER does not evaluate speakers, summaries or decisions.',
                            'Timing/cache reuse is not a speed benchmark.']})
    print(json.dumps(groups, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
