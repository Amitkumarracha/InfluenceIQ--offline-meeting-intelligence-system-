"""Training-only NB calibration and fixed, development-selected three-way mixtures."""
import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.naive_bayes import ComplementNB

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.compare_discussion_models import matrices, calibration_folds, thresholds
from scripts.improve_decision_discussions import load_rows, sha256, smooth_scores, breakdown
from scripts.optimize_discussion_quality import all_metrics, passes_gate
from src.meeting.discussion_ensemble import ProbabilityEnsemble
from src.utils.cache import atomic_json

OUT=ROOT/'professor_guidelines/evaluation/ensemble_quality'
WORK=ROOT/'.runtime/research-ensemble-quality'
BASE=ROOT/'.runtime/research-discussion-pipeline/model.joblib'


def train():
    OUT.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
    protocol={'alpha':[1.,10.], 'nb_weights':[0.,.1,.25,.5], 'forest_share_of_remainder':[.5,.75,1.],
        'smoothing':[0,5,15], 'thresholds':'13 fixed dev-score quantiles plus 0.5',
        'calibration':'Sigmoid, three project-separated training folds; no development labels in calibration',
        'calibration_limit':'Vocabulary/IDF fitted on all training acts; shared across inner calibration folds',
        'selection':'Max dev F1 without any regression on accuracy/precision/recall/F1/AP; otherwise baseline',
        'historical_regression_gate':['f1','balanced_accuracy','average_precision'],
        'test_access':'Separate evaluation invocation after freezing selection and models',
        'baseline_sha256':sha256(BASE),
        'train_sha256':sha256(ROOT/'.runtime/research-decision-model/train.jsonl'),
        'dev_sha256':sha256(ROOT/'.runtime/research-decision-model/dev.jsonl'),
        'code_sha256':{str(p.relative_to(ROOT)):sha256(p) for p in [Path(__file__),ROOT/'src/meeting/discussion_ensemble.py']},
        'scope':'Further exploratory oracle-act optimization; no new final cohort or end-to-end accuracy claim'}
    atomic_json(OUT/'protocol.json',protocol)
    base=joblib.load(BASE);train_rows=load_rows('train');rows=load_rows('dev')
    x_train=matrices(train_rows,base['vectorizers'])['context_40'];x_dev=matrices(rows,base['vectorizers'])['context_40']
    truth=np.array([r['label'] for r in rows]);train_y=np.array([r['label'] for r in train_rows])
    forest=base['classifiers']['forest'].predict_proba(x_dev)[:,1]
    linear=base['classifiers']['linear'].predict_proba(x_dev)[:,1]
    baseline=all_metrics(truth,smooth_scores(rows,.75*forest+.25*linear,5),base['threshold'])
    best={'method':'installed_baseline','dev':baseline,'forest_weight':.75,'linear_weight':.25,'nb_weight':0.,
          'threshold':base['threshold'],'smoothing_radius':5}
    best_model=None;search=[]
    for alpha in protocol['alpha']:
        nb=CalibratedClassifierCV(ComplementNB(alpha=alpha),method='sigmoid',
             cv=calibration_folds(train_rows),ensemble=False,n_jobs=1).fit(x_train,train_y)
        raw_nb=nb.predict_proba(x_dev)[:,1]
        for nw in protocol['nb_weights']:
            for share in protocol['forest_share_of_remainder']:
                fw=(1-nw)*share;lw=1-nw-fw
                raw=fw*forest+lw*linear+nw*raw_nb
                for radius in protocol['smoothing']:
                    scores=smooth_scores(rows,raw,radius)
                    for threshold in thresholds(scores):
                        value=all_metrics(truth,scores,threshold)
                        row={'method':'calibrated_three_way','alpha':alpha,'forest_weight':fw,'linear_weight':lw,
                             'nb_weight':nw,'threshold':float(threshold),'smoothing_radius':radius,
                             'dev':value,'passes_dev_gate':passes_gate(value,baseline)}
                        search.append(row)
                        if row['passes_dev_gate'] and value['f1']>best['dev']['f1']:
                            best=dict(row);best_model=nb
        print('Completed calibration alpha',alpha,flush=True)
    classifiers=dict(base['classifiers'])
    if best_model is not None:
        remainder=1-best['linear_weight']
        classifiers['forest']=ProbabilityEnsemble([classifiers['forest'],best_model],
            [best['forest_weight']/remainder,best['nb_weight']/remainder])
    packaged={**base,**best,'classifiers':classifiers}
    joblib.dump(packaged,WORK/'selected.joblib')
    atomic_json(OUT/'dev_search.json',search)
    atomic_json(OUT/'selection.json',{'primary':best,'baseline_dev':baseline,
        'model_sha256':sha256(WORK/'selected.joblib'),'protocol_sha256':sha256(OUT/'protocol.json')})
    print('FROZEN',json.dumps(best),flush=True)


def evaluate():
    protocol=json.loads((OUT/'protocol.json').read_text());selection=json.loads((OUT/'selection.json').read_text())
    selection_hash=sha256(OUT/'selection.json')
    assert sha256(BASE)==protocol['baseline_sha256']
    assert sha256(WORK/'selected.joblib')==selection['model_sha256']
    assert sha256(OUT/'protocol.json')==selection['protocol_sha256']
    for path,digest in protocol['code_sha256'].items():assert sha256(ROOT/path)==digest
    rows=load_rows('test');truth=np.array([r['label'] for r in rows]);base=joblib.load(BASE)
    matrix=matrices(rows,base['vectorizers'])['context_40']
    chosen=joblib.load(WORK/'selected.joblib');p=selection['primary']
    def scores(bundle):
        raw=bundle['linear_weight']*bundle['classifiers']['linear'].predict_proba(matrix)[:,1]
        raw+=(1-bundle['linear_weight'])*bundle['classifiers']['forest'].predict_proba(matrix)[:,1]
        return smooth_scores(rows,raw,bundle['smoothing_radius'])
    values=scores(chosen);reference=scores(base)
    atomic_json(OUT/'summary.json',{'selection':p,'selection_sha256_before_test_access':selection_hash,
        'baseline_test':all_metrics(truth,reference,base['threshold']),
        'test':all_metrics(truth,values,p['threshold']),
        'test_per_group':breakdown(rows,values,p['threshold'],'group'),
        'test_per_meeting':breakdown(rows,values,p['threshold'],'meeting'),
        'status':'Exploratory reused historical oracle-act cohort'})
    np.savez(WORK/'historical_predictions.npz',truth=truth,scores=values)
    print(json.dumps(json.loads((OUT/'summary.json').read_text()),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evaluate',action='store_true')
    evaluate() if p.parse_args().evaluate else train()
