"""Final refit after model selection; settings fixed, historical meetings excluded."""
import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.compare_discussion_models import matrices, estimator
from scripts.improve_decision_discussions import load_rows, sha256, smooth_scores, breakdown
from scripts.optimize_discussion_quality import all_metrics
from src.utils.cache import atomic_json

OUT=ROOT/'professor_guidelines/evaluation/refit_quality'
WORK=ROOT/'.runtime/research-refit-quality'
BASE=ROOT/'.runtime/research-discussion-pipeline/model.joblib'


def train():
    OUT.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
    original=joblib.load(BASE)
    rows=load_rows('train')+load_rows('dev')
    protocol={'operation':'Final refit of the already selected configuration on train+dev; no further parameter search',
        'training_meetings':35,'training_acts':len(rows),'historical_meetings':12,
        'linear_C':3.,'forest_max_depth':10,'forest_n_estimators':100,'forest_min_samples_leaf':2,
        'linear_weight':original['linear_weight'],'threshold':original['threshold'],
        'smoothing_radius':original['smoothing_radius'],
        'representation':'Unchanged original train-fitted TF-IDF vocabulary/IDF and context-40; only classifier fits change',
        'selection':'All settings inherited from prior train/dev selection; no new dev score after refit',
        'deployment_gate':['f1','balanced_accuracy','average_precision'],
        'gate_rule':'Do not install if any listed historical regression metric is below baseline; no alternative candidate search',
        'baseline_sha256':sha256(BASE),'train_sha256':sha256(ROOT/'.runtime/research-decision-model/train.jsonl'),
        'dev_sha256':sha256(ROOT/'.runtime/research-decision-model/dev.jsonl'),
        'script_sha256':sha256(Path(__file__)),
        'limits':['Training size differs from earlier 29-meeting classifier comparisons; not a matched-data superiority claim.',
                  'Previously examined historical cohort; independent final confirmation still required.',
                  'No independent development score can be claimed for a model refit on development labels.']}
    atomic_json(OUT/'protocol.json',protocol)
    x=matrices(rows,original['vectorizers'])['context_40'];y=np.array([r['label'] for r in rows])
    linear=estimator('logistic_regression',3.,None).fit(x,y)
    forest=estimator('random_forest',10,None).fit(x,y)
    bundle={**original,'classifiers':{'linear':linear,'forest':forest},'method':'refit_forest_linear_discussion_review'}
    joblib.dump(bundle,WORK/'selected.joblib')
    atomic_json(OUT/'selection.json',{'model_sha256':sha256(WORK/'selected.joblib'),
        'protocol_sha256':sha256(OUT/'protocol.json'),'training_acts':len(rows),'training_positive_acts':int(y.sum())})
    print('Frozen refit, training acts',len(rows),flush=True)


def evaluate():
    p=json.loads((OUT/'protocol.json').read_text());selection=json.loads((OUT/'selection.json').read_text())
    digest=sha256(OUT/'selection.json')
    assert sha256(OUT/'protocol.json')==selection['protocol_sha256']
    assert sha256(BASE)==p['baseline_sha256'] and sha256(Path(__file__))==p['script_sha256']
    assert sha256(WORK/'selected.joblib')==selection['model_sha256']
    rows=load_rows('test');truth=np.array([r['label'] for r in rows])
    assert not {r['group'] for r in rows}&{r['group'] for split in ['train','dev'] for r in load_rows(split)}
    baseline=joblib.load(BASE);candidate=joblib.load(WORK/'selected.joblib')
    x=matrices(rows,baseline['vectorizers'])['context_40']
    def score(bundle):
        raw=bundle['linear_weight']*bundle['classifiers']['linear'].predict_proba(x)[:,1]
        raw+=(1-bundle['linear_weight'])*bundle['classifiers']['forest'].predict_proba(x)[:,1]
        return smooth_scores(rows,raw,bundle['smoothing_radius'])
    before,after=score(baseline),score(candidate)
    base_metrics=all_metrics(truth,before,baseline['threshold'])
    candidate_metrics=all_metrics(truth,after,candidate['threshold'])
    gate=all(candidate_metrics[k]+1e-12>=base_metrics[k] for k in p['deployment_gate'])
    result={'baseline_test':base_metrics,'test':candidate_metrics,'passes_deployment_gate':gate,
        'selection_sha256_before_test_access':digest,
        'test_per_group':breakdown(rows,after,candidate['threshold'],'group'),
        'test_per_meeting':breakdown(rows,after,candidate['threshold'],'meeting'),
        'status':'Exploratory historical comparison after final train+dev refit; not independent app accuracy'}
    atomic_json(OUT/'summary.json',result);np.savez(WORK/'historical_predictions.npz',truth=truth,scores=after)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--evaluate',action='store_true')
    evaluate() if parser.parse_args().evaluate else train()
