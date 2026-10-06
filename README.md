# Meet IQ — Offline Meeting Intelligence

Meet IQ has two local execution paths:

- **Laptop application:** React interface, FastAPI/SQLite queue, multilingual faster-whisper, optional pyannote speaker separation and presentation alignment, and evidence-linked reports.
- **Android prototype:** native microphone recording, whisper.cpp inference, timestamped Hindi/English/Hinglish event candidates, local history, resumable analysis, and exports. It has **no INTERNET permission**. It currently does **not** perform speaker separation or the laptop's full interaction/influence analysis.

This is a tested research prototype, not a validated high-accuracy product. See [PROJECT_STATUS.md](PROJECT_STATUS.md) for measured results, implemented changes, and remaining work. The latest focused changes and speed/accuracy tradeoffs are in [EFFICIENCY_IMPROVEMENTS.md](EFFICIENCY_IMPROVEMENTS.md). Earlier workstation instructions in `NEXT_STEPS.md`, `PROJECT_EXECUTION_GUIDE.md`, and the conversion guide are historical.

The latest app includes local AI notes with checked transcript quotations, meeting questions and library search, per-meeting speech model/language/vocabulary/speaker-count settings, visible transcription progress, timestamp playback, and full Markdown/text/subtitle/CSV exports. Browser recording supports microphone selection, level monitoring, pause/resume and optional shared-tab audio. Android adds local WAV import, playback, searchable transcript pages, meeting titles, Markdown export and overlapping transcription context.

See [RUN_MANUALLY.md](RUN_MANUALLY.md) for foreground-only startup and optional local AI setup, and [REPOSITORY_REVIEW.md](REPOSITORY_REVIEW.md) for the four repository reviews and implementation choices. No third-party application code was copied into the app.

## Run on this laptop

The isolated Python 3.11 environment and local speech models have been installed.

```bash
cd '/home/amitkumar/Music/MAI Project'
bash start_app.sh
```

Open **http://127.0.0.1:8000**. Register a local account, upload audio or record in the browser, and open the generated meeting report. No email or external account is needed. Browser recording uses device storage for recovery; stop and save, then submit the recording. Keep the tab open while recording. The native Android app is the preferred path for background phone recording.

`start_app.sh` builds the current frontend before starting the API in the same terminal. Stop it with Ctrl+C. Model provisioning and Ollama startup are manual; the app does not start them.

The API processes one meeting at a time. Uploads are limited to 1 GiB total by default, can contain up to 32 sequential parts, and accept WAV, MP3, M4A, MP4, WebM, OGG, FLAC and AAC. Parts are joined chronologically; these are **not synchronized microphone-array channels**. One optional PPTX is supported. Failed jobs can be retried; queued/interrupted jobs recover after restart. Transcription reuses verified completed chunks.

Reorder uploaded parts before submission. Transcription settings are saved with the job and reused on retry. Automatic language selection is scoped to Hindi/English; vocabulary hints help spellings but are not corrections or an accuracy guarantee. Expected speaker count constrains an available diarization model; it does not enable an unavailable one.

After processing, **Generate notes** uses an already installed local Ollama model. Long transcripts are split into bounded UTF-8 parts; completed notes parts are checkpointed by transcript/model digest. All parts are processed, then cited notes are deduplicated without a lossy global synthesis step. Every displayed note includes an exact quote from a cited segment; unknown owners/deadlines stay empty. Quote checks establish source provenance, not semantic truth. Q&A searches relevant passages and uses those retrieved passages as model context; it does not claim exhaustive understanding of every meeting. Search works without Ollama. Speaker aliases and meeting titles are saved locally and included in exports.

### Rebuild the environment

Requires Linux, Python 3 with venv, Node/npm, FFmpeg and ffprobe. The setup script installs a separate Python 3.11 and CPU PyTorch wheels, without changing system Python.

```bash
bash scripts/setup.sh
.venv/bin/python scripts/download_models.py --slides
```

`requirements.txt` pins the compatibility-sensitive libraries; `requirements-lock.txt` captures the installed package versions. Model download is an explicit **one-time online operation**. Meeting processing defaults to offline mode, with local models under `models/hf`.

### Speaker separation

The transferred model credentials did not grant access. To enable it:

1. Accept the conditions for [speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1) and [segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0).
2. Put an authorized `HF_TOKEN` in `.env` locally. Never commit it or paste it into chat.
3. Run `.venv/bin/python scripts/download_models.py --diarization` while online.

Default `auto` mode continues transcription if speaker separation fails, labels speakers `UNKNOWN`, and shows a warning. It does not invent a speaker count. Use `--diarization required` to fail instead, or `--diarization off` to disable it explicitly. Human names are not automatically identified.

### Model profiles

`small` multilingual/int8 is the default CPU profile. `medium` has also been provisioned. On the measured ten-minute English sample, it reduced WER from 45.84% to 40.83%, while processing time increased from about 175 to 358 seconds. This does not establish Hindi/English accuracy. To choose it for the server:

```bash
MAI_ASR_MODEL=medium bash start_app.sh
```

Or provision another model explicitly:

```bash
.venv/bin/python scripts/download_models.py --asr-model medium
```

Use multilingual models, not `.en` models, for Hindi/English meetings. Language detection is automatic within the configured Hindi/English scope; set `asr.allowed_languages: []` to remove that restriction. `MAI_ASR_LANGUAGE=hi` or `en` is available for experiments; forcing a language is not a guarantee of code-switching accuracy. Model size, CPU threads, chunk duration and speaker constraints are configurable in `config.yaml`. The default chunk duration is now 120 seconds; `MAI_ASR_CHUNK_SECONDS=300` selects the larger throughput profile. The measured 120-second profile improved English WER but took longer overall; see the efficiency report.

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

Install [android/build/meet-iq-debug.apk](android/build/meet-iq-debug.apk) on an Android 8+ ARM64 phone. This is a development APK, not a store release. It also includes x86_64 for emulator testing.

1. Transfer `models/ggml-base.bin` to the phone's Downloads directory.
2. Open Meet IQ Offline and select **Import multilingual Whisper model**. The app copies it into private storage.
3. Grant microphone permission, record a meeting, and tap **Stop recording**.
4. Select the meeting and tap **Analyse / resume**. Processing happens on the phone.
5. View timestamped transcript/event candidates; export JSON or original WAV when needed.

Recording uses 16 kHz mono PCM, about **115 MB/hour**, and stops at six hours. A visible foreground-service notification and wake lock support recording/analysis while the screen is off. Android may still stop the process; recordings and completed analysis chunks are retained. Interruption, battery/thermal behavior, microphone quality and long meetings need physical-device validation. Analysis pauses between chunks rather than instantly interrupting native inference.

Source and build instructions: [android/README.md](android/README.md).

## Verification

```bash
.venv/bin/python scripts/validate_setup.py
OMP_NUM_THREADS=4 .venv/bin/python -m pytest -q
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
| `api.py` | Local accounts, ownership checks, uploads, durable queued jobs, playback and export |
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
