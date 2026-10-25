"""Prepare blind rating sheets and an unlabelled training template from saved influence JSON.

This exports predicted speaker IDs, not verified people. Verify the complete
participant roster and give raters the original recording/checked transcript.
No model score is exposed in the rating sheet and no human label is invented.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.train_influence_weights import KEYS

RAW_KEYS = [key + '_contribution' for key in KEYS[:-1]] + ['slide_grounded_contribution']


def prepare(paths, output):
    templates, ratings, diagnostics, seen = [], [], [], set()
    for path in paths:
        data = json.loads(path.read_text(encoding='utf-8'))
        meeting = data['meeting_id']
        if not isinstance(meeting, str) or not meeting.strip() or meeting in seen:
            raise ValueError('Each input must represent a distinct nonempty meeting_id')
        seen.add(meeting)
        participants = data['participants']
        if not participants:
            raise ValueError('Each meeting needs participants; verify the speaker roster first')
        roster = set()
        for row in sorted(participants, key=lambda row: row['participant']):
            speaker = row['participant']
            if not isinstance(speaker, str) or not speaker.strip() or speaker == 'UNKNOWN' or speaker in roster:
                raise ValueError('Each meeting needs distinct, known participant IDs')
            roster.add(speaker)
            features = {key: row['raw_features'][raw] for key, raw in zip(KEYS, RAW_KEYS)}
            if any(isinstance(v, bool) or not isinstance(v, (int, float)) or
                   not math.isfinite(v) or v < 0 for v in features.values()):
                raise ValueError('Raw contributions must be finite nonnegative numbers')
            templates.append({'meeting_id': meeting, 'participant': speaker,
                              'group_id': None, 'split': None, 'label_source': None,
                              'human_score': None, 'features': features})
            for rater in ['R1', 'R2', 'R3']:
                ratings.append({'meeting_id': meeting, 'participant': speaker, 'rater_id': rater,
                                'score_1_to_5': '', 'supporting_timestamps': '', 'outcome_notes': ''})
        active = [key for key, raw in zip(KEYS, RAW_KEYS)
                  if any(row['raw_features'][raw] > 0 for row in participants)]
        diagnostics.append({'meeting_id': meeting, 'predicted_speaker_ids': len(roster),
                            'active_features': active,
                            'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                            'source_path': str(path.resolve())})
    if not diagnostics:
        raise ValueError('At least one saved influence file is required')
    # A new directory prevents accidental replacement of completed annotations.
    output.mkdir(parents=True, exist_ok=False)
    with (output / 'blind_ratings.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(ratings[0]))
        writer.writeheader()
        writer.writerows(ratings)
    (output / 'training_template.jsonl').write_text(
        '\n'.join(json.dumps(row, allow_nan=False) for row in templates) + '\n', encoding='utf-8')
    result = {'status': 'human_annotations_required', 'meetings': diagnostics,
              'participants': len(templates), 'influence_accuracy': None,
              'warning': 'Predicted speaker IDs require roster verification. Saved features remain exploratory; '
                         'zero features and fragmented speakers cannot be repaired by fitting weights.'}
    (output / 'diagnostics.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--influence', type=Path, nargs='+', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.influence, args.output_dir)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(f"Prepared {result['participants']} participant records in {args.output_dir}; human ratings required")


if __name__ == '__main__':
    main()
