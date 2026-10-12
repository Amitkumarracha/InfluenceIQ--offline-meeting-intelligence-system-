"""Regression coverage for batched fusion, model reuse and complete evaluation inputs."""
import json
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import pytest


def test_batched_scores_preserve_cosine_and_blank_passages_across_batches():
    from src.fusion.semantic_alignment import compute_semantic_scores, iter_semantic_scores
    vectors = {'alpha': [1., 2., 0.], 'beta': [-1., 0., 3.], '': [9., 9., 9.]}
    model = SimpleNamespace(encode=lambda texts, **kw: np.asarray([vectors[text] for text in texts], dtype=np.float32),
                            get_sentence_embedding_dimension=lambda: 3)
    keys = np.asarray([[1., 1., 1.], [0., 0., 0.], [-1., 3., 2.]], dtype=np.float32)
    texts = ['alpha', '', 'beta', 'alpha', 'beta']
    scalar = np.asarray([[score.score for score in compute_semantic_scores(text, ['a','b','c'], keys, model)] for text in texts])
    batched = np.asarray(list(iter_semantic_scores(texts, keys, model, batch_size=2)))
    np.testing.assert_allclose(scalar, batched, atol=1.1e-6)
    assert np.array_equal(batched[1], [0, 0, 0])
    assert np.array_equal(batched[:,1], np.zeros(len(texts)))


def test_model_reuse_respects_device_and_model_changes(monkeypatch):
    from src.audio.asr import _cached_whisper_model, _load_whisper_model
    _cached_whisper_model.cache_clear()
    try:
        with patch('faster_whisper.WhisperModel', side_effect=lambda *a, **kw: object()) as constructor:
            monkeypatch.setenv('MAI_ASR_DEVICE', 'cpu')
            monkeypatch.setenv('MAI_ASR_COMPUTE_TYPE', 'int8')
            first = _load_whisper_model('small')
            assert _load_whisper_model('small') is first
            assert _load_whisper_model('medium') is not first
            monkeypatch.setenv('MAI_ASR_DEVICE', 'cuda')
            monkeypatch.setenv('MAI_ASR_COMPUTE_TYPE', 'float16')
            _load_whisper_model('medium')
            assert constructor.call_count == 3
            assert constructor.call_args.kwargs['device'] == 'cuda'
    finally:
        _cached_whisper_model.cache_clear()


def test_evaluation_runner_reads_non_event_speech_and_alignment(tmp_path, monkeypatch):
    from scripts import run_evaluation
    from tests.test_evaluation import _pipeline_data
    from src.meeting.events import save_events_json
    from src.meeting.evidence import save_evidence_json
    from src.meeting.decisions import save_decisions_json
    from src.meeting.interaction import save_interactions_json
    from src.meeting.influence import compute_influence, save_influence_json
    er, ev, dr, ir = _pipeline_data()
    root = tmp_path / 'data/processed'
    for name, result, saver in [('events', er, save_events_json), ('events', ev, save_evidence_json),
                               ('decisions', dr, save_decisions_json), ('interactions', ir, save_interactions_json),
                               ('influence', compute_influence(er,ev,dr,ir), save_influence_json)]:
        suffix = 'evidence' if result is ev else name
        target = root/name/f'test_{suffix}.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        saver(result, target)
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
    write(root/'audio/test_transcript.json', {'segments': [{'text': 'ordinary speech without any event'}], 'duration': 5})
    write(root/'audio/test_diarization.json', {'segments': [{'start':0,'end':5,'speaker':'A'}]})
    write(root/'alignment/test_alignment.json', {'segments': [{'segment_id':99,'selected_slide':'s99'}]})
    annotations=tmp_path/'annotations.json'
    write(annotations, {'transcript_ground_truth': 'ordinary speech without any event',
        'speaker_ground_truth':[{'start':0,'end':5,'speaker':'A'}],
        'alignment_ground_truth':[{'segment_id':99,'slide_id':'s99'}],
        'decision_ground_truth':[{'topic': d.topic,'status':d.status,'timestamp':0} for d in dr.decisions]})
    out=tmp_path/'evaluation'
    monkeypatch.setattr(run_evaluation,'PROJECT_ROOT',tmp_path)
    monkeypatch.setattr(run_evaluation,'parse_args',lambda:SimpleNamespace(meeting_id='test',output_dir=str(out),annotations=str(annotations),ablation=True,stage_timings=None,audio_duration=None))
    run_evaluation.main()
    metrics=json.loads((out/'test_metrics.json').read_text())
    assert metrics['wer']['wer'] == 0
    assert metrics['der']['der'] == 0
    assert metrics['alignment']['f1'] == 1
    assert metrics['decisions']['status'] == 'ok'
    assert (out/'test_comparison.csv').exists()
    assert (out/'test_ablation.json').exists()


def test_batched_alignment_exports_native_json_numbers():
    from dataclasses import asdict
    from src.audio.asr import TranscriptSegment
    from src.fusion.multimodal_representation import align_segment
    from src.fusion.temporal_alignment import SlideTimingInfo
    result = align_segment(TranscriptSegment(1,0,5,'A','topic'), ['s1'], [SlideTimingInfo('s1')],
        np.ones((1,3),dtype=np.float32), None, 3, .5, .5, .3,
        precomputed_scores={'s1':np.float32(.8)})
    serialized = json.loads(json.dumps(asdict(result)))
    assert serialized['selected_slide'] == 's1'
    assert serialized['slide_candidates'][0]['semantic_score'] == pytest.approx(.8)


def test_missing_predictions_are_errors_and_missing_annotation_path_fails(tmp_path, monkeypatch):
    from scripts import run_evaluation
    with pytest.raises(FileNotFoundError):
        run_evaluation._load_annotations(str(tmp_path/'missing.json'))
    ann=tmp_path/'annotations.json'
    ann.write_text(json.dumps({'transcript_ground_truth':'hello',
        'speaker_ground_truth':[{'start':0,'end':1,'speaker':'A'}],
        'alignment_ground_truth':[{'segment_id':1,'slide_id':'s1'}]}))
    monkeypatch.setattr(run_evaluation,'PROJECT_ROOT',tmp_path)
    out=tmp_path/'results'
    monkeypatch.setattr(run_evaluation,'parse_args',lambda:SimpleNamespace(meeting_id='missing',output_dir=str(out),annotations=str(ann),ablation=False,stage_timings=None,audio_duration=None))
    run_evaluation.main()
    metrics=json.loads((out/'missing_metrics.json').read_text())
    assert all(metrics[key]['status'] == 'error' for key in ['wer','der','alignment'])
