"""Measured stage progress and explicitly estimated completion times."""
from datetime import datetime, timezone


STAGE_WEIGHTS = dict(decoding=2, preprocessing=1, transcription=48, diarization=43,
                     attribution=1, slides=2, alignment=1, events=.5, decisions=.3,
                     interactions=.3, influence=.4, report=.5)


def job_progress(state, status, now=None):
    now = now or datetime.now(timezone.utc)
    stage = state.get('stage')
    details = dict(state.get('progress') or {})
    timings = state.get('stage_timings_seconds') or {}

    def age(value):
        try:
            stamp = datetime.fromisoformat(value)
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            return max(0, (now - stamp).total_seconds())
        except (TypeError, ValueError, AttributeError):
            return None

    stage_elapsed = age(state.get('stage_started_at')) if status == 'processing' else None
    elapsed = age(state.get('started_at')) if status == 'processing' else state.get('worker_elapsed_seconds')
    if elapsed is None and stage_elapsed is not None:
        elapsed = sum(v for k, v in timings.items() if k != 'queued') + stage_elapsed
    completed, total = details.get('completed_seconds', 0), details.get('total_seconds', 0)
    fraction = min(1, max(0, completed / total)) if total and total > 0 else None
    weights = dict(STAGE_WEIGHTS)
    if state.get('diarization') == 'off':
        weights.pop('diarization'); weights.pop('attribution')
    if not state.get('ppt'):
        weights.pop('slides'); weights.pop('alignment')
    # Completed timings also handle jobs from the older diarization-first order.
    done = set(timings) - {stage, 'queued'}
    weighted_done = sum(weight for name, weight in weights.items() if name in done)
    overall = (weighted_done + weights.get(stage, 0) * (fraction or 0)) / sum(weights.values()) * 100
    remaining_stage = None
    if fraction and .01 <= fraction < 1 and stage_elapsed and not details.get('cached'):
        remaining_stage = stage_elapsed * (1 - fraction) / fraction
    estimates = state.get('estimated_stage_seconds') or {}
    remaining_total = None
    if estimates and status == 'processing':
        remaining_total = sum(value for name, value in estimates.items() if name not in done and name != stage)
        if remaining_stage is not None:
            remaining_total += remaining_stage
        elif stage in estimates:
            remaining_total += max(0, estimates[stage] - (stage_elapsed or 0))
        else:
            remaining_total = None
    if status == 'completed':
        overall, remaining_total = 100, 0
    elif status == 'queued':
        overall, elapsed = 0, 0
    details.update(stage_elapsed_seconds=stage_elapsed, elapsed_seconds=elapsed,
                   overall_percent=round(min(99, overall), 1) if status != 'completed' else 100,
                   stage_percent=round(fraction * 100, 1) if fraction is not None else None,
                   remaining_stage_seconds=remaining_stage, estimated_remaining_seconds=remaining_total,
                   estimated_total_seconds=(elapsed or 0) + remaining_total if remaining_total is not None else None,
                   estimate_method='Previous local runs and measured current-stage pace; may change',
                   stage_timings_seconds=timings, started_at=state.get('started_at'),
                   finished_at=state.get('finished_at'), recording_seconds=state.get('audio_duration_seconds'),
                   stages=list(weights))
    return details
