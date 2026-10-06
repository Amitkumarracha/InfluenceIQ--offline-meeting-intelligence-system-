"""Checks for storage, Unicode retrieval, conservative events and chunk previews."""
import json
import sys
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import pytest
import soundfile as sf

from src.audio.parts import decode_parts
from src.audio.preprocess import preprocess_audio
from src.audio.asr import run_asr
from src.meeting.events import KeywordEventExtractor
from src.meeting.search import tokens, search_segments
from src.fusion.lexical_alignment import TfidfIndex


def test_decode_parts_is_ordered_atomic_and_reuses_verified_recording(tmp_path):
    paths = [tmp_path / 'one.wav', tmp_path / 'two.wav']
    sf.write(paths[0], np.ones(8000) * .1, 16000, subtype='PCM_16')
    sf.write(paths[1], np.ones(8000) * -.2, 16000, subtype='PCM_16')
    output = tmp_path / 'joined.wav'
    decode_parts(paths, output)
    values, sr = sf.read(output)
    assert sr == 16000 and len(values) == 16000
    assert np.allclose(values[:8000], .1, atol=.0001)
    assert np.allclose(values[8000:], -.2, atol=.0001)
    with patch('src.audio.parts.subprocess.Popen', side_effect=AssertionError('decoded twice')):
        decode_parts(paths, output)
    original = output.read_bytes()
    sf.write(paths[1], np.ones(8000) * .3, 16000, subtype='PCM_16')
    decode_parts(paths, output)
    assert output.read_bytes() != original
    original = output.read_bytes()
    paths[1].write_bytes(b'corrupt audio')
    with pytest.raises(ValueError, match='decoding failed'):
        decode_parts(paths, output)
    assert output.read_bytes() == original  # Prior durable audio survives failure.
    assert not list(tmp_path.glob('*.partial.wav'))
    reused, metadata = preprocess_audio(output, tmp_path / 'duplicate.wav', reuse_normalized=True)
    assert reused == output and metadata.processed_duration == 1
    assert not (tmp_path / 'duplicate.wav').exists()


def test_hindi_combining_marks_remain_whole_words_and_retrieval_does_not_translate():
    assert tokens('हिंदी में रिपोर्ट भेजूँगा।') == ['हिंदी', 'में', 'रिपोर्ट', 'भेजूँगा']
    segments = [{'segment_id': 1, 'text': 'रिपोर्ट भेजूँगा।'},
                {'segment_id': 2, 'text': 'किराया तय किया।'}]
    assert search_segments(segments, 'रिपोर्ट')[0]['segment_id'] == 1
    index = TfidfIndex([s['text'] for s in segments] + ['budget review'])
    assert index.scores('रिपोर्ट')[0] > 0 and index.scores('रिपोर्ट')[1:] == [0, 0]
    assert index.scores('report') == [0, 0, 0]  # No invented cross-language semantics.
    assert TfidfIndex(['', ' ']).scores('anything') == [0, 0]


@pytest.mark.parametrize('text, forbidden', [
    ('Have we decided to launch?', 'decision'),
    ('क्या हमने तय किया कि सोमवार को लॉन्च होगा?', 'decision'),
    ('kya humne decide kiya?', 'decision'),
    ('humne decide nahi kiya', 'decision'),
    ('अंतिम निर्णय नहीं हुआ है।', 'decision'),
    ('I do not agree.', 'agreement'),
    ('bilkul sahi nahi hai', 'agreement'),
    ('main report nahi bhej dunga', 'action_item'),
])
def test_negation_and_questions_do_not_become_confirmations(text, forbidden):
    result = KeywordEventExtractor().extract([{'segment_id': 1, 'text': text}], 'guards')
    assert all(event.event_type != forbidden for event in result.events)


@pytest.mark.parametrize('text, expected', [
    ('mein report kal bhej dungi', 'action_item'),
    ('aap report review kar dena', 'action_item'),
    ('हमने बजट फाइनल कर दिया।', 'decision'),
    ('humne budget final kar diya', 'decision'),
    ('kya report ready hai', 'question'),
    ('We decided not to launch.', 'decision'),
    ('I will send the report tomorrow.', 'action_item'),
    ('I’ll review the budget.', 'action_item'),
])
def test_more_hinglish_forms_keep_original_source(text, expected):
    event = KeywordEventExtractor().extract([{'segment_id': 7, 'text': text, 'start': 42}], 'forms').events[0]
    assert event.event_type == expected and event.text == text and event.source_segment_id == 7


def test_silence_does_not_load_whisper_and_previews_have_stable_ids(tmp_path):
    audio, diar = tmp_path / 'silent.wav', tmp_path / 'diar.json'
    sf.write(audio, np.zeros(16000 * 25), 16000)
    diar.write_text('{"segments": []}')
    previews = []
    with patch('src.audio.asr._load_whisper_model', side_effect=AssertionError('model loaded for silence')):
        result, _, _ = run_asr(audio, diar, 'silence', tmp_path, on_chunk=lambda rows, state: previews.append(state))
    assert result.segments == [] and result.recording_quality['digital_silence_ratio'] == 1
    assert previews[-1]['completed_seconds'] == 25
    sf.write(audio, np.ones(16000 * 25) * .01, 16000)
    segment = SimpleNamespace(start=3, end=4, text='main report bhej dunga', words=None, avg_logprob=-.1)
    model = SimpleNamespace(transcribe=lambda *a, **k: (iter([segment]), SimpleNamespace(language='en')))
    from src.utils.config import get
    settings = lambda k, default=None: 10 if k == 'asr.chunk_seconds' else get(k, default)
    previews = []
    with patch('src.audio.asr.get', side_effect=settings), patch('src.audio.asr._load_whisper_model', return_value=model):
        result, _, _ = run_asr(audio, diar, 'chunks', tmp_path,
            on_chunk=lambda rows, state: previews.append(([s.segment_id for s in rows], state)))
    assert [s.segment_id for s in result.segments] == [1, 2, 3]
    assert [state['total_segments'] for rows, state in previews] == [1, 2, 3]


def test_tfidf_alignment_works_without_embedding_weights(tmp_path):
    from src.audio.asr import TranscriptResult, TranscriptSegment, _save_json
    from src.ppt.extract import PresentationData, SlideData
    from src.ppt.io import save_presentation_json
    from src.fusion.multimodal_representation import run_alignment
    transcript, slides = tmp_path / 'transcript.json', tmp_path / 'slides.json'
    _save_json(TranscriptResult('lexical', 'hi', 2, 0, [], [TranscriptSegment(1, 0, 2, 'UNKNOWN', 'बजट रिपोर्ट')]), transcript)
    save_presentation_json(PresentationData('lexical', 'slides.pptx', 2, [
        SlideData('slide_001', 1, 'बजट रिपोर्ट', [], [], None, {}), SlideData('slide_002', 2, 'design options', [], [], None, {})]), slides)
    with patch('src.fusion.multimodal_representation.load_embedding_model', side_effect=AssertionError('heavy model loaded')):
        results, _, path, _ = run_alignment(transcript, slides, output_dir=tmp_path, method='tfidf')
    assert results[0].selected_slide == 'slide_001'
    assert json.loads(path.read_text())['alignment_method'] == 'tfidf'


def test_onnx_adapter_keeps_global_speaker_labels_and_cache(tmp_path, monkeypatch):
    from src.audio.diarization import run_diarization
    segmentation, embedding = tmp_path / 'seg.onnx', tmp_path / 'embedding.onnx'
    segmentation.write_bytes(b'test segmentation'); embedding.write_bytes(b'test embedding')
    audio = tmp_path / 'audio.wav'; sf.write(audio, np.ones(16000) * .01, 16000)
    from src.utils.config import get
    values = {'diarization.backend': 'sherpa-onnx',
              'diarization.onnx.segmentation_model': str(segmentation),
              'diarization.onnx.embedding_model': str(embedding)}
    settings = lambda key, default=None: values.get(key, get(key, default))
    factory = lambda **kwargs: SimpleNamespace(**kwargs)
    fake = SimpleNamespace(OfflineSpeakerDiarizationConfig=lambda **kw: SimpleNamespace(validate=lambda: True, **kw),
        OfflineSpeakerSegmentationModelConfig=factory, OfflineSpeakerSegmentationPyannoteModelConfig=factory,
        SpeakerEmbeddingExtractorConfig=factory, FastClusteringConfig=factory)
    calls = []
    def process(samples):
        calls.append(len(samples))
        return SimpleNamespace(sort_by_start_time=lambda: [SimpleNamespace(start=0, end=.4, speaker=5),
                                                          SimpleNamespace(start=.5, end=1, speaker=9)])
    fake.OfflineSpeakerDiarization = lambda config: SimpleNamespace(sample_rate=16000, process=process)
    monkeypatch.setitem(sys.modules, 'sherpa_onnx', fake)
    with patch('src.audio.diarization.get', side_effect=settings), patch('src.audio.onnx_diarization.get', side_effect=settings):
        result, _ = run_diarization(audio, 'onnx', tmp_path, num_speakers=2)
        run_diarization(audio, 'onnx', tmp_path, num_speakers=2)
        assert result.speakers == ['SPEAKER_00', 'SPEAKER_01'] and calls == [16000]
        embedding.write_bytes(b'changed embedding')
        run_diarization(audio, 'onnx', tmp_path, num_speakers=2)
        assert len(calls) == 2


def test_graph_exports_preserve_all_edges_without_networkx(tmp_path):
    from src.meeting.decisions import save_decision_graph_json, LineageEdge
    from src.meeting.interaction import save_interaction_graph_json
    decision = SimpleNamespace(decision_id='d1', status='confirmed', proposal=None, final_decision=None,
        discussion=[], supporting_evidence=[], revisions=[], agreements=[],
        lineage=[LineageEdge('e1', 'supports', 'e2'), LineageEdge('e1', 'revises', 'e2')])
    # Two relationships between the same events must not overwrite each other.
    with patch('src.meeting.decisions._build_networkx_graph', side_effect=AssertionError('NetworkX used')):
        save_decision_graph_json(SimpleNamespace(meeting_id='test', decisions=[decision]), tmp_path / 'decision.json')
    graph = json.loads((tmp_path / 'decision.json').read_text())['decision_graphs'][0]['graph']
    assert graph['nodes'] == ['e1', 'e2'] and len(graph['edges']) == 2
    interaction = SimpleNamespace(source_speaker='A', target_speaker='B', interaction_type='response',
        interaction_id='i1', timestamp=1, related_decision_id=None)
    with patch('src.meeting.interaction.build_participant_graph', side_effect=AssertionError('NetworkX used')):
        save_interaction_graph_json(SimpleNamespace(meeting_id='test', participants=['A', 'B'],
            participant_stats=[], interactions=[interaction, interaction]), tmp_path / 'interaction.json')
    assert len(json.loads((tmp_path / 'interaction.json').read_text())['edges']) == 2


def test_phone_evaluation_groups_human_references_without_changing_scripts(tmp_path, monkeypatch):
    from scripts import evaluate_recordings
    manifest = tmp_path / 'test.jsonl'
    manifest.write_text('\n'.join(json.dumps(row, ensure_ascii=False) for row in [
        {'id': 'one', 'audio': 'one.wav', 'reference': 'रिपोर्ट भेजूँगा', 'group': 'hinglish'},
        {'id': 'two', 'audio': 'two.wav', 'reference': 'budget review complete', 'group': 'hinglish'}]))
    for name in ('one.wav', 'two.wav'):
        (tmp_path / name).write_bytes(b'fixture')
    def process(audio, meeting_id, **options):
        text = 'रिपोर्ट भेजूँगा' if audio.name == 'one.wav' else 'budget review'
        path = tmp_path / (meeting_id + '.json')
        path.write_text(json.dumps({'transcript_segments': [{'text': text}],
                                    'meeting_overview': {'duration_s': 2}}))
        return path
    monkeypatch.setattr(evaluate_recordings, 'run_meeting', process)
    result = tmp_path / 'metrics.json'
    monkeypatch.setattr(sys, 'argv', ['evaluate_recordings.py', '--manifest', str(manifest), '--output', str(result)])
    evaluate_recordings.main()
    metrics = json.loads(result.read_text())
    assert metrics['complete'] and metrics['groups']['hinglish']['wer'] == .2  # One error / five reference words.
    assert evaluate_recordings.normalized('हिंदी, report भेजूँगा।') == 'हिंदी report भेजूँगा'
