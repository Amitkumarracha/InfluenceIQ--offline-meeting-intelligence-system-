"""Decode ordered upload parts into one durable recording, without part WAVs."""
import subprocess
import tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
from src.utils.cache import atomic_json, fingerprint, read_cache


def decode_parts(paths, destination):
    paths = [Path(path) for path in paths]
    if not paths:
        raise ValueError('No audio parts supplied')
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    key = fingerprint(paths, {'sample_rate': 16000, 'channels': 1, 'version': 1})
    manifest = destination.with_suffix('.decode.json')
    saved = read_cache(manifest, key)
    if saved and destination.is_file() and fingerprint([destination]) == saved.get('output_hash'):
        return destination
    temporary = destination.with_suffix('.partial.wav')
    try:
        with sf.SoundFile(temporary, 'w', samplerate=16000, channels=1, subtype='PCM_16') as output:
            for path in paths:
                command = ['ffmpeg', '-nostdin', '-v', 'error', '-protocol_whitelist', 'file,pipe',
                           '-i', str(path), '-map', '0:a:0', '-vn', '-ar', '16000', '-ac', '1',
                           '-f', 's16le', '-c:a', 'pcm_s16le', 'pipe:1']
                # A file for stderr avoids a full pipe deadlock on malformed input.
                with tempfile.TemporaryFile() as errors:
                    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors)
                    try:
                        pending = b''
                        while block := process.stdout.read(32000 * 10):
                            block = pending + block
                            length = len(block) // 2 * 2
                            output.write(np.frombuffer(block[:length], dtype='<i2'))
                            pending = block[length:]
                        if process.wait(timeout=60) or pending:
                            raise ValueError('Audio part decoding failed')
                    finally:
                        process.stdout.close()
                        if process.poll() is None:
                            process.kill()
                        process.wait()
            if output.frames == 0:
                raise ValueError('Recording contains no audio')
        temporary.replace(destination)
        atomic_json(manifest, {'cache_key': key, 'output_hash': fingerprint([destination])})
        return destination
    finally:
        temporary.unlink(missing_ok=True)
