"""Bounded, ephemeral recording previews; final diarization uses the complete audio."""
import io
import wave

MAX_BYTES = 30 * 16000 * 2 + 4096


def decode_preview(payload):
    import numpy as np
    if len(payload) > MAX_BYTES:
        raise ValueError('Preview exceeds 30 seconds')
    with wave.open(io.BytesIO(payload), 'rb') as audio:
        if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) != (16000, 1, 2):
            raise ValueError('Preview requires 16 kHz mono PCM16 WAV')
        frames = audio.getnframes()
        if not 16000 <= frames <= 30 * 16000:
            raise ValueError('Preview must contain 1–30 seconds')
        pcm = audio.readframes(frames)
        if len(pcm) != frames * 2:
            raise ValueError('Truncated preview audio')
    return np.frombuffer(pcm, dtype='<i2').astype(np.float32) / 32768


def transcribe_preview(samples, model_size, language, vocabulary):
    from src.audio.asr import _load_whisper_model
    from src.utils.config import get
    model = _load_whisper_model(model_size or None)
    options = dict(language=None if language == 'auto' else language,
                   beam_size=1, vad_filter=True, condition_on_previous_text=False,
                   hotwords=vocabulary.strip() or None)
    segments, info = model.transcribe(samples, **options)
    allowed = get('asr.allowed_languages', [])
    if language == 'auto' and allowed and info.language not in allowed:
        choices = [(code, probability) for code, probability in
                   (getattr(info, 'all_language_probs', None) or []) if code in allowed]
        if not choices:
            raise ValueError('Select Hindi or English explicitly for this recording')
        options['language'] = max(choices, key=lambda item: item[1])[0]
        segments, info = model.transcribe(samples, **options)
    return {'segments': [{'start': s.start, 'end': s.end, 'text': s.text.strip(),
                          'speaker': 'UNKNOWN'} for s in segments],
            'language': info.language, 'draft': True}
