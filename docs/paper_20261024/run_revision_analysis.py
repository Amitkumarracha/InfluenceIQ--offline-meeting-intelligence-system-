#!/usr/bin/env python3
"""Controlled exploratory diagnostics on preserved GAP features; no app changes.

Prepare the protocol before fitting, then run exactly the declared comparison:
  .venv/bin/python docs/paper_20261024/run_revision_analysis.py --prepare
  .venv/bin/python docs/paper_20261024/run_revision_analysis.py --run
The corpus has already informed development. Cross-validation is not a fresh test.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path
import sys

import numpy as np
from scipy.stats import rankdata
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import sklearn

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[1]
OUT = FOLDER / "analysis"
SOURCE = ROOT / "outputs/training/xgb_influence_20261024_v2/feature_rows.json"
PARTICIPATION = ["duration", "words", "utterances", "mean_words", "early_words", "late_words"]
CONTRIBUTION = ["influence_"+k for k in ["proposal", "evidence", "objection", "revision", "decision", "interaction", "slide_grounding"]]
FAMILIES = {"participation": PARTICIPATION, "contribution": CONTRIBUTION,
            "combined": PARTICIPATION+CONTRIBUTION}
WEIGHTS = np.array([.15, .20, .15, .20, .15, .05, .10])
ALPHAS = [.1, 1., 10., 100.]
SEED = 20261024


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")


def write_csv(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def evaluate(groups, target, prediction):
    per_meeting = []
    for group in sorted(set(groups), key=int):
        indices = np.flatnonzero(groups == group)
        y, p = target[indices], prediction[indices]
        pairs = [(i,j) for i,j in itertools.combinations(range(len(indices)),2) if y[i] != y[j]]
        assert pairs, "Report all-reference-tied groups explicitly rather than removing them"
        values = [.5 if p[i] == p[j] else float((p[i]-p[j])*(y[i]-y[j]) > 0) for i,j in pairs]
        per_meeting.append({"meeting_id":str(group), "participants":len(indices), "comparable_pairs":len(pairs),
                            "pairwise_accuracy":float(np.mean(values)),
                            "predicted_tied_pairs":int(sum(p[i] == p[j] for i,j in pairs)),
                            "constant_prediction":bool(np.ptp(p) == 0),
                            "top_set_correct":bool(set(np.flatnonzero(p == p.max())) == set(np.flatnonzero(y == y.max())))})
    return {"pairwise_accuracy":float(np.mean([r["pairwise_accuracy"] for r in per_meeting])),
            "top_set_accuracy":float(np.mean([r["top_set_correct"] for r in per_meeting])),
            "constant_meetings":sum(r["constant_prediction"] for r in per_meeting),
            "comparable_pairs":sum(r["comparable_pairs"] for r in per_meeting), "per_meeting":per_meeting}


def self_check():
    groups = np.array(["1","1","2","2","2"])
    y = np.array([0.,1.,0.,.5,1.])
    perfect = evaluate(groups,y,y)
    reverse = evaluate(groups,y,-y)
    tied = evaluate(groups,y,np.zeros_like(y))
    assert perfect["pairwise_accuracy"] == perfect["top_set_accuracy"] == 1
    assert reverse["pairwise_accuracy"] == 0 and tied["pairwise_accuracy"] == .5
    assert tied["constant_meetings"] == 2 and tied["top_set_accuracy"] == 0
    json.dumps({"perfect":perfect,"reverse":reverse,"tied":tied},allow_nan=False)
    # Reference ties are excluded; an all-tied prediction must not win top-set.
    assert evaluate(np.array(["1"]*3),np.array([0.,1.,1.]),np.zeros(3))["comparable_pairs"] == 2


def prepare():
    if OUT.exists():
        raise SystemExit("Refusing to overwrite the existing protocol/analysis directory")
    OUT.mkdir()
    rows = json.loads(SOURCE.read_text())
    assert len(rows) == 84 and len({r["meeting_id"] for r in rows}) == 28
    derived = [{"meeting_id":r["meeting_id"], "participant":r["participant"], "aii":r["aii"],
                "target":r["target"], "features":{k:r["full"][k] for k in FAMILIES["combined"]}} for r in rows]
    for group in {r["meeting_id"] for r in derived}:
        current=[r for r in derived if r["meeting_id"] == group]
        target=(rankdata([-r["aii"] for r in current])-1)/(len(current)-1)
        for row,value in zip(current,target):
            row["target"]=float(value)
    save(OUT/"features.json",derived)
    groups = np.array([r["meeting_id"] for r in rows])
    folds = []
    for number,(train,test) in enumerate(GroupKFold(n_splits=7).split(np.zeros(len(rows)),groups=groups),1):
        inner = []
        for fit,dev in GroupKFold(n_splits=3).split(np.zeros(len(train)),groups=groups[train]):
            inner.append({"fit_groups":sorted(set(groups[train][fit]),key=int),
                          "development_groups":sorted(set(groups[train][dev]),key=int)})
        folds.append({"fold":number,"train_groups":sorted(set(groups[train]),key=int),
                      "evaluation_groups":sorted(set(groups[test]),key=int),"inner_folds":inner})
    protocol = {"status":"Exploratory, review-motivated analysis; all corpus groups previously available to development",
                "purpose":"Isolate participation and seven decision-linked features using an identical small model family",
                "features_source":str(SOURCE.relative_to(ROOT)),"features_source_sha256":digest(SOURCE),
                "derived_features_sha256":digest(OUT/"features.json"), "script_sha256":digest(Path(__file__)),
                "feature_families":FAMILIES,"alphas":ALPHAS,"estimator":"Training-fold StandardScaler then Ridge",
                "target":"Average-tie rank of negative AII, minus one, divided by participants minus one; recomputed from AII, not imported XGBoost dense labels",
                "outer_folds":folds,"primary_contrast":"combined minus participation",
                "selection":"Highest pooled inner out-of-fold meeting-macro pairwise accuracy; first alpha wins ties",
                "scoring":"Reference ties excluded; exact predicted ties half-credit; equal meeting weights",
                "baseline_methods":["word_count","speaking_duration","constant_ties","prototype_fixed_weights"],
                "bootstrap":{"unit":"paired meeting","resamples":10000,"seed":SEED,
                             "interpretation":"Descriptive conditional intervals; overlapping CV training sets and prior corpus reuse limit inference"},
                "weight_sensitivity":"Seven fixed-weight feature deletions, no renormalization and no refitting",
                "role_diagnostic":"Fixed keyword defaults on all reference utterances; Proposal vs proposal and Agreement vs agreement only",
                "sklearn":sklearn.__version__,"seed":SEED,"model_epochs":0,
                "installed_in_application":False,"fresh_test":False}
    save(OUT/"protocol.json",protocol)
    print("Protocol and inputs frozen before fitting:",OUT)


def role_diagnostic():
    sys.path.insert(0,str(ROOT))
    from src.meeting.events import KeywordEventExtractor
    from scripts.benchmark_gap_influence import seconds
    utterances = [json.loads(line) for line in (ROOT/".runtime/research-influence-gap/utterances.jsonl").read_text().splitlines()]
    gold = [{s.strip() for s in row["meta"]["Decision"].split(",")} if isinstance(row["meta"]["Decision"],str) else set() for row in utterances]
    segments = [{"segment_id":i,"speaker":r["speaker"],"start":seconds(r["timestamp"]),
                 "end":seconds(r["meta"]["End"]),"text":r["text"].strip('"')} for i,r in enumerate(utterances)]
    events = KeywordEventExtractor().extract(segments,"GAP_fixed_rule_diagnostic")
    predicted = {event.source_segment_id:event.event_type for event in events.events}
    output=[]
    for reference,event_type in [("Proposal","proposal"),("Agreement","agreement")]:
        y=np.array([reference in labels for labels in gold])
        p=np.array([predicted.get(i) == event_type for i in range(len(utterances))])
        tp=int(np.sum(y&p)); fp=int(np.sum(~y&p)); fn=int(np.sum(y&~p))
        precision=tp/(tp+fp) if tp+fp else 0.
        recall=tp/(tp+fn) if tp+fn else 0.
        f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.
        output.append({"reference_role":reference,"event_type":event_type,"reference_positive":int(y.sum()),
                       "predicted_positive":int(p.sum()),"true_positive":tp,"false_positive":fp,
                       "false_negative":fn,"precision":precision,"recall":recall,"f1":f1})
    return {"scope":"Corpus-wide descriptive diagnostic; manual role annotations are not contribution/outcome links",
            "utterances":len(utterances),"threshold":KeywordEventExtractor().confidence_threshold,
            "rows":output,"events_source_sha256":digest(ROOT/"src/meeting/events.py")}


def run():
    if (OUT/"results.json").exists():
        raise SystemExit("Refusing to overwrite recorded analysis results")
    protocol=json.loads((OUT/"protocol.json").read_text())
    assert digest(OUT/"features.json") == protocol["derived_features_sha256"]
    assert digest(Path(__file__)) == protocol["script_sha256"]
    rows=json.loads((OUT/"features.json").read_text())
    groups=np.array([r["meeting_id"] for r in rows]); y=np.array([r["target"] for r in rows])
    x=np.array([[r["features"][k] for k in FAMILIES["combined"]] for r in rows])
    assert np.isfinite(x).all() and (x >= 0).all() and (x <= 1).all()
    for group in set(groups):
        idx=np.flatnonzero(groups == group)
        expected=(rankdata([-rows[i]["aii"] for i in idx])-1)/(len(idx)-1)
        assert np.array_equal(expected,y[idx])
    predictions={}; selections=[]
    for family,keys in FAMILIES.items():
        features=x[:,[FAMILIES["combined"].index(k) for k in keys]]
        oof=np.full(len(rows),np.nan)
        for fold in protocol["outer_folds"]:
            train=np.flatnonzero(np.isin(groups,fold["train_groups"]))
            test=np.flatnonzero(np.isin(groups,fold["evaluation_groups"]))
            assert not set(groups[train])&set(groups[test])
            candidates=[]
            for alpha in ALPHAS:
                inner_pred=np.full(len(train),np.nan)
                for inner in fold["inner_folds"]:
                    fit=np.flatnonzero(np.isin(groups[train],inner["fit_groups"]))
                    dev=np.flatnonzero(np.isin(groups[train],inner["development_groups"]))
                    assert not set(groups[train][fit])&set(groups[train][dev])
                    model=make_pipeline(StandardScaler(),Ridge(alpha=alpha))
                    model.fit(features[train][fit],y[train][fit])
                    inner_pred[dev]=model.predict(features[train][dev])
                assert np.isfinite(inner_pred).all()
                candidates.append({"alpha":alpha,"inner_pairwise_accuracy":evaluate(groups[train],y[train],inner_pred)["pairwise_accuracy"]})
            selected=max(candidates,key=lambda r:r["inner_pairwise_accuracy"])
            model=make_pipeline(StandardScaler(),Ridge(alpha=selected["alpha"]))
            model.fit(features[train],y[train]); oof[test]=model.predict(features[test])
            selections.append({"family":family,"outer_fold":fold["fold"],"candidates":candidates,"selected_alpha":selected["alpha"]})
        assert np.isfinite(oof).all()
        predictions[family]=oof
    predictions.update(word_count=x[:,1],speaking_duration=x[:,0],constant_ties=np.zeros(len(rows)),
                       prototype_fixed_weights=np.round(x[:,6:]@WEIGHTS,6))
    scores={name:evaluate(groups,y,p) for name,p in predictions.items()}
    rng=np.random.default_rng(SEED); n=28
    resamples=rng.integers(0,n,size=(10000,n))
    for result in scores.values():
        values=np.array([r["pairwise_accuracy"] for r in result["per_meeting"]])
        result["descriptive_bootstrap_95_ci"]=np.percentile(values[resamples].mean(axis=1),[2.5,97.5]).tolist()
    contrasts={}
    for left,right in [("combined","participation"),("combined","word_count"),("contribution","participation")]:
        delta=np.array([a["pairwise_accuracy"]-b["pairwise_accuracy"] for a,b in zip(scores[left]["per_meeting"],scores[right]["per_meeting"])])
        contrasts[left+"_minus_"+right]={"difference":float(delta.mean()),
                       "descriptive_paired_bootstrap_95_ci":np.percentile(delta[resamples].mean(axis=1),[2.5,97.5]).tolist(),
                       "meetings_better":int(np.sum(delta>1e-12)),"meetings_same":int(np.sum(np.abs(delta)<=1e-12)),
                       "meetings_worse":int(np.sum(delta < -1e-12))}
    coverage=[]
    for j,key in enumerate(CONTRIBUTION):
        active=x[:,6+j] > 0
        coverage.append({"feature":key,"active_participants":int(active.sum()),
                         "active_meetings":len(set(groups[active])),"participants":84,"meetings":28})
    any_active=np.any(x[:,6:] > 0,axis=1)
    sensitivity=[]
    for j,key in enumerate(CONTRIBUTION):
        weights=WEIGHTS.copy(); weights[j]=0
        result=evaluate(groups,y,np.round(x[:,6:]@weights,6))
        sensitivity.append({"deleted_feature":key,"pairwise_accuracy":result["pairwise_accuracy"],
                            "constant_meetings":result["constant_meetings"]})
    result={"status":protocol["status"],"protocol_sha256":digest(OUT/"protocol.json"),
            "participants":84,"meetings":28,"scores":scores,"primary_contrast":contrasts["combined_minus_participation"],
            "contrasts":contrasts,"feature_coverage":coverage,"participants_without_contribution_features":int((~any_active).sum()),
            "meetings_without_contribution_features":len(set(groups))-len(set(groups[any_active])),
            "fixed_weight_deletions":sensitivity,"role_diagnostic":role_diagnostic(),
            "limitations":["Previously inspected corpus; exploratory only, not fresh independent confirmation.",
                           "AII is outcome alignment, not annotated individual contribution.",
                           "CV training sets overlap; intervals are descriptive conditional on these predictions.",
                           "Reference transcripts/speakers; no slides or complete audio pipeline evaluation."]}
    save(OUT/"results.json",result); save(OUT/"selections.json",selections)
    pred_rows=[{"meeting_id":r["meeting_id"],"participant":r["participant"],"target":r["target"],
                **{name:float(p[i]) for name,p in predictions.items()}} for i,r in enumerate(rows)]
    write_csv(OUT/"predictions.csv",pred_rows); write_csv(OUT/"feature_coverage.csv",coverage)
    write_csv(OUT/"per_meeting.csv",[{"method":name,**r} for name,result in scores.items() for r in result["per_meeting"]])
    print(json.dumps({"scores":{k:v["pairwise_accuracy"] for k,v in scores.items()},
                      "primary_contrast":result["primary_contrast"],"coverage":coverage},indent=2))


if __name__ == "__main__":
    self_check()
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare",action="store_true"); mode.add_argument("--run",action="store_true")
    args=parser.parse_args()
    (prepare if args.prepare else run)()
