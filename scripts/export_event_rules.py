"""Export our shared phrase rules for Android; no models/downloads needed."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.meeting.events import _PATTERNS, _BILINGUAL_PATTERNS
from src.meeting.language_rules import BLOCKERS


def main():
    directory = Path(__file__).resolve().parents[1] / 'android/app/src/main/assets'
    directory.mkdir(parents=True, exist_ok=True)
    patterns = {key: [p.pattern for p in bank] + [p.pattern for p in _BILINGUAL_PATTERNS.get(key, [])]
                for key, bank in _PATTERNS.items()}
    for name, data in [('event_patterns.json', patterns), ('event_blockers.json', BLOCKERS)]:
        (directory / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
