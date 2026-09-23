"""
Multimodal representation: unified view of a transcript segment + slide alignment.

This is the primary data structure consumed by downstream meeting-event
analysis (Phase 8+).  It combines:

  - transcript segment metadata (speaker, timing, text)
  - slide alignment result (selected slide + scores)

Serialisation helpers are included so outputs can be written to JSON
without depending on dataclasses.asdict (which doesn't handle None cleanly
in all Python versions).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from src.audio.asr import TranscriptSegment, TranscriptResult
from src.fusion.temporal_alignment import (
    SlideTimingInfo,
    TemporalScore,
    compute_temporal_scores,
    has_any_timing,
    timings_from_presentation_dict,
)
from src.fusion.semantic_alignment import (
    SemanticScore,
    compute_semantic_scores,
    load_embedding_model,
)
from src.ppt.io import load_presentation_json
from src.ppt.embeddings import load_embeddings
from src.utils.config import get
from src.utils.logging import get_logger

logger = get_logger("fusion.alignment")

NO_SLIDE = "NO_CONFIDENT_SLIDE"


# ---------------------------------------------------------------------------
# Output data structures
# ---------------------------------------------------------------------------

@dataclass
class SlideCandidate:
    """A single slide considered for a transcript segment."""
    slide_id: str
    temporal_score: float | None    # None when timing unavailable
    semantic_score: float
    combined_score: float
    confidence: str                 # "high" | "medium" | "low"


@dataclass
class AlignmentResult:
    """Full alignment result for one transcript segment."""
    segment_id: int
    speaker: str
    start: float
    end: float
    text: str
    slide_candidates: list[SlideCandidate]
    selected_slide: str             # slide_id or NO_SLIDE


@dataclass
class MultimodalSegment:
    """
    Unified multimodal representation of one aligned segment.

    This is the primary input to Phase 8+ (event extraction, etc.).
    """
    segment_id: int
    speaker: str
    start: float
    end: float
    text: str
    slide_id: str                   # may be NO_SLIDE
    temporal_score: float | None
    semantic_score: float | None
    combined_score: float | None


# ---------------------------------------------------------------------------
# Confidence labelling
# ---------------------------------------------------------------------------

def label_confidence(score: float, threshold: float) -> str:
    """Convert a combined score to a human-readable confidence label."""
    if score >= threshold + 0.15:
        return "high"
    if score >= threshold:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Combined scoring
# ---------------------------------------------------------------------------

def combine_scores(
    temporal_score: float | None,
    semantic_score: float,
    temporal_weight: float,
    semantic_weight: float,
) -> float:
    """
    Weighted combination of temporal and semantic scores.

    When temporal_score is None (timing unavailable), the full weight is
    given to the semantic score (renormalised to 1.0).

    NOTE: These weights are initial prototype defaults.  They have NOT been
    validated experimentally and MUST be evaluated against ground-truth
    alignment data before use in production.
    """
    if temporal_score is None:
        # No temporal evidence: use semantic score only (renormalised)
        total_weight = semantic_weight if semantic_weight > 0 else 1.0
        return round(semantic_score * (semantic_weight / total_weight), 6)

    total_weight = temporal_weight + semantic_weight
    if total_weight == 0:
        return 0.0

    combined = (
        temporal_weight * temporal_score
        + semantic_weight * semantic_score
    ) / total_weight
    return round(combined, 6)


# ---------------------------------------------------------------------------
# Per-segment alignment
# ---------------------------------------------------------------------------

def align_segment(
    segment: TranscriptSegment,
    slide_ids: list[str],
    slide_timings: list[SlideTimingInfo],
    slide_embeddings: np.ndarray,
    embedding_model: object,
    top_k: int,
    temporal_weight: float,
    semantic_weight: float,
    threshold: float,
) -> AlignmentResult:
    """
    Align one transcript segment to the best matching slide(s).

    Steps
    -----
    1. Compute temporal scores for every slide (None when timing missing).
    2. If timing is available, pre-filter to slides with any overlap plus
       a safety margin; otherwise keep all slides as candidates.
    3. Compute semantic scores for candidate slides.
    4. Compute combined score and rank; keep top-k.
    5. Apply threshold; if best score < threshold → NO_CONFIDENT_SLIDE.
    """
    timing_available = has_any_timing(slide_timings)

    # Step 1: temporal scores
    temporal_scores: dict[str, float | None] = {}
    if timing_available:
        t_results = compute_temporal_scores(segment.start, segment.end, slide_timings)
        temporal_scores = {r.slide_id: r.score for r in t_results}
    else:
        temporal_scores = {sid: None for sid in slide_ids}

    # Step 2: candidate filtering
    if timing_available:
        # Keep slides with any temporal overlap; always retain a minimum
        # set so we don't lose a semantically strong but slightly misaligned slide.
        overlapping = [
            sid for sid, s in temporal_scores.items() if s is not None and s > 0
        ]
        if not overlapping:
            # No temporal overlap at all — fall back to all slides for semantic pass
            candidate_ids = slide_ids[:]
        else:
            candidate_ids = overlapping
    else:
        candidate_ids = slide_ids[:]

    # Indices into the full slide list for the candidates
    slide_id_to_idx = {sid: i for i, sid in enumerate(slide_ids)}
    candidate_indices = [slide_id_to_idx[sid] for sid in candidate_ids]
    candidate_embeddings = slide_embeddings[candidate_indices]

    # Step 3: semantic scores
    sem_results = compute_semantic_scores(
        segment.text,
        candidate_ids,
        candidate_embeddings,
        embedding_model,
    )
    semantic_scores: dict[str, float] = {r.slide_id: r.score for r in sem_results}

    # Step 4: combined scores for all candidates
    candidates: list[SlideCandidate] = []
    for sid in candidate_ids:
        t_score = temporal_scores.get(sid)
        s_score = semantic_scores.get(sid, 0.0)
        c_score = combine_scores(t_score, s_score, temporal_weight, semantic_weight)
        candidates.append(SlideCandidate(
            slide_id=sid,
            temporal_score=t_score,
            semantic_score=s_score,
            combined_score=c_score,
            confidence=label_confidence(c_score, threshold),
        ))

    # Sort descending by combined score, keep top-k
    candidates.sort(key=lambda c: c.combined_score, reverse=True)
    top_candidates = candidates[:top_k]

    # Step 5: threshold decision
    if top_candidates and top_candidates[0].combined_score >= threshold:
        selected = top_candidates[0].slide_id
    else:
        selected = NO_SLIDE

    return AlignmentResult(
        segment_id=segment.segment_id,
        speaker=segment.speaker,
        start=segment.start,
        end=segment.end,
        text=segment.text,
        slide_candidates=top_candidates,
        selected_slide=selected,
    )


# ---------------------------------------------------------------------------
# Full alignment run
# ---------------------------------------------------------------------------

def run_alignment(
    transcript_path: Path,
    slides_path: Path,
    embeddings_path: Path | None = None,
    meeting_id: str | None = None,
    output_dir: Path | None = None,
) -> tuple[list[AlignmentResult], list[MultimodalSegment], Path, Path]:
    """
    Align a full transcript to slides and produce multimodal representations.

    Parameters
    ----------
    transcript_path : Path
        Path to the ASR transcript JSON (Phase 5 output).
    slides_path : Path
        Path to the slide JSON (Phase 6 output).
    embeddings_path : Path | None
        Path to the slide embeddings .npy file.  If None, looked up from
        the same directory as slides_path.
    meeting_id : str | None
        Override meeting ID; derived from transcript file name if None.
    output_dir : Path | None
        Output directory; defaults to data/processed/alignment/.

    Returns
    -------
    (alignment_results, multimodal_segments, alignment_json_path, multimodal_json_path)
    """
    t0 = time.time()

    # ---- Validate inputs ----
    if not transcript_path.exists():
        raise FileNotFoundError(f"Transcript JSON not found: {transcript_path}")
    if not slides_path.exists():
        raise FileNotFoundError(f"Slides JSON not found: {slides_path}")

    # Resolve embeddings path
    if embeddings_path is None:
        embeddings_path = slides_path.parent / (
            slides_path.stem.replace("_slides", "") + "_embeddings.npy"
        )
    if not embeddings_path.exists():
        raise FileNotFoundError(
            f"Slide embeddings not found: {embeddings_path}\n"
            "Run Phase 6 (PPT processing) with embeddings enabled first."
        )

    # ---- Load data ----
    logger.info("Loading transcript: %s", transcript_path)
    import json as _json
    with open(transcript_path, encoding="utf-8") as f:
        transcript_dict = _json.load(f)

    from src.audio.asr import _deserialise_result
    transcript = _deserialise_result(transcript_dict)

    logger.info("Loading slides: %s", slides_path)
    pdata = load_presentation_json(slides_path)

    logger.info("Loading embeddings: %s", embeddings_path)
    slide_embeddings = load_embeddings(embeddings_path)

    meeting_id = meeting_id or transcript.meeting_id

    logger.info(
        "Aligning %d transcript segments against %d slides",
        len(transcript.segments), pdata.num_slides,
    )

    # ---- Timing info ----
    import json as _json2
    with open(slides_path, encoding="utf-8") as f:
        slides_dict = _json2.load(f)
    slide_timings = timings_from_presentation_dict(slides_dict)
    timing_available = has_any_timing(slide_timings)
    logger.info("Slide timing available: %s", timing_available)

    # ---- Config ----
    top_k: int = int(get("alignment.top_k", 3))
    temporal_weight: float = float(get("alignment.temporal_weight", 0.5))
    semantic_weight: float = float(get("alignment.semantic_weight", 0.5))
    threshold: float = float(get("alignment.threshold", 0.3))
    model_name: str = get("ppt.embeddings.model") or "all-MiniLM-L6-v2"

    logger.info(
        "Config: top_k=%d temporal_w=%.2f semantic_w=%.2f threshold=%.2f model=%s",
        top_k, temporal_weight, semantic_weight, threshold, model_name,
    )

    # ---- Load embedding model ----
    logger.info("Loading embedding model: %s", model_name)
    embedding_model = load_embedding_model(model_name)

    slide_ids = [s.slide_id for s in pdata.slides]

    # ---- Align each segment ----
    alignment_results: list[AlignmentResult] = []
    for seg in transcript.segments:
        result = align_segment(
            segment=seg,
            slide_ids=slide_ids,
            slide_timings=slide_timings,
            slide_embeddings=slide_embeddings,
            embedding_model=embedding_model,
            top_k=top_k,
            temporal_weight=temporal_weight,
            semantic_weight=semantic_weight,
            threshold=threshold,
        )
        alignment_results.append(result)

    # ---- Build multimodal segments ----
    multimodal_segments: list[MultimodalSegment] = []
    for ar in alignment_results:
        best = ar.slide_candidates[0] if ar.slide_candidates else None
        multimodal_segments.append(MultimodalSegment(
            segment_id=ar.segment_id,
            speaker=ar.speaker,
            start=ar.start,
            end=ar.end,
            text=ar.text,
            slide_id=ar.selected_slide,
            temporal_score=best.temporal_score if best else None,
            semantic_score=best.semantic_score if best else None,
            combined_score=best.combined_score if best else None,
        ))

    elapsed = time.time() - t0
    aligned_count = sum(1 for a in alignment_results if a.selected_slide != NO_SLIDE)
    no_slide_count = len(alignment_results) - aligned_count

    logger.info(
        "Alignment complete in %.2fs | aligned=%d | no_confident_slide=%d",
        elapsed, aligned_count, no_slide_count,
    )

    # ---- Save outputs ----
    out_dir = output_dir or Path("data/processed/alignment")
    out_dir.mkdir(parents=True, exist_ok=True)

    alignment_path = out_dir / f"{meeting_id}_alignment.json"
    multimodal_path = out_dir / f"{meeting_id}_multimodal.json"

    _save_alignment_json(alignment_results, meeting_id, alignment_path)
    _save_multimodal_json(multimodal_segments, meeting_id, multimodal_path)

    logger.info("Alignment JSON  : %s", alignment_path)
    logger.info("Multimodal JSON : %s", multimodal_path)

    return alignment_results, multimodal_segments, alignment_path, multimodal_path


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def _candidate_to_dict(c: SlideCandidate) -> dict[str, Any]:
    return {
        "slide_id": c.slide_id,
        "temporal_score": c.temporal_score,
        "semantic_score": c.semantic_score,
        "combined_score": c.combined_score,
        "confidence": c.confidence,
    }


def _alignment_to_dict(a: AlignmentResult) -> dict[str, Any]:
    return {
        "segment_id": a.segment_id,
        "speaker": a.speaker,
        "start": a.start,
        "end": a.end,
        "text": a.text,
        "slide_candidates": [_candidate_to_dict(c) for c in a.slide_candidates],
        "selected_slide": a.selected_slide,
    }


def _multimodal_to_dict(m: MultimodalSegment) -> dict[str, Any]:
    return {
        "segment_id": m.segment_id,
        "speaker": m.speaker,
        "start": m.start,
        "end": m.end,
        "text": m.text,
        "slide_id": m.slide_id,
        "alignment": {
            "temporal_score": m.temporal_score,
            "semantic_score": m.semantic_score,
            "combined_score": m.combined_score,
        },
    }


def _save_alignment_json(
    results: list[AlignmentResult],
    meeting_id: str,
    path: Path,
) -> None:
    payload = {
        "meeting_id": meeting_id,
        "num_segments": len(results),
        "segments": [_alignment_to_dict(a) for a in results],
    }
    with open(path, "w", encoding="utf-8") as f:
        import json as _json
        _json.dump(payload, f, indent=2, ensure_ascii=False)


def _save_multimodal_json(
    segments: list[MultimodalSegment],
    meeting_id: str,
    path: Path,
) -> None:
    payload = {
        "meeting_id": meeting_id,
        "num_segments": len(segments),
        "segments": [_multimodal_to_dict(m) for m in segments],
    }
    with open(path, "w", encoding="utf-8") as f:
        import json as _json
        _json.dump(payload, f, indent=2, ensure_ascii=False)
