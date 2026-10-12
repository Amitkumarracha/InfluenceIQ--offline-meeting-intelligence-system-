"""Editable vocabulary suggestions from observed transcript words, not invented names."""
from collections import Counter
from src.utils.text import words
from src.meeting.search import STOPWORDS

COMMON = STOPWORDS | set('i we you they he she it my our your their have has had will would could should can may might not yes no so but as at by with from be been being if then there here also just very really now get got going want think know like okay ok right yeah well um uh thank thanks all some one two see say said make need use used good time today tomorrow send report meeting discussion'.split()) | set('है हैं हूँ हूं था थी थे हो में से के की का को और पर यह वह हम मैं आप नहीं भी तो लिए एक क्या करना करेंगे करना main mai mein hum aap hai hain ho ka ki ke ko se aur nahi haan toh bhi kar karo karna karenge'.split())


def suggest_vocabulary(segments, limit=20):
    counts = Counter(term for segment in segments for term in words(segment.get('text', ''))
                     if len(term) >= 3 and not term.isdigit() and term not in COMMON)
    # ponytail: frequency suggestions miss context; users review/edit before reuse.
    return [term for term, _ in counts.most_common(limit)]
