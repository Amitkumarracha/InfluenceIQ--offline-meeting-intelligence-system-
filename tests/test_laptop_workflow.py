"""Regression checks for real failure modes discovered during the laptop migration."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import pytest
import soundfile as sf
from src.audio.asr import run_asr, attribute_speaker
from src.meeting.events import KeywordEventExtractor
from src.report.generator import generate_report
from src.evaluation.metrics import calculate_der


def test_word_level_turns_and_changed_input_invalidates_cache(tmp_path, monkeypatch):
    audio = tmp_path / 'meeting.wav'
    sf.write(audio, np.ones(16000 * 12) * .005, 16000)
    diar = tmp_path / 'diar.json'
    diar.write_text(json.dumps({'segments': [
        {'start': 0, 'end': 5, 'speaker': 'A'}, {'start': 5, 'end': 12, 'speaker': 'B'}]}))
    segment = SimpleNamespace(start=1, end=8, text='Hello नमस्ते', avg_logprob=-.1,
        words=[SimpleNamespace(start=1, end=2, word='Hello'),
               SimpleNamespace(start=6, end=8, word=' नमस्ते')])
    model = SimpleNamespace(transcribe=lambda *a, **kw: (iter([segment]), SimpleNamespace(language='hi')))
    with patch('src.audio.asr._load_whisper_model', return_value=model) as loader:
        result, _, _ = run_asr(audio, diar, 'word_turns', tmp_path)
        assert [s.speaker for s in result.segments] == ['A', 'B']
        run_asr(audio, diar, 'word_turns', tmp_path)
        assert loader.call_count == 1
        sf.write(audio, np.ones(16000 * 12) * .01, 16000)
        run_asr(audio, diar, 'word_turns', tmp_path)
        assert loader.call_count == 2
        monkeypatch.setenv("MAI_ASR_MODEL", "medium")
        run_asr(audio, diar, "word_turns", tmp_path)
        assert loader.call_count == 3


def test_interrupted_chunk_resume(tmp_path):
    audio = tmp_path / 'meeting.wav'
    sf.write(audio, np.ones(16000 * 22) * .005, 16000)
    diar = tmp_path / 'diar.json'
    diar.write_text('{"segments": []}')
    calls = []
    def transcribe(samples, **kwargs):
        calls.append(len(samples))
        if len(calls) == 2:
            raise RuntimeError('power lost')
        seg = SimpleNamespace(start=3, end=4, text='Keep this', avg_logprob=-.1, words=None)
        return iter([seg]), SimpleNamespace(language='en')
    from src.utils.config import get
    settings = lambda k, default=None: 10 if k == 'asr.chunk_seconds' else get(k, default)
    model = SimpleNamespace(transcribe=transcribe)
    with patch('src.audio.asr.get', side_effect=settings), patch('src.audio.asr._load_whisper_model', return_value=model):
        with pytest.raises(RuntimeError, match='power lost'):
            run_asr(audio, diar, 'resume', tmp_path)
        result, _, _ = run_asr(audio, diar, 'resume', tmp_path)
    assert len(calls) == 4  # first chunk reused, only two remaining chunks rerun
    assert result.segments[0].start == 3
    assert all(0 <= s.start < s.end <= 22 for s in result.segments)


def test_attribution_sums_split_turns_and_abstains_on_overlap():
    assert attribute_speaker(0, 10, [{'start': 0, 'end': 4, 'speaker': 'A'},
        {'start': 5, 'end': 9, 'speaker': 'A'}], .7) == 'A'
    assert attribute_speaker(0, 2, [{'start': 0, 'end': 2, 'speaker': 'A'},
        {'start': 0, 'end': 2, 'speaker': 'B'}]) == 'UNKNOWN'


@pytest.mark.parametrize('text, kind', [
    ('हमने तय किया कि शुक्रवार को रिलीज करेंगे।', 'decision'),
    ('main report kal bhej dunga', 'action_item'),
    ('मैं रिपोर्ट कल भेज दूंगा।', 'action_item'),
    ('मैं सहमत नहीं हूँ।', 'disagreement'),
    ('बिल्कुल सही।', 'agreement'),
])
def test_bilingual_event_sources_preserved(text, kind):
    result = KeywordEventExtractor().extract([{'segment_id': 4, 'start': 3600, 'end': 3605,
                                              'speaker': 'A', 'text': text}], 'test')
    assert len(result.events) == 1
    assert result.events[0].event_type == kind
    assert result.events[0].text == text
    assert result.events[0].start == 3600


def test_report_counts_full_transcript_not_only_keyword_events(tmp_path):
    (tmp_path / 'audio').mkdir()
    (tmp_path / 'audio/test_transcript.json').write_text(json.dumps({'duration': 7200, 'segments': [
        {'speaker': 'A', 'start': 0, 'end': 5, 'text': 'ordinary words'},
        {'speaker': 'B', 'start': 10, 'end': 20, 'text': 'more ordinary words'},
        {'speaker': 'UNKNOWN', 'start': 20, 'end': 25, 'text': 'uncertain'}]}))
    report = generate_report('test', tmp_path)
    assert report.meeting_overview.duration_s == 7200
    assert report.meeting_overview.num_participants == 2
    assert [p.speaking_duration_s for p in report.participants] == [5, 10]


def test_der_is_invariant_to_cluster_names_and_supports_overlap():
    ref = [{'start': 0, 'end': 4, 'speaker': 'A'}, {'start': 2, 'end': 6, 'speaker': 'B'}]
    hyp = [{**s, 'speaker': {'A': 'SPEAKER_00', 'B': 'SPEAKER_01'}[s['speaker']]} for s in ref]
    assert calculate_der(ref, hyp)['der'] == 0


def test_influence_baselines_include_speech_without_events():
    from src.meeting.events import EventExtractionResult
    from src.meeting.evidence import EvidenceExtractionResult
    from src.meeting.decisions import DecisionResult
    from src.meeting.influence import extract_baselines
    result = extract_baselines(EventExtractionResult('test'), EvidenceExtractionResult('test'),
        DecisionResult('test'), [{'speaker': 'A', 'start': 0, 'end': 50},
                                 {'speaker': 'B', 'start': 50, 'end': 60}])
    assert result['A'].speaking_time == 50
    assert result['B'].speaking_time == 10


def test_language_detection_respects_configured_meeting_languages(tmp_path):
    audio = tmp_path / 'meeting.wav'
    sf.write(audio, np.ones(16000) * .01, 16000)
    diar = tmp_path / 'diar.json'
    diar.write_text('{"segments": []}')
    calls = []
    def transcribe(samples, **kwargs):
        calls.append(kwargs)
        if 'language' not in kwargs:
            return iter([]), SimpleNamespace(language='cy', all_language_probs=[('cy', .5), ('en', .3), ('hi', .1)])
        segment = SimpleNamespace(start=0, end=1, text='English meeting', words=None, avg_logprob=-.1)
        return iter([segment]), SimpleNamespace(language=kwargs['language'])
    with patch('src.audio.asr._load_whisper_model', return_value=SimpleNamespace(transcribe=transcribe)):
        result, _, _ = run_asr(audio, diar, 'languages', tmp_path)
    assert result.language == 'en'
    assert result.segments[0].text == 'English meeting'
    assert len(calls) == 2 and calls[1]['language'] == 'en'
