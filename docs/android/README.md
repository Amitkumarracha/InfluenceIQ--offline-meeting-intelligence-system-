# InfluenceIQ Android prototype

Version **0.6.0-prototype** records and processes meetings locally, including pretrained speaker separation, editable participant names/roles, candidate decision-linked influence and native PPT text fusion. The speech model is imported once; speaker weights are packaged in the APK. There is no INTERNET permission or automatic upload. An optional Settings link opens your configured HTTPS website in an external browser. App data stays private, backup is disabled, and export is explicit. See [the implementation/evaluation report](../validation/19_ANDROID_SPEAKERS_FUSION_AND_VALIDATION.md).

## Build

On the prepared laptop:

```bash
bash android/build.sh
```

On a fresh Linux development machine, first run the project's `scripts/setup.sh`, install an Android SDK platform/build-tools and a JDK, then:

```bash
bash android/setup.sh
bash android/build.sh
```

The build uses the native SDK tools directly. It does not require Gradle or AndroidX. SDK paths can be overridden using `ANDROID_SDK_ROOT`, `ANDROID_BUILD_TOOLS`, `ANDROID_JAR`, and `ANDROID_NDK_HOME`. The supplied defaults match this laptop: build-tools 36.0.0 and platform android-37.0; the APK targets API 35 and supports API 26+.

`setup.sh` provisions NDK r26d and whisper.cpp **v1.7.6**, pinned to commit `a8d002cfd879315632a579e73f0148d06959de36`. The source checkout is an ignored build dependency. Setup also verifies and provisions Sherpa ONNX **1.13.8** native libraries and the shared segmentation/ERes2Net speaker weights through `scripts/setup_android_speakers.py`. On a previously provisioned 0.5 workspace, run `.venv/bin/python scripts/setup_android_speakers.py` before building 0.6. `build.sh` compiles ARM64 and x86_64 native libraries, compiles Java, creates DEX, aligns the APK for 16 KB pages, and signs it with a local development key in `.runtime/`. Output: `android/build/meet-iq-debug.apk`.

Before release: use a production signing key, remove debug mode, complete device/permission/accessibility tests, and review dependency licenses. The debug APK is for local validation.

## Installation

```bash
adb install -r android/build/meet-iq-debug.apk
adb push models/ggml-base.bin /sdcard/Download/ggml-base.bin
```

Open **Settings → Set up analysis** to import the model. Use a multilingual GGML model (`tiny`, `base`, or `small`), not a faster-whisper model directory or an English-only `.en` model. `base` is provisioned here. Model loading can fail if phone memory is insufficient; the original recording remains available.

## What is implemented

- System microphone permission and 16 kHz mono PCM WAV recording.
- Foreground service, visible notification, stop control and wake lock.
- Streaming writes with a recoverable WAV header; six-hour recording ceiling.
- Offline native Whisper inference in 120-second chunks, with original timestamps and language selection restricted to Hindi/English.
- Two seconds of context around chunk boundaries; midpoint ownership avoids deliberately emitting each boundary segment twice.
- Optional English/Hindi language selection and vocabulary prompts, included in checkpoint identity.
- Atomic completed-chunk checkpoints tied to audio/model content hashes.
- Retained audio on process interruption; manual analyse/resume after reopening.
- Extracted event candidates using shared English/Hindi/Hinglish phrase banks, with question/negation guards. Compiled once and applied only to new passages.
- Home/recent-meeting library, editable titles, transcript search with highlighted matches and 20-passage pages, clickable timestamps and recording playback.
- Local MP3/M4A and other platform-supported audio import. WAV PCM8/16/24/32 and float32 with 1–8 channels and 8–192 kHz rates are mixed/resampled to 16 kHz mono PCM16. Already compatible PCM samples are preserved. No manual file conversion is required.
- Partial reports written after each completed transcription chunk; completed ASR chunks recover without reloading the speech model; content-addressed speaker turns are reused when their audio/model/count identity matches.
- Markdown/JSON/WAV export via the document picker, including every transcript passage.
- Dedicated recording screen with a real PCM amplitude history and timer; Stop & save opens the new meeting.
- Minimal Home with recording, audio upload, optional PPTX and vocabulary hints. Overview, Transcript, Participants, Action items, Decisions, Analysis and Presentation tabs; playback, rename and exports are under Meeting options.
- Optional PPTX attachment, native slide text extraction, sparse TF-IDF passage matching, similarity/margin abstention, playable source matches and presentation export.
- Pretrained ONNX speaker segmentation/embeddings with meeting-global clustering and an optional known participant count. Overlap/low coverage remains unassigned. Native Whisper BPE pieces are joined into words before timestamp attribution; attributed passages preserve the raw ASR checkpoint.
- Editable participant names/roles saved in metadata/history and applied to transcript, event, influence, presentation and export labels.
- Candidate decision lineage, source-event links, contribution roles, seven max-normalized weighted influence features and separate attributed speaking time. Multiple rule labels on one passage do not duplicate a contribution.
- Update analysis on Overview reuses unchanged ASR/speaker caches and refreshes presentation matches.
- Editable per-meeting vocabulary and suggestions from observed transcript words, saved in metadata/history and included in exports.
- Visible completed-chunk progress, pause status and resume controls.
- Local audio play/pause/stop and seek bar.
- System light/dark themes, native vector icons, 48dp icon targets and larger-font layouts.
- Settings with a saved local profile, automatic Hindi/English language default and model management; visible transfer errors and unavailable-action states.
- Cached meeting summaries and background file transfers; idle screens do not repeatedly parse full reports.
- No internet permission; speech-model transfer occurs before offline operation. The optional HTTPS browser shortcut performs no upload itself.

## Current limits

The native analysis is a lightweight baseline. It shares event rules and weight categories with the website, but its lexical candidate lineage is not the full Python evidence/decision graph. Scores are not validated causal influence, and roles describe contributions rather than job titles. PPT fusion uses native text, with no OCR, visual encoder or temporal slide windows.

Speaker processing reads the recording into a native float buffer, with a one-hour limit (up to about 230 MB of PCM floats, plus models/intermediates). Longer recordings retain full chunked transcription but speaker analysis is marked unavailable. Low-memory phones and long/background runs still need physical-device tests. Pause waits for the current native stage to finish; upstream speaker inference cannot cancel mid-stage.

The emulator has verified installation, microphone foreground recording, native model loading/transcription and report creation. This does not establish physical-phone speed, battery/thermal behavior, background survival, or Hindi/English accuracy. No physical phone was connected during implementation.

The earlier version **0.4.0-prototype** was built and installed on the existing Pixel_6 x86_64 emulator (API 37, 16 KB pages). The redesigned recording, model/WAV import, native English transcription with vocabulary hints, checkpoint pause/restart/resume, partial-report review, search/pagination, candidate filters, timestamp playback, rename and all three document-picker exports were exercised. Hindi/auto settings reached the service and checkpoint on a digital-silence fixture; that is a wiring check, not a language-accuracy benchmark. Layouts were checked at 360dp/432dp and 1.3× font scale, including theme recreation.

Version **0.5.0-prototype** implements the simpler interface and wider audio import. Its ARM64/x86_64 debug APK builds and installs; real emulator codec checks cover stereo 44.1 kHz WAV, MP3, AAC M4A, extensible 24-bit PCM and float WAV. All five review screens and Settings pass the emulator smoke check, including 360dp/1.3× text. Real document-picker MP3/PPTX import and saved-vocabulary reopening also pass. These checks do not measure recognition accuracy. See [the October 7 implementation report](../validation/17_MINIMAL_UI_IMPLEMENTATION_AND_VALIDATION.md).

`bash android/test.sh` checks WAV parsing/recovery/sample preservation, streaming stereo resampling, arbitrary frame splits, observed Unicode vocabulary, PPTX parsing/XML rejection, real PCM amplitude/progress, and the exported English/Hindi/Hinglish rule banks on the JVM. ARM64 is compiled and signed but has not been exercised on a physical phone. See [design and validation details](DESIGN.md) and [manual instructions](../guides/RUN_MANUALLY.md).

Version **0.6** validation, current accuracy measurements, training guidance and cloud boundaries are in chapters [19](../validation/19_ANDROID_SPEAKERS_FUSION_AND_VALIDATION.md), [20](../research/20_TRAINING_DATA_AND_MULTIMODAL_RESEARCH.md) and [21](../operations/21_OFFLINE_AND_WORKSTATION_DEPLOYMENT.md). `bash android/test-device-analysis.sh` exercises Android’s real JSON/regex runtime and candidate fusion/scoring contracts on a connected emulator/device after a build.
