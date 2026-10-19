"""
Ablation study framework — Phase 12.

Supports systematic removal of one feature/component at a time from the
Phase 11 influence model.  Each ablation reuses the same input data so
comparisons are fair.

Required ablations
------------------
A1  Full proposed system (control)
A2  Without PPT (rerun events/evidence/decisions/interactions without slides)
A3  Without temporal alignment (rerun downstream from semantic-only alignment)
A4  Without semantic alignment (rerun downstream from temporal-only alignment)
A5  Without evidence features      (evidence = 0)
A6  Without interaction features   (interaction = 0)
A7  Without decision-impact features (decision + objection + revision = 0)
A8  Speaking-time-only baseline

Each experiment produces:
  {experiment, removed_component, ablation_flags, influence_scores, metrics}

Metric cells remain None until human evaluation data is supplied.
Do NOT insert fabricated metric values.
"""

from __future__ import annotations

from typing import Any

from src.meeting.decisions import DecisionResult
from src.meeting.events import EventExtractionResult
from src.meeting.evidence import EvidenceExtractionResult
from src.meeting.interaction import InteractionResult
from src.meeting.influence import compute_influence, FEATURE_KEYS
from src.evaluation.metrics import evaluate_influence_ranking


# ---------------------------------------------------------------------------
# Ablation configurations
# ---------------------------------------------------------------------------

# Each entry: (experiment_id, label, removed_component, ablation_flags)
# ablation_flags: {feature_key: False} to zero-out that feature weight.
# An empty dict means all features are active (full system).

ABLATION_CONFIGS: list[tuple[str, str, str, dict[str, bool]]] = [
    (
        "A1",
        "full_system",
        "none",
        {},  # all features active
    ),
    (
        "A2",
        "without_ppt",
        "ppt",
        {},
    ),
    (
        "A3",
        "without_temporal_alignment",
        "temporal_alignment",
        {},
    ),
    (
        "A4",
        "without_semantic_alignment",
        "semantic_alignment",
        {},
    ),
    (
        "A5",
        "without_evidence_features",
        "evidence",
        {"evidence": False},
    ),
    (
        "A6",
        "without_interaction_features",
        "interaction",
        {"interaction": False},
    ),
    (
        "A7",
        "without_decision_impact_features",
        "decision+objection+revision",
        {"decision": False, "objection": False, "revision": False},
    ),
    (
        "A8",
        "speaking_time_only_baseline",
        "all_except_none",
        {k: False for k in FEATURE_KEYS},  # zero all → will use speaking-time baseline
    ),
]


# ---------------------------------------------------------------------------
# Run one ablation
# ---------------------------------------------------------------------------

def reconstruct_variant(segments, meeting_id):
    """Reuse the production NLP stages on one independently aligned transcript."""
    from src.meeting.events import KeywordEventExtractor
    from src.meeting.evidence import extract_evidence
    from src.meeting.decisions import reconstruct_decisions
    from src.meeting.interaction import extract_interactions
    from src.utils.config import get
    events = KeywordEventExtractor().extract(segments, meeting_id)
    evidence = extract_evidence(events, window_s=float(get("meeting_analysis.evidence_window_s", 60)))
    decisions = reconstruct_decisions(events, evidence,
        temporal_window=float(get("decision_analysis.temporal_window", 120)),
        require_final_decision=bool(get("decision_analysis.require_final_decision", False)))
    interactions = extract_interactions(events, evidence, decisions,
        temporal_window=float(get("interaction.temporal_window", 60)))
    return events, evidence, decisions, interactions


def run_ablation(
    experiment_id: str,
    label: str,
    removed_component: str,
    ablation_flags: dict[str, bool],
    event_result: EventExtractionResult,
    evidence_result: EvidenceExtractionResult,
    decision_result: DecisionResult,
    interaction_result: InteractionResult,
    human_ranking: list[str] | None = None,
    transcript_segments: list[dict] | None = None,
    alignment_variants: dict[str, list[dict]] | None = None,
) -> dict[str, Any]:
    """
    Run a single ablation experiment.

    Parameters
    ----------
    experiment_id      : Short ID like "A1".
    label              : Descriptive label.
    removed_component  : Name of what was removed.
    ablation_flags     : {feature_key: False} to disable.
    event_result       : Phase 8 events.
    evidence_result    : Phase 8 evidence.
    decision_result    : Phase 9 decisions.
    interaction_result : Phase 10 interactions.
    human_ranking      : Human-annotated ranking (None if unavailable).

    Returns
    -------
    Ablation result dict.  Metric cells are None if human_ranking is None.
    """
    if experiment_id in {"A2", "A3", "A4"}:
        segments = transcript_segments if experiment_id == "A2" else (alignment_variants or {}).get(experiment_id)
        if segments is None:
            return {"experiment": experiment_id, "label": label, "removed_component": removed_component,
                    "ablation_flags": ablation_flags, "influence_scores": {}, "ranking": [],
                    "status": "input_unavailable", "reason": "An independently recomputed transcript/alignment is required",
                    "metrics": {"spearman": None, "kendall": None, "eval_status": "input_unavailable"}}
        if experiment_id == "A2":
            segments = [dict(row, slide_id=None, alignment={}) for row in segments]
        event_result, evidence_result, decision_result, interaction_result = reconstruct_variant(segments, event_result.meeting_id)
    # A8 uses speaking-time baseline scores instead of influence model
    if experiment_id == "A8":
        from src.evaluation.baselines import baseline_speaking_time
        b = baseline_speaking_time(event_result, transcript_segments)
        scores = b["scores"]
        ranking = sorted(scores.keys(), key=lambda sp: scores[sp], reverse=True)
        eval_result = evaluate_influence_ranking(scores, human_ranking)
        return {
            "experiment": experiment_id,
            "label": label,
            "removed_component": removed_component,
            "ablation_flags": ablation_flags,
            "influence_scores": scores,
            "ranking": ranking,
            "metrics": {
                "spearman": eval_result.get("spearman_correlation"),
                "kendall":  eval_result.get("kendall_tau"),
                "eval_status": eval_result.get("status"),
            },
        }

    result = compute_influence(
        event_result,
        evidence_result,
        decision_result,
        interaction_result,
        ablation_flags=ablation_flags if ablation_flags else None,
        transcript_segments=transcript_segments,
    )

    scores = {p.participant: p.influence_score for p in result.participants}
    ranking = [p.participant for p in result.by_rank()]

    eval_result = evaluate_influence_ranking(scores, human_ranking)

    return {
        "experiment": experiment_id,
        "label": label,
        "removed_component": removed_component,
        "ablation_flags": ablation_flags,
        "analysis_mode": "downstream_rerun" if experiment_id in {"A2", "A3", "A4"} else "feature_weight_ablation",
        "input_counts": {"events": len(event_result.events), "decisions": len(decision_result.decisions),
                         "slide_grounded_events": sum(event.slide_id is not None for event in event_result.events)},
        "influence_scores": scores,
        "ranking": ranking,
        "metrics": {
            "spearman": eval_result.get("spearman_correlation"),
            "kendall":  eval_result.get("kendall_tau"),
            "eval_status": eval_result.get("status"),
        },
    }


# ---------------------------------------------------------------------------
# Run all ablations
# ---------------------------------------------------------------------------

def run_all_ablations(
    event_result: EventExtractionResult,
    evidence_result: EvidenceExtractionResult,
    decision_result: DecisionResult,
    interaction_result: InteractionResult,
    human_ranking: list[str] | None = None,
    transcript_segments: list[dict] | None = None,
    alignment_variants: dict[str, list[dict]] | None = None,
) -> list[dict[str, Any]]:
    """
    Run all configured ablation experiments on the same dataset.

    Parameters
    ----------
    event_result, evidence_result, decision_result, interaction_result:
        Structured outputs from previous pipeline phases.
    human_ranking: Human-annotated ranking list (None → metric cells = None).

    Returns
    -------
    List of ablation result dicts, one per experiment.
    """
    control = (alignment_variants or {}).get("A1")
    if control is not None:
        event_result, evidence_result, decision_result, interaction_result = reconstruct_variant(control, event_result.meeting_id)
    results: list[dict[str, Any]] = []
    for exp_id, label, removed, flags in ABLATION_CONFIGS:
        r = run_ablation(
            exp_id, label, removed, flags,
            event_result, evidence_result, decision_result, interaction_result,
            human_ranking=human_ranking, transcript_segments=transcript_segments,
            alignment_variants=alignment_variants,
        )
        results.append(r)
    return results


# ---------------------------------------------------------------------------
# Serialisation helper
# ---------------------------------------------------------------------------

def ablation_results_to_dict(
    results: list[dict[str, Any]],
    meeting_id: str,
) -> dict[str, Any]:
    """Wrap ablation results in a serialisable container."""
    return {
        "meeting_id": meeting_id,
        "note": (
            "Metric values (spearman, kendall) are None until human evaluation "
            "annotations are provided. Do NOT insert fabricated values."
        ),
        "ablations": results,
    }
