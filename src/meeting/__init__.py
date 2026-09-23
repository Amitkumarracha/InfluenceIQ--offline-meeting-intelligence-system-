"""Meeting analysis package (Phases 8–9: event, evidence, and decision extraction)."""

from src.meeting.events import (
    ALL_EVENT_TYPES,
    BaseEventExtractor,
    EventExtractionResult,
    KeywordEventExtractor,
    MeetingEvent,
    get_active_event_types,
    load_events_json,
    load_multimodal_segments,
    run_event_extraction,
    save_events_json,
)
from src.meeting.evidence import (
    RELATIONSHIP_TYPES,
    EvidenceExtractionResult,
    EvidenceRelation,
    extract_evidence,
    load_evidence_json,
    run_evidence_extraction,
    save_evidence_json,
)
from src.meeting.decisions import (
    DECISION_STATUSES,
    Decision,
    DecisionResult,
    EventImpact,
    LineageEdge,
    ParticipantRole,
    load_decisions_json,
    reconstruct_decisions,
    run_decision_reconstruction,
    save_decision_graph_json,
    save_decisions_json,
)

__all__ = [
    # events
    "ALL_EVENT_TYPES", "BaseEventExtractor", "EventExtractionResult",
    "KeywordEventExtractor", "MeetingEvent", "get_active_event_types",
    "load_events_json", "load_multimodal_segments", "run_event_extraction",
    "save_events_json",
    # evidence
    "RELATIONSHIP_TYPES", "EvidenceExtractionResult", "EvidenceRelation",
    "extract_evidence", "load_evidence_json", "run_evidence_extraction",
    "save_evidence_json",
    # decisions
    "DECISION_STATUSES", "Decision", "DecisionResult", "EventImpact",
    "LineageEdge", "ParticipantRole",
    "load_decisions_json", "reconstruct_decisions", "run_decision_reconstruction",
    "save_decision_graph_json", "save_decisions_json",
]
