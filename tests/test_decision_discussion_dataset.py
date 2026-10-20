import numpy as np
import pytest

from scripts.evaluate_decision_discussions import referenced_ids, metrics


def test_nite_ranges_follow_document_order_and_preserve_gaps():
    ids = ['word1', 'noise2', 'word8', 'word20']
    assert referenced_ids('words.xml#id(word1)..id(word8)', ids) == {'word1', 'noise2', 'word8'}
    assert referenced_ids('words.xml#id(word20)', ids) == {'word20'}
    with pytest.raises(ValueError):
        referenced_ids('words.xml#id(word20)..id(word1)', ids)
    with pytest.raises(ValueError):
        referenced_ids('words.xml#id(missing)', ids)


def test_discussion_metrics_include_false_positives_and_false_negatives():
    result = metrics(np.array([1, 1, 0, 0]), np.array([1, 0, 1, 0]))
    assert result['precision'] == result['recall'] == result['f1'] == .5
    assert result['confusion_matrix_tn_fp_fn_tp'] == [1, 1, 1, 1]
