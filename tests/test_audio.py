"""
Tests for audio preprocessing, VAD, and speaker diarization.
Uses synthetic audio — no real audio files or datasets required.
Diarization model calls are mocked to avoid requiring HF_TOKEN in CI.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.audio.asr import (
    TranscriptResult,
    TranscriptSegment,
    attribute_speaker,
    compute_overlap,
    run_asr,
)
from src.audio.diarization import (
    DiarizationResult,
    DiarizationSegment,
    merge_adjacent_segments,
    normalize_speaker_labels,
    run_diarization,
)
from src.audio.preprocess import AudioMetadata, preprocess_audio
from src.audio.vad import SpeechSegment, run_vad

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_RATE = 16000
DURATION_S = 5


def _make_synthetic_wav(
    path: Path, sr: int = SAMPLE_RATE, duration: float = DURATION_S, channels: int = 1
) -> Path:
    """Generate a 440 Hz sine-wave WAV file using soundfile (no FFmpeg needed)."""
    n_samples = int(sr * duration)
    t = np.linspace(0, duration, n_samples, dtype=np.float32)
    mono = (0.4 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    waveform = np.stack([mono] * channels, axis=1)  # [T, C]
    sf.write(str(path), waveform, sr, subtype="PCM_16")
    return path


def _make_mock_diarization(segments: list[tuple[float, float, str]]):
    """Build a mock pyannote Annotation object from (start, end, speaker) tuples."""
    mock_annotation = MagicMock()
    mock_annotation.itertracks.return_value = [
        (MagicMock(start=s, end=e), None, spk)
        for s, e, spk in segments
    ]
    return mock_annotation


# ---------------------------------------------------------------------------
# Preprocessing tests
# ---------------------------------------------------------------------------

class TestPreprocessAudio:

    def test_invalid_path_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            preprocess_audio(tmp_path / "nonexistent.wav")

    def test_returns_correct_types(self, tmp_path):
        wav = _make_synthetic_wav(tmp_path / "test.wav")
        out_path, meta = preprocess_audio(wav)
        assert isinstance(out_path, Path)
        assert isinstance(meta, AudioMetadata)

    def test_output_file_exists(self, tmp_path):
        wav = _make_synthetic_wav(tmp_path / "test.wav")
        out_path, _ = preprocess_audio(wav)
        assert out_path.exists()

    def test_output_is_16khz(self, tmp_path):
        wav = _make_synthetic_wav(tmp_path / "test.wav", sr=44100)
        out_path, meta = preprocess_audio(wav)
        _, sr = sf.read(str(out_path))
        assert sr == 16000
        assert meta.processed_sample_rate == 16000

    def test_output_is_mono(self, tmp_path):
        wav = _make_synthetic_wav(tmp_path / "stereo.wav", channels=2)
        out_path, meta = preprocess_audio(wav)
        data, _ = sf.read(str(out_path), always_2d=True)
        assert data.shape[1] == 1
        assert meta.original_channels == 2

    def test_metadata_duration(self, tmp_path):
        wav = _make_synthetic_wav(tmp_path / "test.wav", duration=3.0)
        _, meta = preprocess_audio(wav)
        assert abs(meta.original_duration - 3.0) < 0.1
        assert abs(meta.processed_duration - 3.0) < 0.1

    def test_original_file_untouched(self, tmp_path):
        wav = _make_synthetic_wav(tmp_path / "test.wav", sr=44100)
        original_size = wav.stat().st_size
        preprocess_audio(wav)
        assert wav.stat().st_size == original_size


# ---------------------------------------------------------------------------
# VAD tests
# ---------------------------------------------------------------------------

class TestRunVAD:

    def test_invalid_path_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            run_vad(tmp_path / "missing.wav")

    def test_returns_segments_and_path(self, tmp_path):
        wav = _make_synthetic_wav(tmp_path / "vad_input.wav")
        segments, json_path = run_vad(wav, meeting_id="test_meeting")
        assert isinstance(segments, list)
        assert isinstance(json_path, Path)

    def test_json_output_exists(self, tmp_path):
        wav = _make_synthetic_wav(tmp_path / "vad_input.wav")
        _, json_path = run_vad(wav, meeting_id="test_meeting")
        assert json_path.exists()

    def test_json_structure(self, tmp_path):
        wav = _make_synthetic_wav(tmp_path / "vad_input.wav")
        _, json_path = run_vad(wav, meeting_id="test_meeting")
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "meeting_id" in data
        assert "audio_file" in data
        assert "duration" in data
        assert "segments" in data
        assert isinstance(data["segments"], list)

    def test_segment_structure(self, tmp_path):
        wav = _make_synthetic_wav(tmp_path / "vad_input.wav")
        _, json_path = run_vad(wav, meeting_id="test_meeting")
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        for seg in data["segments"]:
            assert "segment_id" in seg
            assert "start" in seg
            assert "end" in seg
            assert seg["end"] > seg["start"]

    def test_segment_ids_sequential(self, tmp_path):
        wav = _make_synthetic_wav(tmp_path / "vad_input.wav")
        segments, _ = run_vad(wav, meeting_id="test_meeting")
        for i, seg in enumerate(segments):
            assert seg.segment_id == i + 1

    def test_speech_segment_type(self, tmp_path):
        wav = _make_synthetic_wav(tmp_path / "vad_input.wav")
        segments, _ = run_vad(wav, meeting_id="test_meeting")
        for seg in segments:
            assert isinstance(seg, SpeechSegment)
            assert isinstance(seg.start, float)
            assert isinstance(seg.end, float)


# ---------------------------------------------------------------------------
# Diarization Helper Tests
# ---------------------------------------------------------------------------

class TestDiarizationHelpers:

    def test_merge_adjacent_segments_same_speaker(self):
        # 0.2s gap between same speaker -> merged
        raw = [(0.0, 2.0, "SPEAKER_00"), (2.2, 4.0, "SPEAKER_00")]
        merged = merge_adjacent_segments(raw, max_gap=0.5)
        assert len(merged) == 1
        assert merged[0] == (0.0, 4.0, "SPEAKER_00")

    def test_merge_adjacent_segments_large_gap_not_merged(self):
        # 1.0s gap with max_gap=0.5 -> not merged
        raw = [(0.0, 2.0, "SPEAKER_00"), (3.0, 4.0, "SPEAKER_00")]
        merged = merge_adjacent_segments(raw, max_gap=0.5)
        assert len(merged) == 2

    def test_merge_adjacent_segments_different_speakers_not_merged(self):
        raw = [(0.0, 2.0, "SPEAKER_00"), (2.1, 4.0, "SPEAKER_01")]
        merged = merge_adjacent_segments(raw, max_gap=0.5)
        assert len(merged) == 2

    def test_merge_adjacent_segments_empty(self):
        assert merge_adjacent_segments([]) == []

    def test_normalize_speaker_labels(self):
        raw = [
            (0.0, 1.0, "CLUSTER_B"),
            (1.5, 2.5, "CLUSTER_A"),
            (3.0, 4.0, "CLUSTER_B"),
        ]
        norm, speakers = normalize_speaker_labels(raw)
        assert speakers == ["SPEAKER_00", "SPEAKER_01"]
        assert norm[0][2] == "SPEAKER_00"
        assert norm[1][2] == "SPEAKER_01"
        assert norm[2][2] == "SPEAKER_00"


# ---------------------------------------------------------------------------
# Diarization Pipeline Tests (model boundary mocked)
# ---------------------------------------------------------------------------

class TestRunDiarization:

    def test_invalid_path_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            run_diarization(tmp_path / "missing.wav")

    def test_missing_hf_token_raises(self, tmp_path, monkeypatch):
        wav = _make_synthetic_wav(tmp_path / "audio.wav")
        monkeypatch.setattr("src.audio.diarization.load_env", lambda: None)
        monkeypatch.delenv("HF_TOKEN", raising=False)
        with pytest.raises(EnvironmentError, match="HF_TOKEN"):
            run_diarization(wav, meeting_id="test")

    def test_returns_result_and_path(self, tmp_path, monkeypatch):
        wav = _make_synthetic_wav(tmp_path / "audio.wav")
        monkeypatch.setenv("HF_TOKEN", "fake-token")
        mock_ann = _make_mock_diarization([
            (0.5, 3.0, "SPEAKER_00"),
            (3.5, 5.0, "SPEAKER_01"),
        ])
        with patch("src.audio.diarization._load_pipeline", return_value=lambda *a, **kw: mock_ann):
            result, json_path = run_diarization(wav, meeting_id="mock_meeting", output_dir=tmp_path)
        assert isinstance(result, DiarizationResult)
        assert isinstance(json_path, Path)
        assert json_path.exists()

    def test_speaker_labels_canonical(self, tmp_path, monkeypatch):
        wav = _make_synthetic_wav(tmp_path / "audio.wav")
        monkeypatch.setenv("HF_TOKEN", "fake-token")
        mock_ann = _make_mock_diarization([
            (0.0, 2.0, "SPEAKER_00"),
            (2.5, 4.0, "SPEAKER_01"),
            (4.5, 5.0, "SPEAKER_00"),
        ])
        with patch("src.audio.diarization._load_pipeline", return_value=lambda *a, **kw: mock_ann):
            result, _ = run_diarization(wav, meeting_id="mock_meeting", output_dir=tmp_path)
        assert result.speakers == ["SPEAKER_00", "SPEAKER_01"]
        assert result.num_speakers == 2

    def test_segments_ordered_by_start(self, tmp_path, monkeypatch):
        wav = _make_synthetic_wav(tmp_path / "audio.wav")
        monkeypatch.setenv("HF_TOKEN", "fake-token")
        # Deliberately out of order to verify sorting
        mock_ann = _make_mock_diarization([
            (3.0, 4.0, "SPEAKER_01"),
            (0.0, 2.0, "SPEAKER_00"),
        ])
        with patch("src.audio.diarization._load_pipeline", return_value=lambda *a, **kw: mock_ann):
            result, _ = run_diarization(wav, meeting_id="mock_meeting", output_dir=tmp_path)
        starts = [s.start for s in result.segments]
        assert starts == sorted(starts)

    def test_segment_ids_sequential(self, tmp_path, monkeypatch):
        wav = _make_synthetic_wav(tmp_path / "audio.wav")
        monkeypatch.setenv("HF_TOKEN", "fake-token")
        mock_ann = _make_mock_diarization([
            (0.0, 1.0, "SPEAKER_00"),
            (1.5, 3.0, "SPEAKER_01"),
            (3.5, 5.0, "SPEAKER_00"),
        ])
        with patch("src.audio.diarization._load_pipeline", return_value=lambda *a, **kw: mock_ann):
            result, _ = run_diarization(wav, meeting_id="mock_meeting", output_dir=tmp_path)
        for i, seg in enumerate(result.segments):
            assert seg.segment_id == i + 1

    def test_json_output_structure(self, tmp_path, monkeypatch):
        wav = _make_synthetic_wav(tmp_path / "audio.wav")
        monkeypatch.setenv("HF_TOKEN", "fake-token")
        mock_ann = _make_mock_diarization([
            (0.0, 2.0, "SPEAKER_00"),
            (2.5, 5.0, "SPEAKER_01"),
        ])
        with patch("src.audio.diarization._load_pipeline", return_value=lambda *a, **kw: mock_ann):
            _, json_path = run_diarization(wav, meeting_id="mock_meeting", output_dir=tmp_path)
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "meeting_id" in data
        assert "num_speakers" in data
        assert "speakers" in data
        assert "segments" in data
        assert isinstance(data["segments"], list)
        for seg in data["segments"]:
            assert {"segment_id", "start", "end", "speaker"} <= seg.keys()
            assert seg["end"] > seg["start"]

    def test_segment_end_gt_start(self, tmp_path, monkeypatch):
        wav = _make_synthetic_wav(tmp_path / "audio.wav")
        monkeypatch.setenv("HF_TOKEN", "fake-token")
        mock_ann = _make_mock_diarization([
            (1.0, 3.5, "SPEAKER_00"),
            (4.0, 5.0, "SPEAKER_01"),
        ])
        with patch("src.audio.diarization._load_pipeline", return_value=lambda *a, **kw: mock_ann):
            result, _ = run_diarization(wav, meeting_id="mock_meeting", output_dir=tmp_path)
        for seg in result.segments:
            assert seg.end > seg.start

    def test_diarization_segment_type(self, tmp_path, monkeypatch):
        wav = _make_synthetic_wav(tmp_path / "audio.wav")
        monkeypatch.setenv("HF_TOKEN", "fake-token")
        mock_ann = _make_mock_diarization([(0.0, 2.0, "SPEAKER_00")])
        with patch("src.audio.diarization._load_pipeline", return_value=lambda *a, **kw: mock_ann):
            result, _ = run_diarization(wav, meeting_id="mock_meeting", output_dir=tmp_path)
        for seg in result.segments:
            assert isinstance(seg, DiarizationSegment)
            assert isinstance(seg.start, float)
            assert isinstance(seg.end, float)
            assert isinstance(seg.speaker, str)

    def test_empty_diarization_handles_gracefully(self, tmp_path, monkeypatch):
        wav = _make_synthetic_wav(tmp_path / "audio.wav")
        monkeypatch.setenv("HF_TOKEN", "fake-token")
        mock_ann = _make_mock_diarization([])
        with patch("src.audio.diarization._load_pipeline", return_value=lambda *a, **kw: mock_ann):
            result, json_path = run_diarization(wav, meeting_id="empty_meeting", output_dir=tmp_path)
        assert result.num_speakers == 0
        assert result.speakers == []
        assert result.segments == []
        assert json_path.exists()


# ---------------------------------------------------------------------------
# ASR Helper Tests
# ---------------------------------------------------------------------------


class TestASRHelpers:

    def test_compute_overlap_full(self):
        # [1, 5] fully inside [0, 6] -> overlap = 4.0
        assert compute_overlap(1.0, 5.0, 0.0, 6.0) == pytest.approx(4.0)

    def test_compute_overlap_partial(self):
        # [2, 6] overlaps [4, 8] by 2s
        assert compute_overlap(2.0, 6.0, 4.0, 8.0) == pytest.approx(2.0)

    def test_compute_overlap_none(self):
        # [0, 2] vs [3, 5] -> no overlap
        assert compute_overlap(0.0, 2.0, 3.0, 5.0) == pytest.approx(0.0)

    def test_compute_overlap_touching(self):
        # [0, 2] vs [2, 4] -> touching but 0 overlap
        assert compute_overlap(0.0, 2.0, 2.0, 4.0) == pytest.approx(0.0)

    def test_attribute_speaker_best_match(self):
        diar = [
            {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
            {"start": 5.0, "end": 10.0, "speaker": "SPEAKER_01"},
        ]
        # ASR segment [1, 4] -> mostly inside SPEAKER_00
        assert attribute_speaker(1.0, 4.0, diar) == "SPEAKER_00"

    def test_attribute_speaker_unknown_below_threshold(self):
        diar = [{"start": 8.0, "end": 10.0, "speaker": "SPEAKER_00"}]
        # ASR segment [0, 10] -> 2s overlap out of 10s = 0.2 < 0.3 threshold
        assert attribute_speaker(0.0, 10.0, diar, min_overlap_ratio=0.3) == "UNKNOWN"

    def test_attribute_speaker_empty_diarization(self):
        assert attribute_speaker(0.0, 5.0, [], min_overlap_ratio=0.3) == "UNKNOWN"

    def test_attribute_speaker_exact_threshold(self):
        diar = [{"start": 0.0, "end": 3.0, "speaker": "SPEAKER_00"}]
        # ASR [0, 10] -> 3/10 = 0.3 overlap ratio; exactly at threshold -> qualified
        assert attribute_speaker(0.0, 10.0, diar, min_overlap_ratio=0.3) == "SPEAKER_00"


# ---------------------------------------------------------------------------
# ASR Pipeline Tests (faster-whisper boundary mocked)
# ---------------------------------------------------------------------------


def _make_mock_asr_segment(start: float, end: float, text: str, avg_logprob: float = -0.3):
    """Build a minimal mock segment matching faster-whisper's Segment namedtuple-like API."""
    seg = MagicMock()
    seg.start = start
    seg.end = end
    seg.text = text
    seg.avg_logprob = avg_logprob
    return seg


def _make_mock_transcription_info(language: str = "en", duration: float = 10.0):
    info = MagicMock()
    info.language = language
    info.duration = duration
    return info


def _write_diarization_json(path, segments):
    """Write a minimal Phase-4 diarization JSON fixture."""
    import json
    payload = {
        "meeting_id": "test_meeting",
        "num_speakers": len({s['speaker'] for s in segments}),
        "speakers": sorted({s['speaker'] for s in segments}),
        "segments": [
            {"segment_id": i + 1, "start": s["start"], "end": s["end"], "speaker": s["speaker"]}
            for i, s in enumerate(segments)
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)


class TestRunASR:

    def test_missing_audio_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            run_asr(tmp_path / "missing.wav", diarization_path=tmp_path / "diar.json")

    def test_missing_diarization_raises(self, tmp_path):
        wav = _make_synthetic_wav(tmp_path / "audio.wav")
        with pytest.raises(FileNotFoundError, match="Diarization JSON not found"):
            run_asr(wav, diarization_path=tmp_path / "nonexistent_diar.json")

    def test_returns_result_and_paths(self, tmp_path):
        wav = _make_synthetic_wav(tmp_path / "audio.wav")
        diar_path = tmp_path / "test_meeting_diarization.json"
        _write_diarization_json(diar_path, [
            {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
        ])
        mock_seg = _make_mock_asr_segment(0.5, 4.5, "Hello world")
        mock_info = _make_mock_transcription_info()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_seg], mock_info)
        with patch("src.audio.asr._load_whisper_model", return_value=mock_model):
            result, json_path, txt_path = run_asr(
                wav, diarization_path=diar_path,
                meeting_id="test_meeting", output_dir=tmp_path,
            )
        assert isinstance(result, TranscriptResult)
        assert json_path.exists()
        assert txt_path.exists()

    def test_speaker_attribution_correct(self, tmp_path):
        wav = _make_synthetic_wav(tmp_path / "audio.wav")
        diar_path = tmp_path / "meet_diarization.json"
        _write_diarization_json(diar_path, [
            {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
            {"start": 5.0, "end": 10.0, "speaker": "SPEAKER_01"},
        ])
        segs = [
            _make_mock_asr_segment(0.5, 3.5, "First speaker"),
            _make_mock_asr_segment(5.5, 9.0, "Second speaker"),
        ]
        mock_info = _make_mock_transcription_info(duration=10.0)
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (segs, mock_info)
        with patch("src.audio.asr._load_whisper_model", return_value=mock_model):
            result, _, _ = run_asr(
                wav, diarization_path=diar_path,
                meeting_id="meet", output_dir=tmp_path,
            )
        assert result.segments[0].speaker == "SPEAKER_00"
        assert result.segments[1].speaker == "SPEAKER_01"

    def test_unknown_speaker_when_no_overlap(self, tmp_path):
        wav = _make_synthetic_wav(tmp_path / "audio.wav")
        diar_path = tmp_path / "empty_diarization.json"
        _write_diarization_json(diar_path, [])  # no diarization segments
        mock_seg = _make_mock_asr_segment(0.0, 5.0, "orphan text")
        mock_info = _make_mock_transcription_info()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_seg], mock_info)
        with patch("src.audio.asr._load_whisper_model", return_value=mock_model):
            result, _, _ = run_asr(
                wav, diarization_path=diar_path,
                meeting_id="empty", output_dir=tmp_path,
            )
        assert result.segments[0].speaker == "UNKNOWN"

    def test_segment_ids_sequential(self, tmp_path):
        wav = _make_synthetic_wav(tmp_path / "audio.wav")
        diar_path = tmp_path / "seq_diarization.json"
        _write_diarization_json(diar_path, [
            {"start": 0.0, "end": 10.0, "speaker": "SPEAKER_00"},
        ])
        segs = [_make_mock_asr_segment(i * 2.0, i * 2.0 + 1.5, f"Seg {i}") for i in range(4)]
        mock_info = _make_mock_transcription_info(duration=10.0)
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (segs, mock_info)
        with patch("src.audio.asr._load_whisper_model", return_value=mock_model):
            result, _, _ = run_asr(
                wav, diarization_path=diar_path,
                meeting_id="seq", output_dir=tmp_path,
            )
        for i, seg in enumerate(result.segments):
            assert seg.segment_id == i + 1

    def test_confidence_attached(self, tmp_path):
        wav = _make_synthetic_wav(tmp_path / "audio.wav")
        diar_path = tmp_path / "conf_diarization.json"
        _write_diarization_json(diar_path, [
            {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
        ])
        mock_seg = _make_mock_asr_segment(0.0, 5.0, "confident", avg_logprob=-0.1)
        mock_info = _make_mock_transcription_info()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_seg], mock_info)
        with patch("src.audio.asr._load_whisper_model", return_value=mock_model):
            result, _, _ = run_asr(
                wav, diarization_path=diar_path,
                meeting_id="conf", output_dir=tmp_path,
            )
        assert result.segments[0].confidence is not None
        assert 0.0 <= result.segments[0].confidence <= 1.0

    def test_json_output_structure(self, tmp_path):
        wav = _make_synthetic_wav(tmp_path / "audio.wav")
        diar_path = tmp_path / "struct_diarization.json"
        _write_diarization_json(diar_path, [
            {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
        ])
        mock_seg = _make_mock_asr_segment(0.5, 4.5, "Some text")
        mock_info = _make_mock_transcription_info()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_seg], mock_info)
        with patch("src.audio.asr._load_whisper_model", return_value=mock_model):
            _, json_path, _ = run_asr(
                wav, diarization_path=diar_path,
                meeting_id="struct", output_dir=tmp_path,
            )
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        required_top = {"meeting_id", "language", "duration", "num_speakers", "speakers", "segments"}
        assert required_top <= data.keys()
        for seg in data["segments"]:
            assert {"segment_id", "start", "end", "speaker", "text"} <= seg.keys()
            assert seg["end"] > seg["start"]

    def test_caching_skips_model_reload(self, tmp_path):
        wav = _make_synthetic_wav(tmp_path / "audio.wav")
        diar_path = tmp_path / "cache_diarization.json"
        _write_diarization_json(diar_path, [
            {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
        ])
        mock_seg = _make_mock_asr_segment(0.5, 4.5, "First call")
        mock_info = _make_mock_transcription_info()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_seg], mock_info)
        with patch("src.audio.asr._load_whisper_model", return_value=mock_model) as mock_loader:
            run_asr(wav, diarization_path=diar_path, meeting_id="cache", output_dir=tmp_path)
            # Second call should hit cache; _load_whisper_model must NOT be called again
            run_asr(wav, diarization_path=diar_path, meeting_id="cache", output_dir=tmp_path)
        assert mock_loader.call_count == 1

    def test_txt_output_contains_speaker_and_text(self, tmp_path):
        wav = _make_synthetic_wav(tmp_path / "audio.wav")
        diar_path = tmp_path / "txt_diarization.json"
        _write_diarization_json(diar_path, [
            {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
        ])
        mock_seg = _make_mock_asr_segment(0.5, 4.5, "Hello from speaker zero")
        mock_info = _make_mock_transcription_info()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_seg], mock_info)
        with patch("src.audio.asr._load_whisper_model", return_value=mock_model):
            _, _, txt_path = run_asr(
                wav, diarization_path=diar_path,
                meeting_id="txt", output_dir=tmp_path,
            )
        content = txt_path.read_text(encoding="utf-8")
        assert "SPEAKER_00" in content
        assert "Hello from speaker zero" in content

