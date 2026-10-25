"""Run every stage with resumable ASR; no server is needed."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.pipeline.orchestrator import run_meeting

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audio', required=True)
    p.add_argument('--meeting-id', required=True)
    p.add_argument('--ppt')
    p.add_argument('--diarization', choices=['auto', 'required', 'off'], default='auto')
    p.add_argument('--topic-aware', action='store_true', help='Experimental semantic decision grouping')
    p.add_argument('--outcome-links', action='store_true', help='Save source-linked outcome candidates for annotation')
    p.add_argument('--outcome-model', help='Directory of an independently trained outcome-relation model')
    p.add_argument('--speaker-margin', type=float, default=0., help='Abstain when overlapping speaker coverage is too close')
    p.add_argument('--num-speakers', type=int, help='Known actual speaker count for diarization')
    p.add_argument('--event-model', help='Optional trained English contextual contribution-role directory')
    p.add_argument('--discussion-model', help='Optional trained contextual discussion directory')
    p.add_argument('--ranker-model', help='Optional frozen research ranker directory; exports separate ranking margins')
    args = p.parse_args()
    if not 0 <= args.speaker_margin <= 1:
        p.error('--speaker-margin must lie in [0, 1]')
    if args.num_speakers is not None and args.num_speakers < 1:
        p.error('--num-speakers must be positive')
    print(run_meeting(args.audio, args.meeting_id, args.ppt, args.diarization,
                      progress=lambda stage, details=None: print('Stage:', stage, details or '', flush=True),
                      options={key: value for key, value in vars(args).items()
                               if key in {'topic_aware', 'outcome_links', 'outcome_model', 'speaker_margin', 'num_speakers', 'event_model', 'discussion_model', 'ranker_model'} and value is not None}))
