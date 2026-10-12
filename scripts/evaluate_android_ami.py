"""Evaluate an exported Android report on a verified AMI excerpt; no model downloads."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.benchmark_ami import normalize
from src.evaluation.metrics import calculate_wer, calculate_der
from src.utils.config import PROJECT_ROOT
from src.utils.cache import atomic_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--audio', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--meeting', default='ES2002a')
    parser.add_argument('--channel', default='Array1-01')
    parser.add_argument('--start', type=float, default=30)
    parser.add_argument('--seconds', type=float, default=20)
    args = parser.parse_args()
    if not args.meeting.replace('_', '').isalnum() or not args.channel.replace('-', '').isalnum():
        parser.error('Invalid AMI identifiers')
    if args.start < 0 or args.seconds <= 0:
        parser.error('Select a positive window')
    report = json.loads(args.report.read_text())
    if not report.get('completed') or abs(report['duration'] - args.seconds) > .01:
        parser.error('The complete report must cover the selected audio duration')
    root = PROJECT_ROOT / 'AMI_dataset'
    source = root / 'audio' / args.channel / args.meeting / 'audio' / f'{args.meeting}.{args.channel}.wav'
    with tempfile.TemporaryDirectory() as temporary:
        clip = Path(temporary) / 'reference-audio.wav'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', str(args.start), '-t', str(args.seconds),
                        '-i', str(source), '-ar', '16000', '-ac', '1', str(clip)], check=True)
        expected, rate = sf.read(clip, dtype='int16'); actual, actual_rate = sf.read(args.audio, dtype='int16')
        if actual_rate != rate or not np.array_equal(expected, actual):
            parser.error('Audio samples do not match the selected AMI excerpt; do not score against a different reference')
    annotations = root / 'annotations/ami_public_manual_1.6.2'
    words, reference_turns = [], []
    for path in sorted((annotations / 'words').glob(f'{args.meeting}.*.words.xml')):
        for word in ET.parse(path).getroot():
            if word.tag.rsplit('}', 1)[-1] == 'w' and word.get('punc') != 'true' and word.text:
                start = float(word.get('starttime', -1))
                if args.start <= start < args.start + args.seconds:
                    words.append((start, word.text))
    for path in sorted((annotations / 'segments').glob(f'{args.meeting}.*.segments.xml')):
        speaker = path.name.split('.')[1]
        for segment in ET.parse(path).getroot():
            start, end = float(segment.get('transcriber_start', -1)), float(segment.get('transcriber_end', -1))
            a, b = max(0, start - args.start), min(args.seconds, end - args.start)
            if b > a:
                reference_turns.append({'start': a, 'end': b, 'speaker': speaker})
    if not words or not reference_turns:
        parser.error('AMI manual word/turn annotations missing')
    reference = normalize(' '.join(word for _, word in sorted(words)))
    hypothesis = normalize(' '.join(segment['text'] for segment in report['transcript_segments']))
    turns = report.get('diarization', {}).get('turns', [])
    hypothesis_turns = [{'start': turn['start'], 'end': turn['end'], 'speaker': str(turn['cluster'])} for turn in turns]
    result = {'dataset': 'AMI public manual 1.6.2', 'meeting': args.meeting, 'channel': args.channel,
              'start_s': args.start, 'duration_s': args.seconds,
              'audio_samples_verified_against_source': True,
              'audio_sha256': hashlib.sha256(args.audio.read_bytes()).hexdigest(),
              'report_sha256': hashlib.sha256(args.report.read_bytes()).hexdigest(),
              'wer': calculate_wer(reference, hypothesis),
              'der_native_turns': calculate_der(reference_turns, hypothesis_turns, collar=.25),
              'der_delivered_passages': calculate_der(reference_turns, [s for s in report['transcript_segments'] if s['speaker'] != 'UNKNOWN'], collar=.25),
              'reference': reference, 'hypothesis': hypothesis, 'reference_turns': reference_turns,
              'limitations': ['Single short English excerpt; not general Android/Hindi/Hinglish accuracy.',
                              'WER reference words ordered by time, including overlap; NFKC/lowercase/punctuation-to-spaces.',
                              'DER uses manual segment transcriber boundaries, optimal label mapping, 0.25s collar and includes overlap.',
                              'Native turn DER and delivered ASR passage DER measure different outputs.',
                              'No physical-phone speed, battery, fusion F1 or influence correlation is measured here.']}
    atomic_json(args.output, result)
    print(json.dumps({key: value for key, value in result.items() if key not in {'reference', 'hypothesis', 'reference_turns'}}, indent=2))


if __name__ == '__main__':
    main()
