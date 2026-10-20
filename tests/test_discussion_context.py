import numpy as np

from scripts.improve_decision_discussions import context_texts, position_features, smooth_scores
from scripts.report_discussion_improvements import paired_interval


def rows():
    # Interleaved input catches accidental context/smoothing across meetings.
    return [
        {'meeting': 'A', 'act_id': 'a2', 'start': 2., 'end': 3., 'text': 'second'},
        {'meeting': 'B', 'act_id': 'b1', 'start': 0., 'end': 1., 'text': 'private'},
        {'meeting': 'A', 'act_id': 'a1', 'start': 0., 'end': 1., 'text': 'first'},
        {'meeting': 'A', 'act_id': 'a3', 'start': 4., 'end': 5., 'text': 'third'},
    ]


def test_context_is_chronological_and_cannot_cross_meetings_or_use_labels():
    data = rows()
    expected = ['first second third', 'private', 'first second', 'second third']
    assert context_texts(data, 1) == expected
    for row in data:
        row.update(label=1, positive_word_fraction=1., context='forbidden annotation')
    assert context_texts(data, 1) == expected


def test_smoothing_handles_edges_without_zero_padding_or_other_meetings():
    scores = np.array([.6, 1., 0., .9])
    np.testing.assert_allclose(smooth_scores(rows(), scores, 1), [.5, 1., .3, .75])
    np.testing.assert_allclose(smooth_scores(rows(), scores, 15), [.5, 1., .5, .5])
    np.testing.assert_array_equal(smooth_scores(rows(), scores, 0), scores)


def test_position_uses_only_each_recordings_observed_time_span():
    data = rows()
    expected = np.array([[.4, .16, .064], [0., 0., 0.], [0., 0., 0.], [.8, .64, .512]])
    np.testing.assert_allclose(position_features(data).toarray(), expected)
    data[1]['end'] = 0.
    assert np.isfinite(position_features(data).toarray()).all()


def test_paired_uncertainty_resamples_the_same_project_groups():
    old = [{'meeting': 'ES1a', 'confusion_matrix_tn_fp_fn_tp': [2, 2, 2, 2]},
           {'meeting': 'IS2a', 'confusion_matrix_tn_fp_fn_tp': [2, 2, 2, 2]}]
    identical = [{'group': 'ES1', 'confusion_matrix_tn_fp_fn_tp': [2, 2, 2, 2]},
                 {'group': 'IS2', 'confusion_matrix_tn_fp_fn_tp': [2, 2, 2, 2]}]
    assert paired_interval(old, identical)['descriptive_f1_delta_interval'] == [0., 0.]
    improved = [{'group': 'ES1', 'confusion_matrix_tn_fp_fn_tp': [4, 0, 0, 4]},
                {'group': 'IS2', 'confusion_matrix_tn_fp_fn_tp': [4, 0, 0, 4]}]
    assert paired_interval(old, improved)['descriptive_f1_delta_interval'] == [.5, .5]
