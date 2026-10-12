# Meet IQ — Offline Meeting Intelligence

For the complete older-versus-current code audit, environment setup, fusion implementation, developer handover, results inventory, and journal research plan, start with the [master documentation](../README.md).

Meet IQ has two local execution paths:

- **Laptop application:** React interface, FastAPI/SQLite queue, multilingual faster-whisper, local sherpa-onnx speaker separation (pyannote is an alternative) and presentation alignment, and evidence-linked reports.
- **Android prototype 0.6:** native recording/whisper.cpp, pretrained ONNX speaker separation, editable participant names/roles, extractive events and candidate decision-linked influence, PPT native-text TF-IDF fusion, local history, resumable analysis and exports. It has **no INTERNET permission**. Its candidate lineage is a lighter implementation than the Python evidence graph.

This is a tested research prototype, not a validated high-accuracy product. See [PROJECT_STATUS.md](../validation/PROJECT_STATUS.md) for measured results, implemented changes, and remaining work. The latest focused changes and speed/accuracy tradeoffs are in [EFFICIENCY_IMPROVEMENTS.md](../validation/EFFICIENCY_IMPROVEMENTS.md). Earlier workstation instructions in `NEXT_STEPS.md`, `PROJECT_EXECUTION_GUIDE.md`, and the conversion guide are historical.

The interface opens with **Record meeting**, **Upload audio**, optional **Upload PPT**, and optional vocabulary hints. **History** keeps saved meetings and edits; **Settings** holds your profile, automatic Hindi/English language selection, and advanced controls. The website has Transcript, Participants, Action items, Decisions, Influence, Events and Presentation views. The laptop supports editable identified speaker names/roles and heuristic influence estimates. Both interfaces explicitly show that meeting accuracy is unmeasured. Generative notes/questions and cross-meeting transcript-word search have been removed. Timestamp playback, saved name/role edits, exports and observed vocabulary suggestions remain available. Android accepts common recordings through local platform codecs and now analyses speakers and native PPT text. See [the current Android implementation and measurements](../validation/19_ANDROID_SPEAKERS_FUSION_AND_VALIDATION.md). Earlier UI checks are in chapter 17.

See [RUN_MANUALLY.md](RUN_MANUALLY.md) for foreground-only startup and local model setup, and [REPOSITORY_REVIEW.md](../history/REPOSITORY_REVIEW.md) for the four repository reviews and implementation choices. No third-party application code was copied into the app.

## Run on this laptop

The isolated Python 3.11 environment and local speech models have been installed.

```bash
cd '/home/amitkumar/Music/MAI Project'
bash scripts/start_app.sh
```

Open **http://127.0.0.1:8000**. Register a local account, upload audio or record in the browser, and open the generated meeting report. No email or external account is needed. Browser recording uses device storage for recovery; stop and save, then submit the recording. Keep the tab open while recording. The native Android app is the preferred path for background phone recording.

`scripts/start_app.sh` rebuilds the frontend when its inputs are newer than the existing build, then starts the API in the same terminal. Stop it with Ctrl+C. Model provisioning is a separate one-time online step. The application runs NLP analysis locally and does not contact an LLM service.

The API processes one meeting at a time. Uploads are limited to 1 GiB total by default, can contain up to 32 sequential parts, and accept WAV, MP3, M4A, MP4, WebM, OGG, FLAC and AAC. Parts are joined chronologically; these are **not synchronized microphone-array channels**. One optional PPTX is supported. Failed jobs can be retried; queued/interrupted jobs recover after restart. Transcription reuses verified completed chunks.

Reorder uploaded parts before submission. Transcription settings are saved with the job and reused on retry. Automatic language selection is scoped to Hindi/English; vocabulary hints help spellings but are not corrections or an accuracy guarantee. Expected speaker count constrains an available diarization model; it does not enable an unavailable one.

After processing, speaker clusters and estimated contribution roles are shown in **Participants**. Editing names and roles updates transcript labels, decisions, actions and influence views, and persists in History/exports. **Influence** shows the existing weighted contribution features, raw counts, source events and prototype scoring method. **Presentation** exposes extracted native slide text/tables, matched discussion and review-required quantity mismatches. The submitted report comparison and implementation boundaries are in [chapter 18](../validation/18_SUBMITTED_REPORT_FEEDBACK_AND_NLP_DELIVERY.md).

For an older UNKNOWN-only meeting, open **Overview → Analyse speakers from saved audio** after restarting the server. This reprocesses its stored audio with the speaker model and rebuilds NLP results; it cannot recover an unavailable source recording. Names are entered by users, not inferred as real-world identities. Heuristic roles describe observed contributions, not certain job titles.

### Rebuild the environment

Requires Linux, Python 3 with venv, Node/npm, FFmpeg and ffprobe. The setup script installs a separate Python 3.11 and CPU PyTorch wheels, without changing system Python.

```bash
bash scripts/setup.sh
.venv/bin/python scripts/download_models.py --slides
.venv/bin/python scripts/download_speaker_models.py
```

`environment/requirements.txt` pins the compatibility-sensitive libraries; `environment/requirements-lock.txt` captures the installed package versions. Model download is an explicit **one-time online operation**. Meeting processing defaults to offline mode, with local models under `models/hf`.

### Speaker separation

The current default uses the existing **sherpa-onnx** adapter with local segmentation and speaker-embedding weights. They have been provisioned on this laptop and verified by checksums. Inference does not require a Hugging Face token or internet connection. Fresh setup:

```bash
.venv/bin/python scripts/download_speaker_models.py
```

The public model workflow follows the [official sherpa-onnx diarization instructions](https://k2-fsa.github.io/sherpa/onnx/speaker-diarization/index.html). Automatic clustering can split or merge speakers incorrectly. The default threshold is unvalidated; set the expected speaker count in Settings when known and review attribution. A real 90-second English integration test produced four attributed clusters with an explicit four-speaker constraint; that is not a DER measurement. ONNX clustering currently reads the full recording, so bounded-memory long-meeting diarization still needs work.

The alternative `backend: pyannote` still needs authorized local weights. Accept its Hugging Face model conditions and run `scripts/download_models.py --diarization` using your locally configured token if choosing that backend.

Default `auto` mode continues transcription if speaker separation fails, labels speakers `UNKNOWN`, and shows a warning. It does not invent a speaker count. Use `--diarization required` to fail instead, or `--diarization off` to disable it explicitly. Human names are not automatically identified.

### Model profiles

`small` multilingual/int8 is the default CPU profile. `medium` has also been provisioned. On the measured ten-minute English sample, it reduced WER from 45.84% to 40.83%, while processing time increased from about 175 to 358 seconds. This does not establish Hindi/English accuracy. To choose it for the server:

```bash
MAI_ASR_MODEL=medium bash scripts/start_app.sh
```

Or provision another model explicitly:

```bash
.venv/bin/python scripts/download_models.py --asr-model medium
```

Use multilingual models, not `.en` models, for Hindi/English meetings. Language detection is automatic within the configured Hindi/English scope; set `asr.allowed_languages: []` to remove that restriction. `MAI_ASR_LANGUAGE=hi` or `en` is available for experiments; forcing a language is not a guarantee of code-switching accuracy. Model size, CPU threads, chunk duration and speaker constraints are configurable in `config/config.yaml`. The default chunk duration is now 120 seconds; `MAI_ASR_CHUNK_SECONDS=300` selects the larger throughput profile. The measured 120-second profile improved English WER but took longer overall; see the efficiency report.

### Command-line processing

```bash
.venv/bin/python scripts/process_meeting.py \
  --audio /path/to/meeting.m4a --meeting-id my_meeting --diarization auto

# Optional presentation:
.venv/bin/python scripts/process_meeting.py \
  --audio /path/to/meeting.wav --ppt /path/to/slides.pptx \
  --meeting-id my_slides_meeting --diarization required
```

Outputs: `data/processed/` contains stage artifacts and transcript chunks; `outputs/reports/` contains reports. Use a distinct meeting ID for each meeting. The API generates unique IDs; rerunning a CLI meeting invalidates changed ASR inputs and refreshes its reports.

### Local account recovery

Public reset-token endpoints are disabled. Recover an account from the laptop terminal:

```bash
.venv/bin/python scripts/reset_password.py
```

The server binds to loopback by default. The browser's recording permission requires localhost or HTTPS; merely exposing the server on a LAN HTTP address does not enable phone microphone capture. The Android native app does not need the server.

## Android app

For existing 0.5 build environments, provision the new packaged speaker dependencies with `.venv/bin/python scripts/setup_android_speakers.py`, then `bash android/build.sh`. Speaker weights are bundled; only the GGML speech model needs importing on the phone.

Install [android/build/meet-iq-debug.apk](../../android/build/meet-iq-debug.apk) on an Android 8+ ARM64 phone. This is a development APK, not a store release. It also includes x86_64 for emulator testing.

1. Transfer `models/ggml-base.bin` to the phone's Downloads directory.
2. Open InfluenceIQ → **Settings** → **Set up analysis**, then select the multilingual model. The app copies it into private storage.
3. Tap **Record meeting**, grant microphone permission, and tap **Stop & save** when finished. Alternatively, use **Upload audio**.
4. Tap **Analyse meeting**, or **Resume analysis** for interrupted work. Processing happens on the phone.
5. Review **Transcript**, **Action items**, **Decisions**, and **Analysis**. Open **Meeting options** for playback, rename or export.

Recording uses 16 kHz mono PCM, about **115 MB/hour**, and stops at six hours. A visible foreground-service notification and wake lock support recording/analysis while the screen is off. Android may still stop the process; recordings and completed analysis chunks are retained. Interruption, battery/thermal behavior, microphone quality and long meetings need physical-device validation. Analysis pauses between chunks rather than instantly interrupting native inference.

Source and build instructions: [android/README.md](../android/README.md).

## Verification

```bash
.venv/bin/python scripts/validate_setup.py
OMP_NUM_THREADS=4 bash scripts/check.sh -q
npm --prefix frontend run build
npm --prefix frontend run lint

# Uses existing local AMI audio and manual word annotations:
OMP_NUM_THREADS=4 .venv/bin/python scripts/benchmark_ami.py --seconds 600
MAI_ASR_MODEL=medium OMP_NUM_THREADS=4 .venv/bin/python scripts/benchmark_ami.py --seconds 600

# Timestamp/memory/offline smoke test, not an accuracy benchmark:
OMP_NUM_THREADS=4 .venv/bin/python scripts/smoke_long_offline.py
```

For a clean speed comparison, use fresh meeting IDs/cache directories and avoid other heavy workloads. Tests mock model boundaries where appropriate; integration results are reported separately. Do not equate passing tests or a model's confidence score with measured transcription accuracy.

## Source layout

| Directory/file | Responsibility |
|---|---|
| `backend/api.py` | Local accounts, ownership checks, uploads, durable queued jobs, playback and export |
| `src/pipeline/orchestrator.py` | Complete audio-to-report workflow |
| `src/audio/` | Streaming decode, packaged VAD, diarization, chunked ASR and word-level speaker attribution |
| `src/ppt/`, `src/fusion/` | Optional slide extraction, embeddings and transcript/slide alignment |
| `src/meeting/` | Event rules, evidence links, decision candidates, interaction and influence estimates |
| `src/report/` | JSON, Markdown, HTML and CSV reports |
| `src/evaluation/` | WER, permutation-aware DER, event/decision metrics and ablations |
| `frontend/` | Responsive browser UI and recoverable IndexedDB recording |
| `android/` | Standalone on-device Android prototype and JNI bindings |
| `scripts/`, `tests/` | Setup, provisioning, runners, benchmarks and regression checks |
| `.venv/`, `.runtime/`, `models/` | Local environment, private runtime artifacts and model weights; ignored by Git |
| `AMI_dataset/`, `data/`, `outputs/` | Existing research data and generated artifacts; not application source |

Model references: [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [whisper.cpp](https://github.com/ggml-org/whisper.cpp), and [pyannote 3.1](https://huggingface.co/pyannote/speaker-diarization-3.1). Review their licenses and the AMI dataset terms before redistributing models or data.

Training from scratch is not required for the pretrained baseline. A human-supervised influence-weight training/evaluation script is now available; see [training and multimodal research](../research/20_TRAINING_DATA_AND_MULTIMODAL_RESEARCH.md). [Workstation deployment files](../operations/21_OFFLINE_AND_WORKSTATION_DEPLOYMENT.md) prepare optional CPU/GPU website hosting. No remote host has been deployed; Android cloud access currently uses an explicit browser link, with separate local/server histories.
