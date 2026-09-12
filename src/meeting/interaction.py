"""
Participant interaction analysis — Phase 10.

Consumes:
  - EventExtractionResult   (Phase 8 events JSON)
  - EvidenceExtractionResult (Phase 8 evidence JSON)
  - DecisionResult           (Phase 9 decisions JSON)

Produces:
  - InteractionResult        : all detected interactions
  - Participant-level graph  : NetworkX DiGraph (speaker nodes, interaction edges)
  - Participant statistics   : descriptive interaction counts (NOT influence scores)

Important distinctions
----------------------
  Conversational interaction  ≠  Conversational dominance  ≠  Decision influence

Statistics produced here describe WHO interacted with WHOM and HOW OFTEN.
They do NOT claim to measure influence, importance, or decision impact.
Those belong to Phase 11.

Detection approach (offline, no cloud model)
--------------------------------------------
Interactions are inferred from EVIDENCE, not from turn-taking alone.
A speaker change is NOT sufficient to create an interaction.

Priority order:
  1. Evidence relations (Phase 8) — strongest signal; use as-is.
  2. Decision lineage (Phase 9)   — extract directed speaker pairs from edges.
  3. Event-type pairs within window — objection after proposal, agreement after
     proposal/revision, etc. — only when source and target speakers differ.

Temporal proximity alone is used only as a gating filter, never as the sole
reason to create an interaction.

Interaction types (9 types — maps to Phase 8 event taxonomy):
  support, objection, response, agreement, disagreement,
  clarification, correction, challenge, reference
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.meeting.decisions import Decision, DecisionResult, load_decisions_json
from src.meeting.events import EventExtractionResult, MeetingEvent, load_events_json
from src.meeting.evidence import EvidenceExtractionResult, EvidenceRelation, load_evidence_json
from src.utils.config import get
from src.utils.logging import get_logger

logger = get_logger("meeting.interaction")

# ---------------------------------------------------------------------------
# Interaction taxonomy
# ---------------------------------------------------------------------------

INTERACTION_TYPES: list[str] = [
    "support",
    "objection",
    "response",
    "agreement",
    "disagreement",
    "clarification",
    "correction",
    "challenge",
    "reference",
]

# Map from event_type / evidence_relationship → interaction_type
_EVENT_TO_INTERACTION: dict[str, str] = {
    "objection":     "objection",
    "agreement":     "agreement",
    "disagreement":  "disagreement",
    "clarification": "clarification",
    "correction":    "correction",
    "evidence":      "support",
    "revision":      "response",
    "question":      "response",
    "proposal":      "reference",
    "decision":      "reference",
    "action_item":   "reference",
}

_EVIDENCE_REL_TO_INTERACTION: dict[str, str] = {
    "supports":    "support",
    "contradicts": "challenge",
    "modifies":    "response",
    "clarifies":   "clarification",
    "affects":     "response",
    "references":  "reference",
}

# Event types that can serve as "target" events (things being responded to)
_TARGETABLE_TYPES = {"proposal", "objection", "revision", "decision", "evidence"}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Interaction:
    """A single directed interaction between two participants."""
    interaction_id: str
    source_speaker: str
    target_speaker: str | None      # None when target cannot be determined
    interaction_type: str
    timestamp: float                # start time of source event
    source_event_id: str
    target_event_id: str | None
    related_decision_id: str | None
    related_slide_id: str | None
    text: str
    confidence: float | None        # None — not estimated in Phase 10


@dataclass
class ParticipantStats:
    """
    Descriptive interaction statistics for one participant.

    These statistics describe conversational behaviour ONLY.
    They must NOT be called 'influence' or 'impact'.
    """
    participant: str
    interactions_initiated: int = 0
    interactions_received: int = 0
    # Per-type initiated counts
    type_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class InteractionResult:
    """Container for all interactions in a meeting."""
    meeting_id: str
    participants: list[str]
    interactions: list[Interaction] = field(default_factory=list)
    participant_stats: list[ParticipantStats] = field(default_factory=list)

    def by_type(self, itype: str) -> list[Interaction]:
        return [i for i in self.interactions if i.interaction_type == itype]

    def count_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for i in self.interactions:
            counts[i.interaction_type] = counts.get(i.interaction_type, 0) + 1
        return counts

    def decision_linked(self) -> list[Interaction]:
        return [i for i in self.interactions if i.related_decision_id is not None]


# ---------------------------------------------------------------------------
# Helper: find event by ID
# ---------------------------------------------------------------------------

def _make_event_index(events: list[MeetingEvent]) -> dict[str, MeetingEvent]:
    return {e.event_id: e for e in events}


def _find_preceding_targetable(
    events: list[MeetingEvent],
    current: MeetingEvent,
    window_s: float,
) -> MeetingEvent | None:
    """
    Find the most recent targetable event before *current* within *window_s*,
    whose speaker differs from current.speaker.
    """
    for ev in reversed(events):
        if ev.event_id == current.event_id:
            continue
        if ev.start >= current.start:
            continue
        if current.start - ev.end > window_s:
            break
        if ev.event_type in _TARGETABLE_TYPES and ev.speaker != current.speaker:
            return ev
    return None


# ---------------------------------------------------------------------------
# Decision-to-event mapping
# ---------------------------------------------------------------------------

def _decision_for_event(
    event_id: str,
    decisions: list[Decision],
) -> str | None:
    """Return the decision_id that contains event_id, or None."""
    for d in decisions:
        # Check proposal, discussion, revisions, agreements, final_decision
        if d.proposal and d.proposal.get("event_id") == event_id:
            return d.decision_id
        if any(item.get("event_id") == event_id for item in d.discussion):
            return d.decision_id
        if any(item.get("event_id") == event_id for item in d.revisions):
            return d.decision_id
        if any(item.get("event_id") == event_id for item in d.agreements):
            return d.decision_id
        if d.final_decision and d.final_decision.get("event_id") == event_id:
            return d.decision_id
    return None


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------

def extract_interactions(
    event_result: EventExtractionResult,
    evidence_result: EvidenceExtractionResult,
    decision_result: DecisionResult,
    temporal_window: float = 60.0,
) -> InteractionResult:
    """
    Extract participant interactions from events, evidence, and decisions.

    Strategy
    --------
    Pass 1 — Evidence relations (strongest signal):
        Each non-slide evidence relation where source and target events have
        DIFFERENT speakers → create an interaction.

    Pass 2 — Decision lineage (structural):
        For each decision's lineage edges, if source and target events have
        different speakers → create an interaction (avoiding duplicates).

    Pass 3 — Event-type pairs within temporal window:
        For reactive event types (objection, agreement, etc.), find the most
        recent targetable event by a DIFFERENT speaker within window_s.
        Only create an interaction if not already covered by Pass 1/2.

    Parameters
    ----------
    event_result  : EventExtractionResult
    evidence_result : EvidenceExtractionResult
    decision_result : DecisionResult
    temporal_window : float
        Gate for Pass 3 only.  Default: 60 s.  Prototype value.

    Returns
    -------
    InteractionResult
    """
    events_sorted = sorted(event_result.events, key=lambda e: e.start)
    ev_index = _make_event_index(events_sorted)
    decisions = decision_result.decisions

    interactions: list[Interaction] = []
    seen: set[tuple[str, str]] = set()   # (source_event_id, target_event_id)
    counter = 0

    def _add(
        source_ev: MeetingEvent,
        target_ev: MeetingEvent | None,
        itype: str,
        decision_id: str | None = None,
    ) -> None:
        nonlocal counter
        key = (source_ev.event_id, target_ev.event_id if target_ev else "")
        if key in seen:
            return
        seen.add(key)

        # Determine related slide
        slide_id: str | None = source_ev.slide_id
        if slide_id is None and target_ev is not None:
            slide_id = target_ev.slide_id

        counter += 1
        interactions.append(Interaction(
            interaction_id=f"interaction_{counter:03d}",
            source_speaker=source_ev.speaker,
            target_speaker=target_ev.speaker if target_ev else None,
            interaction_type=itype,
            timestamp=source_ev.start,
            source_event_id=source_ev.event_id,
            target_event_id=target_ev.event_id if target_ev else None,
            related_decision_id=decision_id or _decision_for_event(source_ev.event_id, decisions),
            related_slide_id=slide_id,
            text=source_ev.text,
            confidence=None,
        ))

    # ------------------------------------------------------------------
    # Pass 1: evidence relations
    # ------------------------------------------------------------------
    for rel in evidence_result.relations:
        src_id = rel.source_event_id
        tgt_id = rel.target_event_id
        if src_id.startswith("slide:"):
            continue
        src_ev = ev_index.get(src_id)
        tgt_ev = ev_index.get(tgt_id)
        if src_ev is None or tgt_ev is None:
            continue
        if src_ev.speaker == tgt_ev.speaker:
            continue
        itype = _EVIDENCE_REL_TO_INTERACTION.get(rel.relationship, "reference")
        dec_id = _decision_for_event(src_id, decisions) or _decision_for_event(tgt_id, decisions)
        _add(src_ev, tgt_ev, itype, dec_id)

    # ------------------------------------------------------------------
    # Pass 2: decision lineage
    # ------------------------------------------------------------------
    for decision in decisions:
        for edge in decision.lineage:
            src_ev = ev_index.get(edge.source)
            tgt_ev = ev_index.get(edge.target)
            if src_ev is None or tgt_ev is None:
                continue
            if src_ev.speaker == tgt_ev.speaker:
                continue
            # Map lineage relationship to interaction type
            itype_map = {
                "challenges":   "challenge",
                "supports":     "support",
                "modifies":     "response",
                "agrees_with":  "agreement",
                "results_in":   "reference",
                "leads_to":     "response",
                "supported_by": "support",
                "contradicts":  "challenge",
                "clarifies":    "clarification",
            }
            itype = itype_map.get(edge.relationship, "reference")
            _add(src_ev, tgt_ev, itype, decision.decision_id)

    # ------------------------------------------------------------------
    # Pass 3: event-type pairs within temporal window
    # ------------------------------------------------------------------
    reactive_types = {
        "objection", "agreement", "disagreement",
        "clarification", "correction", "evidence",
    }
    for ev in events_sorted:
        if ev.event_type not in reactive_types:
            continue
        target_ev = _find_preceding_targetable(events_sorted, ev, temporal_window)
        if target_ev is None:
            continue
        itype = _EVENT_TO_INTERACTION.get(ev.event_type, "reference")
        dec_id = (
            _decision_for_event(ev.event_id, decisions)
            or _decision_for_event(target_ev.event_id, decisions)
        )
        _add(ev, target_ev, itype, dec_id)

    # ------------------------------------------------------------------
    # Compute participant stats
    # ------------------------------------------------------------------
    all_speakers = sorted({e.speaker for e in events_sorted})
    stats_map: dict[str, ParticipantStats] = {
        sp: ParticipantStats(participant=sp) for sp in all_speakers
    }

    for intr in interactions:
        src_sp = intr.source_speaker
        tgt_sp = intr.target_speaker
        if src_sp in stats_map:
            stats_map[src_sp].interactions_initiated += 1
            tc = stats_map[src_sp].type_counts
            tc[intr.interaction_type] = tc.get(intr.interaction_type, 0) + 1
        if tgt_sp and tgt_sp in stats_map:
            stats_map[tgt_sp].interactions_received += 1

    return InteractionResult(
        meeting_id=event_result.meeting_id,
        participants=all_speakers,
        interactions=interactions,
        participant_stats=list(stats_map.values()),
    )


# ---------------------------------------------------------------------------
# NetworkX participant graph
# ---------------------------------------------------------------------------

def build_participant_graph(result: InteractionResult) -> Any:
    """
    Build a directed participant-level graph.

    Nodes: speaker IDs
    Edges: interaction counts and types (NOT influence weights)

    Returns None if NetworkX is unavailable.
    """
    try:
        import networkx as nx  # type: ignore
    except ImportError:
        return None

    G = nx.MultiDiGraph()
    for sp in result.participants:
        # Attach descriptive stats to node — these are interaction counts only
        stats = next((s for s in result.participant_stats if s.participant == sp), None)
        G.add_node(
            sp,
            interactions_initiated=stats.interactions_initiated if stats else 0,
            interactions_received=stats.interactions_received if stats else 0,
        )

    for intr in result.interactions:
        if intr.target_speaker is None:
            continue
        G.add_edge(
            intr.source_speaker,
            intr.target_speaker,
            interaction_type=intr.interaction_type,
            interaction_id=intr.interaction_id,
            timestamp=intr.timestamp,
            related_decision_id=intr.related_decision_id,
        )

    return G


def _participant_graph_to_dict(G: Any, meeting_id: str) -> dict[str, Any]:
    """Serialise participant DiGraph to plain dict."""
    if G is None:
        return {"meeting_id": meeting_id, "nodes": [], "edges": []}

    nodes = [
        {"speaker": n, **dict(G.nodes[n])}
        for n in G.nodes()
    ]
    edges = [
        {
            "source": u,
            "target": v,
            "interaction_type": d.get("interaction_type"),
            "interaction_id": d.get("interaction_id"),
            "timestamp": d.get("timestamp"),
            "related_decision_id": d.get("related_decision_id"),
        }
        for u, v, d in G.edges(data=True)
    ]
    return {"meeting_id": meeting_id, "nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def _interaction_to_dict(i: Interaction) -> dict[str, Any]:
    return {
        "interaction_id": i.interaction_id,
        "source_speaker": i.source_speaker,
        "target_speaker": i.target_speaker,
        "interaction_type": i.interaction_type,
        "timestamp": i.timestamp,
        "source_event_id": i.source_event_id,
        "target_event_id": i.target_event_id,
        "related_decision_id": i.related_decision_id,
        "related_slide_id": i.related_slide_id,
        "text": i.text,
        "confidence": i.confidence,
    }


def _stats_to_dict(s: ParticipantStats) -> dict[str, Any]:
    d: dict[str, Any] = {
        "participant": s.participant,
        "interactions_initiated": s.interactions_initiated,
        "interactions_received": s.interactions_received,
    }
    # Flatten type counts into named fields for readability
    for itype in INTERACTION_TYPES:
        d[itype + "s"] = s.type_counts.get(itype, 0)
    return d


def save_interactions_json(result: InteractionResult, output_path: Path) -> None:
    """Write InteractionResult to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "meeting_id": result.meeting_id,
        "num_participants": len(result.participants),
        "participants": result.participants,
        "num_interactions": len(result.interactions),
        "interactions": [_interaction_to_dict(i) for i in result.interactions],
        "participant_stats": [_stats_to_dict(s) for s in result.participant_stats],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    logger.info("Interactions JSON saved: %s", output_path)


def save_interaction_graph_json(result: InteractionResult, output_path: Path) -> None:
    """Save the participant interaction graph as JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    G = build_participant_graph(result)
    payload = _participant_graph_to_dict(G, result.meeting_id)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    logger.info("Interaction graph JSON saved: %s", output_path)


def load_interactions_json(path: Path) -> InteractionResult:
    """Load an InteractionResult from a saved JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Interactions JSON not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    interactions = [
        Interaction(
            interaction_id=i["interaction_id"],
            source_speaker=i["source_speaker"],
            target_speaker=i.get("target_speaker"),
            interaction_type=i["interaction_type"],
            timestamp=i["timestamp"],
            source_event_id=i["source_event_id"],
            target_event_id=i.get("target_event_id"),
            related_decision_id=i.get("related_decision_id"),
            related_slide_id=i.get("related_slide_id"),
            text=i.get("text", ""),
            confidence=i.get("confidence"),
        )
        for i in data.get("interactions", [])
    ]

    stats = [
        ParticipantStats(
            participant=s["participant"],
            interactions_initiated=s.get("interactions_initiated", 0),
            interactions_received=s.get("interactions_received", 0),
            type_counts={
                itype: s.get(itype + "s", 0)
                for itype in INTERACTION_TYPES
            },
        )
        for s in data.get("participant_stats", [])
    ]

    return InteractionResult(
        meeting_id=data["meeting_id"],
        participants=data.get("participants", []),
        interactions=interactions,
        participant_stats=stats,
    )


# ---------------------------------------------------------------------------
# Top-level runner
# ---------------------------------------------------------------------------

def run_interaction_analysis(
    events_path: Path,
    evidence_path: Path,
    decisions_path: Path,
    meeting_id: str | None = None,
    output_dir: Path | None = None,
) -> tuple[InteractionResult, Path, Path]:
    """
    Run participant interaction analysis.

    Parameters
    ----------
    events_path   : Path to <meeting_id>_events.json
    evidence_path : Path to <meeting_id>_evidence.json
    decisions_path: Path to <meeting_id>_decisions.json
    meeting_id    : Override; derived from events file if None.
    output_dir    : Defaults to data/processed/interactions/.

    Returns
    -------
    (InteractionResult, interactions_json_path, graph_json_path)
    """
    t0 = time.time()

    for p in (events_path, evidence_path, decisions_path):
        if not p.exists():
            raise FileNotFoundError(f"Required input not found: {p}")

    event_result = load_events_json(events_path)
    evidence_result = load_evidence_json(evidence_path)
    decision_result = load_decisions_json(decisions_path)
    meeting_id = meeting_id or event_result.meeting_id

    temporal_window = float(get("interaction.temporal_window", 60.0))

    logger.info(
        "Interaction analysis | meeting=%s | events=%d | relations=%d | decisions=%d | window=%.0fs",
        meeting_id,
        len(event_result.events),
        len(evidence_result.relations),
        len(decision_result.decisions),
        temporal_window,
    )

    result = extract_interactions(
        event_result,
        evidence_result,
        decision_result,
        temporal_window=temporal_window,
    )

    elapsed = time.time() - t0
    type_counts = result.count_by_type()
    decision_linked = len(result.decision_linked())
    unresolved_target = sum(1 for i in result.interactions if i.target_speaker is None)

    logger.info(
        "Interactions: total=%d | by_type=%s | decision_linked=%d | unresolved_target=%d | %.2fs",
        len(result.interactions), type_counts, decision_linked, unresolved_target, elapsed,
    )

    out_dir = output_dir or Path("data/processed/interactions")
    out_dir.mkdir(parents=True, exist_ok=True)

    interactions_path = out_dir / f"{meeting_id}_interactions.json"
    graph_path = out_dir / f"{meeting_id}_interaction_graph.json"

    save_interactions_json(result, interactions_path)
    save_interaction_graph_json(result, graph_path)

    logger.info("Interactions output : %s", interactions_path)
    logger.info("Graph output        : %s", graph_path)

    return result, interactions_path, graph_path
