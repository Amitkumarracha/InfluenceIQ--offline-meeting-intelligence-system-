import os
import uuid
import json
import subprocess
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from pydantic import BaseModel, Field
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
import bcrypt
import jwt

# --- Security Constants ---
SECRET_KEY = "super-secret-meet-iq-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

security = HTTPBearer()

# --- Database Setup ---
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data" / "custom_test"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"
DB_PATH = PROJECT_ROOT / "nexus_v2.db"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    reset_token = Column(String, nullable=True)

class Meeting(Base):
    __tablename__ = "meetings"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    title = Column(String)
    status = Column(String)
    report_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# --- App Setup ---
app = FastAPI(title="Meet IQ API - Core Intelligence")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
logger = logging.getLogger("uvicorn.error")

# Mount static directory to serve audio files for playback
app.mount("/media", StaticFiles(directory=str(DATA_DIR)), name="media")

# --- Auth Dependencies ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid auth token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# --- Auth Pydantic Models ---
class UserCreate(BaseModel):
    email: str
    password: str = Field(..., min_length=8, max_length=64, description="Password must be between 8 and 64 characters")

class UserLogin(BaseModel):
    email: str
    password: str

class ForgotPasswordReq(BaseModel):
    email: str

class ResetPasswordReq(BaseModel):
    token: str
    new_password: str

# --- Auth Endpoints ---
@app.post("/api/auth/register")
def register(user: UserCreate, db = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pw = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    new_user = User(id=uuid.uuid4().hex, email=user.email, password_hash=hashed_pw)
    db.add(new_user)
    db.commit()
    
    token = jwt.encode({"sub": new_user.id, "exp": datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)}, SECRET_KEY, algorithm=ALGORITHM)
    return {"token": token, "email": new_user.email}

@app.post("/api/auth/login")
def login(user: UserLogin, db = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not bcrypt.checkpw(user.password.encode('utf-8'), db_user.password_hash.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = jwt.encode({"sub": db_user.id, "exp": datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)}, SECRET_KEY, algorithm=ALGORITHM)
    return {"token": token, "email": db_user.email}

@app.post("/api/auth/forgot-password")
def forgot_password(req: ForgotPasswordReq, db = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        return {"message": "If an account exists, a reset link has been sent."}
    
    reset_token = uuid.uuid4().hex
    user.reset_token = reset_token
    db.commit()
    
    logger.info(f"--- PASSWORD RESET LINK GENERATED ---")
    logger.info(f"Copy this token to reset {user.email}'s password: {reset_token}")
    
    return {"message": "If an account exists, a reset link has been sent.", "dev_token": reset_token}

@app.post("/api/auth/reset-password")
def reset_password(req: ResetPasswordReq, db = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == req.token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    user.password_hash = bcrypt.hashpw(req.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user.reset_token = None
    db.commit()
    return {"message": "Password successfully reset"}

# --- Background Task ---
def run_pipeline_background(user_id: str, meeting_id: str, audio_path: str, ppt_path: Optional[str]):
    db = SessionLocal()
    try:
        script_path = PROJECT_ROOT / "scripts" / "process_new_meeting.sh"
        cmd = [str(script_path), meeting_id, str(audio_path)]
        if ppt_path: cmd.append(str(ppt_path))

        process = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)

        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if process.returncode != 0:
            logger.error(f"Pipeline failed for {meeting_id}. Return code: {process.returncode}")
            logger.error(f"STDOUT: {process.stdout}")
            logger.error(f"STDERR: {process.stderr}")
            if meeting: meeting.status = "failed"
            db.commit()
            return

        report_json_path = REPORTS_DIR / f"{meeting_id}_report.json"
        if report_json_path.exists():
            with open(report_json_path, "r") as f: report_data = f.read()
            if meeting:
                meeting.status = "completed"
                meeting.report_data = report_data
                db.commit()
        else:
            if meeting: meeting.status = "failed"
            db.commit()

    except Exception:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if meeting: meeting.status = "failed"
        db.commit()
    finally:
        db.close()

# --- Protected API Endpoints ---
@app.post("/api/analyze")
async def analyze_meeting(
    background_tasks: BackgroundTasks,
    audio: List[UploadFile] = File(...),
    ppt: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user)
):
    try:
        meeting_id = f"meeting_{uuid.uuid4().hex[:8]}"
        
        if len(audio) == 1:
            audio_ext = Path(audio[0].filename).suffix
            if not audio_ext: audio_ext = ".webm"
            temp_path = DATA_DIR / f"temp_{meeting_id}{audio_ext}"
            final_audio_path = DATA_DIR / f"{meeting_id}.wav"
            with open(temp_path, "wb") as f: f.write(await audio[0].read())
            # Convert to standard 16kHz mono WAV and apply loudnorm (critical for web recordings & dictaphones)
            subprocess.run(["ffmpeg", "-y", "-i", str(temp_path), "-ar", "16000", "-ac", "1", "-af", "loudnorm", str(final_audio_path)], capture_output=True)
            if temp_path.exists(): os.remove(temp_path)
        else:
            concat_list_path = DATA_DIR / f"{meeting_id}_concat.txt"
            with open(concat_list_path, "w") as f_list:
                for idx, a_file in enumerate(audio):
                    a_path = DATA_DIR / f"{meeting_id}_part{idx}.wav"
                    with open(a_path, "wb") as f_out: f_out.write(await a_file.read())
                    f_list.write(f"file '{a_path.absolute()}'\n")
            final_audio_path = DATA_DIR / f"{meeting_id}_merged.wav"
            subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list_path), "-ar", "16000", "-ac", "1", "-af", "loudnorm", str(final_audio_path)], capture_output=True)

        final_ppt_path = None
        if ppt and len(ppt) > 0 and ppt[0].filename:
            ppt_ext = Path(ppt[0].filename).suffix
            final_ppt_path = DATA_DIR / f"{meeting_id}{ppt_ext}"
            with open(final_ppt_path, "wb") as f: f.write(await ppt[0].read())

        db = SessionLocal()
        new_meeting = Meeting(id=meeting_id, user_id=current_user.id, title=f"Meeting {datetime.now().strftime('%b %d, %Y')}", status="processing")
        db.add(new_meeting)
        db.commit()
        db.close()

        background_tasks.add_task(run_pipeline_background, current_user.id, meeting_id, str(final_audio_path), str(final_ppt_path) if final_ppt_path else None)
        return {"status": "success", "meeting_id": meeting_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/meetings")
def get_meetings(db = Depends(get_db), current_user: User = Depends(get_current_user)):
    meetings = db.query(Meeting).filter(Meeting.user_id == current_user.id).order_by(Meeting.created_at.desc()).all()
    res = [{"id": m.id, "title": m.title, "status": m.status, "created_at": m.created_at.isoformat()} for m in meetings]
    return {"meetings": res}

@app.get("/api/meetings/{meeting_id}")
def get_meeting(meeting_id: str, db = Depends(get_db), current_user: User = Depends(get_current_user)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.user_id == current_user.id).first()
    if not meeting: raise HTTPException(status_code=404, detail="Meeting not found")
    
    data = None
    audio_url = None
    
    if meeting.report_data:
        data = json.loads(meeting.report_data)
        
        # Look for transcript
        transcript_path = PROJECT_ROOT / "data" / "processed" / "audio" / f"{meeting_id}_transcript.json"
        if transcript_path.exists():
            try:
                with open(transcript_path, "r") as f:
                    transcript_json = json.load(f)
                    data["transcript_segments"] = transcript_json.get("segments", [])
            except Exception as e:
                logger.error(f"Failed to load transcript for {meeting_id}: {e}")
                
        # Look for the audio file to serve in the player
        possible_extensions = [".wav", "_merged.wav", ".mp3", ".m4a"]
        for ext in possible_extensions:
            if (DATA_DIR / f"{meeting_id}{ext}").exists():
                audio_url = f"http://localhost:8000/media/{meeting_id}{ext}"
                break

    return {
        "id": meeting.id,
        "title": meeting.title,
        "status": meeting.status,
        "created_at": meeting.created_at.isoformat(),
        "data": data,
        "audio_url": audio_url
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
