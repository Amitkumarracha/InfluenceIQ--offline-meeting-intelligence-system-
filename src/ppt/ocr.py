"""
OCR module for PPT slide processing.

Phase 6 status: INTERFACE ONLY — full OCR pipeline is reserved for a later phase.

Design rationale
----------------
python-pptx can extract all *native* text from PPTX shapes directly (text
frames, table cells, placeholder text).  OCR is only needed when slides
contain images that embed text (e.g. screenshots, scanned charts).

This module defines the interface and a stub implementation so that:
1. The rest of the pipeline can import and call OCR functions without
   breaking when OCR is disabled.
2. A future phase can drop in a real engine (pytesseract, EasyOCR, etc.)
   by replacing `_ocr_image_bytes` without changing any call sites.

Source tagging
--------------
Text produced by this module is *always* tagged with source="ocr" so it
is never confused with native PPT text (source="native").
"""

from __future__ import annotations

from dataclasses import dataclass

from src.utils.logging import get_logger

logger = get_logger("ppt.ocr")

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class OCRResult:
    """Text extracted from a single image region."""
    source: str            # always "ocr"
    slide_id: str
    image_index: int       # 0-based index of the image within the slide
    text: str
    confidence: float | None   # engine confidence if available, else None


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def extract_ocr_text(
    slide_id: str,
    image_bytes_list: list[bytes],
) -> list[OCRResult]:
    """
    Attempt to extract text from a list of raw image bytes for a given slide.

    Parameters
    ----------
    slide_id : str
        Identifier of the slide the images belong to.
    image_bytes_list : list[bytes]
        Raw PNG/JPEG bytes for each image shape on the slide.

    Returns
    -------
    list[OCRResult]
        One OCRResult per image.  In Phase 6 the list is always empty
        because OCR is not yet implemented.

    Notes
    -----
    To enable OCR in a future phase, replace the body of `_ocr_image_bytes`
    with a real engine call.  The function signature must stay the same.
    """
    results: list[OCRResult] = []

    if not _ocr_available():
        # Silently return empty list — OCR is not enabled in this phase
        return results

    for idx, img_bytes in enumerate(image_bytes_list):
        text, confidence = _ocr_image_bytes(img_bytes)
        if text:
            results.append(
                OCRResult(
                    source="ocr",
                    slide_id=slide_id,
                    image_index=idx,
                    text=text,
                    confidence=confidence,
                )
            )

    return results


def is_ocr_enabled() -> bool:
    """Return True when a real OCR engine is wired up and enabled."""
    return _ocr_available()


# ---------------------------------------------------------------------------
# Private helpers (stubs for Phase 6)
# ---------------------------------------------------------------------------

def _ocr_available() -> bool:
    """
    Check whether an OCR engine is available.

    Phase 6: always returns False.
    Future phase: check for pytesseract / EasyOCR installation and
    the `ppt.ocr_enabled` config flag.
    """
    return False


def _ocr_image_bytes(img_bytes: bytes) -> tuple[str, float | None]:
    """
    Run OCR on raw image bytes and return (text, confidence).

    Phase 6: NOT IMPLEMENTED — reserved for a future enhancement.

    To implement, install an OCR engine and replace this function:

        import pytesseract
        from PIL import Image
        import io

        def _ocr_image_bytes(img_bytes: bytes) -> tuple[str, float | None]:
            image = Image.open(io.BytesIO(img_bytes))
            text = pytesseract.image_to_string(image)
            return text.strip(), None
    """
    raise NotImplementedError(
        "OCR engine not implemented in Phase 6. "
        "This function should not be called while _ocr_available() returns False."
    )
