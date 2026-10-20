"""Finite semantic/context search with a development non-regression gate."""
import argparse
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, matthews_corrcoef, roc_auc_score, brier_score_loss

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.compare_discussion_models import thresholds
from scripts.evaluate_decision_discussions import metrics
from scripts.improve_decision_discussions import load_rows, sha256, smooth_scores, breakdown
from src.meeting.discussions import component_scores, combine_scores
from src.meeting.discussion_semantics import encode_rows, context_features
from src.utils.cache import atomic_json

OUT = ROOT / 'professor_guidelines/evaluation/semantic_quality'
WORK = ROOT / '.runtime/research-semantic-quality'
BASE = ROOT / '.runtime/research-discussion-pipeline/model.joblib'
FEATURES = {'context_5': (5, False), 'context_15': (15, False),
            'context_40': (40, False), 'context_15_timing': (15, True)}
PARAMETERS = {'linear': [.3, 3., 30.], 'boosted': [15, 31]}
BLENDS = [0., .25, .5, .75, 1.]
GUARD_METRICS = ['precision', 'recall', 'f1', 'average_precision', 'accuracy']


def with_accuracy(value):
    tn, fp, fn, tp = value['confusion_matrix_tn_fp_fn_tp']
    return {**value, 'accuracy': (tn+tp)/(tn+fp+fn+tp)}


def all_metrics(truth, scores, threshold):
    predicted = scores >= threshold
    value = with_accuracy(metrics(truth, predicted, scores))
    tn, fp, fn, tp = value['confusion_matrix_tn_fp_fn_tp']
    return {**value, 'balanced_accuracy': float(balanced_accuracy_score(truth, predicted)),
        'specificity': tn/(tn+fp) if tn+fp else 0., 'macro_f1': float(f1_score(truth, predicted, average='macro')),
        'mcc': float(matthews_corrcoef(truth, predicted)), 'roc_auc': float(roc_auc_score(truth, scores)),
        'brier': float(brier_score_loss(truth, scores)), 'negative_support': int(tn+fp)}


def passes_gate(candidate, baseline):
    return all(candidate[key] + 1e-12 >= baseline[key] for key in GUARD_METRICS)


def classifier(family, parameter):
    if family == 'linear':
        return LogisticRegression(C=parameter, class_weight='balanced', solver='lbfgs', max_iter=1000, random_state=42)
    return HistGradientBoostingClassifier(max_iter=120, learning_rate=.07, max_leaf_nodes=parameter,
        l2_regularization=10., max_bins=64, class_weight='balanced', early_stopping=False, random_state=42)


def embeddings(split, rows, fingerprint):
    path = WORK / (split+'_embeddings.npz')
    if path.exists():
        saved = np.load(path)
        if str(saved['fingerprint']) == fingerprint:
            return saved['vectors']
    values = encode_rows(rows)
    np.savez(path, vectors=values, fingerprint=fingerprint)
    return values


def train():
    OUT.mkdir(parents=True, exist_ok=True); WORK.mkdir(parents=True, exist_ok=True)
    model_dir = ROOT / 'models/hf/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
    fingerprint = sha256(model_dir/'model.safetensors')
    protocol = {'task': 'Unchanged AMI English decision-discussion act membership',
        'status': 'Continued exploratory optimization after earlier historical-cohort inspection',
        'features': FEATURES, 'classifiers_and_parameter_grid': PARAMETERS, 'semantic_blend_weights': BLENDS,
        'smoothing_radii': [0, 5, 15], 'thresholds': '13 fixed dev-score quantiles plus 0.5',
        'selection': 'Max dev F1 among candidates not worse on any gate metric; otherwise keep installed baseline',
        'gate_metrics': GUARD_METRICS, 'encoder': 'Frozen local all-MiniLM-L6-v2; encoder weights not fine-tuned',
        'encoder_weights_sha256': fingerprint, 'baseline_model_sha256': sha256(BASE),
        'train_sha256': sha256(ROOT/'.runtime/research-decision-model/train.jsonl'),
        'dev_sha256': sha256(ROOT/'.runtime/research-decision-model/dev.jsonl'),
        'code_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in [Path(__file__), ROOT/'src/meeting/discussion_semantics.py']},
        'test_access': 'Separate --evaluate invocation after saving selected model and hashes',
        'training': 'Balanced LR C=0.3/3/30; balanced histogram gradient boosting, leaves=15/31, 120 iterations, no random-act early stopping',
        'limits': ['Oracle text/act boundaries; full ASR accuracy requires separate annotation.',
            'Only two dev and three historical-test project series; no fresh confirmatory cohort.',
            'Relative timing may exploit scenario structure; the timing ablation is reported separately.',
            'Development non-regression does not guarantee non-regression on new data.']}
    atomic_json(OUT/'protocol.json', protocol)
    rows = {split: load_rows(split) for split in ['train', 'dev']}
    truth = {split: np.array([r['label'] for r in values]) for split, values in rows.items()}
    assert not {r['group'] for r in rows['train']} & {r['group'] for r in rows['dev']}
    started = time.perf_counter()
    vectors = {split: embeddings(split, values, fingerprint+protocol[split+'_sha256']) for split, values in rows.items()}
    print('Embeddings ready', {k: v.shape for k, v in vectors.items()}, flush=True)
    baseline_bundle = joblib.load(BASE)
    parts = component_scores(rows['dev'], baseline_bundle)
    baseline_raw = .25*parts['linear']+.75*parts['forest']
    baseline_scores = smooth_scores(rows['dev'], baseline_raw, baseline_bundle['smoothing_radius'])
    baseline = all_metrics(truth['dev'], baseline_scores, baseline_bundle['threshold'])
    best_gate = {'method': 'installed_baseline', 'dev': baseline, 'semantic_weight': 0.,
                 'smoothing_radius': baseline_bundle['smoothing_radius'], 'threshold': baseline_bundle['threshold']}
    gated_model = None
    selected, search = [], []
    for feature, (radius, timing) in FEATURES.items():
        x_train = context_features(rows['train'], vectors['train'], radius, timing)
        x_dev = context_features(rows['dev'], vectors['dev'], radius, timing)
        for family, parameters in PARAMETERS.items():
            method = family+'__'+feature
            best = None
            for parameter in parameters:
                model = classifier(family, parameter).fit(x_train, truth['train'])
                raw = model.predict_proba(x_dev)[:, 1]
                for weight in BLENDS:
                    combined = weight*raw+(1-weight)*baseline_raw
                    for smoothing in [0, 5, 15]:
                        scores = smooth_scores(rows['dev'], combined, smoothing)
                        for threshold in thresholds(scores):
                            value = with_accuracy(metrics(truth['dev'], scores >= threshold, scores))
                            candidate = {'method': method, 'family': family, 'feature': feature,
                                'parameter': parameter, 'semantic_weight': weight,
                                'smoothing_radius': smoothing, 'threshold': float(threshold), 'dev': value,
                                'passes_dev_gate': passes_gate(value, baseline)}
                            search.append(candidate)
                            if best is None or value['f1'] > best['dev']['f1']:
                                best, best_model = dict(candidate), model
                            if candidate['passes_dev_gate'] and value['f1'] > best_gate['dev']['f1']:
                                best_gate, gated_model = dict(candidate), model
            selected.append(best)
            joblib.dump({'classifier': best_model, **best}, WORK/(method+'.joblib'))
            print('Dev selected', method, json.dumps(best['dev']), 'gate', best['passes_dev_gate'], flush=True)
    joblib.dump({'semantic_classifier': gated_model, 'baseline_bundle': baseline_bundle, **best_gate}, WORK/'selected.joblib')
    selection = {'primary': best_gate, 'baseline_dev': baseline, 'variants': selected,
        'elapsed_training_and_selection_seconds': time.perf_counter()-started,
        'model_sha256': sha256(WORK/'selected.joblib'),
        'variant_sha256': {r['method']: sha256(WORK/(r['method']+'.joblib')) for r in selected},
        'protocol_sha256': sha256(OUT/'protocol.json')}
    atomic_json(OUT/'dev_search.json', search); atomic_json(OUT/'selection.json', selection)
    print('FROZEN PRIMARY', json.dumps(best_gate), flush=True)


def evaluate():
    protocol = json.loads((OUT/'protocol.json').read_text())
    selection_hash = sha256(OUT/'selection.json'); selection = json.loads((OUT/'selection.json').read_text())
    assert sha256(OUT/'protocol.json') == selection['protocol_sha256']
    assert sha256(WORK/'selected.joblib') == selection['model_sha256']
    assert sha256(BASE) == protocol['baseline_model_sha256']
    for path, digest in protocol['code_sha256'].items(): assert sha256(ROOT/path) == digest
    for name, digest in selection['variant_sha256'].items(): assert sha256(WORK/(name+'.joblib')) == digest
    rows = load_rows('test'); truth = np.array([r['label'] for r in rows])
    assert not {r['group'] for r in rows} & {r['group'] for split in ['train', 'dev'] for r in load_rows(split)}
    bundle = joblib.load(WORK/'selected.joblib'); baseline_bundle = bundle['baseline_bundle']
    parts = component_scores(rows, baseline_bundle); baseline_raw = .25*parts['linear']+.75*parts['forest']
    baseline_scores = smooth_scores(rows, baseline_raw, baseline_bundle['smoothing_radius'])
    baseline = all_metrics(truth, baseline_scores, baseline_bundle['threshold'])
    vectors = embeddings('test', rows, protocol['encoder_weights_sha256']+sha256(ROOT/'.runtime/research-decision-model/test.jsonl'))
    matrices = {name: context_features(rows, vectors, *args) for name, args in FEATURES.items()}
    outputs = []
    for chosen in selection['variants']:
        model = joblib.load(WORK/(chosen['method']+'.joblib'))['classifier']
        raw = model.predict_proba(matrices[chosen['feature']])[:, 1]
        scores = smooth_scores(rows, chosen['semantic_weight']*raw+(1-chosen['semantic_weight'])*baseline_raw, chosen['smoothing_radius'])
        outputs.append({**chosen, 'test': all_metrics(truth, scores, chosen['threshold'])})
    primary = selection['primary']
    if primary['method'] == 'installed_baseline':
        scores = baseline_scores
    else:
        raw = bundle['semantic_classifier'].predict_proba(matrices[primary['feature']])[:, 1]
        scores = smooth_scores(rows, primary['semantic_weight']*raw+(1-primary['semantic_weight'])*baseline_raw, primary['smoothing_radius'])
    result = {'selection': primary, 'baseline_test': baseline, 'test': all_metrics(truth, scores, primary['threshold']),
        'test_per_group': breakdown(rows, scores, primary['threshold'], 'group'),
        'test_per_meeting': breakdown(rows, scores, primary['threshold'], 'meeting'), 'variants': outputs,
        'selection_sha256_before_test_access': selection_hash,
        'status': 'Previously examined oracle-act cohort; no fresh final or recording-level accuracy claim'}
    np.savez(WORK/'historical_predictions.npz', truth=truth, scores=scores, baseline_scores=baseline_scores)
    atomic_json(OUT/'summary.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--evaluate', action='store_true')
    evaluate() if parser.parse_args().evaluate else train()
