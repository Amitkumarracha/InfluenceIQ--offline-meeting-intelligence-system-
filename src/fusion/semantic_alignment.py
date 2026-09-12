"""
Semantic alignment between transcript segments and slides.

Uses cosine similarity between:
  - a transcript segment text embedding
  - pre-computed slide content embeddings (from Phase 6)

All embedding computation is vectorised (numpy matrix ops) to keep
performance acceptable on long meetings.

The module never mixes OCR-derived text with native text without tagging,
and never fabricates similarity scores.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SemanticScore:
    """Cosine similarity result for one (segment, slide) pair."""
    slide_id: str
    score: float          # cosine similarity in [-1, 1], typically [0, 1]


# ---------------------------------------------------------------------------
# Cosine similarity (vectorised)
# ---------------------------------------------------------------------------

def _l2_normalise(matrix: np.ndarray) -> np.ndarray:
    """Row-wise L2 normalisation.  Zero vectors become zero rows."""
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-12, norms)
    return matrix / norms


def cosine_similarity_matrix(
    query: np.ndarray,          # shape (D,) or (1, D)
    keys: np.ndarray,           # shape (N, D)
) -> np.ndarray:                # shape (N,)
    """
    Compute cosine similarity between one query vector and N key vectors.

    Returns a 1-D array of N similarity scores.
    """
    q = query.reshape(1, -1).astype(np.float32)
    k = keys.astype(np.float32)
    q_norm = _l2_normalise(q)
    k_norm = _l2_normalise(k)
    return (q_norm @ k_norm.T).flatten()


# ---------------------------------------------------------------------------
# Segment embedding
# ---------------------------------------------------------------------------

def embed_text(text: str, model: object) -> np.ndarray:
    """
    Encode a single text string using a sentence-transformers model.

    Parameters
    ----------
    text : str
        The text to embed.  If empty, a zero vector of the model's
        output dimension is returned.
    model : SentenceTransformer
        A loaded sentence-transformers model instance.

    Returns
    -------
    np.ndarray of shape (D,)
    """
    if not text or not text.strip():
        # Attempt to get output dim from the model; fall back to 384
        try:
            dim = model.get_sentence_embedding_dimension()  # type: ignore[attr-defined]
        except Exception:
            dim = 384
        return np.zeros(dim, dtype=np.float32)

    result = model.encode(  # type: ignore[attr-defined]
        [text.strip()],
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return result[0].astype(np.float32)


# ---------------------------------------------------------------------------
# Main semantic scoring function
# ---------------------------------------------------------------------------

def compute_semantic_scores(
    segment_text: str,
    slide_ids: list[str],
    slide_embeddings: np.ndarray,
    model: object,
) -> list[SemanticScore]:
    """
    Compute cosine similarity between a transcript segment and every slide.

    Parameters
    ----------
    segment_text : str
        The ASR text of the transcript segment.
    slide_ids : list[str]
        Slide IDs in the same order as rows in *slide_embeddings*.
    slide_embeddings : np.ndarray
        Shape (num_slides, D) — pre-computed from Phase 6.
    model : SentenceTransformer
        Loaded sentence-transformers model.

    Returns
    -------
    list[SemanticScore], one per slide, in the same order as *slide_ids*.
    """
    if len(slide_ids) != slide_embeddings.shape[0]:
        raise ValueError(
            f"slide_ids length ({len(slide_ids)}) does not match "
            f"embeddings rows ({slide_embeddings.shape[0]})"
        )

    seg_emb = embed_text(segment_text, model)
    scores = cosine_similarity_matrix(seg_emb, slide_embeddings)

    return [
        SemanticScore(slide_id=sid, score=float(round(float(s), 6)))
        for sid, s in zip(slide_ids, scores)
    ]


# ---------------------------------------------------------------------------
# Model loader (shared across alignment calls)
# ---------------------------------------------------------------------------

def load_embedding_model(model_name: str) -> object:
    """
    Load a sentence-transformers model by name.

    Raises ImportError with a helpful message if sentence-transformers is
    not installed.  Raises RuntimeError if the model cannot be loaded.
    """
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "sentence-transformers is required for semantic alignment. "
            "Run: pip install sentence-transformers"
        ) from exc

    try:
        return SentenceTransformer(model_name)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load embedding model '{model_name}': {exc}"
        ) from exc
