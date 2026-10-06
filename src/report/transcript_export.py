"""Exports derived from the saved report, including the full transcript and local notes."""
import csv
import io


def stamp(seconds, separator='.'):
    ms = max(0, round(float(seconds) * 1000))
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}{separator}{ms % 1000:03d}'


def render_export(data, title, format):
    segments = data.get('transcript_segments', [])
    names = data.get('speaker_names', {})
    if format in {'srt', 'vtt'}:
        entries = ['WEBVTT\n'] if format == 'vtt' else []
        for index, s in enumerate(segments, 1):
            sep = ',' if format == 'srt' else '.'
            speaker = names.get(s['speaker'], s['speaker'])
            text = s['text'].replace('-->', '→')
            entries.append(f"{index}\n{stamp(s['start'], sep)} --> {stamp(s['end'], sep)}\n{speaker}: {text}\n")
        return '\n'.join(entries), 'text/vtt' if format == 'vtt' else 'application/x-subrip'
    if format == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['segment_id', 'start', 'end', 'speaker', 'text'])
        for s in segments:
            row = [s.get('segment_id'), s['start'], s['end'], names.get(s['speaker'], s['speaker']), s['text']]
            writer.writerow(["'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v for v in row])
        return output.getvalue(), 'text/csv'
    if format not in {'txt', 'md'}:
        raise ValueError('Unsupported export format')
    lines = [f'# {title}' if format == 'md' else title, '', 'Draft notes — verify against source audio.', '']
    for warning in data.get('processing', {}).get('warnings', []):
        lines += [warning, '']
    notes = data.get('local_notes', {})
    for key, heading in [('overview', 'Overview'), ('decisions', 'Decision candidates'),
                          ('action_items', 'Action candidates'), ('open_questions', 'Open questions')]:
        if notes.get(key):
            lines += [f'## {heading}', '']
            for item in notes[key]:
                lines += [f"- {item['text']} [{stamp(item['start'])}]",
                          f"  Source: {item['quote']}"]
            lines.append('')
    if not notes:
        lines += ['## Decision candidates', '']
        lines += ['- ' + str(d.get('final_decision', '')) for d in data.get('executive_summary', {}).get('confirmed_decisions', [])]
        lines += ['', '## Action candidates', '']
        lines += ['- ' + str(a.get('text', '')) for a in data.get('action_items', [])]
    lines += ['', '## Full transcript', '']
    for s in segments:
        lines.append(f"[{stamp(s['start'])} – {stamp(s['end'])}] {names.get(s['speaker'], s['speaker'])}: {s['text']}")
    return '\n'.join(lines) + '\n', 'text/markdown' if format == 'md' else 'text/plain'
