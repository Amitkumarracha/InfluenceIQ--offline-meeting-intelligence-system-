"""
Evidence extraction — Phase 8.

Identifies relationships between meeting events and their supporting
or opposing information sources (other events, slides).

Design
------
Evidence is derived from the event set produced by KeywordEventExtractor
and the slide associations from Phase 7.  No external model is required.

Relationship taxonomy
---------------------
supports      — source provides evidence for target
contradicts   — source challenges or negates target
modifies      — source alters or refines target
clarifies     — source explains target
affects       — source has an effect on target
references    — source mentions/cites target without stronger claim

Rules for evidence detection (fully offline, deterministic)
------------------------------------------------------------
1.  Slide grounding:
      Any event that has a non-null slide_id gets a "supports" edge from
      the slide to the event — the slide content corroborates the statement.

2.  EVIDENCE → target event:
      An event typed "evidence" is paired with the nearest preceding event
      from the same or a different speaker (temporal proximity ≤ window_s).

3.  OBJECTION → target event:
      An event typed "objection" targets the most recent "proposal",
      "decision", or "revision" before it (within window_s).

4.  CORRECTION → target event:
      An event typed "correction" targets the most recent event of any
      type before it (within window_s).

5.  CLARIFICATION → target event:
      Targets the most recent event before it (within window_s).

6.  AGREEMENT / DISAGREEMENT → target event:
      Target the most recent "proposal", "decision", or "revision"
      before them (within window_s).

7.  REVISION → target event:
      Targets the most recent "proposal" before it (within window_s).

These rules are heuristic starting points.  They are NOT validated against
annotated data.  The window_s parameter controls temporal reach.

Traceability
------------
Every EvidenceRelation preserves source_event_id and target_event_id so
the full chain Segment → Event → Evidence → Slide is navigable.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.meeting.events import (
    EventExtractionResult,
    MeetingEvent,
    load_events_json,
    save_events_json,
)
from src.utils.config import get
from src.utils.logging import get_logger

logger = get_logger("meeting.evidence")

# ---------------------------------------------------------------------------
# Relationship types
# ---------------------------------------------------------------------------

RELATIONSHIP_TYPES: list[str] = [
    "supports",
    "contradicts",
    "modifies",
    "clarifies",
    "affects",
    "references",
]

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class EvidenceRelation:
    """A directed relationship between two events (or a slide and an event)."""
    evidence_id: str
    source_event_id: str          # event_id that is the evidence source
    target_event_id: str          # event_id that is supported/affected
    relationship: str             # one of RELATIONSHIP_TYPES
    slide_id: str | None          # slide involved, if any
    confidence: float | None      # heuristic confidence; None if not estimable


@dataclass
class EvidenceExtractionResult:
    """Container for all evidence relationships in a meeting."""
    meeting_id: str
    relations: list[EvidenceRelation] = field(default_factory=list)

    def by_relationship(self, rel: str) -> list[EvidenceRelation]:
        return [r for r in self.relations if r.relationship == rel]


# ---------------------------------------------------------------------------
# Core extraction logic
# ---------------------------------------------------------------------------

# Event types that can be targets of objections, agreements, disagreements
_PROPOSAL_TYPES = {"proposal", "decision", "revision"}

# Event types whose temporal context we look for as targets
_TARGET_TYPES: dict[str, set[str]] = {
    "objection":     _PROPOSAL_TYPES,
    "agreement":     _PROPOSAL_TYPES,
    "disagreement":  _PROPOSAL_TYPES,
    "revision":      {"proposal"},
    "correction":    set(ALL_TYPES := {
                         "proposal", "question", "objection", "evidence",
                         "correction", "clarification", "agreement",
                         "disagreement", "revision", "decision", "action_item"
                     }),
    "clarification": ALL_TYPES,
    "evidence":      ALL_TYPES,
}


def _find_preceding_event(
    events: list[MeetingEvent],
    current_idx: int,
    target_types: set[str],
    window_s: float,
) -> MeetingEvent | None:
    """
    Return the most recent event before *current_idx* whose type is in
    *target_types* and whose end time is within *window_s* of the current
    event's start time.
    """
    current = events[current_idx]
    for i in range(current_idx - 1, -1, -1):
        candidate = events[i]
        if current.start - candidate.end > window_s:
            break
        if candidate.event_type in target_types:
            return candidate
    return None


def extract_evidence(
    event_result: EventExtractionResult,
    window_s: float = 60.0,
) -> EvidenceExtractionResult:
    """
    Derive evidence relationships from a set of meeting events.

    Parameters
    ----------
    event_result : EventExtractionResult
    window_s : float
        Maximum time gap (seconds) between source and target events.
        Pairs separated by more than this are not linked.
        Default: 60 s.  This is a prototype default only.

    Returns
    -------
    EvidenceExtractionResult
    """
    events = sorted(event_result.events, key=lambda e: e.start)
    relations: list[EvidenceRelation] = []
    counter = 0

    def _add(
        source: MeetingEvent,
        target: MeetingEvent,
        relationship: str,
        slide_id: str | None = None,
        confidence: float | None = None,
    ) -> None:
        nonlocal counter
        counter += 1
        relations.append(EvidenceRelation(
            evidence_id=f"evidence_{counter:03d}",
            source_event_id=source.event_id,
            target_event_id=target.event_id,
            relationship=relationship,
            slide_id=slide_id or source.slide_id,
            confidence=confidence,
        ))

    for idx, event in enumerate(events):

        # ---- Rule 1: Slide grounding ----
        # An event with a slide association is a self-referencing evidence node.
        # We represent it as a slide→event "supports" relation.
        # We use a special sentinel event_id "slide:<slide_id>" for the source.
        if event.slide_id is not None:
            counter += 1
            relations.append(EvidenceRelation(
                evidence_id=f"evidence_{counter:03d}",
                source_event_id=f"slide:{event.slide_id}",
                target_event_id=event.event_id,
                relationship="supports",
                slide_id=event.slide_id,
                confidence=None,   # grounding confidence comes from Phase 7
            ))

        # ---- Rules 2–7: Inter-event relationships ----
        target_types = _TARGET_TYPES.get(event.event_type)
        if target_types is None:
            continue

        target_event = _find_preceding_event(events, idx, target_types, window_s)
        if target_event is None:
            continue

        if event.event_type == "objection":
            _add(event, target_event, "contradicts")
        elif event.event_type in ("agreement",):
            _add(event, target_event, "supports")
        elif event.event_type == "disagreement":
            _add(event, target_event, "contradicts")
        elif event.event_type == "revision":
            _add(event, target_event, "modifies")
        elif event.event_type == "correction":
            _add(event, target_event, "modifies")
        elif event.event_type == "clarification":
            _add(event, target_event, "clarifies")
        elif event.event_type == "evidence":
            _add(event, target_event, "supports")

    return EvidenceExtractionResult(
        meeting_id=event_result.meeting_id,
        relations=relations,
    )


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def save_evidence_json(
    result: EvidenceExtractionResult,
    output_path: Path,
) -> None:
    """Write EvidenceExtractionResult to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "meeting_id": result.meeting_id,
        "num_relations": len(result.relations),
        "relations": [_relation_to_dict(r) for r in result.relations],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    logger.info("Evidence JSON saved: %s", output_path)


def load_evidence_json(path: Path) -> EvidenceExtractionResult:
    """Load an EvidenceExtractionResult from a saved JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Evidence JSON not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    relations = [
        EvidenceRelation(
            evidence_id=r["evidence_id"],
            source_event_id=r["source_event_id"],
            target_event_id=r["target_event_id"],
            relationship=r["relationship"],
            slide_id=r.get("slide_id"),
            confidence=r.get("confidence"),
        )
        for r in data.get("relations", [])
    ]
    return EvidenceExtractionResult(
        meeting_id=data["meeting_id"],
        relations=relations,
    )


def _relation_to_dict(r: EvidenceRelation) -> dict[str, Any]:
    return {
        "evidence_id": r.evidence_id,
        "source_event_id": r.source_event_id,
        "target_event_id": r.target_event_id,
        "relationship": r.relationship,
        "slide_id": r.slide_id,
        "confidence": r.confidence,
    }


# ---------------------------------------------------------------------------
# Top-level runner
# ---------------------------------------------------------------------------

def run_evidence_extraction(
    events_path: Path,
    meeting_id: str | None = None,
    output_dir: Path | None = None,
    window_s: float = 60.0,
) -> tuple[EvidenceExtractionResult, Path]:
    """
    Extract evidence relationships from a saved events JSON file.

    Parameters
    ----------
    events_path : Path
        Path to <meeting_id>_events.json (Phase 8 events output).
    meeting_id : str | None
        Override; derived from events file if None.
    output_dir : Path | None
        Defaults to data/processed/events/.
    window_s : float
        Temporal window for linking events (seconds).

    Returns
    -------
    (EvidenceExtractionResult, evidence_json_path)
    """
    t0 = time.time()

    event_result = load_events_json(events_path)
    meeting_id = meeting_id or event_result.meeting_id

    logger.info(
        "Evidence extraction | meeting=%s | events=%d",
        meeting_id, len(event_result.events),
    )

    evidence_result = extract_evidence(event_result, window_s=window_s)

    elapsed = time.time() - t0
    rel_counts: dict[str, int] = {}
    for r in evidence_result.relations:
        rel_counts[r.relationship] = rel_counts.get(r.relationship, 0) + 1

    logger.info(
        "Extracted %d evidence relations in %.2fs | by_type=%s",
        len(evidence_result.relations), elapsed, rel_counts,
    )

    out_dir = output_dir or Path("data/processed/events")
    out_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = out_dir / f"{meeting_id}_evidence.json"
    save_evidence_json(evidence_result, evidence_path)
    logger.info("Evidence output: %s", evidence_path)

    return evidence_result, evidence_path
