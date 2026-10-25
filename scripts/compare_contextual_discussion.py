"""Report frozen discussion scores and paired project-bootstrap uncertainty."""
import argparse
import json
from pathlib import Path
import sys

import joblib
import numpy as np
from sklearn.metrics import confusion_matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.train_contextual_model import load_data, save, sha
from scripts.improve_decision_discussions import smooth_scores
from src.meeting.discussions import component_scores, combine_scores


def count_metrics(counts):
    tn, fp, fn, tp = counts
    return np.array([(tp+tn)/max(1, sum(counts)),
                     .5*(tp/max(1, tp+fn)+tn/max(1, tn+fp)),
                     2*tp/max(1, 2*tp+fp+fn)])


def paired_intervals(truth, baseline, candidate, groups, seed=42, repeats=10000):
    names = sorted(set(groups))
    counts = np.array([[confusion_matrix(truth[np.array(groups) == group],
        prediction[np.array(groups) == group], labels=[0, 1]).ravel()
        for group in names] for prediction in [baseline, candidate]])
    samples = np.random.default_rng(seed).integers(0, len(names), size=(repeats, len(names)))
    scores = np.array([[count_metrics(counts[method, indices].sum(axis=0)) for indices in samples]
                       for method in range(2)])
    result = {'groups': names, 'bootstrap_repeats': repeats, 'seed': seed,
              'policy': 'Resample entire project groups; pool their confusion counts; paired candidate minus baseline',
              'limits': 'Historical cohort; few independent projects give unstable uncertainty, not confirmation.'}
    for column, metric in enumerate(['accuracy', 'balanced_accuracy', 'positive_f1']):
        result[metric] = {'baseline': float(count_metrics(counts[0].sum(0))[column]),
            'candidate': float(count_metrics(counts[1].sum(0))[column]),
            'candidate_95_interval': np.quantile(scores[1, :, column], [.025, .975]).tolist(),
            'paired_difference_95_interval': np.quantile(scores[1, :, column]-scores[0, :, column], [.025, .975]).tolist()}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(); root = args.output_dir
    target = root/'paired_baseline_comparison.json'
    if target.exists() or not (root/'historical_evaluation.json').exists():
        raise ValueError('A completed historical evaluation and a new comparison output are required')
    selected = json.loads((root/'selection.json').read_text())['development']['blend']
    baseline_path = ROOT/'models/discussion/model.joblib'
    if sha(baseline_path) != json.loads((root/'baseline.json').read_text())['model_sha256']:
        raise ValueError('Baseline model changed')
    rows, labels, _ = load_data('discussion', 'test')
    bundle = joblib.load(baseline_path)
    base = combine_scores(rows, component_scores(rows, bundle), bundle['linear_weight'], bundle['smoothing_radius'])
    neural = np.load(root/'historical_scores.npy')[:, 0]
    blended = selected['neural_weight']*smooth_scores(rows, neural, selected['smoothing_radius'])+(1-selected['neural_weight'])*base
    comparison = paired_intervals(labels[:, 0], base >= bundle['threshold'], blended >= selected['threshold'], [r['group'] for r in rows])
    save(target, comparison); print(json.dumps(comparison, indent=2))


if __name__ == '__main__':
    main()
