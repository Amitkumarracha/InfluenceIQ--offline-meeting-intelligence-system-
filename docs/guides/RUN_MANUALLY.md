# Manual startup — updated 7 October 2026

All commands below run in your terminal. Keep long-running servers in separate visible terminals and stop them with Ctrl+C. No startup service is required.

## Laptop app

```bash
cd '/home/amitkumar/Music/MAI Project'
bash scripts/start_app.sh
```

Open **http://127.0.0.1:8000**. Register a local account, record or upload audio, choose transcription settings, and submit. Existing multilingual small/medium models can be selected in the UI. Search, transcript playback and JSON/Markdown/TXT/SRT/VTT/CSV exports do not require an AI notes model.

## NLP and speaker analysis

The active app has no generative notes/chat, LLM API or cross-meeting transcript-word search. Its structured overview, events, decisions, roles and influence use the local speech/speaker models and deterministic NLP modules. Restart the foreground app after source updates so its API and built website match.

Local speaker models are provisioned on this laptop. On a fresh installation:

```bash
.venv/bin/python scripts/download_speaker_models.py
.venv/bin/python scripts/validate_setup.py
```

This is an explicit one-time online download; inference thereafter is local. For an older UNKNOWN-only meeting, open Overview and choose **Analyse speakers from saved audio**. It reuses saved job options and rebuilds speaker attribution and downstream analysis. If the saved source is missing, upload the original audio again. The default speaker clustering needs review; set a known expected count under advanced Settings for controlled experiments.

## Provision another speech model

Optional, one-time online download:

```bash
.venv/bin/python scripts/download_models.py --asr-model large-v3-turbo
```

Refresh the app to select the downloaded multilingual model. Compare WER on your own annotated audio before claiming better accuracy. For Hindi/English meetings, avoid English-only `.en` models. The default ONNX speaker backend needs the provisioned local files; the alternative pyannote backend still needs authorized weights. See the README.

## Android

Install the rebuilt `android/build/meet-iq-debug.apk` on an Android 8+ ARM64 device. Import `models/ggml-base.bin`, record or upload common audio (including tested MP3/M4A/WAV), then select **Analyse meeting** or **Resume analysis**. Choose Hindi/English and optional vocabulary hints before analysis. Completed chunks survive interruptions. Changing the model, audio, language or vocabulary starts a new analysis rather than reusing incompatible chunks.

Optional manual conversion, if a particular phone codec cannot decode the source:

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
OMP_NUM_THREADS=4 bash scripts/check.sh -q
npm --prefix frontend run build
npm --prefix frontend run lint
node scripts/test_browser_offline.cjs
bash android/test.sh
```

The browser check needs the existing `.runtime/browser` Playwright installation or `MAI_PLAYWRIGHT` pointing to one. It intercepts local fixture responses and starts no web/API server. Its microphone and API responses are fixtures; those checks do not measure real recording or model accuracy.

## Focused efficiency settings — 6 October 2026

No extra installation is needed for the new decoder, Hindi-safe search, partial previews, silence skipping or bilingual guards. Start the application in your own terminal with `bash scripts/start_app.sh`.

The default is 120-second speech chunks. For 300-second chunks:

```bash
MAI_ASR_CHUNK_SECONDS=300 bash scripts/start_app.sh
```

On the measured English sample, 300-second chunks processed faster overall, while 120-second chunks produced lower WER and earlier previews. Changing chunk size invalidates incompatible speech checkpoints. See [EFFICIENCY_IMPROVEMENTS.md](../validation/EFFICIENCY_IMPROVEMENTS.md).

For optional slide matching without a neural embedding model, set this existing section in `config/config.yaml`:

```yaml
alignment:
  method: tfidf
```

Keep the other alignment fields. Restore `method: embeddings` to use the existing default. TF-IDF compares shared words; it does not translate between Hindi and English or recognize paraphrases reliably. Neither method establishes whether a slide supports a claim.

## Local speaker models and real integration check

The default laptop backend is **sherpa-onnx 1.13.8**, installed through the project requirements, using `models/diarization/segmentation.onnx` and `embedding.onnx`. Provisioning script checks the pinned SHA-256 hashes and writes provenance in `models/diarization/provisioning.json`. This follows the [official public model instructions](https://k2-fsa.github.io/sherpa/onnx/speaker-diarization/index.html). No cloud diarization service is used.

Leave `min_speakers` and `max_speakers` null. Automatic clustering uses a prototype threshold; an exact count can be passed to the CLI or through Settings. The global clustering adapter reads the recording into memory; independent chunks would lose consistent speaker identities. Two-hour memory and DER still need evaluation.

Run a real offline integration check on your own audio/PPT:

```bash
OMP_NUM_THREADS=4 .venv/bin/python scripts/smoke_report_scope.py \
  --audio '/path/to/meeting.wav' --ppt '/path/to/slides.pptx' \
  --speakers 4 --id speaker_slide_smoke
```

Omit `--ppt` or `--speakers` when unavailable. This script blocks socket connections and checks that the pipeline returns participant/influence records and presentation links. It does not measure accuracy, and repeated IDs can reuse checkpoints. Use fresh IDs and checked references for benchmarks.

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

## Android 0.6 update

Rebuild/install the [current APK](../../android/build/meet-iq-debug.apk). Speaker models are bundled; import the multilingual GGML speech model once. Use Participants to edit names/roles, Analysis for contribution features/evidence, and Presentation for matched native slide text. After replacing a PPT, choose **Overview → Update analysis**. Unchanged ASR/speaker caches are reused. Known participant count is optional in Settings.

Speaker processing currently supports up to one hour; longer meetings retain transcription. Phone/runtime limits and measured recognition results are in [chapter 19](../validation/19_ANDROID_SPEAKERS_FUSION_AND_VALIDATION.md). Training needs independent human labels; see [20](../research/20_TRAINING_DATA_AND_MULTIMODAL_RESEARCH.md). The optional HTTPS cloud link opens a browser; it does not upload/synchronize app history. The server launch guide is [21](../operations/21_OFFLINE_AND_WORKSTATION_DEPLOYMENT.md).
