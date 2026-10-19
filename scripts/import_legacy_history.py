"""Import local legacy accounts/history additively; dry-run unless --apply is set."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import uuid


def _digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value):
        raise ValueError('Invalid legacy identifier')
    return value


def _copy_new(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + '.import-' + uuid.uuid4().hex)
    try:
        with source.open('rb') as incoming, temporary.open('xb') as outgoing:
            shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
            outgoing.flush(); os.fsync(outgoing.fileno())
        temporary.chmod(0o600)
        os.link(temporary, destination)  # Atomic installation that cannot overwrite an existing file.
    finally:
        temporary.unlink(missing_ok=True)


def import_history(source_root, project_root, apply=False):
    source_root, project_root = Path(source_root).resolve(), Path(project_root).resolve()
    source_db, target_db = source_root / 'nexus_v2.db', project_root / 'data/state/nexus_v2.db'
    if not source_db.is_file() or not target_db.is_file() or source_db.resolve() == target_db.resolve():
        raise ValueError('Supply distinct existing source and main databases')
    source = sqlite3.connect(source_db.as_uri() + '?mode=ro', uri=True)
    target = sqlite3.connect(target_db.as_uri() + '?mode=rw', uri=True, timeout=30)
    source.row_factory = target.row_factory = sqlite3.Row
    installed, backup = [], None
    try:
        if source.execute('PRAGMA quick_check').fetchone()[0] != 'ok' or target.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('Database integrity check failed')
        users = list(source.execute('SELECT id,email,password_hash FROM users'))
        meetings = list(source.execute('SELECT id,user_id,title,status,report_data,created_at FROM meetings'))
        existing_users = {row['id']: row for row in target.execute('SELECT id,email FROM users')}
        existing_emails = {row['email'].strip().lower(): row['id'] for row in existing_users.values()}
        existing_meetings = {row['id']: row['user_id'] for row in target.execute('SELECT id,user_id FROM meetings')}
        source_users = {_identifier(row['id']) for row in users}
        additions, reports, files, jobs, warnings = [], [], [], {}, 0
        for row in users:
            email = row['email'].strip().lower()
            if '@' not in email or len(email) > 254:
                raise ValueError('Legacy account has an invalid email')
            if email in existing_emails and existing_emails[email] != row['id']:
                raise ValueError('Account email collision; no accounts were merged or overwritten')
            if row['id'] in existing_users:
                if existing_users[row['id']]['email'].strip().lower() != email:
                    raise ValueError('Account ID collision')
                continue
            if not isinstance(row['password_hash'], str) or not re.fullmatch(r'\$2[aby]\$(0[4-9]|1[0-6])\$[./A-Za-z0-9]{53}', row['password_hash']):
                raise ValueError('Unsupported legacy password hash')
            additions.append((row['id'], email, row['password_hash']))
            existing_emails[email] = row['id']
        for row in meetings:
            mid, owner = _identifier(row['id']), _identifier(row['user_id'])
            if owner not in source_users:
                raise ValueError('Legacy meeting has no source owner')
            if mid in existing_meetings:
                if existing_meetings[mid] != owner:
                    raise ValueError('Meeting owner collision')
                continue
            candidates = [folder / 'data/custom_test' / (mid + '.wav') for folder in (source_root, source_root/'laptop_backup')]
            audio = next((path for path in candidates if path.is_file()), None)
            if audio is None or not audio.resolve().is_relative_to(source_root):
                raise ValueError('A legacy recording is missing or points outside the source folder')
            with audio.open('rb') as stream:
                header = stream.read(12)
            if header[:4] != b'RIFF' or header[8:12] != b'WAVE':
                raise ValueError('Legacy recording is not a WAV file')
            audio_target = project_root / 'data/custom_test' / (mid + '.wav')
            files.append((audio, audio_target))
            data = json.loads(row['report_data']) if row['report_data'] else None
            status = row['status'] if row['status'] in {'completed', 'failed'} else 'failed'
            if status == 'completed' and not isinstance(data, dict):
                raise ValueError('Completed legacy meeting has no readable report')
            if data is not None:
                if not isinstance(data, dict):
                    raise ValueError('Invalid legacy report')
                processing = data.setdefault('processing', {})
                processing['legacy_import'] = True
                if 'transcript_segments' not in data:
                    transcript = next((folder/'data/processed/audio'/(mid+'_transcript.json') for folder in (source_root, source_root/'laptop_backup')
                                       if (folder/'data/processed/audio'/(mid+'_transcript.json')).is_file()), None)
                    if transcript is not None:
                        if not transcript.resolve().is_relative_to(source_root):
                            raise ValueError('Transcript points outside the source folder')
                        data['transcript_segments'] = json.loads(transcript.read_text())['segments']
                    else:
                        data['transcript_segments'] = []
                        processing['legacy_transcript_missing'] = True
                        processing.setdefault('warnings', []).append('Imported historical report has no saved full transcript. The original recording is retained; reanalyse it to obtain a new transcript. Historical estimates have not been recomputed.')
                        warnings += 1
            reports.append((mid, owner, row['title'] or 'Imported meeting', status,
                json.dumps(data, ensure_ascii=False, allow_nan=False) if data is not None else None, row['created_at']))
            jobs[project_root/'.runtime/jobs'/(mid+'.json')] = {'audio': [str(audio_target)], 'ppt': None,
                'diarization': 'auto', 'options': {'language': None, 'vocabulary': '', 'model_size': None},
                'stage': 'failed' if status == 'failed' else 'completed', 'legacy_import': True,
                'error': 'Historical analysis failed; the saved recording can be retried.' if status == 'failed' else None}
        for incoming, destination in files:
            if destination.exists() and _digest(incoming) != _digest(destination):
                raise ValueError('Recording filename collision; existing audio was retained')
        for destination, data in jobs.items():
            if destination.exists() and json.loads(destination.read_text()) != data:
                raise ValueError('Existing job state would be overwritten')
        result = {'users_added': len(additions), 'meetings_added': len(reports),
            'meetings_already_present': len(meetings)-len(reports), 'reports_missing_full_transcript': warnings,
            'recordings_available': len(files), 'applied': False}
        if not apply or not (additions or reports):
            return result
        backup = project_root/'.runtime/legacy-imports'/uuid.uuid4().hex
        backup.mkdir(parents=True, mode=0o700)
        for connection, name in ((target, 'before.sqlite3'), (source, 'source.sqlite3')):
            snapshot = sqlite3.connect(backup/name)
            try: connection.backup(snapshot)
            finally: snapshot.close()
            (backup/name).chmod(0o600)
        target.execute('BEGIN IMMEDIATE')
        for incoming, destination in files:
            if not destination.exists():
                _copy_new(incoming, destination); installed.append(destination)
        for destination, data in jobs.items():
            if not destination.exists():
                staged = backup/(destination.name+'.json')
                staged.write_text(json.dumps(data, ensure_ascii=False))
                _copy_new(staged, destination); installed.append(destination)
        target.executemany('INSERT INTO users(id,email,password_hash,reset_token) VALUES(?,?,?,NULL)', additions)
        target.executemany('INSERT INTO meetings(id,user_id,title,status,report_data,created_at) VALUES(?,?,?,?,?,?)', reports)
        target.commit()
        installed.clear()  # A later manifest/permission error must not remove committed recordings.
        result.update(applied=True, backup=str(backup.relative_to(project_root)))
        (backup/'manifest.json').write_text(json.dumps(result, indent=2)+'\n')
        target_db.chmod(0o600)
        return result
    except BaseException:
        target.rollback()
        for path in installed:
            path.unlink(missing_ok=True)
        raise
    finally:
        source.close(); target.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    print(json.dumps(import_history(args.source, args.project, args.apply), indent=2))
