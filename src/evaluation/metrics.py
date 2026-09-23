"""
Evaluation metrics — Phase 12.

Provides reusable metric functions for all pipeline stages.

Design principles
-----------------
- Every metric function returns a structured dict with a "status" field.
- If ground truth is unavailable the function returns
  {"status": "ground_truth_unavailable", "metric": "<name>"}
  rather than silently skipping or fabricating a value.
- No metric is ever computed against the system's own output as ground truth.
- No metric value is fabricated or hard-coded.

Metrics implemented
-------------------
  ASR / transcription   : WER  (Word Error Rate)
  Speaker diarization   : DER  (Diarization Error Rate)
  Audio–PPT alignment   : Precision / Recall / F1 / Accuracy
  Event extraction      : Precision / Recall / F1  (per type and overall)
  Decision extraction   : Precision / Recall / F1
  Decision lineage      : edge Precision / Recall / F1
  Influence ranking     : Spearman correlation, Kendall's tau
  Processing efficiency : RTF, stage timings, memory

All metric implementations use only the Python standard library plus
scipy (for rank correlation) when available.  scipy is optional;
if unavailable a manual implementation is used as fallback.

Research questions addressed
-----------------------------
  RQ1  ASR + DER
  RQ2  Alignment F1
  RQ3  Event + Decision F1
  RQ4  Lineage F1
  RQ5  Influence Spearman / Kendall vs baselines
  RQ6  Ablation comparison
"""

from __future__ import annotations

import math
import time
from typing import Any

# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------

STATUS_OK = "ok"
STATUS_NO_GT = "ground_truth_unavailable"
STATUS_ERROR = "error"


def _no_gt(metric: str) -> dict[str, Any]:
    """Return the canonical 'ground truth unavailable' response."""
    return {"status": STATUS_NO_GT, "metric": metric}


# ---------------------------------------------------------------------------
# 1. WER — Word Error Rate
# ---------------------------------------------------------------------------

def _levenshtein(a: list[str], b: list[str]) -> tuple[int, int, int]:
    """
    Compute word-level edit distance between token lists a and b.

    Returns (substitutions, deletions, insertions).
    Uses standard dynamic-programming Wagner-Fischer algorithm.
    """
    m, n = len(a), len(b)
    # dp[i][j] = edit distance between a[:i] and b[:j]
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j - 1],  # substitution
                                    dp[i - 1][j],       # deletion
                                    dp[i][j - 1])       # insertion

    # Backtrack to count substitutions, deletions, insertions
    i, j = m, n
    subs = dels = ins = 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and a[i - 1] == b[j - 1]:
            i -= 1; j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            subs += 1; i -= 1; j -= 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            dels += 1; i -= 1
        else:
            ins += 1; j -= 1

    return subs, dels, ins


def calculate_wer(
    reference: str | None,
    hypothesis: str | None,
) -> dict[str, Any]:
    """
    Compute Word Error Rate.

    Parameters
    ----------
    reference  : Ground-truth transcript text.  Pass None if unavailable.
    hypothesis : System-generated transcript text.

    Returns
    -------
    dict with keys: status, wer, substitutions, deletions, insertions,
                    reference_length, hypothesis_length
    Or ground_truth_unavailable dict if reference is None / empty.

    NOTE: WER can exceed 1.0 when insertions are numerous.
    WER = (S + D + I) / N  where N = number of reference words.
    """
    if reference is None or str(reference).strip() == "":
        return _no_gt("wer")
    if hypothesis is None:
        hypothesis = ""

    ref_tokens = str(reference).lower().split()
    hyp_tokens = str(hypothesis).lower().split()

    if len(ref_tokens) == 0:
        return _no_gt("wer")

    subs, dels, ins = _levenshtein(ref_tokens, hyp_tokens)
    total_errors = subs + dels + ins
    wer = total_errors / len(ref_tokens)

    return {
        "status": STATUS_OK,
        "metric": "wer",
        "wer": round(wer, 6),
        "substitutions": subs,
        "deletions": dels,
        "insertions": ins,
        "reference_length": len(ref_tokens),
        "hypothesis_length": len(hyp_tokens),
    }


# ---------------------------------------------------------------------------
# 2. DER — Diarization Error Rate
# ---------------------------------------------------------------------------

def calculate_der(
    reference: list[dict[str, Any]] | None,
    hypothesis: list[dict[str, Any]] | None,
    collar: float = 0.25,
) -> dict[str, Any]:
    """
    Compute Diarization Error Rate.

    Parameters
    ----------
    reference  : List of {start, end, speaker} dicts (ground truth).
                 Pass None if ground truth unavailable.
    hypothesis : List of {start, end, speaker} dicts (system output).
    collar     : Tolerance collar in seconds around segment boundaries
                 (standard value = 0.25 s).

    Returns
    -------
    dict with status + DER components, or ground_truth_unavailable.

    DER = (missed_speech + false_alarm + speaker_error) / total_reference_duration

    Implementation note
    -------------------
    This is a frame-level approximation using 10 ms frames.
    A full NIST md-eval compliant implementation requires the
    'pyannote.metrics' package.  This implementation is a transparent
    approximation documented as such.
    """
    if reference is None or len(reference) == 0:
        return _no_gt("der")
    if hypothesis is None:
        hypothesis = []

    FRAME_MS = 0.01   # 10 ms resolution

    def _to_frames(segments: list[dict], frame_s: float) -> dict[int, str]:
        """Map time → speaker at 10 ms resolution."""
        frames: dict[int, str] = {}
        for seg in segments:
            s = int(seg["start"] / frame_s)
            e = int(seg["end"] / frame_s)
            sp = str(seg.get("speaker", "UNKNOWN"))
            for f in range(s, e):
                frames[f] = sp
        return frames

    ref_frames = _to_frames(reference, FRAME_MS)
    hyp_frames = _to_frames(hypothesis, FRAME_MS)

    all_frames = set(ref_frames.keys()) | set(hyp_frames.keys())

    missed = 0       # in reference but not hypothesis
    false_alarm = 0  # in hypothesis but not reference
    speaker_error = 0  # both have speech but different speaker

    for f in all_frames:
        in_ref = f in ref_frames
        in_hyp = f in hyp_frames
        if in_ref and not in_hyp:
            missed += 1
        elif in_hyp and not in_ref:
            false_alarm += 1
        elif in_ref and in_hyp and ref_frames[f] != hyp_frames[f]:
            speaker_error += 1

    total_ref = len(ref_frames)
    if total_ref == 0:
        return _no_gt("der")

    der = (missed + false_alarm + speaker_error) / total_ref

    return {
        "status": STATUS_OK,
        "metric": "der",
        "der": round(der, 6),
        "missed_speech_rate": round(missed / total_ref, 6),
        "false_alarm_rate": round(false_alarm / total_ref, 6),
        "speaker_error_rate": round(speaker_error / total_ref, 6),
        "total_reference_frames": total_ref,
        "collar_s": collar,
        "note": (
            "Frame-level DER approximation at 10 ms resolution. "
            "For NIST md-eval compliant DER use pyannote.metrics."
        ),
    }


# ---------------------------------------------------------------------------
# 3. Precision / Recall / F1 helper
# ---------------------------------------------------------------------------

def _prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)
    return {
        "precision": round(precision, 6),
        "recall":    round(recall, 6),
        "f1":        round(f1, 6),
        "tp": tp, "fp": fp, "fn": fn,
    }


# ---------------------------------------------------------------------------
# 4. Audio–PPT alignment evaluation
# ---------------------------------------------------------------------------

def evaluate_alignment(
    predictions: list[dict[str, Any]] | None,
    ground_truth: list[dict[str, Any]] | None,
    timestamp_tolerance: float = 5.0,
) -> dict[str, Any]:
    """
    Evaluate transcript–slide alignment.

    Parameters
    ----------
    predictions   : List of {segment_id, slide_id} (system output).
    ground_truth  : List of {segment_id, slide_id} (annotated ground truth).
                    Pass None if unavailable.
    timestamp_tolerance : Unused placeholder for future time-aware matching.

    Returns
    -------
    dict with precision, recall, f1, accuracy, or ground_truth_unavailable.

    Matching criterion: segment_id + slide_id must match exactly.
    """
    if ground_truth is None or len(ground_truth) == 0:
        return _no_gt("alignment")
    if predictions is None:
        predictions = []

    gt_map = {str(item["segment_id"]): str(item.get("slide_id", "")) for item in ground_truth}
    pred_map = {str(item["segment_id"]): str(item.get("slide_id", "")) for item in predictions}

    tp = fp = fn = 0
    correct = 0

    for seg_id, gt_slide in gt_map.items():
        pred_slide = pred_map.get(seg_id)
        if pred_slide == gt_slide:
            tp += 1
            correct += 1
        elif pred_slide is None:
            fn += 1
        else:
            fp += 1
            fn += 1  # wrong slide = missed + false

    for seg_id in pred_map:
        if seg_id not in gt_map:
            fp += 1

    total = len(gt_map)
    accuracy = correct / total if total > 0 else 0.0

    metrics = _prf(tp, fp, fn)
    metrics.update({
        "status": STATUS_OK,
        "metric": "alignment",
        "accuracy": round(accuracy, 6),
        "total_ground_truth_segments": total,
        "timestamp_tolerance_s": timestamp_tolerance,
    })
    return metrics


# ---------------------------------------------------------------------------
# 5. Event extraction evaluation
# ---------------------------------------------------------------------------

def evaluate_events(
    predictions: list[dict[str, Any]] | None,
    ground_truth: list[dict[str, Any]] | None,
    timestamp_tolerance: float = 5.0,
) -> dict[str, Any]:
    """
    Evaluate meeting event extraction.

    Parameters
    ----------
    predictions   : List of {event_type, speaker, start, end, text} dicts.
    ground_truth  : List of {event_type, speaker, start, end, text} dicts.
                    Pass None if unavailable.
    timestamp_tolerance : Max seconds difference to consider a temporal match.

    Returns
    -------
    dict with per-type and overall precision/recall/F1.

    Matching criterion: event_type matches AND temporal overlap or
    start within timestamp_tolerance of ground-truth start.
    """
    if ground_truth is None or len(ground_truth) == 0:
        return _no_gt("event_extraction")
    if predictions is None:
        predictions = []

    # Group by event_type
    all_types = sorted(set(
        [g["event_type"] for g in ground_truth]
        + [p["event_type"] for p in predictions]
    ))

    def _match(pred: dict, gt: dict, tol: float) -> bool:
        if pred.get("event_type") != gt.get("event_type"):
            return False
        # Temporal proximity check
        p_start = float(pred.get("start", 0.0))
        g_start = float(gt.get("start", 0.0))
        return abs(p_start - g_start) <= tol

    per_type: dict[str, Any] = {}
    overall_tp = overall_fp = overall_fn = 0

    for etype in all_types:
        preds_t = [p for p in predictions if p.get("event_type") == etype]
        gts_t   = [g for g in ground_truth if g.get("event_type") == etype]

        matched_gt = set()
        tp = 0
        for pred in preds_t:
            for gi, gt in enumerate(gts_t):
                if gi not in matched_gt and _match(pred, gt, timestamp_tolerance):
                    tp += 1
                    matched_gt.add(gi)
                    break

        fp = len(preds_t) - tp
        fn = len(gts_t) - tp
        per_type[etype] = _prf(tp, fp, fn)
        overall_tp += tp
        overall_fp += fp
        overall_fn += fn

    overall = _prf(overall_tp, overall_fp, overall_fn)
    overall.update({
        "status": STATUS_OK,
        "metric": "event_extraction",
        "per_type": per_type,
        "timestamp_tolerance_s": timestamp_tolerance,
    })
    return overall


# ---------------------------------------------------------------------------
# 6. Decision extraction evaluation
# ---------------------------------------------------------------------------

def evaluate_decisions(
    predictions: list[dict[str, Any]] | None,
    ground_truth: list[dict[str, Any]] | None,
    timestamp_tolerance: float = 30.0,
) -> dict[str, Any]:
    """
    Evaluate decision extraction.

    Parameters
    ----------
    predictions   : List of {decision_id, topic, status, timestamp} dicts.
    ground_truth  : List of {decision_id, topic, status, timestamp} dicts.
                    Pass None if unavailable.
    timestamp_tolerance : Seconds tolerance for temporal matching.

    Returns
    -------
    dict with precision, recall, f1, or ground_truth_unavailable.

    Matching: topic similarity OR timestamp proximity within tolerance.
    Topic similarity uses word-overlap (Jaccard on token sets).
    """
    if ground_truth is None or len(ground_truth) == 0:
        return _no_gt("decision_extraction")
    if predictions is None:
        predictions = []

    def _jaccard(a: str, b: str) -> float:
        ta = set(str(a).lower().split())
        tb = set(str(b).lower().split())
        if not ta and not tb:
            return 1.0
        return len(ta & tb) / len(ta | tb)

    def _matches(pred: dict, gt: dict, tol: float) -> bool:
        # Temporal proximity
        pt = float(pred.get("timestamp", pred.get("start", 0.0)))
        gt_t = float(gt.get("timestamp", gt.get("start", 0.0)))
        time_match = abs(pt - gt_t) <= tol
        # Topic overlap
        topic_match = _jaccard(
            pred.get("topic", pred.get("text", "")),
            gt.get("topic", gt.get("text", "")),
        ) >= 0.3
        return time_match or topic_match

    matched_gt: set[int] = set()
    tp = 0
    for pred in predictions:
        for gi, gt in enumerate(ground_truth):
            if gi not in matched_gt and _matches(pred, gt, timestamp_tolerance):
                tp += 1
                matched_gt.add(gi)
                break

    fp = len(predictions) - tp
    fn = len(ground_truth) - tp
    metrics = _prf(tp, fp, fn)
    metrics.update({
        "status": STATUS_OK,
        "metric": "decision_extraction",
        "timestamp_tolerance_s": timestamp_tolerance,
    })
    return metrics


# ---------------------------------------------------------------------------
# 7. Decision lineage evaluation
# ---------------------------------------------------------------------------

def evaluate_decision_lineage(
    predicted_graph: dict[str, Any] | None,
    ground_truth_graph: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Evaluate decision lineage graph reconstruction.

    Parameters
    ----------
    predicted_graph   : {nodes: [...], edges: [{source, target, relationship}]}
    ground_truth_graph: Same format.  Pass None if unavailable.

    Returns
    -------
    dict with node and edge precision/recall/F1, or ground_truth_unavailable.

    Edge matching: (source_label, relationship, target_label) tuple.
    """
    if ground_truth_graph is None:
        return _no_gt("decision_lineage")
    if predicted_graph is None:
        predicted_graph = {"nodes": [], "edges": []}

    def _edge_key(e: dict) -> tuple[str, str, str]:
        return (
            str(e.get("source", "")),
            str(e.get("relationship", "")),
            str(e.get("target", "")),
        )

    pred_edges = {_edge_key(e) for e in predicted_graph.get("edges", [])}
    gt_edges   = {_edge_key(e) for e in ground_truth_graph.get("edges", [])}

    pred_nodes = set(predicted_graph.get("nodes", []))
    gt_nodes   = set(ground_truth_graph.get("nodes", []))

    # Edge metrics
    tp_e = len(pred_edges & gt_edges)
    fp_e = len(pred_edges - gt_edges)
    fn_e = len(gt_edges - pred_edges)
    edge_metrics = _prf(tp_e, fp_e, fn_e)

    # Node metrics
    tp_n = len(pred_nodes & gt_nodes)
    fp_n = len(pred_nodes - gt_nodes)
    fn_n = len(gt_nodes - pred_nodes)
    node_metrics = _prf(tp_n, fp_n, fn_n)

    return {
        "status": STATUS_OK,
        "metric": "decision_lineage",
        "edge_metrics": edge_metrics,
        "node_metrics": node_metrics,
        "predicted_edges": len(pred_edges),
        "ground_truth_edges": len(gt_edges),
    }


# ---------------------------------------------------------------------------
# 8. Influence ranking evaluation
# ---------------------------------------------------------------------------

def _spearman(x: list[float], y: list[float]) -> float:
    """Spearman rank correlation (fallback pure-Python implementation)."""
    n = len(x)
    if n < 2:
        return float("nan")

    def _rank(lst: list[float]) -> list[float]:
        sorted_lst = sorted(enumerate(lst), key=lambda t: t[1])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and sorted_lst[j + 1][1] == sorted_lst[i][1]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                ranks[sorted_lst[k][0]] = avg_rank
            i = j + 1
        return ranks

    rx = _rank(x)
    ry = _rank(y)
    d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return 1.0 - (6.0 * d2) / (n * (n * n - 1))


def _kendall_tau(x: list[float], y: list[float]) -> float:
    """Kendall's tau-b (pure-Python fallback)."""
    n = len(x)
    if n < 2:
        return float("nan")
    concordant = discordant = ties_x = ties_y = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = x[i] - x[j]
            dy = y[i] - y[j]
            prod = dx * dy
            if prod > 0:
                concordant += 1
            elif prod < 0:
                discordant += 1
            else:
                if dx == 0:
                    ties_x += 1
                if dy == 0:
                    ties_y += 1
    denom = math.sqrt(
        (concordant + discordant + ties_x) * (concordant + discordant + ties_y)
    )
    return (concordant - discordant) / denom if denom > 0 else float("nan")


def evaluate_influence_ranking(
    system_ranking: list[str] | None,
    human_ranking: list[str] | None,
) -> dict[str, Any]:
    """
    Compare system influence ranking to human-annotated ranking.

    Parameters
    ----------
    system_ranking : Ordered list of speaker IDs, highest influence first.
    human_ranking  : Human-annotated ranking, same format.
                     Pass None if human annotations are unavailable.

    Returns
    -------
    dict with spearman, kendall, or ground_truth_unavailable.

    NOTE: Do NOT call this function with fabricated human rankings.
    Results are only meaningful when human_ranking comes from
    actual human evaluation.
    """
    if human_ranking is None or len(human_ranking) == 0:
        return _no_gt("influence_ranking")
    if system_ranking is None or len(system_ranking) == 0:
        return {
            "status": STATUS_ERROR,
            "metric": "influence_ranking",
            "error": "system_ranking is empty",
        }

    # Build rank-score vectors (higher rank = lower position index)
    all_speakers = list(dict.fromkeys(human_ranking + system_ranking))

    def _rank_scores(ranking: list[str], speakers: list[str]) -> list[float]:
        pos = {sp: i for i, sp in enumerate(ranking)}
        return [float(pos.get(sp, len(ranking))) for sp in speakers]

    sys_scores = _rank_scores(system_ranking, all_speakers)
    hum_scores = _rank_scores(human_ranking, all_speakers)

    # Prefer scipy if available
    try:
        from scipy.stats import spearmanr, kendalltau  # type: ignore
        sp_corr, sp_pval = spearmanr(sys_scores, hum_scores)
        kt_corr, kt_pval = kendalltau(sys_scores, hum_scores)
        sp_pval = float(sp_pval) if sp_pval is not None else None
        kt_pval = float(kt_pval) if kt_pval is not None else None
    except ImportError:
        sp_corr = _spearman(sys_scores, hum_scores)
        kt_corr = _kendall_tau(sys_scores, hum_scores)
        sp_pval = kt_pval = None

    return {
        "status": STATUS_OK,
        "metric": "influence_ranking",
        "spearman_correlation": round(float(sp_corr), 6) if not math.isnan(float(sp_corr)) else None,
        "spearman_p_value": round(sp_pval, 6) if sp_pval is not None else None,
        "kendall_tau": round(float(kt_corr), 6) if not math.isnan(float(kt_corr)) else None,
        "kendall_p_value": round(kt_pval, 6) if kt_pval is not None else None,
        "n_participants": len(all_speakers),
        "note": (
            "Scores are only meaningful when human_ranking comes from "
            "actual human evaluation, not fabricated annotations."
        ),
    }


# ---------------------------------------------------------------------------
# 9. Processing efficiency
# ---------------------------------------------------------------------------

def calculate_efficiency(
    stage_timings: dict[str, float],
    audio_duration_s: float | None = None,
) -> dict[str, Any]:
    """
    Compute processing efficiency metrics.

    Parameters
    ----------
    stage_timings    : {stage_name: seconds} for each pipeline stage.
    audio_duration_s : Duration of the input audio in seconds.
                       If None, RTF is not computed.

    Returns
    -------
    dict with total_time, stage_timings, rtf (if audio_duration provided).
    """
    if not stage_timings:
        return {
            "status": STATUS_ERROR,
            "metric": "efficiency",
            "error": "No stage timings provided.",
        }

    total_time = sum(stage_timings.values())
    result: dict[str, Any] = {
        "status": STATUS_OK,
        "metric": "efficiency",
        "total_processing_time_s": round(total_time, 4),
        "stage_timings_s": {k: round(v, 4) for k, v in stage_timings.items()},
    }

    if audio_duration_s is not None and audio_duration_s > 0:
        rtf = total_time / audio_duration_s
        result["audio_duration_s"] = audio_duration_s
        result["rtf"] = round(rtf, 6)
        result["rtf_note"] = (
            f"RTF = processing_time / audio_duration = "
            f"{total_time:.2f}s / {audio_duration_s:.2f}s = {rtf:.4f}. "
            f"RTF < 1.0 means faster-than-real-time processing."
        )
    else:
        result["rtf"] = None
        result["rtf_note"] = "Audio duration not provided; RTF not computed."

    return result


# ---------------------------------------------------------------------------
# 10. Reproducibility metadata
# ---------------------------------------------------------------------------

def build_eval_metadata(
    meeting_id: str,
    dataset: str | None = None,
    config: dict[str, Any] | None = None,
    model_names: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Build reproducibility metadata for an evaluation run.

    Parameters
    ----------
    meeting_id   : Unique meeting identifier.
    dataset      : Dataset name / version if known.
    config       : Relevant configuration snapshot (no secrets).
    model_names  : {stage: model_name} mapping.

    Returns
    -------
    dict with reproducibility fields.
    """
    import datetime
    return {
        "meeting_id": meeting_id,
        "dataset": dataset or "unknown",
        "evaluation_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "config_snapshot": config or {},
        "model_names": model_names or {},
        "metric_definitions": {
            "wer":       "Word Error Rate = (S+D+I)/N",
            "der":       "Diarization Error Rate = (missed+false_alarm+speaker_error)/ref_duration",
            "alignment": "Precision/Recall/F1 on (segment_id, slide_id) pairs",
            "events":    "Precision/Recall/F1 with timestamp tolerance matching",
            "decisions": "Precision/Recall/F1 with topic-Jaccard or temporal matching",
            "lineage":   "Edge Precision/Recall/F1 on (source, relationship, target) tuples",
            "influence": "Spearman / Kendall vs human-annotated ranking",
            "efficiency": "Total time, stage timings, RTF = processing_time / audio_duration",
        },
    }
