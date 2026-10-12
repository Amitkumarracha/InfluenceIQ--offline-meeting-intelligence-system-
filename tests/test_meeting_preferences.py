"""Saved meeting edits and profiles remain private and survive later report updates."""
import json
from tests.test_api import api_client, register
from src.meeting.vocabulary import suggest_vocabulary


def test_profile_and_meeting_metadata_are_private_and_exported(api_client):
    api, client = api_client
    owner = register(client, 'simple@example.com')
    other = register(client, 'other-simple@example.com')
    assert client.post('/api/profile', headers=owner, json={'name': 'Asha', 'role': 'Researcher', 'organization': 'Local'}).status_code == 200
    assert client.get('/api/profile', headers=owner).json()['name'] == 'Asha'
    assert client.get('/api/profile', headers=other).json()['name'] == ''
    assert client.get('/api/profile').status_code in {401, 403}
    source = {'transcript_segments': [{'segment_id': 1, 'speaker': 'SPEAKER_00', 'start': 1, 'end': 4, 'text': 'Asha discussed the budget.'}]}
    with api.SessionLocal() as db:
        user = db.query(api.User).filter_by(email='simple@example.com').one()
        db.add(api.Meeting(id='saved_simple', user_id=user.id, title='Planning', status='completed', report_data=json.dumps(source)))
        db.commit()
    edits = {'speaker_names': {'SPEAKER_00': 'Asha'}, 'speaker_roles': {'SPEAKER_00': 'Reviewer'}, 'vocabulary': 'Asha, budget'}
    path = '/api/meetings/saved_simple'
    assert client.post(path + '/edit', headers=other, json=edits).status_code == 404
    assert client.post(path + '/edit', headers=owner, json=edits).status_code == 200
    data = client.get(path, headers=owner).json()['data']
    assert all(data[key] == value for key, value in edits.items())
    assert 'budget' in data['vocabulary_suggestions']
    markdown = client.get(path + '/export?format=md', headers=owner).text
    assert 'Asha: Reviewer' in markdown and 'Asha, budget' in markdown
    assert client.post(path + '/edit', headers=owner, json={'speaker_roles': {'UNKNOWN': 'Leader'}}).status_code == 422
    assert client.post(path + '/edit', headers=owner, json={'vocabulary': 'x' * 1001}).status_code == 422
    with api.SessionLocal() as db:
        meeting = db.get(api.Meeting, 'saved_simple')
        data = json.loads(meeting.report_data)
        data['local_notes'] = {'overview': []}
        meeting.report_data = json.dumps(data)
        db.commit()
    assert client.get(path, headers=owner).json()['data']['speaker_roles'] == edits['speaker_roles']


def test_vocabulary_uses_observed_unicode_terms_without_numeric_or_common_words():
    suggestions = suggest_vocabulary([{'text': 'Budget budget बजट हिंदी. We will send the report 2026.'}])
    assert suggestions[0] == 'budget'
    assert 'बजट' in suggestions and 'हिंदी' in suggestions
    assert not {'will', 'report', '2026'} & set(suggestions)
    assert suggest_vocabulary([]) == []
