# Audio implementation and recovery

Layout update, 8 October 2026: use the [master documentation](../README.md) and [structure/performance update](../validation/22_STRUCTURE_PERFORMANCE_AND_GAPS.md). Historical comparisons and measurements below describe their stated audit date. The older working tree is now archived; current paths and runtime are described in the update.

[Handbook index](../handbook/README.md)

## Decode and preprocessing

[`parts.py`](../../src/audio/parts.py) concatenates chronological upload parts by decoding each with FFmpeg to 16 kHz mono PCM16. It consumes bounded pipe blocks rather than making a temporary WAV per part. One durable final WAV remains for playback and restart; originals remain under private uploads.

The decode cache key hashes ordered input bytes and normalization settings. A saved result is reused only when the final output hash also matches. The writer uses a partial WAV, validates nonempty output, renames on success, and saves an atomic manifest. This is sequential-part assembly, not simultaneous microphone fusion, beamforming, or source separation.

[`preprocess.py`](../../src/audio/preprocess.py) probes the audio stream, restricts FFmpeg to file/pipe protocols, converts to target sample rate/channels, and checks errors. Main workflow reuses nonempty PCM16 mono 16 kHz WAVs. Other formats are converted with an atomic partial file. There is no automatic loudness normalization, denoising, or clipping repair.

The older preprocessing path loaded the full waveform, averaged channels, resampled with SciPy, and wrote another WAV. The current version reduces audio buffering and duplicate outputs; model memory and full-recording diarization can still dominate total RAM.

## Voice activity detection

Standalone [`vad.py`](../../src/audio/vad.py) loads packaged Silero weights and reads 300-second blocks with approximately one-second preceding overlap and a 302-second read span. Detected intervals are moved to absolute time and merged when overlapping. YAML controls threshold 0.5, minimum speech 250 ms, minimum silence 100 ms.

Standalone VAD is used by the stage runner. The complete orchestrator instead uses ASR `vad_filter=True`. Its detected standalone VAD JSON is not fed to pyannote or to a learned fusion model.

## Laptop ASR

[`asr.py`](../../src/audio/asr.py) defaults to multilingual Whisper small, CPU/int8, four threads, beam size 5. The model is loaded locally and lazily. A CUDA compatibility loader/fallback was already in the older source; explicit local-files-only loading and current chunked behavior are later improvements.

Each central interval is 120 seconds by default. Two seconds of audio context are read before and after the interval when available. Decoding uses word timestamps, temperature 0, transcription rather than translation, faster-whisper VAD, and `condition_on_previous_text=False`. Vocabulary is passed as hotword hints; generated previous text is not carried into the next chunk.

Words are retained only when their absolute-time midpoint belongs to that central interval. This assigns boundary words to one interval while still providing acoustic context. Speaker changes split output groups; adjacent words from one speaker can be grouped within an ASR segment. These operations do not guarantee perfect word-boundary recognition.

Automatic detected language is restricted to `en`/`hi` by configuration. If another language is detected, available language probabilities select the highest allowed language and decoding is retried. A single selected language per chunk is not a trained code-switching model. Set `allowed_languages: []` for an unrestricted experiment and record that decision.

Exact all-zero read spans skip inference before model loading. Quiet speech, noise, and nonzero silence still take the normal VAD/ASR path. Recording quality contains zero-sample ratio, near-full-scale sample ratio, and peak amplitude. These describe the signal, not recognition correctness.

## Speaker diarization and attribution

[`diarization.py`](../../src/audio/diarization.py) supports pyannote by default and an optional [`sherpa-onnx` adapter](../../src/audio/onnx_diarization.py). pyannote requires authorized cached weights; none were present at inspection. Its device defaults to CPU and optional exact/min/max speaker-count constraints are validated. Consecutive same-speaker turns may merge within 0.5 seconds. Clusters are renamed by first appearance to `SPEAKER_00`, etc.; these are not real-person identities.

ASR attributes each word to the speaker with maximum unioned temporal overlap. Unioning avoids double counting repeated same-speaker tracks. A minimum overlap fraction of 0.3 is required. No sufficient overlap or an exact best-speaker tie returns `UNKNOWN`. Bisected interval indexes reduce the candidate search range.

The full orchestrator supports:

- `auto`: try diarization, continue with UNKNOWN on failure and show a warning.
- `required`: propagate diarization failure.
- `off`: save an empty diarization artifact and transcribe without speaker identity.

The optional ONNX adapter needs manually configured segmentation and embedding model files plus `sherpa-onnx`. It uses the upstream offline full-recording clustering API and reads the full recording into an array. It is not bounded-memory streaming diarization. Only mocked adapter tests exist here; no real ONNX DER/memory/speed benefit is established.

Multiple simultaneous voices are not acoustically separated by temporal word attribution. Neither context overlap nor a requested speaker count repairs overlapping audio.

## Checkpoint identity and semantics

The ASR key is SHA-256 over audio bytes, diarization bytes, ASR configuration, effective model/language/vocabulary/chunk settings, and pipeline version 5. Completed chunk JSON lives under:

```text
data/processed/audio/<meeting_id>_asr_chunks/<cache_key>/<index>.json
```

Each saved chunk contains its key, language, signal-quality statistics, and attributed segments. Atomic writes flush/fsync and replace. Completed chunks and complete transcripts are reused only when the key matches. A missing TXT file can be regenerated from cached JSON. Content/settings changes invalidate reuse.

The key records the model name/configuration, not the downloaded model binary hash. Replacing weights under the same model name/revision cache location requires deliberate experimental cache invalidation and a separately recorded model revision. Android uses model-byte hashing; do not describe laptop/Android keys as identical.

Live processing previews retain the latest 50 segments plus rule candidates. They appear after ingestion and completed ASR chunks. Speaker separation happens before ASR, so a long diarization stage can delay the first preview. This is not microphone-time live transcription or incremental full decision-graph analysis.

## Android differences

Android records at 16 kHz, mono PCM16: 32,000 bytes/s, about 115.2 MB/hour in decimal units. It has a six-hour recording ceiling, a foreground notification, wake lock, recoverable WAV handling, and native whisper.cpp inference.

Central chunks are 120 seconds with two seconds of context. The JNI path returns segment-level results; midpoint ownership is applied to those segments, rather than laptop word-level speaker attribution. Checkpoint identity is `v3:<model hash>:<audio hash>:<language>:<hints>`. Completed chunks and partial reports survive restart; analysis pause completes the current native chunk before stopping.

Android speaker labels remain UNKNOWN, and it has no diarization model. Actual noise/overlap/code-switching quality and physical-phone battery/thermal/long-recording behavior remain unmeasured. See [08](08_APPLICATIONS_API_FRONTEND_ANDROID.md).
