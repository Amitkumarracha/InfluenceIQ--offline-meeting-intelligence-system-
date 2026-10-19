"""Names from explicit self-introductions only; never infer identity from the voice."""
import re
from src.utils.text import words

PATTERNS = [
    re.compile(r"(?:^|[.!?]\s*)my name is\s+([a-z][a-z'’ -]{1,70}?)(?=\s+(?:and|from|with|here)\b|[.,!?]|$)", re.I),
    re.compile(r'(?:^|[।.!?]\s*)मेरा नाम\s+([^।.!?,\n]{1,70}?)\s+है(?:[।.!?,]|\s|$)'),
    re.compile(r'(?:^|[.!?]\s*)mera (?:naam|nam)\s+([a-z][a-z -]{1,70}?)\s+(?:hai|h)(?:[.!?,]|\s|$)', re.I),
]
NOT_NAMES = set('a an the engineer developer student teacher manager director researcher doctor volunteer unknown test example user speaker research software this that my your his her मेरा नाम'.split())


def self_introductions(segments):
    candidates = {}
    for segment in segments:
        speaker = segment.get('speaker')
        if not speaker or speaker == 'UNKNOWN':
            continue
        for pattern in PATTERNS:
            match = pattern.search(segment.get('text', '').strip())
            if not match:
                continue
            name = ' '.join(match.group(1).split())
            tokens = list(words(name))
            if not 1 <= len(tokens) <= 3 or any(token in NOT_NAMES or any(char.isdigit() for char in token) for token in tokens):
                continue
            candidates.setdefault(speaker, {})[name.casefold()] = {
                'name': name, 'method': 'explicit_self_introduction', 'requires_review': True,
                'segment_id': segment.get('segment_id'), 'start': segment.get('start'),
                'source_text': segment.get('text', '')}
    # Conflicting introductions abstain instead of choosing a likely person.
    return {speaker: next(iter(names.values())) for speaker, names in candidates.items() if len(names) == 1}
