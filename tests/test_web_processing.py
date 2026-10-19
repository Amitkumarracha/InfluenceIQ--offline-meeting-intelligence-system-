"""Progress honesty, source-word reuse, presentation validation and speaker correction."""
import io
import json
import subprocess
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile

import numpy as np
import pytest
import soundfile as sf

from tests.test_api import api_client, register
from src.audio.asr import run_asr
from src.meeting.vocabulary import suggest_vocabulary
from src.pipeline.progress import job_progress
from src.ppt.validation import validate_pptx


def test_progress_separates_measured_stage_from_estimated_overall_and_finished_time():
    now = datetime(2026, 10, 19, tzinfo=timezone.utc)
    state = {'stage': 'transcription', 'started_at': (now - timedelta(seconds=100)).isoformat(),
             'stage_started_at': (now - timedelta(seconds=90)).isoformat(),
             'progress': {'completed_seconds': 120, 'total_seconds': 600},
             'stage_timings_seconds': {'decoding': 10},
             'estimated_stage_seconds': {'transcription': 450, 'diarization': 500, 'report': 1}}
    progress = job_progress(state, 'processing', now)
    assert progress['elapsed_seconds'] == 100 and progress['stage_elapsed_seconds'] == 90
    assert progress['stage_percent'] == 20
    assert 0 < progress['overall_percent'] < progress['stage_percent']
    assert progress['remaining_stage_seconds'] == 360
    assert progress['estimated_remaining_seconds'] == 861
    state['worker_elapsed_seconds'] = 1420
    done = job_progress(state, 'completed', now + timedelta(days=1))
    assert done['overall_percent'] == 100 and done['elapsed_seconds'] == 1420
    assert done['estimated_remaining_seconds'] == 0 and done['stage_elapsed_seconds'] is None
    state.pop('started_at')
    assert job_progress(state, 'processing', now)['elapsed_seconds'] == 100  # Older durable jobs.
    assert job_progress({'stage': 'diarization'}, 'processing', now)['stage_percent'] is None
    assert job_progress(state, 'queued', now)['overall_percent'] == 0


def test_changed_speakers_reuses_exact_original_word_observations_without_loading_model(tmp_path):
    audio = tmp_path / 'audio.wav'; sf.write(audio, np.ones(16000 * 12) * .01, 16000)
    diar = tmp_path / 'speakers.json'; diar.write_text('{"segments": []}')
    segment = SimpleNamespace(start=1, end=10, text='Hello नमस्ते world', avg_logprob=-.2, words=[
        SimpleNamespace(start=1, end=2, word='Hello'), SimpleNamespace(start=6, end=7, word=' नमस्ते'),
        SimpleNamespace(start=9, end=10, word=' world')])
    model = SimpleNamespace(transcribe=lambda *a, **kw: (iter([segment]), SimpleNamespace(language='hi')))
    with patch('src.audio.asr._load_whisper_model', return_value=model) as loader:
        before, _, _ = run_asr(audio, diar, 'observations', tmp_path)
        assert loader.call_count == 1
    diar.write_text(json.dumps({'segments': [{'start': 0, 'end': 5, 'speaker': 'A'}, {'start': 5, 'end': 12, 'speaker': 'B'}]}))
    with patch('src.audio.asr._load_whisper_model', side_effect=AssertionError('Whisper decoded twice')):
        after, _, _ = run_asr(audio, diar, 'observations', tmp_path)
    assert [s.speaker for s in before.segments] == ['UNKNOWN', 'UNKNOWN', 'UNKNOWN']
    assert [s.speaker for s in after.segments] == ['A', 'B', 'B']
    assert [(s.start, s.end, s.text) for s in before.segments] == [(s.start, s.end, s.text) for s in after.segments]
    assert before.detected_languages == after.detected_languages == ['hi']
    assert before.recording_quality == after.recording_quality
    # Hints affect neural decoding, so the old observation cache must not hide changed hints.
    with patch('src.audio.asr._load_whisper_model', return_value=model) as loader:
        run_asr(audio, diar, 'observations', tmp_path, options={'vocabulary': 'नमस्ते'})
        assert loader.call_count == 1


def test_vocabulary_ranks_observed_context_not_repeated_filler():
    transcript = [{'text': 'actually basically really people things things actually actually.'},
                  {'text': 'We use GPU and InfluenceIQ for deployment and बजट.'},
                  {'text': 'The InfluenceIQ service uses GPU; latency 120ms.'}]
    terms = suggest_vocabulary(transcript)
    assert {'GPU', 'InfluenceIQ', 'deployment', 'बजट', 'latency', '120ms'} <= set(terms)
    assert not {'actually', 'basically', 'people', 'things', 'really'} & set(terms)
    assert 'GPU' not in suggest_vocabulary([{'text': 'Nothing specific here.'}])
    assert 'foobar' in suggest_vocabulary([{'text': 'we discuss foobar'}], slide_text=['foobar architecture'])


def test_explicit_bilingual_self_introductions_abstain_on_conflicts_and_other_peoples_names():
    from src.meeting.participants import self_introductions
    segments = [
        {'speaker': 'A', 'text': 'My name is Asha Rao, and I work here.', 'start': 1, 'segment_id': 1},
        {'speaker': 'B', 'text': 'मेरा नाम अमित कुमार है।', 'start': 4, 'segment_id': 2},
        {'speaker': 'C', 'text': 'mera naam Ravi hai.', 'start': 8, 'segment_id': 3},
        {'speaker': 'D', 'text': 'I spoke to Asha about the budget.'},
        {'speaker': 'E', 'text': 'My name is software engineer.'},
        {'speaker': 'UNKNOWN', 'text': 'My name is Someone.'},
    ]
    names = self_introductions(segments)
    assert {speaker: info['name'] for speaker, info in names.items()} == {'A': 'Asha Rao', 'B': 'अमित कुमार', 'C': 'Ravi'}
    assert names['B']['source_text'] == segments[1]['text'] and names['B']['requires_review']
    assert 'A' not in self_introductions(segments + [{'speaker': 'A', 'text': 'My name is Another Person.'}])


def test_presentation_rejected_before_queue_and_valid_pptx_accepted(api_client, tmp_path):
    api, client = api_client; auth = register(client, 'ppt@example.com')
    audio = io.BytesIO(); sf.write(audio, np.zeros(16000), 16000, format='WAV')
    files = [('audio', ('speech.wav', audio.getvalue())), ('ppt', ('slides.pptx', b'not a presentation'))]
    assert client.post('/api/analyze', headers=auth, files=files).status_code == 422
    assert not list((api.RUNTIME / 'jobs').glob('*.json'))
    assert not list((api.RUNTIME / 'uploads').glob('*'))
    from pptx import Presentation
    presentation = tmp_path / 'valid.pptx'; Presentation().save(presentation)
    validate_pptx(presentation)
    files[1] = ('ppt', ('slides.pptx', presentation.read_bytes()))
    result = client.post('/api/analyze', headers=auth, files=files)
    assert result.status_code == 202
    state = api.job_state(result.json()['meeting_id'])
    assert state['audio_duration_seconds'] == 1 and state['queued_at']
    bad = tmp_path / 'bad.pptx'
    with ZipFile(bad, 'w') as archive:
        archive.writestr('[Content_Types].xml', '<!DOCTYPE test [<!ENTITY x "bad">]><test>&x;</test>')
        archive.writestr('ppt/presentation.xml', '<p/>')
    with pytest.raises(ValueError): validate_pptx(bad)
    with ZipFile(bad, 'w') as archive:
        archive.writestr('[Content_Types].xml', '<test/>')
        archive.writestr('ppt/presentation.xml', '<test/>')
    with pytest.raises(ValueError): validate_pptx(bad)


@pytest.mark.parametrize('extension', ['wav', 'mp3', 'm4a', 'mp4', 'flac', 'ogg', 'webm', 'aac', 'opus', 'wma', 'aiff', '3gp', 'amr'])
def test_phone_and_desktop_formats_decode_to_bounded_mono_pcm(tmp_path, extension):
    from src.audio.parts import decode_parts
    source = tmp_path / 'source.wav'
    sf.write(source, .05 * np.sin(np.arange(8000) * 2 * np.pi * 440 / 16000), 16000)
    encoded = tmp_path / ('upload.' + extension)
    codec = ['-c:a', 'aac'] if extension == '3gp' else ['-ar', '8000', '-ac', '1', '-b:a', '12.2k'] if extension == 'amr' else []
    subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-y', '-i', str(source), *codec, str(encoded)],
                   check=True, capture_output=True, timeout=30)
    decoded = decode_parts([str(encoded)], tmp_path / 'normalized.wav')
    info = sf.info(decoded)
    assert info.samplerate == 16000 and info.channels == 1 and info.subtype == 'PCM_16'
    assert .4 <= info.duration <= .7


def test_speaker_count_correction_validates_ownership_revision_and_preserves_source(api_client, monkeypatch):
    api, client = api_client
    auth = register(client, 'correction@example.com'); other = register(client, 'not-owner@example.com')
    source = api.DATA_DIR / 'correct.wav'; sf.write(source, np.zeros(16000), 16000)
    with api.SessionLocal() as db:
        user = db.query(api.User).filter_by(email='correction@example.com').one()
        db.add(api.Meeting(id='correct', user_id=user.id, title='Original title', status='completed',
                          report_data=json.dumps({'transcript_segments': [{'speaker': 'SPEAKER_00'}]})))
        db.commit()
    monkeypatch.setattr('src.audio.diarization.diarization_status', lambda: {'ready': True})
    path = '/api/meetings/correct'; endpoint = path + '/analyze-speakers'
    revision = client.get(path, headers=auth).json()['revision']
    assert client.post(endpoint, headers=auth).status_code == 409
    for count in (0, 51):
        assert client.post(endpoint, headers=auth, json={'num_speakers': count}).status_code == 422
    assert client.post(endpoint, headers=other, json={'num_speakers': 3}).status_code == 404
    assert client.post(endpoint, headers=auth, json={'num_speakers': 3, 'revision': 'stale'}).status_code == 409
    assert client.post(endpoint, headers=auth, json={'num_speakers': 3, 'revision': revision}).status_code == 202
    assert api.job_state('correct')['options']['num_speakers'] == 3
    assert client.get(path, headers=auth).json()['title'] == 'Original title' and source.is_file()
    with api.SessionLocal() as db:
        db.get(api.Meeting, 'correct').status = 'completed'
        db.commit()
    assert client.post(endpoint, headers=auth, json={'automatic': True, 'num_speakers': 3}).status_code == 422
    assert client.post(endpoint, headers=auth, json={'automatic': True}).status_code == 202
    assert 'num_speakers' not in api.job_state('correct')['options']
