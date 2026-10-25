"""Prepare independent review sheets, then validate adjudicated outcome labels."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.train_contextual_model import load_data, RELATIONS


def reference_context(meeting):
    files = sorted((ROOT/'AMI_dataset/annotations/ami_public_manual_1.6.2/words').glob(f'{meeting}.*.words.xml'))
    if not files:
        raise ValueError(f'AMI manual reference missing: {meeting}')
    passages, untimed = [], []
    for path in files:
        speaker, batch = path.name.split('.')[1], []
        def flush():
            if batch:
                passages.append((batch[0][0], f"[{batch[0][0]:.2f}–{batch[-1][1]:.2f}] {speaker}: "+' '.join(item[2] for item in batch)))
                batch.clear()
        for word in ET.parse(path).getroot():
            if word.tag.rsplit('}', 1)[-1] != 'w' or not word.text or word.get('punc') == 'true':
                continue
            start, end = float(word.get('starttime', 'nan')), float(word.get('endtime', 'nan'))
            if not all(map(math.isfinite, [start, end])) or start < 0 or end < start:
                untimed.append(f'[untimed] {speaker}: {word.text}')
                continue
            if batch and (start-batch[-1][1] > 2 or start-batch[0][0] > 15):
                flush()
            batch.append((start, end, word.text))
        flush()
    return '\n'.join(['AMI manual reference; times in seconds. Overlapping speakers are possible.',
        'A–D reference speakers require checking against predicted SPEAKER_* identities.',
        *[text for _, text in sorted(passages)], *untimed]), files


def prepare(source, output):
    inputs = sorted(source.glob('*.jsonl'))
    rows = [json.loads(line) for path in inputs for line in path.read_text().splitlines() if line.strip()]
    if not rows:
        raise ValueError('No candidate JSONL rows found')
    if output.exists():
        raise ValueError('Use a new review directory to preserve existing labels')
    contexts, references = {}, []
    for meeting in sorted({row['meeting_id'] for row in rows}):
        if not re.fullmatch(r'(ES|IS|TS)\d{4}[a-d]', meeting):
            raise ValueError('Verify project grouping explicitly for non-AMI candidates')
        contexts[meeting], paths = reference_context(meeting)
        references.extend(paths)
    output.mkdir(parents=True)
    (output/'context').mkdir()
    for meeting, text in contexts.items():
        (output/'context'/f'{meeting}.txt').write_text(text, encoding='utf-8')
    columns = list(dict.fromkeys([key for row in rows for key in row]+[
        'relationship', 'label_source', 'group', 'split', 'include', 'review_note', 'reference_context']))
    for name in ['reviewer_A.csv', 'reviewer_B.csv', 'adjudicated.csv']:
        with (output/name).open('x', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            for row in rows:
                writer.writerow({**row, 'relationship': '', 'label_source': '',
                    'group': row['meeting_id'][:-1], 'split': '', 'include': '', 'review_note': '',
                    'reference_context': f"context/{row['meeting_id']}.txt"})
    (output/'provenance.json').write_text(json.dumps({'status': 'Blank pilot worksheets; human checking required',
        'rows': len(rows), 'sources': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs+references}}, indent=2))
    return {'rows': len(rows), 'directory': str(output), 'status': 'Ready for independent human review'}


def convert(source, output):
    if output.exists():
        raise ValueError('Use a new output file; existing training labels are preserved')
    with source.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    selected, groups, seen = [], {}, set()
    counts = {split: {label: 0 for label in RELATIONS} for split in ['train', 'dev', 'test']}
    for number, row in enumerate(rows, 2):
        included = row.get('include', '').strip().lower()
        if included not in {'yes', 'no'}:
            raise ValueError(f'CSV row {number}: set include to yes or no')
        if included == 'no':
            continue
        if row.get('label_source', '').strip() != 'human' or row.get('relationship') not in RELATIONS:
            raise ValueError(f'CSV row {number}: independently checked human relationship required')
        group, split = row.get('group', '').strip(), row.get('split', '').strip()
        if not group or split not in counts:
            raise ValueError(f'CSV row {number}: group and train/dev/test split required')
        if re.fullmatch(r'(ES|IS|TS)\d{4}[a-d]', row.get('meeting_id', '')) and group != row['meeting_id'][:-1]:
            raise ValueError(f'CSV row {number}: retain the AMI project-series group')
        if groups.setdefault(group, split) != split:
            raise ValueError(f'Project {group} crosses splits')
        if not all(row.get(key, '').strip() for key in ['source_text', 'outcome_text']):
            raise ValueError(f'CSV row {number}: verify source and outcome text; exclude invalid pairs')
        pair = tuple(row.get(key, '') for key in ['meeting_id', 'source_event_id', 'outcome_event_id'])
        if not all(pair) or pair in seen:
            raise ValueError(f'CSV row {number}: unique, traceable source/outcome IDs required')
        seen.add(pair)
        counts[split][row['relationship']] += 1
        row.update(group=group, split=split)
        for key in ['source_start', 'outcome_start']:
            row[key] = float(row[key]) if row.get(key) else None
            if row[key] is not None and (not math.isfinite(row[key]) or row[key] < 0):
                raise ValueError(f'CSV row {number}: invalid {key}')
        if row['source_start'] is not None and row['outcome_start'] is not None and row['source_start'] > row['outcome_start']:
            raise ValueError(f'CSV row {number}: source occurs after outcome')
        selected.append(row)
    missing = [(split, label) for split, labels in counts.items() for label, count in labels.items() if not count]
    if missing:
        raise ValueError(f'Expand the reviewed dataset before four-class training. Missing split/class coverage: {missing}. Counts: {counts}')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        for row in selected:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+'\n')
    for split in counts:
        load_data('links', split, output)
    return {'rows': len(selected), 'groups': len(groups), 'class_counts': counts, 'output': str(output)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare_parser = commands.add_parser('prepare')
    prepare_parser.add_argument('--source', type=Path, default=ROOT/'outputs/training/outcome_annotations_20261024')
    prepare_parser.add_argument('--output', type=Path, required=True)
    convert_parser = commands.add_parser('convert')
    convert_parser.add_argument('--csv', type=Path, required=True)
    convert_parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.source, args.output) if args.command == 'prepare' else convert(args.csv, args.output)
    except ValueError as exc:
        parser.exit(2, str(exc)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
