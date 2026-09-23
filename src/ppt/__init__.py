"""PPT/slide processing package."""

from src.ppt.extract import (
    BaseSlideExtractor,
    PPTXExtractor,
    PresentationData,
    SlideData,
    TableData,
    derive_meeting_id,
)
from src.ppt.features import (
    SlideFeatures,
    extract_presentation_features,
    extract_slide_features,
    presentation_feature_summary,
)

__all__ = [
    "BaseSlideExtractor",
    "PPTXExtractor",
    "PresentationData",
    "SlideData",
    "TableData",
    "derive_meeting_id",
    "SlideFeatures",
    "extract_presentation_features",
    "extract_slide_features",
    "presentation_feature_summary",
]
