"""ASR observations plus explicit script/romanized-Hindi cues; no invented percentages."""
from src.utils.text import words

HINDI_CUES = set('main mein mai hum humne aap tum hai hain ho hoon hun kya kyun kaise kab kaun nahi nahin kal kar karna karenge karunga karungi dunga dena chahiye tay faisla sehmat mera matlab gaya'.split())


def language_profile(segments, asr_languages=()):
    tokens = list(words(' '.join(s.get('text', '') for s in segments)))
    devanagari = sum(any('\u0900' <= c <= '\u097f' for c in word) for word in tokens)
    latin = [word for word in tokens if any('a' <= c <= 'z' for c in word)]
    hindi_cues = sorted(set(latin) & HINDI_CUES)
    observed = sorted({code for code in asr_languages if code})
    romanized = len(hindi_cues) >= 2
    if (devanagari or romanized) and any(word not in HINDI_CUES for word in latin):
        label = 'Possible Hindi–English mix'
    elif devanagari or romanized:
        label = 'Hindi cues observed'
    elif observed == ['en']:
        label = 'English detected'
    elif observed == ['hi']:
        label = 'Hindi detected'
    elif len(observed) > 1:
        label = 'Multiple ASR languages observed'
    else:
        label = 'Language not established' if not tokens else 'Latin-script transcript'
    return {'label': label, 'asr_languages': observed,
            'devanagari_words': devanagari, 'latin_script_words': len(latin),
            'romanized_hindi_cues': hindi_cues,
            'method': 'ASR chunk-language observations and transcript script/word cues',
            'limitations': 'Script/word cues are heuristic; they do not measure code-switching accuracy or language percentages.'}
