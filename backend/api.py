"""Private local meeting API. Run one worker; ML jobs are serialized on the CPU."""
import asyncio
import json
import time
import logging
import os
import secrets
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, DateTime, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.utils.config import PROJECT_ROOT
from src.utils.cache import atomic_json

RUNTIME = Path(os.environ.get('MAI_RUNTIME_DIR', PROJECT_ROOT / '.runtime'))
RUNTIME.mkdir(parents=True, exist_ok=True)
RUNTIME.chmod(0o700)
secret_file = RUNTIME / 'jwt-secret'
if not secret_file.exists():
    try:
        fd = os.open(secret_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(secrets.token_urlsafe(48))
    except FileExistsError:
        pass
SECRET_KEY = os.environ.get('MAI_SECRET_KEY') or secret_file.read_text().strip()
DATA_DIR = Path(os.environ.get('MAI_DATA_DIR', PROJECT_ROOT / 'data' / 'custom_test'))
REPORTS_DIR = PROJECT_ROOT / 'outputs' / 'reports'
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.environ.get('MAI_DB_PATH', PROJECT_ROOT / 'data' / 'state' / 'nexus_v2.db'))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(f'sqlite:///{DB_PATH}', connect_args={'check_same_thread': False, 'timeout': 30})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
logger = logging.getLogger('uvicorn.error')


def redact_media_token(record):
    if isinstance(record.args, tuple) and len(record.args) >= 3 and isinstance(record.args[2], str):
        values = list(record.args)
        values[2] = values[2].split('?token=', 1)[0]
        record.args = tuple(values)
    return True


logging.getLogger('uvicorn.access').addFilter(redact_media_token)
security = HTTPBearer()
MAX_UPLOAD_BYTES = int(os.environ.get('MAI_MAX_UPLOAD_BYTES', 1024 ** 3))
report_lock = threading.Lock()


class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    reset_token = Column(String, nullable=True)


class Meeting(Base):
    __tablename__ = 'meetings'
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    title = Column(String)
    status = Column(String)
    report_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


Base.metadata.create_all(bind=engine)


def job_path(meeting_id):
    return RUNTIME / 'jobs' / f'{meeting_id}.json'


def job_state(meeting_id):
    try:
        return json.loads(job_path(meeting_id).read_text())
    except (OSError, ValueError):
        return {}


def run_pipeline_background(user_id, meeting_id):
    from src.audio.parts import decode_parts
    from src.pipeline.orchestrator import run_meeting
    state = job_state(meeting_id)

    worker_started = stage_started = time.perf_counter()
    state['stage_timings_seconds'] = {}

    def progress(stage, details=None):
        nonlocal stage_started
        now = time.perf_counter()
        if stage != state.get('stage'):
            if state.get('stage'):
                state['stage_timings_seconds'][state['stage']] = round(now - stage_started, 6)
            stage_started = now
        state['worker_elapsed_seconds'] = round(now - worker_started, 6)
        state['stage_started_at'] = (datetime.now(timezone.utc) - timedelta(seconds=now-stage_started)).isoformat()
        state.update(stage=stage, error=None, progress=details,
                     updated_at=datetime.now(timezone.utc).isoformat())
        atomic_json(job_path(meeting_id), state)

    with SessionLocal() as db:
        meeting = db.query(Meeting).filter_by(id=meeting_id, user_id=user_id).first()
        if not meeting:
            return
        meeting.status = 'processing'
        db.commit()
    try:
        progress('decoding')
        final_audio = decode_parts(state['audio'], DATA_DIR / f'{meeting_id}.wav')
        report_path = run_meeting(final_audio, meeting_id, state.get('ppt'),
                                  state.get('diarization', 'auto'), progress, state.get('options'))
        progress('completed')
        with SessionLocal() as db:
            meeting = db.query(Meeting).filter_by(id=meeting_id, user_id=user_id).one()
            meeting.report_data = report_path.read_text(encoding='utf-8')
            meeting.status = 'completed'
            db.commit()
    except Exception as exc:
        logger.exception('Meeting %s failed', meeting_id)
        state.update(stage='failed', error=f'{type(exc).__name__}: {str(exc)[:400]}')
        atomic_json(job_path(meeting_id), state)
        with SessionLocal() as db:
            meeting = db.query(Meeting).filter_by(id=meeting_id, user_id=user_id).first()
            if meeting:
                meeting.status = 'failed'
                db.commit()


@asynccontextmanager
async def lifespan(app):
    import fcntl
    lock = (RUNTIME / 'worker.lock').open('w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise RuntimeError('Another meeting API is running. Use one worker.')
    app.state.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='meeting')
    with SessionLocal() as db:
        for meeting in db.query(Meeting).filter(Meeting.status.in_(['queued', 'processing'])):
            if job_path(meeting.id).exists():
                app.state.executor.submit(run_pipeline_background, meeting.user_id, meeting.id)
            else:
                meeting.status = 'failed'
        db.commit()
    try:
        yield
    finally:
        app.state.executor.shutdown(wait=True)
        lock.close()


app = FastAPI(title='Meet IQ — Offline Meeting Intelligence', lifespan=lifespan)
app.add_middleware(CORSMiddleware,
    allow_origins=os.environ.get('MAI_ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(','),
    allow_methods=['GET', 'POST'], allow_headers=['Authorization', 'Content-Type'])


def get_db():
    with SessionLocal() as db:
        yield db


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db=Depends(get_db)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=['HS256'])
        if payload.get('purpose') != 'access':
            raise jwt.InvalidTokenError()
        user = db.query(User).filter_by(id=payload.get('sub')).first()
        if user is None:
            raise jwt.InvalidTokenError()
        return user
    except jwt.PyJWTError:
        raise HTTPException(401, 'Invalid or expired token')


def access_response(user):
    token = jwt.encode({'sub': user.id, 'purpose': 'access',
        'exp': datetime.now(timezone.utc) + timedelta(hours=24)}, SECRET_KEY, algorithm='HS256')
    return {'token': token, 'email': user.email}


class UserLogin(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=64)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value):
        value = value.strip().lower()
        if '@' not in value:
            raise ValueError('Enter an email address')
        return value

    @field_validator('password')
    @classmethod
    def password_bytes(cls, value):
        if len(value.encode('utf-8')) > 72:
            raise ValueError('Password must be at most 72 UTF-8 bytes')
        return value


class UserCreate(UserLogin):
    password: str = Field(min_length=8, max_length=64)


@app.post('/api/auth/register')
def register(user: UserCreate, db=Depends(get_db)):
    if os.environ.get('MAI_ALLOW_REGISTRATION', '1') != '1':
        raise HTTPException(403, 'Account registration is disabled on this server')
    from sqlalchemy.exc import IntegrityError
    new = User(id=uuid.uuid4().hex, email=user.email,
               password_hash=bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode())
    try:
        db.add(new)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Email already registered')
    return access_response(new)


@app.post('/api/auth/login')
def login(user: UserLogin, db=Depends(get_db)):
    stored = db.query(User).filter_by(email=user.email).first()
    if not stored or not bcrypt.checkpw(user.password.encode(), stored.password_hash.encode()):
        raise HTTPException(401, 'Invalid email or password')
    return access_response(stored)


@app.post('/api/auth/forgot-password')
@app.post('/api/auth/reset-password')
def reset_disabled():
    raise HTTPException(403, 'Offline recovery is available on the laptop: .venv/bin/python scripts/reset_password.py')


@app.get('/api/health')
def health():
    from huggingface_hub import snapshot_download
    from src.utils.config import get
    from faster_whisper.utils import _MODELS
    available = []
    for name in ('tiny', 'base', 'small', 'medium', 'large-v3', 'large-v3-turbo'):
        try:
            location = snapshot_download(_MODELS[name], local_files_only=True)
            if (Path(location) / 'model.bin').exists():
                available.append(name)
        except Exception:
            pass
    from src.audio.diarization import diarization_status
    speakers = diarization_status()
    ready = get('asr.model_size') in available
    return {'status': 'ok', 'inference': 'local-laptop', 'asr_ready': ready,
            'asr_model': get('asr.model_size'), 'asr_models': available,
            'diarization': speakers, 'generative_ai': False, 'offline': True, 'max_upload_bytes': MAX_UPLOAD_BYTES}


@app.post('/api/analyze', status_code=202)
async def analyze_meeting(audio: list[UploadFile] = File(...), ppt: list[UploadFile] | None = File(None),
                          title: str = Form(''), diarization: str = Form('auto'),
                          model_size: str = Form(''), language: str = Form('auto'),
                          vocabulary: str = Form('', max_length=1000), num_speakers: int | None = Form(None, ge=1, le=50),
                          current_user: User = Depends(get_current_user)):
    if not audio or len(audio) > 32:
        raise HTTPException(422, 'Supply between 1 and 32 audio parts, in chronological order')
    if diarization not in {'auto', 'required', 'off'}:
        raise HTTPException(422, 'Invalid diarization mode')
    if model_size and model_size not in {'tiny', 'base', 'small', 'medium', 'large-v3', 'large-v3-turbo'}:
        raise HTTPException(422, 'Invalid speech model')
    if language not in {'auto', 'en', 'hi'}:
        raise HTTPException(422, 'Choose auto, English or Hindi')
    slides = [f for f in (ppt or []) if f.filename]
    if len(slides) > 1:
        raise HTTPException(422, 'Upload one combined PPTX presentation')
    meeting_id = 'meeting_' + uuid.uuid4().hex
    upload_dir = RUNTIME / 'uploads' / meeting_id
    upload_dir.mkdir(parents=True)
    saved = []
    total = 0

    async def save(upload, stem, extensions):
        nonlocal total
        extension = Path(upload.filename or '').suffix.lower()
        if extension not in extensions:
            raise HTTPException(415, 'Unsupported file type')
        destination = upload_dir / (stem + extension)
        saved.append(destination)
        size = 0
        with destination.open('wb') as stream:
            while block := await upload.read(1024 * 1024):
                total += len(block)
                size += len(block)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, 'Recording exceeds the configured upload limit')
                stream.write(block)
        if size == 0:
            raise HTTPException(422, 'Empty file')
        return str(destination)

    try:
        paths = []
        from src.audio.preprocess import probe_audio
        for index, upload in enumerate(audio):
            path = await save(upload, f'audio_{index}', {'.wav', '.mp3', '.m4a', '.mp4', '.webm', '.ogg', '.flac', '.aac'})
            try:
                await asyncio.to_thread(probe_audio, path)
            except ValueError:
                raise HTTPException(422, 'File does not contain decodable audio')
            paths.append(path)
        ppt_path = await save(slides[0], 'slides', {'.pptx'}) if slides else None
        state = {'audio': paths, 'ppt': ppt_path, 'diarization': diarization, 'stage': 'queued', 'error': None,
                 'options': {'model_size': model_size or None, 'language': None if language == 'auto' else language,
                             'vocabulary': vocabulary.strip(), 'num_speakers': num_speakers}}
        atomic_json(job_path(meeting_id), state)
        with SessionLocal() as db:
            db.add(Meeting(id=meeting_id, user_id=current_user.id,
                title=title.strip()[:200] or f'Meeting {datetime.now().strftime("%b %d, %Y")}', status='queued'))
            db.commit()
    except Exception:
        for path in saved:
            path.unlink(missing_ok=True)
        upload_dir.rmdir()
        job_path(meeting_id).unlink(missing_ok=True)
        raise
    finally:
        for upload in audio + (ppt or []):
            await upload.close()
    app.state.executor.submit(run_pipeline_background, current_user.id, meeting_id)
    return {'status': 'queued', 'meeting_id': meeting_id}


def owned_meeting(db, meeting_id, user):
    meeting = db.query(Meeting).filter_by(id=meeting_id, user_id=user.id).first()
    if not meeting:
        raise HTTPException(404, 'Meeting not found')
    return meeting


@app.get('/api/meetings')
def get_meetings(db=Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'meetings': [{'id': m.id, 'title': m.title, 'status': m.status,
        'created_at': m.created_at.isoformat()} for m in db.query(Meeting).filter_by(user_id=current_user.id).order_by(Meeting.created_at.desc())]}


@app.get('/api/meetings/{meeting_id}')
def get_meeting(meeting_id: str, db=Depends(get_db), current_user: User = Depends(get_current_user)):
    m = owned_meeting(db, meeting_id, current_user)
    data = json.loads(m.report_data) if m.report_data else None
    if data and 'transcript_segments' not in data:
        path = PROJECT_ROOT / 'data' / 'processed' / 'audio' / f'{meeting_id}_transcript.json'
        if path.exists():
            data['transcript_segments'] = json.loads(path.read_text()).get('segments', [])
    if data:
        from src.meeting.vocabulary import suggest_vocabulary
        data.pop('local_notes', None)
        if 'vocabulary_suggestions' not in data:
            data['vocabulary_suggestions'] = suggest_vocabulary(data.get('transcript_segments', []))
        data.setdefault('vocabulary', (job_state(meeting_id).get('options') or {}).get('vocabulary', ''))
    media_token = jwt.encode({'sub': current_user.id, 'mid': meeting_id, 'purpose': 'audio',
        'exp': datetime.now(timezone.utc) + timedelta(hours=8)}, SECRET_KEY, algorithm='HS256')
    state = job_state(meeting_id)
    preview = None
    if m.status in {'processing', 'failed'}:
        preview_path = PROJECT_ROOT / 'data' / 'processed' / 'audio' / f'{meeting_id}_preview.json'
        try:
            preview = json.loads(preview_path.read_text())
        except (OSError, ValueError):
            pass
    return {'id': m.id, 'title': m.title, 'status': m.status, 'created_at': m.created_at.isoformat(),
            'data': data, 'stage': state.get('stage'), 'error': state.get('error'),
            'progress': {**(state.get('progress') or {}),
                'stage_elapsed_seconds': max(0, round((datetime.now(timezone.utc) - datetime.fromisoformat(state['stage_started_at'])).total_seconds(), 1))
                    if state.get('stage_started_at') and m.status == 'processing' else None}, 'preview': preview,
            'can_analyze_speakers': bool(state.get('audio') or (DATA_DIR / f'{meeting_id}.wav').is_file()),
            'audio_url': f'/api/meetings/{meeting_id}/audio?token={media_token}' if data else None}


@app.get('/api/meetings/{meeting_id}/audio')
def meeting_audio(meeting_id: str, token: str, db=Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        if payload.get('purpose') != 'audio' or payload.get('mid') != meeting_id:
            raise jwt.InvalidTokenError()
    except jwt.PyJWTError:
        raise HTTPException(401, 'Invalid or expired audio link')
    if not db.query(Meeting).filter_by(id=meeting_id, user_id=payload.get('sub')).first():
        raise HTTPException(404, 'Meeting not found')
    for suffix in ('.wav', '_merged.wav'):
        path = DATA_DIR / (meeting_id + suffix)
        if path.is_file():
            return FileResponse(path, media_type='audio/wav', headers={'Cache-Control': 'private, no-store'})
    raise HTTPException(404, 'Audio not found')


@app.post('/api/meetings/{meeting_id}/retry', status_code=202)
def retry(meeting_id: str, db=Depends(get_db), current_user: User = Depends(get_current_user)):
    meeting = owned_meeting(db, meeting_id, current_user)
    if not job_path(meeting_id).exists():
        raise HTTPException(409, 'Source recording unavailable; upload again')
    # Conditional update prevents duplicate concurrent retries.
    changed = db.query(Meeting).filter_by(id=meeting.id, status='failed').update({'status': 'queued'})
    db.commit()
    if not changed:
        raise HTTPException(409, 'Only failed meetings can be retried')
    app.state.executor.submit(run_pipeline_background, current_user.id, meeting_id)
    return {'status': 'queued'}


@app.post('/api/meetings/{meeting_id}/analyze-speakers', status_code=202)
def analyze_saved_speakers(meeting_id: str, db=Depends(get_db), current_user: User = Depends(get_current_user)):
    """Recover a transcript-only meeting using its saved audio; preserve its title."""
    with report_lock:
        meeting = owned_meeting(db, meeting_id, current_user)
        if meeting.status not in {'completed', 'failed'}:
            raise HTTPException(409, 'Wait for the current analysis to finish')
        data = json.loads(meeting.report_data or '{}')
        if any(s.get('speaker') not in {None, 'UNKNOWN'} for s in data.get('transcript_segments', [])):
            raise HTTPException(409, 'This meeting already has attributed speakers')
        from src.audio.diarization import diarization_status
        if not diarization_status()['ready']:
            raise HTTPException(422, 'Complete local speaker-model setup first')
        state = job_state(meeting_id)
        sources = state.get('audio') or [str(DATA_DIR / f'{meeting_id}.wav')]
        if not all(Path(path).is_file() for path in sources):
            raise HTTPException(409, 'Saved source audio is unavailable; upload the meeting again')
        options = state.get('options') or data.get('processing', {}).get('options') or {}
        options = {**options, 'vocabulary': data.get('vocabulary', options.get('vocabulary', ''))}
        state.update(audio=sources, options=options, diarization='required', stage='queued', error=None, progress=None)
        atomic_json(job_path(meeting_id), state)
        meeting.status = 'queued'
        db.commit()
        app.state.executor.submit(run_pipeline_background, current_user.id, meeting_id)
    return {'status': 'queued'}


class MeetingEdit(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    speaker_names: dict[str, str] | None = None
    speaker_roles: dict[str, str] | None = None
    vocabulary: str | None = Field(default=None, max_length=1000)


@app.post('/api/meetings/{meeting_id}/edit')
def edit_meeting(meeting_id: str, body: MeetingEdit, db=Depends(get_db), current_user: User = Depends(get_current_user)):
    with report_lock:
        meeting = owned_meeting(db, meeting_id, current_user)
        if body.title is not None:
            if not body.title.strip():
                raise HTTPException(422, 'Enter a meeting title')
            meeting.title = body.title.strip()
        if body.speaker_names is not None or body.speaker_roles is not None or body.vocabulary is not None:
            if meeting.status != 'completed':
                raise HTTPException(409, 'Participant edits are available after processing')
            data = json.loads(meeting.report_data)
            known = {s['speaker'] for s in data.get('transcript_segments', [])} - {'UNKNOWN'}
            for field, values in [('speaker_names', body.speaker_names), ('speaker_roles', body.speaker_roles)]:
                if values is not None:
                    if len(values) > 50 or any(k not in known or len(v) > 100 for k, v in values.items()):
                        raise HTTPException(422, 'Use known speaker IDs and values up to 100 characters')
                    data[field] = {k: v.strip() for k, v in values.items() if v.strip()}
            if body.vocabulary is not None:
                data['vocabulary'] = body.vocabulary.strip()
            meeting.report_data = json.dumps(data, ensure_ascii=False)
        db.commit()
        return {'status': 'saved'}


class ProfileEdit(BaseModel):
    name: str = Field(default='', max_length=100)
    role: str = Field(default='', max_length=100)
    organization: str = Field(default='', max_length=200)


@app.get('/api/profile')
def profile(current_user: User = Depends(get_current_user)):
    try:
        saved = json.loads((RUNTIME / 'profiles' / f'{current_user.id}.json').read_text())
    except (OSError, ValueError):
        saved = {}
    return {'email': current_user.email, **ProfileEdit(**saved).model_dump()}


@app.post('/api/profile')
def save_profile(body: ProfileEdit, current_user: User = Depends(get_current_user)):
    atomic_json(RUNTIME / 'profiles' / f'{current_user.id}.json',
                {key: value.strip() for key, value in body.model_dump().items()})
    return {'status': 'saved'}


@app.get('/api/meetings/{meeting_id}/export')
def export_meeting(meeting_id: str, format: str = Query('json', pattern='^(json|md|txt|srt|vtt|csv)$'), db=Depends(get_db), current_user: User = Depends(get_current_user)):
    meeting = owned_meeting(db, meeting_id, current_user)
    if meeting.status != 'completed':
        raise HTTPException(409, 'Meeting is not completed')
    from fastapi.responses import Response
    data = json.loads(meeting.report_data)
    data.pop('local_notes', None)
    content, media_type = json.dumps(data, ensure_ascii=False), 'application/json'
    if format != 'json':
        from src.report.transcript_export import render_export
        content, media_type = render_export(data, meeting.title, format)
    return Response(content, media_type=media_type,
                    headers={'Content-Disposition': f'attachment; filename="{meeting_id}_report.{format}"',
                             'Cache-Control': 'private, no-store'})


if (PROJECT_ROOT / 'frontend' / 'dist').exists():
    app.mount('/', StaticFiles(directory=PROJECT_ROOT / 'frontend' / 'dist', html=True), name='frontend')

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host=os.environ.get('MAI_HOST', '127.0.0.1'), port=8000)
