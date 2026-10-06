"""Unicode transcript search with adjacent turns for context. No extra index/model."""
import math
from src.utils.text import normalize_text, words
from collections import Counter

STOPWORDS = set('a an the is are was were did do does what when who why how to of in on for and or this that me meeting please about'.split())


def tokens(text):
    return [t for t in words(text) if t not in STOPWORDS]


def search_segments(segments, query, limit=20):
    terms = set(tokens(query))
    if not terms:
        return []
    counts = [Counter(tokens(s.get('text', ''))) for s in segments]
    frequency = Counter(t for c in counts for t in c if t in terms)
    ranked = []
    phrase = normalize_text(query).strip()
    for index, (segment, count) in enumerate(zip(segments, counts)):
        score = sum((1 + math.log(count[t])) * math.log(1 + len(segments) / frequency[t]) for t in terms if count[t])
        if phrase and phrase in normalize_text(segment.get('text', '')):
            score += 5
        if score:
            ranked.append((score, index))
    ranked.sort(key=lambda pair: (-pair[0], pair[1]))
    return [{**segments[i], 'score': round(score, 3), 'context': segments[max(0, i - 1):i + 2]}
            for score, i in ranked[:limit]]
