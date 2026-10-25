"""Optional semantic topic grouping; short responses inherit the preceding topic."""
import numpy as np


def event_topics(events, embeddings, similarity=.5, max_gap_s=180):
    vectors = np.asarray(embeddings, dtype=float)
    if (vectors.ndim != 2 or len(vectors) != len(events) or not np.isfinite(vectors).all()
            or not 0 <= similarity <= 1 or max_gap_s <= 0):
        raise ValueError('Valid event embeddings, similarity and time window are required')
    if len({event.event_id for event in events}) != len(events):
        raise ValueError('Event IDs must be unique')
    vectors = vectors/np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12)
    clusters, mapping = [], {}
    previous = None
    for index in sorted(range(len(events)), key=lambda i: (events[i].start, events[i].event_id)):
        event = events[index]
        if previous is not None and len(event.text.split()) <= 3 and event.event_type in {'agreement', 'disagreement', 'clarification'}:
            chosen = previous if event.start-clusters[previous]['end'] <= max_gap_s else None
        else:
            eligible = [(float(vectors[index] @ cluster['center']), i) for i, cluster in enumerate(clusters)
                        if event.start-cluster['end'] <= max_gap_s]
            best = max(eligible, default=(-1, -1))
            chosen = best[1] if best[0] >= similarity else None
        if chosen is None:
            chosen = len(clusters)
            clusters.append({'sum': vectors[index].copy(), 'center': vectors[index].copy(), 'end': event.end})
        else:
            cluster = clusters[chosen]
            cluster['sum'] += vectors[index]
            cluster['center'] = cluster['sum']/max(np.linalg.norm(cluster['sum']), 1e-12)
            cluster['end'] = max(cluster['end'], event.end)
        mapping[event.event_id] = chosen
        previous = chosen
    return mapping


def infer_event_topics(events, similarity=.5, max_gap_s=180):
    if not events:
        return {}
    from src.fusion.semantic_alignment import load_embedding_model
    model = load_embedding_model('all-MiniLM-L6-v2')
    embeddings = model.encode([event.text for event in events], normalize_embeddings=True, show_progress_bar=False)
    return event_topics(events, embeddings, similarity, max_gap_s)
