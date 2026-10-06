"""Evidence, offline-only inference boundaries, and long-meeting recovery."""
import json
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest
import soundfile as sf

from src.audio.asr import run_asr
from src.meeting import local_notes
from src.meeting.search import search_segments
from src.report.transcript_export import render_export
from tests.test_api import api_client, register  # reuse the isolated local API fixture


def segment(id=1, text='Asha will send the report Friday.', start=3600):
    return {'segment_id': id, 'start': start, 'end': start + 5, 'speaker': 'SPEAKER_00', 'text': text}


def item(id=1, quote='send the report Friday.'):
    return {'text': 'Send report', 'quote': quote, 'source_segment_ids': [id], 'owner': 'Asha', 'due': 'Friday'}


def test_invalid_citations_and_invented_owners_are_rejected():
    raw = {'action_items': [item(), {**item(), 'source_segment_ids': [999]},
        {**item(), 'quote': 'invented words'}, {**item(), 'owner': 'Ravi', 'due': '2026-10-09'}, None]}
    checked, rejected = local_notes.checked_items(raw, [segment()])
    assert rejected == 3
    assert checked['action_items'][0]['owner'] == 'Asha'
    assert checked['action_items'][1]['owner'] is None
    assert checked['action_items'][1]['due'] is None
    assert checked['action_items'][0]['start'] == 3600


def test_unicode_long_turns_fit_context_and_preserve_every_character():
    text = 'हमें शुक्रवार को रिपोर्ट भेजनी है। ' * 300
    chunks = list(local_notes.transcript_chunks([segment(text=text)]))
    assert len(chunks) > 1
    assert ''.join(s['text'] for c in chunks for s in c) == text
    assert all(len(json.dumps(c, ensure_ascii=False).encode()) <= 5000 for c in chunks)
    assert {s['segment_id'] for c in chunks for s in c} == {1}


def test_notes_resume_all_parts_and_invalidate_changed_model(tmp_path, monkeypatch):
    segments = [segment(i, f'Unique turn {i}. ' * 60, start=i * 100) for i in range(1, 15)]
    digest = ['first']
    monkeypatch.setattr(local_notes, 'require_local_model', lambda name: {'digest': digest[0]})
    calls = []
    def chat(name, chunk, groups, question=None):
        calls.append(chunk)
        if len(calls) == 2:
            raise RuntimeError('interrupted')
        return {g: ([item(chunk[0]['segment_id'], chunk[0]['text'])] if g == 'overview' else []) for g in groups}
    monkeypatch.setattr(local_notes, '_chat', chat)
    with pytest.raises(RuntimeError, match='interrupted'):
        local_notes.summarize(segments, 'local-model', tmp_path)
    ticks = []
    result = local_notes.summarize(segments, 'local-model', tmp_path, ticks.append)
    assert result['chunks'] == len(list(local_notes.transcript_chunks(segments)))
    assert len(calls) == result['chunks'] + 1
    assert ticks[-1]['completed_chunks'] == ticks[-1]['total_chunks']
    assert result['overview'][-1]['source_segment_ids'][0] > 1
    count = len(calls)
    local_notes.summarize(segments, 'local-model', tmp_path)
    assert len(calls) == count
    digest[0] = 'different'
    local_notes.summarize(segments, 'local-model', tmp_path)
    assert len(calls) == count + result['chunks']


def test_cloud_aliases_never_receive_transcript(monkeypatch):
    calls = []
    def request(method, path, payload=None, timeout=3):
        calls.append(path)
        if path == '/api/tags':
            return {'models': [
                {'name': 'cloud:cloud', 'size': 10, 'details': {'format': 'gguf'}},
                {'name': 'alias', 'size': 10, 'details': {'format': 'gguf'}}]}
        return {'remote_model': 'external'}
    monkeypatch.setattr(local_notes, '_request', request)
    with pytest.raises(ValueError, match='Cloud'):
        local_notes.require_local_model('cloud:cloud')
    with pytest.raises(ValueError, match='Remote'):
        local_notes.require_local_model('alias')
    assert '/api/chat' not in calls


def test_search_keeps_neighbours_and_no_model_fallback(monkeypatch):
    segments = [segment(1, 'Planning.'), segment(2, 'हमें रिपोर्ट शुक्रवार को भेजनी है।'), segment(3, 'Agreed.')]
    monkeypatch.setattr(local_notes, '_request', lambda *a, **k: pytest.fail('Search must not contact Ollama'))
    result = local_notes.ask(segments, 'रिपोर्ट')
    assert result['sources'][0]['segment_id'] == 2
    assert len(result['sources'][0]['context']) == 3
    assert result['method'] == 'transcript_search'
    assert search_segments(segments, 'absentword') == []


def test_exports_keep_late_meeting_times_names_and_csv_safety():
    data = {'transcript_segments': [segment(1, '=SUM(A1)', start=7200.125)], 'speaker_names': {'SPEAKER_00': 'Asha'}}
    for format in ('md', 'txt', 'srt', 'vtt', 'csv'):
        text, _ = render_export(data, 'Meeting', format)
        assert 'Asha' in text and '=SUM(A1)' in text
        if format not in {'csv'}:
            assert '02:00:00' in text
    assert '02:00:00,125' in render_export(data, 'Meeting', 'srt')[0]
    assert render_export(data, 'Meeting', 'vtt')[0].startswith('WEBVTT')
    assert "'=SUM(A1)" in render_export(data, 'Meeting', 'csv')[0]


def test_asr_per_meeting_hints_cache_and_progress(tmp_path):
    audio = tmp_path / 'audio.wav'; diar = tmp_path / 'diar.json'
    sf.write(audio, np.ones(16000) * .005, 16000); diar.write_text('{"segments": []}')
    calls = []
    def transcribe(samples, **kwargs):
        calls.append(kwargs)
        return iter([SimpleNamespace(start=0, end=1, text='Asha', words=None, avg_logprob=-.1)]), SimpleNamespace(language='en')
    options = {'model_size': 'medium', 'language': 'en', 'vocabulary': 'Asha Meet IQ'}
    ticks = []
    with patch('src.audio.asr._load_whisper_model', return_value=SimpleNamespace(transcribe=transcribe)) as loader:
        run_asr(audio, diar, 'options', tmp_path, options, ticks.append)
        loader.assert_called_once_with('medium')
        run_asr(audio, diar, 'options', tmp_path, options, ticks.append)
        run_asr(audio, diar, 'options', tmp_path, {**options, 'vocabulary': 'Ravi'}, ticks.append)
    assert len(calls) == 2
    assert calls[0]['hotwords'] == 'Asha Meet IQ' and calls[0]['language'] == 'en'
    assert ticks[-1]['completed_seconds'] == 1


def test_api_notes_search_edits_and_exports_are_owned(api_client, monkeypatch):
    api, client = api_client
    owner = register(client, 'notes@example.com'); other = register(client, 'other@example.com')
    data = {'transcript_segments': [segment()], 'processing': {'warnings': []}}
    with api.SessionLocal() as db:
        owner_id = db.query(api.User).filter_by(email='notes@example.com').one().id
        db.add(api.Meeting(id='owned', user_id=owner_id, title='Weekly', status='completed', report_data=json.dumps(data)))
        db.commit()
    assert client.get('/api/search?q=report', headers=other).json()['results'] == []
    assert client.get('/api/search?q=report', headers=owner).json()['results'][0]['meeting_id'] == 'owned'
    assert client.post('/api/meetings/owned/ask', headers=owner, json={'question': 'report'}).json()['sources']
    for path in ('edit', 'ask', 'summarize'):
        payload = {'title': 'New'} if path == 'edit' else {'question': 'report'} if path == 'ask' else {'model': 'local'}
        assert client.post('/api/meetings/owned/' + path, headers=other, json=payload).status_code == 404
    assert client.post('/api/meetings/owned/edit', headers=owner, json={'speaker_names': {'UNKNOWN': 'Invented'}}).status_code == 422
    assert client.post('/api/meetings/owned/edit', headers=owner, json={'title': 'Renamed', 'speaker_names': {'SPEAKER_00': 'Asha'}}).status_code == 200
    assert 'Renamed' in client.get('/api/meetings/owned/export?format=md', headers=owner).text
    assert client.get('/api/meetings/owned/export?format=exe', headers=owner).status_code == 422
    monkeypatch.setattr(local_notes, 'require_local_model', lambda name: {'name': name, 'digest': 'one'})
    monkeypatch.setattr(local_notes, '_chat', lambda name, chunk, groups: {g: [item()] if g == 'action_items' else [] for g in groups})
    assert client.post('/api/meetings/owned/summarize', headers=owner, json={'model': 'local'}).status_code == 202
    assert client.post('/api/meetings/owned/summarize', headers=owner, json={'model': 'local'}).status_code == 409
    api.run_summary_background(owner_id, 'owned')
    response = client.get('/api/meetings/owned', headers=owner).json()
    assert response['summary_status'] == 'completed'
    assert response['data']['speaker_names']['SPEAKER_00'] == 'Asha'
    assert response['data']['local_notes']['action_items'][0]['due'] == 'Friday'
    assert 'Send report' in client.get('/api/meetings/owned/export?format=md', headers=owner).text


def test_api_validates_persisted_meeting_options(api_client):
    api, client = api_client
    auth = register(client, 'settings@example.com')
    import io
    buffer = io.BytesIO(); sf.write(buffer, np.zeros(16000), 16000, format='WAV')
    files = {'audio': ('meeting.wav', buffer.getvalue(), 'audio/wav')}
    for settings in ({'model_size': 'cloud'}, {'language': 'invalid'}, {'num_speakers': '0'}, {'vocabulary': 'x' * 1001}):
        assert client.post('/api/analyze', headers=auth, files=files, data=settings).status_code == 422
    response = client.post('/api/analyze', headers=auth, files=files, data={'model_size': 'medium', 'language': 'hi', 'vocabulary': 'मीट आईक्यू', 'num_speakers': '8'})
    assert response.status_code == 202
    options = api.job_state(response.json()['meeting_id'])['options']
    assert options == {'model_size': 'medium', 'language': 'hi', 'vocabulary': 'मीट आईक्यू', 'num_speakers': 8}
