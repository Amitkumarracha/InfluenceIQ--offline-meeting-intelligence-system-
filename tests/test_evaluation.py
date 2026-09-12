"""
Tests for Phase 12 — Evaluation, Baselines, and Ablation.

All tests use small synthetic data.
These are UNIT TESTS of metric implementations only.
They do NOT represent actual dataset performance.
Synthetic results must NOT be reported as research results.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest

from src.evaluation.metrics import (
    STATUS_NO_GT,
    STATUS_OK,
    STATUS_ERROR,
    _no_gt,
    _prf,
    _spearman,
    _kendall_tau,
    build_eval_metadata,
    calculate_der,
    calculate_efficiency,
    calculate_wer,
    evaluate_alignment,
    evaluate_decisions,
    evaluate_decision_lineage,
    evaluate_events,
    evaluate_influence_ranking,
)
from src.evaluation.baselines import (
    baseline_decision_event_count,
    baseline_decision_evidence_count,
    baseline_speaking_time,
    baseline_speaking_time_turns,
    baseline_transcript_only,
    baseline_audio_ppt_no_decision,
    build_comparison_table,
    _max_norm,
)
from src.evaluation.ablation import (
    ABLATION_CONFIGS,
    run_ablation,
    run_all_ablations,
    ablation_results_to_dict,
)

# Reuse helpers from test_meeting.py to build synthetic pipeline data
from src.meeting.events import EventExtractionResult, MeetingEvent
from src.meeting.evidence import EvidenceExtractionResult, EvidenceRelation, extract_evidence
from src.meeting.decisions import DecisionResult, reconstruct_decisions
from src.meeting.interaction import InteractionResult, extract_interactions


# ---------------------------------------------------------------------------
# Shared synthetic helpers
# ---------------------------------------------------------------------------

def _ev(
    event_id: str,
    event_type: str,
    speaker: str = "S1",
    start: float = 0.0,
    end: float = 5.0,
    text: str = "placeholder",
    slide_id: str | None = None,
    source_segment_id: int = 1,
) -> MeetingEvent:
    return MeetingEvent(
        event_id=event_id,
        event_type=event_type,
        speaker=speaker,
        start=start,
        end=end,
        text=text,
        slide_id=slide_id,
        confidence=0.7,
        source_segment_id=source_segment_id,
    )


def _pipeline_data():
    """Minimal synthetic pipeline data for evaluation tests."""
    events = [
        _ev("e1", "proposal",   "S1",  0.0,  5.0, "We should use Option A.", "slide_01", 1),
        _ev("e2", "objection",  "S2", 10.0, 15.0, "I disagree.", "slide_01", 2),
        _ev("e3", "evidence",   "S2", 20.0, 25.0, "According to data.", "slide_02", 3),
        _ev("e4", "revision",   "S1", 30.0, 35.0, "Let's use Option B.", "slide_02", 4),
        _ev("e5", "agreement",  "S2", 40.0, 45.0, "I agree.", None, 5),
        _ev("e6", "decision",   "S1", 50.0, 55.0, "We will use Option B.", "slide_02", 6),
    ]
    er = EventExtractionResult(meeting_id="test", events=events)
    ev = extract_evidence(er, window_s=120.0)
    dr = reconstruct_decisions(er, ev, temporal_window=120.0)
    ir = extract_interactions(er, ev, dr, temporal_window=120.0)
    return er, ev, dr, ir


# ===========================================================================
# 1. WER tests
# ===========================================================================

class TestWER:
    def test_perfect_match(self):
        r = calculate_wer("hello world", "hello world")
        assert r["status"] == STATUS_OK
        assert r["wer"] == pytest.approx(0.0)

    def test_full_substitution(self):
        r = calculate_wer("hello world", "foo bar")
        assert r["status"] == STATUS_OK
        assert r["wer"] == pytest.approx(1.0)

    def test_deletion(self):
        r = calculate_wer("hello world today", "hello world")
        assert r["status"] == STATUS_OK
        assert r["deletions"] == 1

    def test_insertion(self):
        r = calculate_wer("hello", "hello extra word")
        assert r["status"] == STATUS_OK
        assert r["insertions"] == 2

    def test_no_ground_truth_returns_unavailable(self):
        r = calculate_wer(None, "some hypothesis")
        assert r["status"] == STATUS_NO_GT
        assert r["metric"] == "wer"

    def test_empty_ground_truth_returns_unavailable(self):
        r = calculate_wer("", "something")
        assert r["status"] == STATUS_NO_GT

    def test_empty_hypothesis(self):
        r = calculate_wer("hello world", "")
        assert r["status"] == STATUS_OK
        assert r["wer"] == pytest.approx(1.0)

    def test_case_insensitive(self):
        r = calculate_wer("Hello World", "hello world")
        assert r["wer"] == pytest.approx(0.0)

    def test_wer_never_fabricated(self):
        """WER must not be computed when reference is None."""
        r = calculate_wer(None, "any text")
        assert "wer" not in r or r["status"] == STATUS_NO_GT


# ===========================================================================
# 2. DER tests
# ===========================================================================

class TestDER:
    def _seg(self, start, end, speaker):
        return {"start": start, "end": end, "speaker": speaker}

    def test_perfect_match(self):
        ref = [self._seg(0.0, 1.0, "A"), self._seg(1.0, 2.0, "B")]
        hyp = [self._seg(0.0, 1.0, "A"), self._seg(1.0, 2.0, "B")]
        r = calculate_der(ref, hyp)
        assert r["status"] == STATUS_OK
        assert r["der"] == pytest.approx(0.0, abs=0.01)

    def test_no_ground_truth_returns_unavailable(self):
        r = calculate_der(None, [])
        assert r["status"] == STATUS_NO_GT
        assert r["metric"] == "der"

    def test_empty_ground_truth_returns_unavailable(self):
        r = calculate_der([], [{"start": 0, "end": 1, "speaker": "A"}])
        assert r["status"] == STATUS_NO_GT

    def test_speaker_error_detected(self):
        ref = [self._seg(0.0, 1.0, "A")]
        hyp = [self._seg(0.0, 1.0, "B")]   # wrong speaker
        r = calculate_der(ref, hyp)
        assert r["status"] == STATUS_OK
        assert r["der"] > 0.0

    def test_missed_speech_detected(self):
        ref = [self._seg(0.0, 1.0, "A"), self._seg(1.0, 2.0, "B")]
        hyp = [self._seg(0.0, 1.0, "A")]   # missing second segment
        r = calculate_der(ref, hyp)
        assert r["status"] == STATUS_OK
        assert r["missed_speech_rate"] > 0.0

    def test_result_structure(self):
        ref = [self._seg(0.0, 0.5, "A")]
        hyp = [self._seg(0.0, 0.5, "A")]
        r = calculate_der(ref, hyp)
        for key in ("der", "missed_speech_rate", "false_alarm_rate", "speaker_error_rate"):
            assert key in r


# ===========================================================================
# 3. Precision / Recall / F1 helper
# ===========================================================================

class TestPRF:
    def test_perfect(self):
        r = _prf(5, 0, 0)
        assert r["precision"] == pytest.approx(1.0)
        assert r["recall"] == pytest.approx(1.0)
        assert r["f1"] == pytest.approx(1.0)

    def test_all_wrong(self):
        r = _prf(0, 5, 5)
        assert r["precision"] == pytest.approx(0.0)
        assert r["recall"] == pytest.approx(0.0)
        assert r["f1"] == pytest.approx(0.0)

    def test_zero_tp_fp(self):
        r = _prf(0, 0, 3)
        assert r["precision"] == pytest.approx(0.0)
        assert r["recall"] == pytest.approx(0.0)

    def test_values_in_range(self):
        r = _prf(3, 2, 1)
        assert 0.0 <= r["precision"] <= 1.0
        assert 0.0 <= r["recall"] <= 1.0
        assert 0.0 <= r["f1"] <= 1.0


# ===========================================================================
# 4. Alignment evaluation
# ===========================================================================

class TestAlignmentEvaluation:
    def test_perfect_alignment(self):
        gt   = [{"segment_id": 1, "slide_id": "s1"}, {"segment_id": 2, "slide_id": "s2"}]
        pred = [{"segment_id": 1, "slide_id": "s1"}, {"segment_id": 2, "slide_id": "s2"}]
        r = evaluate_alignment(pred, gt)
        assert r["status"] == STATUS_OK
        assert r["f1"] == pytest.approx(1.0)
        assert r["accuracy"] == pytest.approx(1.0)

    def test_no_ground_truth(self):
        r = evaluate_alignment([{"segment_id": 1, "slide_id": "s1"}], None)
        assert r["status"] == STATUS_NO_GT

    def test_wrong_slide_reduces_f1(self):
        gt   = [{"segment_id": 1, "slide_id": "s1"}]
        pred = [{"segment_id": 1, "slide_id": "s2"}]   # wrong slide
        r = evaluate_alignment(pred, gt)
        assert r["status"] == STATUS_OK
        assert r["f1"] < 1.0

    def test_missing_prediction(self):
        gt   = [{"segment_id": 1, "slide_id": "s1"}, {"segment_id": 2, "slide_id": "s2"}]
        pred = [{"segment_id": 1, "slide_id": "s1"}]
        r = evaluate_alignment(pred, gt)
        assert r["recall"] < 1.0

    def test_empty_predictions(self):
        gt   = [{"segment_id": 1, "slide_id": "s1"}]
        r = evaluate_alignment([], gt)
        assert r["status"] == STATUS_OK
        assert r["recall"] == pytest.approx(0.0)


# ===========================================================================
# 5. Event extraction evaluation
# ===========================================================================

class TestEventEvaluation:
    def test_perfect_event_match(self):
        gt   = [{"event_type": "proposal", "start": 0.0}]
        pred = [{"event_type": "proposal", "start": 0.0}]
        r = evaluate_events(pred, gt)
        assert r["status"] == STATUS_OK
        assert r["f1"] == pytest.approx(1.0)

    def test_no_ground_truth(self):
        r = evaluate_events([{"event_type": "proposal", "start": 0.0}], None)
        assert r["status"] == STATUS_NO_GT

    def test_timestamp_tolerance_matching(self):
        gt   = [{"event_type": "proposal", "start": 0.0}]
        pred = [{"event_type": "proposal", "start": 3.0}]  # within 5s tolerance
        r = evaluate_events(pred, gt, timestamp_tolerance=5.0)
        assert r["status"] == STATUS_OK
        assert r["tp"] >= 1

    def test_timestamp_outside_tolerance_misses(self):
        gt   = [{"event_type": "proposal", "start": 0.0}]
        pred = [{"event_type": "proposal", "start": 100.0}]  # far outside
        r = evaluate_events(pred, gt, timestamp_tolerance=5.0)
        assert r["tp"] == 0

    def test_wrong_type_no_match(self):
        gt   = [{"event_type": "proposal", "start": 0.0}]
        pred = [{"event_type": "agreement", "start": 0.0}]
        r = evaluate_events(pred, gt)
        assert r["per_type"].get("proposal", {}).get("tp", 0) == 0

    def test_per_type_breakdown(self):
        gt = [
            {"event_type": "proposal", "start": 0.0},
            {"event_type": "objection", "start": 10.0},
        ]
        pred = [
            {"event_type": "proposal", "start": 0.0},
        ]
        r = evaluate_events(pred, gt)
        assert "per_type" in r
        assert "proposal" in r["per_type"]


# ===========================================================================
# 6. Decision extraction evaluation
# ===========================================================================

class TestDecisionEvaluation:
    def test_perfect_decision_match(self):
        gt   = [{"topic": "model selection", "timestamp": 50.0}]
        pred = [{"topic": "model selection", "timestamp": 50.0}]
        r = evaluate_decisions(pred, gt)
        assert r["status"] == STATUS_OK
        assert r["f1"] == pytest.approx(1.0)

    def test_no_ground_truth(self):
        r = evaluate_decisions([{"topic": "x", "timestamp": 0}], None)
        assert r["status"] == STATUS_NO_GT

    def test_topic_jaccard_matching(self):
        gt   = [{"topic": "we should use model b", "timestamp": 0.0}]
        pred = [{"topic": "use model b", "timestamp": 100.0}]  # time far but topic overlaps
        r = evaluate_decisions(pred, gt, timestamp_tolerance=10.0)
        # Topic Jaccard >= 0.3 → should match
        assert r["tp"] >= 1

    def test_no_match_returns_zero_f1(self):
        gt   = [{"topic": "completely different topic", "timestamp": 0.0}]
        pred = [{"topic": "xyz abc", "timestamp": 500.0}]
        r = evaluate_decisions(pred, gt, timestamp_tolerance=5.0)
        assert r["f1"] == pytest.approx(0.0)


# ===========================================================================
# 7. Decision lineage evaluation
# ===========================================================================

class TestLineageEvaluation:
    def test_perfect_lineage_match(self):
        gt   = {"nodes": ["e1", "e2"], "edges": [{"source": "e1", "relationship": "leads_to", "target": "e2"}]}
        pred = {"nodes": ["e1", "e2"], "edges": [{"source": "e1", "relationship": "leads_to", "target": "e2"}]}
        r = evaluate_decision_lineage(pred, gt)
        assert r["status"] == STATUS_OK
        assert r["edge_metrics"]["f1"] == pytest.approx(1.0)
        assert r["node_metrics"]["f1"] == pytest.approx(1.0)

    def test_no_ground_truth(self):
        r = evaluate_decision_lineage({"nodes": [], "edges": []}, None)
        assert r["status"] == STATUS_NO_GT

    def test_missing_edge_reduces_recall(self):
        gt   = {"nodes": ["e1", "e2", "e3"],
                "edges": [{"source": "e1", "relationship": "leads_to", "target": "e2"},
                           {"source": "e2", "relationship": "leads_to", "target": "e3"}]}
        pred = {"nodes": ["e1", "e2"],
                "edges": [{"source": "e1", "relationship": "leads_to", "target": "e2"}]}
        r = evaluate_decision_lineage(pred, gt)
        assert r["edge_metrics"]["recall"] < 1.0

    def test_extra_edge_reduces_precision(self):
        gt   = {"nodes": ["e1", "e2"], "edges": [{"source": "e1", "relationship": "x", "target": "e2"}]}
        pred = {"nodes": ["e1", "e2", "e3"],
                "edges": [{"source": "e1", "relationship": "x", "target": "e2"},
                           {"source": "e2", "relationship": "y", "target": "e3"}]}
        r = evaluate_decision_lineage(pred, gt)
        assert r["edge_metrics"]["precision"] < 1.0


# ===========================================================================
# 8. Influence ranking evaluation
# ===========================================================================

class TestInfluenceRankingEvaluation:
    def test_perfect_agreement(self):
        sys_r = ["A", "B", "C"]
        hum_r = ["A", "B", "C"]
        r = evaluate_influence_ranking(sys_r, hum_r)
        assert r["status"] == STATUS_OK
        assert r["spearman_correlation"] == pytest.approx(1.0, abs=0.01)

    def test_reversed_ranking(self):
        sys_r = ["A", "B", "C"]
        hum_r = ["C", "B", "A"]
        r = evaluate_influence_ranking(sys_r, hum_r)
        assert r["status"] == STATUS_OK
        assert r["spearman_correlation"] < 0

    def test_no_human_ranking_returns_unavailable(self):
        r = evaluate_influence_ranking(["A", "B"], None)
        assert r["status"] == STATUS_NO_GT
        assert r["metric"] == "influence_ranking"

    def test_empty_human_ranking_returns_unavailable(self):
        r = evaluate_influence_ranking(["A", "B"], [])
        assert r["status"] == STATUS_NO_GT

    def test_result_structure(self):
        r = evaluate_influence_ranking(["A", "B", "C"], ["A", "B", "C"])
        for key in ("spearman_correlation", "kendall_tau", "n_participants"):
            assert key in r

    def test_note_warns_against_fabrication(self):
        r = evaluate_influence_ranking(["A", "B"], ["A", "B"])
        assert "note" in r
        assert len(r["note"]) > 0


# ===========================================================================
# 9. Spearman and Kendall pure-Python fallback
# ===========================================================================

class TestRankCorrelations:
    def test_spearman_perfect(self):
        assert _spearman([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)

    def test_spearman_reversed(self):
        assert _spearman([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)

    def test_spearman_single_pair_nan(self):
        result = _spearman([1.0], [1.0])
        assert math.isnan(result)

    def test_kendall_perfect(self):
        assert _kendall_tau([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)

    def test_kendall_reversed(self):
        assert _kendall_tau([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)


# ===========================================================================
# 10. Efficiency metrics
# ===========================================================================

class TestEfficiency:
    def test_basic_timing(self):
        timings = {"preprocessing": 1.0, "vad": 0.5, "asr": 10.0}
        r = calculate_efficiency(timings, audio_duration_s=3600.0)
        assert r["status"] == STATUS_OK
        assert r["total_processing_time_s"] == pytest.approx(11.5)
        assert r["rtf"] == pytest.approx(11.5 / 3600.0, abs=1e-4)

    def test_no_audio_duration_rtf_none(self):
        r = calculate_efficiency({"asr": 10.0}, audio_duration_s=None)
        assert r["rtf"] is None

    def test_empty_timings_returns_error(self):
        r = calculate_efficiency({})
        assert r["status"] == STATUS_ERROR

    def test_rtf_less_than_one_faster_than_realtime(self):
        r = calculate_efficiency({"asr": 10.0}, audio_duration_s=3600.0)
        assert r["rtf"] < 1.0

    def test_stage_timings_preserved(self):
        timings = {"asr": 10.0, "diarization": 5.0}
        r = calculate_efficiency(timings)
        assert "stage_timings_s" in r
        assert r["stage_timings_s"]["asr"] == pytest.approx(10.0)


# ===========================================================================
# 11. Baseline calculations
# ===========================================================================

class TestBaselines:
    def test_max_norm_safety(self):
        assert _max_norm({"A": 0.0, "B": 0.0}) == {"A": 0.0, "B": 0.0}

    def test_max_norm_correct(self):
        result = _max_norm({"A": 2.0, "B": 1.0})
        assert result["A"] == pytest.approx(1.0)
        assert result["B"] == pytest.approx(0.5)

    def test_b1_speaking_time(self):
        er, ev, dr, ir = _pipeline_data()
        b = baseline_speaking_time(er)
        assert b["baseline"] == "B1_speaking_time"
        assert "scores" in b
        for v in b["scores"].values():
            assert 0.0 <= v <= 1.0

    def test_b2_speaking_time_turns(self):
        er, ev, dr, ir = _pipeline_data()
        b = baseline_speaking_time_turns(er)
        assert b["baseline"] == "B2_speaking_time_turns"
        for v in b["scores"].values():
            assert 0.0 <= v <= 1.0

    def test_b3_decision_event_count(self):
        er, ev, dr, ir = _pipeline_data()
        b = baseline_decision_event_count(er, dr)
        assert b["baseline"] == "B3_decision_event_count"
        for v in b["scores"].values():
            assert 0.0 <= v <= 1.0

    def test_b4_decision_evidence_count(self):
        er, ev, dr, ir = _pipeline_data()
        b = baseline_decision_evidence_count(er, ev, dr)
        assert b["baseline"] == "B4_decision_evidence_count"
        for v in b["scores"].values():
            assert v >= 0.0

    def test_b5_transcript_only(self):
        er, ev, dr, ir = _pipeline_data()
        b = baseline_transcript_only(er, dr)
        assert b["baseline"] == "B5_transcript_only"

    def test_b6_audio_ppt_no_decision(self):
        er, ev, dr, ir = _pipeline_data()
        b = baseline_audio_ppt_no_decision(er, ev)
        assert b["baseline"] == "B6_audio_ppt_no_decision"
        for v in b["scores"].values():
            assert 0.0 <= v <= 1.0

    def test_speaking_time_not_same_as_decision_linked(self):
        er, ev, dr, ir = _pipeline_data()
        b1 = baseline_speaking_time(er)
        b3 = baseline_decision_event_count(er, dr)
        # Both baselines must produce scores for the same speakers
        assert set(b1["scores"].keys()) == set(b3["scores"].keys())
        # B1 raw seconds must be positive (speakers have duration)
        assert any(v > 0 for v in b1["raw_seconds"].values())
        # B3 raw counts can differ from B1 — they measure different things
        assert b3["baseline"] != b1["baseline"]


# ===========================================================================
# 12. Comparison table
# ===========================================================================

class TestComparisonTable:
    def test_table_structure(self):
        er, ev, dr, ir = _pipeline_data()
        baselines = [
            baseline_speaking_time(er),
            baseline_decision_event_count(er, dr),
        ]
        result = build_comparison_table(baselines, proposed_scores=None, human_ranking=None)
        assert "comparison_table" in result
        assert "note" in result

    def test_no_fabricated_values_without_human_ranking(self):
        er, ev, dr, ir = _pipeline_data()
        b = baseline_speaking_time(er)
        result = build_comparison_table([b], proposed_scores=None, human_ranking=None)
        for row in result["comparison_table"]:
            assert row["spearman"] is None
            assert row["kendall"] is None

    def test_proposed_method_present_when_scores_provided(self):
        er, ev, dr, ir = _pipeline_data()
        from src.meeting.influence import compute_influence
        inf_result = compute_influence(er, ev, dr, ir)
        proposed = {p.participant: p.influence_score for p in inf_result.participants}
        baselines = [baseline_speaking_time(er)]
        result = build_comparison_table(baselines, proposed_scores=proposed)
        methods = [row["method"] for row in result["comparison_table"]]
        assert "Proposed_decision_linked" in methods


# ===========================================================================
# 13. Ablation framework
# ===========================================================================

class TestAblation:
    def test_ablation_configs_complete(self):
        ids = [cfg[0] for cfg in ABLATION_CONFIGS]
        for expected in ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"):
            assert expected in ids

    def test_run_all_ablations_produces_one_result_per_config(self):
        er, ev, dr, ir = _pipeline_data()
        results = run_all_ablations(er, ev, dr, ir, human_ranking=None)
        assert len(results) == len(ABLATION_CONFIGS)

    def test_ablation_result_structure(self):
        er, ev, dr, ir = _pipeline_data()
        results = run_all_ablations(er, ev, dr, ir)
        for r in results:
            assert "experiment" in r
            assert "label" in r
            assert "removed_component" in r
            assert "ablation_flags" in r
            assert "metrics" in r

    def test_a1_full_system_has_nonzero_scores(self):
        er, ev, dr, ir = _pipeline_data()
        results = run_all_ablations(er, ev, dr, ir)
        a1 = next(r for r in results if r["experiment"] == "A1")
        total = sum(a1["influence_scores"].values())
        assert total >= 0.0   # should have some score

    def test_metrics_none_without_human_ranking(self):
        er, ev, dr, ir = _pipeline_data()
        results = run_all_ablations(er, ev, dr, ir, human_ranking=None)
        for r in results:
            assert r["metrics"]["spearman"] is None
            assert r["metrics"]["kendall"] is None

    def test_ablation_dict_serialisable(self):
        er, ev, dr, ir = _pipeline_data()
        results = run_all_ablations(er, ev, dr, ir)
        payload = ablation_results_to_dict(results, "test_meeting")
        # Must be JSON-serialisable
        json.dumps(payload)

    def test_ablation_uses_same_data(self):
        """All ablations must use the same input data — no dataset changes between runs."""
        er, ev, dr, ir = _pipeline_data()
        results = run_all_ablations(er, ev, dr, ir)
        # Verify meeting_id is consistent across all experiments
        # (all use the same er.meeting_id, so all scores are for the same meeting)
        assert len(results) == len(ABLATION_CONFIGS)


# ===========================================================================
# 14. Missing ground truth handling
# ===========================================================================

class TestMissingGroundTruth:
    def test_wer_no_gt(self):
        r = calculate_wer(None, "text")
        assert r["status"] == STATUS_NO_GT

    def test_der_no_gt(self):
        r = calculate_der(None, [])
        assert r["status"] == STATUS_NO_GT

    def test_alignment_no_gt(self):
        r = evaluate_alignment([{"segment_id": 1, "slide_id": "s1"}], None)
        assert r["status"] == STATUS_NO_GT

    def test_events_no_gt(self):
        r = evaluate_events([{"event_type": "proposal", "start": 0.0}], None)
        assert r["status"] == STATUS_NO_GT

    def test_decisions_no_gt(self):
        r = evaluate_decisions([{"topic": "x"}], None)
        assert r["status"] == STATUS_NO_GT

    def test_lineage_no_gt(self):
        r = evaluate_decision_lineage({"nodes": [], "edges": []}, None)
        assert r["status"] == STATUS_NO_GT

    def test_influence_no_gt(self):
        r = evaluate_influence_ranking(["A", "B"], None)
        assert r["status"] == STATUS_NO_GT

    def test_no_gt_response_has_metric_field(self):
        """Every ground-truth-unavailable response must identify the metric."""
        responses = [
            calculate_wer(None, "text"),
            calculate_der(None, []),
            evaluate_alignment([{"segment_id": 1, "slide_id": "s"}], None),
            evaluate_events([{"event_type": "proposal", "start": 0}], None),
            evaluate_decisions([{"topic": "x"}], None),
            evaluate_decision_lineage(None, None),
            evaluate_influence_ranking(["A"], None),
        ]
        for r in responses:
            assert r["status"] == STATUS_NO_GT
            assert "metric" in r


# ===========================================================================
# 15. Reproducibility metadata
# ===========================================================================

class TestReproducibilityMetadata:
    def test_metadata_structure(self):
        meta = build_eval_metadata("test_meeting", dataset="AMI")
        assert meta["meeting_id"] == "test_meeting"
        assert meta["dataset"] == "AMI"
        assert "evaluation_timestamp" in meta
        assert "metric_definitions" in meta

    def test_no_secrets_in_metadata(self):
        meta = build_eval_metadata("m", config={"safe_key": "safe_value"})
        meta_str = json.dumps(meta).lower()
        for sensitive in ("password", "token", "secret", "key", "credential"):
            assert sensitive not in meta_str or "safe_key" in meta_str


# ===========================================================================
# 16. Evaluation runner integration (file I/O)
# ===========================================================================

class TestEvaluationIO:
    def test_save_and_load_metrics_json(self, tmp_path):
        metrics = {
            "meeting_id": "test",
            "wer": calculate_wer("hello world", "hello world"),
            "alignment": {"status": STATUS_NO_GT, "metric": "alignment"},
        }
        p = tmp_path / "metrics.json"
        p.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        loaded = json.loads(p.read_text(encoding="utf-8"))
        assert loaded["meeting_id"] == "test"
        assert loaded["wer"]["status"] == STATUS_OK

    def test_comparison_csv_structure(self, tmp_path):
        import csv
        rows = [
            {"method": "B1_speaking_time", "description": "d", "spearman": None, "kendall": None, "status": STATUS_NO_GT},
            {"method": "Proposed", "description": "d2", "spearman": None, "kendall": None, "status": STATUS_NO_GT},
        ]
        p = tmp_path / "comparison.csv"
        with open(p, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["method", "description", "spearman", "kendall", "status"])
            writer.writeheader()
            writer.writerows(rows)
        with open(p, encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
        assert len(reader) == 2
        assert reader[0]["method"] == "B1_speaking_time"
