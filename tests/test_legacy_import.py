"""Legacy imports preserve current users/history, source files and ownership."""
import json
from pathlib import Path
import sqlite3
import bcrypt
import pytest
from scripts.import_legacy_history import import_history
from tests.test_account_sync import audio


def database(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.executescript('CREATE TABLE users(id TEXT PRIMARY KEY,email TEXT UNIQUE,password_hash TEXT,reset_token TEXT); CREATE TABLE meetings(id TEXT PRIMARY KEY,user_id TEXT,title TEXT,status TEXT,report_data TEXT,created_at TEXT);')
    return db


def fixture(tmp_path):
    source, main = tmp_path/'old', tmp_path/'main'
    db = database(source/'nexus_v2.db')
    password_hash = bcrypt.hashpw(b'legacy-password', bcrypt.gensalt(rounds=4)).decode()
    db.execute('INSERT INTO users VALUES(?,?,?,NULL)', ('legacy', 'Legacy@Example.com', password_hash))
    for mid, status, report in [('old1', 'completed', json.dumps({'meeting_overview': {'duration_s': 1}})), ('old2', 'failed', None)]:
        db.execute('INSERT INTO meetings VALUES(?,?,?,?,?,?)', (mid, 'legacy', 'Historical meeting', status, report, '2026-09-26 12:00:00'))
        path = source/'data/custom_test'/(mid+'.wav'); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(audio())
    db.commit(); db.close()
    db = database(main/'data/state/nexus_v2.db')
    db.execute('INSERT INTO users VALUES(?,?,?,NULL)', ('current', 'current@example.com', 'keep-current-password'))
    db.execute('INSERT INTO meetings VALUES(?,?,?,?,?,?)', ('current1', 'current', 'Keep this', 'completed', '{}', '2026-10-01'))
    db.commit(); db.close()
    return source, main, password_hash


def test_import_backup_ownership_passwords_source_and_idempotency(tmp_path):
    source, main, original_hash = fixture(tmp_path)
    original_source = (source/'nexus_v2.db').read_bytes()
    assert not import_history(source, main)['applied']
    result = import_history(source, main, apply=True)
    assert result['users_added'] == 1 and result['meetings_added'] == 2
    backup = sqlite3.connect(main/result['backup']/'before.sqlite3')
    assert backup.execute('SELECT count(*) FROM users').fetchone()[0] == 1
    backup.close()
    db = sqlite3.connect(main/'data/state/nexus_v2.db')
    assert db.execute('SELECT password_hash FROM users WHERE id="current"').fetchone()[0] == 'keep-current-password'
    assert db.execute('SELECT password_hash FROM users WHERE id="legacy"').fetchone()[0] == original_hash
    assert db.execute('SELECT user_id FROM meetings WHERE id="old1"').fetchone()[0] == 'legacy'
    report = json.loads(db.execute('SELECT report_data FROM meetings WHERE id="old1"').fetchone()[0])
    assert report['processing']['legacy_transcript_missing'] and not report['transcript_segments']
    db.close()
    job = json.loads((main/'.runtime/jobs/old2.json').read_text())
    assert job['stage'] == 'failed' and Path(job['audio'][0]).read_bytes() == audio()
    assert (source/'nexus_v2.db').read_bytes() == original_source
    again = import_history(source, main, apply=True)
    assert again['users_added'] == again['meetings_added'] == 0
    assert again['meetings_already_present'] == 2


@pytest.mark.parametrize('collision', ['email', 'audio'])
def test_import_rejects_collisions_without_changing_current_history(tmp_path, collision):
    source, main, _ = fixture(tmp_path)
    if collision == 'email':
        db = sqlite3.connect(main/'data/state/nexus_v2.db')
        db.execute('UPDATE users SET email="legacy@example.com"'); db.commit(); db.close()
    else:
        audio_path = main/'data/custom_test/old1.wav'; audio_path.parent.mkdir(parents=True); audio_path.write_bytes(b'preserve this different audio')
    before = (main/'data/state/nexus_v2.db').read_bytes()
    with pytest.raises(ValueError, match='collision'):
        import_history(source, main, apply=True)
    assert (main/'data/state/nexus_v2.db').read_bytes() == before
    if collision == 'audio':
        assert (main/'data/custom_test/old1.wav').read_bytes() == b'preserve this different audio'


def test_failed_database_insert_rolls_back_only_new_import_files(tmp_path):
    source, main, _ = fixture(tmp_path)
    db = sqlite3.connect(main/'data/state/nexus_v2.db')
    db.execute("CREATE TRIGGER reject_import BEFORE INSERT ON meetings WHEN NEW.id='old2' BEGIN SELECT RAISE(ABORT,'test failure'); END")
    db.commit(); db.close()
    with pytest.raises(sqlite3.IntegrityError):
        import_history(source, main, apply=True)
    db = sqlite3.connect(main/'data/state/nexus_v2.db')
    assert db.execute('SELECT count(*) FROM users').fetchone()[0] == 1
    assert db.execute('SELECT count(*) FROM meetings').fetchone()[0] == 1
    db.close()
    assert not list((main/'data/custom_test').glob('old*.wav'))
    assert not list((main/'.runtime/jobs').glob('old*.json'))


def test_manifest_error_after_commit_keeps_imported_recordings(tmp_path, monkeypatch):
    source, main, _ = fixture(tmp_path)
    original = Path.write_text
    def write(path, *args, **kwargs):
        if path.name == 'manifest.json':
            raise OSError('Simulated manifest write failure')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'write_text', write)
    with pytest.raises(OSError):
        import_history(source, main, apply=True)
    assert (main/'data/custom_test/old1.wav').read_bytes() == audio()
    db = sqlite3.connect(main/'data/state/nexus_v2.db')
    assert db.execute('SELECT count(*) FROM meetings').fetchone()[0] == 3
    db.close()
