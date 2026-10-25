#!/usr/bin/env python3
"""Replay the frozen controlled analysis from derived features, without corpora.

Usage: python reproduce_controlled.py --output-dir /tmp/influenceiq-replay
Requires numpy, scipy and scikit-learn (recorded version: 1.6.1).
Writes only a fresh output directory; does not overwrite research results.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FOLDER=Path(__file__).resolve().parent


def main(output):
    if output.exists():
        raise SystemExit("Choose a new replay output directory")
    spec=importlib.util.spec_from_file_location("frozen_analysis",FOLDER/"run_revision_analysis.py")
    analysis=importlib.util.module_from_spec(spec);spec.loader.exec_module(analysis)
    analysis.self_check()
    protocol=json.loads((FOLDER/"analysis/protocol.json").read_text())
    assert hashlib.sha256((FOLDER/"analysis/features.json").read_bytes()).hexdigest()==protocol["derived_features_sha256"]
    rows=json.loads((FOLDER/"analysis/features.json").read_text())
    expected=json.loads((FOLDER/"analysis/results.json").read_text())
    groups=np.array([r["meeting_id"] for r in rows]);y=np.array([r["target"] for r in rows])
    scores={}; choices=[]
    for family,keys in protocol["feature_families"].items():
        x=np.array([[r["features"][k] for k in keys] for r in rows])
        prediction=np.full(len(rows),np.nan)
        for fold in protocol["outer_folds"]:
            train=np.flatnonzero(np.isin(groups,fold["train_groups"]))
            test=np.flatnonzero(np.isin(groups,fold["evaluation_groups"]))
            assert not set(groups[train])&set(groups[test])
            candidates=[]
            for alpha in protocol["alphas"]:
                inner=np.full(len(train),np.nan)
                for split in fold["inner_folds"]:
                    fit=np.flatnonzero(np.isin(groups[train],split["fit_groups"]))
                    dev=np.flatnonzero(np.isin(groups[train],split["development_groups"]))
                    model=make_pipeline(StandardScaler(),Ridge(alpha=alpha))
                    model.fit(x[train][fit],y[train][fit]);inner[dev]=model.predict(x[train][dev])
                assert np.isfinite(inner).all()
                candidates.append((alpha,analysis.evaluate(groups[train],y[train],inner)["pairwise_accuracy"]))
            alpha=max(candidates,key=lambda value:value[1])[0]
            model=make_pipeline(StandardScaler(),Ridge(alpha=alpha))
            model.fit(x[train],y[train]);prediction[test]=model.predict(x[test])
            choices.append({"family":family,"outer_fold":fold["fold"],"selected_alpha":alpha})
        assert np.isfinite(prediction).all()
        score=analysis.evaluate(groups,y,prediction)
        assert np.isclose(score["pairwise_accuracy"],expected["scores"][family]["pairwise_accuracy"],atol=1e-12)
        assert all(a==b for a,b in zip(score["per_meeting"],expected["scores"][family]["per_meeting"]))
        scores[family]=score
    original=json.loads((FOLDER/"analysis/selections.json").read_text())
    assert choices==[{k:r[k] for k in ["family","outer_fold","selected_alpha"]} for r in original]
    output.mkdir(parents=True)
    (output/"replay_results.json").write_text(json.dumps({"status":"Matched frozen scores, per-meeting observations and selected parameters",
        "scores":scores,"choices":choices,"scope":"Controlled ridge analysis only; role extraction requires original corpus/code"},indent=2)+"\n")
    print("Replay matched all three feature families and 21 selected outer models.")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output-dir",type=Path,required=True)
    main(parser.parse_args().output_dir)
