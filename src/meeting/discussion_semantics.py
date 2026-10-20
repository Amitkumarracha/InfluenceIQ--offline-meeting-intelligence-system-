"""Frozen local sentence features and meeting-bounded context for discussion detection."""
import numpy as np

from src.meeting.discussions import ordered_meetings


def encode_rows(rows, model=None):
    if not rows:
        return np.zeros((0, 384), dtype=np.float32)
    if model is None:
        from src.fusion.semantic_alignment import load_embedding_model
        model = load_embedding_model('all-MiniLM-L6-v2')
    texts = list(dict.fromkeys(row['text'] for row in rows))
    vectors = model.encode(texts, batch_size=64, normalize_embeddings=True,
                           convert_to_numpy=True, show_progress_bar=False)
    lookup = {text: i for i, text in enumerate(texts)}
    return np.asarray(vectors, dtype=np.float32)[[lookup[row['text']] for row in rows]]


def context_features(rows, embeddings, radius, timing=False):
    if len(rows) != len(embeddings) or radius < 0:
        raise ValueError('Invalid semantic context input')
    means = np.zeros_like(embeddings)
    metadata = np.zeros((len(rows), 6), dtype=np.float32)
    for indices in ordered_meetings(rows):
        cumulative = np.vstack([np.zeros((1, embeddings.shape[1])), np.cumsum(embeddings[indices], axis=0, dtype=np.float64)])
        offsets = np.arange(len(indices))
        left, right = np.maximum(0, offsets-radius), np.minimum(len(indices), offsets+radius+1)
        means[indices] = (cumulative[right]-cumulative[left]) / (right-left)[:, None]
        first = min(rows[i]['start'] for i in indices)
        duration = max(max(rows[i]['end'] for i in indices)-first, 1.)
        for offset, index in enumerate(indices):
            row = rows[index]
            position = (row['start']-first)/duration
            previous_gap = max(0., row['start']-rows[indices[offset-1]]['end']) if offset else 0.
            next_gap = max(0., rows[indices[offset+1]]['start']-row['end']) if offset+1 < len(indices) else 0.
            metadata[index] = [np.log1p(len(row['text'].split()))/5,
                np.log1p(max(0., row['end']-row['start']))/5, position, position**2,
                min(previous_gap, 60.)/60, min(next_gap, 60.)/60]
    norms = np.linalg.norm(means, axis=1, keepdims=True)
    means = means / np.maximum(norms, 1e-12)
    return np.hstack([embeddings, means, metadata] if timing else [embeddings, means]).astype(np.float32)
