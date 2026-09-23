"""
Serialise / deserialise PresentationData to/from JSON.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from src.ppt.extract import PresentationData, SlideData, TableData
from src.utils.logging import get_logger

logger = get_logger("ppt.io")


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def _table_to_dict(t: TableData) -> dict[str, Any]:
    return {"rows": t.rows}


def _slide_to_dict(s: SlideData) -> dict[str, Any]:
    return {
        "slide_id": s.slide_id,
        "slide_number": s.slide_number,
        "title": s.title,
        "text": s.text,
        "tables": [_table_to_dict(t) for t in s.tables],
        "notes": s.notes,
        "metadata": s.metadata,
    }


def presentation_to_dict(pdata: PresentationData) -> dict[str, Any]:
    return {
        "meeting_id": pdata.meeting_id,
        "source_file": pdata.source_file,
        "num_slides": pdata.num_slides,
        "slides": [_slide_to_dict(s) for s in pdata.slides],
    }


def save_presentation_json(pdata: PresentationData, output_path: Path) -> None:
    """Write PresentationData to a JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = presentation_to_dict(pdata)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    logger.info("Slide JSON saved to: %s", output_path)


# ---------------------------------------------------------------------------
# Deserialisation
# ---------------------------------------------------------------------------

def load_presentation_json(path: Path) -> PresentationData:
    """Load a PresentationData from a previously saved JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    slides = [
        SlideData(
            slide_id=s["slide_id"],
            slide_number=s["slide_number"],
            title=s.get("title"),
            text=s.get("text", []),
            tables=[TableData(rows=t["rows"]) for t in s.get("tables", [])],
            notes=s.get("notes"),
            metadata=s.get("metadata", {}),
        )
        for s in data.get("slides", [])
    ]

    return PresentationData(
        meeting_id=data["meeting_id"],
        source_file=data["source_file"],
        num_slides=data["num_slides"],
        slides=slides,
    )
