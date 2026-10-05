"""Exercise authentication, ownership, upload validation and durable job scheduling."""
import importlib
import io
import json
import sys
from concurrent.futures import Future
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    monkeypatch.setenv('MAI_RUNTIME_DIR', str(tmp_path / 'runtime'))
    monkeypatch.setenv('MAI_DB_PATH', str(tmp_path / 'test.db'))
    monkeypatch.setenv('MAI_DATA_DIR', str(tmp_path / 'audio'))
    sys.modules.pop('api', None)
    api = importlib.import_module('api')
    with TestClient(api.app) as client:
        # Keep jobs queued; integration tests run the real worker separately.
        monkeypatch.setattr(api.app.state.executor, 'submit', lambda *args: Future())
        yield api, client
    api.engine.dispose()
    sys.modules.pop('api', None)


def register(client, email):
    response = client.post('/api/auth/register', json={'email': email, 'password': 'test-password'})
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['token']}


def test_private_audio_and_cross_account_access(api_client):
    api, client = api_client
    owner = register(client, 'owner@example.com')
    other = register(client, 'other@example.com')
    payload = io.BytesIO()
    sf.write(payload, np.zeros(16000), 16000, format='WAV')
    response = client.post('/api/analyze', headers=owner, files={'audio': ('meeting.wav', payload.getvalue(), 'audio/wav')})
    assert response.status_code == 202
    mid = response.json()['meeting_id']
    assert api.job_path(mid).exists()
    assert client.get('/api/meetings/' + mid, headers=other).status_code == 404
    assert client.get('/api/meetings/' + mid).status_code in {401, 403}
    with api.SessionLocal() as db:
        meeting = db.get(api.Meeting, mid)
        meeting.status = 'completed'
        meeting.report_data = '{"transcript_segments": []}'
        db.commit()
    (api.DATA_DIR / (mid + '.wav')).write_bytes(payload.getvalue())
    info = client.get('/api/meetings/' + mid, headers=owner).json()
    assert client.get(info['audio_url']).status_code == 200
    token = info['audio_url'].split('token=')[1]
    assert client.get('/api/meetings', headers={'Authorization': 'Bearer ' + token}).status_code == 401
    assert client.get('/api/meetings/another/audio?token=' + token).status_code == 401
    assert client.get('/media/' + mid + '.wav').status_code == 404


def test_rejects_invalid_and_oversized_uploads(api_client, monkeypatch):
    api, client = api_client
    auth = register(client, 'owner@example.com')
    assert client.post('/api/analyze', headers=auth, files={'audio': ('bad.wav', b'not audio')}).status_code == 422
    assert client.post('/api/analyze', headers=auth, files={'audio': ('bad.exe', b'anything')}).status_code == 415
    monkeypatch.setattr(api, 'MAX_UPLOAD_BYTES', 5)
    assert client.post('/api/analyze', headers=auth, files={'audio': ('big.wav', b'123456')}).status_code == 413
    assert not list((api.RUNTIME / 'uploads').glob('*'))


def test_password_reset_never_returns_takeover_token(api_client):
    _, client = api_client
    register(client, 'owner@example.com')
    response = client.post('/api/auth/forgot-password', json={'email': 'owner@example.com'})
    assert response.status_code == 403
    assert 'dev_token' not in response.json()
    assert client.post('/api/auth/register', json={'email': 'hi@example.com', 'password': 'अ'*30}).status_code == 422
