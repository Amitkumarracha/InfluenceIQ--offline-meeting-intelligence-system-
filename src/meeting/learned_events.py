"""Optional English contextual role extractor; keyword evidence/revision rules remain available."""
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from src.meeting.contextual import context_pairs, predict_pairs
from src.meeting.events import BaseEventExtractor, EventExtractionResult, MeetingEvent, KeywordEventExtractor

LABELS = ['Proposal', 'Agreement', 'Disagreement', 'Confirmation']
# GAP confirmation is an affirmation, not independent evidence of a final decision.
EVENT_TYPES = ['proposal', 'agreement', 'disagreement', 'agreement']


class ContextualRoleExtractor(BaseEventExtractor):
    def __init__(self, directory):
        self.directory = Path(directory)
        self.protocol = json.loads((self.directory/'protocol.json').read_text())
        self.selection = json.loads((self.directory/'selection.json').read_text())
        if self.protocol.get('task') != 'roles' or self.selection.get('labels') != LABELS:
            raise ValueError('An English contribution-role model is required')
        weights = self.directory/'model/model.safetensors'
        if hashlib.sha256(weights.read_bytes()).hexdigest() != self.selection['model_sha256']:
            raise ValueError('Contribution model differs from frozen selection')
        self.thresholds = self.selection['development']['thresholds']
        if len(self.thresholds) != len(LABELS) or any(not 0 <= value <= 1 for value in self.thresholds):
            raise ValueError('Four finite role thresholds in [0, 1] are required')

    def extract(self, segments, meeting_id):
        rows = []
        seen = set()
        for i, segment in enumerate(segments):
            source_id = segment.get('segment_id', i+1)
            if not isinstance(source_id, int) or isinstance(source_id, bool) or source_id in seen:
                raise ValueError('Contribution source IDs must be unique integers')
            seen.add(source_id)
            if (not isinstance(segment.get('text'), str)
                    or not all(isinstance(segment.get(key), (int, float)) and not isinstance(segment[key], bool)
                               and math.isfinite(segment[key]) for key in ['start', 'end'])
                    or not 0 <= segment['start'] <= segment['end']):
                raise ValueError('Invalid contribution source passage')
            rows.append({**segment, 'source_id': source_id, 'meeting': meeting_id})
        scores = predict_pairs(self.directory/'model', context_pairs(rows), self.protocol['max_length'])
        if scores.shape != (len(rows), len(LABELS)) or not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
            raise ValueError('Invalid contribution model scores')
        # Keep explicit decision rules; agreement and confirmation share one event per passage.
        result = KeywordEventExtractor().extract(segments, meeting_id)
        events = [event for event in result.events if event.event_type not in EVENT_TYPES]
        for row, probabilities in zip(rows, scores):
            detected = {}
            for event_type, value, threshold in zip(EVENT_TYPES, probabilities, self.thresholds):
                if value >= threshold:
                    detected[event_type] = max(detected.get(event_type, 0), float(value))
            for event_type, value in detected.items():
                events.append(MeetingEvent('', event_type, row.get('speaker', 'UNKNOWN'),
                    float(row['start']), float(row['end']), row['text'],
                    None if row.get('slide_id') == 'NO_CONFIDENT_SLIDE' else row.get('slide_id'),
                    value, row['source_id']))
        events.sort(key=lambda event: (event.start, event.source_segment_id, event.event_type))
        for number, event in enumerate(events, 1):
            event.event_id = f'event_{number:03d}'
        return EventExtractionResult(meeting_id, events)
