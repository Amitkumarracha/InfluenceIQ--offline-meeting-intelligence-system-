import pytest

from scripts.compare_asr_quality import pooled
from scripts.report_quality_improvements import asr_release_eligible, majority_metrics


def test_pooled_error_uses_reference_counts_instead_of_mean_sample_rates():
    rows = [{'wer': dict(substitutions=1, deletions=0, insertions=0, reference_length=2)},
            {'wer': dict(substitutions=0, deletions=1, insertions=1, reference_length=8)}]
    assert pooled(rows, 'wer') == {'rate': .3, 'errors': 3, 'reference_length': 10}


def test_majority_accuracy_does_not_imply_positive_class_quality():
    result = majority_metrics({'negative_support': 8, 'positive_support': 2})
    assert result['accuracy'] == .8 and result['balanced_accuracy'] == .5
    assert result['f1'] == result['precision'] == result['recall'] == 0
    assert result['average_precision'] == .2


@pytest.mark.parametrize('corpus,metric', [('hindi', 'wer'), ('hindi', 'cer'), ('hinglish', 'wer'), ('hinglish', 'cer')])
def test_shared_asr_gate_rejects_each_language_metric_regression(corpus, metric):
    small = {'summary': {name: {'wer': .5, 'cer': .2} for name in ['hindi', 'hinglish']}}
    turbo = {'passes_english_dev_gate': True, 'summary': {
        name: {'wer': {'rate': .4}, 'cer': {'rate': .1}} for name in ['hindi', 'hinglish']}}
    assert asr_release_eligible(turbo, small)
    turbo['summary'][corpus][metric]['rate'] = .6
    assert not asr_release_eligible(turbo, small)
    turbo['passes_english_dev_gate'] = False
    assert not asr_release_eligible(turbo, small)
