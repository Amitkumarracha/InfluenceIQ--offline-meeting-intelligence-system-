"""Submitted-report requirements: private, structured NLP, speaker evidence and no LLM routes."""
import io
import json
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf
from tests.test_api import api_client, register
from src.meeting.language import language_profile
from src.meeting.consistency import check_consistency
from src.meeting.events import KeywordEventExtractor, EventExtractionResult
from src.meeting.evidence import EvidenceExtractionResult
from src.meeting.decisions import DecisionResult
from src.meeting.interaction import InteractionResult
from src.meeting.influence import compute_influence
from src.report.generator import generate_report
from src.report.transcript_export import render_export


def test_workstation_can_close_registration_without_blocking_existing_users(api_client, monkeypatch):
    _, client = api_client
    register(client, 'existing-server-user@example.com')
    monkeypatch.setenv('MAI_ALLOW_REGISTRATION', '0')
    assert client.post('/api/auth/register', json={'email': 'new-server-user@example.com', 'password': 'password123'}).status_code == 403
    assert client.post('/api/auth/login', json={'email': 'existing-server-user@example.com', 'password': 'test-password'}).status_code == 200


def test_gpu_profile_overrides_are_explicit(monkeypatch):
    from src.utils.config import get
    monkeypatch.setenv('MAI_ASR_DEVICE', 'cuda')
    monkeypatch.setenv('MAI_ASR_COMPUTE_TYPE', 'float16')
    assert get('asr.device') == 'cuda'
    assert get('asr.compute_type') == 'float16'


def test_no_generative_routes_and_old_notes_are_not_published(api_client):
    api, client = api_client
    auth = register(client, 'nlp@example.com')
    with api.SessionLocal() as db:
        owner = db.query(api.User).filter_by(email='nlp@example.com').one()
        db.add(api.Meeting(id='old', user_id=owner.id, title='Old', status='completed', report_data=json.dumps({'transcript_segments': [], 'local_notes': {'secret': 'old generated output'}})))
        db.commit()
    routes = {r.path for r in api.app.routes}
    assert not {'/api/search', '/api/meetings/{meeting_id}/ask', '/api/meetings/{meeting_id}/summarize'} & routes
    assert 'local_notes' not in client.get('/api/meetings/old', headers=auth).json()['data']
    assert 'local_notes' not in client.get('/api/meetings/old/export', headers=auth).json()
    assert 'old generated output' not in client.get('/api/meetings/old/export?format=md', headers=auth).text
    with api.SessionLocal() as db:
        assert 'local_notes' in json.loads(db.get(api.Meeting, 'old').report_data)  # Retain historical data.


def test_saved_unknown_meeting_can_queue_real_speaker_analysis_privately(api_client, monkeypatch):
    api, client = api_client
    owner = register(client, 'speaker-owner@example.com'); other = register(client, 'speaker-other@example.com')
    wav = api.DATA_DIR / 'old.wav'; sf.write(wav, np.zeros(16000), 16000)
    with api.SessionLocal() as db:
        user = db.query(api.User).filter_by(email='speaker-owner@example.com').one()
        db.add(api.Meeting(id='old', user_id=user.id, title='Preserved', status='completed', report_data=json.dumps({'transcript_segments': [{'speaker': 'UNKNOWN'}], 'vocabulary': 'Asha'})))
        db.commit()
    monkeypatch.setattr('src.audio.diarization.diarization_status', lambda: {'ready': True})
    path = '/api/meetings/old/analyze-speakers'
    assert client.post(path, headers=other).status_code == 404
    assert client.post(path, headers=owner).status_code == 202
    assert api.job_state('old')['diarization'] == 'required'
    assert api.job_state('old')['options']['vocabulary'] == 'Asha'
    assert client.post(path, headers=owner).status_code == 409
    assert client.get('/api/meetings/old', headers=owner).json()['title'] == 'Preserved'
    assert wav.exists()


def test_mixed_language_events_and_negation_keep_source_evidence():
    phrases = [('हमें deployment Friday को करना चाहिए।', 'proposal'),
               ('data ke hisab se latency 120 ms hai.', 'evidence'),
               ('मैं सहमत नहीं हूँ।', 'disagreement'),
               ('हमने तय किया कि Friday को deployment होगा।', 'decision'),
               ('Asha database migration kal tak complete kar dena.', 'action_item')]
    segments = [{'segment_id': i+1, 'start': i*5, 'end': i*5+4, 'speaker': f'SPEAKER_{i%2:02d}', 'text': text} for i, (text, _) in enumerate(phrases)]
    result = KeywordEventExtractor().extract(segments, 'mixed')
    assert [e.event_type for e in result.events] == [kind for _, kind in phrases]
    assert [e.text for e in result.events] == [s['text'] for s in segments]
    assert [e.source_segment_id for e in result.events] == list(range(1,6))
    negative = KeywordEventExtractor().extract([{'segment_id': 8, 'start': 1, 'end': 4, 'speaker': 'A', 'text': 'kal tak database complete nahi kar dena.'}], 'mixed')
    assert not any(e.event_type == 'action_item' for e in negative.events)
    profile = language_profile(segments, ['en','hi'])
    assert profile['label'] == 'Possible Hindi–English mix'
    assert profile['asr_languages'] == ['en','hi'] and profile['devanagari_words'] > 0
    assert 'percentages' in profile['limitations']


def test_full_transcript_participants_with_no_events_have_zero_observed_contributions():
    result = compute_influence(EventExtractionResult('m'), EvidenceExtractionResult('m'), DecisionResult('m'), InteractionResult('m', participants=[]), transcript_segments=[{'speaker': 'A', 'start': 0, 'end': 3}, {'speaker': 'UNKNOWN', 'start': 4, 'end': 5}])
    assert len(result.participants) == 1 and result.participants[0].participant == 'A'
    assert result.participants[0].influence_score == 0
    assert all(value == 0 for value in result.participants[0].raw_features.values())
    assert 'Insufficient' in result.participants[0].explanation[0]


def test_slide_quantity_checks_and_full_report_expose_alignment(tmp_path):
    slides = [{'slide_id': 'slide_01', 'slide_number': 1, 'title': 'Latency', 'text': ['Latency measured 100 ms'], 'tables': []}]
    segment = {'segment_id': 1, 'speaker': 'A', 'start': 1, 'end': 4, 'text': 'Latency measured 120 ms', 'slide_id': 'slide_01'}
    flags = check_consistency([segment], slides)['flags']
    assert flags[0]['spoken_value'] == '120' and flags[0]['slide_value'] == '100' and flags[0]['requires_review']
    assert not check_consistency([{**segment, 'slide_id': 'NO_CONFIDENT_SLIDE'}], slides)['flags']
    assert not check_consistency([{**segment, 'text': 'Latency measured 100 ms'}], slides)['flags']
    for folder in ('slides', 'alignment', 'audio'):
        (tmp_path / folder).mkdir()
    (tmp_path/'slides/m_slides.json').write_text(json.dumps({'slides': slides, 'num_slides': 1}))
    (tmp_path/'audio/m_transcript.json').write_text(json.dumps({'segments': [segment], 'duration': 5, 'language': 'en'}))
    (tmp_path/'alignment/m_alignment.json').write_text(json.dumps({'segments': [{**segment, 'selected_slide': 'slide_01', 'slide_candidates': [{'slide_id': 'slide_01', 'combined_score': .8}]}]}))
    report = generate_report('m', tmp_path)
    assert report.slides == slides and report.aligned_segments[0]['alignment_score'] == .8
    assert report.consistency_checks['flags']
    from src.report.exporter import export_json
    exported = tmp_path / 'report.json'; export_json(report, exported)
    saved = json.loads(exported.read_text())
    assert saved['slides'] == slides and saved['aligned_segments'][0]['alignment_score'] == .8
    assert saved['consistency_checks']['flags'] and saved['language_analysis']


def test_export_role_labels_propagate_and_csv_stays_safe():
    data = {'transcript_segments': [{'segment_id': 1, 'start': 1, 'end': 4, 'speaker': 'A', 'text': 'Source words'}], 'speaker_names': {'A': 'Asha'}, 'speaker_roles': {'A': 'Reviewer'}, 'local_notes': {'overview': [{'text': 'generated content'}]}}
    for format in ('md','txt','srt','vtt'):
        text, _ = render_export(data, 'Planning', format)
        assert 'Asha · Reviewer' in text and 'generated content' not in text
    data['speaker_roles']['A'] = '=formula()'
    text, _ = render_export(data, 'Planning', 'csv')
    assert "'=formula()" in text


def test_persisted_audio_options_remain_validated(api_client):
    api, client = api_client
    auth = register(client, 'options@example.com')
    stream = io.BytesIO(); sf.write(stream, np.zeros(16000), 16000, format='WAV')
    files = {'audio': ('meeting.wav', stream.getvalue(), 'audio/wav')}
    for settings in ({'model_size': 'cloud'}, {'language': 'invalid'}, {'num_speakers': '0'}, {'vocabulary': 'x' * 1001}):
        assert client.post('/api/analyze', headers=auth, files=files, data=settings).status_code == 422
    response = client.post('/api/analyze', headers=auth, files=files, data={'model_size': 'medium', 'language': 'hi', 'vocabulary': 'मीट आईक्यू', 'num_speakers': '4'})
    assert response.status_code == 202
    assert api.job_state(response.json()['meeting_id'])['options']['num_speakers'] == 4
