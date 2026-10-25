"""Diagnostic attribution curve on saved AMI clips using oracle word boundaries."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.audio.asr import attribute_speaker, compute_overlap
from src.utils.cache import atomic_json


def attribution_curve(words, reference_turns, hypothesis, margins=(0., .05, .1, .2)):
    # Speaker IDs are arbitrary; fit one permutation per clip, independent of margin.
    refs = sorted({row['speaker'] for row in reference_turns})
    hyps = sorted({row['speaker'] for row in hypothesis})
    overlap = np.zeros((len(refs), len(hyps)))
    for truth in reference_turns:
        for predicted in hypothesis:
            overlap[refs.index(truth['speaker']), hyps.index(predicted['speaker'])] += compute_overlap(
                truth['start'], truth['end'], predicted['start'], predicted['end'])
    left, right = linear_sum_assignment(-overlap)
    mapping = {hyps[j]: refs[i] for i, j in zip(left, right)}
    results = []
    for margin in margins:
        accepted = correct = 0
        for word in words:
            speaker = attribute_speaker(word['start'], word['end'], hypothesis, min_speaker_margin=margin)
            accepted += speaker != 'UNKNOWN'
            correct += mapping.get(speaker) == word['speaker']
        results.append({'margin': margin, 'words': len(words), 'accepted': accepted, 'correct': correct,
                        'coverage': accepted/len(words) if words else None,
                        'accepted_precision': correct/accepted if accepted else None,
                        'accuracy_unknown_counted_wrong': correct/len(words) if words else None})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve the existing diagnostic')
    from scripts.evaluate_research_audio import reference, SPLITS, START, DURATION
    sources, meetings = {}, []
    for split, names in SPLITS.items():
        for meeting in names:
            path = ROOT/'professor_guidelines/evaluation'/f'ami_{meeting}_threshold_0.9.json'
            sources[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
            saved = json.loads(path.read_text())
            if saved['start'] != START or saved['duration'] != DURATION:
                raise ValueError('Saved diarization must match the reference clip')
            words = []
            for file in sorted((ROOT/'AMI_dataset/annotations/ami_public_manual_1.6.2/words').glob(f'{meeting}.*.words.xml')):
                sources[str(file.relative_to(ROOT))] = hashlib.sha256(file.read_bytes()).hexdigest()
                for word in ET.parse(file).getroot():
                    if word.tag.rsplit('}', 1)[-1] != 'w' or word.get('punc') == 'true' or not word.text:
                        continue
                    start, end = float(word.get('starttime', -1)), float(word.get('endtime', -1))
                    if START <= start < START+DURATION and end > start:
                        words.append({'start': start-START, 'end': min(DURATION, end-START), 'speaker': file.name.split('.')[1]})
            _, turns = reference(meeting)
            meetings.append({'meeting': meeting, 'split': split,
                             'curve': attribution_curve(words, turns, saved['hypothesis'])})
    atomic_json(args.output, {'status': 'Exploratory attribution diagnostic; previously examined clips',
        'limits': ['Oracle word timing; transcription errors are excluded.',
                   'Two development and two historical 120-second English clips; no full-corpus accuracy claim.',
                   'One optimal reference/hypothesis speaker permutation per clip, fixed across margins.',
                   'No default changed from this curve.'], 'source_sha256': sources, 'meetings': meetings})
    print(json.dumps(meetings, indent=2))


if __name__ == '__main__':
    main()
