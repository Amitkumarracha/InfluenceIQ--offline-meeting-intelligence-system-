# Minimal interface update — 7 October 2026

The later [NLP delivery in chapter 18](18_SUBMITTED_REPORT_FEEDBACK_AND_NLP_DELIVERY.md) supersedes this interface scope and removes the optional generative features described below.

This chapter records changes made **after** the comparison audit in chapters 01–16. Their scoped counts, source hashes and older/current comparisons remain an earlier snapshot. The supplied older folder has not been edited.

## Product goal and delivered workflow

The developer feedback was that the app exposed too many technical controls before a user could start. The implementation keeps recording/upload prominent and moves technical choices into Settings or secondary meeting options. It introduces no new model or user-facing accuracy claim.

| Area | Laptop/browser | Native Android 0.5.0-prototype |
| --- | --- | --- |
| Home | Record meeting, audio upload, optional title, PPTX and vocabulary hints | Record meeting, audio upload, optional PPTX and vocabulary hints, three recent meetings |
| Navigation | Home, History, Settings | Home, History button and Settings icon |
| Results | Overview, Transcript, Action items, Decisions, Speakers & analysis | Overview, Transcript, Action items, Decisions, Analysis |
| Technical choices | Collapsed advanced Settings: model, speaker separation, expected count, microphone/capture source | Local model setup and default language in Settings |
| Language | Automatic Hindi/English by default; explicit overrides in Settings | Automatic Hindi/English by default; preferences saved with new recordings/imports |
| Profile | Account-owned local name, role and organisation | Device-local profile, saved as fields are edited |
| Vocabulary | Optional hints; observed transcript-word suggestions; editable and saved per meeting; reusable for the next meeting | Optional hints; observed suggestions on new analysis; editable per-meeting hints saved in metadata |
| Speakers | Identified cluster names and contribution labels editable when separation succeeds | No diarization: names, roles and influence remain unavailable |
| Influence | Actual pipeline estimate when present, explicitly described as heuristic | Unavailable; no fabricated score |
| Accuracy | Explicitly unmeasured without a reference transcript | Explicitly unmeasured without a reference transcript |
| Presentations | Existing audio-to-slide pipeline retained | Saved PPTX and bounded native slide-text viewer for reference; no audio-slide fusion |
| Secondary features | Notes/questions under a disclosure; rename/export/print under Meeting options | Playback, export, rename and PPT replacement under Meeting options |
| History | Existing SQLite meetings plus saved name/role/vocabulary edits | Existing private meeting folders plus preserved metadata and presentation attachments |

Action-item speakers indicate who spoke the commitment; they are not automatically task owners. Decision statuses are pipeline interpretations and require checking the source. Editing vocabulary after analysis saves reusable hints; it does not silently rewrite a transcript or re-run recognition. Automatic word suggestions are frequency-ranked observed terms, not entity recognition, spelling corrections or novel semantic understanding.

The browser retains recording pause/resume, saved-draft recovery, upload-part ordering, timestamp playback, complete printing, library search and local notes with source quotations. The native foreground service, chunk checkpoints, manual resume and existing report formats remain in use.

## Removing the restrictive upload experience

The laptop already decodes multiple audio formats through FFmpeg. Android previously required pre-converted 16 kHz mono PCM16 WAV, which made ordinary recordings inconvenient to upload.

Android now reads common PCM and float WAV variants locally. Platform `MediaExtractor` / `MediaCodec` decodes other supported recordings, including the tested MP3 and AAC M4A. A streaming converter mixes channels and resamples to the existing recognizer's 16 kHz mono PCM16 format. Already compatible WAV sample bytes are preserved. Other imports produce a normalized saved WAV; the external selected file is not deleted. Codec availability depends on the device. Six-hour/storage/import-size limits remain.

The WAV reader supports 8–192 kHz, 1–8 channels, PCM 8/16/24/32-bit and 32-bit float, including supported extensible WAV subformats. WAV ADPCM and unsupported encodings are rejected rather than guessed. No decoder package or network service was added. Conversion makes files usable; its recognition effect has not been evaluated.

PPTX parsing reads native DrawingML text only, without OCR, image descriptions, animation timing or audio-to-slide alignment. Slides, decoded XML and extracted text are bounded, and external entities/DOCTYPE are rejected. Large image-only presentations may have no readable native text.

## Files a new developer should inspect

| File | Change and purpose |
| --- | --- |
| [frontend/src/App.jsx](../../frontend/src/App.jsx) | Simplified navigation/capture/review, profile, saved preferences, separate action/decision views, editable vocabulary and speaker labels; existing recording and request handlers retained |
| [frontend/src/index.css](../../frontend/src/index.css) | Neutral/teal responsive layout, compact panels, native form controls and full-report print rules |
| frontend/src/MeetingNotes.jsx (historical; removed in chapter 18) | Optional model controls under Notes options; concise setup state |
| [api.py](../../backend/api.py) | Authenticated profile GET/POST; owned meeting edit validates speaker roles and vocabulary; suggestions supplied for older reports |
| [src/meeting/vocabulary.py](../../src/meeting/vocabulary.py) | Unicode observed-term counting using existing text normalization/stop words |
| [src/pipeline/orchestrator.py](../../src/pipeline/orchestrator.py) | New reports include submitted vocabulary and observed suggestions |
| [src/report/transcript_export.py](../../src/report/transcript_export.py) | Text/Markdown exports include saved speaker labels/roles and vocabulary |
| [android MainActivity.java](../../android/app/src/main/java/org/meetiq/offline/MainActivity.java) | Minimal Home/review/Settings, metadata loading, vocabulary editing and presentation viewer; blocks analysis until selected metadata has loaded |
| [Ui.java](../../android/app/src/main/java/org/meetiq/offline/Ui.java) | Neutral/teal native palette, existing system widgets/icons |
| [AudioImport.java](../../android/app/src/main/java/org/meetiq/offline/AudioImport.java) | Local platform decoder and bounded/error-checked import |
| [PcmAudio.java](../../android/app/src/main/java/org/meetiq/offline/PcmAudio.java) | Streaming channel averaging/resampling; handles arbitrary decoder frame boundaries |
| [WavAudio.java](../../android/app/src/main/java/org/meetiq/offline/WavAudio.java) | Wider validated WAV parsing and exact compatible-PCM copy |
| [PresentationText.java](../../android/app/src/main/java/org/meetiq/offline/PresentationText.java) | Bounded PPTX slide-text extraction with local ZIP/SAX APIs |
| [Vocabulary.java](../../android/app/src/main/java/org/meetiq/offline/Vocabulary.java) | Native observed-word suggestions |
| [LocalTransfers.java](../../android/app/src/main/java/org/meetiq/offline/LocalTransfers.java) | Background audio/PPT imports, next-meeting draft attachment and explicit exports |
| [MeetingRepository.java](../../android/app/src/main/java/org/meetiq/offline/MeetingRepository.java) | Metadata-preserving vocabulary edits; structured export includes metadata/presentation |
| [MeetingService.java](../../android/app/src/main/java/org/meetiq/offline/MeetingService.java) | Captures default language/hints and pending PPT at recording start; adds observed suggestions to reports |
| [AndroidManifest.xml](../../android/app/src/main/AndroidManifest.xml), [build.gradle.kts](../../android/app/build.gradle.kts) | Synchronised version 5 / 0.5.0-prototype; existing offline permissions retained |
| [pytest.ini](../../config/pytest.ini) | Collects current `tests/`, preventing the supplied older snapshot's duplicate test package from shadowing current imports |

No first-party dependencies were added for these changes. No trained model, fusion equation, speaker algorithm, event-rule bank or native JNI inference implementation was replaced.

## Persistence and compatibility

The laptop profile is an atomic `.runtime/profiles/<user-id>.json` file protected by the existing authentication dependency. Name/role/vocabulary meeting edits update owned SQLite report data, preserving other keys; later local-notes updates retain them. Model/language/separation defaults are stored in browser preferences per account; submitted job settings remain durable in the existing job state. Profiles are optional and do not identify recorded speakers.

Android profile/defaults use existing private SharedPreferences. Per-meeting hints and language use `metadata.json`; title edits preserve these keys. PPT attachments are `presentation.pptx` and `presentation.json`. Next-meeting attachments are staged privately, then copied to the new meeting. `report.json`/`checkpoint.json` remain compatible; `report-export.json` adds metadata and presentation text to an exported copy. Existing meetings without new fields still open.

Historical Android reports lack the new suggestion field. Editing hints remains available, and future completed analyses add suggestions. Reusing or changing hints affects subsequent recognition/checkpoint identity; the UI does not claim retroactive correction.

## Checks and their boundaries

| Check | Result / boundary |
| --- | --- |
| Python suite | 496 passed, 7 dependency warnings; verifies profile privacy/ownership, persisted meeting edits, export and Unicode suggestions alongside existing tests; AI/model boundaries are mocked in applicable unit tests |
| Frontend build/lint | Vite production build and oxlint pass |
| Browser workflow | Intercepted fixture API and synthetic microphone: registration, record/pause/resume/reload recovery, profile and language persistence, model/PPT/hints submission, partial transcript, vocabulary, speaker edits/history, Home navigation, 215-passage pagination/full print, optional notes/Q&A and Markdown download pass |
| Browser layout | 360/390/960 px checks pass with no horizontal page overflow or JavaScript errors; screenshots inspected |
| Android JVM tests | WAV parsing/sample preservation, stereo rate conversion/channel mean, split PCM frames, Unicode vocabulary, PPTX parsing/unsafe XML rejection, PCM progress and bilingual event checks pass |
| Android build | Direct SDK/JDK/NDK ARM64/x86_64 APK compilation/signing pass; 16 KB zip alignment and absence of INTERNET permission checked; emulator update preserves application data |
| Actual Android codecs | Generated 2-second tones: stereo 44.1 kHz WAV, MP3, AAC M4A, extensible 24-bit PCM WAV and float WAV all decode to valid 16 kHz mono PCM16; duration and nonzero signal verified |
| Native screen smoke | Home, profile/language Settings and all five review tabs pass on Pixel_6 x86_64 emulator; review screenshots use a clearly labelled generated report |
| Native larger-text layout | The same navigation/screen check passes at 360dp with 1.3× font scale; screenshots inspected; emulator density/font restored afterward |
| Native persistence/import UI | Saved vocabulary survives force-stop/reopen; unrelated metadata retained; real system picker imports/replaces PPTX, opens extracted English/Hindi text and imports MP3 into an analysable meeting |

Local evidence: `logs/minimal_python_tests.log`, `logs/minimal_browser.log`, `logs/minimal_android_tests.log`, `logs/minimal_android_build.log`, `logs/minimal_android_install.log`, `logs/minimal_android_codec_probe.log`, `logs/minimal_android_ui.log`, `logs/minimal_android_edits.log`, `logs/minimal_android_narrow.log`. Generated fixtures and screenshots are under `.runtime/validation/`. These are validation artifacts, not research ground truth.

Repeat the source/build checks:

```bash
OMP_NUM_THREADS=4 bash scripts/check.sh -q
npm --prefix frontend run lint
npm --prefix frontend run build
node scripts/test_browser_offline.cjs
bash android/test.sh
bash android/build.sh
# Optional: an explicitly selected emulator with the APK installed and Home open.
python3 scripts/check_android_design.py --serial emulator-5554 \
  --meeting-title 'Minimal UI validation' --output outputs/android-minimal
```

The browser fixture check uses an already available Playwright installation in `.runtime/browser/node_modules/playwright`, or `MAI_PLAYWRIGHT` pointing to one. The screen script does not create a meeting; omit `--meeting-title` or supply an existing title. The codec probe [AudioImportProbe.java](../../android/test/AudioImportProbe.java) is compiled with the existing Android SDK and run through emulator `app_process` on generated tone files; it does not invoke Whisper.

## Research and journal interpretation

This is an interface/usability and integration contribution. It does **not** establish improved WER, correct decision interpretation, calibrated influence, validated speaker roles, new multimodal fusion, or faster measured meeting understanding. Existing English WER measurements in chapter 09 still apply to their stated experiments. Hindi/Hinglish recognition and physical-phone performance remain unmeasured here.

A paper can accurately say the prototype presents recorded evidence through a simpler capture/review workflow, preserves user metadata/history, and accepts common phone recordings. Comparative usability claims need a user study: task-completion rate/time, misclicks, errors, discoverability, satisfaction and accessibility, comparing the older interface against this one on identical tasks. Actual recognition and fusion claims require the separate experiments in chapter 11.

The laptop's inherited semantic/temporal fusion and optional TF-IDF matcher are unchanged. Android stores PPT text for reference only, and still lacks diarization, identified speaker editing, influence analysis, interaction graphs and semantic notes. This difference must remain explicit in product descriptions and journal comparisons.
