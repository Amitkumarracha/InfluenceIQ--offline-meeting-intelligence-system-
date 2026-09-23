"""
Lightweight visual/structural metadata extraction for PPT slides.

This module operates on already-extracted SlideData objects (from extract.py)
and enriches their metadata with any additional content-level signals.

Currently implemented (no computer vision required):
- image_count, table_count, shape_count, text_box_count
- slide dimensions
- has_chart flag

Intentionally NOT implemented here:
- Object detection / visual classification
- Image captioning / visual-language models

Those are reserved for a future phase.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.ppt.extract import PresentationData, SlideData


@dataclass
class SlideFeatures:
    """
    Aggregated feature summary for a single slide.

    All fields are derived from python-pptx shape-level metadata;
    no image decoding is performed.
    """
    slide_id: str
    slide_number: int
    image_count: int
    table_count: int
    shape_count: int
    text_box_count: int
    has_chart: bool
    slide_width_cm: float
    slide_height_cm: float
    has_title: bool
    has_text: bool
    has_notes: bool
    text_length: int          # total character count across all text blocks


def extract_slide_features(slide: SlideData) -> SlideFeatures:
    """Return a SlideFeatures summary from a SlideData object."""
    meta: dict[str, Any] = slide.metadata

    all_text = " ".join(slide.text)
    if slide.title:
        all_text = slide.title + " " + all_text

    return SlideFeatures(
        slide_id=slide.slide_id,
        slide_number=slide.slide_number,
        image_count=meta.get("image_count", 0),
        table_count=meta.get("table_count", 0),
        shape_count=meta.get("shape_count", 0),
        text_box_count=meta.get("text_box_count", 0),
        has_chart=meta.get("has_chart", False),
        slide_width_cm=meta.get("slide_width_cm", 0.0),
        slide_height_cm=meta.get("slide_height_cm", 0.0),
        has_title=slide.title is not None,
        has_text=bool(slide.text),
        has_notes=slide.notes is not None,
        text_length=len(all_text.strip()),
    )


def extract_presentation_features(pdata: PresentationData) -> list[SlideFeatures]:
    """Return feature summaries for every slide in a presentation."""
    return [extract_slide_features(s) for s in pdata.slides]


def presentation_feature_summary(features: list[SlideFeatures]) -> dict[str, Any]:
    """Aggregate statistics across all slides (for logging / reporting)."""
    if not features:
        return {}
    return {
        "total_slides": len(features),
        "slides_with_title": sum(1 for f in features if f.has_title),
        "slides_with_text": sum(1 for f in features if f.has_text),
        "slides_with_notes": sum(1 for f in features if f.has_notes),
        "slides_with_tables": sum(1 for f in features if f.table_count > 0),
        "slides_with_images": sum(1 for f in features if f.image_count > 0),
        "slides_with_charts": sum(1 for f in features if f.has_chart),
        "total_tables": sum(f.table_count for f in features),
        "total_images": sum(f.image_count for f in features),
    }
