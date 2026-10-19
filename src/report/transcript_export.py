"""Exports derived from the saved report, including attributed transcript and structured NLP analysis."""
import csv
import io


def stamp(seconds, separator='.'):
    ms = max(0, round(float(seconds) * 1000))
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}{separator}{ms % 1000:03d}'


def render_export(data, title, format, meeting_id=None):
    from src.meeting.followups import action_candidates, active_review, calendar_export
    if format == 'ics':
        return calendar_export(data, title, meeting_id or data.get('meeting_id', 'meeting')), 'text/calendar'
    segments = data.get('transcript_segments', [])
    names = data.get('speaker_names', {})
    roles = data.get('speaker_roles', {})
    estimated = {p['speaker_id']: ', '.join(p.get('roles', [])).replace('_', ' ') for p in data.get('participants', [])}
    def label(speaker):
        speaker = speaker or 'UNKNOWN'
        name = names.get(speaker, speaker)
        role = roles.get(speaker) or estimated.get(speaker)
        return f'{name} · {role}' if role else name
    if format in {'srt', 'vtt'}:
        entries = ['WEBVTT\n'] if format == 'vtt' else []
        for index, s in enumerate(segments, 1):
            sep = ',' if format == 'srt' else '.'
            speaker = label(s['speaker'])
            text = s['text'].replace('-->', '→')
            entries.append(f"{index}\n{stamp(s['start'], sep)} --> {stamp(s['end'], sep)}\n{speaker}: {text}\n")
        return '\n'.join(entries), 'text/vtt' if format == 'vtt' else 'application/x-subrip'
    if format == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['segment_id', 'start', 'end', 'speaker', 'text', 'role'])
        for s in segments:
            row = [s.get('segment_id'), s['start'], s['end'], names.get(s['speaker'], s['speaker']), s['text'], roles.get(s['speaker']) or estimated.get(s['speaker'], '')]
            writer.writerow(["'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v for v in row])
        return output.getvalue(), 'text/csv'
    if format not in {'txt', 'md'}:
        raise ValueError('Unsupported export format')
    lines = [f'# {title}' if format == 'md' else title, '', 'Structured NLP analysis — verify against source audio.', '']
    if data.get('speaker_names') or data.get('speaker_roles'):
        lines += ['## Speakers', '']
        for speaker in sorted(set(names) | set(data.get('speaker_roles', {}))):
            lines.append(f"- {names.get(speaker, speaker)}: {data.get('speaker_roles', {}).get(speaker, 'Role not assigned')}")
        lines.append('')
    if data.get('vocabulary'):
        lines += ['## Vocabulary', '', data['vocabulary'], '']
    for warning in data.get('processing', {}).get('warnings', []):
        lines += [warning, '']
    lines += ['## Decision candidates', '']
    for decision in data.get('decisions', []):
        lines.append(f"- {decision.get('final_decision_text') or decision.get('proposal_text') or decision.get('topic', '')} ({decision.get('status', 'unknown')})")
    lines += ['', '## Action candidates', '']
    for action in action_candidates(data).values():
        lines.append(f"- {label(action.get('speaker', 'UNKNOWN'))}: {action.get('text', '')}")
        review = active_review(data, action)
        if review:
            lines.append(f"  User reviewed: {review['state']}; owner: {review['owner'] or 'Unassigned'}; due: {review['due_date'] or 'Not set'}")
    lines += ['', '## Participant influence estimates', '']
    for person in data.get('influence', []):
        lines.append(f"- {label(person.get('participant') or person.get('speaker_id'))}: {person.get('influence_score', person.get('score'))} / 1")
        lines.extend('  - ' + text for text in person.get('explanation', []))
    lines += ['', '## Presentation', '']
    for slide in data.get('slides', []):
        lines.append(f"- {slide['slide_id']}: {slide.get('title') or ''}")
    for flag in data.get('consistency_checks', {}).get('flags', []):
        lines.append(f"- Review {flag['slide_id']}: spoken {flag['spoken_value']} vs slide {flag['slide_value']} {flag['unit']}")
    lines += ['', '## Full transcript', '']
    for s in segments:
        lines.append(f"[{stamp(s['start'])} – {stamp(s['end'])}] {label(s['speaker'])}: {s['text']}")
    return '\n'.join(lines) + '\n', 'text/markdown' if format == 'md' else 'text/plain'
