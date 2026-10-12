# Project history and older-versus-current comparison

Layout update, 8 October 2026: use the [master documentation](../README.md) and [structure/performance update](../validation/22_STRUCTURE_PERFORMANCE_AND_GAPS.md). Historical comparisons and measurements below describe their stated audit date. The older working tree is now archived; current paths and runtime are described in the update.

[Handbook index](../handbook/README.md)

## What “older GPU workstation version” means here

The comparison baseline is the directory `mai folder older`, not an accessible remote workstation. [`terminal output `](../../archive/older_project.tar.gz) records September 2026 executions under `/home/CL502-12/MAI Project/`, Python 3.10, and faster-whisper `base`/CUDA/float16. It also records a missing `libcublas.so.12` failure. The older [execution guide](../../archive/older_project.tar.gz) describes Ubuntu, GPU acceleration, and an RTX A4000 expected runtime.

Those are historical instructions/logs, not a current hardware inspection or controlled benchmark. The older [configuration](../../archive/older_project.tar.gz) already says `asr.device: cpu`, `compute_type: int8`, and `model_size: base`. The old ASR loader already contains CUDA library preloading and CPU fallback. Therefore, “we newly invented CPU/int8 support” would be incorrect.

The copy has source, frontend, tests, report outputs, database files, and a bundled JRE, but no dataset or venv and only a zero-byte model placeholder. Preserve it as a source/artifact reference; it cannot reproduce the original workstation alone.

## Verified timeline

| Evidence | What it establishes |
| --- | --- |
| Historical September log and guides | A Python 3.10 workstation workflow attempted CUDA; some ASR jobs failed because CUDA 12 libraries were unavailable |
| Git `701ad8e2`, 23 September 2026 | Initial committed enterprise/backend/React/Flutter structure; a Git commit is not proof every advertised feature worked |
| Git `8e8164ec`, 5 October 2026 | Laptop migration: environment scripts, orchestrator, offline provisioning, robust API, Android implementation, tests, and recorded validation |
| Git `d27e29de`, 6 October 2026 | Android local SDK configuration change |
| Git `3e90a243`, 6 October 2026 | Efficiency/bilingual changes, local notes/search/export, TF-IDF, optional ONNX adapter, additional tests |
| Working tree at audit | Later Android 0.4.0 UI/source changes and documentation are partly uncommitted; the older folder itself is untracked |

The table records inspectable history. It does not assign individual authorship or imply that all old code predates every feature named in commit messages.

## Implementation comparison

| Area | Supplied older copy | Current copy | Research implication |
| --- | --- | --- | --- |
| Core folders | `src/audio,ppt,fusion,meeting,evaluation,report,utils,pipeline` | Same core folders | Structure is retained |
| End-to-end orchestration | `src/pipeline/orchestrator.py` is 0 bytes; stage CLI/API perform separate calls | `run_meeting()` coordinates audio to final reports | New execution integration, not a new fusion model |
| Environment | Unpinned 14-package requirements; historical Python 3.10 venv absent | Python 3.11 venv, compatibility pins, full installed-version lock, setup script | Reproducibility improvement |
| Launcher | Two background servers, NVM/home assumptions, CUDA-library export | Project-relative foreground launcher, frontend build, one origin on port 8000 | More portable local deployment |
| Decode/preprocess | Whole-file SoundFile array and SciPy resampling | FFmpeg decode, atomic PCM output, reuse of normalized audio | Reduced audio-buffer/intermediate-copy overhead |
| Upload handling | Whole-file uploads and concatenation | Bounded upload reads, 32 ordered parts, total-size limit, FFmpeg pipe concatenation, hash validation | Ordered parts are consecutive recordings, not microphone-array fusion |
| VAD | Separate whole-recording path using torch.hub | Packaged Silero weights and bounded blocks in stage runner; faster-whisper VAD in main workflow | Explicit offline operation and bounded standalone VAD |
| ASR | Whole-file model call, no word timestamps, file-exists cache | Central chunks, context overlap, word timestamps, content-addressed checkpoints, progress, exact-silence skip | Recovery and boundary-handling engineering |
| Default ASR | `base`, CPU/int8 in saved config | `small`, CPU/int8, 120 s, four threads, en/hi scope | Defaults and operating profile changed |
| Diarization | pyannote and automatic CUDA use when available; no optional backend | Configured device, validated cache, auto/required/off workflow; optional sherpa-onnx adapter | ONNX is not provisioned or empirically validated |
| Fusion | MiniLM cosine similarity plus optional temporal overlap and weighted combination | Same default; optional TF-IDF content score and method metadata | Default fusion is inherited |
| PPT | Native text/tables/notes and structural metadata; OCR stub | Byte-identical PPT implementation | No new image understanding or OCR |
| Events | English keyword rules, one selected type per segment | Unicode normalization, Hindi/Hinglish phrases, explicit commitments, question/negation blockers | Rule coverage expanded; semantic accuracy unmeasured |
| Evidence | Temporal/type heuristic links, slide-to-event support edges | Byte-identical | Not new entailment reasoning |
| Decision reconstruction | Temporal clusters, statuses, roles, lineage | Same core logic; direct graph-list JSON serialization | Model behavior largely inherited |
| Interactions | Three passes using evidence, lineage, reactive events | Same inference; direct graph serialization preserves records | Better graph artifact fidelity |
| Influence | Seven-feature max-normalized weighted score | Same formula; UNKNOWN excluded; main-runner speaking baselines use full transcript | Neither version implements the README's claimed PageRank scoring |
| Evaluation | WER, approximate label-sensitive DER, baselines, weight ablations | Correct permutation-aware DER primitive; inherited evaluation CLI/baselines/ablation problems remain | See [11](11_EVALUATION_BASELINES_AND_ABLATIONS.md) before publication |
| Reports | Structured JSON/MD/HTML/CSV; participant time based on event subset | Transcript-based duration/time, processing diagnostics, full transcript, additional exports | More complete descriptive reporting |
| Local notes/Q&A | Absent | Optional local Ollama, checked quotes, resumable note chunks, lexical retrieval | New optional component; quote presence is not factuality validation |
| API privacy | Fixed JWT secret, public media mount, reset-token disclosure | Private generated secret, ownership checks, scoped playback tokens, terminal recovery | Local application hardening |
| Browser | React dashboard/recording/upload | Persistent IndexedDB recording, pause/resume, devices/tab mix, previews/settings, notes/search/export | User workflow improvement |
| Android | No Android directory | Native Java/JNI/whisper.cpp, local recordings and analysis, latest 0.4.0 interface | Independent prototype; no speakers, PPT, graphs, influence, or LLM notes |

## What was retained unchanged

All PPT modules, temporal alignment, semantic alignment, evidence extraction, baseline/ablation modules, several regression suites, and historical scripts/guides are identical. The [manifest](../validation/14_FILE_BY_FILE_COMPARISON.md) provides every file and hash.

The root `run_resume_pipeline.sh`, `run_single_test.sh`, and `run_small_chunk.py` are retained historical tools. Do not mistake unchanged old guides for the current recommended setup. The Git history contains removed Flutter scaffold files; neither inspected filesystem copy has a working Flutter implementation.

## Are the folders the same as the workstation?

**Same core research layout: yes. Identical code: no. Complete workstation environment/data: no.**

To certify the live workstation, obtain its checked-out commit and dirty diff, Python/package/CUDA versions, model revisions, dataset/annotation manifests, evaluation outputs, and hardware details. Compare those with [16](../validation/16_AUDIT_PROVENANCE_AND_VALIDATION.md) and the file hashes. Until then, call this an older supplied snapshot comparison, not a verified workstation replication.
