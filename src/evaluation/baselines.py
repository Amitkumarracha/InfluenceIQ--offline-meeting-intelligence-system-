"""
Baseline influence methods — Phase 12.

Six baselines plus the proposed method, all separately identifiable.
No baseline value is fabricated — every score derives from actual
meeting data passed in as arguments.

Baselines
---------
B1  speaking_time               — total speaking duration, normalised
B2  speaking_time_turns         — speaking time + turn count, normalised
B3  decision_event_count        — decision-linked event count, normalised
B4  decision_evidence_count     — decision-linked evidence count, normalised
B5  transcript_only             — events without any PPT/slide grounding
B6  audio_ppt_no_decision       — multimodal features, no decision-impact

Proposed
--------
Full system: Audio + PPT + Events + Evidence + Decision lineage +
             Interaction + Decision-linked contribution

Comparison
----------
build_comparison_table() produces a structured dict (NOT a filled-in
table) that can be populated with actual Spearman/Kendall scores once
human evaluation data is available.
"""

from __future__ import annotations

from typing import Any

from src.meeting.decisions import Decision, DecisionResult
from src.meeting.events import EventExtractionResult, MeetingEvent
from src.meeting.evidence import EvidenceExtractionResult, EvidenceRelation


# ---------------------------------------------------------------------------
# Normalisation helper
# ---------------------------------------------------------------------------

def _max_norm(values: dict[str, float]) -> dict[str, float]:
    """Divide each value by the maximum; returns all-zero if max == 0."""
    mx = max(values.values(), default=0.0)
    if mx <= 0.0:
        return {k: 0.0 for k in values}
    return {k: round(v / mx, 6) for k, v in values.items()}


# ---------------------------------------------------------------------------
# Decision cluster helpers (replicated locally to avoid circular imports)
# ---------------------------------------------------------------------------

def _decision_event_ids(d: Decision) -> set[str]:
    ids: set[str] = set()
    if d.proposal:
        ids.add(d.proposal["event_id"])
    for item in d.discussion:
        ids.add(item["event_id"])
    for item in d.revisions:
        ids.add(item["event_id"])
    for item in d.agreements:
        ids.add(item["event_id"])
    if d.final_decision:
        ids.add(d.final_decision["event_id"])
    return ids


# ---------------------------------------------------------------------------
# B1 — Speaking time
# ---------------------------------------------------------------------------

def baseline_speaking_time(
    event_result: EventExtractionResult,
) -> dict[str, Any]:
    """
    B1: Influence proxy = total speaking duration per participant.

    Uses event durations as a proxy for speaking time.
    For a more accurate baseline the raw transcript segments should
    be used; this limitation is documented here.

    Returns {participant: normalised_score} plus raw seconds.
    """
    speakers = sorted({e.speaker for e in event_result.events})
    raw: dict[str, float] = {sp: 0.0 for sp in speakers}
    for e in event_result.events:
        raw[e.speaker] += e.end - e.start

    norm = _max_norm(raw)
    return {
        "baseline": "B1_speaking_time",
        "description": (
            "Total speaking duration per participant (event duration proxy). "
            "Normalised by max."
        ),
        "scores": norm,
        "raw_seconds": {sp: round(raw[sp], 4) for sp in speakers},
    }


# ---------------------------------------------------------------------------
# B2 — Speaking time + turns
# ---------------------------------------------------------------------------

def baseline_speaking_time_turns(
    event_result: EventExtractionResult,
) -> dict[str, Any]:
    """
    B2: Influence proxy = (normalised speaking time + normalised turn count) / 2.
    """
    speakers = sorted({e.speaker for e in event_result.events})
    raw_time: dict[str, float] = {sp: 0.0 for sp in speakers}
    raw_turns: dict[str, int] = {sp: 0 for sp in speakers}

    for e in event_result.events:
        raw_time[e.speaker] += e.end - e.start
        raw_turns[e.speaker] += 1

    norm_time  = _max_norm(raw_time)
    norm_turns = _max_norm({sp: float(raw_turns[sp]) for sp in speakers})
    combined   = _max_norm({
        sp: (norm_time[sp] + norm_turns[sp]) / 2.0
        for sp in speakers
    })

    return {
        "baseline": "B2_speaking_time_turns",
        "description": "Average of normalised speaking time and normalised turn count.",
        "scores": combined,
        "raw_turns": raw_turns,
        "raw_seconds": {sp: round(raw_time[sp], 4) for sp in speakers},
    }


# ---------------------------------------------------------------------------
# B3 — Decision-linked event count
# ---------------------------------------------------------------------------

def baseline_decision_event_count(
    event_result: EventExtractionResult,
    decision_result: DecisionResult,
) -> dict[str, Any]:
    """
    B3: Influence proxy = number of events inside a decision cluster.
    """
    speakers = sorted({e.speaker for e in event_result.events})
    dec_event_ids: set[str] = set()
    for d in decision_result.decisions:
        dec_event_ids |= _decision_event_ids(d)

    ev_index = {e.event_id: e for e in event_result.events}
    counts: dict[str, int] = {sp: 0 for sp in speakers}
    for eid in dec_event_ids:
        ev = ev_index.get(eid)
        if ev and ev.speaker in counts:
            counts[ev.speaker] += 1

    norm = _max_norm({sp: float(counts[sp]) for sp in speakers})
    return {
        "baseline": "B3_decision_event_count",
        "description": "Count of events belonging to a decision cluster, normalised by max.",
        "scores": norm,
        "raw_counts": counts,
    }


# ---------------------------------------------------------------------------
# B4 — Decision-linked evidence count
# ---------------------------------------------------------------------------

def baseline_decision_evidence_count(
    event_result: EventExtractionResult,
    evidence_result: EvidenceExtractionResult,
    decision_result: DecisionResult,
) -> dict[str, Any]:
    """
    B4: Influence proxy = number of evidence relations whose target is in
    a decision cluster and whose source is a participant event (not a slide).
    """
    speakers = sorted({e.speaker for e in event_result.events})
    dec_event_ids: set[str] = set()
    for d in decision_result.decisions:
        dec_event_ids |= _decision_event_ids(d)

    ev_index = {e.event_id: e for e in event_result.events}
    counts: dict[str, int] = {sp: 0 for sp in speakers}

    for rel in evidence_result.relations:
        if rel.source_event_id.startswith("slide:"):
            continue
        if rel.target_event_id not in dec_event_ids:
            continue
        src_ev = ev_index.get(rel.source_event_id)
        if src_ev and src_ev.speaker in counts:
            counts[src_ev.speaker] += 1

    norm = _max_norm({sp: float(counts[sp]) for sp in speakers})
    return {
        "baseline": "B4_decision_evidence_count",
        "description": (
            "Count of evidence relations whose source is a participant event "
            "and target is in a decision cluster. Normalised by max."
        ),
        "scores": norm,
        "raw_counts": counts,
    }


# ---------------------------------------------------------------------------
# B5 — Transcript-only (no PPT grounding)
# ---------------------------------------------------------------------------

def baseline_transcript_only(
    event_result: EventExtractionResult,
    decision_result: DecisionResult,
) -> dict[str, Any]:
    """
    B5: Like B3 but explicitly excludes any slide-grounded contribution.
    Uses only events that have no slide_id association.
    """
    speakers = sorted({e.speaker for e in event_result.events})
    dec_event_ids: set[str] = set()
    for d in decision_result.decisions:
        dec_event_ids |= _decision_event_ids(d)

    ev_index = {e.event_id: e for e in event_result.events}
    counts: dict[str, int] = {sp: 0 for sp in speakers}

    for eid in dec_event_ids:
        ev = ev_index.get(eid)
        if ev and ev.slide_id is None and ev.speaker in counts:
            counts[ev.speaker] += 1

    norm = _max_norm({sp: float(counts[sp]) for sp in speakers})
    return {
        "baseline": "B5_transcript_only",
        "description": (
            "Decision-linked events WITHOUT any PPT/slide grounding. "
            "Represents transcript-only information."
        ),
        "scores": norm,
        "raw_counts": counts,
    }


# ---------------------------------------------------------------------------
# B6 — Audio + PPT, no decision-impact features
# ---------------------------------------------------------------------------

def baseline_audio_ppt_no_decision(
    event_result: EventExtractionResult,
    evidence_result: EvidenceExtractionResult,
) -> dict[str, Any]:
    """
    B6: Multimodal (audio + PPT) features without decision-linked scoring.

    Uses: speaking time + slide-grounded events (any, not decision-limited).
    This separates cross-modal grounding from decision-impact analysis.
    """
    speakers = sorted({e.speaker for e in event_result.events})
    raw_time: dict[str, float] = {sp: 0.0 for sp in speakers}
    slide_count: dict[str, int] = {sp: 0 for sp in speakers}

    for e in event_result.events:
        raw_time[e.speaker] += e.end - e.start
        if e.slide_id is not None:
            slide_count[e.speaker] += 1

    norm_time  = _max_norm(raw_time)
    norm_slide = _max_norm({sp: float(slide_count[sp]) for sp in speakers})
    combined   = _max_norm({
        sp: (norm_time[sp] + norm_slide[sp]) / 2.0
        for sp in speakers
    })

    return {
        "baseline": "B6_audio_ppt_no_decision",
        "description": (
            "Multimodal baseline: average of normalised speaking time and "
            "normalised slide-grounded event count. "
            "No decision-linked impact features."
        ),
        "scores": combined,
        "raw_seconds": {sp: round(raw_time[sp], 4) for sp in speakers},
        "raw_slide_counts": slide_count,
    }


# ---------------------------------------------------------------------------
# Comparison table builder
# ---------------------------------------------------------------------------

def build_comparison_table(
    baselines: list[dict[str, Any]],
    proposed_scores: dict[str, float] | None = None,
    human_ranking: list[str] | None = None,
) -> dict[str, Any]:
    """
    Build a comparison structure ready to be populated with evaluation metrics.

    Parameters
    ----------
    baselines      : List of baseline result dicts (from functions above).
    proposed_scores: {speaker: score} from Phase 11 InfluenceResult.
    human_ranking  : Human-annotated ranking (if available).

    Returns
    -------
    dict with one row per method.  Spearman/Kendall cells are None until
    human evaluation data is available.

    NOTE: Do NOT populate metric cells with fabricated values.
    """
    from src.evaluation.metrics import evaluate_influence_ranking

    rows: list[dict[str, Any]] = []

    # Baselines
    for b in baselines:
        scores = b.get("scores", {})
        ranking = sorted(scores.keys(), key=lambda sp: scores[sp], reverse=True)
        eval_result = evaluate_influence_ranking(ranking, human_ranking)
        rows.append({
            "method": b["baseline"],
            "description": b.get("description", ""),
            "spearman": eval_result.get("spearman_correlation"),
            "kendall": eval_result.get("kendall_tau"),
            "status": eval_result.get("status"),
        })

    # Proposed
    if proposed_scores is not None:
        ranking = sorted(proposed_scores.keys(),
                         key=lambda sp: proposed_scores[sp], reverse=True)
        eval_result = evaluate_influence_ranking(ranking, human_ranking)
        rows.append({
            "method": "Proposed_decision_linked",
            "description": (
                "Full proposed system: Audio + PPT + Events + Evidence + "
                "Decision lineage + Interaction + Decision-linked contribution"
            ),
            "spearman": eval_result.get("spearman_correlation"),
            "kendall": eval_result.get("kendall_tau"),
            "status": eval_result.get("status"),
        })

    return {
        "comparison_table": rows,
        "note": (
            "Spearman and Kendall values are None until human evaluation "
            "annotations are provided. Do not fabricate these values."
        ),
    }
