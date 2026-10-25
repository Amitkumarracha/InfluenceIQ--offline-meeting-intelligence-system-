"""Source-linked outcome candidates and optional independently trained relation inference."""
import hashlib
import json
from pathlib import Path

import numpy as np

from src.meeting.influence import _decision_event_ids
from src.utils.cache import atomic_json

RELATIONS = ['adopted', 'rejected', 'revised', 'unresolved']


def outcome_candidates(events, decisions):
    index = {event.event_id: event for event in events.events}
    rows = []
    for decision in decisions.decisions:
        outcome = index.get((decision.final_decision or {}).get('event_id'))
        for event_id in sorted(_decision_event_ids(decision)):
            event = index.get(event_id)
            if event is None or event.event_type not in {'proposal', 'evidence', 'objection', 'disagreement', 'revision'}:
                continue
            if outcome is not None and event.start > outcome.start:
                continue
            rows.append({'meeting_id': events.meeting_id, 'decision_id': decision.decision_id,
                         'source_event_id': event.event_id, 'source_speaker': event.speaker,
                         'source_start': event.start, 'source_text': event.text, 'source_type': event.event_type,
                         'outcome_event_id': outcome.event_id if outcome else None,
                         'outcome_start': outcome.start if outcome else None,
                         'outcome_text': outcome.text if outcome else None,
                         'relationship': None, 'label_source': None, 'group': None, 'split': None})
    return rows


def link_outcomes(events, decisions, model_dir=None, minimum_score=.5):
    if not 0 <= minimum_score <= 1:
        raise ValueError('Minimum relation score must lie in [0, 1]')
    candidates = outcome_candidates(events, decisions)
    result = {'status': 'independent_annotations_required', 'links': candidates,
              'accuracy_measured': False, 'requires_review': True}
    if model_dir is None:
        return result
    root = Path(model_dir)
    protocol = json.loads((root/'protocol.json').read_text())
    selected = json.loads((root/'selection.json').read_text())
    if protocol.get('task') != 'links' or selected.get('labels') != RELATIONS:
        raise ValueError('An independently trained outcome-link model is required')
    weights = root/'model/model.safetensors'
    if hashlib.sha256(weights.read_bytes()).hexdigest() != selected['model_sha256']:
        raise ValueError('Outcome model differs from frozen selection')
    eligible = [row for row in candidates if row['outcome_text'] is not None]
    from src.meeting.contextual import predict_pairs
    scores = predict_pairs(root/'model', [(row['source_text'], row['outcome_text']) for row in eligible],
                           protocol['max_length'], multiclass=True)
    if scores.shape != (len(eligible), len(RELATIONS)) or not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
        raise ValueError('Invalid outcome model scores')
    for row, values in zip(eligible, scores):
        best = int(values.argmax())
        row['predicted_relationship'] = RELATIONS[best] if values[best] >= minimum_score else None
        row['model_score'] = float(values[best])
        # Predictions never fill the independent-reference relationship or label_source fields.
    return {**result, 'status': 'experimental_predictions', 'score_note': 'Uncalibrated model scores; review against source'}


def save_outcome_analysis(events, decisions, output_path, model_dir=None):
    result = link_outcomes(events, decisions, model_dir)
    atomic_json(Path(output_path), result)
    return result
