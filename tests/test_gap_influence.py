"""Synthetic contracts, not GAP benchmark measurements."""
import json

import numpy as np
from scipy.sparse import csr_matrix

from scripts.benchmark_gap_influence import records, split_groups, fit_model, predict, score


def test_split_is_fixed_and_keeps_all_teams_separate():
    groups = [str(i) for i in range(1, 29)]
    result = split_groups(groups)
    assert result == split_groups(list(reversed(groups)))
    assert list(map(len, result.values())) == [16, 6, 6]
    assert set(result['train']).isdisjoint(result['test'])
    assert set(result['train']).isdisjoint(result['development'])
    assert set(result['development']).isdisjoint(result['test'])


def test_outcomes_and_manual_metadata_cannot_change_features(tmp_path):
    speakers = {speaker: {'Group Number': '1', 'AII': aii, 'Ind_Lead': 5}
                for speaker, aii in [('1.A', 10), ('1.B', 30)]}
    utterances = [{'speaker': speaker, 'timestamp': f'00:{i*10:02d}.0',
                   'meta': {'End': f'00:{i*10+5:02d}.0', 'Decision': 999, 'Sentiment': 999},
                   'text': text} for i, (speaker, text) in enumerate([
                       ('1.A', 'We should use the rope because it is useful'),
                       ('1.B', 'I agree we will use the rope')])]
    path = tmp_path/'speakers.json'
    path.write_text(json.dumps(speakers))
    text_path = tmp_path/'utterances.jsonl'
    text_path.write_text('\n'.join(json.dumps(row) for row in utterances))
    first = records(tmp_path, ['1'])
    assert first[0]['target'] > first[1]['target']  # Lower AII means higher influence.
    for speaker in speakers.values():
        speaker['AII'] = 50-speaker['AII']
        speaker['Ind_Lead'] = -999
    for row in utterances:
        row['meta']['Decision'] = -999
        row['meta']['Sentiment'] = -999
    path.write_text(json.dumps(speakers))
    text_path.write_text('\n'.join(json.dumps(row) for row in utterances))
    second = records(tmp_path, ['1'])
    assert second[0]['target'] < second[1]['target']
    assert all(np.array_equal(left['vector'], right['vector']) for left, right in zip(first, second))
    assert [r['text'] for r in first] == [r['text'] for r in second]


def test_pairwise_model_and_metrics_keep_influence_direction():
    rows = [{'meeting_id': meeting, 'target': value} for meeting in ['a', 'b'] for value in [0., 1.]]
    x = csr_matrix(np.array([[0.], [1.], [0.], [1.]]))
    model = fit_model('pairwise_logistic', 1, x, rows)
    predictions = predict(model, x)
    assert score(rows, predictions)['meeting_macro_pairwise_accuracy'] == 1
    assert score(rows, -predictions)['meeting_macro_pairwise_accuracy'] == 0
