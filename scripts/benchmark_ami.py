"""Reproducible AMI excerpt benchmark, using manual annotations as reference."""
import argparse
import json
import re
import resource
import subprocess
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.utils.config import PROJECT_ROOT, get
from src.utils.cache import atomic_json
from src.pipeline.orchestrator import run_meeting
from src.evaluation.metrics import calculate_wer


def normalize(text):
    text = unicodedata.normalize('NFKC', text).lower()
    return ' '.join(''.join(c if c.isalnum() or c.isspace() or unicodedata.category(c).startswith('M') else ' ' for c in text).split())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--meeting', default='ES2002a')
    p.add_argument('--start', type=float, default=30)
    p.add_argument('--seconds', type=float, default=90)
    p.add_argument('--channel', default='Array1-01')
    p.add_argument('--tag', default='', help='Optional identifier suffix for a fresh comparison')
    args = p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.meeting) or not re.fullmatch(r'[A-Za-z0-9_-]+', args.channel):
        p.error('Invalid meeting or channel')
    root = PROJECT_ROOT / 'AMI_dataset'
    audio = root / 'audio' / args.channel / args.meeting / 'audio' / f'{args.meeting}.{args.channel}.wav'
    annotations = root / 'annotations/ami_public_manual_1.6.2/words'
    words = []
    for file in sorted(annotations.glob(f'{args.meeting}.*.words.xml')):
        for word in ET.parse(file).getroot():
            if word.tag.rsplit('}', 1)[-1] != 'w' or word.get('punc') == 'true':
                continue
            start = float(word.get('starttime', -1))
            if args.start <= start < args.start + args.seconds and word.text:
                words.append((start, word.text))
    if not words:
        raise SystemExit('Manual reference words unavailable for this window')
    work = PROJECT_ROOT / '.runtime' / 'validation'
    work.mkdir(parents=True, exist_ok=True)
    mid = f'benchmark_{args.meeting}_{int(args.start)}_{int(args.seconds)}_{get("asr.model_size")}'
    if args.tag:
        if not re.fullmatch(r'[A-Za-z0-9_-]+', args.tag):
            p.error('Invalid benchmark tag')
        mid += '_' + args.tag
    clip = work / f'{mid}.wav'
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', str(args.start), '-t', str(args.seconds),
                    '-i', str(audio), '-ar', '16000', '-ac', '1', str(clip)], check=True)
    started = time.perf_counter()
    report_path = run_meeting(clip, mid, diarization='off')
    elapsed = time.perf_counter() - started
    report = json.loads(report_path.read_text())
    reference = normalize(' '.join(word for _, word in sorted(words)))
    hypothesis = normalize(' '.join(s['text'] for s in report['transcript_segments']))
    result = {'dataset': 'AMI manual 1.6.2', 'meeting': args.meeting, 'channel': args.channel,
              'start_s': args.start, 'duration_s': args.seconds, 'asr_model': get('asr.model_size'),
              'device': 'cpu', 'compute_type': 'int8', 'elapsed_s': round(elapsed, 3),
              'real_time_factor': round(elapsed / args.seconds, 4),
              'process_peak_rss_mb': round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
              'wer': calculate_wer(reference, hypothesis),
              'reference': reference, 'hypothesis': hypothesis,
              'limitations': ['Single English AMI meeting; not Hindi/English accuracy evidence',
                              'Overlapping reference words ordered by time',
                              'NFKC, lowercase, punctuation-to-spaces normalization',
                              'Elapsed time may include cache reuse on repeat runs',
                              'Speaker separation unavailable; DER not evaluated']}
    output = PROJECT_ROOT / 'outputs' / 'evaluation' / f'{mid}_benchmark.json'
    atomic_json(output, result)
    print(json.dumps({k: v for k, v in result.items() if k not in {'reference', 'hypothesis'}}, indent=2))
    print(output)

if __name__ == '__main__':
    main()
