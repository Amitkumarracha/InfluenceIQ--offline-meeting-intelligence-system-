"""Separate weak-supervision pilot: scores are agreement with AI labels, never human accuracy."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import joblib
import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.pipeline import FeatureUnion, Pipeline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.train_contextual_model import RELATIONS


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False))


def load_rows(path):
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    groups, ids = {}, set()
    for row in rows:
        if row.get('label_source') != 'ai_generated' or row.get('independent_human_review') is not False:
            raise ValueError('This pilot requires explicitly AI-generated labels, not claimed human references')
        if not isinstance(row.get('include'), bool) or row.get('relationship') not in RELATIONS:
            raise ValueError('Each AI judgment needs an explicit inclusion flag and valid relationship')
        if not row.get('pair_id') or row['pair_id'] in ids:
            raise ValueError('Unique pair IDs are required')
        ids.add(row['pair_id'])
        if not row.get('group') or row.get('split') not in {'train', 'dev', 'test'}:
            raise ValueError('Frozen project groups and splits are required')
        if groups.setdefault(row['group'], row['split']) != row['split']:
            raise ValueError('Project groups cross splits')
        if not all(isinstance(row.get(key), str) and row[key].strip() for key in ['source_text', 'outcome_text']):
            raise ValueError('Verbatim source and outcome text are required')
        if not row.get('source_reference') or not row.get('outcome_reference'):
            raise ValueError('Reference citations are required')
    selected = [row for row in rows if row['include']]
    if any(not any(row['split'] == split for row in selected) for split in ['train', 'dev', 'test']):
        raise ValueError('Nonempty train, dev and test cohorts are required')
    if {row['relationship'] for row in selected if row['split'] == 'train'} != set(RELATIONS):
        raise ValueError('All four relationship classes must occur in training')
    return selected


def texts(rows, mode):
    if mode == 'source_only':
        return [row['source_text'] for row in rows]
    if mode == 'outcome_only':
        return [row['outcome_text'] for row in rows]
    return ['SOURCE '+row['source_text']+' OUTCOME '+row['outcome_text'] for row in rows]


def metrics(labels, predictions):
    precision, recall, f1, support = precision_recall_fscore_support(
        labels, predictions, labels=RELATIONS, zero_division=0)
    return {'ai_label_agreement': float(accuracy_score(labels, predictions)),
            'macro_f1_four_classes': float(np.mean(f1)),
            'per_class': {label: {'precision': float(precision[i]), 'recall': float(recall[i]),
                'f1': float(f1[i]), 'reference_support': int(support[i])} for i, label in enumerate(RELATIONS)},
            'absent_reference_classes': [label for label, n in zip(RELATIONS, support) if not n],
            'confusion_matrix_label_order': RELATIONS,
            'confusion_matrix': confusion_matrix(labels, predictions, labels=RELATIONS).tolist()}


def train(data, output):
    rows = load_rows(data)
    provenance_path = data.parent/'annotation_provenance.json'
    provenance = json.loads(provenance_path.read_text())
    if provenance['labels_sha256'] != digest(data):
        raise ValueError('Frozen AI annotation data changed')
    for name, expected in provenance['source_sha256'].items():
        if digest(ROOT/name) != expected:
            raise ValueError('An annotation reference or curation source changed')
    training = [row for row in rows if row['split'] == 'train']
    development = [row for row in rows if row['split'] == 'dev']
    output.mkdir(parents=True, exist_ok=False)
    counts = {label: sum(row['relationship'] == label for row in training) for label in RELATIONS}
    majority = max(RELATIONS, key=lambda label: counts[label])
    protocol = {'status': 'AI-generated weak-supervision pilot; no independent human accuracy measured',
        'selection': 'Development four-class macro F1; ties prefer earlier/simpler candidate',
        'seed': 42, 'class_weight': 'balanced', 'paired_C_grid': [.1, 1., 10.],
        'training_examples': len(training), 'development_examples': len(development),
        'splits': {split: sorted({row['group'] for row in rows if row['split'] == split}) for split in ['train', 'dev', 'test']},
        'input_path': str(data.resolve()), 'input_sha256': digest(data),
        'annotation_provenance_sha256': digest(provenance_path), 'labels': RELATIONS,
        'source_sha256': digest(Path(__file__)), 'sklearn_version': sklearn.__version__,
        'input_note': 'Reference transcripts and supplied outcomes; some outcomes are human written meeting summaries.',
        'reference_note': 'Relation labels generated by one Codex assistant; no human adjudication or independent inter-annotator agreement.',
        'installed_in_application': False}
    save(output/'protocol.json', protocol)
    labels = [row['relationship'] for row in development]
    search = [{'name': 'majority', 'C': None, 'development': metrics(labels, [majority]*len(labels))}]
    models = {}
    for mode in ['source_only', 'outcome_only', 'paired']:
        candidates = []
        for c in protocol['paired_C_grid'] if mode == 'paired' else [1.]:
            model = Pipeline([('features', FeatureUnion([
                ('word', TfidfVectorizer(ngram_range=(1, 2), max_features=6000, sublinear_tf=True)),
                ('character', TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), max_features=10000, sublinear_tf=True))])),
                ('classifier', LogisticRegression(C=c, class_weight='balanced', max_iter=2000, random_state=42))])
            model.fit(texts(training, mode), [row['relationship'] for row in training])
            entry = {'name': mode, 'C': c, 'development': metrics(labels, model.predict(texts(development, mode)))}
            search.append(entry); candidates.append((entry, model))
        selected, models[mode] = max(candidates, key=lambda item: item[0]['development']['macro_f1_four_classes'])
    primary = max(search, key=lambda entry: entry['development']['macro_f1_four_classes'])
    joblib.dump({'models': models, 'majority_label': majority}, output/'models.joblib')
    save(output/'development_search.json', search)
    save(output/'selection.json', {**primary, 'model_sha256': digest(output/'models.joblib'), 'installed_in_application': False})
    print(json.dumps({'frozen_primary': primary['name'], 'development': primary['development']}, indent=2))


def evaluate(data, output):
    target = output/'ai_agreement_evaluation.json'
    if target.exists():
        raise ValueError('Preserve the existing AI-agreement evaluation')
    protocol = json.loads((output/'protocol.json').read_text())
    selection = json.loads((output/'selection.json').read_text())
    if digest(data) != protocol['input_sha256'] or digest(Path(__file__)) != protocol['source_sha256']:
        raise ValueError('Frozen data or evaluation source changed')
    if digest(data.parent/'annotation_provenance.json') != protocol['annotation_provenance_sha256'] or protocol['labels'] != RELATIONS:
        raise ValueError('Annotation provenance or label schema changed')
    if digest(output/'models.joblib') != selection['model_sha256']:
        raise ValueError('Frozen models changed')
    rows = [row for row in load_rows(data) if row['split'] == 'test']
    labels = [row['relationship'] for row in rows]
    bundle = joblib.load(output/'models.joblib')
    predictions = {'majority': [bundle['majority_label']]*len(rows), **{
        mode: model.predict(texts(rows, mode)).tolist() for mode, model in bundle['models'].items()}}
    result = {'status': protocol['status'], 'examples': len(rows), 'project_groups': sorted({row['group'] for row in rows}),
        'primary_selected_on_development': selection['name'],
        'methods': {mode: metrics(labels, values) for mode, values in predictions.items()},
        'predictions': [{'pair_id': row['pair_id'], 'group': row['group'], 'ai_reference': labels[i],
                         **{mode: values[i] for mode, values in predictions.items()}} for i, row in enumerate(rows)],
        'independent_human_accuracy_measured': False, 'presenter_influence_accuracy_measured': False,
        'installed_in_application': False}
    save(target, result)
    print(json.dumps({mode: {'ai_label_agreement': value['ai_label_agreement'], 'macro_f1_four_classes': value['macro_f1_four_classes']}
                      for mode, value in result['methods'].items()}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--evaluate', action='store_true')
    args = parser.parse_args()
    evaluate(args.data, args.output_dir) if args.evaluate else train(args.data, args.output_dir)
