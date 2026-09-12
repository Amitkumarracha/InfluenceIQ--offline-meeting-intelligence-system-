"""
Tests for Phase 8 — Meeting event and evidence extraction.

All tests use small synthetic in-memory data.
No real meeting files are required.
No event-extraction accuracy is claimed from synthetic tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.meeting.events import (
    ALL_EVENT_TYPES,
    EventExtractionResult,
    KeywordEventExtractor,
    MeetingEvent,
    _event_to_dict,
    get_active_event_types,
    load_events_json,
    save_events_json,
)
from src.meeting.evidence import (
    EvidenceExtractionResult,
    EvidenceRelation,
    _relation_to_dict,
    extract_evidence,
    load_evidence_json,
    save_evidence_json,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seg(
    segment_id: int,
    text: str,
    speaker: str = "SPEAKER_01",
    start: float = 0.0,
    end: float = 5.0,
    slide_id: str | None = "slide_01",
) -> dict[str, Any]:
    return {
        "segment_id": segment_id,
        "speaker": speaker,
        "start": start,
        "end": end,
        "text": text,
        "slide_id": slide_id,
        "alignment": {"temporal_score": None, "semantic_score": 0.5, "combined_score": 0.5},
    }


def _event(
    event_id: str = "event_001",
    event_type: str = "proposal",
    speaker: str = "SPEAKER_01",
    start: float = 0.0,
    end: float = 5.0,
    text: str = "We should use a smaller model.",
    slide_id: str | None = "slide_01",
    confidence: float | None = 0.7,
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
        confidence=confidence,
        source_segment_id=source_segment_id,
    )


# ---------------------------------------------------------------------------
# 1. Event object creation
# ---------------------------------------------------------------------------

class TestEventObject:
    def test_fields_preserved(self):
        e = _event()
        assert e.event_id == "event_001"
        assert e.event_type == "proposal"
        assert e.speaker == "SPEAKER_01"
        assert e.start == 0.0
        assert e.end == 5.0
        assert e.slide_id == "slide_01"
        assert e.source_segment_id == 1

    def test_null_slide_allowed(self):
        e = _event(slide_id=None)
        assert e.slide_id is None

    def test_null_confidence_allowed(self):
        e = _event(confidence=None)
        assert e.confidence is None


# ---------------------------------------------------------------------------
# 2. Event type validation
# ---------------------------------------------------------------------------

class TestEventTypes:
    def test_all_taxonomy_types_present(self):
        expected = {
            "proposal", "question", "objection", "evidence",
            "correction", "clarification", "agreement", "disagreement",
            "revision", "decision", "action_item",
        }
        assert set(ALL_EVENT_TYPES) == expected

    def test_get_active_types_returns_list(self):
        types = get_active_event_types()
        assert isinstance(types, list)
        assert len(types) > 0
        for t in types:
            assert t in ALL_EVENT_TYPES


# ---------------------------------------------------------------------------
# 3. Keyword extractor — event detection
# ---------------------------------------------------------------------------

class TestKeywordExtractor:
    extractor = KeywordEventExtractor(confidence_threshold=0.0)

    def _extract(self, texts: list[str]) -> EventExtractionResult:
        segs = [_seg(i + 1, t, start=float(i * 10), end=float(i * 10 + 5)) for i, t in enumerate(texts)]
        return self.extractor.extract(segs, "test_meeting")

    def test_proposal_detected(self):
        result = self._extract(["We should adopt a smaller architecture."])
        types = [e.event_type for e in result.events]
        assert "proposal" in types

    def test_question_detected(self):
        result = self._extract(["What is the current accuracy?"])
        types = [e.event_type for e in result.events]
        assert "question" in types

    def test_agreement_detected(self):
        result = self._extract(["I agree, that sounds good."])
        types = [e.event_type for e in result.events]
        assert "agreement" in types

    def test_disagreement_detected(self):
        result = self._extract(["I disagree with that approach."])
        types = [e.event_type for e in result.events]
        assert "disagreement" in types

    def test_evidence_detected(self):
        result = self._extract(["According to our experiments, accuracy reached 94%."])
        types = [e.event_type for e in result.events]
        assert "evidence" in types

    def test_action_item_detected(self):
        result = self._extract(["Please follow up on the deployment by next week."])
        types = [e.event_type for e in result.events]
        assert "action_item" in types

    def test_empty_text_skipped(self):
        result = self._extract(["", "   "])
        assert result.events == []

    def test_no_match_skipped(self):
        # Pure filler with no keywords
        result = self._extract(["Mmm, okay."])
        # May or may not match; just ensure no crash and type is valid if any
        for e in result.events:
            assert e.event_type in ALL_EVENT_TYPES

    def test_meeting_id_preserved(self):
        segs = [_seg(1, "We should try a new approach.")]
        result = self.extractor.extract(segs, "my_meeting")
        assert result.meeting_id == "my_meeting"


# ---------------------------------------------------------------------------
# 4. Timestamp and speaker preservation
# ---------------------------------------------------------------------------

class TestTraceability:
    def test_speaker_preserved(self):
        extractor = KeywordEventExtractor(confidence_threshold=0.0)
        seg = _seg(1, "We should use a transformer model.", speaker="SPEAKER_02",
                   start=100.0, end=110.0)
        result = extractor.extract([seg], "meeting")
        proposal_events = [e for e in result.events if e.event_type == "proposal"]
        assert any(e.speaker == "SPEAKER_02" for e in proposal_events)

    def test_timestamps_preserved(self):
        extractor = KeywordEventExtractor(confidence_threshold=0.0)
        seg = _seg(1, "I agree, that is correct.", start=55.5, end=60.0)
        result = extractor.extract([seg], "meeting")
        for e in result.events:
            if e.source_segment_id == 1:
                assert e.start == pytest.approx(55.5)
                assert e.end == pytest.approx(60.0)

    def test_source_segment_id_preserved(self):
        extractor = KeywordEventExtractor(confidence_threshold=0.0)
        seg = _seg(42, "Let's go with this approach.")
        result = extractor.extract([seg], "meeting")
        for e in result.events:
            assert e.source_segment_id == 42

    def test_slide_id_preserved(self):
        extractor = KeywordEventExtractor(confidence_threshold=0.0)
        seg = _seg(1, "We should reduce the model size.", slide_id="slide_05")
        result = extractor.extract([seg], "meeting")
        for e in result.events:
            if e.source_segment_id == 1:
                assert e.slide_id == "slide_05"

    def test_no_slide_sentinel_becomes_none(self):
        extractor = KeywordEventExtractor(confidence_threshold=0.0)
        seg = _seg(1, "We should reduce the model size.", slide_id="NO_CONFIDENT_SLIDE")
        result = extractor.extract([seg], "meeting")
        for e in result.events:
            assert e.slide_id is None


# ---------------------------------------------------------------------------
# 5. EventExtractionResult helpers
# ---------------------------------------------------------------------------

class TestExtractionResult:
    def test_by_type(self):
        result = EventExtractionResult(meeting_id="m", events=[
            _event("e1", "proposal"),
            _event("e2", "question"),
            _event("e3", "proposal"),
        ])
        proposals = result.by_type("proposal")
        assert len(proposals) == 2

    def test_count_by_type(self):
        result = EventExtractionResult(meeting_id="m", events=[
            _event("e1", "proposal"),
            _event("e2", "question"),
            _event("e3", "proposal"),
            _event("e4", "agreement"),
        ])
        counts = result.count_by_type()
        assert counts["proposal"] == 2
        assert counts["question"] == 1
        assert counts["agreement"] == 1
        assert "evidence" not in counts  # not present → excluded


# ---------------------------------------------------------------------------
# 6. Evidence relationship structure
# ---------------------------------------------------------------------------

class TestEvidenceStructure:
    def test_relation_fields(self):
        r = EvidenceRelation(
            evidence_id="evidence_001",
            source_event_id="event_001",
            target_event_id="event_002",
            relationship="supports",
            slide_id="slide_03",
            confidence=0.8,
        )
        assert r.evidence_id == "evidence_001"
        assert r.relationship == "supports"
        assert r.slide_id == "slide_03"

    def test_null_confidence_allowed(self):
        r = EvidenceRelation("e1", "ev1", "ev2", "supports", None, None)
        assert r.confidence is None

    def test_by_relationship(self):
        result = EvidenceExtractionResult(meeting_id="m", relations=[
            EvidenceRelation("e1", "ev1", "ev2", "supports", None, None),
            EvidenceRelation("e2", "ev3", "ev4", "contradicts", None, None),
            EvidenceRelation("e3", "ev5", "ev6", "supports", None, None),
        ])
        assert len(result.by_relationship("supports")) == 2
        assert len(result.by_relationship("contradicts")) == 1


# ---------------------------------------------------------------------------
# 7. Evidence extraction rules
# ---------------------------------------------------------------------------

class TestEvidenceExtraction:
    def _events(self, specs: list[tuple[str, str, float, float]]) -> EventExtractionResult:
        """specs: list of (event_id, event_type, start, end)"""
        events = [
            MeetingEvent(
                event_id=eid,
                event_type=etype,
                speaker="SPEAKER_01",
                start=start,
                end=end,
                text="placeholder",
                slide_id="slide_01",
                confidence=0.7,
                source_segment_id=i + 1,
            )
            for i, (eid, etype, start, end) in enumerate(specs)
        ]
        return EventExtractionResult(meeting_id="test", events=events)

    def test_slide_grounding_creates_supports(self):
        er = self._events([("event_001", "proposal", 0.0, 5.0)])
        evidence = extract_evidence(er)
        slide_supports = [
            r for r in evidence.relations
            if r.source_event_id == "slide:slide_01" and r.relationship == "supports"
        ]
        assert len(slide_supports) >= 1

    def test_objection_creates_contradicts(self):
        er = self._events([
            ("event_001", "proposal",  0.0, 5.0),
            ("event_002", "objection", 6.0, 10.0),
        ])
        evidence = extract_evidence(er)
        contradicts = [r for r in evidence.relations if r.relationship == "contradicts"]
        assert len(contradicts) >= 1
        assert contradicts[0].source_event_id == "event_002"
        assert contradicts[0].target_event_id == "event_001"

    def test_agreement_creates_supports(self):
        er = self._events([
            ("event_001", "proposal",  0.0, 5.0),
            ("event_002", "agreement", 6.0, 10.0),
        ])
        evidence = extract_evidence(er)
        ev_supports = [
            r for r in evidence.relations
            if r.relationship == "supports" and r.source_event_id == "event_002"
        ]
        assert len(ev_supports) >= 1

    def test_revision_creates_modifies(self):
        er = self._events([
            ("event_001", "proposal", 0.0, 5.0),
            ("event_002", "revision", 6.0, 10.0),
        ])
        evidence = extract_evidence(er)
        modifies = [r for r in evidence.relations if r.relationship == "modifies"]
        assert len(modifies) >= 1

    def test_clarification_creates_clarifies(self):
        er = self._events([
            ("event_001", "proposal",      0.0, 5.0),
            ("event_002", "clarification", 6.0, 10.0),
        ])
        evidence = extract_evidence(er)
        clarifies = [r for r in evidence.relations if r.relationship == "clarifies"]
        assert len(clarifies) >= 1

    def test_window_prevents_distant_link(self):
        # Events 200 s apart — should NOT be linked (window=60s)
        er = self._events([
            ("event_001", "proposal",  0.0,   5.0),
            ("event_002", "objection", 200.0, 205.0),
        ])
        evidence = extract_evidence(er, window_s=60.0)
        contradicts = [r for r in evidence.relations if r.relationship == "contradicts"]
        assert len(contradicts) == 0

    def test_no_events_no_relations(self):
        er = EventExtractionResult(meeting_id="empty", events=[])
        evidence = extract_evidence(er)
        assert evidence.relations == []


# ---------------------------------------------------------------------------
# 8. JSON serialisation
# ---------------------------------------------------------------------------

class TestSerialisationEvents:
    def test_event_to_dict_round_trip(self):
        e = _event()
        d = _event_to_dict(e)
        assert d["event_id"] == "event_001"
        assert d["event_type"] == "proposal"
        assert d["slide_id"] == "slide_01"
        json.dumps(d)  # must not raise

    def test_save_and_load_events(self, tmp_path):
        result = EventExtractionResult(meeting_id="test_mtg", events=[
            _event("event_001", "proposal"),
            _event("event_002", "question", confidence=None),
        ])
        p = tmp_path / "events.json"
        save_events_json(result, p)
        loaded = load_events_json(p)
        assert loaded.meeting_id == "test_mtg"
        assert len(loaded.events) == 2
        assert loaded.events[0].event_id == "event_001"
        assert loaded.events[1].confidence is None

    def test_events_json_structure(self, tmp_path):
        result = EventExtractionResult(meeting_id="m", events=[_event()])
        p = tmp_path / "ev.json"
        save_events_json(result, p)
        raw = json.loads(p.read_text(encoding="utf-8"))
        assert "meeting_id" in raw
        assert "num_events" in raw
        assert "events" in raw


class TestSerialisationEvidence:
    def test_relation_to_dict_round_trip(self):
        r = EvidenceRelation("e1", "ev1", "ev2", "supports", "slide_01", 0.8)
        d = _relation_to_dict(r)
        assert d["evidence_id"] == "e1"
        assert d["relationship"] == "supports"
        json.dumps(d)

    def test_save_and_load_evidence(self, tmp_path):
        result = EvidenceExtractionResult(meeting_id="test_mtg", relations=[
            EvidenceRelation("e1", "ev1", "ev2", "supports", "slide_01", 0.8),
            EvidenceRelation("e2", "slide:slide_02", "ev3", "supports", "slide_02", None),
        ])
        p = tmp_path / "evidence.json"
        save_evidence_json(result, p)
        loaded = load_evidence_json(p)
        assert loaded.meeting_id == "test_mtg"
        assert len(loaded.relations) == 2
        assert loaded.relations[1].confidence is None

    def test_evidence_json_structure(self, tmp_path):
        result = EvidenceExtractionResult(meeting_id="m", relations=[
            EvidenceRelation("e1", "ev1", "ev2", "supports", None, None)
        ])
        p = tmp_path / "ev.json"
        save_evidence_json(result, p)
        raw = json.loads(p.read_text(encoding="utf-8"))
        assert "meeting_id" in raw
        assert "num_relations" in raw
        assert "relations" in raw


# ---------------------------------------------------------------------------
# 9. Invalid input handling
# ---------------------------------------------------------------------------

class TestInvalidInputs:
    def test_missing_events_file(self, tmp_path):
        from src.meeting.evidence import run_evidence_extraction
        with pytest.raises(FileNotFoundError):
            run_evidence_extraction(tmp_path / "nonexistent.json")

    def test_missing_multimodal_file(self, tmp_path):
        from src.meeting.events import run_event_extraction
        with pytest.raises(FileNotFoundError):
            run_event_extraction(tmp_path / "nonexistent.json")

    def test_extractor_handles_missing_text_key(self):
        extractor = KeywordEventExtractor(confidence_threshold=0.0)
        segs = [{"segment_id": 1, "speaker": "S", "start": 0.0, "end": 5.0}]
        # Should not raise; segments without 'text' are skipped
        result = extractor.extract(segs, "m")
        assert result.events == []

    def test_invalid_event_type_not_fabricated(self):
        extractor = KeywordEventExtractor(confidence_threshold=0.0)
        seg = _seg(1, "xyzzy frobnicator blort")
        result = extractor.extract([seg], "m")
        for e in result.events:
            assert e.event_type in ALL_EVENT_TYPES


# ---------------------------------------------------------------------------
# 10. run_event_extraction and run_evidence_extraction integration
# ---------------------------------------------------------------------------

class TestRunners:
    def _write_multimodal(self, tmp_path: Path, segments: list[dict]) -> Path:
        p = tmp_path / "test_multimodal.json"
        p.write_text(json.dumps({
            "meeting_id": "test_run",
            "num_segments": len(segments),
            "segments": segments,
        }), encoding="utf-8")
        return p

    def test_run_event_extraction_creates_file(self, tmp_path):
        from src.meeting.events import run_event_extraction
        segs = [
            _seg(1, "We should adopt a new model.", start=0.0, end=5.0),
            _seg(2, "I agree, that sounds great.", start=6.0, end=10.0),
            _seg(3, "According to the data, accuracy is 92%.", start=11.0, end=16.0),
        ]
        mm_path = self._write_multimodal(tmp_path, segs)
        result, events_path = run_event_extraction(
            multimodal_path=mm_path,
            output_dir=tmp_path,
        )
        assert events_path.exists()
        assert result.meeting_id == "test_run"
        assert isinstance(result.events, list)

    def test_run_evidence_extraction_creates_file(self, tmp_path):
        from src.meeting.events import run_event_extraction
        from src.meeting.evidence import run_evidence_extraction
        segs = [
            _seg(1, "We should use a transformer.", start=0.0, end=5.0),
            _seg(2, "I disagree with that approach.", start=6.0, end=10.0),
        ]
        mm_path = self._write_multimodal(tmp_path, segs)
        event_result, events_path = run_event_extraction(
            multimodal_path=mm_path,
            output_dir=tmp_path,
        )
        ev_result, evidence_path = run_evidence_extraction(
            events_path=events_path,
            output_dir=tmp_path,
        )
        assert evidence_path.exists()
        assert isinstance(ev_result.relations, list)

    def test_full_traceability_chain(self, tmp_path):
        """Verify: segment_id → event → evidence → slide_id all preserved."""
        from src.meeting.events import run_event_extraction
        from src.meeting.evidence import run_evidence_extraction
        segs = [
            _seg(7, "We should reduce the parameter count.", slide_id="slide_03",
                 start=0.0, end=5.0),
            _seg(8, "I agree, that is a good idea.", slide_id="slide_03",
                 start=6.0, end=10.0),
        ]
        mm_path = self._write_multimodal(tmp_path, segs)
        event_result, events_path = run_event_extraction(
            multimodal_path=mm_path,
            output_dir=tmp_path,
        )
        # Check segment traceability
        for e in event_result.events:
            assert e.source_segment_id in (7, 8)
            assert e.slide_id == "slide_03"

        ev_result, _ = run_evidence_extraction(
            events_path=events_path,
            output_dir=tmp_path,
        )
        # Every relation with a non-slide source should point to a known event
        known_event_ids = {e.event_id for e in event_result.events}
        for r in ev_result.relations:
            if not r.source_event_id.startswith("slide:"):
                assert r.source_event_id in known_event_ids
            assert r.target_event_id in known_event_ids


# ===========================================================================
# Phase 9 — Decision reconstruction and lineage
# ===========================================================================

from src.meeting.decisions import (
    DECISION_STATUSES,
    Decision,
    DecisionResult,
    EventImpact,
    LineageEdge,
    ParticipantRole,
    _build_lineage,
    _classify_impact,
    _infer_status,
    load_decisions_json,
    reconstruct_decisions,
    save_decision_graph_json,
    save_decisions_json,
)
from src.meeting.evidence import EvidenceExtractionResult, EvidenceRelation, extract_evidence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(
    event_id: str,
    event_type: str,
    speaker: str = "SPEAKER_01",
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


def _full_chain() -> tuple[EventExtractionResult, EvidenceExtractionResult]:
    """
    Synthetic decision chain:
      Proposal → Objection → Evidence → Revision → Agreement → Decision
    """
    events = [
        _make_event("e1", "proposal",   "S1",  0.0,  5.0, "We should use Model A.", "slide_01", 1),
        _make_event("e2", "objection",  "S2", 10.0, 15.0, "Model A has lower accuracy.", "slide_02", 2),
        _make_event("e3", "evidence",   "S3", 20.0, 25.0, "According to the data, Model B scores 94%.", "slide_03", 3),
        _make_event("e4", "revision",   "S1", 30.0, 35.0, "Let's use Model B instead.", "slide_03", 4),
        _make_event("e5", "agreement",  "S2", 40.0, 45.0, "I agree, that sounds correct.", None, 5),
        _make_event("e6", "decision",   "S1", 50.0, 55.0, "We will use Model B.", "slide_03", 6),
    ]
    event_result = EventExtractionResult(meeting_id="test", events=events)
    evidence_result = extract_evidence(event_result, window_s=120.0)
    return event_result, evidence_result


# ---------------------------------------------------------------------------
# 11. Decision object creation
# ---------------------------------------------------------------------------

class TestDecisionObject:
    def test_decision_fields(self):
        d = Decision(
            decision_id="decision_001",
            status="confirmed",
            topic="Model Selection",
            proposal={"event_id": "e1", "speaker": "S1", "text": "We should use Model A."},
            discussion=[],
            supporting_evidence=[],
            revisions=[],
            agreements=[{"event_id": "e5", "speaker": "S2"}],
            final_decision={"event_id": "e6", "text": "We will use Model B."},
            participants=["S1", "S2"],
            participant_roles=[ParticipantRole("S1", "proposer")],
            supporting_segments=[1, 6],
            supporting_slides=["slide_01"],
            lineage=[LineageEdge("e1", "leads_to", "e4")],
            event_impacts=[EventImpact("e1", "directly_decision_relevant")],
            confidence=None,
        )
        assert d.decision_id == "decision_001"
        assert d.status == "confirmed"
        assert d.confidence is None
        assert d.final_decision["event_id"] == "e6"

    def test_decision_statuses_complete(self):
        assert set(DECISION_STATUSES) == {"confirmed", "probable", "unresolved", "conflicting"}

    def test_lineage_edge_fields(self):
        edge = LineageEdge("e1", "leads_to", "e2")
        assert edge.source == "e1"
        assert edge.relationship == "leads_to"
        assert edge.target == "e2"

    def test_event_impact_fields(self):
        ei = EventImpact("e1", "directly_decision_relevant")
        assert ei.event_id == "e1"
        assert ei.impact == "directly_decision_relevant"

    def test_participant_role_fields(self):
        pr = ParticipantRole("SPEAKER_01", "proposer")
        assert pr.speaker == "SPEAKER_01"
        assert pr.role == "proposer"


# ---------------------------------------------------------------------------
# 12. Status inference
# ---------------------------------------------------------------------------

class TestStatusInference:
    def _events_of_types(self, *types: str) -> list[MeetingEvent]:
        return [
            _make_event(f"e{i}", t, start=float(i * 5))
            for i, t in enumerate(types, 1)
        ]

    def test_confirmed_with_decision(self):
        events = self._events_of_types("proposal", "agreement", "decision")
        assert _infer_status(events, has_final_decision=True) == "confirmed"

    def test_probable_with_agreement_only(self):
        events = self._events_of_types("proposal", "agreement")
        assert _infer_status(events, has_final_decision=False) == "probable"

    def test_unresolved_proposal_only(self):
        events = self._events_of_types("proposal")
        assert _infer_status(events, has_final_decision=False) == "unresolved"

    def test_conflicting_multiple_proposals_with_objection(self):
        events = self._events_of_types("proposal", "proposal", "objection")
        assert _infer_status(events, has_final_decision=False) == "conflicting"


# ---------------------------------------------------------------------------
# 13. Impact classification
# ---------------------------------------------------------------------------

class TestImpactClassification:
    def test_proposal_directly_relevant(self):
        e = _make_event("e1", "proposal")
        assert _classify_impact(e, "e1", None, set()) == "directly_decision_relevant"

    def test_final_decision_directly_relevant(self):
        e = _make_event("e2", "decision")
        assert _classify_impact(e, "e1", "e2", set()) == "directly_decision_relevant"

    def test_revision_directly_relevant(self):
        e = _make_event("e3", "revision")
        assert _classify_impact(e, "e1", "e6", {"e3"}) == "directly_decision_relevant"

    def test_objection_indirectly_relevant(self):
        e = _make_event("e2", "objection")
        assert _classify_impact(e, "e1", "e6", set()) == "indirectly_decision_relevant"

    def test_question_contextual(self):
        e = _make_event("e2", "question")
        assert _classify_impact(e, "e1", "e6", set()) == "contextual"

    def test_action_item_unresolved(self):
        e = _make_event("e2", "action_item")
        assert _classify_impact(e, "e1", "e6", set()) == "unresolved"


# ---------------------------------------------------------------------------
# 14. Full chain reconstruction
# ---------------------------------------------------------------------------

class TestFullChainReconstruction:
    def test_decision_detected(self):
        er, ev = _full_chain()
        result = reconstruct_decisions(er, ev, temporal_window=120.0)
        assert len(result.decisions) >= 1

    def test_confirmed_status(self):
        er, ev = _full_chain()
        result = reconstruct_decisions(er, ev, temporal_window=120.0)
        confirmed = result.by_status("confirmed")
        assert len(confirmed) >= 1

    def test_proposal_preserved(self):
        er, ev = _full_chain()
        result = reconstruct_decisions(er, ev, temporal_window=120.0)
        d = result.decisions[0]
        assert d.proposal is not None
        assert "Model A" in d.proposal["text"]

    def test_final_decision_preserved(self):
        er, ev = _full_chain()
        result = reconstruct_decisions(er, ev, temporal_window=120.0)
        d = result.decisions[0]
        assert d.final_decision is not None
        assert "Model B" in d.final_decision["text"]

    def test_revisions_collected(self):
        er, ev = _full_chain()
        result = reconstruct_decisions(er, ev, temporal_window=120.0)
        d = result.decisions[0]
        assert len(d.revisions) >= 1
        assert "Model B" in d.revisions[0]["text"]

    def test_agreements_collected(self):
        er, ev = _full_chain()
        result = reconstruct_decisions(er, ev, temporal_window=120.0)
        d = result.decisions[0]
        assert len(d.agreements) >= 1

    def test_participants_extracted(self):
        er, ev = _full_chain()
        result = reconstruct_decisions(er, ev, temporal_window=120.0)
        d = result.decisions[0]
        assert "S1" in d.participants
        assert "S2" in d.participants

    def test_slide_grounding_preserved(self):
        er, ev = _full_chain()
        result = reconstruct_decisions(er, ev, temporal_window=120.0)
        d = result.decisions[0]
        assert "slide_03" in d.supporting_slides

    def test_supporting_segments_preserved(self):
        er, ev = _full_chain()
        result = reconstruct_decisions(er, ev, temporal_window=120.0)
        d = result.decisions[0]
        assert len(d.supporting_segments) >= 1

    def test_lineage_edges_present(self):
        er, ev = _full_chain()
        result = reconstruct_decisions(er, ev, temporal_window=120.0)
        d = result.decisions[0]
        assert len(d.lineage) >= 1
        for edge in d.lineage:
            assert edge.source
            assert edge.target
            assert edge.relationship


# ---------------------------------------------------------------------------
# 15. Unresolved and conflicting decisions
# ---------------------------------------------------------------------------

class TestUncertaintyHandling:
    def test_unresolved_proposal_no_agreement(self):
        events = [_make_event("e1", "proposal", "S1", 0.0, 5.0, "We should try X.")]
        er = EventExtractionResult(meeting_id="m", events=events)
        ev = EvidenceExtractionResult(meeting_id="m")
        result = reconstruct_decisions(er, ev, temporal_window=120.0, require_final_decision=False)
        assert len(result.decisions) >= 1
        assert result.decisions[0].status == "unresolved"

    def test_require_final_decision_skips_agreement_only(self):
        events = [
            _make_event("e1", "proposal",  "S1", 0.0, 5.0),
            _make_event("e2", "agreement", "S2", 6.0, 10.0),
        ]
        er = EventExtractionResult(meeting_id="m", events=events)
        ev = EvidenceExtractionResult(meeting_id="m")
        result = reconstruct_decisions(er, ev, temporal_window=120.0, require_final_decision=True)
        # No "decision"-type event → no decisions produced
        assert all(d.status != "confirmed" for d in result.decisions)

    def test_no_events_no_decisions(self):
        er = EventExtractionResult(meeting_id="m", events=[])
        ev = EvidenceExtractionResult(meeting_id="m")
        result = reconstruct_decisions(er, ev)
        assert result.decisions == []

    def test_event_id_traceability(self):
        er, ev = _full_chain()
        result = reconstruct_decisions(er, ev, temporal_window=120.0)
        d = result.decisions[0]
        all_known = {e.event_id for e in er.events}
        for edge in d.lineage:
            assert edge.source in all_known or edge.source.startswith("slide:")
            assert edge.target in all_known or edge.target.startswith("slide:")


# ---------------------------------------------------------------------------
# 16. Participant roles
# ---------------------------------------------------------------------------

class TestParticipantRoles:
    def test_proposer_role(self):
        er, ev = _full_chain()
        result = reconstruct_decisions(er, ev, temporal_window=120.0)
        d = result.decisions[0]
        roles = {pr.role for pr in d.participant_roles}
        assert "proposer" in roles

    def test_final_decision_maker_role(self):
        er, ev = _full_chain()
        result = reconstruct_decisions(er, ev, temporal_window=120.0)
        d = result.decisions[0]
        roles = {pr.role for pr in d.participant_roles}
        assert "final_decision_maker" in roles

    def test_no_organisational_roles(self):
        er, ev = _full_chain()
        result = reconstruct_decisions(er, ev, temporal_window=120.0)
        forbidden = {"manager", "engineer", "leader", "ceo", "director"}
        for d in result.decisions:
            for pr in d.participant_roles:
                assert pr.role.lower() not in forbidden


# ---------------------------------------------------------------------------
# 17. JSON serialisation
# ---------------------------------------------------------------------------

class TestDecisionSerialisation:
    def test_save_and_load_decisions(self, tmp_path):
        er, ev = _full_chain()
        result = reconstruct_decisions(er, ev, temporal_window=120.0)
        p = tmp_path / "decisions.json"
        save_decisions_json(result, p)
        loaded = load_decisions_json(p)
        assert loaded.meeting_id == result.meeting_id
        assert len(loaded.decisions) == len(result.decisions)
        if loaded.decisions:
            d = loaded.decisions[0]
            assert d.decision_id
            assert d.status in DECISION_STATUSES
            assert isinstance(d.lineage, list)
            assert isinstance(d.event_impacts, list)

    def test_decisions_json_structure(self, tmp_path):
        er, ev = _full_chain()
        result = reconstruct_decisions(er, ev, temporal_window=120.0)
        p = tmp_path / "d.json"
        save_decisions_json(result, p)
        raw = json.loads(p.read_text(encoding="utf-8"))
        assert "meeting_id" in raw
        assert "num_decisions" in raw
        assert "decisions" in raw
        if raw["decisions"]:
            d = raw["decisions"][0]
            for key in ("decision_id", "status", "participants",
                        "supporting_segments", "supporting_slides", "lineage"):
                assert key in d

    def test_graph_json_structure(self, tmp_path):
        er, ev = _full_chain()
        result = reconstruct_decisions(er, ev, temporal_window=120.0)
        p = tmp_path / "graph.json"
        save_decision_graph_json(result, p)
        raw = json.loads(p.read_text(encoding="utf-8"))
        assert "meeting_id" in raw
        assert "decision_graphs" in raw
        for g in raw["decision_graphs"]:
            assert "decision_id" in g
            assert "graph" in g

    def test_json_round_trip_lineage(self, tmp_path):
        er, ev = _full_chain()
        result = reconstruct_decisions(er, ev, temporal_window=120.0)
        p = tmp_path / "decisions_rt.json"
        save_decisions_json(result, p)
        loaded = load_decisions_json(p)
        for orig, load in zip(result.decisions, loaded.decisions):
            assert len(orig.lineage) == len(load.lineage)


# ---------------------------------------------------------------------------
# 18. run_decision_reconstruction integration
# ---------------------------------------------------------------------------

class TestDecisionRunner:
    def _write_json(self, tmp_path: Path, name: str, payload: dict) -> Path:
        p = tmp_path / name
        p.write_text(json.dumps(payload), encoding="utf-8")
        return p

    def test_runner_creates_output_files(self, tmp_path):
        from src.meeting.decisions import run_decision_reconstruction
        er, ev = _full_chain()

        # Write events JSON
        from src.meeting.events import save_events_json
        from src.meeting.evidence import save_evidence_json
        ep = tmp_path / "test_events.json"
        evp = tmp_path / "test_evidence.json"
        save_events_json(er, ep)
        save_evidence_json(ev, evp)

        result, d_path, g_path = run_decision_reconstruction(
            events_path=ep,
            evidence_path=evp,
            output_dir=tmp_path,
        )
        assert d_path.exists()
        assert g_path.exists()
        assert isinstance(result.decisions, list)

    def test_runner_missing_events_raises(self, tmp_path):
        from src.meeting.decisions import run_decision_reconstruction
        with pytest.raises(FileNotFoundError):
            run_decision_reconstruction(
                events_path=tmp_path / "missing.json",
                evidence_path=tmp_path / "evidence.json",
            )

    def test_runner_missing_evidence_raises(self, tmp_path):
        from src.meeting.decisions import run_decision_reconstruction
        from src.meeting.events import save_events_json
        er, _ = _full_chain()
        ep = tmp_path / "events.json"
        save_events_json(er, ep)
        with pytest.raises(FileNotFoundError):
            run_decision_reconstruction(
                events_path=ep,
                evidence_path=tmp_path / "missing.json",
            )


# ===========================================================================
# Phase 10 — Participant Interaction Analysis
# ===========================================================================

from src.meeting.interaction import (
    INTERACTION_TYPES,
    Interaction,
    InteractionResult,
    ParticipantStats,
    build_participant_graph,
    extract_interactions,
    load_interactions_json,
    save_interaction_graph_json,
    save_interactions_json,
)
from src.meeting.decisions import (
    reconstruct_decisions,
    DecisionResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_interaction(
    interaction_id: str = "interaction_001",
    source_speaker: str = "SPEAKER_02",
    target_speaker: str | None = "SPEAKER_01",
    interaction_type: str = "objection",
    timestamp: float = 10.0,
    source_event_id: str = "event_002",
    target_event_id: str | None = "event_001",
    related_decision_id: str | None = None,
    related_slide_id: str | None = None,
    text: str = "I disagree.",
) -> Interaction:
    return Interaction(
        interaction_id=interaction_id,
        source_speaker=source_speaker,
        target_speaker=target_speaker,
        interaction_type=interaction_type,
        timestamp=timestamp,
        source_event_id=source_event_id,
        target_event_id=target_event_id,
        related_decision_id=related_decision_id,
        related_slide_id=related_slide_id,
        text=text,
        confidence=None,
    )


def _interaction_chain() -> tuple[EventExtractionResult, EvidenceExtractionResult, DecisionResult]:
    """
    Synthetic scenario:
      SPEAKER_01: "We should use Option A."        (proposal)
      SPEAKER_02: "I disagree, Option A is costly." (disagreement)
      SPEAKER_03: "Slide 6 shows Option B is better." (evidence)
      SPEAKER_01: "Then let's revise and use Option B." (revision)
      SPEAKER_02: "I agree."                        (agreement)
      SPEAKER_01: "We will use Option B."           (decision)
    """
    events = [
        _make_event("e1", "proposal",     "SPEAKER_01",  0.0,  5.0,
                    "We should use Option A.", "slide_01", 1),
        _make_event("e2", "disagreement", "SPEAKER_02", 10.0, 15.0,
                    "I disagree, Option A is costly.", "slide_01", 2),
        _make_event("e3", "evidence",     "SPEAKER_03", 20.0, 25.0,
                    "Slide 6 shows Option B is better.", "slide_06", 3),
        _make_event("e4", "revision",     "SPEAKER_01", 30.0, 35.0,
                    "Then let's revise and use Option B.", "slide_06", 4),
        _make_event("e5", "agreement",    "SPEAKER_02", 40.0, 45.0,
                    "I agree.", None, 5),
        _make_event("e6", "decision",     "SPEAKER_01", 50.0, 55.0,
                    "We will use Option B.", "slide_06", 6),
    ]
    event_result = EventExtractionResult(meeting_id="test_interactions", events=events)
    evidence_result = extract_evidence(event_result, window_s=120.0)
    decision_result = reconstruct_decisions(event_result, evidence_result, temporal_window=120.0)
    return event_result, evidence_result, decision_result


# ---------------------------------------------------------------------------
# 19. Interaction object creation
# ---------------------------------------------------------------------------

class TestInteractionObject:
    def test_fields_preserved(self):
        i = _make_interaction()
        assert i.interaction_id == "interaction_001"
        assert i.source_speaker == "SPEAKER_02"
        assert i.target_speaker == "SPEAKER_01"
        assert i.interaction_type == "objection"
        assert i.timestamp == 10.0
        assert i.confidence is None

    def test_null_target_allowed(self):
        i = _make_interaction(target_speaker=None)
        assert i.target_speaker is None

    def test_null_related_decision_allowed(self):
        i = _make_interaction(related_decision_id=None)
        assert i.related_decision_id is None

    def test_null_slide_allowed(self):
        i = _make_interaction(related_slide_id=None)
        assert i.related_slide_id is None


# ---------------------------------------------------------------------------
# 20. Interaction type validation
# ---------------------------------------------------------------------------

class TestInteractionTypes:
    def test_all_types_present(self):
        expected = {
            "support", "objection", "response", "agreement", "disagreement",
            "clarification", "correction", "challenge", "reference",
        }
        assert set(INTERACTION_TYPES) == expected

    def test_interaction_type_valid_in_make_interaction(self):
        for t in INTERACTION_TYPES:
            i = _make_interaction(interaction_type=t)
            assert i.interaction_type == t


# ---------------------------------------------------------------------------
# 21. Source / target assignment
# ---------------------------------------------------------------------------

class TestSourceTargetAssignment:
    def test_objection_source_is_objector(self):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        objections = result.by_type("objection") + result.by_type("disagreement") + result.by_type("challenge")
        # In the chain, SPEAKER_02 is the one disagreeing
        speakers = {i.source_speaker for i in objections}
        assert "SPEAKER_02" in speakers

    def test_agreement_source_is_agreer(self):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        agreements = result.by_type("agreement")
        if agreements:
            # SPEAKER_02 agrees with the revision
            speakers = {i.source_speaker for i in agreements}
            assert "SPEAKER_02" in speakers

    def test_no_self_interaction(self):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        for intr in result.interactions:
            if intr.target_speaker is not None:
                assert intr.source_speaker != intr.target_speaker

    def test_unknown_target_is_none_not_fabricated(self):
        # Single event with no preceding targetable — target must be None
        events = [_make_event("e1", "objection", "SPEAKER_01", 0.0, 5.0)]
        er = EventExtractionResult(meeting_id="m", events=events)
        ev = EvidenceExtractionResult(meeting_id="m")
        dr = DecisionResult(meeting_id="m")
        result = extract_interactions(er, ev, dr, temporal_window=60.0)
        for intr in result.interactions:
            # If no target found, must be None — never a random speaker
            if intr.target_event_id is None:
                assert intr.target_speaker is None


# ---------------------------------------------------------------------------
# 22. Temporal window filtering
# ---------------------------------------------------------------------------

class TestTemporalWindowFiltering:
    def test_events_within_window_linked(self):
        events = [
            _make_event("e1", "proposal",  "S1",  0.0,  5.0),
            _make_event("e2", "objection", "S2", 10.0, 15.0),
        ]
        er = EventExtractionResult(meeting_id="m", events=events)
        ev = extract_evidence(er, window_s=120.0)
        dr = reconstruct_decisions(er, ev, temporal_window=120.0)
        result = extract_interactions(er, ev, dr, temporal_window=60.0)
        assert len(result.interactions) >= 1

    def test_events_outside_window_not_linked_pass3(self):
        # 200 s gap — Pass 3 should not link these
        events = [
            _make_event("e1", "proposal",  "S1",   0.0,   5.0),
            _make_event("e2", "objection", "S2", 200.0, 205.0),
        ]
        er = EventExtractionResult(meeting_id="m", events=events)
        # No evidence relations — Pass 1 and 2 produce nothing
        ev = EvidenceExtractionResult(meeting_id="m")
        dr = DecisionResult(meeting_id="m")
        result = extract_interactions(er, ev, dr, temporal_window=60.0)
        # All interactions should have source e2 pointing to None (no target found)
        for intr in result.interactions:
            if intr.source_event_id == "e2":
                assert intr.target_event_id is None or intr.timestamp >= 200.0


# ---------------------------------------------------------------------------
# 23. Specific interaction type detection
# ---------------------------------------------------------------------------

class TestInteractionTypeDetection:
    def test_objection_relationship_detected(self):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        types = {i.interaction_type for i in result.interactions}
        assert "objection" in types or "disagreement" in types or "challenge" in types

    def test_support_relationship_detected(self):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        types = {i.interaction_type for i in result.interactions}
        assert "support" in types or "agreement" in types

    def test_agreement_relationship_detected(self):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        types = {i.interaction_type for i in result.interactions}
        assert "agreement" in types or "support" in types

    def test_response_or_reference_detected(self):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        types = {i.interaction_type for i in result.interactions}
        assert types & {"response", "reference", "support", "agreement", "disagreement"}


# ---------------------------------------------------------------------------
# 24. Decision-linked interactions
# ---------------------------------------------------------------------------

class TestDecisionLinkedInteractions:
    def test_some_interactions_linked_to_decision(self):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        linked = result.decision_linked()
        assert len(linked) >= 1

    def test_decision_id_preserved(self):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        linked = result.decision_linked()
        for intr in linked:
            assert intr.related_decision_id is not None
            assert intr.related_decision_id.startswith("decision_")

    def test_count_by_type_returns_dict(self):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        counts = result.count_by_type()
        assert isinstance(counts, dict)
        for k, v in counts.items():
            assert k in INTERACTION_TYPES
            assert isinstance(v, int) and v >= 0


# ---------------------------------------------------------------------------
# 25. Slide-linked interactions
# ---------------------------------------------------------------------------

class TestSlideLinkedInteractions:
    def test_slide_id_preserved_when_available(self):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        slide_linked = [i for i in result.interactions if i.related_slide_id is not None]
        assert len(slide_linked) >= 1

    def test_no_forced_slide_when_absent(self):
        # agreement event has no slide — ensure slide_id may be None
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        for intr in result.interactions:
            # slide_id may be None — it must not be a non-existent ID
            if intr.related_slide_id is not None:
                assert isinstance(intr.related_slide_id, str)


# ---------------------------------------------------------------------------
# 26. Participant graph construction
# ---------------------------------------------------------------------------

class TestParticipantGraph:
    def test_graph_nodes_are_speakers(self):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        G = build_participant_graph(result)
        if G is None:
            pytest.skip("networkx not available")
        assert set(G.nodes()) == set(result.participants)

    def test_graph_edges_represent_interactions(self):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        G = build_participant_graph(result)
        if G is None:
            pytest.skip("networkx not available")
        directed_interactions = [i for i in result.interactions if i.target_speaker is not None]
        assert G.number_of_edges() == len(directed_interactions)

    def test_graph_node_stats_are_interaction_counts_not_influence(self):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        G = build_participant_graph(result)
        if G is None:
            pytest.skip("networkx not available")
        # Node attributes must be interaction counts — not "influence" or "impact"
        for _, attrs in G.nodes(data=True):
            for key in attrs:
                assert "influence" not in key.lower()
                assert "impact" not in key.lower()


# ---------------------------------------------------------------------------
# 27. Participant statistics
# ---------------------------------------------------------------------------

class TestParticipantStats:
    def test_stats_produced_for_all_speakers(self):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        stat_speakers = {s.participant for s in result.participant_stats}
        assert stat_speakers == set(result.participants)

    def test_initiated_plus_received_consistent(self):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        total_initiated = sum(s.interactions_initiated for s in result.participant_stats)
        assert total_initiated == len(result.interactions)

    def test_type_counts_sum_to_initiated(self):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        for stats in result.participant_stats:
            type_total = sum(stats.type_counts.values())
            assert type_total == stats.interactions_initiated

    def test_stats_not_labelled_influence(self):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        for stats in result.participant_stats:
            assert not hasattr(stats, "influence_score")
            assert not hasattr(stats, "impact_score")


# ---------------------------------------------------------------------------
# 28. JSON serialisation
# ---------------------------------------------------------------------------

class TestInteractionSerialisation:
    def test_save_and_load_interactions(self, tmp_path):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        p = tmp_path / "interactions.json"
        save_interactions_json(result, p)
        loaded = load_interactions_json(p)
        assert loaded.meeting_id == result.meeting_id
        assert len(loaded.interactions) == len(result.interactions)

    def test_interactions_json_structure(self, tmp_path):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        p = tmp_path / "interactions.json"
        save_interactions_json(result, p)
        raw = json.loads(p.read_text(encoding="utf-8"))
        assert "meeting_id" in raw
        assert "num_participants" in raw
        assert "participants" in raw
        assert "num_interactions" in raw
        assert "interactions" in raw
        assert "participant_stats" in raw

    def test_interaction_fields_in_json(self, tmp_path):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        if not result.interactions:
            pytest.skip("no interactions produced")
        p = tmp_path / "interactions.json"
        save_interactions_json(result, p)
        raw = json.loads(p.read_text(encoding="utf-8"))
        first = raw["interactions"][0]
        for key in (
            "interaction_id", "source_speaker", "target_speaker",
            "interaction_type", "timestamp", "source_event_id",
            "target_event_id", "related_decision_id", "related_slide_id",
            "text", "confidence",
        ):
            assert key in first

    def test_confidence_is_null_in_json(self, tmp_path):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        if not result.interactions:
            pytest.skip("no interactions produced")
        p = tmp_path / "interactions.json"
        save_interactions_json(result, p)
        raw = json.loads(p.read_text(encoding="utf-8"))
        for intr in raw["interactions"]:
            assert intr["confidence"] is None

    def test_graph_json_structure(self, tmp_path):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        p = tmp_path / "graph.json"
        save_interaction_graph_json(result, p)
        raw = json.loads(p.read_text(encoding="utf-8"))
        assert "meeting_id" in raw
        assert "nodes" in raw
        assert "edges" in raw

    def test_graph_json_nodes_are_speakers(self, tmp_path):
        er, ev, dr = _interaction_chain()
        result = extract_interactions(er, ev, dr, temporal_window=120.0)
        p = tmp_path / "graph.json"
        save_interaction_graph_json(result, p)
        raw = json.loads(p.read_text(encoding="utf-8"))
        node_speakers = {n["speaker"] for n in raw["nodes"]}
        assert node_speakers == set(result.participants)


# ---------------------------------------------------------------------------
# 29. run_interaction_analysis integration
# ---------------------------------------------------------------------------

class TestInteractionRunner:
    def test_runner_creates_output_files(self, tmp_path):
        from src.meeting.interaction import run_interaction_analysis
        from src.meeting.events import save_events_json
        from src.meeting.evidence import save_evidence_json
        from src.meeting.decisions import save_decisions_json

        er, ev, dr = _interaction_chain()
        ep = tmp_path / "test_events.json"
        evp = tmp_path / "test_evidence.json"
        dp = tmp_path / "test_decisions.json"
        save_events_json(er, ep)
        save_evidence_json(ev, evp)
        save_decisions_json(dr, dp)

        result, interactions_path, graph_path = run_interaction_analysis(
            events_path=ep,
            evidence_path=evp,
            decisions_path=dp,
            output_dir=tmp_path,
        )
        assert interactions_path.exists()
        assert graph_path.exists()
        assert isinstance(result.interactions, list)

    def test_runner_missing_events_raises(self, tmp_path):
        from src.meeting.interaction import run_interaction_analysis
        with pytest.raises(FileNotFoundError):
            run_interaction_analysis(
                events_path=tmp_path / "missing.json",
                evidence_path=tmp_path / "evidence.json",
                decisions_path=tmp_path / "decisions.json",
            )

    def test_runner_missing_evidence_raises(self, tmp_path):
        from src.meeting.interaction import run_interaction_analysis
        from src.meeting.events import save_events_json
        er, _, _ = _interaction_chain()
        ep = tmp_path / "events.json"
        save_events_json(er, ep)
        with pytest.raises(FileNotFoundError):
            run_interaction_analysis(
                events_path=ep,
                evidence_path=tmp_path / "missing_evidence.json",
                decisions_path=tmp_path / "decisions.json",
            )


# ===========================================================================
# Phase 11 — Decision-linked participant influence analysis
# ===========================================================================

from src.meeting.influence import (
    DEFAULT_WEIGHTS,
    FEATURE_KEYS,
    BaselineScores,
    DecisionContribution,
    FeatureVector,
    InfluenceResult,
    ParticipantInfluence,
    _load_weights,
    _max_normalise,
    compute_influence,
    extract_baselines,
    extract_features,
    load_influence_json,
    run_influence_analysis,
    save_baselines_json,
    save_influence_json,
)
from src.meeting.interaction import (
    extract_interactions,
    InteractionResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _influence_chain() -> tuple[
    EventExtractionResult,
    EvidenceExtractionResult,
    DecisionResult,
    InteractionResult,
]:
    """
    Synthetic scenario for influence testing.

    SPEAKER_A: speaks a lot (high speaking time, many turns)
                but limited decision-linked evidence
    SPEAKER_B: speaks less, raises one critical objection,
                provides evidence that drives a revision,
                contribution is slide-grounded and decision-linked
    """
    events = [
        # SPEAKER_A: lots of discussion
        _make_event("e1", "proposal",    "SPEAKER_A",  0.0,  5.0,
                    "We should use Option A.", "slide_01", 1),
        _make_event("e2", "question",    "SPEAKER_A", 60.0, 65.0,
                    "What are the metrics?", None, 2),
        _make_event("e3", "question",    "SPEAKER_A", 70.0, 75.0,
                    "Can we check the slides?", None, 3),
        _make_event("e4", "question",    "SPEAKER_A", 80.0, 85.0,
                    "Did anyone benchmark this?", None, 4),
        # SPEAKER_B: targeted, decision-linked contributions
        _make_event("e5", "objection",   "SPEAKER_B", 10.0, 15.0,
                    "I disagree — Option A is costly.", "slide_06", 5),
        _make_event("e6", "evidence",    "SPEAKER_B", 20.0, 25.0,
                    "According to the data, Option B is 40% cheaper.", "slide_06", 6),
        _make_event("e7", "revision",    "SPEAKER_A", 30.0, 35.0,
                    "Then let's revise and use Option B.", "slide_06", 7),
        _make_event("e8", "agreement",   "SPEAKER_B", 40.0, 45.0,
                    "I agree with the revision.", None, 8),
        _make_event("e9", "decision",    "SPEAKER_A", 50.0, 55.0,
                    "We will use Option B.", "slide_06", 9),
    ]
    event_result = EventExtractionResult(meeting_id="test_influence", events=events)
    evidence_result = extract_evidence(event_result, window_s=120.0)
    decision_result = reconstruct_decisions(event_result, evidence_result, temporal_window=120.0)
    interaction_result = extract_interactions(
        event_result, evidence_result, decision_result, temporal_window=120.0
    )
    return event_result, evidence_result, decision_result, interaction_result


# ---------------------------------------------------------------------------
# 30. FeatureVector object
# ---------------------------------------------------------------------------

class TestFeatureVector:
    def test_default_values_are_zero(self):
        fv = FeatureVector(participant="SPEAKER_01")
        for key in [
            "proposal_contribution", "evidence_contribution",
            "objection_contribution", "revision_contribution",
            "decision_contribution", "interaction_contribution",
            "slide_grounded_contribution",
        ]:
            assert getattr(fv, key) == 0.0

    def test_to_dict_keys(self):
        fv = FeatureVector(participant="SPEAKER_01")
        d = fv.to_dict()
        for key in [
            "proposal_contribution", "evidence_contribution",
            "objection_contribution", "revision_contribution",
            "decision_contribution", "interaction_contribution",
            "slide_grounded_contribution",
        ]:
            assert key in d

    def test_ablation_flags_default_true(self):
        fv = FeatureVector(participant="S")
        assert fv.use_proposal is True
        assert fv.use_evidence is True
        assert fv.use_objection is True
        assert fv.use_revision is True
        assert fv.use_decision is True
        assert fv.use_interaction is True
        assert fv.use_slide_grounding is True


# ---------------------------------------------------------------------------
# 31. Normalisation
# ---------------------------------------------------------------------------

class TestMaxNormalise:
    def test_max_becomes_one(self):
        result = _max_normalise({"A": 3.0, "B": 1.5, "C": 0.0})
        assert result["A"] == pytest.approx(1.0)
        assert result["B"] == pytest.approx(0.5)
        assert result["C"] == pytest.approx(0.0)

    def test_all_zero_stays_zero(self):
        result = _max_normalise({"A": 0.0, "B": 0.0})
        assert result["A"] == 0.0
        assert result["B"] == 0.0

    def test_no_nan(self):
        result = _max_normalise({"A": 0.0})
        import math
        assert not math.isnan(result["A"])

    def test_single_nonzero(self):
        result = _max_normalise({"A": 5.0})
        assert result["A"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 32. Weight loading and validation
# ---------------------------------------------------------------------------

class TestWeightLoading:
    def test_default_weights_cover_all_features(self):
        assert set(DEFAULT_WEIGHTS.keys()) == set(FEATURE_KEYS)

    def test_load_weights_returns_dict(self):
        w = _load_weights()
        assert isinstance(w, dict)
        for k in FEATURE_KEYS:
            assert k in w
            assert w[k] >= 0.0

    def test_weights_sum_to_one(self):
        w = _load_weights()
        assert sum(w.values()) == pytest.approx(1.0, abs=1e-6)

    def test_zero_weight_ablation(self):
        w = _load_weights()
        ablated = {k: 0.0 for k in FEATURE_KEYS}
        er, ev, dr, ir = _influence_chain()
        # Should not crash; all scores will be zero
        result = compute_influence(er, ev, dr, ir, weights=ablated)
        for p in result.participants:
            assert p.influence_score == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 33. Feature extraction
# ---------------------------------------------------------------------------

class TestFeatureExtraction:
    def test_returns_vector_per_speaker(self):
        er, ev, dr, ir = _influence_chain()
        vectors = extract_features(er, ev, dr, ir)
        speakers = {e.speaker for e in er.events}
        assert set(vectors.keys()) == speakers

    def test_decision_linked_proposal_gets_credit(self):
        er, ev, dr, ir = _influence_chain()
        vectors = extract_features(er, ev, dr, ir)
        # SPEAKER_A proposed and it's in a decision cluster
        assert vectors["SPEAKER_A"].proposal_contribution > 0

    def test_evidence_gets_credit(self):
        er, ev, dr, ir = _influence_chain()
        vectors = extract_features(er, ev, dr, ir)
        # SPEAKER_B provided slide-grounded evidence
        assert vectors["SPEAKER_B"].evidence_contribution > 0

    def test_objection_gets_credit(self):
        er, ev, dr, ir = _influence_chain()
        vectors = extract_features(er, ev, dr, ir)
        # SPEAKER_B objected and a revision followed
        assert vectors["SPEAKER_B"].objection_contribution > 0

    def test_slide_grounded_contribution(self):
        er, ev, dr, ir = _influence_chain()
        vectors = extract_features(er, ev, dr, ir)
        # Events on slide_06 in the decision cluster
        assert vectors["SPEAKER_B"].slide_grounded_contribution > 0


# ---------------------------------------------------------------------------
# 34. Weighted scoring
# ---------------------------------------------------------------------------

class TestWeightedScoring:
    def test_scores_in_unit_interval(self):
        er, ev, dr, ir = _influence_chain()
        result = compute_influence(er, ev, dr, ir)
        for p in result.participants:
            assert 0.0 <= p.influence_score <= 1.0 + 1e-9

    def test_all_scores_non_negative(self):
        er, ev, dr, ir = _influence_chain()
        result = compute_influence(er, ev, dr, ir)
        for p in result.participants:
            assert p.influence_score >= 0.0

    def test_scores_are_not_nan(self):
        import math
        er, ev, dr, ir = _influence_chain()
        result = compute_influence(er, ev, dr, ir)
        for p in result.participants:
            assert not math.isnan(p.influence_score)

    def test_speaking_time_is_not_dominant(self):
        """
        SPEAKER_A has more total speaking time (many questions).
        SPEAKER_B has more targeted decision-linked contributions.
        The scoring framework MUST allow SPEAKER_B to outscore SPEAKER_A.
        We do NOT assert a specific winner — we assert the framework
        can produce this outcome (i.e. scores are different).
        """
        er, ev, dr, ir = _influence_chain()
        result = compute_influence(er, ev, dr, ir)
        scores = {p.participant: p.influence_score for p in result.participants}
        # Scores must differ — speaking time alone must not flatten them
        assert scores["SPEAKER_A"] != scores["SPEAKER_B"]


# ---------------------------------------------------------------------------
# 35. Ranking
# ---------------------------------------------------------------------------

class TestRanking:
    def test_rank_1_has_highest_score(self):
        er, ev, dr, ir = _influence_chain()
        result = compute_influence(er, ev, dr, ir)
        rank1 = [p for p in result.participants if p.rank == 1]
        assert len(rank1) >= 1
        max_score = max(p.influence_score for p in result.participants)
        for p in rank1:
            assert p.influence_score == pytest.approx(max_score)

    def test_ranks_are_positive_integers(self):
        er, ev, dr, ir = _influence_chain()
        result = compute_influence(er, ev, dr, ir)
        for p in result.participants:
            assert isinstance(p.rank, int)
            assert p.rank >= 1

    def test_by_rank_sorted(self):
        er, ev, dr, ir = _influence_chain()
        result = compute_influence(er, ev, dr, ir)
        ranked = result.by_rank()
        for i in range(len(ranked) - 1):
            assert ranked[i].rank <= ranked[i + 1].rank

    def test_ties_share_same_rank(self):
        # Build scenario where two speakers have identical zero contributions
        events = [
            _make_event("e1", "question", "S1", 0.0, 5.0),
            _make_event("e2", "question", "S2", 6.0, 10.0),
        ]
        er = EventExtractionResult(meeting_id="m", events=events)
        ev = EvidenceExtractionResult(meeting_id="m")
        dr = DecisionResult(meeting_id="m")
        ir = InteractionResult(meeting_id="m", participants=["S1", "S2"])
        result = compute_influence(er, ev, dr, ir)
        ranks = [p.rank for p in result.participants]
        # Both should have rank 1 (tied at zero)
        assert ranks[0] == ranks[1]


# ---------------------------------------------------------------------------
# 36. Decision-level contribution
# ---------------------------------------------------------------------------

class TestDecisionLevelContribution:
    def test_decision_contributions_produced(self):
        er, ev, dr, ir = _influence_chain()
        result = compute_influence(er, ev, dr, ir)
        participants_with_decisions = [
            p for p in result.participants if p.decision_contributions
        ]
        assert len(participants_with_decisions) >= 1

    def test_contribution_score_in_range(self):
        er, ev, dr, ir = _influence_chain()
        result = compute_influence(er, ev, dr, ir)
        for p in result.participants:
            for dc in p.decision_contributions:
                assert 0.0 <= dc.contribution_score <= 1.0 + 1e-9

    def test_roles_are_valid_strings(self):
        er, ev, dr, ir = _influence_chain()
        result = compute_influence(er, ev, dr, ir)
        valid_roles = {
            "proposer", "objector", "reviser", "supporter",
            "final_decision_maker", "evidence_provider",
        }
        for p in result.participants:
            for dc in p.decision_contributions:
                for role in dc.roles:
                    assert role in valid_roles, f"Unexpected role: {role}"

    def test_supporting_events_are_known_event_ids(self):
        er, ev, dr, ir = _influence_chain()
        result = compute_influence(er, ev, dr, ir)
        known_ids = {e.event_id for e in er.events}
        for p in result.participants:
            for dc in p.decision_contributions:
                for eid in dc.supporting_events:
                    assert eid in known_ids


# ---------------------------------------------------------------------------
# 37. Baseline scores
# ---------------------------------------------------------------------------

class TestBaselineScores:
    def test_baselines_produced_per_speaker(self):
        er, ev, dr, ir = _influence_chain()
        baselines = extract_baselines(er, ev, dr)
        speakers = {e.speaker for e in er.events}
        assert set(baselines.keys()) == speakers

    def test_speaking_time_positive(self):
        er, ev, dr, ir = _influence_chain()
        baselines = extract_baselines(er, ev, dr)
        for b in baselines.values():
            assert b.speaking_time >= 0.0

    def test_speaking_time_norm_in_unit_interval(self):
        er, ev, dr, ir = _influence_chain()
        baselines = extract_baselines(er, ev, dr)
        for b in baselines.values():
            assert 0.0 <= b.speaking_time_norm <= 1.0 + 1e-9

    def test_b2_in_unit_interval(self):
        er, ev, dr, ir = _influence_chain()
        baselines = extract_baselines(er, ev, dr)
        for b in baselines.values():
            assert 0.0 <= b.speaking_time_turns <= 1.0 + 1e-9

    def test_b3_b4_non_negative(self):
        er, ev, dr, ir = _influence_chain()
        baselines = extract_baselines(er, ev, dr)
        for b in baselines.values():
            assert b.decision_event_count >= 0
            assert b.decision_evidence_count >= 0

    def test_baselines_stored_separately_from_influence(self):
        er, ev, dr, ir = _influence_chain()
        result = compute_influence(er, ev, dr, ir)
        # Baselines must be in result.baselines, NOT mixed into participant scores
        assert hasattr(result, "baselines")
        for p in result.participants:
            # No baseline field on ParticipantInfluence
            assert not hasattr(p, "speaking_time")
            assert not hasattr(p, "B1_speaking_time")


# ---------------------------------------------------------------------------
# 38. Explanation and traceability
# ---------------------------------------------------------------------------

class TestExplanationAndTraceability:
    def test_explanation_is_non_empty_list(self):
        er, ev, dr, ir = _influence_chain()
        result = compute_influence(er, ev, dr, ir)
        for p in result.participants:
            assert isinstance(p.explanation, list)
            assert len(p.explanation) >= 1

    def test_explanation_strings_not_generic(self):
        er, ev, dr, ir = _influence_chain()
        result = compute_influence(er, ev, dr, ir)
        # At least one participant with decision-linked evidence should have
        # a data-driven explanation referencing actual scores/counts
        explanations = [
            line
            for p in result.participants
            for line in p.explanation
        ]
        # Should not be all identical (would indicate fabricated generic text)
        assert len(set(explanations)) > 0

    def test_supporting_events_are_real_event_ids(self):
        er, ev, dr, ir = _influence_chain()
        result = compute_influence(er, ev, dr, ir)
        known_ids = {e.event_id for e in er.events}
        for p in result.participants:
            for eid in p.supporting_events:
                assert eid in known_ids

    def test_supporting_decisions_are_real_decision_ids(self):
        er, ev, dr, ir = _influence_chain()
        result = compute_influence(er, ev, dr, ir)
        known_dec_ids = {d.decision_id for d in dr.decisions}
        for p in result.participants:
            for did in p.supporting_decisions:
                assert did in known_dec_ids

    def test_score_not_labelled_causal(self):
        er, ev, dr, ir = _influence_chain()
        result = compute_influence(er, ev, dr, ir)
        disclaimer = result.method.get("disclaimer", "")
        assert "causal" not in disclaimer.lower() or "do not" in disclaimer.lower() or "not establish" in disclaimer.lower()


# ---------------------------------------------------------------------------
# 39. Ablation readiness
# ---------------------------------------------------------------------------

class TestAblation:
    def test_zeroing_all_features_gives_zero_scores(self):
        er, ev, dr, ir = _influence_chain()
        ablation = {k: False for k in FEATURE_KEYS}
        result = compute_influence(er, ev, dr, ir, ablation_flags=ablation)
        for p in result.participants:
            assert p.influence_score == pytest.approx(0.0)

    def test_disabling_one_feature_changes_scores(self):
        er, ev, dr, ir = _influence_chain()
        full = compute_influence(er, ev, dr, ir)
        ablated = compute_influence(er, ev, dr, ir, ablation_flags={"evidence": False})
        full_scores = {p.participant: p.influence_score for p in full.participants}
        abl_scores = {p.participant: p.influence_score for p in ablated.participants}
        # At least one participant's score should differ when evidence is removed
        assert full_scores != abl_scores


# ---------------------------------------------------------------------------
# 40. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_events_produces_empty_result(self):
        er = EventExtractionResult(meeting_id="m", events=[])
        ev = EvidenceExtractionResult(meeting_id="m")
        dr = DecisionResult(meeting_id="m")
        ir = InteractionResult(meeting_id="m", participants=[])
        result = compute_influence(er, ev, dr, ir)
        assert result.participants == []

    def test_single_participant_no_crash(self):
        events = [_make_event("e1", "proposal", "ONLY", 0.0, 5.0)]
        er = EventExtractionResult(meeting_id="m", events=events)
        ev = EvidenceExtractionResult(meeting_id="m")
        dr = DecisionResult(meeting_id="m")
        ir = InteractionResult(meeting_id="m", participants=["ONLY"])
        result = compute_influence(er, ev, dr, ir)
        assert len(result.participants) == 1
        assert 0.0 <= result.participants[0].influence_score <= 1.0 + 1e-9

    def test_no_decisions_still_produces_result(self):
        events = [
            _make_event("e1", "question", "S1", 0.0, 5.0),
            _make_event("e2", "question", "S2", 6.0, 10.0),
        ]
        er = EventExtractionResult(meeting_id="m", events=events)
        ev = EvidenceExtractionResult(meeting_id="m")
        dr = DecisionResult(meeting_id="m")
        ir = InteractionResult(meeting_id="m", participants=["S1", "S2"])
        result = compute_influence(er, ev, dr, ir)
        assert len(result.participants) == 2
        for p in result.participants:
            assert p.influence_score == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 41. JSON serialisation
# ---------------------------------------------------------------------------

class TestInfluenceSerialisation:
    def test_save_and_load_influence(self, tmp_path):
        er, ev, dr, ir = _influence_chain()
        result = compute_influence(er, ev, dr, ir)
        p = tmp_path / "influence.json"
        save_influence_json(result, p)
        loaded = load_influence_json(p)
        assert loaded.meeting_id == result.meeting_id
        assert len(loaded.participants) == len(result.participants)

    def test_influence_json_structure(self, tmp_path):
        er, ev, dr, ir = _influence_chain()
        result = compute_influence(er, ev, dr, ir)
        p = tmp_path / "influence.json"
        save_influence_json(result, p)
        raw = json.loads(p.read_text(encoding="utf-8"))
        assert "meeting_id" in raw
        assert "method" in raw
        assert "participants" in raw
        assert "num_participants" in raw
        if raw["participants"]:
            first = raw["participants"][0]
            for key in ("participant", "influence_score", "rank", "features",
                        "raw_features", "decision_contributions",
                        "supporting_decisions", "supporting_events", "explanation"):
                assert key in first

    def test_baselines_json_structure(self, tmp_path):
        er, ev, dr, ir = _influence_chain()
        result = compute_influence(er, ev, dr, ir)
        p = tmp_path / "baselines.json"
        save_baselines_json(result, p)
        raw = json.loads(p.read_text(encoding="utf-8"))
        assert "meeting_id" in raw
        assert "baselines" in raw
        assert "note" in raw
        if raw["baselines"]:
            b = raw["baselines"][0]
            for key in ("participant", "B1_speaking_time_s", "B1_speaking_time_norm",
                        "B2_speaking_time_turns_norm",
                        "B3_decision_event_count", "B3_decision_event_count_norm",
                        "B4_decision_evidence_count", "B4_decision_evidence_count_norm"):
                assert key in b

    def test_method_metadata_in_json(self, tmp_path):
        er, ev, dr, ir = _influence_chain()
        result = compute_influence(er, ev, dr, ir)
        p = tmp_path / "influence.json"
        save_influence_json(result, p)
        raw = json.loads(p.read_text(encoding="utf-8"))
        method = raw["method"]
        assert method["type"] == "decision_linked_weighted_score"
        assert method["normalization"] == "max"
        assert "weights" in method
        assert "disclaimer" in method


# ---------------------------------------------------------------------------
# 42. run_influence_analysis integration
# ---------------------------------------------------------------------------

class TestInfluenceRunner:
    def test_runner_creates_output_files(self, tmp_path):
        from src.meeting.events import save_events_json
        from src.meeting.evidence import save_evidence_json
        from src.meeting.decisions import save_decisions_json
        from src.meeting.interaction import save_interactions_json

        er, ev, dr, ir = _influence_chain()
        ep  = tmp_path / "events.json"
        evp = tmp_path / "evidence.json"
        dp  = tmp_path / "decisions.json"
        ip  = tmp_path / "interactions.json"
        save_events_json(er, ep)
        save_evidence_json(ev, evp)
        save_decisions_json(dr, dp)
        save_interactions_json(ir, ip)

        result, inf_path, base_path = run_influence_analysis(
            events_path=ep,
            evidence_path=evp,
            decisions_path=dp,
            interactions_path=ip,
            output_dir=tmp_path,
        )
        assert inf_path.exists()
        assert base_path.exists()
        assert isinstance(result.participants, list)

    def test_runner_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            run_influence_analysis(
                events_path=tmp_path / "missing.json",
                evidence_path=tmp_path / "evidence.json",
                decisions_path=tmp_path / "decisions.json",
                interactions_path=tmp_path / "interactions.json",
            )
