"""Development-only continuity selection; historical scoring is a separate step."""
import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.compare_discussion_models import thresholds
from scripts.improve_decision_discussions import load_rows, sha256, smooth_scores, breakdown
from scripts.optimize_discussion_quality import all_metrics, passes_gate
from src.meeting.discussions import component_scores
from src.meeting.discussion_sequence import learn_rates, sequence_scores
from src.utils.cache import atomic_json

OUT = ROOT/'professor_guidelines/evaluation/sequence_quality'
WORK = ROOT/'.runtime/research-sequence-quality'
BASE = ROOT/'.runtime/research-discussion-pipeline/model.joblib'


def train():
    OUT.mkdir(parents=True, exist_ok=True); WORK.mkdir(parents=True, exist_ok=True)
    protocol = {'task': 'Same AMI reference-act discussion membership',
        'linear_weights': [0., .25, .5, .75, 1.], 'speed': [.1, .3, 1., 3.], 'power': [.5, 1., 2.],
        'continuity': 'Two-state continuous-time transitions estimated only from training labels and elapsed seconds',
        'selection': 'Dev F1 with the same five-metric non-regression gate; otherwise retain installed baseline',
        'thresholds': 'Same 13 development-score quantiles plus 0.5',
        'baseline_sha256': sha256(BASE), 'train_sha256': sha256(ROOT/'.runtime/research-decision-model/train.jsonl'),
        'dev_sha256': sha256(ROOT/'.runtime/research-decision-model/dev.jsonl'),
        'code_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in [Path(__file__),ROOT/'src/meeting/discussion_sequence.py']},
        'historical_regression_gate': ['f1', 'balanced_accuracy', 'average_precision'],
        'limits': ['Offline forward/backward access; no causal streaming claim.',
            'Classifier emissions are discriminative scores, not independent generative observations; output is uncalibrated.',
            'Repeated historical cohort, oracle text/act boundaries, only three independent test series.']}
    atomic_json(OUT/'protocol.json', protocol)
    rates = learn_rates(load_rows('train'))
    rows = load_rows('dev'); truth = np.array([r['label'] for r in rows])
    base = joblib.load(BASE); parts = component_scores(rows, base)
    old_scores = smooth_scores(rows, .25*parts['linear']+.75*parts['forest'], 5)
    baseline = all_metrics(truth, old_scores, base['threshold'])
    best = {'method':'installed_baseline', 'dev':baseline,'linear_weight':.25,
            'threshold':base['threshold'], 'smoothing_radius':5}
    search = []
    for weight in protocol['linear_weights']:
        for speed in protocol['speed']:
            for power in protocol['power']:
                scores = sequence_scores(rows, weight*parts['linear']+(1-weight)*parts['forest'], rates,speed,power)
                for threshold in thresholds(scores):
                    value = all_metrics(truth, scores, threshold)
                    candidate = {'method':'continuous_time_discussion','linear_weight':weight,'speed':speed,
                        'power':power,'threshold':float(threshold),'dev':value,
                        'passes_dev_gate':passes_gate(value,baseline)}
                    search.append(candidate)
                    if candidate['passes_dev_gate'] and value['f1'] > best['dev']['f1']:
                        best = dict(candidate)
    joblib.dump({'baseline_bundle':base,'rates':rates,**best}, WORK/'selected.joblib')
    atomic_json(OUT/'selection.json',{'primary':best,'baseline_dev':baseline,'rates':rates,
        'model_sha256':sha256(WORK/'selected.joblib'),'protocol_sha256':sha256(OUT/'protocol.json')})
    atomic_json(OUT/'dev_search.json',search)
    print('FROZEN',json.dumps(best),flush=True)


def evaluate():
    protocol=json.loads((OUT/'protocol.json').read_text()); selection=json.loads((OUT/'selection.json').read_text())
    digest=sha256(OUT/'selection.json')
    assert sha256(OUT/'protocol.json')==selection['protocol_sha256']
    assert sha256(WORK/'selected.joblib')==selection['model_sha256']
    assert sha256(BASE)==protocol['baseline_sha256']
    for path,expected in protocol['code_sha256'].items():assert sha256(ROOT/path)==expected
    rows=load_rows('test');truth=np.array([r['label'] for r in rows])
    bundle=joblib.load(WORK/'selected.joblib');base=bundle['baseline_bundle'];parts=component_scores(rows,base)
    old_scores=smooth_scores(rows,.25*parts['linear']+.75*parts['forest'],5)
    chosen=selection['primary']
    scores=old_scores if chosen['method']=='installed_baseline' else sequence_scores(rows,
        chosen['linear_weight']*parts['linear']+(1-chosen['linear_weight'])*parts['forest'],
        selection['rates'],chosen['speed'],chosen['power'])
    result={'selection':chosen,'selection_sha256_before_test_access':digest,
        'baseline_test':all_metrics(truth,old_scores,base['threshold']),
        'test':all_metrics(truth,scores,chosen['threshold']),
        'test_per_group':breakdown(rows,scores,chosen['threshold'],'group'),
        'test_per_meeting':breakdown(rows,scores,chosen['threshold'],'meeting'),
        'status':'Exploratory historical oracle-act evaluation'}
    np.savez(WORK/'historical_predictions.npz',truth=truth,scores=scores)
    atomic_json(OUT/'summary.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--evaluate',action='store_true')
    evaluate() if parser.parse_args().evaluate else train()
