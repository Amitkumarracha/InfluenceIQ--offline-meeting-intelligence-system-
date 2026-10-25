"""Synthetic contract tests for blind annotation preparation."""
import csv
import json

import pytest

from scripts.prepare_influence_annotations import RAW_KEYS, prepare
from scripts.train_influence_weights import load_rows


def source(tmp_path):
    path = tmp_path / 'influence.json'
    path.write_text(json.dumps({'meeting_id': 'm', 'participants': [
        {'participant': participant, 'influence_score': .99,
         'raw_features': {key: int(key == 'decision_contribution') for key in RAW_KEYS}}
        for participant in ['A', 'B']]}))
    return path


def test_preparation_keeps_ratings_blind_and_never_invents_labels(tmp_path):
    output = tmp_path / 'annotations'
    result = prepare([source(tmp_path)], output)
    assert result['influence_accuracy'] is None
    assert result['meetings'][0]['active_features'] == ['decision']
    with (output / 'blind_ratings.csv').open() as stream:
        ratings = list(csv.DictReader(stream))
    assert len(ratings) == 6
    assert all(row['score_1_to_5'] == '' for row in ratings)
    assert 'influence_score' not in ratings[0] and 'features' not in ratings[0]
    template = output / 'training_template.jsonl'
    rows = [json.loads(line) for line in template.read_text().splitlines()]
    assert all(row['human_score'] is None and row['label_source'] is None for row in rows)
    with pytest.raises(ValueError):
        load_rows(template)
    (output / 'blind_ratings.csv').write_text('completed ratings')
    with pytest.raises(FileExistsError):
        prepare([source(tmp_path)], output)
    assert (output / 'blind_ratings.csv').read_text() == 'completed ratings'


def test_invalid_features_do_not_create_an_annotation_directory(tmp_path):
    path = source(tmp_path)
    data = json.loads(path.read_text())
    data['participants'][0]['raw_features']['proposal_contribution'] = -1
    path.write_text(json.dumps(data))
    output = tmp_path / 'annotations'
    with pytest.raises(ValueError, match='nonnegative'):
        prepare([path], output)
    assert not output.exists()


def test_unknown_speakers_require_resolution_before_rating(tmp_path):
    path = source(tmp_path)
    data = json.loads(path.read_text())
    data['participants'][0]['participant'] = 'UNKNOWN'
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='known participant IDs'):
        prepare([path], tmp_path / 'annotations')
