"""Matched quick classifier comparison; freeze on dev, evaluate history separately."""
import argparse
import csv
import json
import platform
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import sklearn
from scipy.sparse import hstack
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.naive_bayes import ComplementNB
from sklearn.svm import LinearSVC
from sklearn.utils.class_weight import compute_sample_weight

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.evaluate_decision_discussions import metrics
from scripts.improve_decision_discussions import (
    breakdown, context_texts, load_rows, sha256, smooth_scores,
)
from src.utils.cache import atomic_json

OUT = ROOT / 'professor_guidelines/evaluation/classifier_comparison'
WORK = ROOT / '.runtime/research-classifier-comparison'
VECTORIZER_SOURCE = ROOT / '.runtime/research-decision-model-v2/context_40.joblib'
FAMILIES = {
    'logistic_regression': [.3, 1., 3.],
    'complement_nb': [.1, 1., 10.],
    'linear_svm': [.3, 1., 3.],
    'random_forest': [10, 30, None],
}
FEATURES = ['local', 'context_40']
SMOOTHING = [0, 5, 15]
QUANTILES = np.linspace(.05, .95, 13)


def calibration_folds(rows):
    groups = np.array([row['group'] for row in rows])
    return list(GroupKFold(n_splits=3).split(np.zeros(len(rows)), groups=groups))


def thresholds(scores):
    # Equal search opportunity even for sharply concentrated NB/forest probabilities.
    return np.unique(np.r_[np.quantile(scores, QUANTILES), .5])


def estimator(family, parameter, folds):
    if family == 'logistic_regression':
        return LogisticRegression(C=parameter, class_weight='balanced', solver='liblinear',
                                  max_iter=500, random_state=42)
    if family == 'complement_nb':
        return ComplementNB(alpha=parameter)
    if family == 'linear_svm':
        return CalibratedClassifierCV(
            LinearSVC(C=parameter, class_weight='balanced', max_iter=5000, random_state=42),
            method='sigmoid', cv=folds, ensemble=False, n_jobs=1)
    if family == 'random_forest':
        return RandomForestClassifier(n_estimators=100, max_depth=parameter,
            min_samples_leaf=2, class_weight='balanced_subsample', n_jobs=2, random_state=42)
    raise ValueError('Unknown classifier: ' + family)


def matrices(rows, vectorizers):
    local = hstack([vectorizers[key].transform([r['text'] for r in rows])
                    for key in ['word', 'char']], format='csr')
    context = vectorizers['context_40'].transform(context_texts(rows, 40))
    return {'local': local, 'context_40': hstack([local, context], format='csr')}


def train():
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    source = ROOT / '.runtime/research-decision-model'
    protocol = {
        'task': 'Unchanged binary AMI reference-act decision-discussion membership',
        'status': 'Exploratory comparison after previous historical-cohort inspection',
        'families_and_parameter_grid': FAMILIES,
        'parameter_names': {'logistic_regression': 'C', 'complement_nb': 'alpha',
                            'linear_svm': 'C', 'random_forest': 'max_depth'},
        'features': FEATURES, 'smoothing_radius_grid': SMOOTHING,
        'threshold_quantiles': QUANTILES.tolist(), 'additional_threshold': .5,
        'thresholds': 'Each configuration: 13 fixed dev-score quantiles plus 0.5; duplicate thresholds removed',
        'selection': 'Pooled development F1, fixed loop order breaks ties; all eight pipelines retained',
        'primary': 'Maximum development F1 across the eight independently selected pipelines',
        'vectorizers': 'Reuse unchanged train-fitted v2 word/character/context-40 TF-IDF for every family',
        'svm': 'Sigmoid calibration from three project-group-separated training folds; final SVM fits all training rows',
        'calibration_limit': 'Training-fitted TF-IDF vocabulary/IDF shared by inner calibration folds; no dev/test text fitted',
        'random_forest': {'n_estimators': 100, 'min_samples_leaf': 2,
                          'class_weight': 'balanced_subsample', 'max_features': 'sqrt'},
        'class_balance': 'Balanced class/sample weights for LR/SVM/NB; balanced_subsample for forest',
        'seed': 42, 'python': platform.python_version(), 'scikit_learn': sklearn.__version__,
        'vectorizer_source_sha256': sha256(VECTORIZER_SOURCE),
        'v2_summary_sha256': sha256(ROOT / 'professor_guidelines/evaluation/decision_discussion_v2/summary.json'),
        'v1_summary_sha256': sha256(ROOT / 'professor_guidelines/evaluation/decision_discussion/summary.json'),
        'train_sha256': sha256(source / 'train.jsonl'), 'dev_sha256': sha256(source / 'dev.jsonl'),
        'code_sha256': {str(path.relative_to(ROOT)): sha256(path) for path in [Path(__file__),
            ROOT / 'scripts/improve_decision_discussions.py', ROOT / 'scripts/evaluate_decision_discussions.py']},
        'test_access': 'Only in separate --evaluate invocation after selections and model hashes saved',
        'limits': ['Previously examined historical cohort; no fresh independent confirmatory test.',
                   'Oracle English transcripts and act boundaries; only three test project series.',
                   'Classifier comparison, not a benchmark of complete meeting assistants or influence.',
                   'Same small search count does not mean equal compute or globally optimal hyperparameters.'],
        'documentation': [
            'https://scikit-learn.org/1.6/auto_examples/text/plot_document_classification_20newsgroups.html',
            'https://scikit-learn.org/1.6/modules/generated/sklearn.calibration.CalibratedClassifierCV.html'],
    }
    atomic_json(OUT / 'protocol.json', protocol)
    train_rows, dev_rows = load_rows('train'), load_rows('dev')
    assert not {r['group'] for r in train_rows} & {r['group'] for r in dev_rows}
    y_train = np.array([r['label'] for r in train_rows])
    y_dev = np.array([r['label'] for r in dev_rows])
    bundle = joblib.load(VECTORIZER_SOURCE)
    started = time.perf_counter()
    x_train, x_dev = matrices(train_rows, bundle['vectorizers']), matrices(dev_rows, bundle['vectorizers'])
    transform_seconds = time.perf_counter() - started
    folds = calibration_folds(train_rows)
    atomic_json(OUT / 'calibration_groups.json', [{
        'fit_groups': sorted({train_rows[i]['group'] for i in fit}),
        'calibration_groups': sorted({train_rows[i]['group'] for i in cal})} for fit, cal in folds])
    selected, search = [], []
    for feature in FEATURES:
        for family, parameters in FAMILIES.items():
            name = family + '__' + feature
            best = None
            fit_seconds = 0.
            for parameter in parameters:
                model = estimator(family, parameter, folds)
                started = time.perf_counter()
                if family == 'complement_nb':
                    model.fit(x_train[feature], y_train, sample_weight=compute_sample_weight('balanced', y_train))
                else:
                    model.fit(x_train[feature], y_train)
                fit_seconds += time.perf_counter() - started
                raw = model.predict_proba(x_dev[feature])[:, 1]
                for radius in SMOOTHING:
                    scores = smooth_scores(dev_rows, raw, radius)
                    for threshold in thresholds(scores):
                        value = metrics(y_dev, scores >= threshold, scores)
                        candidate = {'method': name, 'family': family, 'features': feature,
                            'parameter': parameter, 'smoothing_radius': radius,
                            'threshold': float(threshold), 'dev': value}
                        search.append(candidate)
                        if best is None or value['f1'] > best['dev']['f1']:
                            best = dict(candidate)
                            chosen_model, chosen_scores = model, scores
            best['fit_grid_seconds'] = fit_seconds
            best['dev_per_group'] = breakdown(dev_rows, chosen_scores, best['threshold'], 'group')
            selected.append(best)
            joblib.dump({'classifier': chosen_model, **best}, WORK / (name + '.joblib'))
            print('Dev selected', name, json.dumps(best['dev']), flush=True)
    selection = {'models': selected, 'primary': max(selected, key=lambda r: r['dev']['f1'])['method'],
        'shared_transform_seconds': transform_seconds,
        'protocol_sha256': sha256(OUT / 'protocol.json'),
        'model_sha256': {r['method']: sha256(WORK / (r['method'] + '.joblib')) for r in selected}}
    atomic_json(OUT / 'dev_search.json', search)
    atomic_json(OUT / 'selection.json', selection)
    print('FROZEN primary', selection['primary'], flush=True)


def evaluate():
    selection_path = OUT / 'selection.json'
    selection_hash = sha256(selection_path)
    selection = json.loads(selection_path.read_text())
    protocol = json.loads((OUT / 'protocol.json').read_text())
    assert sha256(OUT / 'protocol.json') == selection['protocol_sha256']
    assert sha256(VECTORIZER_SOURCE) == protocol['vectorizer_source_sha256']
    for path, digest in protocol['code_sha256'].items():
        assert sha256(ROOT / path) == digest, 'Code changed after selection'
    for split in ['train', 'dev']:
        assert sha256(ROOT / '.runtime/research-decision-model' / (split + '.jsonl')) == protocol[split + '_sha256']
    for name, digest in selection['model_sha256'].items():
        assert sha256(WORK / (name + '.joblib')) == digest
    rows = load_rows('test')
    source_groups = {r['group'] for split in ['train', 'dev'] for r in load_rows(split)}
    assert not source_groups & {r['group'] for r in rows}
    truth = np.array([r['label'] for r in rows])
    vectorizers = joblib.load(VECTORIZER_SOURCE)['vectorizers']
    started = time.perf_counter()
    x_test = matrices(rows, vectorizers)
    transform_seconds = time.perf_counter() - started
    outputs = []
    predictions_path = WORK / 'historical_predictions.jsonl'
    with predictions_path.open('w') as stream:
        for chosen in selection['models']:
            model = joblib.load(WORK / (chosen['method'] + '.joblib'))['classifier']
            started = time.perf_counter()
            raw = model.predict_proba(x_test[chosen['features']])[:, 1]
            scores = smooth_scores(rows, raw, chosen['smoothing_radius'])
            elapsed = time.perf_counter() - started
            outputs.append({**chosen, 'test': metrics(truth, scores >= chosen['threshold'], scores),
                'test_per_group': breakdown(rows, scores, chosen['threshold'], 'group'),
                'test_per_meeting': breakdown(rows, scores, chosen['threshold'], 'meeting'),
                'classification_and_smoothing_seconds': elapsed,
                'timing_scope': 'Single warm classifier+smoothing pass; excludes text transforms, loading and I/O'})
            for row, score in zip(rows, scores):
                stream.write(json.dumps({'method': chosen['method'], 'act_id': row['act_id'],
                    'meeting': row['meeting'], 'label': row['label'], 'score': float(score),
                    'predicted': int(score >= chosen['threshold'])}) + '\n')
    result = {'primary': selection['primary'], 'models': outputs,
        'selection_sha256_before_test_access': selection_hash,
        'test_sha256': sha256(ROOT / '.runtime/research-decision-model/test.jsonl'),
        'predictions_sha256': sha256(predictions_path), 'shared_test_transform_seconds': transform_seconds,
        'status': 'Historical-cohort exploratory model comparison; all configurations retained'}
    atomic_json(OUT / 'summary.json', result)
    with (OUT / 'comparison.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['method', 'dev_f1', 'precision', 'recall', 'f1', 'average_precision'])
        for row in outputs:
            writer.writerow([row['method'], row['dev']['f1'],
                *[row['test'][key] for key in ['precision', 'recall', 'f1', 'average_precision']]])
    print(json.dumps({'primary': result['primary'], 'models': [
        {'method': r['method'], 'test': r['test']} for r in outputs]}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evaluate', action='store_true')
    evaluate() if parser.parse_args().evaluate else train()
