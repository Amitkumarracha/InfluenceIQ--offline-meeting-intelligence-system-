# Meet IQ Android prototype

This Java/NDK app records and processes meetings locally. No cloud endpoint, Python server, account, WebView, or INTERNET permission is used. Models are imported with Android's system document picker. App data stays private and Android backup is disabled; export is an explicit user action.

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

`setup.sh` provisions NDK r26d and whisper.cpp **v1.7.6**, pinned to commit `a8d002cfd879315632a579e73f0148d06959de36`. The source checkout is an ignored build dependency. `build.sh` compiles ARM64 and x86_64 native libraries, compiles Java, creates DEX, aligns the APK for 16 KB pages, and signs it with a local development key in `.runtime/`. Output: `android/build/meet-iq-debug.apk`.

Before release: use a production signing key, remove debug mode, complete device/permission/accessibility tests, and review dependency licenses. The debug APK is for local validation.

## Installation

```bash
adb install -r android/build/meet-iq-debug.apk
adb push models/ggml-base.bin /sdcard/Download/ggml-base.bin
```

Open the app and use its model-import button. Use a multilingual GGML model (`tiny`, `base`, or `small`), not a faster-whisper model directory or an English-only `.en` model. `base` is provisioned here. Model loading can fail if phone memory is insufficient; the original recording remains available.

## What is implemented

- System microphone permission and 16 kHz mono PCM WAV recording.
- Foreground service, visible notification, stop control and wake lock.
- Streaming writes with a recoverable WAV header; six-hour recording ceiling.
- Offline native Whisper inference in 120-second chunks, with original timestamps and language selection restricted to Hindi/English.
- Atomic completed-chunk checkpoints tied to audio/model content hashes.
- Retained audio on process interruption; manual analyse/resume after reopening.
- Extracted event candidates using shared English/Hindi/Hinglish phrase banks.
- Local meeting selection, transcript viewing, JSON/WAV export via the document picker.
- No internet permission; model transfer occurs before offline operation.

## Current limits

This app is a prototype, not feature parity with the laptop. It does not yet implement speaker separation, overlapping-speaker recovery, slide alignment, decision lineage/interaction graphs, influence scores, or local semantic summarization. Speaker labels are explicitly UNKNOWN. Native chunk boundaries are non-overlapping; boundary-word quality needs evaluation. Silence handling suppresses exact digital silence; real noise can still produce recognition errors. Mixed-language phrase rules are not a validated semantic model.

The emulator has verified installation, microphone foreground recording, native model loading/transcription and report creation. This does not establish physical-phone speed, battery/thermal behavior, background survival, or Hindi/English accuracy. No physical phone was connected during implementation.
