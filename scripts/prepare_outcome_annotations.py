"""Export source-linked candidates with blank references for independent annotation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.meeting.events import load_events_json
from src.meeting.decisions import load_decisions_json
from src.meeting.outcomes import outcome_candidates


def export(events_path, decisions_path, output):
    events, decisions = load_events_json(events_path), load_decisions_json(decisions_path)
    if events.meeting_id != decisions.meeting_id:
        raise ValueError('Event and decision meeting IDs must match')
    rows = outcome_candidates(events, decisions)
    if not rows:
        raise ValueError('No source-linked contribution candidates were found')
    if output.exists() or output.with_suffix('.provenance.json').exists():
        raise ValueError('Refusing to overwrite annotation work')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False)+'\n')
    provenance = {'status': 'Unlabelled candidates, not training references', 'rows': len(rows),
                  'sources': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in [events_path, decisions_path]}}
    output.with_suffix('.provenance.json').write_text(json.dumps(provenance, indent=2))
    return provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--events', type=Path, required=True)
    parser.add_argument('--decisions', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.events, args.decisions, args.output), indent=2))


if __name__ == '__main__':
    main()
