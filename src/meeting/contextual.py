"""Contextual discriminative text models; source passages remain unchanged."""
from functools import lru_cache
from pathlib import Path

import numpy as np


def context_pairs(rows, radius=2):
    """Target text plus neighboring turns, always bounded by meeting."""
    if radius < 0:
        raise ValueError('Context radius must be nonnegative')
    pairs = [None]*len(rows)
    groups = {}
    for i, row in enumerate(rows):
        if not isinstance(row.get('text'), str) or not row.get('meeting'):
            raise ValueError('Each passage needs text and a meeting ID')
        groups.setdefault(row['meeting'], []).append(i)
    for indices in groups.values():
        indices.sort(key=lambda i: (rows[i]['start'], str(rows[i].get('act_id', i))))
        for offset, index in enumerate(indices):
            before = ' '.join(rows[j]['text'] for j in indices[max(0, offset-radius):offset])
            after = ' '.join(rows[j]['text'] for j in indices[offset+1:offset+radius+1])
            pairs[index] = (rows[index]['text'], 'Previous: '+before+' Following: '+after)
    return pairs


@lru_cache(maxsize=2)
def load_contextual_model(directory):
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    path = Path(directory)
    tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(path, local_files_only=True)
    model.eval()
    return tokenizer, model


def predict_pairs(directory, pairs, max_length=96, batch_size=32, multiclass=False):
    import torch
    if batch_size < 1:
        raise ValueError('Batch size must be positive')
    tokenizer, model = load_contextual_model(str(Path(directory).resolve()))
    if not pairs:
        return np.empty((0, model.config.num_labels))
    scores = []
    with torch.inference_mode():
        for start in range(0, len(pairs), batch_size):
            batch = pairs[start:start+batch_size]
            tokens = tokenizer([p[0] for p in batch], [p[1] for p in batch],
                               padding=True, truncation=True, max_length=max_length, return_tensors='pt')
            logits = model(**tokens).logits
            scores.append((logits.softmax(-1) if multiclass else logits.sigmoid()).numpy())
    return np.vstack(scores)
