"""
Tests for Phase 6 — PPT/slide processing.

All tests use a small in-memory PPTX created with python-pptx so no
external file is required.  The tests cover:
  - invalid PPT path → FileNotFoundError
  - presentation loading and slide count
  - slide number extraction
  - text and title extraction
  - table extraction
  - speaker notes extraction
  - visual metadata extraction
  - meeting ID derivation
  - JSON serialisation round-trip
  - slide text builder (for embeddings)
"""

from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers – build a small in-memory PPTX
# ---------------------------------------------------------------------------

def _make_pptx(tmp_path: Path) -> Path:
    """
    Create a minimal PPTX with 3 slides:

    Slide 1 – title + body text
    Slide 2 – title + table + speaker notes
    Slide 3 – no title, just a text box
    """
    from pptx import Presentation
    from pptx.util import Inches, Pt

    prs = Presentation()
    blank_layout = prs.slide_layouts[6]          # completely blank
    title_layout = prs.slide_layouts[1]          # title + content

    # ---- Slide 1: title + body ----
    slide1 = prs.slides.add_slide(prs.slide_layouts[1])
    slide1.shapes.title.text = "Project Architecture"
    # The content placeholder is index 1 on layout 1
    body = slide1.placeholders[1]
    tf = body.text_frame
    tf.text = "Data Collection"
    tf.add_paragraph().text = "Pre-processing"
    tf.add_paragraph().text = "Model Training"

    # ---- Slide 2: title + table + notes ----
    slide2 = prs.slides.add_slide(prs.slide_layouts[5])  # title only
    slide2.shapes.title.text = "Results"

    # Add a 2×2 table
    rows, cols = 2, 2
    left, top, width, height = Inches(1), Inches(2), Inches(6), Inches(1.5)
    tbl_shape = slide2.shapes.add_table(rows, cols, left, top, width, height)
    tbl = tbl_shape.table
    tbl.cell(0, 0).text = "Metric"
    tbl.cell(0, 1).text = "Value"
    tbl.cell(1, 0).text = "Accuracy"
    tbl.cell(1, 1).text = "92%"

    # Add speaker notes
    notes_slide = slide2.notes_slide
    notes_slide.notes_text_frame.text = "Highlight the accuracy improvement."

    # ---- Slide 3: blank + free text box ----
    slide3 = prs.slides.add_slide(blank_layout)
    txBox = slide3.shapes.add_textbox(Inches(1), Inches(1), Inches(5), Inches(1))
    txBox.text_frame.text = "Standalone text box content"

    out = tmp_path / "test_presentation.pptx"
    prs.save(str(out))
    return out


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pptx_path(tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("ppt")
    return _make_pptx(tmp)


@pytest.fixture(scope="module")
def presentation_data(pptx_path):
    from src.ppt.extract import PPTXExtractor
    extractor = PPTXExtractor(pptx_path)
    return extractor.extract()


# ---------------------------------------------------------------------------
# 1. Invalid path
# ---------------------------------------------------------------------------

def test_invalid_path_raises():
    from src.ppt.extract import PPTXExtractor
    extractor = PPTXExtractor("/nonexistent/path/slides.pptx")
    with pytest.raises(FileNotFoundError):
        extractor.validate()


def test_invalid_extension_raises(tmp_path):
    from src.ppt.extract import PPTXExtractor
    bad = tmp_path / "slides.txt"
    bad.write_text("not a pptx")
    extractor = PPTXExtractor(bad)
    with pytest.raises(ValueError, match="Unsupported file type"):
        extractor.validate()


# ---------------------------------------------------------------------------
# 2. Presentation loading & slide count
# ---------------------------------------------------------------------------

def test_slide_count(presentation_data):
    assert presentation_data.num_slides == 3
    assert len(presentation_data.slides) == 3


# ---------------------------------------------------------------------------
# 3. Slide number extraction
# ---------------------------------------------------------------------------

def test_slide_numbers(presentation_data):
    numbers = [s.slide_number for s in presentation_data.slides]
    assert numbers == [1, 2, 3]


def test_slide_ids(presentation_data):
    ids = [s.slide_id for s in presentation_data.slides]
    assert ids == ["slide_01", "slide_02", "slide_03"]


# ---------------------------------------------------------------------------
# 4. Title extraction
# ---------------------------------------------------------------------------

def test_title_slide1(presentation_data):
    assert presentation_data.slides[0].title == "Project Architecture"


def test_title_slide2(presentation_data):
    assert presentation_data.slides[1].title == "Results"


def test_no_title_slide3(presentation_data):
    # Slide 3 uses a blank layout — no title placeholder
    assert presentation_data.slides[2].title is None


# ---------------------------------------------------------------------------
# 5. Text extraction
# ---------------------------------------------------------------------------

def test_text_slide1(presentation_data):
    text = presentation_data.slides[0].text
    combined = " ".join(text)
    assert "Data Collection" in combined
    assert "Pre-processing" in combined
    assert "Model Training" in combined


def test_text_does_not_duplicate_title(presentation_data):
    slide = presentation_data.slides[0]
    # Title should not appear again in the text blocks
    assert slide.title not in slide.text


def test_text_slide3_textbox(presentation_data):
    text = presentation_data.slides[2].text
    assert any("Standalone text box content" in t for t in text)


# ---------------------------------------------------------------------------
# 6. Table extraction
# ---------------------------------------------------------------------------

def test_no_tables_slide1(presentation_data):
    assert presentation_data.slides[0].tables == []


def test_table_slide2(presentation_data):
    tables = presentation_data.slides[1].tables
    assert len(tables) == 1
    rows = tables[0].rows
    assert rows[0] == ["Metric", "Value"]
    assert rows[1] == ["Accuracy", "92%"]


# ---------------------------------------------------------------------------
# 7. Notes extraction
# ---------------------------------------------------------------------------

def test_notes_slide2(presentation_data):
    notes = presentation_data.slides[1].notes
    assert notes is not None
    assert "accuracy" in notes.lower()


def test_notes_slide1_none(presentation_data):
    # Slide 1 has no notes set
    assert presentation_data.slides[0].notes is None


# ---------------------------------------------------------------------------
# 8. Metadata extraction
# ---------------------------------------------------------------------------

def test_metadata_keys(presentation_data):
    meta = presentation_data.slides[0].metadata
    for key in ("image_count", "table_count", "shape_count", "text_box_count",
                "has_chart", "slide_width_cm", "slide_height_cm"):
        assert key in meta, f"Missing metadata key: {key}"


def test_metadata_table_count_slide2(presentation_data):
    assert presentation_data.slides[1].metadata["table_count"] == 1


def test_metadata_dimensions(presentation_data):
    meta = presentation_data.slides[0].metadata
    assert meta["slide_width_cm"] > 0
    assert meta["slide_height_cm"] > 0


# ---------------------------------------------------------------------------
# 9. Meeting ID derivation
# ---------------------------------------------------------------------------

def test_meeting_id_from_filename(tmp_path):
    from src.ppt.extract import derive_meeting_id
    assert derive_meeting_id(tmp_path / "My Meeting 2024.pptx") == "my_meeting_2024"


def test_meeting_id_custom(pptx_path):
    from src.ppt.extract import PPTXExtractor
    extractor = PPTXExtractor(pptx_path, meeting_id="custom_meeting")
    pdata = extractor.extract()
    assert pdata.meeting_id == "custom_meeting"


def test_meeting_id_derived(pptx_path):
    from src.ppt.extract import PPTXExtractor
    extractor = PPTXExtractor(pptx_path)
    pdata = extractor.extract()
    assert pdata.meeting_id == "test_presentation"


# ---------------------------------------------------------------------------
# 10. JSON serialisation round-trip
# ---------------------------------------------------------------------------

def test_json_serialisation(presentation_data, tmp_path):
    from src.ppt.io import save_presentation_json, load_presentation_json

    out = tmp_path / "slides.json"
    save_presentation_json(presentation_data, out)

    assert out.exists()

    # Validate JSON is parseable
    raw = json.loads(out.read_text(encoding="utf-8"))
    assert raw["meeting_id"] == presentation_data.meeting_id
    assert raw["num_slides"] == presentation_data.num_slides
    assert len(raw["slides"]) == presentation_data.num_slides

    # Round-trip via load
    loaded = load_presentation_json(out)
    assert loaded.meeting_id == presentation_data.meeting_id
    assert loaded.num_slides == presentation_data.num_slides
    assert loaded.slides[0].title == presentation_data.slides[0].title
    assert loaded.slides[1].tables[0].rows == presentation_data.slides[1].tables[0].rows


def test_json_slide_structure(presentation_data, tmp_path):
    from src.ppt.io import save_presentation_json

    out = tmp_path / "slides2.json"
    save_presentation_json(presentation_data, out)
    raw = json.loads(out.read_text(encoding="utf-8"))

    slide = raw["slides"][0]
    assert "slide_id" in slide
    assert "slide_number" in slide
    assert "title" in slide
    assert "text" in slide
    assert "tables" in slide
    assert "notes" in slide
    assert "metadata" in slide


# ---------------------------------------------------------------------------
# 11. Slide text builder (used by embeddings)
# ---------------------------------------------------------------------------

def test_build_slide_text_includes_title(presentation_data):
    from src.ppt.embeddings import build_slide_text
    text = build_slide_text(presentation_data.slides[0])
    assert "Project Architecture" in text


def test_build_slide_text_includes_body(presentation_data):
    from src.ppt.embeddings import build_slide_text
    text = build_slide_text(presentation_data.slides[0])
    assert "Data Collection" in text


def test_build_slide_text_includes_table_cells(presentation_data):
    from src.ppt.embeddings import build_slide_text
    text = build_slide_text(presentation_data.slides[1])
    assert "Accuracy" in text
    assert "92%" in text


def test_build_slide_text_includes_notes(presentation_data):
    from src.ppt.embeddings import build_slide_text
    text = build_slide_text(presentation_data.slides[1])
    assert "accuracy" in text.lower()


# ---------------------------------------------------------------------------
# 12. SlideFeatures
# ---------------------------------------------------------------------------

def test_slide_features_extraction(presentation_data):
    from src.ppt.features import extract_slide_features
    f = extract_slide_features(presentation_data.slides[0])
    assert f.has_title is True
    assert f.has_text is True
    assert f.text_length > 0


def test_presentation_feature_summary(presentation_data):
    from src.ppt.features import extract_presentation_features, presentation_feature_summary
    features = extract_presentation_features(presentation_data)
    summary = presentation_feature_summary(features)
    assert summary["total_slides"] == 3
    assert summary["slides_with_title"] >= 2
    assert summary["slides_with_tables"] == 1


# ---------------------------------------------------------------------------
# 13. OCR interface (stub)
# ---------------------------------------------------------------------------

def test_ocr_disabled_returns_empty():
    from src.ppt.ocr import extract_ocr_text, is_ocr_enabled
    assert is_ocr_enabled() is False
    results = extract_ocr_text("slide_01", [b"fake_image_bytes"])
    assert results == []
