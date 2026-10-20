"""Freeze a forest/linear pipeline on dev, then evaluate and package for review."""
import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.compare_discussion_models import thresholds
from scripts.evaluate_decision_discussions import metrics
from scripts.improve_decision_discussions import breakdown, load_rows, sha256
from src.meeting.discussions import MODEL_VERSION, component_scores, combine_scores
from src.utils.cache import atomic_json

OUT = ROOT / 'professor_guidelines/evaluation/pipeline_improvement'
WORK = ROOT / '.runtime/research-discussion-pipeline'
SOURCES = {
    'linear': ROOT / '.runtime/research-classifier-comparison/logistic_regression__context_40.joblib',
    'forest': ROOT / '.runtime/research-classifier-comparison/random_forest__context_40.joblib',
    'vectorizers': ROOT / '.runtime/research-decision-model-v2/context_40.joblib',
}
WEIGHTS = [0., .25, .5, .75, 1.]


def base_bundle():
    return {'version': MODEL_VERSION, 'task': 'discussion_membership', 'context_radius': 40,
        'vectorizers': joblib.load(SOURCES['vectorizers'])['vectorizers'],
        'classifiers': {key: joblib.load(SOURCES[key])['classifier'] for key in ['linear', 'forest']}}


def train():
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    protocol = {'status': 'Further exploratory development on existing AMI cohort',
        'linear_weight_grid': WEIGHTS, 'smoothing_radius_grid': [0, 5, 15],
        'threshold_rule': 'Same 13 dev-score quantiles plus 0.5 as matched comparison',
        'selection': 'Maximum pooled dev F1; fixed loop order breaks ties',
        'models': 'Reuse train-fitted, previously dev-selected context-40 LR and random forest',
        'component_sha256': {key: sha256(path) for key, path in SOURCES.items()},
        'train_sha256': sha256(ROOT / '.runtime/research-decision-model/train.jsonl'),
        'dev_sha256': sha256(ROOT / '.runtime/research-decision-model/dev.jsonl'),
        'code_sha256': {str(path.relative_to(ROOT)): sha256(path) for path in [Path(__file__),
            ROOT / 'src/meeting/discussions.py', ROOT / 'scripts/compare_discussion_models.py',
            ROOT / 'scripts/improve_decision_discussions.py']},
        'test_access': 'Separate --evaluate invocation after saving model and selection hashes',
        'runtime': 'Batched local scoring of actual transcript passages; English only; suggestions for human review',
        'limits': ['Oracle-act results are not ASR-passage accuracy.',
                   'Historical test cohort previously examined; only three independent series.',
                   'Discussion suggestions do not create final decisions or alter influence weights.']}
    atomic_json(OUT / 'protocol.json', protocol)
    bundle = base_bundle()
    rows = load_rows('dev')
    truth = np.array([r['label'] for r in rows])
    components = component_scores(rows, bundle)
    np.savez(WORK / 'dev_components.npz', **components)
    search, best = [], None
    for weight in WEIGHTS:
        for radius in [0, 5, 15]:
            scores = combine_scores(rows, components, weight, radius)
            for threshold in thresholds(scores):
                value = metrics(truth, scores >= threshold, scores)
                candidate = {'linear_weight': weight, 'smoothing_radius': radius,
                             'threshold': float(threshold), 'dev': value}
                search.append(candidate)
                if best is None or value['f1'] > best['dev']['f1']:
                    best = dict(candidate)
    method = ('forest_discussion_review' if best['linear_weight'] == 0 else
              'linear_discussion_review' if best['linear_weight'] == 1 else 'forest_linear_discussion_review')
    joblib.dump({**bundle, **best, 'method': method}, WORK / 'model.joblib')
    selection = {**best, 'model_sha256': sha256(WORK / 'model.joblib'),
                 'protocol_sha256': sha256(OUT / 'protocol.json')}
    atomic_json(OUT / 'selection.json', selection)
    atomic_json(OUT / 'dev_search.json', search)
    print('FROZEN', json.dumps(selection), flush=True)


def evaluate():
    protocol = json.loads((OUT / 'protocol.json').read_text())
    selection_hash = sha256(OUT / 'selection.json')
    selection = json.loads((OUT / 'selection.json').read_text())
    assert sha256(OUT / 'protocol.json') == selection['protocol_sha256']
    assert sha256(WORK / 'model.joblib') == selection['model_sha256']
    for key, digest in protocol['component_sha256'].items():
        assert sha256(SOURCES[key]) == digest
    for path, digest in protocol['code_sha256'].items():
        assert sha256(ROOT / path) == digest
    for split in ['train', 'dev']:
        assert sha256(ROOT / '.runtime/research-decision-model' / (split + '.jsonl')) == protocol[split + '_sha256']
    rows = load_rows('test')
    bundle = joblib.load(WORK / 'model.joblib')
    components = component_scores(rows, bundle)
    scores = combine_scores(rows, components, selection['linear_weight'], selection['smoothing_radius'])
    truth = np.array([r['label'] for r in rows])
    result = {'selection': selection, 'selection_sha256_before_test_access': selection_hash,
        'test': metrics(truth, scores >= selection['threshold'], scores),
        'test_per_group': breakdown(rows, scores, selection['threshold'], 'group'),
        'test_per_meeting': breakdown(rows, scores, selection['threshold'], 'meeting'),
        'status': 'Oracle-act historical comparison; actual ASR-passage accuracy remains unmeasured'}
    # Report all prespecified weights, each with settings selected exclusively on dev.
    search = json.loads((OUT / 'dev_search.json').read_text())
    result['variants'] = []
    for weight in WEIGHTS:
        chosen = max([r for r in search if r['linear_weight'] == weight], key=lambda r: r['dev']['f1'])
        variant_scores = combine_scores(rows, components, weight, chosen['smoothing_radius'])
        result['variants'].append({**chosen, 'test': metrics(truth, variant_scores >= chosen['threshold'], variant_scores)})
    np.savez(WORK / 'historical_predictions.npz', scores=scores, truth=truth)
    atomic_json(OUT / 'summary.json', result)
    print(json.dumps(result, indent=2))


def install():
    # Installation always uses the frozen dev-selected model, irrespective of historical ranking.
    selection_hash = sha256(OUT / 'selection.json')
    selection = json.loads((OUT / 'selection.json').read_text())
    assert sha256(WORK / 'model.joblib') == selection['model_sha256']
    bundle = joblib.load(WORK / 'model.joblib')
    target = ROOT / 'models/discussion'
    target.mkdir(parents=True, exist_ok=True)
    temporary = target / 'model.joblib.tmp'
    joblib.dump({**bundle, 'selection_sha256': selection_hash}, temporary)
    temporary.replace(target / 'model.joblib')
    atomic_json(target / 'manifest.json', {'task': 'discussion_membership', 'language': 'en',
        'selection_sha256': selection_hash, 'model_sha256': sha256(target / 'model.joblib'),
        'scope': 'Review suggestions on ASR passages; no measured recording-level accuracy',
        **{key: selection[key] for key in ['linear_weight', 'smoothing_radius', 'threshold']}})
    print('Installed', target / 'model.joblib')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--evaluate', action='store_true')
    mode.add_argument('--install', action='store_true')
    args = parser.parse_args()
    install() if args.install else evaluate() if args.evaluate else train()
