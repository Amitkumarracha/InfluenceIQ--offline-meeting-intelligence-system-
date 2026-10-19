"""Same account, portable native reports, ownership and safe sync retries."""
import io
import json
import uuid
import wave
import struct
from tests.test_api import api_client, register


def audio():
    output = io.BytesIO()
    with wave.open(output, 'wb') as stream:
        stream.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        stream.writeframes(b'\0\0' * 16000)
    return output.getvalue()


def package():
    return {'client_key': str(uuid.uuid4()), 'title': 'Hindi English planning', 'report': {
        'completed': True, 'duration': 1, 'language': 'hi',
        'transcript_segments': [{'segment_id': 1, 'start': 0, 'end': 1, 'speaker': 'SPEAKER_00', 'text': 'हमने budget approve किया।'}],
        'participants': [{'speaker': 'SPEAKER_00', 'roles': ['Decision contributor'], 'speaking_time_s': 1}],
        'speaker_names': {'SPEAKER_00': 'Asha'}, 'speaker_roles': {'SPEAKER_00': 'Lead'},
        'events': [{'event_id': 'E1', 'event_type': 'decision', 'start': 0, 'end': 1, 'speaker': 'SPEAKER_00', 'text': 'Budget approve किया।'}],
        'decisions': [{'decision_id': 'D1', 'text': 'Budget approve किया।', 'requires_review': True}],
        'influence': [{'participant': 'SPEAKER_00', 'influence_score': .15, 'raw_features': {'decision': 1}, 'normalised_features': {'decision': 1}, 'explanation': ['Candidate contribution']}],
        'slides': [{'slide_id': 'slide_1', 'slide_number': 1, 'text': 'Budget 500'}],
        'aligned_segments': [{'segment_id': 1, 'selected_slide': 1, 'score': .5}], 'interactions': []}}


def publish(client, auth, body, recording=None):
    files = {'payload': ('report.json', json.dumps(body, ensure_ascii=False).encode(), 'application/json')}
    if recording is not None:
        files['audio'] = ('audio.wav', recording, 'audio/wav')
    return client.post('/api/sync/meetings', headers=auth, files=files)


def test_shared_account_profile_history_native_report_and_exports(api_client):
    api, client = api_client
    web = register(client, ' Shared@Example.com ')
    app = client.post('/api/auth/login', json={'email': 'shared@example.com', 'password': 'test-password'}).json()
    auth = {'Authorization': 'Bearer ' + app['token']}
    assert client.get('/api/auth/me', headers=web).json() == {'email': app['email'], 'user_id': app['user_id']}
    assert client.get('/api/auth/me').status_code in (401, 403)
    profile = {'name': 'आशा', 'role': 'Lead', 'organization': 'Community'}
    assert client.post('/api/profile', headers=web, json=profile).status_code == 200
    assert client.get('/api/profile', headers=auth).json()['name'] == 'आशा'
    body = package()
    response = publish(client, auth, body, audio())
    assert response.status_code == 200, response.text
    mid = response.json()['id']
    assert client.get('/api/meetings', headers=web).json()['meetings'][0]['id'] == mid
    saved = client.get('/api/meetings/' + mid, headers=web).json()
    assert saved['revision'] == response.json()['revision']
    data = saved['data']
    assert data['participants'][0]['speaker_id'] == 'SPEAKER_00'
    assert data['slides'][0]['text'] == ['Budget 500']
    assert data['aligned_segments'][0]['slide_id'] == 'slide_1'
    assert data['meeting_overview']['duration_s'] == 1
    assert data['decisions'][0]['status'] == 'candidate'
    assert data['influence'][0]['raw_features']['decision_contribution'] == 1
    for format in ['json', 'md', 'txt', 'csv', 'srt', 'vtt']:
        exported = client.get(f'/api/meetings/{mid}/export?format={format}', headers=web)
        assert exported.status_code == 200, exported.text
    assert client.get(f'/api/sync/meetings/{mid}/audio', headers=auth).content == audio()
    import jwt
    expired = jwt.encode({'sub': app['user_id'], 'purpose': 'access', 'exp': 0}, api.SECRET_KEY, algorithm='HS256')
    expired_auth = {'Authorization': 'Bearer ' + expired}
    assert client.get('/api/auth/me', headers=expired_auth).status_code == 401
    assert client.get(f'/api/sync/meetings/{mid}/audio', headers=expired_auth).status_code == 401


def test_sync_idempotency_conflicts_and_account_isolation(api_client):
    api, client = api_client
    owner, other = register(client, 'owner@example.com'), register(client, 'other@example.com')
    body = package()
    original = publish(client, owner, body, audio()).json()
    assert publish(client, owner, body, audio()).json() == original
    assert len(client.get('/api/meetings', headers=owner).json()['meetings']) == 1
    mid = original['id']
    body.update(remote_id=mid, base_revision=original['revision'])
    body['title'] = 'Phone title'
    updated = publish(client, owner, body)
    assert updated.status_code == 200
    assert updated.json()['id'] == mid
    client.post(f'/api/meetings/{mid}/edit', headers=owner, json={'title': 'Website correction'})
    assert publish(client, owner, body).status_code == 409
    assert client.get('/api/meetings/' + mid, headers=owner).json()['title'] == 'Website correction'
    assert client.get(f'/api/sync/meetings/{mid}/audio', headers=other).status_code == 404
    assert publish(client, other, body, audio()).status_code == 404
    with api.SessionLocal() as db:
        assert db.query(api.Meeting).count() == 1
    assert not list(api.DATA_DIR.glob('sync-*.tmp'))


def test_sync_rejects_bad_packages_audio_and_limits_without_creating_records(api_client, monkeypatch):
    api, client = api_client
    auth = register(client, 'owner@example.com')
    body = package()
    assert publish(client, auth, body).status_code == 422
    assert publish(client, auth, body, b'fake WAV').status_code == 422
    body['report']['transcript_segments'][0]['end'] = -1
    assert publish(client, auth, body, audio()).status_code == 422
    body = package(); body['report']['completed'] = False
    assert publish(client, auth, body, audio()).status_code == 422
    body = package(); body['report']['duration'] = 100
    assert publish(client, auth, body, audio()).status_code == 422
    body = package(); body['report']['participants'][0]['roles'] = 'malformed'
    assert publish(client, auth, body, audio()).status_code == 422
    monkeypatch.setattr(api, 'MAX_UPLOAD_BYTES', 100)
    assert publish(client, auth, package(), audio()).status_code == 413
    with api.SessionLocal() as db:
        assert db.query(api.Meeting).count() == db.query(api.SyncLink).count() == 0
    assert not list(api.DATA_DIR.glob('sync-*.tmp'))


def test_republish_compares_pcm_not_wav_metadata_and_preserves_server_audio(api_client):
    api, client = api_client
    auth = register(client, 'owner@example.com')
    body = package()
    saved = publish(client, auth, body, audio()).json()
    mid = saved['id']
    canonical = audio()
    # ffmpeg and desktop files can include extra RIFF chunks; Android rewrites the header.
    extended = canonical[:12] + b'JUNK' + struct.pack('<I', 4) + b'test' + canonical[12:]
    extended = extended[:4] + struct.pack('<I', len(extended) - 8) + extended[8:]
    path = api.DATA_DIR / (mid + '.wav')
    path.write_bytes(extended)
    body.update(remote_id=mid, base_revision=saved['revision'], title='Reviewed on Android')
    response = publish(client, auth, body, canonical)
    assert response.status_code == 200, response.text
    assert path.read_bytes() == extended
    changed = canonical[:-2] + b'\x01\x00'
    assert publish(client, auth, body, changed).status_code == 409
    assert path.read_bytes() == extended


def test_concurrent_publication_retries_create_one_meeting(api_client):
    from concurrent.futures import ThreadPoolExecutor
    api, client = api_client
    auth = register(client, 'owner@example.com')
    body = package()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: publish(client, auth, body, audio()), range(2)))
    assert [result.status_code for result in results] == [200, 200]
    assert results[0].json() == results[1].json()
    with api.SessionLocal() as db:
        assert db.query(api.Meeting).count() == db.query(api.SyncLink).count() == 1
    assert not list(api.DATA_DIR.glob('sync-*.tmp'))
