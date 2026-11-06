import pytest

from scripts.generate_results import confusion_metrics, pooled_der


def test_der_pools_reference_speaker_time_instead_of_averaging_excerpts():
    rows=[{'der':{'der':.1,'total_reference_duration':90}},
          {'der':{'der':.9,'total_reference_duration':10}}]
    assert pooled_der(rows)==pytest.approx(.18)
    with pytest.raises(ValueError,match='speaker-time'):
        pooled_der([{'der':{'der':.1,'total_reference_duration':0}}])


def test_imbalanced_classifier_metrics_do_not_equate_accuracy_with_positive_f1():
    baseline=confusion_metrics([8655,0,2481,0])
    assert baseline['accuracy']==pytest.approx(.7772090517241379)
    assert baseline['precision']==baseline['recall']==baseline['f1']==0
    installed=confusion_metrics([5627,3028,467,2014])
    assert installed['precision']==pytest.approx(.3994446648155494)
    assert installed['recall']==pytest.approx(.8117694478033051)
    assert installed['f1']==pytest.approx(.5354246975940449)
