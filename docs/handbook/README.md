# Historical research and developer audit index

Start with the current [master documentation](../README.md). Folder reorganization, corrected evaluator and processing diagnostics are covered in [chapter 22](../validation/22_STRUCTURE_PERFORMANCE_AND_GAPS.md). This index preserves the original audit narrative.

Audited **7 October 2026, Asia/Kolkata**. This handbook compares the current project root with the supplied [`mai folder older`](../../archive/older_project.tar.gz) snapshot. It explains how to install, understand, extend, evaluate, and describe the system in a journal paper.

The latest Android/training/deployment delivery is in [19](../validation/19_ANDROID_SPEAKERS_FUSION_AND_VALIDATION.md), [20](../research/20_TRAINING_DATA_AND_MULTIMODAL_RESEARCH.md) and [21](../operations/21_OFFLINE_AND_WORKSTATION_DEPLOYMENT.md). These supersede earlier statements that Android lacks speakers/influence/fusion.

The latest delivered website/pipeline scope and submitted-report comparison are in [18 — NLP delivery](../validation/18_SUBMITTED_REPORT_FEEDBACK_AND_NLP_DELIVERY.md); generative notes/chat have since been removed.

Chapters 01–16 and their file hashes describe the audit snapshot **before** the subsequent UI changes. Read [17 — Minimal UI implementation and validation](../validation/17_MINIMAL_UI_IMPLEMENTATION_AND_VALIDATION.md) for the later October 7 changes. The snapshot counts below are historical, not a checksum manifest of the newly edited interface.

## What the audit establishes

The research module structure is substantially preserved. The older snapshot already implements transcript–slide alignment, event/evidence rules, decision lineage, interaction analysis, and decision-linked weighted influence. The migration made these modules usable through an end-to-end laptop pipeline and added recoverable audio processing, bilingual rules, optional TF-IDF matching and native Android. Optional local AI notes existed in the initial audit snapshot and were removed in chapter 18; chapter 19 adds native speaker/influence/fusion analysis.

The old folder is **not a complete workstation backup**: it lacks `data/`, `AMI_dataset/`, `.venv/`, and actual model weights. Its historical log documents a Python 3.10 CUDA attempt; its saved `config/config.yaml` already selects CPU/int8. Exact equivalence to the live GPU workstation cannot be established from this copy alone.

There are **147 first-party source/config/documentation files** in the comparison: **49 identical, 32 modified, 66 current-only, and 0 older-only**. See the exact scope and SHA-256 values in [14](../validation/14_FILE_BY_FILE_COMPARISON.md). These counts exclude datasets, outputs, environments, third-party vendor code, and generated builds.

All **561 report-directory files** common to the two copies are byte-identical. The current copy contains 84 additional report files, including validation/demo outputs. Existing reports therefore establish artifact availability, not an old-versus-new accuracy improvement. Measured WER evidence is limited to one English AMI excerpt; Hindi/Hinglish, slide alignment, decision quality, influence validity, and physical-phone performance still require evaluation.

## Reading order

| File | What you learn |
| --- | --- |
| [01 — History and comparison](../research/01_PROJECT_HISTORY_AND_COMPARISON.md) | What existed earlier, what changed, and what is genuinely inherited |
| [02 — Folder structure](../development/02_FOLDER_STRUCTURE.md) | Source, data, runtime, model, and output locations |
| [03 — Environment and setup](../development/03_ENVIRONMENT_AND_SETUP.md) | Workstation history, current venv, packages, models, configuration, launch commands |
| [04 — Architecture and pipeline](../development/04_ARCHITECTURE_AND_PIPELINE.md) | End-to-end execution and the distinction between the two Python runners |
| [05 — Audio implementation](../development/05_AUDIO_IMPLEMENTATION.md) | Decode, VAD, ASR, speakers, boundaries, checkpoints, and memory limits |
| [06 — Fusion methods](../research/06_FUSION_METHODS.md) | Exact implemented temporal/semantic/TF-IDF fusion, equations, defaults, and limitations |
| [07 — Meeting analysis](../development/07_EVENTS_DECISIONS_INTERACTIONS_INFLUENCE.md) | Event taxonomy, evidence edges, decision reconstruction, graphs, influence formula |
| [08 — Applications](../development/08_APPLICATIONS_API_FRONTEND_ANDROID.md) | API routes, browser workflow, local notes/Q&A, Android architecture and feature comparison |
| [09 — Data, outputs, results](../validation/09_DATA_OUTPUTS_AND_RESULTS.md) | Artifact schemas, existing experiment numbers, provenance, and result interpretation |
| [10 — Novelty and related work](../research/10_RESEARCH_NOVELTY_AND_RELATED_WORK.md) | Defensible contribution candidates, inherited methods, cited primary research |
| [11 — Evaluation and ablations](../research/11_EVALUATION_BASELINES_AND_ABLATIONS.md) | Existing metrics, confirmed evaluation defects, proper comparative experiment design |
| [12 — Journal blueprint](../research/12_JOURNAL_PAPER_BLUEPRINT.md) | Paper structure, methods wording, comparison tables, figures, and evidence checklist |
| [13 — Developer handover](../development/13_DEVELOPER_HANDOVER_AND_GAPS.md) | First-day workflow, extension points, tests, debugging, and ranked remaining work |
| [14 — File comparison manifest](../validation/14_FILE_BY_FILE_COMPARISON.md) | Every scoped file's status, size, and hashes in both copies |
| [15 — Source reference](../development/15_SOURCE_CODE_REFERENCE.md) | Module descriptions and Python entry points with source locations |
| [16 — Audit provenance](../validation/16_AUDIT_PROVENANCE_AND_VALIDATION.md) | How this handbook was checked and which evidence is historical |
| [17 — Minimal interface update](../validation/17_MINIMAL_UI_IMPLEMENTATION_AND_VALIDATION.md) | Earlier October 7 UI update; subsequent scope is in chapter 18 |
| [18 — Submitted report and NLP delivery](../validation/18_SUBMITTED_REPORT_FEEDBACK_AND_NLP_DELIVERY.md) | Six-objective comparison, local speaker setup, structured evidence views, removed generative features, test results and remaining accuracy gaps |
| [19 — Android speakers and fusion](../validation/19_ANDROID_SPEAKERS_FUSION_AND_VALIDATION.md) | Native model provisioning, participant edits, influence evidence, text fusion, measurements and limitations |
| [20 — Training and multimodal research](../research/20_TRAINING_DATA_AND_MULTIMODAL_RESEARCH.md) | Pretrained versus trainable components, real annotation needs, supervised influence trainer, novelty and journal experiments |
| [21 — Offline and workstation deployment](../operations/21_OFFLINE_AND_WORKSTATION_DEPLOYMENT.md) | Default offline phone mode, optional browser/server mode, GPU selection, launch/config files and undeployed boundaries |

For a new developer: read 01–08, then 13 and 15. For paper writing: read 06, 07, and 09–12. For checking workstation migration: read 01–03 and 14.

## Evidence labels

- **Implemented:** verified from executable source; does not imply empirical quality.
- **Recorded measurement:** historical saved metrics; current rerun measurements are explicitly dated in chapter 19.
- **Confirmed diagnostic:** a small assertion run during this audit, using no speech model.
- **Proposed:** experiment or extension still to be performed.
- **Unavailable:** evidence or capability not present here.

Names are historical: MAI is the folder/project name, Meet IQ is the laptop application, and InfluenceIQ is the latest Android label. They are related implementations, not three separately trained models.

This folder contains Markdown only. Chapters 01–16 document the preserved audit snapshot; chapters 17–21 describe subsequent implementation changes. User recordings and the older snapshot remain intact. A navigation link is added to the main project README.
