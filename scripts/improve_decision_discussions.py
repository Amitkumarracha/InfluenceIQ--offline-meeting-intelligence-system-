"""Train/dev-only context experiments; score the frozen historical cohort separately.

Run without flags to freeze development selections, then with --evaluate to score.
The previously examined test cohort is exploratory, not a fresh final test.
"""
import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.evaluate_decision_discussions import metrics
from src.utils.cache import atomic_json

SOURCE = ROOT / '.runtime/research-decision-model'
WORK = ROOT / '.runtime/research-decision-model-v2'
OUT = ROOT / 'professor_guidelines/evaluation/decision_discussion_v2'
VARIANTS = {
    'local': None,
    'context_1': 1,
    'context_5': 5,
    'context_15': 15,
    'context_40': 40,
    'context_15_position': 15,
}
C_GRID = [.3, 1., 3.]
SMOOTHING_GRID = [0, 5, 15]
THRESHOLDS = np.arange(.15, .751, .05).round(2).tolist()


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rows(split):
    return [json.loads(line) for line in (SOURCE / (split + '.jsonl')).read_text().splitlines()]


def meeting_indices(rows):
    meetings = {}
    for i, row in enumerate(rows):
        meetings.setdefault(row['meeting'], []).append(i)
    return [np.array(sorted(indices, key=lambda i: (rows[i]['start'], rows[i]['act_id'])))
            for indices in meetings.values()]


def context_texts(rows, radius):
    """Use input text only, keeping neighbours within the same meeting."""
    texts = [''] * len(rows)
    for indices in meeting_indices(rows):
        for offset, index in enumerate(indices):
            texts[index] = ' '.join(rows[j]['text'] for j in indices[
                max(0, offset - radius):offset + radius + 1])
    return texts


def position_features(rows):
    """Observable recording position only; no meeting IDs, roles or act-type labels."""
    result = np.zeros((len(rows), 3))
    for indices in meeting_indices(rows):
        first = min(rows[i]['start'] for i in indices)
        duration = max(rows[i]['end'] for i in indices) - first
        position = np.array([(rows[i]['start'] - first) / max(duration, 1.) for i in indices])
        result[indices] = np.column_stack([position, position ** 2, position ** 3])
    return csr_matrix(result)


def smooth_scores(rows, scores, radius):
    scores = np.asarray(scores, dtype=float)
    if radius == 0:
        return scores.copy()
    result = np.empty(len(scores))
    for indices in meeting_indices(rows):
        cumulative = np.r_[0., np.cumsum(scores[indices])]
        offsets = np.arange(len(indices))
        left = np.maximum(0, offsets - radius)
        right = np.minimum(len(indices), offsets + radius + 1)
        result[indices] = (cumulative[right] - cumulative[left]) / (right - left)
    return result


def breakdown(rows, scores, threshold, field):
    truth = np.array([r['label'] for r in rows])
    return [{field: name, **metrics(truth[mask], scores[mask] >= threshold, scores[mask])}
            for name in sorted({r[field] for r in rows})
            for mask in [np.array([r[field] == name for r in rows])]]


def vectorize(rows, vectorizers=None):
    fitted = {} if vectorizers is None else vectorizers
    matrices = {}
    fields = {'word': [r['text'] for r in rows], 'char': [r['text'] for r in rows]}
    fields.update({f'context_{radius}': context_texts(rows, radius) for radius in [1, 5, 15, 40]})
    for name, texts in fields.items():
        if vectorizers is None:
            char = name == 'char'
            fitted[name] = TfidfVectorizer(analyzer='char_wb' if char else 'word',
                ngram_range=(3, 5) if char else (1, 2), min_df=2,
                max_features=20000 if char else 12000, sublinear_tf=True)
            matrices[name] = fitted[name].fit_transform(texts)
        else:
            matrices[name] = fitted[name].transform(texts)
    matrices['position'] = position_features(rows)
    return fitted, matrices


def feature_matrix(matrices, name):
    radius = VARIANTS[name]
    names = ['word', 'char'] + ([f'context_{radius}'] if radius is not None else [])
    if name.endswith('_position'):
        names.append('position')
    return hstack([matrices[key] for key in names], format='csr')


def train():
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    # Write the finite search and data provenance before fitting; do not read test rows.
    protocol = {
        'task': 'Unchanged AMI oracle-input decision-discussion membership',
        'status': 'Continued development after inspecting the original test results',
        'variants': VARIANTS, 'C_grid': C_GRID, 'smoothing_radius_grid': SMOOTHING_GRID,
        'class_weight': 'balanced', 'threshold_grid': THRESHOLDS, 'seed': 42,
        'selection': 'Maximum pooled development F1; fixed iteration order breaks ties',
        'smoothing_ablation': 'Same fitted classifier, no smoothing, threshold reselected on development F1',
        'secondary_operating_point': 'On selected model only: maximum dev precision with dev recall >= 0.5',
        'features': 'Train-fitted TF-IDF text; optional relative recording position and its square/cube',
        'smoothing': 'Arithmetic mean of predicted probabilities within +/- radius acts of same meeting',
        'split_protocol_sha256': sha256(ROOT / 'professor_guidelines/evaluation/decision_discussion/protocol.json'),
        'baseline_summary_sha256': sha256(ROOT / 'professor_guidelines/evaluation/decision_discussion/summary.json'),
        'train_sha256': sha256(SOURCE / 'train.jsonl'), 'dev_sha256': sha256(SOURCE / 'dev.jsonl'),
        'script_sha256': sha256(Path(__file__)),
        'test_access': 'Separate --evaluate invocation after model and selection are saved',
        'limits': ['Same previously examined historical test cohort; fresh independent confirmation required.',
                   'Reference transcripts, act boundaries and recording position are oracle inputs.',
                   'Offline next-act access; no streaming or final-decision extraction claim.',
                   'No new annotations, relabelling, generative model or production model installation.'],
    }
    atomic_json(OUT / 'protocol.json', protocol)
    rows = {split: load_rows(split) for split in ['train', 'dev']}
    assert not {r['group'] for r in rows['train']} & {r['group'] for r in rows['dev']}
    truth = {split: np.array([r['label'] for r in values]) for split, values in rows.items()}
    started = time.perf_counter()
    vectorizers, train_matrices = vectorize(rows['train'])
    _, dev_matrices = vectorize(rows['dev'], vectorizers)
    selected, candidates = {}, []
    for name in VARIANTS:
        x_train, x_dev = feature_matrix(train_matrices, name), feature_matrix(dev_matrices, name)
        best = None
        for c in C_GRID:
            model = LogisticRegression(C=c, class_weight='balanced', max_iter=500,
                solver='liblinear', random_state=42).fit(x_train, truth['train'])
            raw = model.predict_proba(x_dev)[:, 1]
            for radius in SMOOTHING_GRID:
                scores = smooth_scores(rows['dev'], raw, radius)
                for threshold in THRESHOLDS:
                    value = metrics(truth['dev'], scores >= threshold, scores)
                    candidate = {'method': name, 'C': c, 'smoothing_radius': radius,
                                 'threshold': threshold, 'dev': value}
                    candidates.append(candidate)
                    if best is None or value['f1'] > best['dev']['f1']:
                        best = dict(candidate)
                        chosen_model, chosen_scores = model, scores
        best['dev_per_group'] = breakdown(rows['dev'], chosen_scores, best['threshold'], 'group')
        best['dev_per_meeting'] = breakdown(rows['dev'], chosen_scores, best['threshold'], 'meeting')
        best['unsmoothed_operating_point'] = max(
            [r for r in candidates if r['method'] == name and r['C'] == best['C'] and r['smoothing_radius'] == 0],
            key=lambda r: r['dev']['f1'])
        selected[name] = best
        joblib.dump({'classifier': chosen_model, 'vectorizers': vectorizers, **best}, WORK / (name + '.joblib'))
        print('Dev selected', json.dumps(best), flush=True)
    primary = max(selected, key=lambda name: selected[name]['dev']['f1'])
    # A separately frozen precision-oriented threshold keeps the recall trade-off explicit.
    bundle = joblib.load(WORK / (primary + '.joblib'))
    scores = smooth_scores(rows['dev'], bundle['classifier'].predict_proba(
        feature_matrix(dev_matrices, primary))[:, 1], bundle['smoothing_radius'])
    precision_candidates = []
    for threshold in THRESHOLDS:
        value = metrics(truth['dev'], scores >= threshold, scores)
        if value['recall'] >= .5:
            precision_candidates.append({'threshold': threshold, 'dev': value})
    precision_point = max(precision_candidates, key=lambda r: (r['dev']['precision'], r['dev']['f1'])) if precision_candidates else None
    selection = {'primary': primary, 'models': list(selected.values()),
                 'precision_operating_point': precision_point,
                 'train_and_selection_seconds': time.perf_counter() - started,
                 'model_sha256': {name: sha256(WORK / (name + '.joblib')) for name in selected},
                 'protocol_sha256': sha256(OUT / 'protocol.json')}
    atomic_json(OUT / 'selection.json', selection)
    atomic_json(OUT / 'dev_search.json', candidates)
    with (OUT / 'dev_search.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['method', 'C', 'smoothing_radius', 'threshold', 'precision', 'recall', 'f1', 'average_precision'])
        for row in candidates:
            writer.writerow([row['method'], row['C'], row['smoothing_radius'], row['threshold'],
                             *[row['dev'][k] for k in ['precision', 'recall', 'f1', 'average_precision']]])
    print('FROZEN primary:', primary, 'dev:', selected[primary]['dev'], flush=True)


def evaluate():
    selection_path = OUT / 'selection.json'
    selection_hash = sha256(selection_path)
    selection = json.loads(selection_path.read_text())
    protocol = json.loads((OUT / 'protocol.json').read_text())
    assert sha256(OUT / 'protocol.json') == selection['protocol_sha256'], 'Protocol changed after selection'
    assert sha256(Path(__file__)) == protocol['script_sha256'], 'Script changed after selection; retrain first'
    for split in ['train', 'dev']:
        assert sha256(SOURCE / (split + '.jsonl')) == protocol[split + '_sha256']
    for name, digest in selection['model_sha256'].items():
        assert sha256(WORK / (name + '.joblib')) == digest, 'Model changed after selection'
    rows = load_rows('test')
    seen_groups = {r['group'] for split in ['train', 'dev'] for r in load_rows(split)}
    assert not seen_groups & {r['group'] for r in rows}
    truth = np.array([r['label'] for r in rows])
    bundle = joblib.load(WORK / (selection['primary'] + '.joblib'))
    _, matrices = vectorize(rows, bundle['vectorizers'])
    outputs = []
    predictions_path = WORK / 'historical_predictions.jsonl'
    with predictions_path.open('w') as stream:
        for chosen in selection['models']:
            name = chosen['method']
            bundle = joblib.load(WORK / (name + '.joblib'))
            raw = bundle['classifier'].predict_proba(feature_matrix(matrices, name))[:, 1]
            scores = smooth_scores(rows, raw, chosen['smoothing_radius'])
            outputs.append({**chosen, 'test': metrics(truth, scores >= chosen['threshold'], scores),
                'test_per_group': breakdown(rows, scores, chosen['threshold'], 'group'),
                'test_per_meeting': breakdown(rows, scores, chosen['threshold'], 'meeting'),
                'unsmoothed_test': metrics(truth, raw >= chosen['unsmoothed_operating_point']['threshold'], raw)})
            for row, score in zip(rows, scores):
                stream.write(json.dumps({'method': name, 'act_id': row['act_id'], 'meeting': row['meeting'],
                    'group': row['group'], 'label': row['label'], 'score': float(score),
                    'predicted': int(score >= chosen['threshold'])}) + '\n')
            if name == selection['primary'] and selection['precision_operating_point']:
                point = selection['precision_operating_point']
                precision_result = {**point, 'test': metrics(truth, scores >= point['threshold'], scores)}
    result = {'primary': selection['primary'], 'selection_sha256_before_test_access': selection_hash,
        'test_sha256': sha256(SOURCE / 'test.jsonl'), 'predictions_sha256': sha256(predictions_path),
        'models': outputs, 'precision_operating_point': precision_result if selection['precision_operating_point'] else None,
        'status': 'Exploratory historical-cohort comparison; no fresh final evaluation or app accuracy claim'}
    atomic_json(OUT / 'summary.json', result)
    print(json.dumps({**result, 'models': [{'method': r['method'], 'test': r['test']} for r in outputs]}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evaluate', action='store_true')
    evaluate() if parser.parse_args().evaluate else train()
