import io
import json
import zipfile

import numpy as np
import pytest
import soundfile as sf

from scripts.package_huggingface import FILES, package_backend
from tests.test_api import api_client, register


def test_separate_frontend_cors_and_private_audio(monkeypatch, request):
    origin = 'https://meetiq-test.onrender.com'
    monkeypatch.setenv('MAI_ALLOWED_ORIGINS', origin)
    monkeypatch.setenv('MAI_PUBLIC_URL', 'https://meetiq-test.hf.space/')
    api, client = request.getfixturevalue('api_client')
    preflight = {'Origin': origin, 'Access-Control-Request-Method': 'POST',
                 'Access-Control-Request-Headers': 'authorization,content-type'}
    response = client.options('/api/analyze', headers=preflight)
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == origin
    assert client.options('/api/analyze', headers={**preflight, 'Origin': 'https://untrusted.invalid'}).status_code == 400

    owner = register(client, 'cloud-owner@example.com')
    other = register(client, 'cloud-other@example.com')
    payload = io.BytesIO()
    sf.write(payload, np.zeros(16000), 16000, format='WAV')
    uploaded = client.post('/api/analyze', headers={**owner, 'Origin': origin},
                           files={'audio': ('meeting.wav', payload.getvalue(), 'audio/wav')})
    assert uploaded.status_code == 202
    assert uploaded.headers['access-control-allow-origin'] == origin
    mid = uploaded.json()['meeting_id']
    with api.SessionLocal() as db:
        meeting = db.get(api.Meeting, mid)
        meeting.status = 'completed'
        meeting.report_data = json.dumps({'transcript_segments': []})
        db.commit()
    (api.DATA_DIR / (mid + '.wav')).write_bytes(payload.getvalue())
    result = client.get('/api/meetings/' + mid, headers=owner).json()
    assert result['audio_url'].startswith(f'https://meetiq-test.hf.space/api/meetings/{mid}/audio?token=')
    assert client.get(result['audio_url'], headers={'Origin': origin}).content == payload.getvalue()
    assert client.get('/api/meetings/' + mid, headers=other).status_code == 404
    media_token = result['audio_url'].split('token=')[1]
    assert client.get('/api/meetings/wrong/audio?token=' + media_token).status_code == 401


def test_package_contains_backend_and_model_without_private_state(tmp_path):
    root = tmp_path / 'project'
    names = [*FILES, 'backend/api.py', 'src/__init__.py', 'src/audio/asr.py',
             'config/.env', 'backend/.env', 'src/private.env', 'data/state/private.db',
             '.runtime/jwt-secret', 'frontend/src/App.jsx', 'outputs/private.json',
             'models/hf/large-model.bin', 'src/__pycache__/private.pyc']
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name)
    destination = package_backend(root, tmp_path / 'packages')
    with zipfile.ZipFile(destination.with_suffix('.zip')) as archive:
        files = {name for name in archive.namelist() if not name.endswith('/')}
    expected = {*FILES.values(), 'backend/api.py', 'src/__init__.py', 'src/audio/asr.py'}
    assert files == expected
    assert (destination / 'README.md').read_text() == 'deployment/huggingface/README.md'
    assert (root / '.runtime/jwt-secret').read_text() == '.runtime/jwt-secret'


@pytest.mark.parametrize('invalid_model', ['missing', 'symlink'])
def test_package_rejects_missing_or_linked_trained_model(tmp_path, invalid_model):
    root = tmp_path / 'project'
    for name in [*FILES, 'backend/api.py', 'src/__init__.py']:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    (root / 'models/discussion/model.joblib').unlink()
    if invalid_model == 'symlink':
        private = tmp_path / 'private-file'
        private.write_text('not a model')
        (root / 'models/discussion/model.joblib').symlink_to(private)
    with pytest.raises(ValueError, match='model.joblib'):
        package_backend(root, tmp_path / 'packages')
    assert not (tmp_path / 'packages').exists()
