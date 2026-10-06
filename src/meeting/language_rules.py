"""Conservative bilingual guards shared with the native Android rule engine."""
BLOCKERS = {
    'decision': [
        r"\b(?:not|never)\s+(?:yet\s+)?(?:decided|agreed|finalized|finalised|settled)\b",
        r"\b(?:haven't|have not|hasn't|has not)\s+(?:yet\s+)?(?:decided|agreed|finalized|finalised)\b",
        r"(?:निर्णय|फैसला|तय|निर्णीत).{0,20}(?:नहीं|नही|नहि)",
        r"(?:नहीं|नही|नहि).{0,20}(?:निर्णय|फैसला|तय)",
        r"\b(?:decide|decided|decision|faisla|tay|final).{0,20}\b(?:nahi|nahin|nai)\b",
        r"^(?:have|has|had|did|do|does|will|can|could|should|would)\b",
        r"^(?:क्या|क्यों|कैसे)|^(?:kya|kyun|kaise)\b",
    ],
    'agreement': [
        r"\b(?:not|never|don't|do not|cannot|can't)\s+(?:really\s+)?agree\b",
        r"(?:सहमत|सही).{0,12}(?:नहीं|नही|नहि)",
        r"\b(?:sehmat|sahmat|sahi).{0,12}\b(?:nahi|nahin|nai)\b",
    ],
    'action_item': [
        r"\b(?:main|mein|mai)\b.{0,50}\b(?:nahi|nahin|nai)\b.{0,25}\b(?:karunga|karungi|dunga|dungi)\b",
        r"मैं.{0,50}(?:नहीं|नही).{0,25}(?:करूँगा|करूंगा|करूँगी|करूंगी|दूंगा|दूँगा|दूंगी|दूँगी)",
    ],
}
