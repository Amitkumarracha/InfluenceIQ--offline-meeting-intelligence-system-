# Manual startup — 5 October 2026

All commands below run in your terminal. Keep long-running servers in separate visible terminals and stop them with Ctrl+C. No startup service is required.

## Laptop app

```bash
cd '/home/amitkumar/Music/MAI Project'
bash start_app.sh
```

Open **http://127.0.0.1:8000**. Register a local account, record or upload audio, choose transcription settings, and submit. Existing multilingual small/medium models can be selected in the UI. Search, transcript playback and JSON/Markdown/TXT/SRT/VTT/CSV exports do not require an AI notes model.

## Optional local AI notes and answers

Ollama was not installed or started during this change. The app uses only `127.0.0.1:11434`, ignores proxy environment variables, disables redirects, and rejects cloud/remote model aliases. Start Ollama with cloud features disabled, as described in the [official FAQ](https://docs.ollama.com/faq#how-do-i-disable-ollama-cloud-features).

If you already have Ollama, use its `ollama` command in place of `.runtime/ollama/bin/ollama` below. For this x86_64 Linux laptop, an installation confined to the project can be extracted manually. This adapts the [official Linux manual installation](https://docs.ollama.com/linux#manual-install) to a project directory; it does not install a system service. `tar` needs zstd support and sufficient disk space for the archive and model.

One-time download while online:

```bash
cd '/home/amitkumar/Music/MAI Project'
mkdir -p .runtime/ollama
curl -fL https://ollama.com/download/ollama-linux-amd64.tar.zst -o .runtime/ollama-package.tar.zst
tar --zstd -xf .runtime/ollama-package.tar.zst -C .runtime/ollama
```

Terminal A — keep this running in the foreground:

```bash
cd '/home/amitkumar/Music/MAI Project'
OLLAMA_NO_CLOUD=1 OLLAMA_HOST=127.0.0.1:11434 OLLAMA_MODELS="$PWD/models/ollama" .runtime/ollama/bin/ollama serve
```

Terminal B — provision a local model once while online; this is an example starting model, not a measured accuracy recommendation:

```bash
cd '/home/amitkumar/Music/MAI Project'
OLLAMA_HOST=127.0.0.1:11434 .runtime/ollama/bin/ollama pull qwen2.5:3b
```

[Model information](https://ollama.com/library/qwen2.5:3b). Check model terms before redistributing weights. A larger multilingual model can be selected if your RAM permits it. The app enumerates installed local GGUF models; refresh the browser after provisioning, then use **Generate notes** or **Ask meeting**. Once downloaded, these models can run with internet disconnected. Retrying notes reuses completed parts for the same transcript/model. The previous successful notes remain available if regeneration fails.

Terminal B — after the pull completes, run the laptop app:

```bash
bash start_app.sh
```

## Provision another speech model

Optional, one-time online download:

```bash
.venv/bin/python scripts/download_models.py --asr-model large-v3-turbo
```

Refresh the app to select the downloaded multilingual model. Compare WER on your own annotated audio before claiming better accuracy. For Hindi/English meetings, avoid English-only `.en` models. Speaker separation still needs the pyannote gates and an authorized local token; see the README.

## Android

Install the rebuilt `android/build/meet-iq-debug.apk` on an Android 8+ ARM64 device. Import `models/ggml-base.bin`, record or import a **16 kHz mono, 16-bit PCM WAV**, then select **Analyse / resume**. Choose Hindi/English and optional vocabulary hints before analysis. Completed chunks survive interruptions. Changing the model, audio, language or vocabulary starts a new analysis rather than reusing incompatible chunks.

To convert another recording on the laptop for phone import:

```bash
ffmpeg -i '/path/to/meeting.m4a' -ac 1 -ar 16000 -c:a pcm_s16le '/path/to/meeting-phone.wav'
```

Tap timestamps for playback, search transcript words, rename a meeting, and export Markdown/JSON/WAV. The APK has no INTERNET permission. Phone semantic AI summaries and speaker separation are not implemented; Android uses event candidates and explicit UNKNOWN speakers. This is a debug prototype, not a store release.

Rebuild manually when needed:

```bash
bash android/test.sh
bash android/build.sh
```

## Checks

```bash
OMP_NUM_THREADS=4 .venv/bin/python -m pytest -q
npm --prefix frontend run build
npm --prefix frontend run lint
node scripts/test_browser_offline.cjs
bash android/test.sh
```

The browser check needs the existing `.runtime/browser` Playwright installation or `MAI_PLAYWRIGHT` pointing to one. It intercepts local fixture responses and starts no web/API server. Its microphone is synthetic and AI notes are mocked; those checks do not measure real recording or model accuracy.

## Focused efficiency settings — 6 October 2026

No extra installation is needed for the new decoder, Hindi-safe search, partial previews, silence skipping or bilingual guards. Start the application in your own terminal with `bash start_app.sh`.

The default is 120-second speech chunks. For 300-second chunks:

```bash
MAI_ASR_CHUNK_SECONDS=300 bash start_app.sh
```

On the measured English sample, 300-second chunks processed faster overall, while 120-second chunks produced lower WER and earlier previews. Changing chunk size invalidates incompatible speech checkpoints. See [EFFICIENCY_IMPROVEMENTS.md](EFFICIENCY_IMPROVEMENTS.md).

For optional slide matching without a neural embedding model, set this existing section in `config.yaml`:

```yaml
alignment:
  method: tfidf
```

Keep the other alignment fields. Restore `method: embeddings` to use the existing default. TF-IDF compares shared words; it does not translate between Hindi and English or recognize paraphrases reliably. Neither method establishes whether a slide supports a claim.

## Optional ONNX speaker separation — manual provisioning only

This adapter is implemented for the **laptop**, not integrated into the Android APK. The default pyannote workflow remains available. If you want to evaluate the optional backend, install it yourself while online:

```bash
.bootstrap/bin/uv pip install --python .venv/bin/python sherpa-onnx
.bootstrap/bin/uv pip check --python .venv/bin/python
```

Download a compatible pyannote segmentation ONNX model and a speaker embedding ONNX model from the [official diarization model instructions](https://k2-fsa.github.io/sherpa/onnx/speaker-diarization/index.html). Quantized weights are optional; compare accuracy before adopting them. Extract the files locally, then configure their actual paths:

```yaml
diarization:
  backend: sherpa-onnx
  onnx:
    segmentation_model: models/diarization/segmentation/model.int8.onnx
    embedding_model: models/diarization/embedding.onnx
    cluster_threshold: 0.5
```

These are example paths, not files already installed. Keep the remaining diarization settings. Leave `min_speakers` and `max_speakers` as `null`; this adapter supports an exact speaker count or automatic clustering. Use `--diarization required` for an evaluation so a failed model cannot silently fall back to UNKNOWN speakers:

```bash
.venv/bin/python scripts/process_meeting.py --audio '/path/to/meeting.wav' \
  --meeting-id onnx_trial --diarization required
```

The clustering threshold is an unvalidated starting setting. The adapter consumes the complete recording for global clustering; it does not yet provide bounded-memory streaming speaker separation. No real ONNX speed, memory or DER result is available from this upgrade. Restore `backend: pyannote` to return to the existing method.

## Measure Hindi / English / Hinglish recognition

Prepare short phone-recorded excerpts and independently checked human transcripts. Keep evaluation speakers and meetings separate from any future training. Put one JSON object per line in a UTF-8 manifest, for example:

```json
{"id":"room1","audio":"room1.wav","reference":"कल budget review करेंगे और report भेजेंगे।","group":"hinglish","language":"auto"}
{"id":"room2","audio":"room2.wav","reference":"Please send the revised report tomorrow.","group":"english","language":"en"}
```

Paths are relative to the manifest directory. Valid groups: `hindi`, `english`, `hinglish`; language hints: `auto`, `hi`, `en`. Here Hinglish means spoken Hindi–English switching. Define a consistent reference script policy, preferably Hindi words in Devanagari and English words in Latin; Romanized Hindi and Devanagari are not silently equated by the evaluator.

```bash
OMP_NUM_THREADS=4 .venv/bin/python scripts/evaluate_recordings.py \
  --manifest '/path/to/phone-test.jsonl' \
  --output outputs/evaluation/phone-small.json --model small
```

The command uses installed local models, saves reports/checkpoints, and aggregates WER by reference word count within each group. Repeated runs may reuse transcription, so this command is an accuracy workflow rather than a speed benchmark. Its human references are retained in your manifest; reported metrics do not replace speaker, decision or task evaluations.
