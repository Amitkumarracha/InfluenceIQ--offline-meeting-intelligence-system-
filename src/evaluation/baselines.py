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

def _speech_inputs(event_result, transcript_segments):
    if transcript_segments is not None:
        from src.meeting.influence import speech_statistics
        return (*speech_statistics(transcript_segments), "full_transcript")
    seconds, turns = {}, {}
    for event in event_result.events:
        if event.speaker == "UNKNOWN":
            continue
        seconds[event.speaker] = seconds.get(event.speaker, 0) + max(0, event.end-event.start)
        turns[event.speaker] = turns.get(event.speaker, 0) + 1
    return seconds, turns, "event_duration_proxy"


def baseline_speaking_time(event_result, transcript_segments=None) -> dict[str, Any]:
    seconds, _, source = _speech_inputs(event_result, transcript_segments)
    return {"baseline": "B1_speaking_time", "description": "Speaker interval duration, max-normalized; source: " + source,
            "input_source": source, "scores": _max_norm(seconds),
            "raw_seconds": {sp: round(value, 4) for sp, value in seconds.items()}}


def baseline_speaking_time_turns(event_result, transcript_segments=None) -> dict[str, Any]:
    seconds, turns, source = _speech_inputs(event_result, transcript_segments)
    nt, nc = _max_norm(seconds), _max_norm(turns)
    return {"baseline": "B2_speaking_time_turns", "description": "Speaking duration plus turns, max-normalized; source: " + source,
            "input_source": source, "turn_gap_seconds": .5 if transcript_segments is not None else None,
            "scores": _max_norm({sp: (nt[sp]+nc[sp])/2 for sp in seconds}),
            "raw_turns": turns, "raw_seconds": {sp: round(value, 4) for sp, value in seconds.items()}}


# ---------------------------------------------------------------------------
# B3 — Decision-linked event count
# ---------------------------------------------------------------------------

def baseline_decision_event_count(
    event_result: EventExtractionResult,
    decision_result: DecisionResult,
    transcript_segments: list[dict] | None = None,
) -> dict[str, Any]:
    """
    B3: Influence proxy = number of events inside a decision cluster.
    """
    speakers = sorted(({e.speaker for e in event_result.events} |
                       {row.get("speaker", "UNKNOWN") for row in transcript_segments or []}) - {"UNKNOWN", None, ""})
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
    transcript_segments: list[dict] | None = None,
) -> dict[str, Any]:
    """
    B4: Influence proxy = number of evidence relations whose target is in
    a decision cluster and whose source is a participant event (not a slide).
    """
    speakers = sorted(({e.speaker for e in event_result.events} |
                       {row.get("speaker", "UNKNOWN") for row in transcript_segments or []}) - {"UNKNOWN", None, ""})
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
    transcript_segments: list[dict] | None = None,
) -> dict[str, Any]:
    """Reconstruct evidence/decisions after removing slide links, retaining all speech events."""
    from dataclasses import replace
    from src.meeting.evidence import extract_evidence
    from src.meeting.decisions import reconstruct_decisions
    from src.utils.config import get
    ungrounded = EventExtractionResult(event_result.meeting_id,
                                      [replace(event, slide_id=None) for event in event_result.events])
    evidence = extract_evidence(ungrounded, window_s=float(get("meeting_analysis.evidence_window_s", 60)))
    decisions = reconstruct_decisions(ungrounded, evidence,
        temporal_window=float(get("decision_analysis.temporal_window", 120)),
        require_final_decision=bool(get("decision_analysis.require_final_decision", False)))
    result = baseline_decision_event_count(ungrounded, decisions, transcript_segments)
    result.update(baseline="B5_transcript_only", description="Decision-linked event count after evidence/decision rerun with all slide links removed.",
                  input_source="all_transcript_events_without_slide_links")
    return result


# ---------------------------------------------------------------------------
# B6 — Audio + PPT, no decision-impact features
# ---------------------------------------------------------------------------

def baseline_audio_ppt_no_decision(
    event_result: EventExtractionResult,
    evidence_result: EvidenceExtractionResult,
    transcript_segments: list[dict] | None = None,
) -> dict[str, Any]:
    """
    B6: Multimodal (audio + PPT) features without decision-linked scoring.

    Uses: speaking time + slide-grounded events (any, not decision-limited).
    This separates cross-modal grounding from decision-impact analysis.
    """
    raw_time, _, source = _speech_inputs(event_result, transcript_segments)
    speakers = sorted(raw_time)
    slide_count = {sp: 0 for sp in speakers}
    for event in event_result.events:
        if event.slide_id is not None and event.speaker in slide_count:
            slide_count[event.speaker] += 1

    norm_time  = _max_norm(raw_time)
    norm_slide = _max_norm({sp: float(slide_count[sp]) for sp in speakers})
    combined   = _max_norm({
        sp: (norm_time[sp] + norm_slide[sp]) / 2.0
        for sp in speakers
    })

    return {
        "baseline": "B6_audio_ppt_no_decision",
        "input_source": source,
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
        eval_result = evaluate_influence_ranking(scores, human_ranking)
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
        eval_result = evaluate_influence_ranking(proposed_scores, human_ranking)
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
