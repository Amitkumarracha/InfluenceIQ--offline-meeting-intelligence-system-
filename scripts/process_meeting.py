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
    args = p.parse_args()
    print(run_meeting(args.audio, args.meeting_id, args.ppt, args.diarization,
                      progress=lambda stage, details=None: print('Stage:', stage, details or '', flush=True)))
