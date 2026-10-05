"""Helpers for resume checkpoints and progress tracking."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHECKPOINT_ROOT = PROJECT_ROOT / "data" / "checkpoints" / "per_meeting"
DEFAULT_STATE_FILE = "resume_state.json"


def ensure_meeting_checkpoint_dir(meeting_id: str, root: str | Path | None = None) -> Path:
    """Return the checkpoint directory for a meeting."""
    checkpoint_root = Path(root) if root is not None else DEFAULT_CHECKPOINT_ROOT
    meeting_dir = checkpoint_root / meeting_id
    meeting_dir.mkdir(parents=True, exist_ok=True)
    return meeting_dir


def load_resume_state(meeting_id: str, root: str | Path | None = None) -> dict[str, Any]:
    """Load checkpoint state for a meeting if it exists."""
    checkpoint_dir = ensure_meeting_checkpoint_dir(meeting_id, root=root)
    state_file = checkpoint_dir / DEFAULT_STATE_FILE
    if not state_file.exists():
        return {
            "meeting_id": meeting_id,
            "current_stage": "not_started",
            "completed_stages": [],
            "status": "not_started",
            "last_output": None,
            "started_at": None,
            "updated_at": None,
        }
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "meeting_id": meeting_id,
            "current_stage": "not_started",
            "completed_stages": [],
            "status": "not_started",
            "last_output": None,
            "started_at": None,
            "updated_at": None,
        }


def save_resume_state(
    meeting_id: str,
    current_stage: str,
    completed_stages: list[str] | None = None,
    status: str = "running",
    last_output: str | None = None,
    root: str | Path | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write the resume checkpoint state for a meeting."""
    checkpoint_dir = ensure_meeting_checkpoint_dir(meeting_id, root=root)
    state_file = checkpoint_dir / DEFAULT_STATE_FILE
    current = load_resume_state(meeting_id, root=root)
    current["meeting_id"] = meeting_id
    current["current_stage"] = current_stage
    current["completed_stages"] = sorted(set((completed_stages or []) + current.get("completed_stages", [])))
    current["status"] = status
    current["last_output"] = last_output or current.get("last_output")
    current["updated_at"] = str(__import__("datetime").datetime.utcnow().isoformat(timespec="seconds")) + "Z"
    if current.get("started_at") is None:
        current["started_at"] = current["updated_at"]
    if extra:
        for key, value in extra.items():
            current[key] = value
    from src.utils.cache import atomic_json
    atomic_json(state_file, current)
    return current


def mark_stage_complete(
    meeting_id: str,
    completed_stage: str,
    output_path: str | Path | None = None,
    root: str | Path | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Mark a pipeline stage as complete and persist it."""
    state = load_resume_state(meeting_id, root=root)
    completed = list(state.get("completed_stages", []))
    completed.append(completed_stage)
    completed = sorted(set(completed))
    return save_resume_state(
        meeting_id=meeting_id,
        current_stage=completed_stage,
        completed_stages=completed,
        status="running",
        last_output=str(output_path) if output_path else state.get("last_output"),
        root=root,
        extra=extra,
    )
