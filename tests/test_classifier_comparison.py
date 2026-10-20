import numpy as np
import pytest
from scipy.sparse import csr_matrix

from scripts.compare_discussion_models import calibration_folds, estimator, thresholds


def test_calibration_keeps_entire_project_series_out_of_each_training_fold():
    rows = [{'group': group} for group in ['A', 'B', 'C', 'D', 'A', 'B', 'C', 'D']]
    folds = calibration_folds(rows)
    held_out = []
    for train, calibration in folds:
        assert not {rows[i]['group'] for i in train} & {rows[i]['group'] for i in calibration}
        held_out.extend(calibration)
    assert sorted(held_out) == list(range(len(rows)))


def test_threshold_candidates_cover_concentrated_scores_without_using_labels():
    scores = np.array([.000001, .000002, .000003, .000004])
    values = thresholds(scores)
    assert .5 in values
    assert len(values) <= 14
    assert sum(values < scores.max()) > 1
    np.testing.assert_array_equal(thresholds(np.ones(5)), [.5, 1.])


def test_each_classifier_supports_same_sparse_input_and_positive_class_scores():
    x = csr_matrix([[1., 0.], [0., 1.]] * 6)
    y = np.array([0, 1] * 6)
    folds = calibration_folds([{'group': str(i // 4)} for i in range(12)])
    for family, parameter in [('logistic_regression', .3), ('complement_nb', 1.),
                              ('linear_svm', .3), ('random_forest', 10)]:
        model = estimator(family, parameter, folds).fit(x, y)
        scores = model.predict_proba(x)[:, 1]
        assert scores.shape == (12,) and np.isfinite(scores).all()
        assert scores[1] > scores[0]
    with pytest.raises(ValueError):
        estimator('unknown', 1, folds)
