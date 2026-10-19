"""Translate native reports to the website schema without rerunning inference."""
import copy
import math


def website_report(source):
    if not isinstance(source, dict) or source.get('completed') is not True:
        raise ValueError('Publish a completed meeting report')
    data = copy.deepcopy(source)
    segments = data.get('transcript_segments')
    if not isinstance(segments, list) or len(segments) > 100_000:
        raise ValueError('Invalid transcript')
    for index, row in enumerate(segments):
        if not isinstance(row, dict) or not isinstance(row.get('text'), str) or not isinstance(row.get('speaker'), str):
            raise ValueError('Invalid transcript passage')
        start, end = row.get('start'), row.get('end')
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (start, end)) or not 0 <= start <= end:
            raise ValueError('Invalid passage timestamps')
        row.setdefault('segment_id', index + 1)
    duration = data.get('duration', data.get('meeting_overview', {}).get('duration_s', 0))
    if not isinstance(duration, (int, float)) or not math.isfinite(duration) or not 0 <= duration <= 21600:
        raise ValueError('Invalid meeting duration')
    if any(row['end'] > duration + 1 for row in segments):
        raise ValueError('Transcript extends beyond the meeting duration')
    # Reject malformed containers before they can break either report viewer.
    for key in ('participants', 'influence', 'decisions', 'slides', 'aligned_segments', 'events', 'event_timeline', 'action_items'):
        if key in data and (not isinstance(data[key], list) or any(not isinstance(row, dict) for row in data[key])):
            raise ValueError('Invalid report collection: ' + key)
    for key in ('speaker_names', 'speaker_roles'):
        values = data.setdefault(key, {})
        if not isinstance(values, dict) or len(values) > 100 or any(not isinstance(v, str) or len(v) > 200 for v in values.values()):
            raise ValueError('Invalid participant labels')
    data.setdefault('meeting_overview', {})['duration_s'] = duration
    data.setdefault('processing', {})['language'] = data.get('language', 'auto')
    data.setdefault('event_timeline', data.get('events', []))
    data.setdefault('action_items', [dict(e, timestamp_s=e.get('start')) for e in data['event_timeline'] if e.get('event_type') == 'action_item'])
    from src.meeting.followups import validate_reviews
    validate_reviews(data)
    for person in data.get('participants', []):
        person.setdefault('speaker_id', person.get('speaker', 'UNKNOWN'))
        person.setdefault('speaking_duration_s', person.get('speaking_time_s', 0))
        if not isinstance(person['speaker_id'], str) or not isinstance(person.get('roles', []), list) or any(not isinstance(role, str) for role in person.get('roles', [])):
            raise ValueError('Invalid participant roles')
    for decision in data.get('decisions', []):
        decision.setdefault('topic', decision.get('text', ''))
        decision.setdefault('status', 'candidate')
        decision.setdefault('final_decision_text', decision.get('text', ''))
    for slide in data.get('slides', []):
        if isinstance(slide.get('text'), str):
            slide['text'] = [slide['text']]
    for match in data.get('aligned_segments', []):
        if 'selected_slide' in match and 'slide_id' not in match:
            number = match['selected_slide']
            slides = data.get('slides', [])
            match['slide_id'] = next((s.get('slide_id') for s in slides if s.get('slide_number') == number), None)
            match['alignment_score'] = match.get('score')
    if isinstance(data.get('interactions'), list):
        data['interactions'] = {'relationships': [dict(edge, source_speaker=edge.get('source'), target_speaker=edge.get('target')) for edge in data['interactions']]}
    feature_names = dict(zip(('proposal', 'evidence', 'objection', 'revision', 'decision', 'interaction', 'slide_grounding'),
        ('proposal_contribution', 'evidence_contribution', 'objection_contribution', 'revision_contribution', 'decision_contribution', 'interaction_contribution', 'slide_grounded_contribution')))
    for person in data.get('influence', []):
        for field in ('raw_features', 'normalised_features'):
            values = person.get(field, {})
            for short, full in feature_names.items():
                if short in values:
                    values.setdefault(full, values[short])
        if 'normalised_features' in person:
            person.setdefault('features', person['normalised_features'])
    return data
