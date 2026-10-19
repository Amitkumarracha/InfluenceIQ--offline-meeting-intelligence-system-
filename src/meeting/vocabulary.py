"""Editable vocabulary suggestions from observed transcript words, not invented names."""
from collections import Counter
from functools import lru_cache
import re
import unicodedata
from src.utils.text import words
from src.meeting.search import STOPWORDS

COMMON = STOPWORDS | set('i we you they he she it my our your their have has had will would could should can may might not yes no so but as at by with from be been being if then there here also just very really now get got going want think know like okay ok right yeah well um uh thank thanks all some one two see say said make need use used good time today tomorrow send report meeting discussion'.split()) | set('है हैं हूँ हूं था थी थे हो में से के की का को और पर यह वह हम मैं आप नहीं भी तो लिए एक क्या करना करेंगे करना main mai mein hum aap hai hain ho ka ki ke ko se aur nahi haan toh bhi kar karo karna karenge'.split())


VOCABULARY_VERSION = 2
COMMON |= set('actually basically probably usually already always almost another around because before after between both each every everything everyone anything something someone nothing things thing lot lots kind sort point maybe much many more most less only over under into about again still even first next last please let lets dont doesnt didnt thats its were been sure happen happening talking talk tells tell told look looking really people person different important possible example part question answer understand understood correct exactly means meaning whatever whenever anywhere alright hmm ah matlab mtlb bas acha achha accha thik theek ji toh to fir phir ab jab tab kyunki kyonki humko mujhe tum tumhe tumko unko isko usko isliye wala wali wale kuch sab bahut thoda hoga hogi honge tha thi the kiya kiye karte karta karti rahi raha rahe raha gaya gayi gaye hai हैं कुछ सब बहुत अब फिर क्योंकि होगा होगी होंगे करते करता करती रहा रहे रही गया गई गए अपने अपनी अपना इस उस जैसे लेकिन अगर जब तक'.split())
DOMAIN = set('budget latency throughput deployment database migration architecture infrastructure kubernetes docker python java javascript android whisper onnx diarization transcription hinglish hindi english वित्तीय बजट हिंदी अंग्रेजी परियोजना तकनीकी'.split())


def suggest_vocabulary(segments, limit=20, slide_text=()):
    return list(_suggest(tuple(segment.get('text', '') for segment in segments), limit, tuple(slide_text)))


@lru_cache(maxsize=16)
def _suggest(texts, limit, slide_text):
    counts = Counter(term for text in texts for term in words(text)
                     if len(term) >= 3 and not term.isdigit() and term not in COMMON)
    slide_terms = set(term for text in slide_text for term in words(text)) - COMMON
    acronyms, names, spelling = set(), set(), {}
    # Preserve observed acronym spelling. A capital at the start of a sentence
    # alone is not evidence of a person's or product's name.
    for text in texts:
        for index, token in enumerate(re.findall(r"[^\W_]+", unicodedata.normalize('NFKC', text), re.UNICODE)):
            key = token.casefold()
            if token.isupper() and token.isalpha() and 2 <= len(token) <= 10 and key not in COMMON:
                acronyms.add(key); spelling[key] = token
                counts[key] = max(1, counts[key])
            elif index > 0 and token[:1].isupper() and token[1:] != token[1:].lower() and key not in COMMON:
                names.add(key); spelling[key] = token
            elif index > 0 and token.istitle() and key not in COMMON:
                names.add(key)
    scored = []
    for term, count in counts.items():
        acronym = term in acronyms
        named = term in names and count >= 2
        technical = term in DOMAIN or any(char.isdigit() for char in term) and any(char.isalpha() for char in term)
        on_slide = term in slide_terms
        if not (acronym or named or technical or on_slide):
            continue
        score = (5 if acronym else 0) + (3 if named else 0) + (3 if technical else 0) + (4 if on_slide else 0) + min(count, 3)
        scored.append((-score, -count, term))
    return tuple(spelling.get(term, term) for _, _, term in sorted(scored)[:max(0, limit)])
