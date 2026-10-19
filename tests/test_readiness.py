"""Regressions for the remaining product and evaluation gaps."""
import numpy as np
import pytest
import json


def test_decision_consumed_by_previous_cluster_is_not_reused_as_final():
    from src.meeting.decisions import reconstruct_decisions
    from src.meeting.events import EventExtractionResult
    from src.meeting.evidence import EvidenceExtractionResult
    from tests.test_meeting import _make_event
    events = EventExtractionResult(meeting_id="m", events=[
        _make_event("e1", "decision", "S1", 0, 5),
        _make_event("e2", "decision", "S2", 80, 85),
        _make_event("e3", "proposal", "S1", 190, 195),
    ])
    result = reconstruct_decisions(events, EvidenceExtractionResult(meeting_id="m"),
                                   require_final_decision=True)
    assert len(result.decisions) == 1
    assert result.decisions[0].final_decision["event_id"] == "e2"


def test_distant_generic_agreement_does_not_resolve_a_proposal_from_hours_ago():
    from src.meeting.decisions import reconstruct_decisions
    from src.meeting.events import EventExtractionResult
    from src.meeting.evidence import EvidenceExtractionResult
    from tests.test_meeting import _make_event
    events=EventExtractionResult("m", [_make_event("p", "proposal", "A", 0, 5),
                                      _make_event("a", "agreement", "B", 7200, 7205)])
    result=reconstruct_decisions(events, EvidenceExtractionResult("m"), temporal_window=120)
    assert len(result.decisions)==1 and result.decisions[0].status=="unresolved"


@pytest.mark.parametrize("temporal_weight,semantic_weight", [(0, 1), (.1, .9)])
def test_timing_does_not_veto_a_stronger_semantic_slide(temporal_weight, semantic_weight):
    from src.audio.asr import TranscriptSegment
    from src.fusion.multimodal_representation import align_segment
    from src.fusion.temporal_alignment import SlideTimingInfo
    result = align_segment(
        TranscriptSegment(1, 0, 5, "S1", "budget review"), ["current", "revisited"],
        [SlideTimingInfo("current", 0, 5), SlideTimingInfo("revisited", 20, 25)],
        np.zeros((2, 2)), None, 2, temporal_weight, semantic_weight, .3,
        precomputed_scores={"current": .05, "revisited": .95})
    assert result.selected_slide == "revisited"
    assert len(result.slide_candidates) == 2


def test_full_transcript_baselines_include_speech_without_events_and_merge_turns():
    from src.evaluation.baselines import baseline_speaking_time, baseline_speaking_time_turns
    from src.meeting.events import EventExtractionResult
    from tests.test_meeting import _make_event
    events = EventExtractionResult("m", [_make_event("e1", "proposal", "A", 0, 5)])
    speech = [{"speaker": "A", "start": 0, "end": 5},
              {"speaker": "B", "start": 6, "end": 30},
              {"speaker": "B", "start": 29, "end": 60},
              {"speaker": "UNKNOWN", "start": 60, "end": 62},
              {"speaker": "B", "start": 62, "end": 63}]
    result = baseline_speaking_time(events, speech)
    assert result["input_source"] == "full_transcript"
    assert result["raw_seconds"] == {"A": 5, "B": 55}
    assert result["scores"]["B"] == 1
    assert baseline_speaking_time_turns(events, speech)["raw_turns"] == {"A": 1, "B": 2}
    assert baseline_speaking_time(events)["input_source"] == "event_duration_proxy"


def test_transcript_only_baseline_keeps_slide_grounded_speech():
    from src.evaluation.baselines import baseline_transcript_only
    from tests.test_evaluation import _pipeline_data
    er, _, dr, _ = _pipeline_data()
    from dataclasses import replace
    er.events = [replace(event, slide_id="slide_01") for event in er.events]
    result = baseline_transcript_only(er, dr)
    assert sum(result["raw_counts"].values()) > 0
    assert all(event.slide_id == "slide_01" for event in er.events)


def test_structural_ablations_rerun_downstream_instead_of_changing_weights():
    from src.evaluation.ablation import run_all_ablations
    from tests.test_evaluation import _pipeline_data
    er, ev, dr, ir = _pipeline_data()
    speech = [{"segment_id": 1, "speaker": "A", "start": 0, "end": 3,
               "text": "We should approve the budget.", "slide_id": "slide_01"},
              {"segment_id": 2, "speaker": "B", "start": 4, "end": 7,
               "text": "We decided to approve the budget.", "slide_id": "slide_01"},
              {"segment_id": 3, "speaker": "C", "start": 8, "end": 30,
               "text": "Ordinary discussion without a candidate."}]
    results = {r["experiment"]: r for r in run_all_ablations(er, ev, dr, ir,
        transcript_segments=speech, alignment_variants={"A3": speech})}
    for key in ("A2", "A3"):
        assert results[key]["analysis_mode"] == "downstream_rerun"
        assert results[key]["ablation_flags"] == {}
        assert "C" in results[key]["influence_scores"]
    assert results["A4"]["status"] == "input_unavailable"
    assert results["A4"]["metrics"]["spearman"] is None
    assert all(r["metrics"]["spearman"] is None for r in results.values())


def test_temporal_only_alignment_needs_no_embedding_model_or_weights(tmp_path):
    from src.audio.asr import TranscriptResult, TranscriptSegment, _save_json
    from src.ppt.extract import PresentationData, SlideData
    from src.ppt.io import save_presentation_json
    from src.fusion.multimodal_representation import run_alignment
    transcript, slides = tmp_path/"transcript.json", tmp_path/"slides.json"
    _save_json(TranscriptResult("m", "en", 5, 0, [], [TranscriptSegment(1, 0, 5, "A", "budget")]), transcript)
    save_presentation_json(PresentationData("m", "slides.pptx", 1,
        [SlideData("slide_01", 1, "Budget", [], [], None, {})]), slides)
    data = json.loads(slides.read_text())
    data["slides"][0].update(start_time=0, end_time=5)
    slides.write_text(json.dumps(data))
    result, _, _, _ = run_alignment(transcript, slides, output_dir=tmp_path,
        temporal_weight=1, semantic_weight=0)
    assert result[0].selected_slide == "slide_01"


def test_tied_influence_scores_are_not_arbitrarily_sorted_into_ranks():
    from src.evaluation.metrics import evaluate_influence_ranking, _spearman, _kendall_tau
    from scipy.stats import spearmanr, kendalltau
    x, y = [1, 1, 2, 3], [1, 1, 3, 2]
    assert _spearman(x, y) == pytest.approx(spearmanr(x, y).statistic)
    assert _kendall_tau(x, y) == pytest.approx(kendalltau(x, y).statistic)
    result = evaluate_influence_ranking({"A": .5, "B": .5, "C": 0}, ["A", "B", "C"])
    assert result["spearman_correlation"] == pytest.approx(.866025, abs=1e-6)
    undefined = evaluate_influence_ranking({"A": 0, "B": 0}, ["A", "B"])
    assert undefined["spearman_correlation"] is None
    assert undefined["status"] == "error"
    json.dumps(undefined, allow_nan=False)


def test_decision_matching_does_not_invent_zero_times_or_ignore_conflicting_fields():
    from src.evaluation.metrics import evaluate_decisions
    assert evaluate_decisions([{}], [{}])["tp"] == 0
    assert evaluate_decisions([{"topic": "budget", "timestamp": 0}],
                              [{"topic": "budget", "timestamp": 500}])["tp"] == 0
    assert evaluate_decisions([{"topic": "budget", "timestamp": 0}],
                              [{"topic": "hiring", "timestamp": 0}])["tp"] == 0


def test_event_matching_is_maximum_one_to_one_and_respects_known_speakers():
    from src.evaluation.metrics import evaluate_events
    predictions = [{"event_type": "proposal", "start": start, "speaker": "A"} for start in [3, 0]]
    truth = [{"event_type": "proposal", "start": start, "speaker": "A"} for start in [1, 6]]
    assert evaluate_events(predictions, truth, 3)["tp"] == 2
    assert evaluate_events(predictions[::-1], truth[::-1], 3)["tp"] == 2
    truth[0]["speaker"] = "B"
    assert evaluate_events(predictions, truth, 3)["tp"] == 1
    assert evaluate_events([{"event_type":"proposal"}], [{"event_type":"proposal"}])["tp"] == 0
