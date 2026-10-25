"""Synthetic regression checks; these do not measure research accuracy."""
from src.meeting.decisions import reconstruct_decisions, _build_lineage
from src.meeting.events import EventExtractionResult, MeetingEvent
from src.meeting.evidence import extract_evidence, EvidenceRelation
from src.meeting.influence import compute_influence
from src.meeting.interaction import InteractionResult


def analyse(kinds):
    events = EventExtractionResult('m', [
        MeetingEvent(f'e{i}', kind, f'P{i}', i*10, i*10+5, kind, None, None, i)
        for i, kind in enumerate(kinds)])
    evidence = extract_evidence(events)
    decisions = reconstruct_decisions(events, evidence)
    result = compute_influence(events, evidence, decisions, InteractionResult('m', participants=[]))
    return decisions, result


def test_secondary_proposals_and_decisions_retain_speaker_credit():
    decisions, result = analyse(['proposal', 'proposal', 'decision', 'decision'])
    assert len(decisions.decisions) == 1
    decision = decisions.decisions[0]
    assert decision.proposal['event_id'] == 'e0'
    assert decision.final_decision['event_id'] == 'e3'
    assert {row['event_id'] for row in decision.discussion} == {'e1', 'e2'}
    for participant in result.participants:
        assert participant.raw_features['decision_contribution'] == 1
        assert len(participant.supporting_events) == 1
        assert participant.supporting_decisions == [decision.decision_id]
    for speaker in ['P0', 'P1']:
        assert result.for_participant(speaker).raw_features['proposal_contribution'] == 1
        assert 'proposer' in result.for_participant(speaker).decision_contributions[0].roles


def test_evidence_provider_role_does_not_require_a_detected_proposal():
    _, result = analyse(['evidence', 'decision'])
    provider = result.for_participant('P0')
    assert provider.raw_features['evidence_contribution'] == 1
    assert 'evidence_provider' in provider.decision_contributions[0].roles


def test_confirmed_cluster_does_not_prove_the_initial_proposal_was_adopted():
    events = EventExtractionResult('m', [
        MeetingEvent('p', 'proposal', 'A', 0, 5, 'We should use option A.', None, None, 0),
        MeetingEvent('o', 'objection', 'B', 10, 15, 'Option A will not work.', None, None, 1),
        MeetingEvent('d', 'decision', 'B', 20, 25, 'We will use option B.', None, None, 2)])
    evidence = extract_evidence(events)
    decisions = reconstruct_decisions(events, evidence)
    assert decisions.decisions[0].status == 'confirmed'
    result = compute_influence(events, evidence, decisions, InteractionResult('m', participants=[]))
    # Being in the cluster earns base credit, not an unverified adoption bonus.
    assert result.for_participant('A').raw_features['proposal_contribution'] == 1


def test_evidence_lineage_preserves_who_supports_whom():
    proposal = MeetingEvent('p', 'proposal', 'A', 0, 5, 'Choose A.', None, None, 0)
    evidence = MeetingEvent('e', 'evidence', 'B', 10, 15, 'Data supports A.', None, None, 1)
    relation = EvidenceRelation('r', 'e', 'p', 'supports', None, None)
    edges = _build_lineage([proposal, evidence], [relation], 'p', None)
    assert {(edge.source, edge.relationship, edge.target) for edge in edges} == {('e', 'supports', 'p')}
