"""Synthetic validation cases, not research reference labels."""
import csv
import json

import pytest

from scripts import outcome_annotation_workflow as workflow


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def labelled_fixture():
    return [{'meeting_id': group, 'source_event_id': label, 'outcome_event_id': 'outcome',
             'source_text': 'Synthetic source', 'outcome_text': 'Synthetic outcome',
             'source_start': '1', 'outcome_start': '2', 'group': group, 'split': split,
             'relationship': label, 'label_source': 'human', 'include': 'yes'}
            for split, group in [('train', 'g1'), ('dev', 'g2'), ('test', 'g3')]
            for label in workflow.RELATIONS]


def test_converter_preserves_checked_data_and_prevents_overwrite(tmp_path):
    source, target = tmp_path/'labels.csv', tmp_path/'labels.jsonl'
    write_csv(source, labelled_fixture())
    result = workflow.convert(source, target)
    assert result['rows'] == 12 and result['groups'] == 3
    assert json.loads(target.read_text().splitlines()[0])['source_start'] == 1.
    with pytest.raises(ValueError, match='preserved'):
        workflow.convert(source, target)


@pytest.mark.parametrize('change,error', [
    ({'include': ''}, 'include'), ({'label_source': ''}, 'human'),
    ({'group': 'g2'}, 'crosses splits'), ({'outcome_text': ''}, 'verify source'),
    ({'source_start': '3'}, 'after outcome'), ({'source_start': 'nan'}, 'invalid'),
])
def test_converter_rejects_unchecked_or_invalid_labels(tmp_path, change, error):
    rows = labelled_fixture(); rows[0].update(change)
    source, target = tmp_path/'labels.csv', tmp_path/'labels.jsonl'
    write_csv(source, rows)
    with pytest.raises(ValueError, match=error):
        workflow.convert(source, target)
    assert not target.exists()


def test_pilot_without_class_coverage_cannot_silently_train_four_classes(tmp_path):
    rows = labelled_fixture()[:-1]
    source, target = tmp_path/'labels.csv', tmp_path/'labels.jsonl'
    write_csv(source, rows)
    with pytest.raises(ValueError, match='Missing split/class coverage'):
        workflow.convert(source, target)
    assert not target.exists()


def test_prepare_is_blank_and_keeps_independent_copies(tmp_path, monkeypatch):
    source, target = tmp_path/'source', tmp_path/'review'
    source.mkdir()
    (source/'rows.jsonl').write_text(json.dumps({'meeting_id': 'ES2002a',
        'source_text': 'Source', 'outcome_text': 'Outcome', 'relationship': 'adopted'}))
    monkeypatch.setattr(workflow, 'reference_context', lambda meeting: ('Manual context', []))
    workflow.prepare(source, target)
    assert (target/'context/ES2002a.txt').read_text() == 'Manual context'
    assert (target/'reviewer_A.csv').read_bytes() == (target/'reviewer_B.csv').read_bytes()
    with (target/'adjudicated.csv').open(encoding='utf-8-sig') as stream:
        row = next(csv.DictReader(stream))
    assert row['relationship'] == row['label_source'] == row['include'] == row['split'] == ''
    assert row['group'] == 'ES2002'
    with pytest.raises(ValueError, match='preserve existing labels'):
        workflow.prepare(source, target)
