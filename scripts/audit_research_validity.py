"""Trace paper weaknesses to saved observations; preserve all reported measurements."""
import difflib
import json
import statistics
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.evaluate_research_audio import reference, START, DURATION
from src.evaluation.metrics import calculate_der, calculate_wer
from src.utils.cache import atomic_json
from src.utils.text import words

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / 'professor_guidelines/evaluation'
MID = 'meeting_9af97509bd1a48739b5736accf903a1e'


def feature_activity(participants):
    keys = sorted({key for row in participants for key in row.get('raw_features', {})})
    return {key: {'nonzero_clusters': sum(row.get('raw_features', {}).get(key, 0) > 0 for row in participants),
                  'raw_total': sum(row.get('raw_features', {}).get(key, 0) for row in participants)} for key in keys}


def scalar_residual(left, right, scale):
    if not left or set(left) != set(right):
        raise ValueError('Comparable nonempty score maps required')
    return max(abs(left[key] - scale * right[key]) for key in left)


def main():
    influence = json.loads((ROOT / f'data/processed/influence/{MID}_influence.json').read_text())
    activity = feature_activity(influence['participants'])
    downstream = EV / 'downstream'
    ablations = json.loads((downstream / f'{MID}_ablation.json').read_text())['ablations']
    baselines = json.loads((downstream / f'{MID}_baselines.json').read_text())['baselines']
    control = ablations[0]['influence_scores']
    b3 = next(row['scores'] for row in baselines if row['baseline'] == 'B3_decision_event_count')
    weights = influence['method']['weights']
    checks = {'proposed_vs_decision_count_scaled': scalar_residual(control, b3, weights['decision']),
              'evidence_ablation_vs_pure_rescaling': scalar_residual(ablations[4]['influence_scores'], control, 1 / (1 - weights['evidence'])),
              'interaction_ablation_vs_pure_rescaling': scalar_residual(ablations[5]['influence_scores'], control, 1 / (1 - weights['interaction']))}
    slides = json.loads((ROOT / f'data/processed/slides/{MID}_slides.json').read_text())['slides']
    meeting = 'TS3007d'
    annotations = ROOT / 'AMI_dataset/annotations/ami_public_manual_1.6.2'
    all_words = []
    for path in sorted((annotations / 'words').glob(meeting + '.*.words.xml')):
        for word in ET.parse(path).getroot():
            if word.tag == 'w' and word.get('punc') != 'true' and word.text:
                start = float(word.get('starttime', -1))
                if 0 <= start < START + DURATION:
                    all_words.extend((start, token) for token in words(word.text))
    all_words.sort()
    first_segment = min(float(segment.get('transcriber_start'))
        for path in (annotations / 'segments').glob(meeting + '.*.segments.xml')
        for segment in ET.parse(path).getroot())
    cache_dir = ROOT / '.runtime/research-evaluation/research_TS3007d_asr_words'
    paths = list(cache_dir.glob('*/*.json'))
    if len(paths) != 1:
        raise ValueError('Inspect cache versions manually before selecting a speech observation file')
    speech = json.loads(paths[0].read_text())
    hyp_words = [(word['start'] + START, token)
        for segment in speech['segments'] for word in segment['words'] for token in words(word['word'])]
    matcher = difflib.SequenceMatcher(None, [w for _, w in all_words], [w for _, w in hyp_words], autojunk=False)
    offsets = []
    for block in matcher.get_matching_blocks():
        if block.size >= 4:
            offsets.extend(all_words[block.a+i][0] - hyp_words[block.b+i][0] for i in range(block.size))
    ref_text, ref_turns = reference(meeting)
    clipped_hypothesis = ' '.join(token for start, token in hyp_words if start >= first_segment)
    sensitivity = {'status': 'post_hoc_sensitivity_only_not_replacement_score',
        'first_segment_absolute_seconds': first_segment, 'first_word_absolute_seconds': all_words[0][0],
        'reference_uncovered_prefix_seconds_within_excerpt': first_segment - START,
        'reported_original_wer': next(row['wer'] for row in json.loads((EV / 'audio_summary.json').read_text())['asr'] if row['meeting'] == meeting),
        'raw_word_observation_wer': calculate_wer(ref_text, ' '.join(token for _, token in hyp_words)),
        'prefix_exclusion_wer': calculate_wer(ref_text, clipped_hypothesis),
        'median_matching_word_offset_seconds': statistics.median(offsets), 'matched_words_for_offset': len(offsets),
        'warning': 'The standard BUT/pyannote UEM covers the whole recording. Excluding this prefix is post-hoc sensitivity, not official scoring or proven reference repair.'}
    first_local = first_segment - START
    for threshold in [.5, .9]:
        saved = json.loads((EV / f'ami_TS3007d_threshold_{threshold}.json').read_text())
        def crop(rows):
            return [{**r, 'start': max(r['start'], first_local) - first_local,
                     'end': r['end'] - first_local} for r in rows if r['end'] > first_local]
        sensitivity[str(threshold)] = {'original_der': saved['der'],
            'prefix_exclusion_der': calculate_der(crop(ref_turns), crop(saved['hypothesis']), duration=DURATION-first_local)}
    result = {'active_features': activity, 'score_residual_checks': checks,
        'slide_count': len(slides), 'slides_with_recorded_timestamps': sum(row.get('start_time') is not None and row.get('end_time') is not None for row in slides),
        'ami_coverage_sensitivity': sensitivity,
        'scope': 'Forensic diagnostics of saved pilot; no original metrics, model configuration or user meeting overwritten'}
    atomic_json(EV / 'research_validity_audit.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
