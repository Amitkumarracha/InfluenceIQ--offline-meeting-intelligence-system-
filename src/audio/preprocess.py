"""Bounded-memory decoding of phone recordings into lossless 16 kHz PCM."""
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from src.utils.config import get
from src.utils.paths import get_processed_audio_dir


@dataclass
class AudioMetadata:
    file_name: str
    original_duration: float
    processed_duration: float
    original_sample_rate: int
    processed_sample_rate: int
    original_channels: int


def probe_audio(path):
    result = subprocess.run([
        'ffprobe', '-v', 'error', '-protocol_whitelist', 'file,pipe', '-select_streams', 'a:0',
        '-show_entries', 'stream=sample_rate,channels,duration:format=duration',
        '-of', 'json', str(path),
    ], capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise ValueError('Invalid or unsupported audio file')
    data = json.loads(result.stdout)
    if not data.get('streams'):
        raise ValueError('File contains no audio stream')
    stream = data['streams'][0]
    duration = float(data.get('format', {}).get('duration') or stream.get('duration') or 0)
    return stream, duration


def preprocess_audio(input_path, output_path=None):
    input_path = Path(input_path)
    if not input_path.is_file():
        raise FileNotFoundError(f'Audio file not found: {input_path}')
    stream, duration = probe_audio(input_path)
    target_sr = int(get('audio.sample_rate', 16000))
    out_path = Path(output_path) if output_path else get_processed_audio_dir() / (input_path.stem + '_processed.wav')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = out_path.with_suffix('.partial.wav')
    cmd = ['ffmpeg', '-nostdin', '-v', 'error', '-y', '-protocol_whitelist', 'file,pipe', '-i', str(input_path), '-map', '0:a:0', '-vn', '-ar', str(target_sr)]
    if get('audio.mono', True):
        cmd += ['-ac', '1']
    # Avoid automatic denoising/loudnorm: these can distort quiet speech and
    # cannot repair clipping, overlap, or distant microphones.
    try:
        result = subprocess.run(cmd + ['-c:a', 'pcm_s16le', str(temporary)], capture_output=True, timeout=7200)
        if result.returncode:
            raise ValueError('Audio decoding failed')
        _, processed_duration = probe_audio(temporary)
        if processed_duration <= 0:
            raise ValueError('Audio is empty')
        temporary.replace(out_path)
    finally:
        temporary.unlink(missing_ok=True)
    return out_path, AudioMetadata(input_path.name, duration, processed_duration,
                                  int(stream['sample_rate']), target_sr, int(stream['channels']))
