"""Local learned discussion review; membership scores never create final decisions."""
import logging
import math
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.sparse import hstack

from src.utils.cache import atomic_json
from src.utils.config import PROJECT_ROOT, get

logger = logging.getLogger(__name__)
MODEL_VERSION = 1


def ordered_meetings(rows):
    groups = {}
    for i, row in enumerate(rows):
        groups.setdefault(row.get('meeting', ''), []).append(i)
    return [np.array(sorted(indices, key=lambda i: (rows[i]['start'], str(rows[i].get('act_id', i)))))
            for indices in groups.values()]


def component_scores(rows, bundle, batch_size=256):
    """Bound feature matrices and expanded context to one batch, preserving input order."""
    result = {key: np.empty(len(rows)) for key in ['linear', 'forest']}
    vectorizers = bundle['vectorizers']
    radius = bundle['context_radius']
    for indices in ordered_meetings(rows):
        for left in range(0, len(indices), batch_size):
            chosen = indices[left:left + batch_size]
            texts = [rows[i]['text'] for i in chosen]
            contexts = [' '.join(rows[j]['text'] for j in indices[max(0, offset-radius):offset+radius+1])
                        for offset in range(left, left + len(chosen))]
            matrix = hstack([vectorizers['word'].transform(texts), vectorizers['char'].transform(texts),
                             vectorizers['context_40'].transform(contexts)], format='csr')
            for key in result:
                result[key][chosen] = bundle['classifiers'][key].predict_proba(matrix)[:, 1]
    return result


def combine_scores(rows, components, linear_weight, smoothing_radius):
    scores = linear_weight * components['linear'] + (1-linear_weight) * components['forest']
    result = scores.copy()
    for indices in ordered_meetings(rows):
        cumulative = np.r_[0., np.cumsum(scores[indices])]
        offsets = np.arange(len(indices))
        left = np.maximum(0, offsets - smoothing_radius)
        right = np.minimum(len(indices), offsets + smoothing_radius + 1)
        result[indices] = (cumulative[right]-cumulative[left]) / (right-left)
    return result


@lru_cache(maxsize=1)
def _load_model(path, modified_ns, size):
    import joblib
    bundle = joblib.load(path)
    if (bundle.get('version') != MODEL_VERSION or bundle.get('task') != 'discussion_membership'
            or bundle.get('context_radius') != 40 or not 0 <= bundle.get('linear_weight', -1) <= 1
            or not 0 <= bundle.get('threshold', -1) <= 1
            or bundle.get('smoothing_radius') not in {0, 5, 15}):
        raise ValueError('Unsupported discussion model')
    return bundle


def review_discussions(segments, meeting_id, language, model_path):
    result = {'status': 'unavailable', 'passages': [], 'requires_review': True,
              'task': 'discussion_membership', 'accuracy_measured': False}
    if language != 'en':
        return {**result, 'status': 'unsupported_language'}
    path = Path(model_path)
    if not path.is_file():
        return {**result, 'status': 'model_unavailable'}
    rows = []
    ids = set()
    for i, segment in enumerate(segments):
        start, end, text = segment.get('start'), segment.get('end'), segment.get('text')
        if (not isinstance(text, str) or any(isinstance(v, bool) or not isinstance(v, (int, float))
                or not math.isfinite(v) for v in (start, end)) or not 0 <= start <= end):
            raise ValueError('Invalid transcript passage for discussion review')
        source_id = segment.get('segment_id', i + 1)
        if not isinstance(source_id, int) or isinstance(source_id, bool) or source_id in ids:
            raise ValueError('Discussion source segment IDs must be unique integers')
        ids.add(source_id)
        if text.strip():
            rows.append({'meeting': meeting_id, 'start': start, 'end': end, 'text': text,
                         'source_segment_id': source_id, 'speaker': segment.get('speaker', 'UNKNOWN')})
    stat = path.stat()
    bundle = _load_model(str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    components = component_scores(rows, bundle) if rows else {'linear': np.array([]), 'forest': np.array([])}
    scores = combine_scores(rows, components, bundle['linear_weight'], bundle['smoothing_radius'])
    for row, score in zip(rows, scores):
        if score >= bundle['threshold']:
            result['passages'].append({key: row[key] for key in
                ['source_segment_id', 'start', 'end', 'text', 'speaker']} | {'score': float(score)})
    result['passages'].sort(key=lambda row: (row['start'], row['source_segment_id']))
    return {**result, 'status': 'ready', 'scored_segments': len(rows),
            'model': bundle['method'], 'selection_sha256': bundle['selection_sha256'],
            'limitations': 'English research model applied to ASR passages; these are review suggestions, not final decisions. Scores are not calibrated correctness probabilities; recording-level accuracy has not been measured.'}


def run_discussion_review(segments, meeting_id, language, output_root):
    started = time.perf_counter()
    if not get('discussion_review.enabled', True):
        result = {'status': 'disabled', 'passages': [], 'requires_review': True}
    else:
        path = PROJECT_ROOT / get('discussion_review.model', 'models/discussion/model.joblib')
        try:
            result = review_discussions(segments, meeting_id, language, path)
        except Exception:
            logger.exception('Learned discussion review failed for %s', meeting_id)
            result = {'status': 'error', 'passages': [], 'requires_review': True}
    result['elapsed_seconds'] = round(time.perf_counter() - started, 6)
    atomic_json(Path(output_root) / 'discussions' / f'{meeting_id}_discussions.json', result)
    return result
