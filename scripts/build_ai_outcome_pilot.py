"""Materialize explicitly AI-annotated, citation-grounded research pairs; no human-label claims."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.train_contextual_model import RELATIONS

NITE = '{http://nite.sourceforge.net/}id'
REFERENCE = ROOT/'AMI_dataset/annotations/ami_public_manual_1.6.2'


def passage(meeting, span, sources):
    path = REFERENCE/'words'/f"{meeting}.{span['speaker']}.words.xml"
    sources.add(path)
    words = []
    for word in ET.parse(path).getroot():
        if word.tag.rsplit('}', 1)[-1] != 'w' or not word.text or word.get('punc') == 'true':
            continue
        start, end = float(word.get('starttime', 'nan')), float(word.get('endtime', 'nan'))
        if all(map(math.isfinite, [start, end])) and span['start'] <= start < span['end']:
            words.append({'id': word.get(NITE), 'start': start, 'end': end, 'text': word.text})
    if not words or any(not word['id'] for word in words):
        raise ValueError(f'No traceable words for {meeting}: {span}')
    return {'text': ' '.join(word['text'] for word in words), 'start': words[0]['start'],
            'end': words[-1]['end'], 'word_ids': [word['id'] for word in words],
            'path': str(path.relative_to(ROOT)), 'speaker': span['speaker']}


def build(directory):
    directory = directory.resolve()
    target = directory/'ai_labels.jsonl'
    if target.exists():
        raise ValueError('Preserve frozen AI annotations; use a new directory')
    protocol_path, specs_path = directory/'annotation_protocol.json', directory/'curation_specs.json'
    protocol = json.loads(protocol_path.read_text())
    splits = {group: split for split, groups in protocol['splits'].items() for group in groups}
    sources, rows = {protocol_path, specs_path}, []
    for number, spec in enumerate(json.loads(specs_path.read_text()), 1):
        meeting = spec['meeting_id']
        if spec['relationship'] not in RELATIONS or meeting[:-1] not in splits:
            raise ValueError('A declared relationship and frozen project split are required')
        source = passage(meeting, spec, sources)
        if 'outcome_span' in spec:
            outcome = passage(meeting, spec['outcome_span'], sources)
            if outcome['start'] < source['start']:
                raise ValueError('Outcome precedes contribution')
            outcome_type = 'manual_transcript_passage'
        else:
            path = REFERENCE/'abstractive'/f'{meeting}.abssumm.xml'
            sources.add(path)
            index = {item.get(NITE): item for item in ET.parse(path).getroot().iter() if item.get(NITE)}
            outcome = {'text': ' '.join(' '.join(' '.join(index[key].itertext()).split()) for key in spec['summary_ids']),
                       'summary_ids': spec['summary_ids'], 'path': str(path.relative_to(ROOT)),
                       'start': None, 'end': None}
            outcome_type = 'human_written_meeting_summary'
        rows.append({'pair_id': f'ai_pair_{number:03d}', 'meeting_id': meeting,
            'group': meeting[:-1], 'split': splits[meeting[:-1]], 'source_text': source['text'],
            'outcome_text': outcome['text'], 'source_speaker': source['speaker'],
            'source_type': spec['source_type'], 'source_start': source['start'], 'source_end': source['end'],
            'outcome_start': outcome['start'], 'relationship': spec['relationship'],
            'label_source': 'ai_generated', 'annotator': 'Codex assistant in this conversation',
            'independent_human_review': False, 'include': spec.get('include', True),
            'uncertainty_note': spec.get('uncertainty_note', ''), 'review_rationale': spec['reason'],
            'outcome_input_type': outcome_type, 'source_reference': source, 'outcome_reference': outcome})
    with target.open('x', encoding='utf-8') as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+'\n')
    fields = ['pair_id', 'meeting_id', 'group', 'split', 'include', 'relationship', 'label_source',
              'source_speaker', 'source_start', 'source_text', 'outcome_text', 'outcome_input_type',
              'review_rationale', 'uncertainty_note']
    with (directory/'AI_reviewed_pairs.csv').open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader(); writer.writerows(rows)
    counts = {split: {label: sum(r['include'] and r['split'] == split and r['relationship'] == label for r in rows)
                      for label in RELATIONS} for split in ['train', 'dev', 'test']}
    provenance = {'status': 'AI-generated weak labels, not independent human reference labels',
        'pairs': len(rows), 'included': sum(row['include'] for row in rows), 'class_counts': counts,
        'limits': ['Single AI annotator; no inter-annotator agreement was measured.',
                  'Human written outcome summaries are privileged inputs for some pairs.',
                  'Judgments describe contribution/outcome alignment, not causal presenter influence.',
                  'Historical AMI groups; small purposive sample; selection and annotation biases remain.'],
        'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(sources)},
        'builder_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'labels_sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
    (directory/'annotation_provenance.json').write_text(json.dumps(provenance, indent=2))
    return provenance


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.directory), indent=2))
