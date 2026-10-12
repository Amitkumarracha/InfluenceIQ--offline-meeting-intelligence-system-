"""Real offline audio-to-participants/PPT/NLP/influence integration; not an accuracy benchmark."""
import argparse
import json
from pathlib import Path
import socket
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.pipeline.orchestrator import run_meeting


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio', type=Path, required=True)
    parser.add_argument('--ppt', type=Path)
    parser.add_argument('--speakers', type=int)
    parser.add_argument('--id', default='report_scope_smoke')
    args = parser.parse_args()
    calls = []
    def offline(*values, **kwargs):
        calls.append('socket_connection')
        raise AssertionError('Inference attempted a network connection')
    original = socket.socket.connect
    socket.socket.connect = offline
    started = time.perf_counter()
    try:
        path = run_meeting(args.audio, args.id, args.ppt, diarization='required',
                           options={'num_speakers': args.speakers})
    finally:
        socket.socket.connect = original
    report = json.loads(path.read_text())
    assert report['participants'] and report['influence'], 'No attributed participant/influence records'
    assert not report['processing']['generative_ai'] and 'local_notes' not in report
    assert all(s['speaker'] == 'UNKNOWN' or any(p['speaker_id'] == s['speaker'] for p in report['participants']) for s in report['transcript_segments'])
    if args.ppt:
        assert report['slides'] and report['aligned_segments']
    result = {'report': str(path), 'duration_s': report['meeting_overview']['duration_s'],
        'participants': len(report['participants']), 'transcript_passages': len(report['transcript_segments']),
        'events': len(report['event_timeline']), 'decisions': len(report['decisions']),
        'influence_records': len(report['influence']), 'slides': len(report['slides']),
        'confident_slide_links': sum(s['slide_id'] != 'NO_CONFIDENT_SLIDE' for s in report['aligned_segments']),
        'elapsed_s': round(time.perf_counter()-started, 3), 'socket_connections': len(calls),
        'generative_ai': False, 'accuracy_benchmark': False}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
