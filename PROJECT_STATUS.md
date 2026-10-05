# Project audit and implementation status — 5 October 2026

## Assessment

There was already a substantial offline research backend, a React dashboard, processed AMI data, tests, and reports. The migration had not produced a runnable laptop installation: Python dependencies and model weights were missing, API dependencies were absent from `requirements.txt`, and launcher scripts assumed the workstation's CUDA paths. The pipeline orchestrator was empty. The Flutter files were already deleted in the working tree when this work began; those deletions were preserved.

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

The final long-audio test made **zero socket connection attempts** and retained the correct first speech timestamp at **7,202.05 seconds**. Browser recording recovery retained two recorded chunks across reload. Native Android restart recovery retained all ten test segments. Metrics without meeting transcript text are saved in [validation-results.json](validation-results.json).

Detailed local evidence:

- `logs/tests_release_candidate.log`, `logs/browser_final.log`, `logs/browser_recording.log`
- `logs/ppt_offline_test.log`, `logs/long_offline_final.log`
- `logs/android_final_inference.log`, `logs/android_resume_test.log`
- `outputs/evaluation/benchmark_ES2002a_30_600_benchmark.json`
- `outputs/evaluation/benchmark_ES2002a_30_600_medium_language_scope_benchmark.json`

These generated logs and artifacts are local and ignored by Git; benchmark scripts and regression tests are included in the source.

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
- Native Android analysis uses non-overlapping chunks, so boundary quality needs further work. Both native and browser recordings can be interrupted by their operating systems.
- Browser recordings remain local until upload; laptop processing then requires that laptop. The native Android path requires no laptop after model import.
- The laptop API is a single-process local service, not a hardened internet-facing multi-tenant deployment. Files are private local artifacts, not an encrypted application vault.
- Existing transferred databases/data were retained. User-preexisting `.gitignore` changes and Flutter deletions were preserved. No commit, push or publication was performed.
