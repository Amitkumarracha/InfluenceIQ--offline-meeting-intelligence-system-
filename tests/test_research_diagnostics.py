import pytest

from src.evaluation.diagnostics import character_error_rate, diarization_diagnostics, score_sensitivity


def test_character_error_counts_unicode_and_does_not_invent_missing_references():
    assert character_error_rate('हिंदी, TEAM!', 'हिंदी team')['cer'] == 0
    assert character_error_rate('abc', 'axc')['cer'] == pytest.approx(1 / 3, abs=1e-6)
    assert character_error_rate(None, 'hello')['status'] == 'ground_truth_unavailable'


def test_evaluation_cli_includes_new_metrics_and_keeps_human_labels_missing(tmp_path, monkeypatch):
    import json
    import scripts.run_evaluation as cli
    folder = tmp_path / 'data/processed/audio'; folder.mkdir(parents=True)
    (folder / 'trial_transcript.json').write_text(json.dumps({'duration': 4, 'segments': [
        {'text': 'hello team', 'speaker': 'X', 'start': 0, 'end': 2}]}))
    (folder / 'trial_diarization.json').write_text(json.dumps({'segments': [
        {'start': 0, 'end': 2, 'speaker': 'X'}]}))
    annotations = tmp_path / 'truth.json'
    annotations.write_text(json.dumps({'transcript_ground_truth': 'hello team',
        'speaker_ground_truth': [{'start': 0, 'end': 2, 'speaker': 'A'}]}))
    monkeypatch.setattr(cli, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr('sys.argv', ['run_evaluation.py', '--meeting-id', 'trial',
        '--annotations', str(annotations), '--output-dir', str(tmp_path / 'results')])
    cli.main()
    result = json.loads((tmp_path / 'results/trial_metrics.json').read_text())
    assert result['cer']['cer'] == 0 and result['audio_diagnostics']['jer'] == 0
    assert result['audio_diagnostics']['speech_f1'] == 1
    assert result['influence']['status'] == 'ground_truth_unavailable'


def test_permuted_labels_have_zero_jer_and_perfect_speech_detection():
    ref = [{'start': 0, 'end': 2, 'speaker': 'A'}, {'start': 1, 'end': 3, 'speaker': 'B'}]
    hyp = [{**row, 'speaker': {'A': 'X', 'B': 'Y'}[row['speaker']]} for row in ref]
    result = diarization_diagnostics(ref, hyp, 4, collar=0)
    assert result['jer'] == 0 and result['speech_f1'] == 1
    assert result['speaker_count_absolute_error'] == 0


def test_missing_speech_and_extra_clusters_are_not_hidden():
    ref = [{'start': 0, 'end': 2, 'speaker': 'A'}]
    missed = diarization_diagnostics(ref, [], 4, collar=0)
    assert missed['jer'] == 1 and missed['speech_f1'] == 0
    hyp = [{'start': 0, 'end': 2, 'speaker': 'X'}, {'start': 2, 'end': 4, 'speaker': 'Y'}]
    result = diarization_diagnostics(ref, hyp, 4, collar=0)
    assert result['speech_precision'] == .5 and result['speech_recall'] == 1
    assert result['speaker_count_absolute_error'] == 1
    assert diarization_diagnostics(None, hyp, 4)['status'] == 'ground_truth_unavailable'
    with pytest.raises(ValueError):
        diarization_diagnostics(ref, hyp, float('nan'))


def test_sensitivity_is_not_accuracy_and_requires_same_clusters():
    result = score_sensitivity({'A': .4, 'B': 0}, {'A': .8, 'B': 0})
    assert result['changed_scores'] == 1 and result['mean_absolute_score_change'] == .2
    assert result['human_accuracy_status'] == 'ground_truth_unavailable'
    assert score_sensitivity({'A': 1}, {'B': 1})['status'] == 'incomparable_participant_sets'
    with pytest.raises(ValueError):
        score_sensitivity({'A': float('nan')}, {'A': 1})
