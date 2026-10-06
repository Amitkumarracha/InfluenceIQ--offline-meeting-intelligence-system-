# Efficiency and bilingual changes — 6 October 2026

The interrupted work resumed from its saved files. Changes address observed defects and measured tradeoffs. No package installation, model download, cloud deployment or background app server was performed during this upgrade. Existing research files and user meetings were retained.

## Decisions on the proposed architecture

| Proposal | Implemented decision | Reason and boundary |
| --- | --- | --- |
| Remove giant intermediate WAVs | Decode uploaded parts through bounded FFmpeg pipes into one atomic, recoverable PCM recording. Reuse normalized PCM in the pipeline. Verify content hashes before reusing a decoded recording. | Removes per-part WAVs and a second normalized copy. One durable recording remains for playback/restart; multi-hour audio is not held entirely in RAM. Original uploads remain available. |
| Replace pyannote with quantized ONNX | Added an optional `sherpa-onnx` adapter; pyannote remains the default. | Requires manual dependency/model provisioning and real speaker evaluation. No measured 70% RAM reduction is claimed. The upstream offline API accepts the full recording for global speaker clustering; it is not bounded-memory streaming diarization. |
| Use overlapping two-minute chunks | Laptop ASR defaults to 120-second central chunks with two seconds of context, bounded previews and automatic checkpoints. Android retains its existing overlapping 120-second chunks. | Improves time to the first preview and recognition on the measured sample, but increases total inference time. The 300-second setting remains available. This is incremental processing after ingestion, not live transcription while recording. Full decision/interaction graphs are generated after transcription. |
| Replace heavy dependencies | Added sparse TF-IDF slide matching without a neural model. Normal graph JSON exports now use plain node/edge lists. | TF-IDF is optional; the existing embedding method remains default. Lexical matching misses paraphrases and Hindi/English cross-script equivalents. NumPy remains necessary for efficient audio/model operations. Optional NetworkX graph helpers remain compatible with research callers. |

The speech engine already used CTranslate2 int8 quantization. Replacing it simply because another runtime uses ONNX would require accuracy, latency and memory comparisons first. [faster-whisper documentation](https://github.com/SYSTRAN/faster-whisper).

The optional diarization adapter follows the upstream segmentation → speaker embeddings → global clustering interface. Choose model files and assess their licensing and performance for Indian meeting audio before deployment. [sherpa-onnx diarization documentation](https://k2-fsa.github.io/sherpa/onnx/speaker-diarization/index.html).

## Necessary correctness and usability fixes

- Hindi words retain combining vowel marks during search and TF-IDF tokenization. For example, `हिंदी` and `भेजूँगा` remain complete words.
- Added common `main/mai/mein`, request and commitment forms in Hinglish, plus explicit English commitments such as “I’ll send the report”. Original text and source timestamps remain unchanged.
- Added conservative guards against interpreting questions or negated statements as decisions, agreements or positive task commitments. These rules remain candidates for human review; they do not understand every clause or implication.
- Added bounded, owner-protected processing previews: latest saved transcript passages, progress and event candidates. Previews remain available through interrupted-job recovery.
- Added exact-digital-silence skipping before Whisper model loading; quiet speech and room noise still receive normal VAD/ASR.
- Added recording diagnostics for digital silence, peak amplitude and samples near full scale. Potential clipping triggers a review notice; diagnostics are not accuracy probabilities.
- Low-scoring transcript passages have a “Review audio” shortcut. Model scores remain uncalibrated.
- Graph JSON now preserves multiple source relationships between the same events rather than overwriting a relationship in a simple graph.
- Android compiles shared rule banks once and processes only new transcript passages for partial reports, replacing repeated full-history rule matching. Exact silence also avoids native model loading. Existing compatible transcript checkpoints remain reusable.
- Added a manual phone-recording evaluation command with separate Hindi/English/Hinglish groups and word-count-weighted WER. Human transcripts are required; no self-generated ground truth is used.

## Measured ASR tradeoff

Fresh runs on **AMI ES2002a, Array1-01, seconds 30–630**, with multilingual Whisper small/int8:

| Central chunk length | Word error rate | Processing time for 600 s | Python process peak RSS |
| --- | ---: | ---: | ---: |
| 300 seconds | 45.8364% | 82.254 s | 1,516.7 MiB |
| 120 seconds | 41.4886% | 115.043 s | 1,479.7 MiB |

The 120-second setting reduced WER by **4.3478 percentage points** on this sample and reduced peak RSS by about **2.4%**, while taking about **40% longer**. It is the default for earlier previews and the observed recognition improvement; use 300 seconds when throughput matters more. Smaller buffers do not eliminate model-weight memory.

Both runs used fresh cache identifiers. Other local tests ran during part of the comparison, so these timings are practical observations, not an isolated performance study. This is one English distant-microphone recording with overlap/disfluencies; it is not Hindi/Hinglish accuracy evidence. Earlier historical timings in `PROJECT_STATUS.md` were obtained in different runs and should not be treated as a controlled speed comparison.

Detailed metrics without transcript text: [efficiency-results.json](efficiency-results.json). Full local artifacts are in `outputs/evaluation/benchmark_ES2002a_30_600_small_efficiency_v5_{300,120}_benchmark.json`.

## Verification

**494 Python tests passed** (7 dependency deprecation warnings, 7.41 seconds). Frontend build/lint, browser fixtures, real offline integration and Android build/JVM checks passed. Results are recorded in `efficiency-results.json` and the linked project status. Evidence files:

- `logs/tests_efficiency_release.log`: complete Python regression suite.
- `logs/browser_efficiency_final.log`: production frontend, synthetic microphone/recovery, processing preview, settings, pagination, notes/export fixtures; no JS errors or overflow at 390 px. No server was started.
- `logs/frontend_efficiency_build_final.log`, `logs/frontend_efficiency_lint_final.log`: frontend build and lint.
- `logs/ppt_efficiency_offline.log`: real 90-second AMI speech plus PPT; TF-IDF, previews and all reports passed, zero socket connections, no duplicate processed WAV.
- `logs/long_efficiency_final.log`: 7,290-second timeline passed in 17.896 s, 1,008.4 MiB peak RSS, zero network attempts; first speech at 7,202.05 s. Most input was synthetic silence, so this does not establish real long-meeting accuracy.
- `logs/android_efficiency_jvm_release.log`: WAV handling and actual exported bilingual rule banks tested on the JVM.
- `logs/android_efficiency_build_release.log`: ARM64/x86_64 development APK compiled and signed. New flows still need physical-device validation; no emulator or phone was launched during this upgrade.

ONNX model boundaries are mocked in regression tests. Real ONNX model speed, memory, speaker error rate and Hindi/Hinglish performance have not been measured. Android remains without speaker separation, slide alignment and the full laptop analysis engine.

## Manual next steps

The normal app uses the already installed environment/models. Run `bash start_app.sh` yourself when ready. See [RUN_MANUALLY.md](RUN_MANUALLY.md) for optional ONNX provisioning, TF-IDF settings, chunk selection and phone-recording evaluation. None of these optional installations is required for the existing transcription workflow.

The next accuracy milestone requires consented phone recordings with independently checked human transcripts, held-out speakers/meetings, and annotated speakers/decisions/tasks. Fine-tuning or switching model runtimes should follow those measurements.
