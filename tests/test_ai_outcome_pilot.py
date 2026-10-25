"""Synthetic fixtures test provenance handling, never provide research labels."""
import json

import numpy as np
import pytest

from scripts.train_ai_outcome_pilot import load_rows, metrics, texts, train, evaluate, digest
from scripts.train_contextual_model import load_data, RELATIONS
from scripts import build_ai_outcome_pilot as builder


def fixture_rows():
    return [{'pair_id': f'{split}_{i}', 'group': split, 'split': split,
             'source_text': f'Synthetic {label} option', 'outcome_text': f'Synthetic {label} outcome',
             'relationship': label, 'label_source': 'ai_generated', 'independent_human_review': False,
             'include': True, 'source_reference': {'word_ids': ['fixture']},
             'outcome_reference': {'word_ids': ['fixture']}, 'review_rationale': 'Excluded from model features'}
            for split in ['train', 'dev', 'test'] for i, label in enumerate(RELATIONS)]


def write(path, rows):
    path.write_text('\n'.join(json.dumps(row) for row in rows))


def test_ai_references_are_rejected_by_human_only_trainer(tmp_path):
    path = tmp_path/'ai.jsonl'; write(path, fixture_rows())
    assert len(load_rows(path)) == 12
    with pytest.raises(ValueError, match='independent human'):
        load_data('links', 'train', path)


@pytest.mark.parametrize('change,error', [
    ({'label_source': 'human'}, 'AI-generated'),
    ({'independent_human_review': True}, 'AI-generated'),
    ({'group': 'dev'}, 'cross splits'),
    ({'source_reference': {}}, 'citations'),
])
def test_invalid_provenance_or_leakage_is_rejected(tmp_path, change, error):
    rows = fixture_rows(); rows[0].update(change)
    path = tmp_path/'ai.jsonl'; write(path, rows)
    with pytest.raises(ValueError, match=error):
        load_rows(path)


def test_metric_keeps_four_class_denominator_and_excludes_annotation_notes():
    values = metrics(['adopted', 'rejected'], ['adopted', 'rejected'])
    assert values['ai_label_agreement'] == 1
    assert values['macro_f1_four_classes'] == .5
    assert values['absent_reference_classes'] == ['revised', 'unresolved']
    assert 'Excluded from model features' not in texts(fixture_rows(), 'paired')[0]


def test_training_and_evaluation_preserve_explicit_scope(tmp_path):
    path, output = tmp_path/'ai.jsonl', tmp_path/'model'
    write(path, fixture_rows())
    (tmp_path/'annotation_provenance.json').write_text(json.dumps({'labels_sha256': digest(path), 'source_sha256': {}}))
    train(path, output)
    evaluate(path, output)
    result = json.loads((output/'ai_agreement_evaluation.json').read_text())
    assert result['independent_human_accuracy_measured'] is False
    assert result['presenter_influence_accuracy_measured'] is False
    assert result['installed_in_application'] is False
    with pytest.raises(ValueError, match='Preserve'):
        evaluate(path, output)


def test_reference_passage_uses_verbatim_word_ids_and_time(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, 'ROOT', tmp_path)
    monkeypatch.setattr(builder, 'REFERENCE', tmp_path/'reference')
    words = tmp_path/'reference/words'; words.mkdir(parents=True)
    (words/'ES2002a.A.words.xml').write_text('''<root xmlns:nite="http://nite.sourceforge.net/">
      <w nite:id="w1" starttime="1" endtime="2">Original</w>
      <w nite:id="w2" starttime="2" endtime="3">passage</w>
      <w nite:id="w3" starttime="4" endtime="5">Later</w></root>''')
    sources = set()
    result = builder.passage('ES2002a', {'speaker': 'A', 'start': 1, 'end': 3}, sources)
    assert result['text'] == 'Original passage'
    assert result['word_ids'] == ['w1', 'w2']
    assert result['start'] == 1 and result['end'] == 3
    with pytest.raises(ValueError, match='No traceable'):
        builder.passage('ES2002a', {'speaker': 'A', 'start': 9, 'end': 10}, sources)
