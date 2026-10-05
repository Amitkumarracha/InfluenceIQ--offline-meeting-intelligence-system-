"""Offline Silero speech detection with bounded audio memory."""
from dataclasses import asdict, dataclass
from pathlib import Path
import soundfile as sf
import torch
from src.utils.cache import atomic_json
from src.utils.config import get
from src.utils.paths import get_processed_audio_dir


@dataclass
class SpeechSegment:
    segment_id: int
    start: float
    end: float


def _load_silero_vad():
    from silero_vad import load_silero_vad, get_speech_timestamps
    return load_silero_vad(), (get_speech_timestamps,)


def run_vad(audio_path, meeting_id=None):
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f'Processed audio not found: {audio_path}')
    meeting_id = meeting_id or audio_path.stem.replace('_processed', '')
    model, utils = _load_silero_vad()
    intervals = []
    with sf.SoundFile(audio_path) as audio:
        if audio.samplerate != 16000:
            raise ValueError(f'Expected 16000 Hz audio, got {audio.samplerate}')
        sr = audio.samplerate
        duration = len(audio) / sr
        # Overlap protects speech around block boundaries.
        for start in range(0, len(audio), 300 * sr):
            offset = max(0, start - sr)
            audio.seek(offset)
            samples = audio.read(302 * sr, dtype='float32', always_2d=True).mean(axis=1)
            found = utils[0](torch.from_numpy(samples), model, sampling_rate=sr,
                threshold=float(get('vad.threshold', .5)),
                min_speech_duration_ms=int(get('vad.min_speech_duration_ms', 250)),
                min_silence_duration_ms=int(get('vad.min_silence_duration_ms', 100)),
                return_seconds=True)
            for seg in found:
                a, b = offset / sr + float(seg['start']), min(duration, offset / sr + float(seg['end']))
                if intervals and a <= intervals[-1][1]:
                    intervals[-1][1] = max(intervals[-1][1], b)
                elif b > a:
                    intervals.append([a, b])
    segments = [SpeechSegment(i+1, round(a, 3), round(b, 3)) for i, (a, b) in enumerate(intervals)]
    out_path = get_processed_audio_dir() / f'{meeting_id}_vad.json'
    atomic_json(out_path, {'meeting_id': meeting_id, 'audio_file': str(audio_path),
        'duration': duration, 'num_segments': len(segments),
        'total_speech_duration': sum(s.end-s.start for s in segments),
        'segments': [asdict(s) for s in segments]})
    return segments, out_path
