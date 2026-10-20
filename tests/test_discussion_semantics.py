from types import SimpleNamespace

import numpy as np

from src.meeting.discussion_semantics import encode_rows, context_features
from scripts.optimize_discussion_quality import all_metrics, passes_gate


def test_sentence_encoding_deduplicates_only_text_and_restores_row_order():
    seen = []
    def encode(texts, **kwargs):
        seen.extend(texts)
        return np.array([[1., 0.], [0., 1.]])
    rows = [{'text': 'same', 'label': 0}, {'text': 'different'}, {'text': 'same', 'label': 1}]
    values = encode_rows(rows, SimpleNamespace(encode=encode))
    assert seen == ['same', 'different']
    np.testing.assert_array_equal(values, [[1, 0], [0, 1], [1, 0]])


def test_context_means_cannot_cross_meetings_or_use_outcome_labels():
    rows = [{'meeting': m, 'start': t, 'end': t+1, 'act_id': str(i), 'text': 'source'}
            for i, (m, t) in enumerate([('A', 2), ('B', 0), ('A', 0)])]
    vectors = np.array([[1., 0.], [0., 1.], [1., 0.]], dtype=np.float32)
    values = context_features(rows, vectors, 40)
    np.testing.assert_allclose(values, np.hstack([vectors, vectors]))
    for row in rows: row.update(label=1, positive_word_fraction=1.)
    np.testing.assert_allclose(context_features(rows, vectors, 40), values)
    timing = context_features(rows, vectors, 40, timing=True)
    assert timing.shape == (3, 10) and np.isfinite(timing).all()
    assert timing[1, -4] == timing[2, -4] == 0.


def test_metrics_and_non_regression_gate_include_accuracy_and_recall():
    values = all_metrics(np.array([0, 0, 1, 1]), np.array([.1, .2, .8, .9]), .5)
    assert values['accuracy'] == values['balanced_accuracy'] == values['macro_f1'] == values['mcc'] == 1.
    assert values['roc_auc'] == values['specificity'] == 1.
    assert passes_gate(values, values)
    assert not passes_gate(dict(values, recall=.9), values)
    assert not passes_gate(dict(values, accuracy=.9), values)
