"""Synthetic contract tests only; fixtures are not a research dataset."""
import json
import numpy as np
import pytest
from scripts.train_influence_weights import KEYS, load_rows, train


def manifest(tmp_path):
    rows = []
    target = [.05, .30, .05, .15, .20, .05, .20]
    for meeting, split in [('train-a', 'train'), ('train-b', 'train'), ('valid', 'validation'), ('heldout', 'test')]:
        for i, key in enumerate(KEYS):
            rows.append({'meeting_id': meeting, 'participant': key, 'split': split,
                         'label_source': 'human', 'human_score': target[i],
                         'features': {name: int(name == key) for name in KEYS}})
    path = tmp_path / 'synthetic-unit-fixture.jsonl'
    path.write_text('\n'.join(json.dumps(row) for row in rows))
    return path, rows


def test_complete_meeting_split_and_supervised_fit(tmp_path):
    path, _ = manifest(tmp_path)
    result = train(load_rows(path))
    assert np.isclose(sum(result['weights'].values()), 1)
    assert all(weight >= 0 for weight in result['weights'].values())
    assert result['metrics']['test']['learned']['participant_mse'] < 1e-8
    assert result['metrics']['test']['prototype_weights']['participant_mse'] > 0.001
    assert not result['installed_in_application']
    assert len(result['metrics']['test']['ablations_zero_feature_no_renormalization']) == 7


@pytest.mark.parametrize('mutation', ['split_leakage', 'machine_labels', 'bad_score', 'duplicate', 'nan_features'])
def test_invalid_annotations_are_rejected(tmp_path, mutation):
    path, rows = manifest(tmp_path)
    if mutation == 'split_leakage':
        rows[0]['split'] = 'test'
    elif mutation == 'machine_labels':
        rows[0]['label_source'] = 'pipeline'
    elif mutation == 'bad_score':
        rows[0]['human_score'] = 1.2
    elif mutation == 'nan_features':
        rows[0]['features']['proposal'] = float('nan')
    else:
        rows.append(rows[0])
    path.write_text('\n'.join(json.dumps(row) for row in rows))
    with pytest.raises(ValueError):
        load_rows(path)
