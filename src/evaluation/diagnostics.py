"""Complementary audio errors and unlabelled ablation sensitivity diagnostics."""
import math


def character_error_rate(reference, hypothesis):
    """Strict NFKC/casefold Unicode CER, excluding whitespace and punctuation."""
    from src.evaluation.metrics import calculate_wer
    from src.utils.text import words
    if reference is None:
        return {'status': 'ground_truth_unavailable', 'metric': 'cer'}
    ref = ' '.join(''.join(words(reference)))
    hyp = ' '.join(''.join(words(hypothesis or '')))
    result = calculate_wer(ref, hyp)
    result['metric'] = 'cer'
    if 'wer' in result:
        result['cer'] = result.pop('wer')
    result['unit'] = 'Unicode code point after NFKC/casefold, excluding punctuation and spaces'
    return result


def diarization_diagnostics(reference, hypothesis, duration, collar=.25):
    """JER and speech-region PRF on the same UEM; no inference or label fitting."""
    if not reference:
        return {'status': 'ground_truth_unavailable'}
    if not math.isfinite(duration) or duration <= 0 or collar < 0:
        raise ValueError('Use a positive finite duration and nonnegative collar')
    from pyannote.core import Annotation, Segment, Timeline
    from pyannote.metrics.diarization import JaccardErrorRate
    from pyannote.metrics.detection import DetectionPrecisionRecallFMeasure

    def annotation(rows):
        output = Annotation()
        for i, row in enumerate(rows or []):
            if not all(math.isfinite(row[k]) for k in ('start', 'end')):
                raise ValueError('Segment times must be finite')
            start, end = max(0, row['start']), min(duration, row['end'])
            if end > start:
                output[Segment(start, end), i] = str(row['speaker'])
        return output

    ref, hyp = annotation(reference), annotation(hypothesis)
    if not ref:
        return {'status': 'ground_truth_unavailable'}
    uem = Timeline([Segment(0, duration)])
    jer = JaccardErrorRate(collar=collar, skip_overlap=False)(ref, hyp, uem=uem, detailed=True)
    speech = DetectionPrecisionRecallFMeasure(collar=collar, skip_overlap=False)(ref, hyp, uem=uem, detailed=True)
    retrieved, relevant, correct = (speech[k] for k in ('retrieved', 'relevant', 'relevant retrieved'))
    precision = correct / retrieved if retrieved else 0
    recall = correct / relevant if relevant else 0
    return {'status': 'ok', 'jer': jer['jaccard error rate'],
            'jer_speaker_count': jer['speaker count'], 'jer_speaker_error': jer['speaker error'],
            'speech_precision': precision, 'speech_recall': recall,
            'speech_f1': 2 * precision * recall / (precision + recall) if precision + recall else 0,
            'speech_retrieved_seconds': retrieved, 'speech_reference_seconds': relevant,
            'speech_correct_seconds': correct, 'reference_speakers': len(ref.labels()),
            'hypothesis_speakers': len(hyp.labels()),
            'speaker_count_absolute_error': abs(len(ref.labels()) - len(hyp.labels())),
            'duration_seconds': duration, 'collar_seconds': collar, 'overlap_included': True}


def score_sensitivity(scores, control):
    """Changes versus a model control, explicitly not human-grounded accuracy."""
    if not scores or not control:
        return {'status': 'input_unavailable'}
    if any(not math.isfinite(value) for value in [*scores.values(), *control.values()]):
        raise ValueError('Scores must be finite')
    if set(scores) != set(control):
        return {'status': 'incomparable_participant_sets'}
    differences = [abs(scores[speaker] - control[speaker]) for speaker in control]
    return {'status': 'ok', 'clusters': len(scores),
            'nonzero_scores': sum(value > 0 for value in scores.values()),
            'changed_scores': sum(value > 1e-8 for value in differences),
            'mean_absolute_score_change': sum(differences) / len(differences),
            'max_absolute_score_change': max(differences),
            'human_accuracy_status': 'ground_truth_unavailable'}
