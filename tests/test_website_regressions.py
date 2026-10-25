"""Reported web failures: auth, decoding progress, vocabulary, and lost contributions."""
import json
import re

import numpy as np
import pytest
import soundfile as sf

from tests.test_api import api_client, register
from src.audio.parts import decode_parts
from src.meeting.events import KeywordEventExtractor
from src.meeting.vocabulary import suggest_vocabulary


def test_authentication_normalizes_email_rejects_duplicate_and_wrong_password(api_client):
    _, client = api_client
    body = {'email': ' Test.User@Example.com ', 'password': 'test-password'}
    created = client.post('/api/auth/register', json=body)
    assert created.status_code == 200
    assert created.json()['email'] == 'test.user@example.com'
    assert client.post('/api/auth/register', json=body).status_code == 409
    assert client.post('/api/auth/login', json={**body, 'password': 'wrong'}).status_code == 401
    signed_in = client.post('/api/auth/login', json=body)
    assert signed_in.status_code == 200
    assert signed_in.json()['user_id'] == created.json()['user_id']
    assert 'no-store' in signed_in.headers['cache-control']
    for password in ('short', 'अ' * 25):
        assert client.post('/api/auth/register', json={**body, 'password': password}).status_code == 422


def test_meeting_status_and_final_report_are_never_browser_cached(api_client):
    api, client = api_client
    headers = register(client, 'fresh@example.com')
    with api.SessionLocal() as db:
        user = db.query(api.User).filter_by(email='fresh@example.com').one()
        db.add(api.Meeting(id='fresh', user_id=user.id, title='Test', status='processing'))
        db.commit()
    before = client.get('/api/meetings/fresh', headers=headers)
    assert before.json()['status'] == 'processing'
    assert 'no-store' in before.headers['cache-control']
    with api.SessionLocal() as db:
        meeting = db.get(api.Meeting, 'fresh')
        meeting.status = 'completed'
        meeting.report_data = json.dumps({'transcript_segments': [], 'decisions': [{'decision_id': 'd1'}],
                                          'influence': [{'participant': 'A', 'influence_score': .7}]})
        db.commit()
    after = client.get('/api/meetings/fresh', headers=headers)
    assert after.json()['data']['decisions'][0]['decision_id'] == 'd1'
    assert after.json()['data']['influence'][0]['influence_score'] == .7


def test_decode_progress_counts_every_ordered_part_and_cached_completion(tmp_path):
    inputs = []
    for index, value in enumerate([.1, -.2]):
        path = tmp_path / f'{index}.wav'
        sf.write(path, np.full(16000, value), 16000)
        inputs.append(path)
    progress = []
    output = decode_parts(inputs, tmp_path / 'joined.wav', progress.append)
    assert progress[-1] == {'completed_seconds': 2., 'parts_completed': 2, 'parts_total': 2, 'cached': False}
    assert any(item['parts_completed'] == 1 for item in progress)
    assert [item['completed_seconds'] for item in progress] == sorted(item['completed_seconds'] for item in progress)
    samples, _ = sf.read(output)
    assert samples[:16000].mean() > 0 and samples[16000:].mean() < 0
    progress.clear()
    decode_parts(inputs, output, progress.append)
    assert progress == [{'completed_seconds': 2., 'parts_completed': 2, 'parts_total': 2, 'cached': True}]


def test_sentence_capitals_and_ordinals_do_not_become_vocabulary():
    segments = [{'text': 'Anyway Friday. Ordinary words. Ordinary words. Secondly 1st 2nd.'},
                {'text': 'We use GPU and InfluenceIQ. InfluenceIQ uses GPU at 120ms.'},
                {'text': 'We asked Asha twice, and Asha recommended the database.'}]
    terms = set(suggest_vocabulary(segments))
    assert {'GPU', 'InfluenceIQ', '120ms', 'Asha', 'database'} <= terms
    assert not {'ordinary', 'Ordinary', 'Friday', 'friday', 'secondly', '1st', '2nd', 'words'} & terms


@pytest.mark.parametrize('text, kind', [('We should use blue.', 'proposal'),
    ('According to the data sheet.', 'evidence'), ('According to John.', 'evidence')])
def test_default_threshold_keeps_explicit_proposal_and_evidence_cues(text, kind):
    segments = [{'segment_id': 1, 'speaker': 'A', 'start': 1, 'end': 2, 'text': text}]
    events = KeywordEventExtractor().extract(segments, 'test').events
    assert len(events) == 1 and events[0].event_type == kind
    assert events[0].text == text and events[0].confidence >= .3


def test_alternative_patterns_do_not_lower_confidence_of_an_explicit_cue(monkeypatch):
    from src.meeting import events
    before = events._match_event_type('We should use blue.', ['proposal'])
    monkeypatch.setitem(events._PATTERNS, 'proposal', [*events._PATTERNS['proposal'],
        *[re.compile(f'never-observed-{i}') for i in range(20)]])
    assert events._match_event_type('We should use blue.', ['proposal']) == before
    assert not KeywordEventExtractor(confidence_threshold=.31).extract(
        [{'text': 'We should use blue.'}], 'strict').events


def test_complete_decision_chain_keeps_sources_and_records_all_speakers():
    from src.meeting.evidence import extract_evidence
    from src.meeting.decisions import reconstruct_decisions
    from src.meeting.interaction import extract_interactions
    from src.meeting.influence import compute_influence
    rows = [{'segment_id': i, 'speaker': speaker, 'start': i * 10., 'end': i * 10. + 4,
             'text': text} for i, (speaker, text) in enumerate([
        ('A', 'We should use blue.'), ('B', 'According to John, blue is available.'),
        ('C', 'We decided to use blue.'), ('D', 'Ordinary conversation.')], 1)]
    events = KeywordEventExtractor().extract(rows, 'chain')
    evidence = extract_evidence(events)
    decisions = reconstruct_decisions(events, evidence)
    interactions = extract_interactions(events, evidence, decisions)
    scores = compute_influence(events, evidence, decisions, interactions, transcript_segments=rows)
    assert {event.event_type for event in events.events} >= {'proposal', 'evidence', 'decision'}
    assert scores.for_participant('A').raw_features['proposal_contribution'] == 1
    assert scores.for_participant('B').raw_features['evidence_contribution'] == 1
    assert scores.for_participant('D').influence_score == 0
    assert len(scores.participants) == 4
    assert all(0 <= person.influence_score <= 1 for person in scores.participants)
    assert all(event.source_segment_id in {row['segment_id'] for row in rows} for event in events.events)


def test_complete_draft_stays_visible_during_partial_speaker_attribution(tmp_path, monkeypatch):
    from dataclasses import asdict
    from types import SimpleNamespace
    from src.audio import asr, diarization, preprocess
    from src.pipeline import orchestrator
    from src.meeting import discussions
    root = tmp_path / 'data/processed/audio'
    root.mkdir(parents=True)
    path = root / 'draft_transcript.json'
    draft = [asr.TranscriptSegment(i, float(i), float(i) + .5, 'UNKNOWN', f'Original passage {i}')
             for i in range(1, 4)]
    calls = []

    def transcribe(*args, on_chunk, **kwargs):
        if calls:
            on_chunk(draft[:1], {'completed_seconds': 1., 'total_seconds': 4.})
            preview = json.loads((root / 'draft_preview.json').read_text())
            assert [s['text'] for s in preview['transcript_segments']] == [s.text for s in draft]
        calls.append(True)
        on_chunk(draft, {'completed_seconds': 4., 'total_seconds': 4.})
        result = asr.TranscriptResult('draft', 'en', 4., 0, [], draft, detected_languages=['en'])
        path.write_text(json.dumps(asdict(result)))
        return result, path, None

    monkeypatch.setattr(orchestrator, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(orchestrator, 'save_resume_state', lambda *a, **kw: None)
    monkeypatch.setattr(orchestrator, 'mark_stage_complete', lambda *a, **kw: None)
    monkeypatch.setattr(preprocess, 'preprocess_audio', lambda *a, **kw: (tmp_path / 'audio.wav', {}))
    monkeypatch.setattr(asr, 'run_asr', transcribe)
    monkeypatch.setattr(diarization, 'run_diarization', lambda *a, **kw:
        (SimpleNamespace(segments=[1], speakers=['A']), root / 'speakers.json'))
    monkeypatch.setattr(discussions, 'review_discussions', lambda *a, **kw:
        {'status': 'model_unavailable', 'passages': [], 'requires_review': True})
    orchestrator.run_meeting(tmp_path / 'audio.wav', 'draft')
    assert len(calls) == 2


@pytest.mark.parametrize('format', ['md', 'txt', 'csv', 'srt', 'vtt'])
def test_exports_use_the_same_first_appearance_speaker_numbers_without_changing_ids(format):
    from src.report.transcript_export import render_export
    data = {'transcript_segments': [
        {'segment_id': 1, 'speaker': 'SPEAKER_42', 'start': 0, 'end': 1, 'text': 'First.'},
        {'segment_id': 2, 'speaker': 'SPEAKER_03', 'start': 1, 'end': 2, 'text': 'Second.'},
        {'segment_id': 3, 'speaker': 'UNKNOWN', 'start': 2, 'end': 3, 'text': 'Unassigned.'}],
        'speaker_names': {'SPEAKER_42': ''}}
    before = json.dumps(data)
    content, _ = render_export(data, 'Meeting', format)
    assert 'Speaker 1' in content and 'Speaker 2' in content
    assert 'Speaker not identified' in content
    assert 'SPEAKER_42' not in content and 'SPEAKER_03' not in content
    assert json.dumps(data) == before
