"""Human-reviewed follow-ups, separate from the original extracted evidence."""
from datetime import date, datetime, timedelta, timezone
import hashlib
import math
import re


def action_candidates(data):
    rows = data.get('action_items')
    if not isinstance(rows, list):
        rows = [e for e in data.get('event_timeline', data.get('events', [])) if e.get('event_type') == 'action_item']
    return {row['event_id']: row for row in rows if isinstance(row.get('event_id'), str) and row['event_id']}


def source_start(action):
    value = action.get('start', action.get('timestamp_s', action.get('timestamp')))
    if isinstance(value, str) and re.fullmatch(r'\d+:\d{2}:\d{2}(?:\.\d+)?', value):
        h, m, s = value.split(':')
        value = int(h) * 3600 + int(m) * 60 + float(s)
    return float(value) if not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0 else None


def make_review(action, owner='', due_date='', state='open'):
    if not isinstance(owner, str) or len(owner) > 100 or any(ord(c) < 32 or ord(c) == 127 for c in owner):
        raise ValueError('Use an owner label of up to 100 characters without control characters')
    if not isinstance(state, str) or state not in {'open', 'done', 'dismissed'}:
        raise ValueError('Choose open, done or dismissed')
    if not isinstance(due_date, str):
        raise ValueError('Use a date in YYYY-MM-DD format')
    if due_date:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', due_date):
            raise ValueError('Use a date in YYYY-MM-DD format')
        try:
            parsed = date.fromisoformat(due_date)
            if parsed.year > 9998:
                raise ValueError()
        except ValueError as error:
            raise ValueError('Enter a valid calendar date') from error
    return {'owner': owner.strip(), 'due_date': due_date, 'state': state, 'human_reviewed': True,
            'source_text': action.get('text', ''), 'source_start': source_start(action)}


def active_review(data, action):
    reviews = data.get('action_reviews', {})
    value = reviews.get(action.get('event_id')) if isinstance(reviews, dict) else None
    if not isinstance(value, dict) or value.get('human_reviewed') is not True:
        return None
    if value.get('source_text') != action.get('text', '') or value.get('source_start') != source_start(action):
        return None  # A rerun may assign an old event ID to a different passage.
    try:
        return make_review(action, value.get('owner', ''), value.get('due_date', ''), value.get('state'))
    except (ValueError, TypeError):
        return None


def validate_reviews(data):
    reviews = data.get('action_reviews', {})
    if not isinstance(reviews, dict) or len(reviews) > 5000:
        raise ValueError('Invalid follow-up reviews')
    for event_id, review in reviews.items():
        if not isinstance(event_id, str) or len(event_id) > 200 or not isinstance(review, dict):
            raise ValueError('Invalid follow-up review')
        make_review({}, review.get('owner', ''), review.get('due_date', ''), review.get('state'))
        if review.get('human_reviewed') is not True or not isinstance(review.get('source_text'), str):
            raise ValueError('Invalid review evidence')
        value = review.get('source_start')
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0):
            raise ValueError('Invalid review timestamp')


def calendar_export(data, title, meeting_id):
    """All-day reminders only for reviewed, open tasks with an explicit date."""
    def escape(value):
        value = ''.join(c for c in str(value) if (ord(c) >= 32 and ord(c) != 127) or c in '\r\n')
        return value.replace('\\', '\\\\').replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\\n').replace(';', '\\;').replace(',', '\\,')
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//InfluenceIQ//Offline Follow-ups//EN', 'CALSCALE:GREGORIAN']
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    for event_id, action in action_candidates(data).items():
        review = active_review(data, action)
        if not review or review['state'] != 'open' or not review['due_date']:
            continue
        due = date.fromisoformat(review['due_date'])
        identity = f"{meeting_id}\n{event_id}\n{action.get('text', '')}"
        uid = hashlib.sha256(identity.encode()).hexdigest() + '@influenceiq.local'
        description = f"Meeting: {title}\nOwner: {review['owner'] or 'Unassigned'}\nSource seconds: {source_start(action)}\nUser-reviewed follow-up. Verify the original recording."
        lines += ['BEGIN:VEVENT', 'UID:' + uid, 'DTSTAMP:' + stamp,
                  'DTSTART;VALUE=DATE:' + due.isoformat().replace('-', ''),
                  'DTEND;VALUE=DATE:' + (due + timedelta(days=1)).isoformat().replace('-', ''),
                  'SUMMARY:' + escape(action.get('text', 'Follow-up')),
                  'DESCRIPTION:' + escape(description), 'TRANSP:TRANSPARENT', 'END:VEVENT']
    if 'BEGIN:VEVENT' not in lines:
        raise ValueError('Confirm an open action item and set its due date before exporting a calendar')
    lines.append('END:VCALENDAR')
    folded = []
    for line in lines:
        current, length = '', 0
        for char in line:
            count = len(char.encode('utf-8'))
            if length + count > 75:
                folded.append(current)
                current, length = ' ', 1
            current += char
            length += count
        folded.append(current)
    return '\r\n'.join(folded) + '\r\n'
