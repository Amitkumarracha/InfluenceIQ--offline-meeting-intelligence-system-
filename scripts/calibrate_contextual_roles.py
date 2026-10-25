"""Choose role thresholds from development scores before any historical scoring."""
import argparse
import json
from pathlib import Path
import shutil
import sys

import numpy as np
from sklearn.metrics import precision_recall_curve

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.train_contextual_model import load_data, save, sha


def calibrate(labels, scores):
    if labels.shape != scores.shape or not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
        raise ValueError('Finite development probabilities matching reference labels are required')
    values = []
    for column in range(labels.shape[1]):
        if not labels[:, column].any():
            values.append({'threshold': 1., 'precision': 0., 'recall': 0., 'f1': 0.})
            continue
        precision, recall, thresholds = precision_recall_curve(labels[:, column], scores[:, column])
        f1 = 2*precision[:-1]*recall[:-1]/np.maximum(precision[:-1]+recall[:-1], 1e-12)
        best = max(range(len(thresholds)), key=lambda i: (f1[i], precision[i], thresholds[i]))
        values.append({'threshold': float(thresholds[best]), 'precision': float(precision[best]),
                       'recall': float(recall[best]), 'f1': float(f1[best])})
    return {'thresholds': [v['threshold'] for v in values], 'per_label': values,
            'macro_f1': float(np.mean([v['f1'] for v in values]))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    root = args.output_dir
    if any((root/name).exists() for name in ['historical_evaluation.json', 'historical_scores.npy', 'calibration.json']):
        raise ValueError('Thresholds can only be selected once before historical scoring')
    protocol = json.loads((root/'protocol.json').read_text())
    selection = json.loads((root/'selection.json').read_text())
    history = json.loads((root/'history.json').read_text())
    if protocol['task'] != 'roles' or len(history) != protocol['epochs']:
        raise ValueError('A completed role training run is required')
    if sha(root/'model/model.safetensors') != selection['model_sha256']:
        raise ValueError('Saved model changed')
    for path, expected in protocol['input_sha256'].items():
        if sha(Path(path)) != expected:
            raise ValueError('Frozen role data changed')
    _, labels, paths = load_data('roles', 'dev')
    development = calibrate(labels, np.load(root/'dev_scores.npy'))
    original_sha = sha(root/'selection.json')
    shutil.copyfile(root/'selection.json', root/'coarse_grid_selection.json')
    save(root/'selection.json', {**selection, 'development': development,
                                'threshold_selection': 'Exact development precision-recall curve; checkpoint unchanged'})
    save(root/'calibration.json', {'rule': 'Maximum per-role development F1; ties use precision then threshold',
        'limits': 'Checkpoint selection used the original coarse threshold grid. No historical labels or scores accessed.',
        'original_selection_sha256': original_sha, 'source_sha256': sha(Path(__file__)),
        'development_sources': {str(path): sha(path) for path in paths}, 'development': development})
    print(json.dumps(development, indent=2))


if __name__ == '__main__':
    main()
