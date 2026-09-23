"""Cross-modal fusion package (Phase 7: Audio–PPT alignment)."""

from src.fusion.temporal_alignment import (
    SlideTimingInfo,
    TemporalScore,
    compute_overlap_seconds,
    compute_temporal_scores,
    has_any_timing,
    temporal_score_for_slide,
    timings_from_presentation_dict,
)
from src.fusion.semantic_alignment import (
    SemanticScore,
    compute_semantic_scores,
    cosine_similarity_matrix,
    embed_text,
    load_embedding_model,
)
from src.fusion.multimodal_representation import (
    NO_SLIDE,
    AlignmentResult,
    MultimodalSegment,
    SlideCandidate,
    align_segment,
    combine_scores,
    label_confidence,
    run_alignment,
)

__all__ = [
    # temporal
    "SlideTimingInfo", "TemporalScore",
    "compute_overlap_seconds", "compute_temporal_scores",
    "has_any_timing", "temporal_score_for_slide",
    "timings_from_presentation_dict",
    # semantic
    "SemanticScore", "compute_semantic_scores",
    "cosine_similarity_matrix", "embed_text", "load_embedding_model",
    # multimodal
    "NO_SLIDE", "AlignmentResult", "MultimodalSegment", "SlideCandidate",
    "align_segment", "combine_scores", "label_confidence", "run_alignment",
]
