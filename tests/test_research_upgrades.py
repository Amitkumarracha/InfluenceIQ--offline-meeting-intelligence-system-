"""Regression checks for optional research paths; no accuracy claims from fixtures."""
import hashlib
import json

import numpy as np
import pytest

from src.audio.asr import attribute_speaker
from src.meeting.contextual import context_pairs
from src.meeting.decisions import reconstruct_decisions
from src.meeting.events import EventExtractionResult, MeetingEvent
from src.meeting.evidence import extract_evidence
from src.meeting.influence import compute_influence
from src.meeting.interaction import InteractionResult
from src.meeting.outcomes import link_outcomes
from src.meeting.ranking import FEATURE_NAMES, participant_features, rank_participants
from src.meeting.topics import event_topics


def passages():
    return EventExtractionResult('m', [
        MeetingEvent('p1', 'proposal', 'A', 0, 1, 'Use blue.', None, None, 1),
        MeetingEvent('p2', 'proposal', 'B', 2, 3, 'Use aluminium.', None, None, 2),
        MeetingEvent('d1', 'decision', 'A', 4, 5, 'Blue is final.', None, None, 3),
        MeetingEvent('d2', 'decision', 'B', 6, 7, 'Aluminium is final.', None, None, 4)])


def test_context_preserves_input_order_and_never_crosses_meetings():
    rows = [{'meeting': group, 'start': start, 'text': text} for group, start, text in
            [('a', 2, 'last'), ('b', 0, 'private'), ('a', 0, 'first'), ('a', 1, 'middle')]]
    paired = context_pairs(rows, radius=1)
    assert paired[0] == ('last', 'Previous: middle Following: ')
    assert paired[1] == ('private', 'Previous:  Following: ')
    assert paired[2] == ('first', 'Previous:  Following: middle')
    with pytest.raises(ValueError):
        context_pairs(rows, radius=-1)


def test_topic_grouping_separates_nearby_decisions_and_attaches_short_replies():
    events = passages()
    reply = MeetingEvent('r', 'agreement', 'C', 3, 4, 'Yes.', None, None, 5)
    events.events.append(reply)
    topics = event_topics(events.events, [[1, 0], [0, 1], [1, 0], [0, 1], [1, 0]])
    assert topics == {'p1': 0, 'p2': 1, 'r': 1, 'd1': 0, 'd2': 1}
    evidence = extract_evidence(events)
    decisions = reconstruct_decisions(events, evidence, topic_ids=topics)
    assert len(decisions.decisions) == 2
    assert [(d.proposal['event_id'], d.final_decision['event_id']) for d in decisions.decisions] == [('p1', 'd1'), ('p2', 'd2')]
    with pytest.raises(ValueError, match='Topic'):
        reconstruct_decisions(events, evidence, topic_ids={'p1': 0})


def test_speaker_margin_trades_coverage_for_abstention():
    diar = [{'start': 0., 'end': 5.2, 'speaker': 'A'}, {'start': 5.2, 'end': 10., 'speaker': 'B'}]
    assert attribute_speaker(0, 10, diar) == 'A'
    assert attribute_speaker(0, 10, diar, min_speaker_margin=.1) == 'UNKNOWN'
    assert attribute_speaker(0, 4, diar, min_speaker_margin=.1) == 'A'
    with pytest.raises(ValueError):
        attribute_speaker(0, 10, diar, min_speaker_margin=1.1)


def test_attribution_diagnostic_counts_unknown_as_wrong_and_maps_once():
    from scripts.evaluate_speaker_margin import attribution_curve
    truth = [{'start': 0., 'end': 10., 'speaker': 'A'}]
    hyp = [{'start': 0., 'end': 5.2, 'speaker': 'cluster1'},
           {'start': 5.2, 'end': 10., 'speaker': 'cluster2'}]
    curve = attribution_curve(truth, truth, hyp, margins=(0., .1))
    assert curve[0]['accepted_precision'] == curve[0]['accuracy_unknown_counted_wrong'] == 1
    assert curve[1]['coverage'] == curve[1]['accuracy_unknown_counted_wrong'] == 0
    assert curve[1]['accepted_precision'] is None


def model_fixture(root, task, labels):
    (root/'model').mkdir()
    weights = root/'model/model.safetensors'
    weights.write_bytes(b'mocked weights')
    (root/'protocol.json').write_text(json.dumps({'task': task, 'max_length': 96}))
    (root/'selection.json').write_text(json.dumps({'labels': labels,
        'model_sha256': hashlib.sha256(weights.read_bytes()).hexdigest(),
        'development': {'thresholds': [.5]*len(labels)}}))


def test_outcome_predictions_never_become_reference_labels(tmp_path, monkeypatch):
    from src.meeting.outcomes import RELATIONS
    events = passages()
    decisions = reconstruct_decisions(events, extract_evidence(events))
    blank = link_outcomes(events, decisions)
    assert blank['status'] == 'independent_annotations_required'
    assert len(blank['links']) == 2
    assert all(row['relationship'] is row['label_source'] is None for row in blank['links'])
    model_fixture(tmp_path, 'links', RELATIONS)
    monkeypatch.setattr('src.meeting.contextual.predict_pairs', lambda *args, **kwargs: np.array([[.8, .1, .05, .05]]*2))
    result = link_outcomes(events, decisions, tmp_path)
    assert all(row['predicted_relationship'] == 'adopted' for row in result['links'])
    assert all(row['relationship'] is row['label_source'] is None for row in result['links'])
    monkeypatch.setattr('src.meeting.contextual.predict_pairs', lambda *args, **kwargs: np.array([[np.nan]*4]*2))
    with pytest.raises(ValueError, match='scores'):
        link_outcomes(events, decisions, tmp_path)


def test_outcome_manifest_rejects_unlabelled_or_leaking_groups(tmp_path):
    from scripts.train_contextual_model import load_data
    path = tmp_path/'links.jsonl'
    row = {'source_text': 'Use A', 'outcome_text': 'A agreed', 'group': 'g', 'split': 'train',
           'relationship': None, 'label_source': None}
    path.write_text(json.dumps(row))
    with pytest.raises(ValueError, match='independent human'):
        load_data('links', 'train', path)
    row.update(relationship='adopted', label_source='human')
    path.write_text(json.dumps(row)+'\n'+json.dumps({**row, 'split': 'test'}))
    with pytest.raises(ValueError, match='cross splits'):
        load_data('links', 'train', path)


def test_development_calibration_covers_rare_low_probability_roles():
    from scripts.calibrate_contextual_roles import calibrate
    labels = np.array([[0], [1], [0], [1]])
    scores = np.array([[.01], [.03], [.02], [.04]])
    chosen = calibrate(labels, scores)
    assert chosen['thresholds'] == [.03]
    assert chosen['macro_f1'] == 1
    with pytest.raises(ValueError):
        calibrate(labels, np.array([[np.nan]]*4))


def test_paired_comparison_resamples_groups_and_keeps_identical_models_equal():
    from scripts.compare_contextual_discussion import paired_intervals
    truth = np.array([0, 1, 1, 0])
    predicted = np.array([0, 1, 0, 0])
    comparison = paired_intervals(truth, predicted, predicted, ['a', 'a', 'b', 'b'], repeats=50)
    assert comparison['accuracy']['candidate'] == .75
    assert comparison['positive_f1']['paired_difference_95_interval'] == [0, 0]


def test_learned_roles_keep_sources_and_reject_missing_predictions(tmp_path, monkeypatch):
    from src.meeting.learned_events import ContextualRoleExtractor, LABELS
    model_fixture(tmp_path, 'roles', LABELS)
    model = ContextualRoleExtractor(tmp_path)
    segments = [{'segment_id': 7, 'speaker': 'A', 'start': 1., 'end': 2., 'text': 'Use blue.',
                 'slide_id': 'NO_CONFIDENT_SLIDE'}]
    monkeypatch.setattr('src.meeting.learned_events.predict_pairs', lambda *args: np.array([[.8, .1, .1, .1]]))
    result = model.extract(segments, 'm')
    assert [(e.event_type, e.source_segment_id, e.text) for e in result.events] == [('proposal', 7, 'Use blue.')]
    assert result.events[0].slide_id is None
    zero_duration = model.extract([{**segments[0], 'end': 1.}], 'm')
    assert zero_duration.events[0].start == zero_duration.events[0].end == 1.
    monkeypatch.setattr('src.meeting.learned_events.predict_pairs', lambda *args: np.array([[.1, .8, .1, .9]]))
    result = model.extract(segments, 'm')
    assert [(event.event_type, event.confidence) for event in result.events] == [('agreement', .9)]
    monkeypatch.setattr('src.meeting.learned_events.predict_pairs', lambda *args: np.empty((0, 4)))
    with pytest.raises(ValueError, match='scores'):
        model.extract(segments, 'm')
    with pytest.raises(ValueError, match='passage'):
        model.extract([{**segments[0], 'end': float('inf')}], 'm')


def test_ranker_features_unique_normalized_and_inference_verified(tmp_path, monkeypatch):
    events = passages()
    evidence = extract_evidence(events)
    decisions = reconstruct_decisions(events, evidence)
    influence = compute_influence(events, evidence, decisions, InteractionResult('m', participants=[]))
    segments = [{'speaker': 'A', 'start': 0, 'end': 2, 'text': 'one two three four'},
                {'speaker': 'B', 'start': 2, 'end': 3, 'text': 'one two'}]
    features = participant_features(events, influence, segments)
    assert len(set(FEATURE_NAMES)) == len(FEATURE_NAMES)
    assert features['A']['words'] == 1
    assert features['B']['words'] == .5
    assert all(0 <= value <= 1 for row in features.values() for value in row.values())
    weights = tmp_path/'ranker.ubj'; weights.write_bytes(b'mock')
    (tmp_path/'ranker.json').write_text(json.dumps({'features': ['words'], 'topic_aware': False,
        'model_sha256': hashlib.sha256(weights.read_bytes()).hexdigest()}))
    class Ranker:
        def load_model(self, path):
            pass
        def set_params(self, **params):
            pass
        def predict(self, matrix):
            return matrix[:, 0]
    monkeypatch.setattr('src.meeting.ranking.xgb_ranker_class', lambda: Ranker)
    result = rank_participants(tmp_path, features)
    assert [row['participant'] for row in result['participants']] == ['A', 'B']
    assert not result['accuracy_measured']
    with pytest.raises(ValueError, match='matching topic'):
        rank_participants(tmp_path, features, topic_aware=True)
    weights.write_bytes(b'changed')
    with pytest.raises(ValueError, match='frozen'):
        rank_participants(tmp_path, features)


def test_pipeline_rejects_untrained_ranker_and_extractor_combination(tmp_path):
    from src.pipeline.orchestrator import run_meeting
    with pytest.raises(ValueError, match='require keyword events'):
        run_meeting(tmp_path/'absent.wav', 'm', options={'event_model': 'roles', 'ranker_model': 'ranker'})
    assert not (tmp_path/'data').exists()
