"""
Slide embedding generation using sentence-transformers.

Each slide is represented as a single text string combining:
  title + body text + table text + notes (when available)

A semantic embedding is then generated for that string using a
configurable sentence-transformers model.

Embeddings are stored separately from the main JSON output
(data/processed/slides/<meeting_id>_embeddings.npy) to keep the
primary output file lightweight.

The model name is read from config.yaml:
    ppt.embeddings.model
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np

from src.ppt.extract import PresentationData, SlideData
from src.utils.config import get
from src.utils.logging import get_logger

logger = get_logger("ppt.embeddings")

# ---------------------------------------------------------------------------
# Text construction
# ---------------------------------------------------------------------------

def build_slide_text(slide: SlideData) -> str:
    """
    Construct a single text representation for a slide.

    Order: title → body text → table cells → notes
    """
    parts: list[str] = []

    if slide.title:
        parts.append(slide.title)

    parts.extend(slide.text)

    for table in slide.tables:
        for row in table.rows:
            row_text = " ".join(cell for cell in row if cell)
            if row_text:
                parts.append(row_text)

    if slide.notes:
        parts.append(slide.notes)

    return " ".join(parts).strip()


# ---------------------------------------------------------------------------
# Embedding generation
# ---------------------------------------------------------------------------

def generate_embeddings(
    pdata: PresentationData,
    model_name: str | None = None,
) -> np.ndarray | None:
    """
    Generate a 2-D embedding matrix of shape (num_slides, embedding_dim).

    Parameters
    ----------
    pdata : PresentationData
        Fully extracted presentation.
    model_name : str | None
        sentence-transformers model name.  Falls back to config.yaml value
        ``ppt.embeddings.model``.  If still None, uses a safe default.

    Returns
    -------
    numpy.ndarray of shape (num_slides, dim) or None if generation fails.
    """
    resolved_model = model_name or get("ppt.embeddings.model") or "all-MiniLM-L6-v2"

    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except ImportError:
        logger.error(
            "sentence-transformers is not installed. "
            "Run: pip install sentence-transformers"
        )
        return None

    texts = [build_slide_text(s) for s in pdata.slides]

    # Warn about empty slides but don't abort
    empty = [i + 1 for i, t in enumerate(texts) if not t]
    if empty:
        logger.warning("Slides with no text content (will produce zero-vectors): %s", empty)

    logger.info("Loading embedding model: %s", resolved_model)
    t0 = time.time()

    try:
        model = SentenceTransformer(resolved_model)
    except Exception as exc:
        logger.error("Failed to load model '%s': %s", resolved_model, exc)
        return None

    logger.info("Encoding %d slides …", len(texts))
    embeddings: np.ndarray = model.encode(
        texts,
        show_progress_bar=False,
        convert_to_numpy=True,
    )

    logger.info(
        "Embeddings generated in %.2fs | shape=%s",
        time.time() - t0,
        embeddings.shape,
    )
    return embeddings


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def save_embeddings(embeddings: np.ndarray, output_path: Path) -> None:
    """Save embedding matrix to a .npy file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(str(output_path), embeddings)
    logger.info("Embeddings saved to: %s", output_path)


def load_embeddings(path: Path) -> np.ndarray:
    """Load a previously saved embedding matrix."""
    return np.load(str(path))


def get_slide_embedding(embeddings: np.ndarray, slide_index: int) -> np.ndarray:
    """Return the embedding vector for a single slide (0-indexed)."""
    return embeddings[slide_index]
