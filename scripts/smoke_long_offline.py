"""Long-duration regression: two hours of silence followed by real speech.
This tests timestamp/memory/offline handling, not two-hour meeting accuracy.
"""
import json
import resource
import socket
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import soundfile as sf
from src.utils.config import PROJECT_ROOT
from src.utils.cache import atomic_json
from src.pipeline.orchestrator import run_meeting


def main():
    source = PROJECT_ROOT / '.runtime/validation/ami_90s.wav'
    if not source.exists():
        raise SystemExit('Create the AMI 90-second validation clip first (see PROJECT_STATUS.md).')
    path = source.parent / 'two_hours_then_speech.wav'
    silence = np.zeros(16000 * 60, dtype=np.int16)
    with sf.SoundFile(path, 'w', samplerate=16000, channels=1, subtype='PCM_16') as out:
        for _ in range(120):
            out.write(silence)
        with sf.SoundFile(source) as audio:
            for block in audio.blocks(blocksize=16000 * 30, dtype='int16'):
                out.write(block)
    attempts = []
    original = socket.socket.connect
    def deny(self, address):
        attempts.append(str(address))
        raise RuntimeError('Network access disabled by offline smoke test')
    socket.socket.connect = deny
    started = time.perf_counter()
    try:
        report = run_meeting(path, 'two_hour_offline_validation', diarization='off')
    finally:
        socket.socket.connect = original
    data = json.loads(report.read_text())
    segments = data['transcript_segments']
    assert not attempts, attempts
    assert segments, 'Real speech after silence must be recognized'
    assert all(s['start'] >= 7198 and s['end'] <= 7290 for s in segments), 'Silence hallucination or timestamp corruption'
    result = {'duration_s': 7290, 'elapsed_s': round(time.perf_counter() - started, 3),
              'network_connect_attempts': len(attempts), 'transcript_segments': len(segments),
              'first_segment_start': segments[0]['start'],
              'peak_rss_mb': round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
              'passed': True, 'limitation': 'Synthetic long silence plus 90 seconds of English AMI speech; not long-meeting accuracy validation.'}
    atomic_json(PROJECT_ROOT / 'outputs/evaluation/two_hour_offline_smoke.json', result)
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
