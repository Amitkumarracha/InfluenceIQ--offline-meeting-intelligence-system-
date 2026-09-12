"""
Decision reconstruction and lineage — Phase 9.

Consumes:
  - EventExtractionResult   (Phase 8 events JSON)
  - EvidenceExtractionResult (Phase 8 evidence JSON)
  - multimodal segments       (Phase 7 multimodal JSON, optional — for segment IDs)

Produces:
  - DecisionResult     : structured decisions with full lineage
  - NetworkX DiGraph   : machine-readable lineage graph per decision

Architecture
------------
The reconstruction is fully offline and operates on structured JSON only.
No audio reload.  No cloud model.

Reconstruction approach (heuristic, clearly documented)
---------------------------------------------------------
1.  Identify "anchor" events — those that strongly signal a decision point:
      - event_type == "decision"  (explicit)
      - event_type == "agreement" with a preceding proposal (resolved)

2.  For each anchor, grow a decision cluster by collecting events within
    a configurable temporal_window (seconds) that are connected to the
    anchor through evidence relations or temporal proximity.

3.  Within a cluster, classify roles:
      proposal → the earliest proposal-type event
      objections, evidence, revisions, agreements → collected by type
      final_decision → the anchor event (or the last "decision"-type)

4.  Determine status:
      "confirmed"   — anchor is a "decision" event OR at least one agreement
                       follows the proposal within the cluster
      "probable"    — anchor is "agreement" but no explicit "decision" event
      "unresolved"  — proposal with no agreement/decision within window
      "conflicting" — more than one unresolved objection remains and no
                       agreement resolves them

5.  Build lineage edges from evidence relations within the cluster
    plus inferred edges (proposal→revision→agreement→decision).

6.  Build a NetworkX DiGraph; serialise to node/edge lists.

Uncertainty principle
---------------------
The system never invents a decision.  If no qualifying anchor exists,
a proposal becomes "unresolved".  Conflicting proposals produce
"conflicting" status.

Decision impact classification (Phase 9 scope only — NOT influence scoring)
---------------------------------------------------------------------------
  directly_decision_relevant   — anchor + immediate proposal/revision
  indirectly_decision_relevant — objections, supporting evidence
  contextual                   — questions, clarifications, corrections
  unresolved                   — events in cluster with no clear role

Limitations (documented)
------------------------
- Coreference is not resolved; two proposals on the same topic may
  produce separate decision candidates.
- Temporal proximity is a heuristic, not a semantic grouping.
- No participant influence scores are computed (Phase 10).
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
)
from src.meeting.evidence import (
    EvidenceExtractionResult,
    EvidenceRelation,
    load_evidence_json,
)
from src.utils.config import get
from src.utils.logging import get_logger

logger = get_logger("meeting.decisions")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DECISION_STATUSES = ("confirmed", "probable", "unresolved", "conflicting")

PARTICIPANT_ROLES = (
    "proposer", "objector", "evidence_provider",
    "reviser", "supporter", "final_decision_maker",
)

LINEAGE_RELATIONSHIPS = (
    "leads_to", "challenges", "supports", "contradicts",
    "modifies", "agrees_with", "results_in", "supported_by",
)

IMPACT_LEVELS = (
    "directly_decision_relevant",
    "indirectly_decision_relevant",
    "contextual",
    "unresolved",
)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class LineageEdge:
    """A directed edge in the decision lineage graph."""
    source: str       # event_id
    relationship: str # one of LINEAGE_RELATIONSHIPS
    target: str       # event_id


@dataclass
class ParticipantRole:
    """A speaker's role within a single decision."""
    speaker: str
    role: str         # one of PARTICIPANT_ROLES


@dataclass
class EventImpact:
    """Decision-relevance classification for an event within a decision."""
    event_id: str
    impact: str       # one of IMPACT_LEVELS


@dataclass
class Decision:
    """
    A fully reconstructed decision with lineage.

    All fields that may be absent are typed as | None or empty list.
    confidence is intentionally None unless a reliable estimate exists.
    """
    decision_id: str
    status: str                         # confirmed | probable | unresolved | conflicting
    topic: str | None                   # derived from proposal text; None if unavailable
    proposal: dict[str, Any] | None     # {event_id, speaker, text}
    discussion: list[dict[str, Any]]    # [{event_id, speaker, event_type, text}]
    supporting_evidence: list[dict[str, Any]]  # [{event_id, slide_id, relationship}]
    revisions: list[dict[str, Any]]     # [{event_id, text}]
    agreements: list[dict[str, Any]]    # [{event_id, speaker}]
    final_decision: dict[str, Any] | None      # {event_id, text}
    participants: list[str]
    participant_roles: list[ParticipantRole]
    supporting_segments: list[int]      # source_segment_ids
    supporting_slides: list[str]        # slide_ids
    lineage: list[LineageEdge]
    event_impacts: list[EventImpact]
    confidence: float | None            # None — not estimated in Phase 9


@dataclass
class DecisionResult:
    """Container for all reconstructed decisions in a meeting."""
    meeting_id: str
    decisions: list[Decision] = field(default_factory=list)

    def by_status(self, status: str) -> list[Decision]:
        return [d for d in self.decisions if d.status == status]

    def count_by_status(self) -> dict[str, int]:
        counts: dict[str, int] = {s: 0 for s in DECISION_STATUSES}
        for d in self.decisions:
            counts[d.status] = counts.get(d.status, 0) + 1
        return {k: v for k, v in counts.items() if v > 0}


# ---------------------------------------------------------------------------
# Graph utilities (NetworkX optional but preferred)
# ---------------------------------------------------------------------------

def _build_networkx_graph(decision: Decision) -> Any:
    """Build a NetworkX DiGraph for one decision.  Returns None if unavailable."""
    try:
        import networkx as nx  # type: ignore
    except ImportError:
        return None

    G = nx.DiGraph()
    G.graph["decision_id"] = decision.decision_id
    G.graph["status"] = decision.status

    # Add nodes
    all_event_ids: set[str] = set()
    if decision.proposal:
        all_event_ids.add(decision.proposal["event_id"])
    for d in decision.discussion:
        all_event_ids.add(d["event_id"])
    for e in decision.supporting_evidence:
        if not e["event_id"].startswith("slide:"):
            all_event_ids.add(e["event_id"])
    for r in decision.revisions:
        all_event_ids.add(r["event_id"])
    for a in decision.agreements:
        all_event_ids.add(a["event_id"])
    if decision.final_decision:
        all_event_ids.add(decision.final_decision["event_id"])

    for eid in all_event_ids:
        G.add_node(eid)

    # Add edges
    for edge in decision.lineage:
        G.add_edge(edge.source, edge.target, relationship=edge.relationship)

    return G


def _graph_to_dict(G: Any) -> dict[str, Any]:
    """Serialise a NetworkX DiGraph to a plain dict."""
    if G is None:
        return {}
    return {
        "nodes": list(G.nodes()),
        "edges": [
            {"source": u, "target": v, "relationship": d.get("relationship", "")}
            for u, v, d in G.edges(data=True)
        ],
        "attributes": dict(G.graph),
    }


# ---------------------------------------------------------------------------
# Reconstruction helpers
# ---------------------------------------------------------------------------

def _topic_from_text(text: str | None) -> str | None:
    """Extract a very short topic label from proposal text (first 60 chars)."""
    if not text:
        return None
    stripped = text.strip()
    return stripped[:60] + ("…" if len(stripped) > 60 else "")


def _event_index(events: list[MeetingEvent]) -> dict[str, MeetingEvent]:
    return {e.event_id: e for e in events}


def _evidence_for_event(
    event_id: str,
    relations: list[EvidenceRelation],
) -> list[EvidenceRelation]:
    """Return evidence relations where target is event_id."""
    return [r for r in relations if r.target_event_id == event_id]


def _events_in_window(
    anchor: MeetingEvent,
    all_events: list[MeetingEvent],
    window_s: float,
) -> list[MeetingEvent]:
    """
    Collect all events whose time range overlaps or is adjacent to
    [anchor.start - window_s, anchor.end + window_s].
    """
    lo = anchor.start - window_s
    hi = anchor.end + window_s
    return [e for e in all_events if e.start <= hi and e.end >= lo]


def _classify_impact(
    event: MeetingEvent,
    proposal_id: str | None,
    final_id: str | None,
    revision_ids: set[str],
) -> str:
    """Classify decision relevance of an event within a cluster."""
    if event.event_id in {proposal_id, final_id}:
        return "directly_decision_relevant"
    if event.event_id in revision_ids:
        return "directly_decision_relevant"
    if event.event_type in ("objection", "evidence", "agreement", "disagreement"):
        return "indirectly_decision_relevant"
    if event.event_type in ("question", "clarification", "correction"):
        return "contextual"
    return "unresolved"


def _infer_status(
    cluster_events: list[MeetingEvent],
    has_final_decision: bool,
) -> str:
    """
    Determine decision status from the events in a cluster.

    NOTE: These heuristics are prototypes and have not been validated
    against annotated data.
    """
    types = {e.event_type for e in cluster_events}

    if has_final_decision:
        return "confirmed"

    has_agreement = "agreement" in types
    has_unresolved_objection = "objection" in types and "agreement" not in types

    if has_agreement:
        return "probable"

    # Multiple proposals with objections and no resolution → conflicting
    proposal_count = sum(1 for e in cluster_events if e.event_type == "proposal")
    if proposal_count > 1 and has_unresolved_objection:
        return "conflicting"

    return "unresolved"


def _build_lineage(
    cluster: list[MeetingEvent],
    relations: list[EvidenceRelation],
    proposal_id: str | None,
    final_id: str | None,
) -> list[LineageEdge]:
    """
    Build lineage edges from:
    a) evidence relations within the cluster
    b) inferred structural edges (proposal→revision, revision→decision, etc.)
    """
    cluster_ids = {e.event_id for e in cluster}
    edges: list[LineageEdge] = []
    seen: set[tuple[str, str, str]] = set()

    def _add_edge(src: str, rel: str, tgt: str) -> None:
        key = (src, rel, tgt)
        if key not in seen and src != tgt:
            seen.add(key)
            edges.append(LineageEdge(source=src, relationship=rel, target=tgt))

    # Evidence-relation edges (only for events in this cluster)
    rel_map = {
        "supports":    "supported_by",  # reversed: target supported_by source
        "contradicts": "challenges",
        "modifies":    "modifies",
        "clarifies":   "leads_to",
        "affects":     "leads_to",
        "references":  "leads_to",
    }
    for r in relations:
        src = r.source_event_id
        tgt = r.target_event_id
        if src.startswith("slide:"):
            continue
        if src not in cluster_ids or tgt not in cluster_ids:
            continue
        rel_label = rel_map.get(r.relationship, "leads_to")
        _add_edge(src, rel_label, tgt)

    # Inferred structural edges within the cluster (sorted by time)
    sorted_cluster = sorted(cluster, key=lambda e: e.start)
    for i, ev in enumerate(sorted_cluster):
        for prev in sorted_cluster[:i]:
            # proposal → revision
            if prev.event_type == "proposal" and ev.event_type == "revision":
                _add_edge(prev.event_id, "leads_to", ev.event_id)
                _add_edge(ev.event_id, "modifies", prev.event_id)
            # proposal/revision → agreement
            elif prev.event_type in ("proposal", "revision") and ev.event_type == "agreement":
                _add_edge(ev.event_id, "agrees_with", prev.event_id)
            # proposal/revision/agreement → decision
            elif prev.event_type in ("proposal", "revision", "agreement") and ev.event_type == "decision":
                _add_edge(prev.event_id, "results_in", ev.event_id)
            # proposal → objection
            elif prev.event_type == "proposal" and ev.event_type == "objection":
                _add_edge(ev.event_id, "challenges", prev.event_id)
            # evidence → proposal/revision
            elif ev.event_type == "evidence" and prev.event_type in ("proposal", "revision"):
                _add_edge(ev.event_id, "supports", prev.event_id)

    return edges


# ---------------------------------------------------------------------------
# Core reconstruction
# ---------------------------------------------------------------------------

def reconstruct_decisions(
    event_result: EventExtractionResult,
    evidence_result: EvidenceExtractionResult,
    temporal_window: float = 120.0,
    require_final_decision: bool = False,
) -> DecisionResult:
    """
    Reconstruct structured decisions from events and evidence.

    Parameters
    ----------
    event_result : EventExtractionResult
    evidence_result : EvidenceExtractionResult
    temporal_window : float
        Seconds around an anchor event to collect cluster members.
        Default: 120 s.  Prototype value — not validated.
    require_final_decision : bool
        If True, only produce decisions with an explicit "decision" event.
        Default: False.

    Returns
    -------
    DecisionResult
    """
    events = sorted(event_result.events, key=lambda e: e.start)
    relations = evidence_result.relations
    ev_index = _event_index(events)

    # ---- Step 1: identify anchors ----
    anchors: list[MeetingEvent] = []
    for ev in events:
        if ev.event_type == "decision":
            anchors.append(ev)
        elif ev.event_type == "agreement" and not require_final_decision:
            # Only count agreement as anchor if there is a preceding proposal
            has_proposal = any(
                p.event_type == "proposal" and p.start <= ev.start
                for p in events
            )
            if has_proposal:
                anchors.append(ev)

    # De-duplicate: if two anchors are within temporal_window/2 of each other,
    # keep only the first (they likely belong to the same discussion).
    deduplicated: list[MeetingEvent] = []
    last_anchor_end: float = -1e9
    for anchor in sorted(anchors, key=lambda a: a.start):
        if anchor.start - last_anchor_end > temporal_window / 2:
            deduplicated.append(anchor)
            last_anchor_end = anchor.end

    # If no anchors found and proposals exist, treat each proposal as unresolved
    if not deduplicated:
        proposals = [e for e in events if e.event_type == "proposal"]
        deduplicated = proposals[:] if proposals else []

    result = DecisionResult(meeting_id=event_result.meeting_id)
    used_event_ids: set[str] = set()
    decision_counter = 0

    for anchor in deduplicated:
        # ---- Step 2: build cluster ----
        cluster = _events_in_window(anchor, events, temporal_window)
        if not cluster:
            continue

        # Avoid same event appearing in multiple decisions (use earliest cluster)
        cluster = [e for e in cluster if e.event_id not in used_event_ids]
        if not cluster:
            continue

        for e in cluster:
            used_event_ids.add(e.event_id)

        cluster_ids = {e.event_id for e in cluster}

        # ---- Step 3: classify cluster members ----
        proposals_ev = sorted(
            [e for e in cluster if e.event_type == "proposal"],
            key=lambda e: e.start,
        )
        objections_ev = [e for e in cluster if e.event_type == "objection"]
        evidence_ev   = [e for e in cluster if e.event_type == "evidence"]
        revisions_ev  = [e for e in cluster if e.event_type == "revision"]
        agreements_ev = [e for e in cluster if e.event_type == "agreement"]
        decision_ev   = [e for e in cluster if e.event_type == "decision"]
        discussion_ev = [
            e for e in cluster
            if e.event_type not in {"proposal", "decision"}
        ]

        # Anchor-based final decision
        final_event = (
            decision_ev[-1] if decision_ev
            else (anchor if anchor.event_type == "decision" else None)
        )
        has_final = final_event is not None and final_event.event_type == "decision"

        # ---- Step 4: status ----
        status = _infer_status(cluster, has_final)

        # ---- Step 5: participants & roles ----
        participants: list[str] = []
        participant_roles: list[ParticipantRole] = []
        seen_speakers: set[str] = set()

        def _add_role(speaker: str, role: str) -> None:
            if speaker not in seen_speakers:
                participants.append(speaker)
                seen_speakers.add(speaker)
            participant_roles.append(ParticipantRole(speaker=speaker, role=role))

        if proposals_ev:
            _add_role(proposals_ev[0].speaker, "proposer")
        for e in objections_ev:
            _add_role(e.speaker, "objector")
        for e in evidence_ev:
            _add_role(e.speaker, "evidence_provider")
        for e in revisions_ev:
            _add_role(e.speaker, "reviser")
        for e in agreements_ev:
            _add_role(e.speaker, "supporter")
        if final_event:
            _add_role(final_event.speaker, "final_decision_maker")
        # Any remaining cluster members as participants
        for e in cluster:
            if e.speaker not in seen_speakers:
                participants.append(e.speaker)
                seen_speakers.add(e.speaker)

        # ---- Step 6: slide grounding ----
        supporting_slides: list[str] = sorted({
            e.slide_id for e in cluster if e.slide_id is not None
        })
        supporting_segments: list[int] = sorted({
            e.source_segment_id for e in cluster
        })

        # ---- Step 7: supporting evidence entries ----
        cluster_relations = [
            r for r in relations
            if (r.target_event_id in cluster_ids
                and not r.source_event_id.startswith("slide:"))
        ]
        slide_relations = [
            r for r in relations
            if r.target_event_id in cluster_ids and r.source_event_id.startswith("slide:")
        ]

        supporting_evidence_list: list[dict[str, Any]] = [
            {
                "event_id": r.source_event_id,
                "slide_id": r.slide_id,
                "relationship": r.relationship,
            }
            for r in slide_relations
        ] + [
            {
                "event_id": r.source_event_id,
                "slide_id": r.slide_id,
                "relationship": r.relationship,
            }
            for r in cluster_relations
            if r.source_event_id in cluster_ids
        ]

        # ---- Step 8: lineage ----
        lineage = _build_lineage(cluster, cluster_relations + slide_relations, 
                                  proposals_ev[0].event_id if proposals_ev else None,
                                  final_event.event_id if final_event else None)

        # ---- Step 9: event impact classification ----
        revision_ids = {e.event_id for e in revisions_ev}
        event_impacts = [
            EventImpact(
                event_id=e.event_id,
                impact=_classify_impact(
                    e,
                    proposals_ev[0].event_id if proposals_ev else None,
                    final_event.event_id if final_event else None,
                    revision_ids,
                ),
            )
            for e in cluster
        ]

        # ---- Step 10: build Decision object ----
        decision_counter += 1
        decision = Decision(
            decision_id=f"decision_{decision_counter:03d}",
            status=status,
            topic=_topic_from_text(proposals_ev[0].text if proposals_ev else
                                   (final_event.text if final_event else None)),
            proposal=(
                {"event_id": proposals_ev[0].event_id,
                 "speaker": proposals_ev[0].speaker,
                 "text": proposals_ev[0].text}
                if proposals_ev else None
            ),
            discussion=[
                {"event_id": e.event_id,
                 "speaker": e.speaker,
                 "event_type": e.event_type,
                 "text": e.text}
                for e in discussion_ev
            ],
            supporting_evidence=supporting_evidence_list,
            revisions=[
                {"event_id": e.event_id, "text": e.text}
                for e in revisions_ev
            ],
            agreements=[
                {"event_id": e.event_id, "speaker": e.speaker}
                for e in agreements_ev
            ],
            final_decision=(
                {"event_id": final_event.event_id, "text": final_event.text}
                if final_event else None
            ),
            participants=participants,
            participant_roles=participant_roles,
            supporting_segments=supporting_segments,
            supporting_slides=supporting_slides,
            lineage=lineage,
            event_impacts=event_impacts,
            confidence=None,   # not estimated in Phase 9
        )
        result.decisions.append(decision)

    return result


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def _decision_to_dict(d: Decision) -> dict[str, Any]:
    return {
        "decision_id": d.decision_id,
        "status": d.status,
        "topic": d.topic,
        "proposal": d.proposal,
        "discussion": d.discussion,
        "supporting_evidence": d.supporting_evidence,
        "revisions": d.revisions,
        "agreements": d.agreements,
        "final_decision": d.final_decision,
        "participants": d.participants,
        "participant_roles": [
            {"speaker": pr.speaker, "role": pr.role}
            for pr in d.participant_roles
        ],
        "supporting_segments": d.supporting_segments,
        "supporting_slides": d.supporting_slides,
        "lineage": [
            {"source": e.source, "relationship": e.relationship, "target": e.target}
            for e in d.lineage
        ],
        "event_impacts": [
            {"event_id": ei.event_id, "impact": ei.impact}
            for ei in d.event_impacts
        ],
        "confidence": d.confidence,
    }


def save_decisions_json(result: DecisionResult, output_path: Path) -> None:
    """Write DecisionResult to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "meeting_id": result.meeting_id,
        "num_decisions": len(result.decisions),
        "decisions": [_decision_to_dict(d) for d in result.decisions],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    logger.info("Decisions JSON saved: %s", output_path)


def save_decision_graph_json(result: DecisionResult, output_path: Path) -> None:
    """Serialise NetworkX decision graphs to JSON (node/edge lists)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    graphs: list[dict[str, Any]] = []
    for decision in result.decisions:
        G = _build_networkx_graph(decision)
        graphs.append({
            "decision_id": decision.decision_id,
            "graph": _graph_to_dict(G),
        })
    payload = {"meeting_id": result.meeting_id, "decision_graphs": graphs}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    logger.info("Decision graph JSON saved: %s", output_path)


def load_decisions_json(path: Path) -> DecisionResult:
    """Load a DecisionResult from a saved JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Decisions JSON not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    decisions: list[Decision] = []
    for d in data.get("decisions", []):
        decisions.append(Decision(
            decision_id=d["decision_id"],
            status=d["status"],
            topic=d.get("topic"),
            proposal=d.get("proposal"),
            discussion=d.get("discussion", []),
            supporting_evidence=d.get("supporting_evidence", []),
            revisions=d.get("revisions", []),
            agreements=d.get("agreements", []),
            final_decision=d.get("final_decision"),
            participants=d.get("participants", []),
            participant_roles=[
                ParticipantRole(speaker=pr["speaker"], role=pr["role"])
                for pr in d.get("participant_roles", [])
            ],
            supporting_segments=d.get("supporting_segments", []),
            supporting_slides=d.get("supporting_slides", []),
            lineage=[
                LineageEdge(
                    source=e["source"],
                    relationship=e["relationship"],
                    target=e["target"],
                )
                for e in d.get("lineage", [])
            ],
            event_impacts=[
                EventImpact(event_id=ei["event_id"], impact=ei["impact"])
                for ei in d.get("event_impacts", [])
            ],
            confidence=d.get("confidence"),
        ))

    return DecisionResult(meeting_id=data["meeting_id"], decisions=decisions)


# ---------------------------------------------------------------------------
# Top-level runner
# ---------------------------------------------------------------------------

def run_decision_reconstruction(
    events_path: Path,
    evidence_path: Path,
    meeting_id: str | None = None,
    output_dir: Path | None = None,
) -> tuple[DecisionResult, Path, Path]:
    """
    Reconstruct decisions from Phase 8 outputs.

    Parameters
    ----------
    events_path : Path
        Path to <meeting_id>_events.json
    evidence_path : Path
        Path to <meeting_id>_evidence.json
    meeting_id : str | None
        Override; derived from events file if None.
    output_dir : Path | None
        Defaults to data/processed/decisions/.

    Returns
    -------
    (DecisionResult, decisions_json_path, graph_json_path)
    """
    t0 = time.time()

    if not events_path.exists():
        raise FileNotFoundError(f"Events JSON not found: {events_path}")
    if not evidence_path.exists():
        raise FileNotFoundError(f"Evidence JSON not found: {evidence_path}")

    event_result = load_events_json(events_path)
    evidence_result = load_evidence_json(evidence_path)
    meeting_id = meeting_id or event_result.meeting_id

    # Config
    temporal_window = float(get("decision_analysis.temporal_window", 120.0))
    require_final = bool(get("decision_analysis.require_final_decision", False))

    logger.info(
        "Decision reconstruction | meeting=%s | events=%d | relations=%d | window=%.0fs",
        meeting_id,
        len(event_result.events),
        len(evidence_result.relations),
        temporal_window,
    )

    result = reconstruct_decisions(
        event_result,
        evidence_result,
        temporal_window=temporal_window,
        require_final_decision=require_final,
    )

    elapsed = time.time() - t0
    status_counts = result.count_by_status()
    lineage_total = sum(len(d.lineage) for d in result.decisions)

    logger.info(
        "Reconstructed %d decisions in %.2fs | status=%s | lineage_edges=%d",
        len(result.decisions), elapsed, status_counts, lineage_total,
    )

    out_dir = output_dir or Path("data/processed/decisions")
    out_dir.mkdir(parents=True, exist_ok=True)

    decisions_path = out_dir / f"{meeting_id}_decisions.json"
    graph_path = out_dir / f"{meeting_id}_decision_graph.json"

    save_decisions_json(result, decisions_path)
    save_decision_graph_json(result, graph_path)

    logger.info("Decisions output  : %s", decisions_path)
    logger.info("Graph output      : %s", graph_path)

    return result, decisions_path, graph_path
