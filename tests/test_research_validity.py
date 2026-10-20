import pytest

from scripts.audit_research_validity import feature_activity, scalar_residual


def test_audit_distinguishes_inactive_features_from_score_changes():
    result = feature_activity([
        {'raw_features': {'decision': 2, 'evidence': 0}},
        {'raw_features': {'decision': 1, 'evidence': 0}},
        {'raw_features': {'decision': 0, 'evidence': 0}}])
    assert result['evidence'] == {'nonzero_clusters': 0, 'raw_total': 0}
    assert result['decision'] == {'nonzero_clusters': 2, 'raw_total': 3}
    control = {'A': .15, 'B': .075, 'C': 0}
    scaled = {'A': .1875, 'B': .09375, 'C': 0}
    assert scalar_residual(scaled, control, 1 / .8) == 0
    assert scalar_residual(control, {'A': 1, 'B': .5, 'C': 0}, .15) == 0


def test_incomparable_audit_inputs_fail_instead_of_silently_matching():
    with pytest.raises(ValueError):
        scalar_residual({'A': .1}, {'B': .1}, 1)
    with pytest.raises(ValueError):
        scalar_residual({}, {}, 1)
