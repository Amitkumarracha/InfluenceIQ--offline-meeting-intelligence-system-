"""Optional participant ranking using the same observed features in research and runtime."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

import numpy as np

from src.meeting.events import ALL_EVENT_TYPES
from src.meeting.influence import FEATURE_KEYS, speech_statistics
from src.utils.config import PROJECT_ROOT

RAW_KEYS = [key+'_contribution' for key in FEATURE_KEYS[:-1]]+['slide_grounded_contribution']
FEATURE_NAMES = ['duration', 'words', 'utterances', 'mean_words', 'early_words', 'late_words',
                 'reason_markers', 'suggestion_markers', 'first_person', 'inclusive_pronouns']+[
                     'event_'+name for name in ALL_EVENT_TYPES]+['influence_'+name for name in FEATURE_KEYS]


def participant_features(events, influence, segments):
    seconds, _ = speech_statistics(segments)
    end = max((row['end'] for row in segments), default=0)
    values = {}
    for participant in influence.participants:
        speaker = participant.participant
        own = [row for row in segments if row.get('speaker') == speaker]
        text = ' '.join(row['text'] for row in own)
        tokens = re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower())
        counts = Counter(event.event_type for event in events.events if event.speaker == speaker)
        raw = [seconds.get(speaker, 0), len(tokens), len(own), len(tokens)/max(1, len(own)),
               sum(len(row['text'].split()) for row in own if row['start'] < end/3),
               sum(len(row['text'].split()) for row in own if row['start'] >= end*2/3),
               sum(token in {'because', 'since', 'reason', 'therefore', 'evidence'} for token in tokens),
               len(re.findall(r"\b(?:i think|we should|how about|let's|i suggest|we need)\b", text.lower())),
               sum(token in {'i', 'my', 'me'} for token in tokens),
               sum(token in {'we', 'our', 'us'} for token in tokens)]
        values[speaker] = raw+[counts[name] for name in ALL_EVENT_TYPES]+[participant.raw_features[key] for key in RAW_KEYS]
    if not values:
        return {}
    matrix = np.array(list(values.values()), dtype=float)
    maximum = matrix.max(axis=0)
    matrix = np.divide(matrix, maximum, out=np.zeros_like(matrix), where=maximum > 0)
    return {speaker: dict(zip(FEATURE_NAMES, vector)) for speaker, vector in zip(values, matrix)}


def xgb_ranker_class():
    try:
        from xgboost import XGBRanker
    except ImportError:
        directory = PROJECT_ROOT/'.runtime/research-ranking-deps'
        if not (directory/'xgboost/__init__.py').is_file():
            raise RuntimeError('CPU XGBoost is not provisioned; see the research upgrade guide')
        sys.path.insert(0, str(directory))
        from xgboost import XGBRanker
    return XGBRanker


def rank_participants(directory, features, topic_aware=False):
    root = Path(directory)
    metadata = json.loads((root/'ranker.json').read_text())
    if metadata.get('topic_aware') != topic_aware:
        raise ValueError('Ranking model requires matching topic grouping')
    path = root/'ranker.ubj'
    if hashlib.sha256(path.read_bytes()).hexdigest() != metadata['model_sha256']:
        raise ValueError('Ranker differs from the frozen research model')
    if not set(metadata['features']).issubset(FEATURE_NAMES):
        raise ValueError('Unsupported ranking feature schema')
    speakers = sorted(features)
    matrix = np.array([[features[speaker][name] for name in metadata['features']] for speaker in speakers])
    if not np.isfinite(matrix).all():
        raise ValueError('Ranker features must be finite')
    if not speakers:
        return {'status': 'unavailable_without_speakers', 'participants': []}
    model = xgb_ranker_class()()
    model.load_model(path); model.set_params(n_jobs=2)
    scores = model.predict(matrix)
    return {'status': 'experimental_outcome_alignment_ranking', 'accuracy_measured': False,
            'score_note': 'Raw ranking margins, not correctness probabilities or causal influence',
            'participants': sorted([{'participant': speaker, 'raw_score': float(value)}
                                    for speaker, value in zip(speakers, scores)], key=lambda row: -row['raw_score'])}
