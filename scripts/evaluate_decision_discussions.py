"""Non-generative decision-discussion experiment with independently annotated AMI spans.

Research-only: oracle transcript/act boundaries, group-separated local split.
No application model or weights are changed by this experiment.
"""
import csv
import hashlib
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import joblib
import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, confusion_matrix, precision_recall_fscore_support

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.meeting.events import KeywordEventExtractor
from src.utils.cache import atomic_json

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'AMI_dataset/annotations/ami_public_manual_1.6.2'
OUT = ROOT / 'professor_guidelines/evaluation/decision_discussion'
WORK = ROOT / '.runtime/research-decision-model'
NITE_ID = '{http://nite.sourceforge.net/}id'
TEST_GROUPS = {'ES2016', 'IS1006', 'TS3005'}
DEV_GROUPS = {'IS1008', 'TS3004'}
VARIANTS = {'word': ('word',), 'char': ('char',), 'word_char': ('word', 'char'),
            'word_char_context': ('word', 'char', 'context')}


def referenced_ids(href, file_ids):
    ids = re.findall(r'id\(([^)]+)\)', href)
    if not 1 <= len(ids) <= 2:
        raise ValueError('Unrecognised NITE range: ' + href)
    lookup = {value: i for i, value in enumerate(file_ids)}
    if any(value not in lookup for value in ids):
        raise ValueError('NITE reference endpoint is absent')
    first, last = lookup[ids[0]], lookup[ids[-1]]
    if first > last:
        raise ValueError('Reversed NITE range')
    return set(file_ids[first:last + 1])


def load_meeting(meeting):
    files, orders = {}, {}
    for path in sorted((BASE / 'words').glob(meeting + '.*.words.xml')):
        nodes = list(ET.parse(path).getroot())
        files[path.name] = {node.get(NITE_ID): node for node in nodes}
        orders[path.name] = list(files[path.name])
    selected = set()
    for decision in ET.parse(BASE / 'decision/manual' / (meeting + '.decision.xml')).getroot():
        for child in decision:
            href = child.get('href')
            if href:
                filename = href.split('#')[0]
                selected.update(referenced_ids(href, orders[filename]))
    rows = []
    for path in sorted((BASE / 'dialogueActs').glob(meeting + '.*.dialog-act.xml')):
        for act in ET.parse(path).getroot():
            nodes = []
            for child in act:
                href = child.get('href', '')
                if child.tag.rsplit('}', 1)[-1] == 'child' and href:
                    filename = href.split('#')[0]
                    chosen = referenced_ids(href, orders[filename])
                    nodes.extend(node for key, node in files[filename].items() if key in chosen)
            tokens = [node for node in nodes if node.tag == 'w' and node.get('punc') != 'true' and node.text]
            if not tokens:
                continue
            text = ' '.join(node.text for node in tokens)
            ratio = sum(node.get(NITE_ID) in selected for node in tokens) / len(tokens)
            rows.append({'meeting': meeting, 'group': meeting[:-1], 'act_id': act.get(NITE_ID),
                'start': min(float(node.get('starttime', 0)) for node in tokens),
                'end': max(float(node.get('endtime', 0)) for node in tokens), 'text': text,
                'label': int(ratio >= .5), 'positive_word_fraction': ratio})
    rows.sort(key=lambda row: (row['start'], row['act_id']))
    for i, row in enumerate(rows):
        row['context'] = ' '.join(rows[j]['text'] for j in range(max(0, i-1), min(len(rows), i+2)))
    return rows


def metrics(truth, predicted, scores=None):
    p, r, f, support = precision_recall_fscore_support(truth, predicted, labels=[1], average=None, zero_division=0)
    return {'precision': float(p[0]), 'recall': float(r[0]), 'f1': float(f[0]), 'positive_support': int(support[0]),
        'average_precision': float(average_precision_score(truth, scores)) if scores is not None and sum(truth) else None,
        'confusion_matrix_tn_fp_fn_tp': confusion_matrix(truth, predicted, labels=[0, 1]).ravel().tolist()}


def main():
    OUT.mkdir(parents=True, exist_ok=True); WORK.mkdir(parents=True, exist_ok=True)
    meetings = sorted(path.name.split('.')[0] for path in (BASE / 'decision/manual').glob('*.xml'))
    split_meetings = {key: [] for key in ['train', 'dev', 'test']}
    for meeting in meetings:
        split = 'test' if meeting[:-1] in TEST_GROUPS else 'dev' if meeting[:-1] in DEV_GROUPS else 'train'
        split_meetings[split].append(meeting)
    protocol = {'task': 'Binary dialogue-act membership in manually annotated decision-discussion spans',
        'positive_rule': 'At least 50% of act lexical word IDs belong to manual decision spans',
        'splits': split_meetings, 'group_separation': 'Meeting series/project; no dialogue-act random split',
        'official_test_status': 'No selected manual decision files intersect official BUT test; this is a custom group-separated experiment',
        'oracle_inputs': 'Reference words, dialogue-act boundaries; no DA type labels or decision labels enter features',
        'variants': VARIANTS, 'C_grid': [.3, 1, 3], 'threshold_grid': [.2, .35, .5, .65, .8],
        'selection': 'F1 on dev only; fixed tie order; all prespecified variants reported on test',
        'seed': 42, 'installed_in_application': False,
        'limits': ['English AMI scenario discussions; not Hindi/Hinglish validation.',
                   'Decision-discussion membership is not final decision extraction or influence accuracy.',
                   'Manual boundary input removes ASR and segmentation errors; full pipeline requires a separate study.',
                   'Outside-span acts are treated as negatives, assuming manual decision annotations are exhaustive.',
                   'Neighbour context includes next act: offline classification, not causal streaming.']}
    atomic_json(OUT / 'protocol.json', protocol)
    all_rows = {split: [row for meeting in names for row in load_meeting(meeting)] for split, names in split_meetings.items()}
    assert not any(set(m[:-1] for m in split_meetings[a]) & set(m[:-1] for m in split_meetings[b]) for a, b in [('train','dev'), ('train','test'), ('dev','test')])
    labels = {split: np.array([r['label'] for r in rows]) for split, rows in all_rows.items()}
    for split, rows in all_rows.items():
        with (WORK / (split + '.jsonl')).open('w') as stream:
            stream.write('\n'.join(json.dumps(row, ensure_ascii=False) for row in rows))
    atomic_json(OUT / 'dataset_counts.json', {split: {'meetings': len(split_meetings[split]), 'acts': len(rows),
        'positive_acts': int(labels[split].sum()), 'partial_overlap_acts': sum(0 < r['positive_word_fraction'] < 1 for r in rows)} for split, rows in all_rows.items()})
    print('Dataset loaded', {k: (len(v), int(labels[k].sum())) for k, v in all_rows.items()}, flush=True)
    matrices, vectorizers = {}, {}
    for feature in ['word', 'char', 'context']:
        vectorizer = TfidfVectorizer(analyzer='char_wb' if feature == 'char' else 'word',
            ngram_range=(3, 5) if feature == 'char' else (1, 2), min_df=2,
            max_features=20000 if feature == 'char' else 12000, sublinear_tf=True)
        field = 'context' if feature == 'context' else 'text'
        train = vectorizer.fit_transform([r[field] for r in all_rows['train']]); vectorizers[feature] = vectorizer
        matrices[feature] = {'train': train, **{split: vectorizer.transform([r[field] for r in all_rows[split]]) for split in ['dev','test']}}
    trained = []
    # Test labels are used only after every variant's model and threshold have been selected.
    for name, features in VARIANTS.items():
        matrix = {split: hstack([matrices[f][split] for f in features], format='csr') for split in ['train','dev','test']}
        best = None
        started = time.perf_counter()
        for c in protocol['C_grid']:
            model = LogisticRegression(C=c, class_weight='balanced', max_iter=500, solver='liblinear', random_state=42)
            model.fit(matrix['train'], labels['train'])
            probabilities = model.predict_proba(matrix['dev'])[:,1]
            for threshold in protocol['threshold_grid']:
                value = metrics(labels['dev'], probabilities >= threshold, probabilities)
                if best is None or value['f1'] > best['dev']['f1']:
                    best = dict(model=model, dev=value, C=c, threshold=threshold)
        trained.append(dict(name=name, features=features, matrix=matrix, elapsed=time.perf_counter()-started, **best))
        print('Selected on dev', name, best['dev'], flush=True)
    outputs = []
    for row in trained:
        started = time.perf_counter(); scores = row['model'].predict_proba(row['matrix']['test'])[:,1]; elapsed = time.perf_counter()-started
        predictions = scores >= row['threshold']
        per_meeting = []
        for meeting in split_meetings['test']:
            mask = np.array([r['meeting'] == meeting for r in all_rows['test']])
            per_meeting.append({'meeting': meeting, **metrics(labels['test'][mask], predictions[mask], scores[mask])})
        outputs.append({'method': row['name'], 'features': row['features'], 'C': row['C'], 'threshold': row['threshold'],
            'dev': row['dev'], 'test': metrics(labels['test'], predictions, scores), 'per_meeting': per_meeting,
            'fit_selection_seconds': row['elapsed'], 'test_classification_seconds': elapsed,
            'timing_scope': 'Classifier only; excludes vectorizer fitting/transforms and file I/O'})
        joblib.dump({'classifier': row['model'], 'threshold': row['threshold'],
            'vectorizers': {k: vectorizers[k] for k in row['features']}, 'protocol': protocol}, WORK / (row['name'] + '.joblib'))
    extractor = KeywordEventExtractor()
    keyword_predictions = np.array([any(e.event_type == 'decision' for e in extractor.extract(
        [{'text': r['text'], 'start': r['start'], 'end': r['end'], 'speaker': 'UNKNOWN', 'segment_id': 1}], 'benchmark').events) for r in all_rows['test']])
    baselines = [{'method': 'always_positive', 'test': metrics(labels['test'], np.ones(len(labels['test']), dtype=int))},
                 {'method': 'always_negative', 'test': metrics(labels['test'], np.zeros(len(labels['test']), dtype=int))},
                 {'method': 'current_explicit_decision_rule', 'test': metrics(labels['test'], keyword_predictions),
                  'scope': 'Explicit decision cue used for broader discussion-membership task; lexical models are stronger same-task baselines'}]
    source_files = [BASE/'decision/manual'/(m+'.decision.xml') for m in meetings]
    source_files += [p for m in meetings for directory, pattern in [('words', m+'.*.words.xml'), ('dialogueActs', m+'.*.dialog-act.xml')] for p in sorted((BASE/directory).glob(pattern))]
    atomic_json(OUT / 'summary.json', {'protocol': protocol, 'models': outputs, 'baselines': baselines,
        'dev_selected_variant': max(outputs, key=lambda r: r['dev']['f1'])['method'],
        'test_prevalence': float(labels['test'].mean()), 'source_sha256': {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files},
        'research_status': 'Exploratory supervised English decision-discussion classification; no influence or full-pipeline claim'})
    print(json.dumps({'models': [{'method': r['method'], 'dev': r['dev'], 'test': r['test']} for r in outputs], 'baselines': baselines}, indent=2), flush=True)


if __name__ == '__main__':
    main()
