"""Conservative aligned quantity-mismatch flags, requiring human review."""
import re
from decimal import Decimal
from src.meeting.search import STOPWORDS
from src.utils.text import normalize_text, words

QUANTITY = re.compile(r'(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>%|percent\b|प्रतिशत|milliseconds?\b|ms\b|seconds?\b|sec\b|hours?\b|days?\b|दिन|घंटे|usd\b|inr\b|rupees?\b)', re.I)
UNITS = {'percent': '%', 'प्रतिशत': '%', 'millisecond': 'ms', 'milliseconds': 'ms', 'seconds': 'sec', 'second': 'sec', 'hours': 'hour', 'घंटे': 'hour', 'days': 'day', 'दिन': 'day', 'rupee': 'inr', 'rupees': 'inr'}
IGNORE = STOPWORDS | set('data report according slide shown shows value values test tests measured result results current new old ms sec hour day percent inr usd is was the our we it has have of at by for and according'.split())


def quantities(text):
    found = {}
    for match in QUANTITY.finditer(normalize_text(text)):
        unit = UNITS.get(match['unit'], match['unit'])
        found.setdefault(unit, set()).add(Decimal(match['value']))
    return found


def check_consistency(segments, slides):
    index = {s['slide_id']: s for s in slides}
    flags = []
    for segment in segments:
        slide = index.get(segment.get('slide_id'))
        if not slide:
            continue
        claims = quantities(segment.get('text', ''))
        if not claims:
            continue
        blocks = [slide.get('title') or '', *slide.get('text', [])]
        blocks += [' '.join(row) for table in slide.get('tables', []) for row in table.get('rows', [])]
        claim_words = set(words(segment['text'])) - IGNORE
        for block in blocks:
            shared = sorted(claim_words & (set(words(block)) - IGNORE))
            if not any(not term.isdigit() for term in shared):
                continue
            for unit, values in quantities(block).items():
                spoken = claims.get(unit, set())
                # ponytail: only unambiguous same-unit values with shared lexical context;
                # no entity/coreference resolution or semantic contradiction guarantee.
                if len(spoken) == len(values) == 1 and spoken != values:
                    flags.append({'segment_id': segment['segment_id'], 'speaker': segment.get('speaker'),
                        'start': segment.get('start'), 'slide_id': slide['slide_id'],
                        'statement': segment['text'], 'slide_text': block, 'shared_terms': shared,
                        'spoken_value': str(next(iter(spoken))), 'slide_value': str(next(iter(values))),
                        'unit': unit, 'kind': 'possible_quantity_mismatch', 'requires_review': True})
    return {'method': 'Same-unit quantity comparison on aligned statements with shared lexical context',
            'status': 'checked' if slides else 'no_presentation', 'flags': flags,
            'limitations': 'Flags can compare different quantities. An empty list does not establish consistency; semantic and visual contradictions are not evaluated.'}
