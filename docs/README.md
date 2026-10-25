# InfluenceIQ / Meet IQ — master developer and research documentation

Updated **19 October 2026**. Start with the [main/nested project reconciliation](validation/25_NESTED_PROJECT_RECONCILIATION_2026_10_19.md), [current readiness delivery](validation/23_READINESS_2026_10_18.md) and [plain terminal startup/device commands](guides/RUN_CURRENT.md). The current Android APK is **0.7.1-prototype**, with [shared web/Android accounts and explicit meeting sync](guides/ACCOUNT_SYNC.md). See [account sync validation](validation/24_ACCOUNT_SYNC_2026_10_18.md). Older chapters retain dated experiments and comparisons; [the latest structure/performance audit](validation/22_STRUCTURE_PERFORMANCE_AND_GAPS.md) explains changes since those snapshots.

The [cumulative final CA4 report](submitted/Group12_Multimodal_AI_Final_Report_CA4.pdf) and its [editable Markdown](submitted/Multimodal%20AI%20Mini%20Project%20Continuous%20Assessment%204.md) were prepared on **10 October 2026**. It includes the three alignment comparisons, corrected EDA and scoped results. The [complete supporting record](submitted/Group12_Complete_CA1_to_CA4_Record.pdf) also preserves earlier submitted PDFs.

This project analyses meetings locally: audio becomes a speaker-attributed transcript; optional PPT content is matched to passages; NLP rules extract candidate actions, decisions, evidence, interactions and influence. Users can correct speaker names/roles and revisit results in history. There is no generative notes/chat feature. Influence scores and inferred roles are analytical estimates requiring review against the recording.

The [presenter-influence study guide](research/PRESENTER_INFLUENCE_STUDY.md), added 24 October 2026, keeps outcome influence as the research objective and covers blind annotation preparation, contribution-attribution corrections and ranking evaluation.

The [contextual-model experiments](research/CONTEXTUAL_INFLUENCE_UPGRADE.md) record optional transformer, topic, outcome-link, speaker-margin and XGBoost paths, with measured results and remaining independent-annotation requirements.

The [AI-annotated outcome-link pilot](research/AI_OUTCOME_PILOT.md) records the completed assistant review, separate weak-supervision experiment and paper-reporting limits.

The canonical workspace is `/home/amitkumar/Music/MAI Project`. The old nested repository has been retired to `waste/InfluenceIQ--offline-meeting-intelligence-system-/`; useful missing historical records were preserved separately. See the [complete inventory and cleanup record](validation/26_LEGACY_CLEANUP_2026_10_19.md). Launch the application from the canonical workspace.

The [Read.ai comparison and repository review](validation/27_READ_AI_COMPARISON_AND_FOLLOWUPS_2026_10_19.md) records current feature gaps and candidate model tradeoffs. [Reviewed task owners, deadlines, completion status and offline calendar export](guides/FOLLOW_UPS.md) now work on web and Android without new models.

## Start on this machine

Run commands from the project directory:

```bash
cd '/home/amitkumar/Music/MAI Project'
export MAI_HOST=127.0.0.1
export MAI_PORT=8001
.venv/bin/python -m backend.api
```

Open **http://127.0.0.1:8001**. Stop the foreground server with Ctrl+C. The current frontend build is already prepared; use the [separate frontend/backend guide](guides/RUN_CURRENT.md) for development. The backend port is configurable to avoid other local applications. The API has one meeting worker; a second meeting waits for the first. Use `python -m backend.api` through the project venv for direct API startup.

For a new installation:

```bash
bash scripts/setup.sh
.venv/bin/python scripts/download_models.py --slides
.venv/bin/python scripts/download_speaker_models.py
.venv/bin/python scripts/validate_setup.py
bash scripts/start_app.sh
```

Setup creates `.bootstrap` for uv and `.venv` for Python 3.11, installs CPU PyTorch and the locked dependencies in `environment/`, and builds the website. Model provisioning needs connectivity once. Meeting inference uses local cached models afterward. Read [environment details](development/03_ENVIRONMENT_AND_SETUP.md), [manual commands](guides/RUN_MANUALLY.md) and [quick start](guides/QUICK_START.md). Do not relocate the venv independently: its launch scripts contain absolute interpreter paths.

Edit `config/config.yaml`; optional secrets belong in `config/.env`, using `config/.env.example` as a template. Restart after YAML changes. The active SQLite account/history database is `data/state/nexus_v2.db`; uploads, inference caches and `.runtime/jwt-secret` are retained. Preserve these for account/history continuity. Keep private runtime/archive data out of publication assets.

## Folder map

```text
MAI Project/
├── backend/          FastAPI, accounts, private history and serialized job worker
├── src/              audio, PPT, fusion, NLP, influence, reports, evaluation, utilities
├── frontend/         React/Vite source, dependencies and generated website
├── android/          native offline app, bundled model assets, tests and APK build
├── config/           YAML settings, private env file, env template and pytest settings
├── environment/      Python requirements and installed-version lock
├── scripts/          setup, startup, checks, provisioning, benchmarks, training CLI
├── deployment/       workstation launcher and HTTPS/configuration examples
├── docs/             this master index and categorized Markdown documentation
│   ├── guides/       current startup and usage
│   ├── development/  setup, architecture, module reference and path migration
│   ├── research/     fusion, novelty, evaluation, training and paper blueprint
│   ├── validation/   dated results and delivery/audit evidence
│   ├── operations/   offline and workstation deployment
│   ├── android/      Android build/design instructions
│   ├── submitted/    immutable submitted report
│   ├── history/      superseded workstation guides
│   └── handbook/     original audit index
├── data/             recordings, annotations, stage artifacts and account state
├── AMI_dataset/      existing local research dataset and annotations
├── models/           provisioned ASR, speaker, embedding and Android model weights
├── outputs/          reports, evaluations and training/research artifacts
├── logs/             diagnostics and validation logs
├── tests/            Python regression suite
├── notebooks/        notebook workspace
├── archive/          verified older source archive, private legacy recovery records and tools
├── waste/            inactive nested checkout; reversible, private and excluded from Git/tests
├── .bootstrap/       uv bootstrap environment
├── .venv/            project Python environment
├── .runtime/         durable job state, secrets and local validation tools
└── .gitignore        Git's conventional root control file
```

Application files, scripts, configuration and Markdown are inside folders. `.gitignore` is the conventional root exception. Do not move `.git`, `.venv` or third-party dependency internals merely to change their layout. The [path migration table](development/PATH_MIGRATION.md) maps relocated files. [Source reference](development/15_SOURCE_CODE_REFERENCE.md) describes the modules; old comparison manifests use the names from their dated snapshot.

## How the implemented pipeline works

1. Browser/API accepts audio and normalizes it with FFmpeg to 16 kHz mono PCM. Recording, interrupted chunks and inputs remain local.
2. Pretrained sherpa-onnx segmentation/embedding models cluster speakers. A known speaker count can constrain clustering. Failures in auto mode produce `UNKNOWN`, with a visible warning; no participant identity is invented.
3. Multilingual faster-whisper transcribes central chunks with overlap and assigns passages using speaker timestamps. The default laptop profile is small, CPU/int8, four threads. Android uses whisper.cpp base and packaged speaker models.
4. Optional PPT extraction reads text, tables and notes. Python supports pretrained sentence embeddings or TF-IDF. Transcript–slide cosine scores combine with temporal overlap when timing exists. Untimed decks use semantic scores. Low-confidence matches are rejected.
5. English/Hindi/Hinglish keyword rules produce events. Evidence links, candidate decision lineage and interaction relations feed weighted decision-linked influence. Source timestamps and event/slide references make the estimates inspectable.
6. Reports/history expose transcript, participant edits, actions, decisions and influence; JSON/Markdown/HTML/CSV and transcript exports remain available. Each new Python report records processing-stage durations.

Read [architecture](development/04_ARCHITECTURE_AND_PIPELINE.md), [audio](development/05_AUDIO_IMPLEMENTATION.md), [fusion formulas and limitations](research/06_FUSION_METHODS.md), [NLP/influence](development/07_EVENTS_DECISIONS_INTERACTIONS_INFLUENCE.md) and [API/frontend](development/08_APPLICATIONS_API_FRONTEND_ANDROID.md). [Android delivery and real measurements](validation/19_ANDROID_SPEAKERS_FUSION_AND_VALIDATION.md) distinguish the native implementation from Python.

## Older code versus current code

The older copy was an incomplete GPU-workstation snapshot. It already contained the research fusion/events/evidence/decision/influence modules; those are not all newly invented here. Its saved configuration uses CPU/int8, while historical logs describe CUDA attempts. It did not include the workstation's live dataset, model weights or venv, so exact workstation equivalence cannot be established.

The initial audit compared 147 first-party files: 49 identical, 32 modified and 66 current-only; 561 shared report files were identical. These are **7 October snapshot counts**, not current totals. The active system subsequently gained the simplified NLP-only website, real speaker analysis, Android speaker/influence/PPT analysis, training tooling, deployment preparation, and this folder/performance update.

The redundant `mai folder older/` working copy has been removed after verifying **662 archived files** against their SHA-256 hashes. Recover its application/source/report snapshot from `archive/older_project.tar.gz` and the per-file `archive/older_project_manifest.json`. The old Git commit `701ad8e2645ba35f560021f8d26611064668f4f9` is already an ancestor in the active Git repository. Generated/system caches were excluded from that source archive. It is not a full operating-system backup.

For review, read [history/comparison](research/01_PROJECT_HISTORY_AND_COMPARISON.md), [dated file-by-file manifest](validation/14_FILE_BY_FILE_COMPARISON.md), [report/feedback implementation](validation/18_SUBMITTED_REPORT_FEEDBACK_AND_NLP_DELIVERY.md) and [the submitted report](submitted/GRPUP_NO_12_MAI_REPORT_1_LLM.md). Submitted-report content was unchanged during relocation.

## Why processing can take longer

The saved 6 October 42.7-minute job had unavailable speaker analysis and no PPT alignment. The 7 October job with the same audio duration had speaker analysis and embedding-based PPT fusion. Those additional computations matter. Historical jobs did not record stage durations, so the exact historical slowdown remains unmeasured.

This update reuses one configured Whisper model in the worker, shares one sentence-embedding model between PPT and transcript alignment, batches transcript encoding, and avoids rebuilding an unchanged website on startup. It retains decoding/quality settings. A local benchmark of 256 saved passages against 34 slides measured **1.43× faster semantic scoring**, with identical semantic-only slide selections; this is not a whole-pipeline improvement or an accuracy claim. Speaker threading tests retained four threads as the fastest tested setting. [Chapter 22](validation/22_STRUCTURE_PERFORMANCE_AND_GAPS.md) contains methodology, timings and limitations.

## Research, training and journal writing

Current fusion is **audio-derived text plus extracted PPT text, optionally with temporal overlap**, followed by evidence/decision-linked scoring. Android uses native-text TF-IDF and a simpler candidate-lineage analysis. No visual encoder, learned end-to-end fusion network or trained influence model is deployed. Pretrained ASR, speaker and embedding models are already used; inference does not require training them again.

A CPU weight-training CLI exists for human-labelled, disjoint meeting-level train/validation/test splits. It exports a research artifact and does not automatically change production weights. No real human-labelled training run has been completed. [Training and multimodal research](research/20_TRAINING_DATA_AND_MULTIMODAL_RESEARCH.md) explains datasets, labels and the distinction between implemented and proposed work.

Read [novelty and related work](research/10_RESEARCH_NOVELTY_AND_RELATED_WORK.md), [metrics/baselines/ablations](research/11_EVALUATION_BASELINES_AND_ABLATIONS.md), [paper blueprint](research/12_JOURNAL_PAPER_BLUEPRINT.md), [output inventory](validation/09_DATA_OUTPUTS_AND_RESULTS.md) and [remaining gaps](development/13_DEVELOPER_HANDOVER_AND_GAPS.md). The newest audit supersedes relocated paths and the evaluator defects listed in older chapters.

Journal comparisons require the same labelled meetings, microphone/audio windows, model/device settings, thresholds and metrics across methods. Report cold, warm-model and cached latency separately. Do not present existing identical report artifacts, synthetic slides, tests or inferred influence scores as demonstrated novelty or research accuracy. Hindi/Hinglish accuracy, real paired slide alignment, human influence agreement, physical-phone/long-meeting validation and deployed cloud performance still need data and experiments.

## Verification and developer workflow

```bash
.venv/bin/python scripts/validate_setup.py
OMP_NUM_THREADS=4 bash scripts/check.sh -q
npm --prefix frontend run lint
npm --prefix frontend run build
node scripts/test_browser_offline.cjs
bash android/test.sh
```

Use `scripts/check.sh` so pytest targets `tests/` with `config/pytest.ini`, avoiding vendored Android/runtime tests. Browser checks use intercepted fixtures; they are not ASR benchmarks. Android JVM tests are distinct from emulator and physical-phone tests.

For existing meeting artifacts:

```bash
.venv/bin/python scripts/run_evaluation.py --meeting-id YOUR_MEETING_ID --ablation
.venv/bin/python scripts/benchmark_alignment.py --meeting-id YOUR_MEETING_ID --output outputs/evaluation/alignment_benchmark.json
```

Supply real annotations to measure research metrics. The evaluator reads full saved transcript/speaker/alignment outputs and leaves annotation-dependent metrics unavailable when no ground truth exists. `--stage-timings` overrides saved stage timings; comparison CSVs use the meeting ID to avoid overwriting other runs.

For remote processing, read [offline/workstation operation](operations/21_OFFLINE_AND_WORKSTATION_DEPLOYMENT.md). Android remains independently offline; its optional Account & sync screen shares identity and explicitly publishes/downloads completed meetings with the configured server. Its separate browser link opens the website. A GPU requires compatible runtime provisioning. No public deployment has been completed.

## Documentation index

The sections above give the recommended reading order. This inventory preserves the full documentation without merging dated evidence into unsupported current claims.

### Guides

- [Review follow-ups and export calendar deadlines](guides/FOLLOW_UPS.md)
- [Current plain terminal commands and Samsung phone setup](guides/RUN_CURRENT.md)

- [Meet IQ — Offline Meeting Intelligence](guides/QUICK_START.md)
- [Manual startup — updated 7 October 2026](guides/RUN_MANUALLY.md)

### Development

- [Folder structure and ownership](development/02_FOLDER_STRUCTURE.md)
- [Environment, venv, models, and reproducible startup](development/03_ENVIRONMENT_AND_SETUP.md)
- [Architecture and complete pipeline](development/04_ARCHITECTURE_AND_PIPELINE.md)
- [Audio implementation and recovery](development/05_AUDIO_IMPLEMENTATION.md)
- [Events, evidence, decisions, interactions, and influence](development/07_EVENTS_DECISIONS_INTERACTIONS_INFLUENCE.md)
- [API, browser, local AI, and Android implementation](development/08_APPLICATIONS_API_FRONTEND_ANDROID.md)
- [New developer handover and ranked remaining work](development/13_DEVELOPER_HANDOVER_AND_GAPS.md)
- [Source reference and entry points](development/15_SOURCE_CODE_REFERENCE.md)
- [Notebook workspace](development/NOTEBOOKS.md)
- [File relocation — 8 October 2026](development/PATH_MIGRATION.md)

### Research

- [Project history and older-versus-current comparison](research/01_PROJECT_HISTORY_AND_COMPARISON.md)
- [Exact fusion methods implemented](research/06_FUSION_METHODS.md)
- [Research contribution, novelty boundaries, and related work](research/10_RESEARCH_NOVELTY_AND_RELATED_WORK.md)
- [Evaluation, baselines, ablations, and publication blockers](research/11_EVALUATION_BASELINES_AND_ABLATIONS.md)
- [Journal paper blueprint and comparison material](research/12_JOURNAL_PAPER_BLUEPRINT.md)
- [Training, annotation and multimodal research](research/20_TRAINING_DATA_AND_MULTIMODAL_RESEARCH.md)

### Validation

- [Website progress, participant review and validation — 19 October 2026](validation/28_WEBSITE_PROCESSING_2026_10_19.md)
- [Read.ai comparison, repository research and follow-up delivery — 19 October 2026](validation/27_READ_AI_COMPARISON_AND_FOLLOWUPS_2026_10_19.md)
- [Complete legacy-folder inventory and reversible cleanup — 19 October 2026](validation/26_LEGACY_CLEANUP_2026_10_19.md)
- [Main/nested checkout reconciliation and authorized history import — 19 October 2026](validation/25_NESTED_PROJECT_RECONCILIATION_2026_10_19.md)
- [Shared web/Android accounts and sync verification — 18–19 October 2026](validation/24_ACCOUNT_SYNC_2026_10_18.md)
- [Readiness fixes, OCR, evaluation and Android memory hardening — 18 October 2026](validation/23_READINESS_2026_10_18.md)

- [Structure, processing performance and remaining gaps — 8 October 2026](validation/22_STRUCTURE_PERFORMANCE_AND_GAPS.md)
- [Data, output artifacts, and measured results](validation/09_DATA_OUTPUTS_AND_RESULTS.md)
- [File-by-file older/current comparison](validation/14_FILE_BY_FILE_COMPARISON.md)
- [Audit provenance, validation, and limits](validation/16_AUDIT_PROVENANCE_AND_VALIDATION.md)
- [Minimal interface update — 7 October 2026](validation/17_MINIMAL_UI_IMPLEMENTATION_AND_VALIDATION.md)
- [Submitted report, teammate feedback and NLP delivery — 7 October 2026](validation/18_SUBMITTED_REPORT_FEEDBACK_AND_NLP_DELIVERY.md)
- [Android speaker, influence and PPT fusion delivery](validation/19_ANDROID_SPEAKERS_FUSION_AND_VALIDATION.md)
- [Efficiency and bilingual changes — 6 October 2026](validation/EFFICIENCY_IMPROVEMENTS.md)
- [Project audit and implementation status — 5 October 2026](validation/PROJECT_STATUS.md)

### Operations

- [Offline operation and optional workstation/cloud deployment](operations/21_OFFLINE_AND_WORKSTATION_DEPLOYMENT.md)

### Android

- [InfluenceIQ Android design and validation](android/DESIGN.md)
- [InfluenceIQ Android prototype](android/README.md)

### Submitted

- [---](submitted/GRPUP_NO_12_MAI_REPORT_1_LLM.md)

### History

- [Audio-Only Meeting Intelligence Conversion Guide](history/AUDIO_ONLY_CONVERSION_GUIDE.md)
- [Meet IQ - Next Steps & Architecture](history/NEXT_STEPS.md)
- [Complete Project Execution Guide: Multimodal Meeting-Intelligence System](history/PROJECT_EXECUTION_GUIDE.md)
- [Repository and product review — 5 October 2026](history/REPOSITORY_REVIEW.md)

### Handbook

- [Historical research and developer audit index](handbook/README.md)
