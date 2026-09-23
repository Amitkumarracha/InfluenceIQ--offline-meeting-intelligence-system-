"""
Tests for Phase 13 — Report generation and export.

All tests use small synthetic structured data.
No ML model is run; tests exercise the report builder and exporter only.
Synthetic results must NOT be presented as real meeting performance.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from src.report.generator import (
    _NOT_AVAILABLE,
    _build_action_items,
    _build_decisions,
    _build_executive_summary,
    _build_influence,
    _build_influence_vs_speaking,
    _build_interactions,
    _build_overview,
    _build_participants,
    _build_slide_discussions,
    _build_traceability,
    _fmt_ts,
    generate_report,
    ActionItem,
    DecisionReport,
    InfluenceReport,
    MeetingOverview,
    MeetingReport,
    ParticipantSummary,
)
from src.report.exporter import (
    export_all,
    export_csv_action_items,
    export_csv_decisions,
    export_csv_influence,
    export_csv_participants,
    export_html,
    export_json,
    export_markdown,
)

# ---------------------------------------------------------------------------
# Minimal synthetic pipeline data dicts
# ---------------------------------------------------------------------------

_EVENTS_DATA = {
    "meeting_id": "test_meeting",
    "events": [
        {"event_id": "e1", "event_type": "proposal",   "speaker": "S1",
         "start": 0.0,   "end": 5.0,   "text": "We should use Option A.", "slide_id": "slide_01"},
        {"event_id": "e2", "event_type": "objection",  "speaker": "S2",
         "start": 10.0,  "end": 15.0,  "text": "I disagree.",             "slide_id": "slide_01"},
        {"event_id": "e3", "event_type": "evidence",   "speaker": "S2",
         "start": 20.0,  "end": 25.0,  "text": "Data shows B is better.", "slide_id": "slide_02"},
        {"event_id": "e4", "event_type": "revision",   "speaker": "S1",
         "start": 30.0,  "end": 35.0,  "text": "Let's use Option B.",     "slide_id": "slide_02"},
        {"event_id": "e5", "event_type": "agreement",  "speaker": "S2",
         "start": 40.0,  "end": 45.0,  "text": "I agree.",                "slide_id": None},
        {"event_id": "e6", "event_type": "decision",   "speaker": "S1",
         "start": 50.0,  "end": 55.0,  "text": "We will use Option B.",   "slide_id": "slide_02"},
        {"event_id": "e7", "event_type": "action_item","speaker": "S2",
         "start": 60.0,  "end": 65.0,  "text": "Please follow up.",       "slide_id": None},
    ],
}

_DECISIONS_DATA = {
    "meeting_id": "test_meeting",
    "decisions": [
        {
            "decision_id": "decision_001",
            "status": "confirmed",
            "topic": "Option B selection",
            "proposal": {"event_id": "e1", "speaker": "S1", "text": "We should use Option A."},
            "discussion": [
                {"event_id": "e2", "speaker": "S2", "event_type": "objection", "text": "I disagree."},
                {"event_id": "e3", "speaker": "S2", "event_type": "evidence", "text": "Data shows B is better."},
            ],
            "supporting_evidence": [],
            "revisions": [{"event_id": "e4", "text": "Let's use Option B."}],
            "agreements": [{"event_id": "e5", "speaker": "S2"}],
            "final_decision": {"event_id": "e6", "text": "We will use Option B."},
            "participants": ["S1", "S2"],
            "participant_roles": [
                {"speaker": "S1", "role": "proposer"},
                {"speaker": "S2", "role": "objector"},
            ],
            "supporting_slides": ["slide_01", "slide_02"],
            "supporting_segments": [1, 2, 3, 4, 5, 6],
            "lineage": [
                {"source": "e1", "relationship": "leads_to", "target": "e4"},
            ],
            "event_impacts": [],
            "confidence": None,
        }
    ],
}

_INTERACTIONS_DATA = {
    "meeting_id": "test_meeting",
    "participants": ["S1", "S2"],
    "interactions": [
        {"interaction_id": "i1", "source_speaker": "S2", "target_speaker": "S1",
         "interaction_type": "challenge", "timestamp": 10.0,
         "source_event_id": "e2", "target_event_id": "e1",
         "related_decision_id": "decision_001", "related_slide_id": "slide_01",
         "text": "I disagree.", "confidence": None},
    ],
    "participant_stats": [
        {"participant": "S1", "interactions_initiated": 0, "interactions_received": 1,
         "supports": 0, "objections": 0, "responses": 0,
         "agreements": 0, "disagreements": 0, "clarifications": 0,
         "corrections": 0, "challenges": 0, "references": 0},
        {"participant": "S2", "interactions_initiated": 1, "interactions_received": 0,
         "supports": 0, "objections": 0, "responses": 0,
         "agreements": 0, "disagreements": 0, "clarifications": 0,
         "corrections": 0, "challenges": 1, "references": 0},
    ],
}

_INFLUENCE_DATA = {
    "meeting_id": "test_meeting",
    "method": {"type": "decision_linked_weighted_score", "normalization": "max",
               "weights": {}, "disclaimer": "Analytical estimate only."},
    "participants": [
        {
            "participant": "S2", "influence_score": 0.72, "rank": 1,
            "features": {"proposal_contribution": 0.0, "evidence_contribution": 0.9,
                         "objection_contribution": 0.8, "revision_contribution": 0.0,
                         "decision_contribution": 0.5, "interaction_contribution": 0.4,
                         "slide_grounded_contribution": 0.7},
            "raw_features": {"proposal_contribution": 0, "evidence_contribution": 2.0,
                              "objection_contribution": 1.5, "revision_contribution": 0,
                              "decision_contribution": 1, "interaction_contribution": 1,
                              "slide_grounded_contribution": 2},
            "decision_contributions": [
                {"decision_id": "decision_001", "contribution_score": 0.45,
                 "roles": ["objector", "evidence_provider"], "supporting_events": ["e2", "e3"]}
            ],
            "supporting_decisions": ["decision_001"],
            "supporting_events": ["e2", "e3"],
            "explanation": ["Provided evidence linked to Decision 1.",
                            "Raised objection followed by revision."],
        },
        {
            "participant": "S1", "influence_score": 0.58, "rank": 2,
            "features": {"proposal_contribution": 0.8, "evidence_contribution": 0.0,
                         "objection_contribution": 0.0, "revision_contribution": 0.9,
                         "decision_contribution": 0.8, "interaction_contribution": 0.1,
                         "slide_grounded_contribution": 0.6},
            "raw_features": {"proposal_contribution": 2.0, "evidence_contribution": 0,
                              "objection_contribution": 0, "revision_contribution": 1,
                              "decision_contribution": 2, "interaction_contribution": 0,
                              "slide_grounded_contribution": 2},
            "decision_contributions": [
                {"decision_id": "decision_001", "contribution_score": 0.60,
                 "roles": ["proposer", "reviser", "final_decision_maker"],
                 "supporting_events": ["e1", "e4", "e6"]}
            ],
            "supporting_decisions": ["decision_001"],
            "supporting_events": ["e1", "e4", "e6"],
            "explanation": ["Introduced proposal linked to Decision 1.",
                            "Performed revision and made final decision."],
        },
    ],
}


def _make_minimal_report() -> MeetingReport:
    """Build a MeetingReport from synthetic data dicts."""
    overview = _build_overview(
        "test_meeting", _EVENTS_DATA, _DECISIONS_DATA, _INTERACTIONS_DATA, None
    )
    participants = _build_participants(
        _EVENTS_DATA, _INTERACTIONS_DATA, _INFLUENCE_DATA, _DECISIONS_DATA
    )
    summary   = _build_executive_summary(_EVENTS_DATA, _DECISIONS_DATA)
    slide_dis = _build_slide_discussions(_EVENTS_DATA, None)
    proposals = _build_overview("test_meeting", _EVENTS_DATA, _DECISIONS_DATA, None, None)
    decisions = _build_decisions(_DECISIONS_DATA)
    actions   = _build_action_items(_EVENTS_DATA, _DECISIONS_DATA)
    intrs     = _build_interactions(_INTERACTIONS_DATA)
    influence = _build_influence(_INFLUENCE_DATA)
    inf_vs_sp = _build_influence_vs_speaking(participants)
    trace     = _build_traceability(_DECISIONS_DATA, _INFLUENCE_DATA, _EVENTS_DATA)

    return MeetingReport(
        meeting_id="test_meeting",
        meeting_overview=overview,
        participants=participants,
        executive_summary=summary,
        topics=[{"topic": "Option B", "decision_id": "decision_001",
                 "participants": ["S1", "S2"], "supporting_slides": ["slide_01"], "status": "confirmed"}],
        slide_discussions=slide_dis,
        proposals=[],
        evidence_items=[],
        decisions=decisions,
        action_items=actions,
        interactions=intrs,
        influence=influence,
        influence_vs_speaking=inf_vs_sp,
        evaluation={"status": _NOT_AVAILABLE},
        ablation={"status": "Ablation results are not yet available."},
        traceability=trace,
    )


# ===========================================================================
# 1. Timestamp formatter
# ===========================================================================

class TestTimestampFormatter:
    def test_zero(self):
        assert _fmt_ts(0.0) == "00:00:00"

    def test_one_hour(self):
        assert _fmt_ts(3600.0) == "01:00:00"

    def test_none(self):
        assert _fmt_ts(None) == "N/A"

    def test_hms(self):
        assert _fmt_ts(3723.0) == "01:02:03"


# ===========================================================================
# 2. Overview building
# ===========================================================================

class TestOverviewBuilding:
    def test_meeting_id(self):
        o = _build_overview("m1", _EVENTS_DATA, _DECISIONS_DATA, None, None)
        assert o.meeting_id == "m1"

    def test_num_participants(self):
        o = _build_overview("m", _EVENTS_DATA, _DECISIONS_DATA, None, None)
        assert o.num_participants == 2   # S1, S2

    def test_num_decisions(self):
        o = _build_overview("m", _EVENTS_DATA, _DECISIONS_DATA, None, None)
        assert o.num_decisions == 1

    def test_num_action_items(self):
        o = _build_overview("m", _EVENTS_DATA, _DECISIONS_DATA, None, None)
        assert o.num_action_items == 1

    def test_duration_positive(self):
        o = _build_overview("m", _EVENTS_DATA, _DECISIONS_DATA, None, None)
        assert o.duration_s > 0

    def test_missing_events_graceful(self):
        o = _build_overview("m", None, None, None, None)
        assert o.num_events == 0
        assert o.num_decisions == 0


# ===========================================================================
# 3. Participant building
# ===========================================================================

class TestParticipantBuilding:
    def test_all_speakers_present(self):
        ps = _build_participants(_EVENTS_DATA, _INTERACTIONS_DATA, _INFLUENCE_DATA, _DECISIONS_DATA)
        speakers = {p.speaker_id for p in ps}
        assert {"S1", "S2"} == speakers

    def test_influence_scores_attached(self):
        ps = _build_participants(_EVENTS_DATA, _INTERACTIONS_DATA, _INFLUENCE_DATA, _DECISIONS_DATA)
        with_score = [p for p in ps if p.influence_score is not None]
        assert len(with_score) == 2

    def test_speaking_duration_positive(self):
        ps = _build_participants(_EVENTS_DATA, None, None, _DECISIONS_DATA)
        for p in ps:
            assert (p.speaking_duration_s or 0) >= 0

    def test_roles_populated(self):
        ps = _build_participants(_EVENTS_DATA, _INTERACTIONS_DATA, _INFLUENCE_DATA, _DECISIONS_DATA)
        all_roles = [role for p in ps for role in p.roles]
        assert len(all_roles) > 0


# ===========================================================================
# 4. Executive summary
# ===========================================================================

class TestExecutiveSummary:
    def test_no_fabricated_content(self):
        s = _build_executive_summary(_EVENTS_DATA, _DECISIONS_DATA)
        assert s["method"] == "structured_extraction"
        assert "note" in s

    def test_num_proposals_correct(self):
        s = _build_executive_summary(_EVENTS_DATA, _DECISIONS_DATA)
        assert s["num_proposals"] >= 1

    def test_confirmed_decisions_listed(self):
        s = _build_executive_summary(_EVENTS_DATA, _DECISIONS_DATA)
        assert s["num_confirmed_decisions"] >= 1

    def test_missing_data_graceful(self):
        s = _build_executive_summary(None, None)
        assert s["num_proposals"] == 0


# ===========================================================================
# 5. Decision rendering
# ===========================================================================

class TestDecisionRendering:
    def test_decision_count(self):
        decisions = _build_decisions(_DECISIONS_DATA)
        assert len(decisions) == 1

    def test_decision_fields(self):
        d = _build_decisions(_DECISIONS_DATA)[0]
        assert d.decision_id == "decision_001"
        assert d.status == "confirmed"
        assert d.proposal_text is not None
        assert d.final_decision_text is not None

    def test_lineage_text_not_empty(self):
        d = _build_decisions(_DECISIONS_DATA)[0]
        assert len(d.lineage_text) > 0
        assert "→" in d.lineage_text

    def test_unresolved_decision_says_unresolved(self):
        data = {"decisions": [{"decision_id": "d1", "status": "unresolved",
                                "topic": None, "proposal": None, "discussion": [],
                                "supporting_evidence": [], "revisions": [], "agreements": [],
                                "final_decision": None, "participants": [],
                                "participant_roles": [], "supporting_slides": [],
                                "supporting_segments": [], "lineage": [],
                                "event_impacts": [], "confidence": None}]}
        d = _build_decisions(data)[0]
        assert "Unresolved" in d.lineage_text

    def test_missing_decisions_graceful(self):
        decisions = _build_decisions(None)
        assert decisions == []


# ===========================================================================
# 6. Action items
# ===========================================================================

class TestActionItems:
    def test_action_item_count(self):
        items = _build_action_items(_EVENTS_DATA, _DECISIONS_DATA)
        assert len(items) == 1

    def test_action_item_speaker(self):
        items = _build_action_items(_EVENTS_DATA, _DECISIONS_DATA)
        assert items[0].speaker == "S2"

    def test_action_item_timestamp(self):
        items = _build_action_items(_EVENTS_DATA, _DECISIONS_DATA)
        assert items[0].timestamp == 60.0

    def test_unassigned_when_no_speaker(self):
        data = {"events": [{"event_id": "e1", "event_type": "action_item",
                             "start": 0.0, "end": 5.0, "text": "Do something."}]}
        items = _build_action_items(data, None)
        assert items[0].speaker is None  # exporter handles "Unassigned"


# ===========================================================================
# 7. Influence rendering
# ===========================================================================

class TestInfluenceRendering:
    def test_influence_list_populated(self):
        inf = _build_influence(_INFLUENCE_DATA)
        assert len(inf) == 2

    def test_ranked_correctly(self):
        inf = _build_influence(_INFLUENCE_DATA)
        assert inf[0].rank == 1
        assert inf[0].speaker_id == "S2"

    def test_explanations_non_empty(self):
        inf = _build_influence(_INFLUENCE_DATA)
        for i in inf:
            assert len(i.explanation) > 0

    def test_missing_influence_returns_empty(self):
        assert _build_influence(None) == []

    def test_no_fabricated_scores(self):
        inf = _build_influence(_INFLUENCE_DATA)
        for i in inf:
            assert i.score == pytest.approx(
                _INFLUENCE_DATA["participants"][
                    0 if i.speaker_id == "S2" else 1
                ]["influence_score"]
            )


# ===========================================================================
# 8. Influence vs speaking time
# ===========================================================================

class TestInfluenceVsSpeaking:
    def test_produces_rows_per_participant(self):
        ps = _build_participants(_EVENTS_DATA, _INTERACTIONS_DATA, _INFLUENCE_DATA, _DECISIONS_DATA)
        rows = _build_influence_vs_speaking(ps)
        assert len(rows) == 2

    def test_both_ranks_present(self):
        ps = _build_participants(_EVENTS_DATA, _INTERACTIONS_DATA, _INFLUENCE_DATA, _DECISIONS_DATA)
        rows = _build_influence_vs_speaking(ps)
        for r in rows:
            assert "speaking_rank" in r
            assert "influence_rank" in r


# ===========================================================================
# 9. Traceability
# ===========================================================================

class TestTraceability:
    def test_chains_produced(self):
        t = _build_traceability(_DECISIONS_DATA, _INFLUENCE_DATA, _EVENTS_DATA)
        assert "chains" in t
        assert len(t["chains"]) > 0

    def test_chain_fields(self):
        t = _build_traceability(_DECISIONS_DATA, _INFLUENCE_DATA, _EVENTS_DATA)
        for c in t["chains"]:
            for key in ("participant", "event_id", "speaker", "timestamp", "decision_id"):
                assert key in c

    def test_event_ids_real(self):
        t = _build_traceability(_DECISIONS_DATA, _INFLUENCE_DATA, _EVENTS_DATA)
        known_ids = {e["event_id"] for e in _EVENTS_DATA["events"]}
        for c in t["chains"]:
            assert c["event_id"] in known_ids


# ===========================================================================
# 10. Missing input handling
# ===========================================================================

class TestMissingInputHandling:
    def test_missing_influence_json(self, tmp_path):
        # generate_report should not crash if influence.json doesn't exist
        report = generate_report("nonexistent_meeting", tmp_path)
        assert report.meeting_id == "nonexistent_meeting"
        assert report.meeting_overview.num_events == 0

    def test_missing_influence_section_marked(self, tmp_path):
        report = generate_report("nonexistent", tmp_path)
        # Influence should be empty list (not crash)
        assert isinstance(report.influence, list)

    def test_missing_evaluation_marked_unavailable(self, tmp_path):
        report = generate_report("nonexistent", tmp_path)
        assert report.evaluation.get("status") == _NOT_AVAILABLE

    def test_interactions_status_when_missing(self, tmp_path):
        report = generate_report("nonexistent", tmp_path)
        assert report.interactions.get("status") == _NOT_AVAILABLE


# ===========================================================================
# 11. JSON export
# ===========================================================================

class TestJSONExport:
    def test_json_created(self, tmp_path):
        r = _make_minimal_report()
        p = tmp_path / "report.json"
        export_json(r, p)
        assert p.exists()

    def test_json_structure(self, tmp_path):
        r = _make_minimal_report()
        p = tmp_path / "report.json"
        export_json(r, p)
        data = json.loads(p.read_text(encoding="utf-8"))
        for key in ("meeting_overview", "participants", "decisions",
                    "action_items", "influence", "traceability"):
            assert key in data

    def test_json_serialisable(self, tmp_path):
        r = _make_minimal_report()
        p = tmp_path / "report.json"
        export_json(r, p)
        # Should not raise
        json.loads(p.read_text(encoding="utf-8"))

    def test_json_meeting_id(self, tmp_path):
        r = _make_minimal_report()
        p = tmp_path / "report.json"
        export_json(r, p)
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["meeting_overview"]["meeting_id"] == "test_meeting"


# ===========================================================================
# 12. Markdown export
# ===========================================================================

class TestMarkdownExport:
    def test_markdown_created(self, tmp_path):
        r = _make_minimal_report()
        p = tmp_path / "report.md"
        export_markdown(r, p)
        assert p.exists()

    def test_markdown_has_headings(self, tmp_path):
        r = _make_minimal_report()
        p = tmp_path / "report.md"
        export_markdown(r, p)
        content = p.read_text(encoding="utf-8")
        assert "# Meeting Intelligence Report" in content
        assert "## 1. Meeting Overview" in content
        assert "## 7. Decisions" in content

    def test_markdown_no_fabricated_scores(self, tmp_path):
        r = _make_minimal_report()
        p = tmp_path / "report.md"
        export_markdown(r, p)
        content = p.read_text(encoding="utf-8")
        # Should not claim ground truth is available when it isn't
        assert "Not evaluated" in content or _NOT_AVAILABLE in content

    def test_markdown_influence_disclaimer(self, tmp_path):
        r = _make_minimal_report()
        p = tmp_path / "report.md"
        export_markdown(r, p)
        content = p.read_text(encoding="utf-8")
        assert "analytical" in content.lower() or "causal" in content.lower()

    def test_markdown_speaking_vs_influence(self, tmp_path):
        r = _make_minimal_report()
        p = tmp_path / "report.md"
        export_markdown(r, p)
        content = p.read_text(encoding="utf-8")
        assert "Influence vs Speaking" in content


# ===========================================================================
# 13. HTML export
# ===========================================================================

class TestHTMLExport:
    def test_html_created(self, tmp_path):
        r = _make_minimal_report()
        p = tmp_path / "report.html"
        export_html(r, p)
        assert p.exists()

    def test_html_valid_structure(self, tmp_path):
        r = _make_minimal_report()
        p = tmp_path / "report.html"
        export_html(r, p)
        content = p.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "<table>" in content
        assert "</html>" in content

    def test_html_no_external_deps(self, tmp_path):
        r = _make_minimal_report()
        p = tmp_path / "report.html"
        export_html(r, p)
        content = p.read_text(encoding="utf-8")
        assert "cdn." not in content
        assert "googleapis" not in content
        assert "cloudflare" not in content

    def test_html_contains_meeting_id(self, tmp_path):
        r = _make_minimal_report()
        p = tmp_path / "report.html"
        export_html(r, p)
        assert "test_meeting" in p.read_text(encoding="utf-8")


# ===========================================================================
# 14. CSV exports
# ===========================================================================

class TestCSVExport:
    def test_participants_csv(self, tmp_path):
        r = _make_minimal_report()
        p = tmp_path / "participants.csv"
        export_csv_participants(r, p)
        assert p.exists()
        with open(p, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2
        assert "speaker_id" in rows[0]

    def test_decisions_csv(self, tmp_path):
        r = _make_minimal_report()
        p = tmp_path / "decisions.csv"
        export_csv_decisions(r, p)
        assert p.exists()
        with open(p, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["decision_id"] == "decision_001"

    def test_influence_csv(self, tmp_path):
        r = _make_minimal_report()
        p = tmp_path / "influence.csv"
        export_csv_influence(r, p)
        assert p.exists()
        with open(p, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2
        for row in rows:
            assert "rank" in row
            assert "influence_score" in row

    def test_action_items_csv(self, tmp_path):
        r = _make_minimal_report()
        p = tmp_path / "actions.csv"
        export_csv_action_items(r, p)
        assert p.exists()
        with open(p, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["speaker"] == "S2"


# ===========================================================================
# 15. Export all
# ===========================================================================

class TestExportAll:
    def test_all_formats_created(self, tmp_path):
        r = _make_minimal_report()
        paths = export_all(r, tmp_path, formats=["json", "markdown", "html", "csv"])
        assert (tmp_path / "test_meeting_report.json").exists()
        assert (tmp_path / "test_meeting_report.md").exists()
        assert (tmp_path / "test_meeting_report.html").exists()
        assert (tmp_path / "test_meeting_participants.csv").exists()
        assert (tmp_path / "test_meeting_decisions.csv").exists()
        assert (tmp_path / "test_meeting_influence.csv").exists()
        assert (tmp_path / "test_meeting_action_items.csv").exists()

    def test_selective_format(self, tmp_path):
        r = _make_minimal_report()
        paths = export_all(r, tmp_path, formats=["json"])
        assert "json" in paths
        assert "markdown" not in paths

    def test_returns_path_dict(self, tmp_path):
        r = _make_minimal_report()
        paths = export_all(r, tmp_path, formats=["json"])
        assert isinstance(paths, dict)
        assert all(isinstance(v, Path) for v in paths.values())


# ===========================================================================
# 16. Slide-linked discussion
# ===========================================================================

class TestSlideDiscussions:
    def test_slides_grouped(self):
        discs = _build_slide_discussions(_EVENTS_DATA, None)
        slide_ids = {d["slide_id"] for d in discs}
        assert "slide_01" in slide_ids
        assert "slide_02" in slide_ids

    def test_no_slide_events_excluded(self):
        # e5 has no slide_id — should not appear
        discs = _build_slide_discussions(_EVENTS_DATA, None)
        for d in discs:
            for seg in d["segments"]:
                assert seg["event_id"] != "e5"

    def test_missing_events_graceful(self):
        discs = _build_slide_discussions(None, None)
        assert discs == []


# ===========================================================================
# 17. Interactions section
# ===========================================================================

class TestInteractionsSection:
    def test_interaction_count(self):
        intr = _build_interactions(_INTERACTIONS_DATA)
        assert intr["total_interactions"] == 1

    def test_interaction_type_counts(self):
        intr = _build_interactions(_INTERACTIONS_DATA)
        assert "challenge" in intr["interactions_by_type"]

    def test_note_about_influence(self):
        intr = _build_interactions(_INTERACTIONS_DATA)
        assert "NOT influence" in intr.get("note", "")

    def test_missing_interactions_returns_unavailable(self):
        intr = _build_interactions(None)
        assert "status" in intr
