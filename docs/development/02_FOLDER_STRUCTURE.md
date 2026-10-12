# Folder structure and ownership

Layout update, 8 October 2026: use the [master documentation](../README.md) and [structure/performance update](../validation/22_STRUCTURE_PERFORMANCE_AND_GAPS.md). Historical comparisons and measurements below describe their stated audit date. The older working tree is now archived; current paths and runtime are described in the update.

[Handbook index](../handbook/README.md)

## Current project map

```text
MAI Project/
├── README.md, RUN_MANUALLY.md, PROJECT_STATUS.md
├── EFFICIENCY_IMPROVEMENTS.md, REPOSITORY_REVIEW.md
├── PROJECT_EXECUTION_GUIDE.md, NEXT_STEPS.md       # historical
├── AUDIO_ONLY_CONVERSION_GUIDE.md               # historical
├── research_developer_docs/                     # this handbook
├── config.yaml                                 # research/inference defaults
├── requirements.txt, requirements-lock.txt
├── .env.example                                # empty credential template
├── .env                                        # private local credentials
├── .bootstrap/                                 # setup uv environment
├── .venv/                                      # isolated Python 3.11
├── .runtime/                                   # private jobs/uploads/keys/build tools
├── api.py, start_app.sh
├── nexus.db, nexus_v2.db                        # existing SQLite files
├── src/
│   ├── audio/                                  # decode, VAD, ASR, diarization
│   ├── ppt/                                    # slide data/text/features/embeddings
│   ├── fusion/                                 # temporal, semantic, lexical matching
│   ├── meeting/                                # events/evidence/decisions/notes/search
│   ├── pipeline/orchestrator.py                # shared complete workflow
│   ├── report/                                 # report assembly/export
│   ├── evaluation/                             # metrics/baselines/weight ablations
│   └── utils/                                  # config/paths/cache/checkpoints/text
├── frontend/
│   ├── src/App.jsx, MeetingNotes.jsx, recordingStore.js
│   ├── src/main.jsx, index.css, App.css
│   ├── package.json, package-lock.json, vite.config.js
│   ├── node_modules/                           # installed dependencies
│   └── dist/                                   # compiled UI served by FastAPI
├── android/
│   ├── app/src/main/AndroidManifest.xml
│   ├── app/src/main/java/org/meetiq/offline/     # native UI/service/storage/audio
│   ├── app/src/main/cpp/                        # JNI and CMake
│   ├── app/src/main/assets/                     # exported phrase/blocker rules
│   ├── app/src/main/res/                        # local icons/themes
│   ├── test/                                   # JVM checks
│   ├── setup.sh, build.sh, test.sh
│   ├── vendor/whisper.cpp/                      # upstream dependency, ignored
│   ├── build/meet-iq-debug.apk                  # direct-build output
│   ├── app/.cxx/                               # generated alternate-build artifacts
│   └── design/screenshots/                     # emulator UI evidence
├── scripts/                                    # setup/runners/benchmarks/validation
├── tests/                                      # Python regressions
├── notebooks/README.md                         # notebook guidance, no implemented study
├── AMI_dataset/                                # supplied external corpus
├── data/
│   ├── raw/audio/, raw/ppt/                     # staged corpus inputs
│   ├── processed/audio/, slides/, alignment/
│   ├── processed/events/, decisions/, interactions/, influence/
│   ├── processed/transcripts/                  # placeholder, main transcripts use audio/
│   ├── custom_test/                            # normalized application recordings
│   ├── checkpoints/per_meeting/                # resume_state.json
│   └── annotations/                            # human-annotation templates
├── models/
│   ├── hf/hub/                                 # real local model snapshots/blobs
│   ├── ggml-base.bin                           # Android Whisper model
│   ├── audio/                                  # legacy directories
│   └── checkpoints/                            # legacy directories
├── outputs/reports/, evaluation/, exports/, visualizations/
├── outputs/android-design/                     # additional emulator artifacts
├── logs/                                       # prior build/test/integration evidence
├── mai folder older/                           # baseline snapshot; do not modify
├── jdk-17.0.12+7-jre/                           # transferred JRE, not a full JDK
└── run_resume_pipeline.sh, run_single_test.sh, run_small_chunk.py
```

The tree is a responsibility map, not a promise that every directory contains active outputs. Empty model/training directory names do not establish training or fine-tuning. The supplied JRE alone cannot compile Java; the Android build needs a JDK with `javac`.

## Older snapshot map

```text
mai folder older/
├── README.md, PROJECT_EXECUTION_GUIDE.md, NEXT_STEPS.md
├── AUDIO_ONLY_CONVERSION_GUIDE.md
├── api.py, config.yaml, requirements.txt, start_app.sh
├── src/{audio,ppt,fusion,meeting,pipeline,report,evaluation,utils}/
├── frontend/{src,package.json,package-lock.json,...}
├── scripts/, tests/, notebooks/
├── outputs/{reports,evaluation,exports,visualizations}/
├── models/{audio,checkpoints,.gitkeep}            # no weights
├── logs/                                       # empty
├── nexus.db, nexus_v2.db
├── jdk-17.0.12+7-jre/
├── terminal output                             # historical workstation log
└── legacy Python/shell batch runners
```

`data/`, `AMI_dataset/`, `.venv/`, `.bootstrap/`, `.runtime/`, and `android/` are absent from the older copy.

## Where changes belong

| Change | Primary location | Relevant validation |
| --- | --- | --- |
| ASR/chunk/speaker assignment | `src/audio/asr.py` | `tests/test_audio.py`, `test_laptop_workflow.py`, `test_efficiency.py` |
| Decode/preprocessing | `src/audio/parts.py`, `preprocess.py` | Laptop workflow/efficiency tests |
| Diarization backend | `diarization.py`, `onnx_diarization.py` | Model-boundary tests plus real DER experiments |
| Slide extraction/representation | `src/ppt/` | `tests/test_ppt.py` |
| Fusion scores/candidates | `src/fusion/` | `tests/test_alignment.py`, annotated alignment study |
| Event language rules | `src/meeting/events.py`, `language_rules.py` | Meeting/efficiency tests; regenerate Android assets |
| Evidence/decision/interaction/influence | `src/meeting/` | `tests/test_meeting.py`, human annotations |
| Notes/retrieval | `local_notes.py`, `search.py` | `tests/test_local_notes.py` |
| User ownership/jobs | `backend/api.py` | `tests/test_api.py` |
| Browser UX | `frontend/src/` | Build/lint and deliberate browser checks |
| Android lifecycle/audio/native behavior | `android/app/src/` | `android/test.sh`, direct build, emulator/device checks |
| Paper metrics/runners | `src/evaluation/`, `scripts/` | `tests/test_evaluation.py` plus ground-truth integration |

Transferred `.config/`, `.nvm/`, `.npm/`, `.gradle/`, credentials, and caches are machine state rather than research source. Do not copy them into a paper supplement. The audit did not read their credential contents.

Git ignores most datasets, outputs, weights, and runtime files. A source checkout alone will not contain all local evidence. Some generated `android/app/.cxx/` files are already tracked in Git; they are excluded from the first-party comparison and should not be counted as algorithm implementation.
