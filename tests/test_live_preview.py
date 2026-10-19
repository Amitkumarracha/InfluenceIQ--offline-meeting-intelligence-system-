"""Preview safety, scheduling and bounded audio; no production accounts or neural downloads."""
import io
from concurrent.futures import Future
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest
import soundfile as sf

from tests.test_api import api_client, register
from src.audio.live import decode_preview, transcribe_preview


def wav(seconds=1, rate=16000):
    stream = io.BytesIO()
    sf.write(stream, np.zeros(int(seconds * rate)), rate, format='WAV', subtype='PCM_16')
    return stream.getvalue()


def test_preview_audio_contract():
    assert decode_preview(wav()).shape == (16000,)
    for payload in (wav(.5), wav(31), wav(1, 8000), wav()[:-4]):
        with pytest.raises(ValueError):
            decode_preview(payload)


def test_diarization_evaluation_uses_explicit_recording_interval():
    from src.evaluation.metrics import calculate_der
    reference = [{'start': 0, 'end': 1, 'speaker': 'A'}]
    hypothesis = reference + [{'start': 2, 'end': 3, 'speaker': 'A'}]
    assert calculate_der(reference, hypothesis, collar=0, duration=1)['der'] == 0
    assert calculate_der(reference, hypothesis, collar=0, duration=3)['der'] == 1
    with pytest.raises(ValueError):
        calculate_der(reference, hypothesis, duration=float('nan'))


def test_preview_reuses_local_model_and_abstains_from_speakers():
    model = SimpleNamespace(transcribe=lambda *a, **k: (iter([SimpleNamespace(start=0, end=1, text=' नमस्ते team ')]), SimpleNamespace(language='hi')))
    with patch('src.audio.asr._load_whisper_model', return_value=model):
        result = transcribe_preview(np.zeros(16000), 'small', 'auto', '')
    assert result['segments'][0]['text'] == 'नमस्ते team'
    assert result['segments'][0]['speaker'] == 'UNKNOWN'
    assert result['draft'] and result['language'] == 'hi'


def test_preview_auto_language_obeys_same_allowed_languages_as_final_analysis():
    calls = []
    def transcribe(samples, **options):
        calls.append(options)
        return iter([]), SimpleNamespace(language=options['language'] or 'ur',
            all_language_probs=[('ur', .7), ('hi', .2), ('en', .1)])
    with patch('src.audio.asr._load_whisper_model', return_value=SimpleNamespace(transcribe=transcribe)):
        result = transcribe_preview(np.zeros(16000), 'small', 'auto', '')
    assert result['language'] == 'hi' and len(calls) == 2


def test_preview_auth_validation_and_backpressure(api_client, monkeypatch):
    api, client = api_client
    url = '/api/recording/preview'
    files = {'audio': ('preview.wav', wav(), 'audio/wav')}
    assert client.post(url, files=files).status_code in {401, 403}
    auth = register(client, 'preview@example.com')
    assert client.post(url, headers=auth, files={'audio': ('bad.wav', b'bad')}).status_code == 422
    assert client.post(url, headers=auth, files=files, data={'language': 'invalid'}).status_code == 422
    assert client.post(url, headers=auth, files={'audio': ('large.wav', wav(31))}).status_code == 413
    api.preview_lock.acquire()
    try:
        assert client.post(url, headers=auth, files=files).status_code == 429
    finally:
        api.preview_lock.release()
    def submit(fn, *args):
        future = Future(); future.set_result({'segments': [], 'draft': True, 'language': 'en'}); return future
    monkeypatch.setattr(api.app.state.executor, 'submit', submit)
    assert client.post(url, headers=auth, files=files).json()['draft']
    assert not api.preview_lock.locked()
    with api.SessionLocal() as db:
        db.add(api.Meeting(id='pending', user_id='other', status='processing'))
        db.commit()
    assert client.post(url, headers=auth, files=files).status_code == 429
