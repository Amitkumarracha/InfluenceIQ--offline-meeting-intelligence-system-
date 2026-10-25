"""Source-bound human reviews, portable sync, calendar safety and private edits."""
import copy
import pytest
from src.meeting.followups import action_candidates, active_review, make_review, validate_reviews, calendar_export
from src.report.portable import website_report
from tests.test_api import api_client, register
from tests.test_account_sync import package, publish, audio


def task():
    return {'event_id': 'E2', 'event_type': 'action_item', 'start': .5, 'end': 1,
            'speaker': 'SPEAKER_00', 'text': 'कल report भेज देना।'}


def test_review_keeps_owner_separate_and_abstains_after_changed_analysis():
    action = task()
    report = {'events': [action]}
    original = copy.deepcopy(report)
    review = make_review(action, 'रवि', '2026-10-20', 'open')
    assert report == original and action['speaker'] == 'SPEAKER_00'
    report['action_reviews'] = {'E2': review}
    validate_reviews(report)
    assert active_review(report, action)['owner'] == 'रवि'
    assert active_review(report, dict(action, text='A different commitment')) is None
    assert active_review(report, dict(action, start=.6)) is None
    assert active_review(report, dict(action, event_id='E9')) is None
    legacy = dict(action, start=None)
    assert make_review(legacy)['source_start'] is None
    for owner, due, state in [('x\r\nATTENDEE:evil', '', 'open'), ('x'*101, '', 'open'), ('', '2026-02-30', 'open'),
                              ('', '2026-1-2', 'open'), ('', '9999-12-31', 'open'), ('', '', 'guessed'), ('', '', [])]:
        with pytest.raises(ValueError): make_review(action, owner, due, state)


def test_calendar_requires_review_and_explicit_date_and_folds_utf8_safely():
    action = dict(task(), text='रिपोर्ट; भेजना, ' * 20 + '\nATTENDEE:unsafe@example.com')
    report = {'events': [action]}
    with pytest.raises(ValueError): calendar_export(report, 'Planning', 'm1')
    report['action_reviews'] = {'E2': make_review(action, 'रवि', '2026-12-31', 'open')}
    text = calendar_export(report, 'Planning\nBEGIN:VEVENT', 'm1')
    lines = text.split('\r\n')
    assert all(len(line.encode()) <= 75 for line in lines)
    unfolded = text.replace('\r\n ', '')
    assert text.count('BEGIN:VEVENT\r\n') == 1
    assert 'DTSTART;VALUE=DATE:20261231' in text and 'DTEND;VALUE=DATE:20270101' in text
    assert '\r\nATTENDEE:' not in unfolded and '\\nATTENDEE:' in unfolded
    assert '\\;' in unfolded and '\\,' in unfolded
    uid = next(line for line in lines if line.startswith('UID:'))
    assert uid in calendar_export(report, 'Renamed', 'm1')
    assert uid not in calendar_export(report, 'Renamed', 'm2')
    for state, due in [('done', '2026-10-20'), ('dismissed', '2026-10-20'), ('open', '')]:
        report['action_reviews']['E2'] = make_review(action, '', due, state)
        with pytest.raises(ValueError): calendar_export(report, 'Planning', 'm1')


def test_sync_validates_and_preserves_review_metadata_without_inventing_it():
    source = package()['report']
    action = task(); source['events'].append(action)
    assert 'action_reviews' not in website_report(source)
    source['action_reviews'] = {'E2': make_review(action, 'रवि', '2026-10-20', 'open')}
    translated = website_report(source)
    assert active_review(translated, action_candidates(translated)['E2']) == source['action_reviews']['E2']
    source['action_reviews']['E2']['due_date'] = 'tomorrow'
    with pytest.raises(ValueError): website_report(source)
    source['action_reviews'] = []
    with pytest.raises(ValueError): website_report(source)


def test_private_revision_checked_task_edits_exports_and_native_round_trip(api_client):
    api, client = api_client
    auth = register(client, 'tasks@example.com'); other = register(client, 'other@example.com')
    body = package(); body['report']['events'].append(task())
    published = publish(client, auth, body, audio()).json(); mid = published['id']
    endpoint = f'/api/meetings/{mid}/actions/E2'
    values = {'revision': published['revision'], 'owner': 'रवि', 'due_date': '2026-10-20', 'state': 'open'}
    assert client.get(f'/api/meetings/{mid}/export?format=ics', headers=auth).status_code == 422
    assert client.post(endpoint, headers=other, json=values).status_code == 404
    assert client.post(endpoint, json=values).status_code in (401, 403)
    assert client.post(endpoint.replace('E2', 'unknown'), headers=auth, json=values).status_code == 404
    assert client.post(endpoint, headers=auth, json=dict(values, due_date='2026-02-30')).status_code == 422
    before = client.get(f'/api/meetings/{mid}', headers=auth).json()['data']
    saved = client.post(endpoint, headers=auth, json=values)
    assert saved.status_code == 200, saved.text
    assert client.post(endpoint, headers=auth, json=values).status_code == 409
    reviewed = client.get(f'/api/meetings/{mid}', headers=auth).json()
    assert reviewed['data']['event_timeline'] == before['event_timeline']
    assert reviewed['data']['transcript_segments'] == before['transcript_segments']
    assert reviewed['data']['action_items'][0]['speaker'] == 'SPEAKER_00'
    ics = client.get(f'/api/meetings/{mid}/export?format=ics', headers=auth)
    assert ics.status_code == 200 and 'text/calendar' in ics.headers['content-type']
    assert 'SUMMARY:कल report भेज देना।' in ics.text  # Preserve mixed-language source, without translation.
    assert 'Owner: रवि' in ics.text.replace('\r\n ', '')
    assert 'due: 2026-10-20' in client.get(f'/api/meetings/{mid}/export?format=md', headers=auth).text
    # A native download/republication retains reviews; explicit local task edits update them.
    body.update(remote_id=mid, base_revision=reviewed['revision'], report=reviewed['data'])
    body['report']['action_reviews']['E2']['state'] = 'done'
    returned = publish(client, auth, body)
    assert returned.status_code == 200, returned.text
    assert client.get(f'/api/meetings/{mid}/export?format=ics', headers=auth).status_code == 422
    with api.SessionLocal() as db: assert db.query(api.Meeting).count() == 1


def test_reanalysis_keeps_manual_history_but_does_not_apply_it_to_changed_evidence(api_client, monkeypatch, tmp_path):
    from src.audio import parts
    from src.pipeline import orchestrator
    api, client = api_client
    auth = register(client, 'rerun@example.com')
    body = package(); action = task(); body['report']['events'].append(action)
    published = publish(client, auth, body, audio()).json(); mid = published['id']
    values = {'revision': published['revision'], 'owner': 'Ravi', 'due_date': '2026-10-20', 'state': 'open'}
    assert client.post(f'/api/meetings/{mid}/actions/E2', headers=auth, json=values).status_code == 200
    with api.SessionLocal() as db: user_id = db.get(api.Meeting, mid).user_id
    next_report = website_report(body['report'])
    next_report['action_items'][0]['text'] = 'A different action at the same position'
    path = tmp_path / 'new-report.json'
    import json
    path.write_text(json.dumps(next_report))
    api.atomic_json(api.job_path(mid), {'audio': ['preserved.wav']})
    monkeypatch.setattr(parts, 'decode_parts', lambda *args, **kwargs: 'preserved.wav')
    monkeypatch.setattr(orchestrator, 'run_meeting', lambda *args: path)
    api.run_pipeline_background(user_id, mid)
    after = client.get('/api/meetings/' + mid, headers=auth).json()
    assert after['status'] == 'completed'
    assert after['data']['action_reviews']['E2']['owner'] == 'Ravi'
    assert active_review(after['data'], after['data']['action_items'][0]) is None
