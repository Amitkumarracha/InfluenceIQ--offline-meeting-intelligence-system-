"""
Temporal alignment between transcript segments and slides.

A slide may carry explicit timing (start_time / end_time in seconds) that
records when it was displayed during the meeting.  When that information is
present, a temporal overlap score can be calculated.  When it is absent the
score is explicitly marked as unavailable — it is NEVER invented.

Design principles
-----------------
- AVAILABLE timing  → normalised overlap score in [0, 1]
- UNAVAILABLE timing → score is None; the caller must handle this
- Slide-transition boundaries are handled by splitting credit across the
  two slides when a transcript segment straddles a transition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SlideTimingInfo:
    """
    Optional timing for a single slide.

    Fields
    ------
    slide_id : str
    start_time : float | None   seconds from meeting start
    end_time   : float | None   seconds from meeting start
    """
    slide_id: str
    start_time: float | None = None
    end_time: float | None = None

    @property
    def has_timing(self) -> bool:
        return self.start_time is not None and self.end_time is not None


@dataclass
class TemporalScore:
    """
    Temporal overlap result for one (transcript segment, slide) pair.

    score is None when timing is unavailable.
    """
    slide_id: str
    score: float | None          # normalised overlap in [0,1], or None
    timing_available: bool


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------

def compute_overlap_seconds(
    seg_start: float,
    seg_end: float,
    slide_start: float,
    slide_end: float,
) -> float:
    """Return the overlap in seconds between two intervals (≥ 0)."""
    return max(0.0, min(seg_end, slide_end) - max(seg_start, slide_start))


def temporal_score_for_slide(
    seg_start: float,
    seg_end: float,
    timing: SlideTimingInfo,
) -> TemporalScore:
    """
    Compute the normalised temporal overlap score for a single slide.

    The score is the fraction of the transcript segment's duration that
    falls within the slide's active interval:

        overlap_seconds / segment_duration

    This produces a value in [0, 1] where 1.0 means the segment is
    entirely contained within the slide's window.

    Parameters
    ----------
    seg_start, seg_end : float
        Transcript segment boundaries in seconds.
    timing : SlideTimingInfo
        Slide timing (may have start_time / end_time as None).

    Returns
    -------
    TemporalScore with score=None when timing is unavailable.
    """
    if not timing.has_timing:
        return TemporalScore(
            slide_id=timing.slide_id,
            score=None,
            timing_available=False,
        )

    seg_duration = max(seg_end - seg_start, 1e-9)
    overlap = compute_overlap_seconds(
        seg_start, seg_end,
        timing.start_time,   # type: ignore[arg-type]
        timing.end_time,     # type: ignore[arg-type]
    )
    score = min(1.0, overlap / seg_duration)

    return TemporalScore(
        slide_id=timing.slide_id,
        score=round(score, 6),
        timing_available=True,
    )


def compute_temporal_scores(
    seg_start: float,
    seg_end: float,
    slide_timings: list[SlideTimingInfo],
) -> list[TemporalScore]:
    """
    Return temporal scores for every slide in *slide_timings*.

    If NO slide carries timing information (all have score=None), the list
    is still returned — the caller must check timing_available.
    """
    return [
        temporal_score_for_slide(seg_start, seg_end, t)
        for t in slide_timings
    ]


def has_any_timing(slide_timings: list[SlideTimingInfo]) -> bool:
    """Return True if at least one slide has usable timing."""
    return any(t.has_timing for t in slide_timings)


# ---------------------------------------------------------------------------
# Helpers for building SlideTimingInfo from different input formats
# ---------------------------------------------------------------------------

def timing_from_slide_dict(slide_dict: dict[str, Any]) -> SlideTimingInfo:
    """
    Build a SlideTimingInfo from a slide JSON dict.

    Expected optional keys: "start_time", "end_time" (seconds).
    If absent, timing is None.
    """
    return SlideTimingInfo(
        slide_id=slide_dict["slide_id"],
        start_time=slide_dict.get("start_time"),
        end_time=slide_dict.get("end_time"),
    )


def timings_from_presentation_dict(pres_dict: dict[str, Any]) -> list[SlideTimingInfo]:
    """Build SlideTimingInfo list from a full presentation JSON dict."""
    return [timing_from_slide_dict(s) for s in pres_dict.get("slides", [])]
