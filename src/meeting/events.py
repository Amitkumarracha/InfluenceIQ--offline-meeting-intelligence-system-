"""
Meeting event extraction — Phase 8.

Identifies structured meeting events from the multimodal representation
produced by Phase 7 (Transcript + Slide alignment).

Architecture
------------
BaseEventExtractor  — abstract interface; any extraction strategy must
                       subclass this so the method is replaceable without
                       changing downstream code.

KeywordEventExtractor — primary implementation.  Runs fully offline with
                         no external model downloads.  Uses curated
                         keyword/pattern lists per event type.  Confidence
                         is estimated from keyword match strength; it is
                         NOT a calibrated probability.

(Future) TransformerEventExtractor — plug-in slot for a local zero-shot
                                      classifier once a suitable model is
                                      cached locally.

Event taxonomy (configurable via config.yaml meeting_analysis.event_types):
  proposal, question, objection, evidence, correction, clarification,
  agreement, disagreement, revision, decision, action_item

Design constraints
------------------
- No cloud LLM calls.
- No fabricated labels or confidence values.
- Every event preserves full traceability to its source segment.
- Decision reconstruction is NOT performed here (Phase 9).
"""

from __future__ import annotations

import json
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.utils.config import get
from src.utils.logging import get_logger

logger = get_logger("meeting.events")

# ---------------------------------------------------------------------------
# Event taxonomy
# ---------------------------------------------------------------------------

ALL_EVENT_TYPES: list[str] = [
    "proposal",
    "question",
    "objection",
    "evidence",
    "correction",
    "clarification",
    "agreement",
    "disagreement",
    "revision",
    "decision",
    "action_item",
]


def get_active_event_types() -> list[str]:
    """Return event types from config, falling back to the full taxonomy."""
    configured = get("meeting_analysis.event_types")
    if isinstance(configured, list) and configured:
        return [t for t in configured if t in ALL_EVENT_TYPES]
    return ALL_EVENT_TYPES[:]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class MeetingEvent:
    """A single detected meeting event."""
    event_id: str
    event_type: str
    speaker: str
    start: float
    end: float
    text: str
    slide_id: str | None          # None when segment had no confident slide
    confidence: float | None      # extraction confidence; None if not estimable
    source_segment_id: int        # traceability back to MultimodalSegment


@dataclass
class EventExtractionResult:
    """Container for all events extracted from a meeting."""
    meeting_id: str
    events: list[MeetingEvent] = field(default_factory=list)

    def by_type(self, event_type: str) -> list[MeetingEvent]:
        return [e for e in self.events if e.event_type == event_type]

    def count_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {t: 0 for t in ALL_EVENT_TYPES}
        for e in self.events:
            counts[e.event_type] = counts.get(e.event_type, 0) + 1
        return {k: v for k, v in counts.items() if v > 0}


# ---------------------------------------------------------------------------
# Abstract base extractor
# ---------------------------------------------------------------------------

class BaseEventExtractor(ABC):
    """
    Interface for event extraction strategies.

    Implementations:
      KeywordEventExtractor  — offline keyword/pattern matching (Phase 8)
      (future) TransformerEventExtractor — local NLI/zero-shot model
    """

    @abstractmethod
    def extract(
        self,
        segments: list[dict[str, Any]],
        meeting_id: str,
    ) -> EventExtractionResult:
        """
        Extract events from a list of multimodal segment dicts.

        Each dict has the shape produced by Phase 7 _multimodal_to_dict():
            segment_id, speaker, start, end, text, slide_id, alignment{}
        """


# ---------------------------------------------------------------------------
# Keyword patterns (offline, no model required)
# ---------------------------------------------------------------------------

# Each entry is a list of compiled patterns.  A match on any pattern counts.
# Patterns are ordered from most specific to most general within each type.
_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "proposal": [re.compile(p, re.IGNORECASE) for p in [
        r"\bwe should\b", r"\bi propose\b", r"\blet('s| us)\b",
        r"\bwhy don't we\b", r"\bmy suggestion\b", r"\bi suggest\b",
        r"\bwhat if we\b", r"\bone option (is|would be)\b",
        r"\bwe could\b", r"\bwe might\b", r"\bhow about\b",
    ]],
    "question": [re.compile(p, re.IGNORECASE) for p in [
        r"\?$", r"\?\s*$",
        r"^(what|when|where|who|why|how|which|could you|can you|do you|did|does|is|are|was|were)\b",
        r"\bcan anyone\b", r"\bdoes anyone\b", r"\bwould you\b",
        r"\bany (questions|thoughts|comments)\b",
    ]],
    "objection": [re.compile(p, re.IGNORECASE) for p in [
        r"\bbut (that|this|it)\b", r"\bthat('s| is) (wrong|incorrect|not right|a problem)\b",
        r"\bi('m| am) not (sure|convinced|comfortable)\b",
        r"\bthe (issue|problem|concern) (is|with)\b",
        r"\bthat won't work\b", r"\bthis is problematic\b",
        r"\bhowever\b.*\bconcern\b", r"\bi have (a|some) concern\b",
        r"\bactually,? (no|that's not)\b",
    ]],
    "evidence": [re.compile(p, re.IGNORECASE) for p in [
        r"\baccording to\b", r"\bthe (data|results?|findings?|numbers?|figure[s]?|chart[s]?)\b",
        r"\bas (shown|seen|displayed|indicated|presented)\b",
        r"\bour (experiments?|tests?|evaluation|benchmark|analysis)\b",
        r"\bthis (shows?|demonstrates?|confirms?|proves?|indicates?)\b",
        r"\bfor example\b", r"\bfor instance\b",
        r"\bon (slide|page)\b", r"\bthe (table|graph|plot)\b",
        r"\b\d+(\.\d+)?%\b",           # percentage figure
        r"\bstatistically\b",
    ]],
    "correction": [re.compile(p, re.IGNORECASE) for p in [
        r"\bactually\b.*\b(is|was|should|it'?s)\b",
        r"\bthat('s| is) (actually|not quite|incorrect|wrong)\b",
        r"\blet me correct\b", r"\bi meant to say\b",
        r"\bto clarify the (numbers?|figures?|stats?)\b",
        r"\bsorry,? (i meant|the correct)\b",
        r"\bno,? (actually|the correct)\b",
    ]],
    "clarification": [re.compile(p, re.IGNORECASE) for p in [
        r"\bto (clarify|be clear|be more specific|elaborate)\b",
        r"\bwhat i (mean|meant) (is|was)\b",
        r"\bin other words\b", r"\bthat is to say\b",
        r"\bjust to (be clear|clarify|explain)\b",
        r"\bmore specifically\b", r"\bto (put|rephrase) it\b",
    ]],
    "agreement": [re.compile(p, re.IGNORECASE) for p in [
        r"\bi agree\b", r"\byes\b.*\b(that'?s?|this)\b",
        r"\bthat('s| is) (right|correct|a good point|exactly|true)\b",
        r"\bsounds? (good|great|right|correct)\b",
        r"\bexactly\b", r"\bprecisely\b",
        r"\bi('m| am) (on board|fine with|ok with)\b",
        r"\bthat makes sense\b",
    ]],
    "disagreement": [re.compile(p, re.IGNORECASE) for p in [
        r"\bi disagree\b", r"\bi don'?t (think|agree|believe)\b",
        r"\bthat('s| is) not (right|correct|accurate|true)\b",
        r"\bno,? i\b", r"\bno,? (that|this)\b",
        r"\bi('m| am) not (sure|convinced) (about|that|this)\b",
        r"\bthat's not (how|what|the right)\b",
    ]],
    "revision": [re.compile(p, re.IGNORECASE) for p in [
        r"\binstead (of|we should|let('s| us))\b",
        r"\bwe (could|should) (revise|update|change|modify|adjust)\b",
        r"\ba (revised?|updated?|modified?) (version|approach|proposal)\b",
        r"\bchanging it to\b", r"\bmodifying\b.*\bto\b",
        r"\brather than\b.*\bwe should\b",
    ]],
    "decision": [re.compile(p, re.IGNORECASE) for p in [
        r"\bwe (have |will |are going to )?(decided?|agreed?|concluded?|resolved?)\b",
        r"\bthe (final |agreed |chosen )?(decision|choice|approach|solution) (is|will be)\b",
        r"\bgoing (ahead|forward) with\b",
        r"\blet'?s (go with|use|adopt|implement)\b",
        r"\bwe('ll| will) (use|go with|implement|adopt)\b",
        r"\bit('s| is) (settled|decided|agreed)\b",
    ]],
    "action_item": [re.compile(p, re.IGNORECASE) for p in [
        r"\b(please|can you|could you|would you)\b.*\b(do|check|update|send|write|create|look into|follow up|review|fix|make sure)\b",
        r"\b(name|someone|everyone|who)\b.*\bwill\b.*\b(do|handle|take care|be responsible)\b",
        r"\baction (item|required|needed)\b",
        r"\bfollow[- ]?up\b",
        r"\bby (monday|tuesday|wednesday|thursday|friday|next week|end of (day|week|month))\b",
        r"\b(assigned?|responsible) (to|for)\b",
        r"\btake (care of|this|that)\b",
    ]],
}


def _match_event_type(
    text: str,
    active_types: list[str],
) -> tuple[str | None, float | None]:
    """
    Match text against keyword patterns and return (event_type, confidence).

    Confidence is based on the number of matching patterns relative to the
    number available for that type — a rough heuristic, NOT a calibrated
    probability.  Returns (None, None) when no type matches.
    """
    best_type: str | None = None
    best_score: float = 0.0

    for etype in active_types:
        patterns = _PATTERNS.get(etype, [])
        if not patterns:
            continue

        hits = sum(1 for p in patterns if p.search(text))
        if hits == 0:
            continue

        # Normalise by number of patterns; cap at 1.0
        score = min(1.0, hits / max(1, len(patterns)) * 3.0)
        if score > best_score:
            best_score = score
            best_type = etype

    if best_type is None:
        return None, None
    return best_type, round(best_score, 4)


# ---------------------------------------------------------------------------
# Keyword extractor (primary offline implementation)
# ---------------------------------------------------------------------------

class KeywordEventExtractor(BaseEventExtractor):
    """
    Offline keyword/pattern-based event extractor.

    Approach
    --------
    - Iterates over multimodal segments.
    - For each segment, runs pattern matching across all active event types.
    - Returns the highest-scoring type when a match exists.
    - Segments with no keyword match are skipped (not forced to an event).
    - Confidence is a heuristic match-density value, NOT a calibrated score.

    Limitations (clearly documented)
    ----------------------------------
    - Cannot understand context or coreference ("it", "that", "this").
    - May miss events phrased unusually.
    - May misclassify short or ambiguous utterances.
    - Confidence values are estimates only.
    - A TransformerEventExtractor should be used when a suitable local
      model is available.
    """

    def __init__(self, confidence_threshold: float | None = None) -> None:
        self.confidence_threshold: float = (
            confidence_threshold
            if confidence_threshold is not None
            else float(get("meeting_analysis.confidence_threshold", 0.5))
        )

    def extract(
        self,
        segments: list[dict[str, Any]],
        meeting_id: str,
    ) -> EventExtractionResult:
        active_types = get_active_event_types()
        result = EventExtractionResult(meeting_id=meeting_id)
        event_counter = 0

        for seg in segments:
            text: str = seg.get("text", "").strip()
            if not text:
                continue

            etype, confidence = _match_event_type(text, active_types)
            if etype is None:
                continue
            if confidence is not None and confidence < self.confidence_threshold:
                continue

            event_counter += 1
            slide_id = seg.get("slide_id")
            # Treat NO_CONFIDENT_SLIDE sentinel as None for cleaner output
            if slide_id == "NO_CONFIDENT_SLIDE":
                slide_id = None

            result.events.append(MeetingEvent(
                event_id=f"event_{event_counter:03d}",
                event_type=etype,
                speaker=seg.get("speaker", "UNKNOWN"),
                start=float(seg.get("start", 0.0)),
                end=float(seg.get("end", 0.0)),
                text=text,
                slide_id=slide_id,
                confidence=confidence,
                source_segment_id=int(seg.get("segment_id", 0)),
            ))

        return result


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_multimodal_segments(path: Path) -> tuple[str, list[dict[str, Any]]]:
    """
    Load the multimodal JSON produced by Phase 7.

    Returns (meeting_id, list_of_segment_dicts).
    """
    if not path.exists():
        raise FileNotFoundError(f"Multimodal JSON not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    meeting_id: str = data.get("meeting_id", path.stem)
    segments: list[dict[str, Any]] = data.get("segments", [])
    return meeting_id, segments


def save_events_json(
    result: EventExtractionResult,
    output_path: Path,
) -> None:
    """Write EventExtractionResult to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "meeting_id": result.meeting_id,
        "num_events": len(result.events),
        "events": [_event_to_dict(e) for e in result.events],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    logger.info("Events JSON saved: %s", output_path)


def load_events_json(path: Path) -> EventExtractionResult:
    """Load an EventExtractionResult from a saved JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Events JSON not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    events = [
        MeetingEvent(
            event_id=e["event_id"],
            event_type=e["event_type"],
            speaker=e["speaker"],
            start=e["start"],
            end=e["end"],
            text=e["text"],
            slide_id=e.get("slide_id"),
            confidence=e.get("confidence"),
            source_segment_id=e["source_segment_id"],
        )
        for e in data.get("events", [])
    ]
    return EventExtractionResult(meeting_id=data["meeting_id"], events=events)


def _event_to_dict(e: MeetingEvent) -> dict[str, Any]:
    return {
        "event_id": e.event_id,
        "event_type": e.event_type,
        "speaker": e.speaker,
        "start": e.start,
        "end": e.end,
        "text": e.text,
        "slide_id": e.slide_id,
        "confidence": e.confidence,
        "source_segment_id": e.source_segment_id,
    }


# ---------------------------------------------------------------------------
# Top-level runner
# ---------------------------------------------------------------------------

def run_event_extraction(
    multimodal_path: Path,
    meeting_id: str | None = None,
    output_dir: Path | None = None,
    extractor: BaseEventExtractor | None = None,
) -> tuple[EventExtractionResult, Path]:
    """
    Extract meeting events from a Phase 7 multimodal JSON file.

    Parameters
    ----------
    multimodal_path : Path
        Path to <meeting_id>_multimodal.json
    meeting_id : str | None
        Override; derived from file if None.
    output_dir : Path | None
        Defaults to data/processed/events/.
    extractor : BaseEventExtractor | None
        Injection point for custom extractors.  Defaults to
        KeywordEventExtractor.

    Returns
    -------
    (EventExtractionResult, events_json_path)
    """
    t0 = time.time()

    loaded_id, segments = load_multimodal_segments(multimodal_path)
    meeting_id = meeting_id or loaded_id

    logger.info(
        "Event extraction | meeting=%s | segments=%d | file=%s",
        meeting_id, len(segments), multimodal_path,
    )

    if extractor is None:
        extractor = KeywordEventExtractor()

    result = extractor.extract(segments, meeting_id)

    elapsed = time.time() - t0
    counts = result.count_by_type()
    low_conf = sum(
        1 for e in result.events
        if e.confidence is not None and e.confidence < float(get("meeting_analysis.confidence_threshold", 0.5))
    )

    logger.info(
        "Extracted %d events in %.2fs | by_type=%s | low_confidence=%d",
        len(result.events), elapsed, counts, low_conf,
    )

    out_dir = output_dir or Path("data/processed/events")
    out_dir.mkdir(parents=True, exist_ok=True)
    events_path = out_dir / f"{meeting_id}_events.json"
    save_events_json(result, events_path)
    logger.info("Events output: %s", events_path)

    return result, events_path
