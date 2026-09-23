"""
Evaluation script — Phase 12.

Runs the evaluation framework against existing pipeline outputs.
Does NOT rerun the full ML pipeline.

Usage examples
--------------
# Evaluate all available metrics for a meeting:
python scripts/run_evaluation.py --meeting-id <id>

# Evaluate with a human annotation file:
python scripts/run_evaluation.py --meeting-id <id> --annotations data/annotations/<id>_annotations.json

# Run ablation study:
python scripts/run_evaluation.py --meeting-id <id> --ablation

# Evaluate efficiency with audio duration:
python scripts/run_evaluation.py --meeting-id <id> --audio-duration 3600

Input paths (auto-resolved from meeting ID unless overridden):
  data/processed/events/<id>_events.json
  data/processed/events/<id>_evidence.json
  data/processed/decisions/<id>_decisions.json
  data/processed/interactions/<id>_interactions.json
  data/processed/influence/<id>_influence.json

Output:
  outputs/evaluation/<id>_metrics.json
  outputs/evaluation/<id>_baselines.json
  outputs/evaluation/<id>_ablation.json     (with --ablation)
  outputs/evaluation/comparison.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logging import get_logger

logger = get_logger("evaluation")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase 12 evaluation framework")
    p.add_argument("--meeting-id", required=True, help="Meeting identifier")
    p.add_argument(
        "--annotations",
        default=None,
        help="Path to annotation JSON (ground truth for all metrics)",
    )
    p.add_argument(
        "--ablation",
        action="store_true",
        help="Run ablation study",
    )
    p.add_argument(
        "--audio-duration",
        type=float,
        default=None,
        help="Audio duration in seconds (for RTF calculation)",
    )
    p.add_argument(
        "--stage-timings",
        default=None,
        help="JSON string of {stage: seconds} for efficiency evaluation",
    )
    p.add_argument(
        "--output-dir",
        default="outputs/evaluation",
        help="Output directory (default: outputs/evaluation)",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _resolve_paths(meeting_id: str) -> dict[str, Path]:
    return {
        "events":       Path(f"data/processed/events/{meeting_id}_events.json"),
        "evidence":     Path(f"data/processed/events/{meeting_id}_evidence.json"),
        "decisions":    Path(f"data/processed/decisions/{meeting_id}_decisions.json"),
        "interactions": Path(f"data/processed/interactions/{meeting_id}_interactions.json"),
        "influence":    Path(f"data/processed/influence/{meeting_id}_influence.json"),
    }


# ---------------------------------------------------------------------------
# Load annotation file (if provided)
# ---------------------------------------------------------------------------

def _load_annotations(path: str | None) -> dict:
    if path is None:
        return {}
    ann_path = Path(path)
    if not ann_path.exists():
        logger.warning("Annotation file not found: %s — evaluation without ground truth", ann_path)
        return {}
    with open(ann_path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Main evaluation runner
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    meeting_id = args.meeting_id
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = _resolve_paths(meeting_id)
    annotations = _load_annotations(args.annotations)

    # ---- Load available pipeline outputs ----
    from src.meeting.events import load_events_json
    from src.meeting.evidence import load_evidence_json
    from src.meeting.decisions import load_decisions_json
    from src.meeting.interaction import load_interactions_json
    from src.meeting.influence import load_influence_json
    from src.evaluation.metrics import (
        calculate_wer, calculate_der, evaluate_alignment,
        evaluate_events, evaluate_decisions, evaluate_decision_lineage,
        evaluate_influence_ranking, calculate_efficiency, build_eval_metadata,
    )
    from src.evaluation.baselines import (
        baseline_speaking_time, baseline_speaking_time_turns,
        baseline_decision_event_count, baseline_decision_evidence_count,
        baseline_transcript_only, baseline_audio_ppt_no_decision,
        build_comparison_table,
    )

    def _try_load(loader, path: Path):
        if path.exists():
            try:
                return loader(path)
            except Exception as exc:
                logger.warning("Could not load %s: %s", path, exc)
        return None

    event_result    = _try_load(load_events_json, paths["events"])
    evidence_result = _try_load(load_evidence_json, paths["evidence"])
    decision_result = _try_load(load_decisions_json, paths["decisions"])
    interaction_result = _try_load(load_interactions_json, paths["interactions"])
    influence_result   = _try_load(load_influence_json, paths["influence"])

    # ---- Ground-truth fields from annotation file ----
    gt_transcript   = annotations.get("transcript_ground_truth")
    gt_diarization  = annotations.get("speaker_ground_truth")
    gt_alignment    = annotations.get("alignment_ground_truth")
    gt_events       = annotations.get("event_ground_truth")
    gt_decisions    = annotations.get("decision_ground_truth")
    gt_lineage      = annotations.get("lineage_ground_truth")
    human_ranking   = annotations.get("influence_ranking")

    # ---- Compute metrics ----
    metrics_out: dict = {
        "meeting_id": meeting_id,
        "metadata": build_eval_metadata(
            meeting_id,
            dataset=annotations.get("dataset"),
            config={"source": "config.yaml"},
        ),
    }

    # ASR
    hyp_transcript = None
    if event_result:
        hyp_transcript = " ".join(e.text for e in event_result.events)
    metrics_out["wer"] = calculate_wer(gt_transcript, hyp_transcript)

    # DER
    hyp_diarization = None
    metrics_out["der"] = calculate_der(gt_diarization, hyp_diarization)

    # Alignment
    pred_alignment = None
    if event_result:
        pred_alignment = [
            {"segment_id": e.source_segment_id, "slide_id": e.slide_id}
            for e in event_result.events
        ]
    from src.utils.config import get as cfg_get
    tol = float(cfg_get("evaluation.alignment.timestamp_tolerance", 5.0))
    metrics_out["alignment"] = evaluate_alignment(pred_alignment, gt_alignment, tol)

    # Events
    pred_events = None
    if event_result:
        pred_events = [
            {"event_type": e.event_type, "speaker": e.speaker,
             "start": e.start, "end": e.end, "text": e.text}
            for e in event_result.events
        ]
    metrics_out["events"] = evaluate_events(pred_events, gt_events, tol)

    # Decisions
    pred_decisions = None
    if decision_result:
        pred_decisions = [
            {"decision_id": d.decision_id, "topic": d.topic or "",
             "status": d.status, "timestamp": d.proposal["start"]
             if d.proposal and event_result else 0.0}
            for d in decision_result.decisions
        ]
    metrics_out["decisions"] = evaluate_decisions(pred_decisions, gt_decisions)

    # Lineage
    pred_lineage = None
    if decision_result:
        all_edges = []
        all_nodes = set()
        for d in decision_result.decisions:
            for edge in d.lineage:
                all_edges.append({
                    "source": edge.source,
                    "relationship": edge.relationship,
                    "target": edge.target,
                })
                all_nodes.add(edge.source)
                all_nodes.add(edge.target)
        pred_lineage = {"nodes": list(all_nodes), "edges": all_edges}
    metrics_out["lineage"] = evaluate_decision_lineage(pred_lineage, gt_lineage)

    # Influence ranking
    sys_ranking = None
    if influence_result:
        ranked = influence_result.by_rank()
        sys_ranking = [p.participant for p in ranked]
    metrics_out["influence"] = evaluate_influence_ranking(sys_ranking, human_ranking)

    # Efficiency
    stage_timings: dict[str, float] = {}
    if args.stage_timings:
        try:
            stage_timings = json.loads(args.stage_timings)
        except json.JSONDecodeError:
            logger.warning("Could not parse --stage-timings JSON")
    metrics_out["efficiency"] = calculate_efficiency(stage_timings, args.audio_duration)

    # ---- Save metrics ----
    metrics_path = out_dir / f"{meeting_id}_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_out, f, indent=2, ensure_ascii=False)
    logger.info("Metrics saved: %s", metrics_path)

    # ---- Baselines ----
    baselines_out: list[dict] = []
    if event_result:
        baselines_out.append(baseline_speaking_time(event_result))
        baselines_out.append(baseline_speaking_time_turns(event_result))
        if decision_result:
            baselines_out.append(baseline_decision_event_count(event_result, decision_result))
            baselines_out.append(baseline_transcript_only(event_result, decision_result))
        if evidence_result and decision_result:
            baselines_out.append(baseline_decision_evidence_count(
                event_result, evidence_result, decision_result))
        if evidence_result:
            baselines_out.append(baseline_audio_ppt_no_decision(event_result, evidence_result))

    proposed_scores = None
    if influence_result:
        proposed_scores = {p.participant: p.influence_score for p in influence_result.participants}

    comparison = build_comparison_table(baselines_out, proposed_scores, human_ranking)

    baselines_payload = {
        "meeting_id": meeting_id,
        "baselines": baselines_out,
        "comparison": comparison,
    }
    baselines_path = out_dir / f"{meeting_id}_baselines.json"
    with open(baselines_path, "w", encoding="utf-8") as f:
        json.dump(baselines_payload, f, indent=2, ensure_ascii=False)
    logger.info("Baselines saved: %s", baselines_path)

    # ---- CSV comparison table ----
    csv_path = out_dir / "comparison.csv"
    rows = comparison.get("comparison_table", [])
    if rows:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["method", "description", "spearman", "kendall", "status"]
            )
            writer.writeheader()
            writer.writerows(rows)
        logger.info("Comparison CSV saved: %s", csv_path)

    # ---- Ablation ----
    if args.ablation:
        if all(x is not None for x in [
            event_result, evidence_result, decision_result, interaction_result
        ]):
            from src.evaluation.ablation import run_all_ablations, ablation_results_to_dict
            ablation_results = run_all_ablations(
                event_result, evidence_result, decision_result, interaction_result,
                human_ranking=human_ranking,
            )
            ablation_payload = ablation_results_to_dict(ablation_results, meeting_id)
            abl_path = out_dir / f"{meeting_id}_ablation.json"
            with open(abl_path, "w", encoding="utf-8") as f:
                json.dump(ablation_payload, f, indent=2, ensure_ascii=False)
            logger.info("Ablation results saved: %s", abl_path)
        else:
            logger.warning("Ablation skipped — some required pipeline outputs missing.")

    # ---- Summary ----
    print(f"\n[Evaluation Summary — {meeting_id}]")
    for key in ("wer", "der", "alignment", "events", "decisions", "lineage", "influence"):
        m = metrics_out.get(key, {})
        status = m.get("status", "unknown")
        if status == "ok":
            display_val = {
                "wer":       f"WER={m.get('wer')}",
                "der":       f"DER={m.get('der')}",
                "alignment": f"F1={m.get('f1')}",
                "events":    f"F1={m.get('f1')}",
                "decisions": f"F1={m.get('f1')}",
                "lineage":   f"EdgeF1={m.get('edge_metrics', {}).get('f1')}",
                "influence": f"Spearman={m.get('spearman_correlation')}",
            }.get(key, "")
            print(f"  {key:<12}: {display_val}")
        else:
            print(f"  {key:<12}: {status}")
    print(f"\n  Metrics JSON   : {metrics_path}")
    print(f"  Baselines JSON : {baselines_path}")
    print("\nNOTE: ground_truth_unavailable means no annotation was supplied.")
    print("Do NOT interpret unit-test results as real dataset performance.")
    print("\nDone.")


if __name__ == "__main__":
    main()
