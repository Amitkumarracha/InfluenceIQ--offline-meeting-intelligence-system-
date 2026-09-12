"""
Final meeting report generator — Phase 13.

Consumes structured JSON outputs from all previous phases and assembles
a MeetingReport object.  Does NOT rerun any ML model.

All report content is derived from existing structured outputs.
Missing sections are marked explicitly — nothing is fabricated.

Sections
--------
1.  meeting_overview
2.  participants
3.  executive_summary
4.  topics
5.  slide_discussions
6.  proposals
7.  evidence_items
8.  decisions
9.  action_items
10. interactions
11. influence
12. influence_vs_speaking
13. evaluation
14. ablation
15. traceability
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.utils.logging import get_logger

logger = get_logger("report.generator")

_NOT_AVAILABLE = "Not available — this analysis has not been executed."


# ---------------------------------------------------------------------------
# Report data structures
# ---------------------------------------------------------------------------

@dataclass
class MeetingOverview:
    meeting_id: str
    duration_s: float | None
    num_participants: int
    num_slides: int | None
    num_events: int
    num_decisions: int
    num_action_items: int
    num_interactions: int


@dataclass
class ParticipantSummary:
    speaker_id: str
    speaking_duration_s: float | None
    num_turns: int
    interactions_initiated: int
    interactions_received: int
    influence_score: float | None
    influence_rank: int | None
    decision_linked_events: int
    roles: list[str]                    # roles across all decisions
    supporting_decisions: list[str]


@dataclass
class DecisionReport:
    decision_id: str
    status: str
    topic: str | None
    proposal_text: str | None
    proposal_speaker: str | None
    proposal_event_id: str | None
    objections: list[dict[str, Any]]
    evidence_items: list[dict[str, Any]]
    revisions: list[dict[str, Any]]
    agreements: list[dict[str, Any]]
    final_decision_text: str | None
    final_decision_event_id: str | None
    participants: list[str]
    supporting_slides: list[str]
    supporting_segments: list[int]
    lineage_text: str               # textual lineage chain
    confidence: float | None


@dataclass
class ActionItem:
    text: str
    speaker: str | None
    timestamp: float | None
    event_id: str
    related_decision_id: str | None
    related_slide_id: str | None


@dataclass
class InfluenceReport:
    speaker_id: str
    rank: int
    score: float
    features: dict[str, float]
    raw_features: dict[str, float]
    explanation: list[str]
    supporting_decisions: list[str]
    supporting_events: list[str]
    decision_contributions: list[dict[str, Any]]


@dataclass
class MeetingReport:
    meeting_id: str
    meeting_overview: MeetingOverview
    participants: list[ParticipantSummary]
    executive_summary: dict[str, Any]
    topics: list[dict[str, Any]]
    slide_discussions: list[dict[str, Any]]
    proposals: list[dict[str, Any]]
    evidence_items: list[dict[str, Any]]
    decisions: list[DecisionReport]
    action_items: list[ActionItem]
    interactions: dict[str, Any]
    influence: list[InfluenceReport]
    influence_vs_speaking: list[dict[str, Any]]
    evaluation: dict[str, Any]
    ablation: dict[str, Any]
    traceability: dict[str, Any]


# ---------------------------------------------------------------------------
# Timestamp formatter
# ---------------------------------------------------------------------------

def _fmt_ts(seconds: float | None) -> str:
    if seconds is None:
        return "N/A"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ---------------------------------------------------------------------------
# Lineage text builder
# ---------------------------------------------------------------------------

def _build_lineage_text(decision: dict[str, Any]) -> str:
    """
    Build a simple textual chain showing how a decision evolved.
    Only uses events that actually appear in the decision dict.
    """
    parts: list[str] = []
    if decision.get("proposal"):
        sp = decision["proposal"].get("speaker", "?")
        parts.append(f"Proposal ({sp})")
    for d in decision.get("discussion", []):
        etype = d.get("event_type", "?")
        sp = d.get("speaker", "?")
        parts.append(f"{etype.capitalize()} ({sp})")
    for r in decision.get("revisions", []):
        parts.append("Revision")
    for a in decision.get("agreements", []):
        sp = a.get("speaker", "?")
        parts.append(f"Agreement ({sp})")
    if decision.get("final_decision"):
        parts.append(f"Final Decision [status: {decision.get('status', '?')}]")
    elif decision.get("status") == "unresolved":
        parts.append("Unresolved")
    elif decision.get("status") == "conflicting":
        parts.append("Conflicting — no resolution")

    return " → ".join(parts) if parts else "No lineage data available"


# ---------------------------------------------------------------------------
# Core loader helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Could not load %s: %s", path, exc)
        return None


def _resolve_input_paths(meeting_id: str, input_dir: Path) -> dict[str, Path]:
    ev_dir   = input_dir / "events"
    dec_dir  = input_dir / "decisions"
    int_dir  = input_dir / "interactions"
    inf_dir  = input_dir / "influence"
    sld_dir  = input_dir / "slides"
    aln_dir  = input_dir / "alignment"
    return {
        "events":       ev_dir  / f"{meeting_id}_events.json",
        "evidence":     ev_dir  / f"{meeting_id}_evidence.json",
        "decisions":    dec_dir / f"{meeting_id}_decisions.json",
        "interactions": int_dir / f"{meeting_id}_interactions.json",
        "influence":    inf_dir / f"{meeting_id}_influence.json",
        "slides":       sld_dir / f"{meeting_id}_slides.json",
        "alignment":    aln_dir / f"{meeting_id}_alignment.json",
        "eval_metrics": Path("outputs/evaluation") / f"{meeting_id}_metrics.json",
        "eval_ablation":Path("outputs/evaluation") / f"{meeting_id}_ablation.json",
        "baselines":    Path("data/processed/influence") / f"{meeting_id}_baselines.json",
    }


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _build_overview(
    meeting_id: str,
    events_data: dict | None,
    decisions_data: dict | None,
    interactions_data: dict | None,
    slides_data: dict | None,
) -> MeetingOverview:
    events = (events_data or {}).get("events", [])
    decisions = (decisions_data or {}).get("decisions", [])
    action_items = [e for e in events if e.get("event_type") == "action_item"]
    interactions = (interactions_data or {}).get("interactions", [])
    slides = (slides_data or {}).get("slides", [])

    # Duration: max end time of events
    duration_s: float | None = None
    if events:
        try:
            duration_s = max(float(e.get("end", 0)) for e in events)
        except (ValueError, TypeError):
            pass

    participants = sorted({e.get("speaker", "UNKNOWN") for e in events})

    return MeetingOverview(
        meeting_id=meeting_id,
        duration_s=duration_s,
        num_participants=len(participants),
        num_slides=len(slides) if slides_data else None,
        num_events=len(events),
        num_decisions=len(decisions),
        num_action_items=len(action_items),
        num_interactions=len(interactions),
    )


def _build_participants(
    events_data: dict | None,
    interactions_data: dict | None,
    influence_data: dict | None,
    decisions_data: dict | None,
) -> list[ParticipantSummary]:
    events = (events_data or {}).get("events", [])
    all_speakers = sorted({e.get("speaker", "UNKNOWN") for e in events})

    # Speaking duration and turns
    speaking_time: dict[str, float] = {sp: 0.0 for sp in all_speakers}
    turn_count: dict[str, int] = {sp: 0 for sp in all_speakers}
    for e in events:
        sp = e.get("speaker", "UNKNOWN")
        if sp in speaking_time:
            speaking_time[sp] += float(e.get("end", 0)) - float(e.get("start", 0))
            turn_count[sp] += 1

    # Decision-linked events
    dec_event_ids: set[str] = set()
    all_decisions = (decisions_data or {}).get("decisions", [])
    for d in all_decisions:
        for field_name in ("proposal", "final_decision"):
            item = d.get(field_name)
            if item and "event_id" in item:
                dec_event_ids.add(item["event_id"])
        for lst_name in ("discussion", "revisions", "agreements"):
            for item in d.get(lst_name, []):
                if "event_id" in item:
                    dec_event_ids.add(item["event_id"])
    ev_index = {e["event_id"]: e for e in events if "event_id" in e}
    dec_event_count: dict[str, int] = {sp: 0 for sp in all_speakers}
    for eid in dec_event_ids:
        ev = ev_index.get(eid)
        if ev and ev.get("speaker") in dec_event_count:
            dec_event_count[ev["speaker"]] += 1

    # Roles from decisions
    roles_map: dict[str, set[str]] = {sp: set() for sp in all_speakers}
    supporting_dec_map: dict[str, list[str]] = {sp: [] for sp in all_speakers}
    for d in all_decisions:
        did = d.get("decision_id", "")
        for pr in d.get("participant_roles", []):
            sp = pr.get("speaker")
            if sp in roles_map:
                roles_map[sp].add(pr.get("role", ""))
                if did and did not in supporting_dec_map[sp]:
                    supporting_dec_map[sp].append(did)

    # Interaction stats
    stats_map: dict[str, dict] = {}
    for s in (interactions_data or {}).get("participant_stats", []):
        stats_map[s["participant"]] = s

    # Influence
    inf_map: dict[str, dict] = {}
    for p in (influence_data or {}).get("participants", []):
        inf_map[p["participant"]] = p

    result: list[ParticipantSummary] = []
    for sp in all_speakers:
        stats = stats_map.get(sp, {})
        inf   = inf_map.get(sp, {})
        result.append(ParticipantSummary(
            speaker_id=sp,
            speaking_duration_s=round(speaking_time[sp], 2),
            num_turns=turn_count[sp],
            interactions_initiated=stats.get("interactions_initiated", 0),
            interactions_received=stats.get("interactions_received", 0),
            influence_score=inf.get("influence_score"),
            influence_rank=inf.get("rank"),
            decision_linked_events=dec_event_count[sp],
            roles=sorted(roles_map[sp]),
            supporting_decisions=supporting_dec_map[sp],
        ))
    return result


def _build_executive_summary(
    events_data: dict | None,
    decisions_data: dict | None,
) -> dict[str, Any]:
    """
    Build an executive summary from structured outputs only.
    No LLM — extracts actual proposals, decisions, and action items.
    """
    events = (events_data or {}).get("events", [])
    decisions = (decisions_data or {}).get("decisions", [])

    proposals = [e for e in events if e.get("event_type") == "proposal"]
    action_items = [e for e in events if e.get("event_type") == "action_item"]
    confirmed = [d for d in decisions if d.get("status") == "confirmed"]
    unresolved = [d for d in decisions if d.get("status") == "unresolved"]

    return {
        "method": "structured_extraction",
        "note": (
            "This summary is derived from structured event/decision outputs. "
            "No language model was used. Content reflects detected events only."
        ),
        "num_proposals": len(proposals),
        "num_confirmed_decisions": len(confirmed),
        "num_unresolved_proposals": len(unresolved),
        "num_action_items": len(action_items),
        "major_proposals": [
            {"text": e.get("text", ""), "speaker": e.get("speaker"), "timestamp": e.get("start")}
            for e in proposals[:5]
        ],
        "confirmed_decisions": [
            {
                "decision_id": d.get("decision_id"),
                "topic": d.get("topic"),
                "final_decision": d.get("final_decision", {}).get("text") if d.get("final_decision") else None,
            }
            for d in confirmed
        ],
        "action_items_summary": [
            {"text": e.get("text", ""), "speaker": e.get("speaker"), "timestamp": e.get("start")}
            for e in action_items[:5]
        ],
    }


def _build_slide_discussions(
    events_data: dict | None,
    alignment_data: dict | None,
) -> list[dict[str, Any]]:
    events = (events_data or {}).get("events", [])
    # Group events by slide_id
    slide_groups: dict[str, list[dict]] = {}
    for e in events:
        sid = e.get("slide_id")
        if sid:
            slide_groups.setdefault(sid, []).append(e)

    result: list[dict[str, Any]] = []
    for slide_id, slide_events in sorted(slide_groups.items()):
        result.append({
            "slide_id": slide_id,
            "num_events": len(slide_events),
            "speakers": sorted({e.get("speaker", "?") for e in slide_events}),
            "event_types": sorted({e.get("event_type", "?") for e in slide_events}),
            "segments": [
                {
                    "event_id": e.get("event_id"),
                    "speaker": e.get("speaker"),
                    "timestamp": _fmt_ts(e.get("start")),
                    "text": e.get("text", ""),
                    "event_type": e.get("event_type"),
                }
                for e in sorted(slide_events, key=lambda x: x.get("start", 0))
            ],
        })
    return result


def _build_proposals(
    events_data: dict | None,
    decisions_data: dict | None,
) -> list[dict[str, Any]]:
    events = (events_data or {}).get("events", [])
    decisions = (decisions_data or {}).get("decisions", [])

    # Map proposal event_id → decision
    proposal_to_decision: dict[str, dict] = {}
    for d in decisions:
        p = d.get("proposal")
        if p:
            proposal_to_decision[p.get("event_id", "")] = d

    proposals = [e for e in events if e.get("event_type") == "proposal"]
    result: list[dict[str, Any]] = []
    for e in proposals:
        dec = proposal_to_decision.get(e.get("event_id", ""))
        result.append({
            "event_id": e.get("event_id"),
            "speaker": e.get("speaker"),
            "timestamp": _fmt_ts(e.get("start")),
            "text": e.get("text", ""),
            "slide_id": e.get("slide_id"),
            "decision_linked": dec is not None,
            "decision_id": dec.get("decision_id") if dec else None,
            "decision_status": dec.get("status") if dec else None,
            "final_outcome": (dec.get("final_decision") or {}).get("text") if dec else None,
        })
    return result


def _build_evidence_items(
    events_data: dict | None,
    evidence_data: dict | None,
) -> list[dict[str, Any]]:
    events = (events_data or {}).get("events", [])
    relations = (evidence_data or {}).get("relations", [])
    ev_index = {e["event_id"]: e for e in events if "event_id" in e}

    result: list[dict[str, Any]] = []
    for rel in relations:
        src_id = rel.get("source_event_id", "")
        if src_id.startswith("slide:"):
            continue
        src_ev = ev_index.get(src_id)
        if not src_ev:
            continue
        tgt_ev = ev_index.get(rel.get("target_event_id", ""))
        result.append({
            "evidence_id": rel.get("evidence_id"),
            "source_speaker": src_ev.get("speaker"),
            "source_event_id": src_id,
            "source_text": src_ev.get("text", ""),
            "source_timestamp": _fmt_ts(src_ev.get("start")),
            "relationship": rel.get("relationship"),
            "target_event_id": rel.get("target_event_id"),
            "target_text": tgt_ev.get("text", "") if tgt_ev else None,
            "slide_id": rel.get("slide_id"),
        })
    return result


def _build_decisions(decisions_data: dict | None) -> list[DecisionReport]:
    decisions = (decisions_data or {}).get("decisions", [])
    result: list[DecisionReport] = []
    for d in decisions:
        proposal = d.get("proposal") or {}
        fd = d.get("final_decision") or {}
        lineage_text = _build_lineage_text(d)
        discussion = d.get("discussion", [])
        objections = [x for x in discussion if x.get("event_type") in ("objection", "disagreement")]
        ev_items   = [x for x in discussion if x.get("event_type") == "evidence"]

        result.append(DecisionReport(
            decision_id=d.get("decision_id", ""),
            status=d.get("status", "unknown"),
            topic=d.get("topic"),
            proposal_text=proposal.get("text"),
            proposal_speaker=proposal.get("speaker"),
            proposal_event_id=proposal.get("event_id"),
            objections=objections,
            evidence_items=ev_items,
            revisions=d.get("revisions", []),
            agreements=d.get("agreements", []),
            final_decision_text=fd.get("text"),
            final_decision_event_id=fd.get("event_id"),
            participants=d.get("participants", []),
            supporting_slides=d.get("supporting_slides", []),
            supporting_segments=d.get("supporting_segments", []),
            lineage_text=lineage_text,
            confidence=d.get("confidence"),
        ))
    return result


def _build_action_items(
    events_data: dict | None,
    decisions_data: dict | None,
) -> list[ActionItem]:
    events = (events_data or {}).get("events", [])
    decisions = (decisions_data or {}).get("decisions", [])

    # event_id → decision_id
    ev_to_dec: dict[str, str] = {}
    for d in decisions:
        for field_name in ("proposal", "final_decision"):
            item = d.get(field_name)
            if item and "event_id" in item:
                ev_to_dec[item["event_id"]] = d["decision_id"]
        for lst in ("discussion", "revisions", "agreements"):
            for item in d.get(lst, []):
                if "event_id" in item:
                    ev_to_dec[item["event_id"]] = d["decision_id"]

    result: list[ActionItem] = []
    for e in events:
        if e.get("event_type") != "action_item":
            continue
        result.append(ActionItem(
            text=e.get("text", ""),
            speaker=e.get("speaker"),
            timestamp=e.get("start"),
            event_id=e.get("event_id", ""),
            related_decision_id=ev_to_dec.get(e.get("event_id", "")),
            related_slide_id=e.get("slide_id"),
        ))
    return result


def _build_interactions(interactions_data: dict | None) -> dict[str, Any]:
    if interactions_data is None:
        return {"status": _NOT_AVAILABLE}

    stats = interactions_data.get("participant_stats", [])
    interactions = interactions_data.get("interactions", [])

    type_counts: dict[str, int] = {}
    for i in interactions:
        t = i.get("interaction_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    # Textual graph summary
    graph_lines: list[str] = []
    for intr in interactions:
        src = intr.get("source_speaker", "?")
        tgt = intr.get("target_speaker")
        itype = intr.get("interaction_type", "?")
        if tgt:
            graph_lines.append(f"{src} --[{itype}]--> {tgt}")

    return {
        "total_interactions": len(interactions),
        "interactions_by_type": type_counts,
        "decision_linked": sum(
            1 for i in interactions if i.get("related_decision_id")
        ),
        "participant_stats": stats,
        "graph_summary": graph_lines[:50],  # limit for readability
        "note": "Statistics describe conversational interaction, NOT influence.",
    }


def _build_influence(influence_data: dict | None) -> list[InfluenceReport]:
    if influence_data is None:
        return []
    result: list[InfluenceReport] = []
    for p in influence_data.get("participants", []):
        result.append(InfluenceReport(
            speaker_id=p.get("participant", ""),
            rank=p.get("rank", 0),
            score=p.get("influence_score", 0.0),
            features=p.get("features", {}),
            raw_features=p.get("raw_features", {}),
            explanation=p.get("explanation", []),
            supporting_decisions=p.get("supporting_decisions", []),
            supporting_events=p.get("supporting_events", []),
            decision_contributions=p.get("decision_contributions", []),
        ))
    return sorted(result, key=lambda x: x.rank)


def _build_influence_vs_speaking(
    participants: list[ParticipantSummary],
) -> list[dict[str, Any]]:
    if not participants:
        return []
    with_time = [p for p in participants if p.speaking_duration_s is not None]
    if not with_time:
        return []

    speaking_ranked = sorted(with_time, key=lambda p: p.speaking_duration_s or 0, reverse=True)
    influence_ranked = sorted(
        [p for p in with_time if p.influence_rank is not None],
        key=lambda p: p.influence_rank or 999,
    )

    sp_rank_map = {p.speaker_id: i + 1 for i, p in enumerate(speaking_ranked)}
    inf_rank_map = {p.speaker_id: p.influence_rank for p in influence_ranked}

    result: list[dict[str, Any]] = []
    for p in sorted(participants, key=lambda x: x.speaker_id):
        result.append({
            "participant": p.speaker_id,
            "speaking_rank": sp_rank_map.get(p.speaker_id),
            "speaking_duration_s": p.speaking_duration_s,
            "influence_rank": inf_rank_map.get(p.speaker_id),
            "influence_score": p.influence_score,
        })
    return result


def _build_traceability(
    decisions_data: dict | None,
    influence_data: dict | None,
    events_data: dict | None,
) -> dict[str, Any]:
    """Build a traceability index: influence feature → event → speaker → timestamp → slide → decision."""
    events = (events_data or {}).get("events", [])
    ev_index = {e["event_id"]: e for e in events if "event_id" in e}

    chains: list[dict[str, Any]] = []
    for p in (influence_data or {}).get("participants", []):
        sp = p.get("participant")
        for dc in p.get("decision_contributions", []):
            for eid in dc.get("supporting_events", []):
                ev = ev_index.get(eid)
                if ev:
                    chains.append({
                        "participant": sp,
                        "influence_score": p.get("influence_score"),
                        "decision_id": dc.get("decision_id"),
                        "event_id": eid,
                        "event_type": ev.get("event_type"),
                        "speaker": ev.get("speaker"),
                        "timestamp": _fmt_ts(ev.get("start")),
                        "slide_id": ev.get("slide_id"),
                        "text": ev.get("text", "")[:120],
                    })

    return {
        "description": (
            "Each chain traces: participant → influence_score → decision → "
            "event → speaker + timestamp → slide."
        ),
        "chains": chains,
    }


def _build_evaluation(eval_metrics: dict | None) -> dict[str, Any]:
    if eval_metrics is None:
        return {"status": _NOT_AVAILABLE}

    def _format_metric(m: dict | None) -> Any:
        if m is None:
            return _NOT_AVAILABLE
        if m.get("status") == "ground_truth_unavailable":
            return "Not evaluated — ground truth unavailable."
        return m

    return {
        "wer":        _format_metric(eval_metrics.get("wer")),
        "der":        _format_metric(eval_metrics.get("der")),
        "alignment":  _format_metric(eval_metrics.get("alignment")),
        "events":     _format_metric(eval_metrics.get("events")),
        "decisions":  _format_metric(eval_metrics.get("decisions")),
        "lineage":    _format_metric(eval_metrics.get("lineage")),
        "influence":  _format_metric(eval_metrics.get("influence")),
        "efficiency": _format_metric(eval_metrics.get("efficiency")),
    }


def _build_ablation(ablation_data: dict | None) -> dict[str, Any]:
    if ablation_data is None:
        return {"status": "Ablation results are not yet available."}
    ablations = ablation_data.get("ablations", [])
    return {
        "num_experiments": len(ablations),
        "note": ablation_data.get("note", ""),
        "results": [
            {
                "experiment": a.get("experiment"),
                "label": a.get("label"),
                "removed_component": a.get("removed_component"),
                "metrics": a.get("metrics", {}),
            }
            for a in ablations
        ],
    }


# ---------------------------------------------------------------------------
# Top-level generator
# ---------------------------------------------------------------------------

def generate_report(
    meeting_id: str,
    input_dir: Path,
    eval_metrics_path: Path | None = None,
    ablation_path: Path | None = None,
) -> MeetingReport:
    """
    Generate a MeetingReport from existing pipeline outputs.

    Parameters
    ----------
    meeting_id       : Meeting identifier.
    input_dir        : Root of data/processed/ directory.
    eval_metrics_path: Optional path to evaluation metrics JSON.
    ablation_path    : Optional path to ablation JSON.

    Returns
    -------
    MeetingReport
    """
    paths = _resolve_input_paths(meeting_id, input_dir)

    # Load all available outputs
    events_data      = _load_json(paths["events"])
    evidence_data    = _load_json(paths["evidence"])
    decisions_data   = _load_json(paths["decisions"])
    interactions_data = _load_json(paths["interactions"])
    influence_data   = _load_json(paths["influence"])
    slides_data      = _load_json(paths["slides"])
    alignment_data   = _load_json(paths["alignment"])
    eval_data        = _load_json(eval_metrics_path or paths["eval_metrics"])
    ablation_data    = _load_json(ablation_path or paths["eval_ablation"])

    logger.info(
        "Generating report for %s | events=%s | decisions=%s | influence=%s",
        meeting_id,
        "yes" if events_data else "missing",
        "yes" if decisions_data else "missing",
        "yes" if influence_data else "missing",
    )

    overview     = _build_overview(meeting_id, events_data, decisions_data, interactions_data, slides_data)
    participants = _build_participants(events_data, interactions_data, influence_data, decisions_data)
    summary      = _build_executive_summary(events_data, decisions_data)
    slide_discs  = _build_slide_discussions(events_data, alignment_data)
    proposals    = _build_proposals(events_data, decisions_data)
    evidence     = _build_evidence_items(events_data, evidence_data)
    decisions    = _build_decisions(decisions_data)
    action_items = _build_action_items(events_data, decisions_data)
    interactions = _build_interactions(interactions_data)
    influence    = _build_influence(influence_data)
    inf_vs_sp    = _build_influence_vs_speaking(participants)
    evaluation   = _build_evaluation(eval_data)
    ablation     = _build_ablation(ablation_data)
    traceability = _build_traceability(decisions_data, influence_data, events_data)

    # Topics: group by slide or by proposal text (lightweight, no LLM)
    topics: list[dict[str, Any]] = []
    for d in decisions_data.get("decisions", []) if decisions_data else []:
        topics.append({
            "topic": d.get("topic") or f"Discussion — {d.get('decision_id')}",
            "decision_id": d.get("decision_id"),
            "participants": d.get("participants", []),
            "supporting_slides": d.get("supporting_slides", []),
            "status": d.get("status"),
        })

    return MeetingReport(
        meeting_id=meeting_id,
        meeting_overview=overview,
        participants=participants,
        executive_summary=summary,
        topics=topics,
        slide_discussions=slide_discs,
        proposals=proposals,
        evidence_items=evidence,
        decisions=decisions,
        action_items=action_items,
        interactions=interactions,
        influence=influence,
        influence_vs_speaking=inf_vs_sp,
        evaluation=evaluation,
        ablation=ablation,
        traceability=traceability,
    )
