# Run the current project — 19 October 2026

Run these plain terminal commands from this laptop. The backend is now `backend/api.py`; the old root-level `api.py` no longer exists. Dependencies and local speech/speaker/slide models are already provisioned. Ports 8000 and 5173 are currently used by other local services (5173 belongs to a Docker-hosted service). The commands below use backend port 8001 and frontend port 5174 without stopping those services.

## Terminal 1: backend

```sh
cd "/home/amitkumar/Music/MAI Project"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_HUB_DISABLE_TELEMETRY=1
export OMP_NUM_THREADS=4
export MAI_HOST=127.0.0.1
export MAI_PORT=8001
.venv/bin/python -m backend.api
```

Keep it running. API: `http://127.0.0.1:8001`. The built website is also served at this address.

## Terminal 2: frontend development

```sh
cd "/home/amitkumar/Music/MAI Project/frontend"
export MAI_BACKEND_URL=http://127.0.0.1:8001
npm run dev -- --host 127.0.0.1 --port 5174 --strictPort
```

Open `http://127.0.0.1:5174`. Register/login with a local account, then record or upload audio and optionally a PPTX. API calls are proxied to port 8001. Stop either server with Ctrl+C. Do not run two backend instances against the same runtime/database.

## Website processing and review

After **Analyse meeting**, the page shows upload progress, measured audio-stage progress, elapsed processing time, estimated overall progress and an ETA when comparable local timings are available. Draft transcript chunks appear before speaker analysis finishes; completed sections open automatically. Open a completed meeting's Overview to see its processing time. Microphone recording now also provides bounded 15-second local draft previews. Busy preview windows are disclosed; the complete saved recording is used for final analysis.

Leave **Expected speakers** empty if unknown. Review automatic clusters before interpreting influence; an unusually high count is flagged. Use automatic rerun if the count is unknown. When the actual number is known, use **Overview → Review speaker separation** to reanalyse with that count. Groups may change, so review names and roles again. Edit names/roles in **Participants**; the transcript and evidence use those labels too. Explicit self-introductions can suggest names, which still need review.

Select or add multiple audio files and up to 32 `.pptx` presentations. Reorder or remove them before analysis; audio parts join into one meeting and presentation slides combine in the listed order. Convert binary `.ppt` to `.pptx` first. The backend checks presentations before audio inference. Audio accepts WAV, MP3, M4A, MP4, FLAC, OGG, WebM, AAC, OPUS, WMA, AIFF/AIF, AMR and 3GP when FFmpeg can decode them.

The updated backend is running on port 8001, with logs in `.runtime/backend-web.log`. Do not start a second backend. For a later source update, let current jobs finish, stop the existing backend, then run Terminal 1's command. The frontend development server updates source changes automatically.

See [website validation and remaining limits](../validation/28_WEBSITE_PROCESSING_2026_10_19.md) for the measured timings, speaker issue and outstanding Hindi/Hinglish accuracy checks. No model download or installation is needed for these changes.

## Terminal 3: Samsung/Android phone

Enable USB debugging, connect the phone, accept its authorization prompt and list devices:

```sh
cd "/home/amitkumar/Music/MAI Project"
export PATH="/home/amitkumar/Android/Sdk/platform-tools:$PATH"
adb devices
```

Replace `PHONE_SERIAL` with the phone's actual device serial:

```sh
adb -s PHONE_SERIAL install -r --no-incremental android/build/meet-iq-debug.apk
adb -s PHONE_SERIAL push models/ggml-base.bin /sdcard/Download/ggml-base.bin
adb -s PHONE_SERIAL shell am start -n org.meetiq.offline/.MainActivity
```

On a fresh installation, use **Settings → Set up analysis** to import `Downloads/ggml-base.bin` once. Keep the multilingual base model for the initial 6 GB phone test. Choose automatic Hindi/English, or an explicit language, and add names/acronyms as vocabulary hints. Record/upload audio, optionally attach PPTX, then analyse. Speaker models are packaged in the APK. The app does not need the web servers or a cloud service.

This is **0.7.1-prototype**, retaining greedy speech decoding and compatible v4 ASR checkpoints, signed with the existing development key. `install -r` preserves existing compatible app data. Do not uninstall or clear app storage to update. Beam search was evaluated but not adopted because the longer English pilot regressed; see the readiness report.

For an emulator instead, start it in another terminal if it is closed:

```sh
/home/amitkumar/Android/Sdk/emulator/emulator -avd Pixel_6
```

Use `emulator-5554` in place of `PHONE_SERIAL` in the install/launch commands.

## Optional shared account and meeting sync

The website and Android now use the same account database when connected to the same server. Follow [Account & sync](ACCOUNT_SYNC.md) for sign-in, USB forwarding and explicit publish/download. Local recording/analysis needs neither an account nor a server connection. The 0.7 APK includes Internet permission for these optional account operations.

## Review actions and export deadlines

Open a completed meeting's **Action items** tab to confirm an owner, due date and open/done/dismissed status. Export a reviewed task calendar from Meeting options on the website or Export on Android. See [the follow-up guide](FOLLOW_UPS.md). Reviews transfer through explicit account publish/download; local use needs no connection.

## Optional laptop OCR for slide images

English/Hindi OCR files were downloaded and verified on this laptop (about 5.0 MiB total). No OCR download happens while processing meetings. The existing optional setting remains disabled to avoid adding OCR work to every presentation.

To enable it, edit the existing `ppt` section in `config/config.yaml`:

```yaml
  ocr_enabled: true
  ocr_languages: eng+hin
  ocr_model_dir: models/tesseract
```

Restart the backend and analyse the presentation again. Recognized image text is tagged as OCR in slide metadata and included in matching/report text. The browser labels slides that include OCR. This reads printed text, not the meaning of charts or images. Android still uses native PPTX text, without this Tesseract engine.

Provisioning command for another prepared laptop, while online:

```sh
.venv/bin/python scripts/download_ocr_models.py
```

Tesseract must also be installed on that machine. On this laptop it was already installed; no system package installation was performed.

## Checks and diagnostics

```sh
cd "/home/amitkumar/Music/MAI Project"
.venv/bin/python scripts/validate_setup.py
OMP_NUM_THREADS=4 .venv/bin/python -m pytest --rootdir=. -c config/pytest.ini tests -q
npm --prefix frontend run lint
npm --prefix frontend run build
node scripts/test_browser_offline.cjs
curl http://127.0.0.1:8001/api/health
```

Optional isolated API check (creates its own validation account/database, not records in the user's database):

```sh
OMP_NUM_THREADS=4 .venv/bin/python scripts/smoke_local_api.py
```

For Android errors:

```sh
adb -s PHONE_SERIAL logcat -s AndroidRuntime:E
```

Current implementation, measurements and the outstanding physical-phone/Hinglish checks are in the [readiness report](../validation/23_READINESS_2026_10_18.md).

Current research results, measured Hindi/Hinglish errors and Word report files: [research package](../../professor_guidelines/README.md).

## Latest speech-model comparison

`large-v3-turbo` is now provisioned locally and appears in the website's **Speech model** selector. Select it before analysing to try its output; saved model preferences still apply. The shared default remains `small` because stronger recognition did not improve every evaluated cohort. Compare the fixed English, Hindi and Hinglish results in [the quality scorecard](../../professor_guidelines/QUALITY_IMPROVEMENTS.md). Existing meetings require reanalysis to obtain another model's transcript. This laptop model does not change Android's native speech model.

On the unchanged eight-sample Hindi pilot, Turbo reduced WER from 50.96% to 28.85% and character error from 20.09% to 9.41%. On the eight Hinglish samples, WER decreased from 66.13% to 57.26%. These small pilots support trying Turbo for those languages; they do not establish full-recording accuracy.
