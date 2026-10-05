"""Automatic Speech Recognition (ASR) and speaker-attributed transcript generation.

Uses faster-whisper for offline transcription and matches each ASR segment
against diarization segments via temporal overlap to assign speaker IDs.

Phase 5 of the Multimodal Meeting Intelligence Pipeline.
"""

import json
from bisect import bisect_left, bisect_right
from itertools import accumulate
import math
import os
import soundfile as sf
from src.utils.cache import atomic_json, fingerprint, read_cache
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.utils.config import get
from src.utils.logging import get_logger
from src.utils.paths import get_processed_audio_dir

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class TranscriptSegment:
    """One ASR segment attributed to a single speaker."""

    segment_id: int
    start: float
    end: float
    speaker: str
    text: str
    confidence: float | None = None


@dataclass
class TranscriptResult:
    """Complete speaker-attributed transcript for a meeting."""

    meeting_id: str
    language: str | None
    duration: float
    num_speakers: int
    speakers: list[str]
    segments: list[TranscriptSegment] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------


def _preload_cuda_libraries() -> None:
    """Preload libcublas.so.12 if present on system (e.g. in /usr/local/lib/ollama/cuda_v12)."""
    import ctypes
    candidate_paths = [
        "/usr/local/lib/ollama/cuda_v12",
        "/usr/local/cuda-12/lib64",
        "/usr/local/cuda/lib64",
    ]
    for p in candidate_paths:
        cublas_path = Path(p) / "libcublas.so.12"
        cublas_lt_path = Path(p) / "libcublasLt.so.12"
        if cublas_path.exists():
            try:
                if cublas_lt_path.exists():
                    ctypes.CDLL(str(cublas_lt_path), mode=ctypes.RTLD_GLOBAL)
                ctypes.CDLL(str(cublas_path), mode=ctypes.RTLD_GLOBAL)
                logger.info("Successfully preloaded CUDA 12 cublas from %s", p)
                break
            except Exception as e:
                logger.warning("Could not preload cublas from %s: %s", p, e)


def _load_whisper_model():
    """Load the faster-whisper WhisperModel per config.yaml settings.

    Some environments advertise CUDA support for pyannote but do not have a
    working libcublas runtime for faster-whisper. In that case, fall back to the
    CPU path instead of crashing during the ASR stage.
    """
    _preload_cuda_libraries()
    from faster_whisper import WhisperModel  # type: ignore[import-untyped]

    model_size: str = get("asr.model_size", "base")
    requested_device: str = str(get("asr.device", "cpu")).lower()
    requested_compute: str = str(get("asr.compute_type", "int8")).lower()

    attempts: list[tuple[str, str]] = [(requested_device, requested_compute)]
    if requested_device == "cuda":
        attempts.append(("cpu", "int8"))
    elif requested_device == "auto":
        attempts.append(("cpu", "int8"))

    last_error: Exception | None = None
    for device, compute_type in attempts:
        logger.info(
            "Loading faster-whisper model: size=%s device=%s compute_type=%s",
            model_size, device, compute_type,
        )
        try:
            return WhisperModel(model_size, device=device, compute_type=compute_type,
                cpu_threads=int(get("asr.cpu_threads", 4)),
                local_files_only=os.environ.get("HF_HUB_OFFLINE", "1") == "1")
        except Exception as exc:  # pragma: no cover - exercised in integration envs
            msg = str(exc)
            if "libcublas" in msg.lower() or "cuda" in msg.lower() and "not found" in msg.lower():
                logger.warning(
                    "CUDA runtime unavailable for faster-whisper; retrying on CPU. Details: %s",
                    msg,
                )
                last_error = exc
                continue
            raise

    if last_error is not None:
        logger.error(
            "Unable to load faster-whisper model with requested settings; last error: %s",
            last_error,
        )
    raise last_error if last_error is not None else RuntimeError("Unable to load faster-whisper model")


# ---------------------------------------------------------------------------
# Overlap-based attribution helpers
# ---------------------------------------------------------------------------


def compute_overlap(
    asr_start: float,
    asr_end: float,
    diar_start: float,
    diar_end: float,
) -> float:
    """Return the overlap duration (seconds) between two intervals."""
    return max(0.0, min(asr_end, diar_end) - max(asr_start, diar_start))


def attribute_speaker(
    asr_start: float,
    asr_end: float,
    diar_segments: list[dict[str, Any]],
    min_overlap_ratio: float = 0.3,
) -> str:
    """Assign the speaker whose diarization segment has the greatest overlap.

    Returns "UNKNOWN" when no segment covers at least *min_overlap_ratio*
    of the ASR segment duration.
    """
    asr_duration = max(asr_end - asr_start, 1e-6)
    # Union intervals per speaker: split diarization turns must not undercount,
    # and overlapping tracks from the same speaker must not double-count.
    intervals = {}
    for seg in diar_segments:
        a, b = max(asr_start, seg["start"]), min(asr_end, seg["end"])
        if b > a:
            intervals.setdefault(seg["speaker"], []).append((a, b))
    totals = {}
    for speaker, spans in intervals.items():
        end = float('-inf')
        total = 0.0
        for a, b in sorted(spans):
            total += max(0, b - max(a, end))
            end = max(end, b)
        totals[speaker] = total
    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    if not ranked or ranked[0][1] / asr_duration < min_overlap_ratio:
        return "UNKNOWN"
    if len(ranked) > 1 and abs(ranked[0][1] - ranked[1][1]) < 1e-6:
        return "UNKNOWN"
    return ranked[0][0]


# ---------------------------------------------------------------------------
# Core ASR + attribution
# ---------------------------------------------------------------------------


def _load_diarization_json(path: Path) -> list[dict[str, Any]]:
    """Load diarization segments from a Phase 4 JSON file."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("segments", [])


def run_asr(
    audio_path: str | Path,
    diarization_path: str | Path | None = None,
    meeting_id: str | None = None,
    output_dir: Path | None = None,
) -> tuple["TranscriptResult", Path, Path]:
    """Transcribe meeting audio and attribute segments to speakers.

    Args:
        audio_path: Path to the 16 kHz mono WAV file.
        diarization_path: Path to the Phase 4 diarization JSON.  When None,
            looks for <audio_dir>/<meeting_id>_diarization.json.
        meeting_id: Identifier used for output filenames.
        output_dir: Output directory; defaults to the configured
            processed-audio directory.

    Returns:
        Tuple of (TranscriptResult, path-to-JSON, path-to-TXT).

    Raises:
        FileNotFoundError: If audio or diarization file is missing.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if meeting_id is None:
        meeting_id = audio_path.stem.replace("_processed", "")

    if diarization_path is None:
        diarization_path = audio_path.parent / f"{meeting_id}_diarization.json"
    diarization_path = Path(diarization_path)
    if not diarization_path.exists():
        raise FileNotFoundError(f"Diarization JSON not found: {diarization_path}")

    language: str | None = get("asr.language", None)
    beam_size: int = int(get("asr.beam_size", 5))
    min_overlap_ratio: float = float(get("asr.min_overlap_ratio", 0.3))

    diar_segments = sorted(_load_diarization_json(diarization_path), key=lambda item: item["start"])
    diar_starts = [item["start"] for item in diar_segments]
    diar_end_prefix = list(accumulate((item["end"] for item in diar_segments), max))
    diar_speakers = sorted({seg["speaker"] for seg in diar_segments if seg.get("speaker")})
    logger.info(
        "Loaded %d diarization segments (%d speakers)",
        len(diar_segments), len(diar_speakers),
    )

    out_dir = output_dir or get_processed_audio_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{meeting_id}_transcript.json"
    txt_path = out_dir / f"{meeting_id}_transcript.txt"

    settings = dict(get("asr", {}))
    settings["model_size"] = get("asr.model_size", "small")
    settings["language"] = get("asr.language", None)
    settings["pipeline_version"] = 3
    key = fingerprint([audio_path, diarization_path], settings)
    cached = read_cache(json_path, key)
    if cached is not None:
        result = _deserialise_result(cached)
        if not txt_path.exists():
            _save_txt(result, txt_path)
        return result, json_path, txt_path

    chunk_seconds = int(get("asr.chunk_seconds", 300))
    if chunk_seconds < 10:
        raise ValueError("asr.chunk_seconds must be at least 10")
    chunk_dir = out_dir / f"{meeting_id}_asr_chunks" / key
    transcript_segments = []
    detected_language = language
    model = None
    with sf.SoundFile(audio_path) as audio:
        sr = audio.samplerate
        if sr != 16000 or audio.channels != 1:
            raise ValueError("ASR requires 16 kHz mono audio; preprocess first")
        duration = len(audio) / sr
        for index, first in enumerate(range(0, len(audio), chunk_seconds * sr)):
            chunk_path = chunk_dir / f"{index:06d}.json"
            cached_chunk = read_cache(chunk_path, key)
            if cached_chunk is not None:
                transcript_segments.extend(TranscriptSegment(**item) for item in cached_chunk["segments"])
                detected_language = detected_language or cached_chunk.get("language")
                continue
            if model is None:
                model = _load_whisper_model()
            offset = max(0, first - 2 * sr)
            end = min(len(audio), first + (chunk_seconds + 2) * sr)
            audio.seek(offset)
            samples = audio.read(end - offset, dtype="float32")
            kwargs = dict(beam_size=beam_size, word_timestamps=True,
                          vad_filter=True, condition_on_previous_text=False,
                          temperature=0.0, task="transcribe")
            if language:
                kwargs["language"] = language
            segments_iter, info = model.transcribe(samples, **kwargs)
            chunk_language = getattr(info, "language", None)
            allowed = get("asr.allowed_languages", [])
            if not language and allowed and isinstance(chunk_language, str) and chunk_language not in allowed:
                probabilities = getattr(info, "all_language_probs", None) or []
                choices = [(code, probability) for code, probability in probabilities if code in allowed]
                if not choices:
                    raise RuntimeError("Detected language outside configured meeting languages; set MAI_ASR_LANGUAGE explicitly")
                selected_language = max(choices, key=lambda choice: choice[1])[0]
                logger.warning("Detected %s outside configured languages %s; decoding with %s", chunk_language, allowed, selected_language)
                segments_iter, info = model.transcribe(samples, **{**kwargs, "language": selected_language})
                chunk_language = selected_language
            detected_language = detected_language or chunk_language
            chunk_segments = []
            for seg in segments_iter:
                words = getattr(seg, "words", None)
                if not isinstance(words, (list, tuple)) or not words:
                    words = [seg]
                group = None
                for word in words:
                    a = max(0.0, offset / sr + float(word.start))
                    b = min(duration, offset / sr + float(word.end))
                    # Each word belongs to one central chunk, keeping overlap
                    # context without emitting duplicate boundary words.
                    midpoint = (a + b) / 2
                    if not first / sr <= midpoint < min(duration, first / sr + chunk_seconds):
                        continue
                    text = (getattr(word, "word", None) if word is not seg else seg.text) or ""
                    if not isinstance(text, str) or not text.strip() or b <= a:
                        continue
                    candidates = diar_segments[bisect_right(diar_end_prefix, a):bisect_left(diar_starts, b)]
                    speaker = attribute_speaker(a, b, candidates, min_overlap_ratio)
                    logprob = getattr(seg, "avg_logprob", None)
                    confidence = round(min(1.0, math.exp(float(logprob))), 4) if isinstance(logprob, (int, float)) else None
                    if group is not None and group.speaker == speaker and a - group.end < 1.0:
                        group.end = round(b, 3)
                        group.text += text
                    else:
                        group = TranscriptSegment(0, round(a, 3), round(b, 3), speaker, text, confidence)
                        chunk_segments.append(group)
                group = None
            for item in chunk_segments:
                item.text = item.text.strip()
            atomic_json(chunk_path, {"cache_key": key, "language": detected_language,
                                    "segments": [asdict(item) for item in chunk_segments]})
            transcript_segments.extend(chunk_segments)
            logger.info("ASR checkpoint %d: %.1f / %.1f seconds", index + 1,
                        min(duration, first / sr + chunk_seconds), duration)
    for index, segment in enumerate(transcript_segments, 1):
        segment.segment_id = index

    transcript_speakers = sorted(
        {s.speaker for s in transcript_segments if s.speaker != "UNKNOWN"}
    )

    result = TranscriptResult(
        meeting_id=meeting_id,
        language=detected_language,
        duration=round(duration, 3),
        num_speakers=len(transcript_speakers),
        speakers=transcript_speakers,
        segments=transcript_segments,
    )

    _save_json(result, json_path, key)
    _save_txt(result, txt_path)
    logger.info(
        "Transcript saved: %d segments, %d speakers — %s",
        len(transcript_segments), len(transcript_speakers), json_path,
    )
    return result, json_path, txt_path


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _save_json(result: TranscriptResult, path: Path, cache_key=None) -> None:
    """Serialise TranscriptResult to a JSON file."""
    payload = {
        "meeting_id": result.meeting_id,
        "language": result.language,
        "duration": result.duration,
        "num_speakers": result.num_speakers,
        "speakers": result.speakers,
        "segments": [asdict(s) for s in result.segments],
    }
    payload["cache_key"] = cache_key
    atomic_json(path, payload)


def _save_txt(result: TranscriptResult, path: Path) -> None:
    """Write a human-readable transcript to plain text."""
    speakers_str = ", ".join(result.speakers) if result.speakers else "none"
    lines = [
        f"Meeting ID  : {result.meeting_id}",
        f"Language    : {result.language or 'unknown'}",
        f"Duration    : {result.duration:.2f}s",
        f"Speakers    : {speakers_str}",
        "",
        "-" * 72,
        "",
    ]
    for seg in result.segments:
        ts = f"[{_fmt_ts(seg.start)} -> {_fmt_ts(seg.end)}]"
        conf = f" (conf={seg.confidence:.2f})" if seg.confidence is not None else ""
        lines.append(f"{ts}  {seg.speaker}{conf}")
        lines.append(f"  {seg.text}")
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _fmt_ts(seconds: float) -> str:
    """Format seconds as MM:SS.mmm."""
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m:02d}:{s:06.3f}"


def _deserialise_result(data: dict[str, Any]) -> TranscriptResult:
    """Reconstruct a TranscriptResult from a saved JSON dict."""
    segments = [
        TranscriptSegment(
            segment_id=s["segment_id"],
            start=s["start"],
            end=s["end"],
            speaker=s["speaker"],
            text=s["text"],
            confidence=s.get("confidence"),
        )
        for s in data.get("segments", [])
    ]
    return TranscriptResult(
        meeting_id=data["meeting_id"],
        language=data.get("language"),
        duration=data.get("duration", 0.0),
        num_speakers=data.get("num_speakers", 0),
        speakers=data.get("speakers", []),
        segments=segments,
    )
