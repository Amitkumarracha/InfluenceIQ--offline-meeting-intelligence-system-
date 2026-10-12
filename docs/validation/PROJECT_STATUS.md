# Project audit and implementation status — 5 October 2026

Latest update: Android **0.6** now includes local speakers, editable names/roles, candidate influence and native-slide-text fusion. Read [chapter 19](19_ANDROID_SPEAKERS_FUSION_AND_VALIDATION.md) for the current measurements and limits, [20](../research/20_TRAINING_DATA_AND_MULTIMODAL_RESEARCH.md) for supervised training, and [21](../operations/21_OFFLINE_AND_WORKSTATION_DEPLOYMENT.md) for optional workstation hosting. Earlier sections below are historical migration records.

## Assessment

There was already a substantial offline research backend, a React dashboard, processed AMI data, tests, and reports. The migration had not produced a runnable laptop installation: Python dependencies and model weights were missing, API dependencies were absent from `environment/requirements.txt`, and launcher scripts assumed the workstation's CUDA paths. The pipeline orchestrator was empty. The Flutter files were already deleted in the working tree when this work began; those deletions were preserved.

The project now has a working local laptop pipeline and a separately compiled Android on-device prototype. It is **not yet a validated high-accuracy meeting product**, and this work does not establish patent novelty or patentability.

## Existing implementation reviewed

| Area | Existing implementation | Important limitation |
|---|---|---|
| Audio | Soundfile/resampling, Silero VAD, pyannote 3.1, faster-whisper | Entire audio loaded in several paths; ASR depended on successful diarization |
| Slides | PPTX text, tables, notes, optional OCR, embeddings | Alignment scores are heuristic; slide relevance is not proof that a statement is true |
| Analysis | English keyword events, temporal evidence links, reconstructed decisions, graphs, weighted influence | Rules do not reliably understand negation, topic changes, coreference, or multilingual semantics |
| Reports | JSON/Markdown/HTML/CSV and source traceability | Speaking statistics counted only extracted events; ordinary conversation was omitted |
| Evaluation | WER, approximate DER, event/decision/alignment metrics, ablations | DER treated arbitrary speaker labels as identities and ignored its configured collar |
| App | React recording/upload UI, FastAPI accounts, SQLite meetings | Public audio paths, hardcoded JWT key, account-reset token disclosure, unrestricted whole-file uploads |
| Mobile | Historical Flutter scaffold, already deleted | No on-device inference implementation existed in the current working tree |

## Implemented during laptop migration

### Environment and reproducibility

- Isolated Python 3.11 `.venv`, CPU PyTorch/torchaudio, compatible dependency pins and installed-version snapshot.
- Downloaded local multilingual Whisper small and medium, the existing slide embedding model, and the Android multilingual base model.
- Explicit model-provisioning script; normal inference defaults to offline mode and disables model telemetry.
- Portable project-relative startup/setup scripts, one origin for the built UI and API, and a complete CLI orchestrator.
- Ignored transferred workstation home folders and credentials. Sanitized `.env.example`; the old credential found there should be rotated.

### Audio and long meetings

- FFmpeg streaming conversion with checked errors and protocol restrictions; no forced loudness/noise filters that could distort speech.
- Bounded VAD blocks using packaged Silero weights rather than a GitHub torch.hub fetch.
- CPU int8 transcription with five-minute chunks, overlap, word timestamps, word-level speaker changes, and silence filtering.
- Content-addressed ASR checkpoints and atomic writes. Interrupted jobs reuse completed chunks; changed audio/settings/diarization invalidate caches.
- Speaker overlap union and abstention for exact ties; indexed lookup avoids scanning every diarization turn for every word.
- ASR continues with explicit UNKNOWN speakers when gated diarization is unavailable. Missing speaker identity is not presented as a real participant.
- Removed global PyTorch/hub monkey patches.

### Analysis, reporting and evaluation

- Added Hindi and common romanized Hinglish event phrases without diluting the English rule scores.
- Preserved source text and timestamps; added limited negative-decision guards.
- Corrected report duration/participants/speaking time and speaking-time baselines to use the complete transcript.
- Suppressed UNKNOWN participant influence entries.
- Replaced frame-label comparison with pyannote.metrics DER, using optimal label permutation, overlap and the actual collar.
- Reduced WER edit-distance memory from a full matrix to two rows.
- Added reproducible AMI benchmarking against human annotations and explicit normalization/limitations.
- Reports/UI distinguish event and decision candidates from validated conclusions.

### Laptop app

- Random persistent local JWT secret, bcrypt input validation and meeting ownership checks.
- Protected audio URLs restricted to one meeting and expiring after eight hours; media tokens cannot authenticate API requests.
- Removed publicly returned password-reset tokens; recovery is terminal-only.
- Incremental bounded uploads, decoded-file validation, checked format conversion and sequential-part normalization.
- Serialized CPU job execution, durable job manifests, restart recovery, processing stages and retry endpoint.
- IndexedDB recording recovery, media-type negotiation, microphone cleanup and responsive phone-width layout.
- Complete report JSON export rather than an abbreviated highlights-only file.

### Android

- Created `android/` with a native Java foreground recorder and whisper.cpp JNI inference.
- Built a signed debug APK for ARM64 phones and x86_64 emulators.
- No INTERNET permission; model import, local history, WAV recording, chunk checkpoints, timestamped transcript, heuristic event candidates and JSON/WAV export.
- The APK is an **on-device prototype**, not a wrapper around the laptop API.

## Verification evidence

### Automated checks

The original 446-test suite passed after correcting a fixture that supplied nine seconds of mocked output for five seconds of audio. Additional tests cover cache invalidation, interrupted-chunk resumption, word-level speaker turns, Hindi/Hinglish rules, full-transcript statistics, correct DER mapping, ownership, upload bounds and reset-token disclosure. **Final suite: 461 passed, 7 dependency warnings in 29.65 seconds.** Frontend production build and ESLint passed. The installed Python dependency set passed `uv pip check`. The signed Android APK passed signature and 16 KB alignment verification; its manifest has no INTERNET permission.

### Real inference and integration

| Check | Result | What it does not prove |
|---|---|---|
| Real 90-second AMI recording | Full laptop audio-to-report pipeline passed | General or Hindi/English accuracy |
| Browser at 390 px width | Register, upload, queued processing, report and authenticated audio playback passed; no JS errors/overflow | Physical browser microphone quality |
| Audio + PPT with socket connections blocked | All stages and report exports passed; no network connection attempted | Semantic slide alignment accuracy |
| 7,290-second timeline stress test | Passed; speech begins after 7,200 s with correct offsets; zero network connections; 189.7 seconds runtime and 854.6 MB peak RSS | A two-hour real conversation: most input was synthetic silence |
| Android emulator | APK installation, foreground microphone recording, native 20-second transcription (111.7 seconds on the final two-core emulator) and report creation passed; forced app restart reused checkpoints in 2.1 seconds | Real phone speed, power, background survival or bilingual accuracy |

### Accuracy baseline

For **AMI ES2002a, Array1-01, seconds 30–630**, Whisper small/int8 on this laptop produced:

- **WER: 45.8364%** (150 substitutions, 447 deletions, 25 insertions; 1,357 reference words).
- End-to-end processing: about **175 seconds** for 600 seconds of audio; real-time factor **0.292**.
- Process peak RSS: about **890 MB**.

This is one English meeting through a distant array microphone, with overlapping speakers and disfluencies. Reference words from all manually annotated speakers were ordered by time; text was NFKC-normalized, lowercased, and punctuation was replaced with spaces. Competing emulator workloads affected speed. Do not present this result as a published AMI benchmark score, overall product accuracy, Hindi/English accuracy, or evidence of superiority to another device. The result is **not close to the requested accuracy goal**.

With the same recording and normalization, **medium/int8 with Hindi/English language scope produced WER 40.8254%** (132 substitutions, 391 deletions, 31 insertions), taking **357.776 seconds**, real-time factor **0.5963**, and **2,309.2 MB** process peak RSS. This is a 5.01 percentage-point reduction on this one sample, at greater runtime and memory cost. Small remains the default laptop profile; medium can be selected with `MAI_ASR_MODEL=medium`.

An initial unrestricted medium run incorrectly detected Welsh and produced WER 66.7649%. This exposed a real language-detection failure. Both laptop and native Android inference now constrain automatic selection to the requested Hindi/English scope. A regression test covers the out-of-scope detection case. This restriction is not evidence that mixed-language transcription is accurate.

The final long-audio test made **zero socket connection attempts** and retained the correct first speech timestamp at **7,202.05 seconds**. Browser recording recovery retained two recorded chunks across reload. Native Android restart recovery retained all ten test segments. Metrics without meeting transcript text are saved in [validation-results.json](../../outputs/evaluation/validation-results.json).

Detailed local evidence:

- `logs/tests_release_candidate.log`, `logs/browser_final.log`, `logs/browser_recording.log`
- `logs/ppt_offline_test.log`, `logs/long_offline_final.log`
- `logs/android_final_inference.log`, `logs/android_resume_test.log`
- `outputs/evaluation/benchmark_ES2002a_30_600_benchmark.json`
- `outputs/evaluation/benchmark_ES2002a_30_600_medium_language_scope_benchmark.json`

These generated logs and artifacts are local and ignored by Git; benchmark scripts and regression tests are included in the source.

## Repository-inspired app upgrade — 5 October 2026

Reviewed all four supplied repositories and the three product sites; selected source files were downloaded for inspection into ignored `.runtime/reference-review/`. No third-party application code was copied. Details and source links are in [REPOSITORY_REVIEW.md](../history/REPOSITORY_REVIEW.md); foreground-only launch and provisioning commands are in [RUN_MANUALLY.md](../guides/RUN_MANUALLY.md).

The laptop now saves per-meeting speech model/language/vocabulary/speaker-count settings, reports transcription progress, and includes local Ollama notes with checked quotations and source timestamps. Long notes jobs checkpoint each bounded transcript part and recover after restart. Unknown owners/deadlines are not filled in. The UI includes retrieved-passage meeting questions, cross-meeting transcript search, persisted speaker aliases/titles, microphone selection and levels, pause/resume, optional shared-tab audio, upload-part ordering, timestamp playback, 100-passage transcript pages, full printing, and JSON/Markdown/TXT/SRT/VTT/CSV exports. The launcher rebuilds the current frontend every time.

Android version 0.3.0 adds normalized PCM WAV import, playback, searchable transcript pages, meeting titles, Markdown export, language/vocabulary settings, context overlap, partial reports after each completed chunk, and recovery of already completed analyses without model loading. It retains no INTERNET permission and explicit UNKNOWN speaker labels.

Current verification:

| Check | Result | Boundary |
| --- | --- | --- |
| Python suite | **470 passed, 7 dependency warnings, 7.27 seconds** | Local notes model output is mocked; tests verify evidence, ownership, settings, export and resume logic. |
| Frontend | Vite production build and oxlint passed | No new dependencies added. |
| Foreground browser fixture check | Synthetic microphone record/pause/resume, IndexedDB reload recovery, settings submission, late transcript pages, complete print DOM, notes polling, questions and Markdown download passed; no JS errors or horizontal overflow at 390 px | API/AI responses are intercepted fixtures; no web/API server was started. |
| Real 30-second AMI pipeline | Small model + English/vocabulary job settings produced 10 transcript segments and reports in 4.89 seconds, with **zero network connection attempts** under a blocked socket connect | An integration check, not a new WER measurement. |
| Android | ARM64/x86_64 APK compiled and signed; PCM JVM checks passed | New native/UI flows have not been retested on a phone/emulator. |

Ollama was not installed or started during this work. Actual semantic notes require manual local model provisioning/startup and a model quality evaluation. Existing small/medium WER baselines below remain unchanged; no higher accuracy or competitor superiority is claimed. No background app server was launched, no model weights were downloaded in this upgrade, and no existing user meetings were removed.

## Focused efficiency and bilingual fixes — 6 October 2026

Resumed the interrupted work and fixed duplicate WAV conversion, Hindi token splitting, negation/question false confirmations, repeated Android rule compilation/scanning and graph relationship loss. Added owner-protected partial previews, exact-silence skipping, audio diagnostics, optional TF-IDF slide matching, an inactive optional ONNX diarization adapter, and manual phone-recording evaluation. **494 Python tests passed**; frontend build/lint and browser fixtures passed; Android 0.3.1 was compiled/signed and JVM audio/bilingual checks passed. Existing neural slide alignment and pyannote remain the defaults; no dependencies/models were installed and no app server was launched.

Fresh small-model tests on the same ten-minute English AMI sample gave **45.8364% WER / 82.254 seconds with 300-second chunks**, and **41.4886% WER / 115.043 seconds with 120-second chunks**. The shorter setting improved this sample but was slower overall. Hindi/Hinglish ground-truth accuracy remains unmeasured. The long synthetic timeline passed with zero network connections in 17.896 seconds; real speech + PPT also passed offline. Details, verification boundaries and manual commands are in [EFFICIENCY_IMPROVEMENTS.md](EFFICIENCY_IMPROVEMENTS.md) and [efficiency-results.json](../../outputs/evaluation/efficiency-results.json).

## Remaining work, in priority order

1. **Unblock real diarization.** Hugging Face rejected the transferred token/model access. Accept both pyannote model gates and update `.env` locally; then provision and evaluate with real speaker annotations. No physical identity recognition is implemented.
2. **Collect consented Hindi/English phone recordings and ground truth.** Include quiet/noisy rooms, distant speech, accents, code-switching, interruptions, overlapping speakers, and 30/60/120-minute meetings. Have humans independently annotate transcripts, speakers, decisions, owners, deadlines and evidence links.
3. **Improve measured ASR accuracy.** Compare model sizes/quantization, VAD thresholds and acoustic placement on held-out recordings. Track WER and character error rate with documented bilingual normalization. Do not report `1 - WER` as a universal accuracy percentage.
4. **Replace/validate heuristic understanding.** Current event, evidence and decision rules can miss or misclassify intent. Relevance, temporal proximity, agreement and actual decisions must be separately evaluated. A slide association currently creates a heuristic support relation; it is not semantic entailment.
5. **Validate speaker attribution and overlap.** Word timestamps improve alignment but do not separate two simultaneous voices. Full-recording pyannote memory/runtime on multi-hour meetings remains unmeasured here.
6. **Bring Android to feature parity.** On-device speaker embeddings/clustering with cross-chunk identity consistency, noise/overlap handling, richer bilingual analysis, correction workflows, and any desired graph/slide features are still absent.
7. **Physical Android validation.** Need the actual phone model/RAM and device tests for battery, thermal throttling, OS/background interruption, interrupted imports, storage exhaustion, long capture, release signing and lifecycle/accessibility behavior. The build is a debug APK, not a store-ready release.
8. **Research/patent preparation.** Define the specific proposed invention, review prior art, document what differs from existing recording/transcription/diarization systems, compare against baselines on the same held-out data, and retain reproducible experiments. No novelty search, patent claim drafting or legal assessment was performed.

## Known operating limits

- Speaker labels are clusters, not real names. Inference confidences and influence scores are uncalibrated analytical estimates.
- Small/base models are practical CPU baselines; neither guarantees good far-field or mixed-language accuracy.
- The legacy English MiniLM slide model has not been validated for Hindi/English cross-language alignment.
- Native Android analysis now uses context overlap; boundary quality still needs validation. Both native and browser recordings can be interrupted by their operating systems.
- Browser recordings remain local until upload; laptop processing then requires that laptop. The native Android path requires no laptop after model import.
- The laptop API is a single-process local service, not a hardened internet-facing multi-tenant deployment. Files are private local artifacts, not an encrypted application vault.
- Existing transferred databases/data were retained. User-preexisting `.gitignore` changes and Flutter deletions were preserved. No commit, push or publication was performed.


## Android UI delivery — October 6, 2026

InfluenceIQ **0.4.0-prototype** replaces the Android control panel with native Home, Recording, Meeting Detail (five tabs), analysis progress and Settings screens. It supports system light/dark themes, local vector icons, accessible touch targets, transcript highlighting/pagination, candidate filters and local audio seeking. Existing meeting folders, report/checkpoint schemas, JNI inference and offline restrictions are retained. No packages or models were downloaded for this redesign.

JVM audio/progress/bilingual checks and the direct ARM64/x86_64 build passed. Emulator checks covered real microphone capture, local model/WAV import, English native inference with hints, chunk pause/restart/resume, partial reports, 225-passage search/pagination, filtering, metadata-preserving rename, playback and Markdown/JSON/WAV exports. Layout checks covered 360dp and 432dp with 1.3× fonts. This does not establish physical-phone performance, Hindi/Hinglish accuracy or speaker separation. See [Android design report](../android/DESIGN.md) for files, commands, screenshots and test boundaries.


## Minimal interface and common recording upload — October 7, 2026

The browser and native Android app now start with recording/audio upload and optional PPTX/vocabulary, with History and Settings kept separate. Technical controls have moved into Settings; results separate Transcript, Action items, Decisions and Analysis. The laptop saves editable identified speaker names/roles and vocabulary in owned reports, and optional local profiles. Android **0.5.0-prototype** saves per-meeting hints/default language, attaches PPTX with a native text viewer for reference, and imports common phone recordings through local system codecs. Compatible PCM bytes are preserved; other imports normalize to the recognizer's 16 kHz mono PCM16. Native names/roles/influence remain unavailable without diarization; accuracy is explicitly unmeasured on both interfaces.

Verification: **496 Python tests passed (7 dependency warnings)**; frontend build/lint and browser fixtures passed at 360/390/960 px without overflow/JS errors. Recording pause/resume/reload recovery, saved profile/language, PPT/hints submission, partial preview, speaker edits/history, vocabulary, Home navigation, full printing and export were exercised. Android JVM checks and the ARM64/x86_64 signed build/install passed. Real emulator codecs preserve signal/duration for stereo 44.1 kHz WAV, MP3, AAC M4A, extensible PCM24 and float32 WAV. Home, Settings and all five review tabs passed; real Android document-picker MP3/PPTX imports and saved-vocabulary reopening passed. The same screen check also passed at 360dp/1.3× text, with emulator settings restored. APK 16 KB alignment and absence of INTERNET permission were checked.

No ASR model, fusion method or event-rule algorithm was replaced; these checks establish integration and UI behavior, not higher recognition accuracy. The earlier documentation audit and its file hashes remain a historical snapshot. Current changes and research boundaries are documented in [chapter 17](17_MINIMAL_UI_IMPLEMENTATION_AND_VALIDATION.md). APK: [android/build/meet-iq-debug.apk](../../android/build/meet-iq-debug.apk). No physical phone was connected, no model download was performed, and no existing user meeting was deleted.


## Submitted-report scope and website NLP delivery — October 7, 2026

Read the submitted Group 12 report and both pasted discussions. The active website now exposes Participants, Influence, Events and Presentation alongside transcript/actions/decisions; role/name edits propagate through transcript and evidence. Missing gated pyannote models were the main cause of UNKNOWN-only output. The existing ONNX adapter is now the laptop default, using pinned sherpa-onnx 1.13.8 and checksum-verified public local weights. Health/Settings show speaker readiness and UNKNOWN-only saved meetings can explicitly queue speaker analysis from retained audio. Generative notes/chat modules, workers/routes and library transcript search have been removed; historical stored output is retained but not published/exported.

Added observed chunk-language metadata/script cues, bounded Hinglish task/negation handling, narrow review-required slide quantity checks, full participant scoring coverage, numeric action timestamps and serialized analytical fields. Corrected UI/schema mismatches for actual influence JSON. Existing influence weights and fusion algorithms remain. **494 Python tests passed (7 warnings)**; frontend lint/build, browser checks at 360/390/960 px and shared Android JVM rules passed; package/setup checks pass. Real 90-second English audio with a four-speaker constraint yielded four participants, 23 passages, three events, four influence records and three links to two validation slides, with zero socket connections. Unconstrained diarization produced eight clusters, showing the default threshold still needs evaluation. The cached full-pipeline rerun took 2.873 seconds and is not a cold speed benchmark.

Mixed-text downstream NLP produced source-preserving events, a reconstructed decision and explained scores, but its speech/speaker boundaries were mocked. Public Hindi/English speech samples detected `hi`/`en`; their constructed 7.213-second concatenation retained both scripts with zero socket connections. This is a smoke test, not a natural meeting or WER benchmark. Real Hinglish WER, DER, cross-language slide quality and human influence rankings remain unevaluated. General semantic/visual inconsistency detection is still incomplete. The submitted report was not changed. Detailed objective mapping, changes and test boundaries: [chapter 18](18_SUBMITTED_REPORT_FEEDBACK_AND_NLP_DELIVERY.md).
