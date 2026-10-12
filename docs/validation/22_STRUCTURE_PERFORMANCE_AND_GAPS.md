# Structure, processing performance and remaining gaps — 8 October 2026

[Master documentation](../README.md)

This update supersedes earlier paths and evaluator defects in the dated handbook. It organizes the existing implementation; it does not establish new model accuracy, complete workstation parity or a published deployment.

## Delivered organization

- `backend/api.py` is the active API; launch with `bash scripts/start_app.sh` or `.venv/bin/python -m backend.api` from the project root.
- Settings/env/pytest files are in `config/`; dependency specifications are in `environment/`; scripts are in `scripts/`; evaluation JSONs are in `outputs/evaluation/`.
- Markdown guides and research documents are categorized under `docs/`, with one current master index at `docs/README.md`. Dated histories, manifests and submitted evidence are retained and labelled.
- The database moved to `data/state/nexus_v2.db`. Existing uploads, job states, model caches, account data and signing secret were retained. A pre-move SQLite backup is in `archive/legacy_state/before_reorganization.db`.
- Obsolete launch helpers are under `archive/legacy_tools/`; the legacy terminal transcript is under `archive/legacy_logs/`. These are historical evidence, not supported launchers.
- `.gitignore` is the sole loose root file, retained for Git's conventional repository layout. Application, shell, config and Markdown files are inside folders. Third-party caches, the active venv and `.git` retain their required structure.

The [path migration table](../development/PATH_MIGRATION.md) records all moves. Runtime imports, config/env loading, password recovery, setup, workstation launch and test discovery were repaired for the new paths. Current guide commands were updated; historical tree diagrams/manifests retain their original snapshot names.

## Older-folder cleanup and provenance

The older working copy occupied approximately **6.7 GB**, principally copied system/build caches and duplicate Git history. Its useful snapshot is now `archive/older_project.tar.gz` (approximately 556 KiB compressed), with `archive/older_project_manifest.json` storing per-file sizes and SHA-256 hashes. **662 archived files were verified** against the original before its removal and verified again after the move.

The old Git commit is `701ad8e2645ba35f560021f8d26611064668f4f9`; it is already contained in the active repository's ancestry. The tar archive preserves the copied working-tree application/source/report files, including differences outside the commit. Generated directories such as `.git`, `.gradle`, `.npm`, `.nvm`, dependency/build folders and the copied JRE were excluded. The snapshot remains incomplete as a live-workstation backup: old model weights, venv and dataset were not supplied.

Additional unused build/tool caches copied into the current project root were removed after checking that active scripts use actual system Java/user tool directories. Small historical configuration remnants and copied desktop configuration remain under private `archive/workstation_home/`; they are not active dependencies. `archive/pruned_generated_files.json` records the copied caches removed. This cleanup reclaims storage and reduces accidental scanning; it does not make ASR neural inference inherently faster.

Read-only SQLite comparison against the pre-move backup verified identical rows in both tables: **9 users and 13 meetings**. No account emails, password hashes or signing secrets were printed. The submitted report retained SHA-256 `e79538cf3beff442326574fb155086f921a4c48b5c7163e260ab296d2a828f68`. See [preservation verification](../../logs/maintenance_preservation.json).

To inspect the old source without recreating a duplicate working copy:

```bash
tar -tzf archive/older_project.tar.gz
# Example: view one original source file.
tar -xOzf archive/older_project.tar.gz 'mai folder older/src/fusion/semantic_alignment.py'
git show 701ad8e2645ba35f560021f8d26611064668f4f9:config.yaml
```

Keep the archive private: it can contain historical database/configuration material. For paper submission, export only reviewed research artifacts and anonymized data.

## Evidence for the reported slowdown

No active inference/API process was running when this inspection began. The saved comparable-duration jobs show:

| Saved job | Duration | Speaker analysis | PPT alignment |
| --- | --- | --- | --- |
| 6 October, `meeting_b91e8f0c5db44484b8510e7556da4cdf` | 2560.569 s | unavailable/UNKNOWN | absent |
| 7 October, `meeting_8e464f9471b34c46ad9f4ab3a547c923` | 2560.569 s | sherpa-onnx enabled | sentence embeddings |

Those jobs did not persist stage timings. Added speaker inference and PPT fusion are confirmed extra work; their precise historical cost cannot be recovered. Different cache states, model settings, CPU contention and thermal behavior can also affect latency, but were not recorded for those historical executions. Same audio duration alone is not proof of identical input bytes.

The current API serializes meetings through one worker to avoid competing heavy CPU jobs. Queued time, recording/upload time, decoder time and neural inference are different costs. A cached rerun is also different from a new meeting. New job state records elapsed stage times; the UI shows time spent in the current step, including long speaker processing. JSON reports record `processing.stage_timings_seconds`, `elapsed_seconds`, requested device/precision, thread count and whether the last ASR chunk was cached. Requested settings are labelled explicitly; a fallback's actual device is logged by the ASR loader. The last-chunk flag is not a claim that every chunk was cached.

Report timings cover the processing stages after module imports, through report preparation; upload/decode, queue wait and final JSON/checkpoint writes are excluded. Worker job-state timings include decode and worker elapsed time. Existing completed reports are not retroactively assigned invented timings.

## Changes that reduce avoidable work

| Change | Purpose / boundary |
| --- | --- |
| One cached Whisper instance keyed by model/device/precision/threads/offline setting | Avoid reloading weights for each new job in the single worker; changing settings selects a different instance. Restart releases retained model memory. |
| One shared sentence-transformer instance | Reuse the same CPU/offline model for slide embeddings and transcript matching; avoid duplicate model construction. |
| Transcript encoding in bounded batches of 32 | Reduce per-passage calls and normalize slide vectors once; keep only one batch of score rows live. |
| Native Python numbers in exported alignment | Preserve JSON serialization after batched NumPy computation. |
| Explicit zero vectors for empty slides/passages | Empty text must not contribute a semantic embedding match. |
| Reuse unchanged frontend build on startup | Skip Vite build when source/public/package/config inputs are older than `dist/index.html`; rebuild when inputs change. |
| Canonical `scripts/check.sh` | Restrict pytest to first-party `tests/`; avoid accidentally collecting NDK/vendor/browser scripts after config relocation. |

No beam-size, model-size, VAD, chunking, clustering threshold or temporal-fusion weights were changed for these performance fixes. Retaining a warm model trades some persistent RAM for avoided reload cost. The single-worker design prevents simultaneous model mutation; this cache is not designed as a multiple-worker deployment solution.

Sentence Transformers supports batched encoding and explicit local-only loading; see the [official API documentation](https://sbert.net/docs/package_reference/sentence_transformer/model.html). The [official faster-whisper benchmarks](https://github.com/SYSTRAN/faster-whisper) show that ASR batching can trade memory for throughput. Full ASR batching was not introduced here: it needs a separate RAM/quality evaluation with this pipeline's speaker timestamps and resumable chunks. The [sherpa-onnx diarization documentation](https://k2-fsa.github.io/sherpa/onnx/speaker-diarization/index.html) describes the segmentation/embedding/clustering workflow. Independent speaker chunking was not substituted, because it would reset cluster identities across chunks.

## Measured checks

### Semantic matching

[Benchmark output](../../outputs/evaluation/maintenance_alignment_batch.json), [log](../../logs/maintenance_alignment_batch.log), [reproducible CLI](../../scripts/benchmark_alignment.py).

- 256 real saved transcript passages, 34 saved slides, all-MiniLM-L6-v2, CPU/four Torch threads.
- Scalar path: **1.6661 s**. Batched path: **1.1672 s**. Ratio: **1.4274×** for warm-model cosine scoring only.
- Maximum rounded score difference: approximately **1.01e-6**. Semantic-only thresholded selections agreed for all 256 passages.
- One local run, scalar first, model warmed before both; OS/CPU warm-order effects remain. Model load was measured separately at 1.09 s. This is not a whole-meeting speedup, paired slide-grounding accuracy or proof that every future threshold/tie remains identical.

### Speaker threads

[Results](../../logs/maintenance_speaker_threads.json), [log](../../logs/maintenance_speaker_threads.log).

Real 90-second AMI ES2002a Array1-01 audio, source window 60–150 seconds, known count four, same models/thresholds:

| CPU threads | Time including adapter/model setup | Speaker turns | DER |
| --- | --- | --- | --- |
| 4 | 20.4257 s | 12 | 0.134815 |
| 1 | 35.2162 s | 12 | 0.134815 |
| 2 | 26.6317 s | 12 | 0.134815 |

DER uses existing manual AMI speaker annotations, optimal cluster-label mapping, 0.25 s collar and overlap. Cases ran in the order 4, 1, 2; this is one short-file experiment, not a universal thread recommendation. Four remains the configured default. There is no new old-code/current-code DER comparison here.

### Real end-to-end integration and cache behavior

[Timing JSON](../../outputs/evaluation/maintenance_pipeline_timing.json), [pipeline log](../../logs/maintenance_pipeline.log).

A fresh meeting ID used the real 90-second audio plus the existing artificial three-slide test PPT, required speaker analysis, known four speakers, English language and the unchanged small/CPU/int8 ASR profile:

| Stage | Fresh input | Same-ID cached repeat |
| --- | --- | --- |
| Preprocessing | 0.0496 s | 0.0553 s |
| Diarization | 18.4100 s | 0.0441 s |
| Transcription | 16.1251 s | 0.0180 s |
| Slide extraction/embedding | 1.7024 s | 0.0327 s |
| Alignment | 0.1282 s | 0.1166 s |
| Remaining NLP/report stages | about 0.043 s | about 0.043 s |
| Recorded processing elapsed | **36.4631 s** | **0.3138 s** |

Both runs produced four participant records, 20 transcript passages and speaker/PPT/NLP/report artifacts. The second run reused speaker and ASR caches and a warm embedding model. The first run used fresh inference caches but an already provisioned model/OS environment; it is not a first-ever installation benchmark. No baseline before these edits was measured for this complete pipeline. A cached repeat is not processing 90 seconds of new speech in 0.31 seconds. Synthetic slides test integration only and must not be used as journal alignment-accuracy evidence.

## Research evaluator repairs

`run_evaluation.py` now:

- reads the full saved transcript for WER, rather than concatenating only keyword-event snippets;
- reads saved diarization intervals for DER, rather than always evaluating an empty hypothesis;
- reads the complete saved alignment output rather than only slide-linked events;
- resolves a decision timestamp from its proposal's source event instead of assuming `proposal['start']`, which is not in that schema;
- reports unavailable source timestamps as an error when annotated decision evaluation would otherwise require them;
- loads saved stage timings/audio duration when available and allows explicit timing overrides;
- rejects a missing explicitly supplied annotation file and marks missing prediction artifacts as errors when ground truth exists, rather than presenting missing outputs as measured failures;
- writes meeting-specific comparison CSVs, validates meeting identifiers and resolves input artifacts against the project directory.

The latest stored 42.7-minute meeting completed metrics, six baseline methods and ablation CLI generation successfully without annotation-dependent fabricated scores. Synthetic regression coverage also verifies complete transcript/alignment inputs and real DER API wiring. No genuine influence annotations were supplied for a journal comparison. Remaining metric limitations from [chapter 11](../research/11_EVALUATION_BASELINES_AND_ABLATIONS.md), including coarse decision matching and ranking ties, still need research protocol decisions.

## Verification

- **507 Python tests passed** with seven existing upstream deprecation warnings. New coverage checks scalar/batched cosine consistency, JSON export, model reuse/settings changes and evaluator input completeness. [Log](../../logs/maintenance_tests.log).
- Frontend lint/build passed. [Lint](../../logs/maintenance_frontend_lint.log), [build](../../logs/maintenance_frontend_build.log).
- Browser fixture checks passed at widths 360, 390 and 960, including recording recovery, profile/settings, PPT/vocabulary, speaker edits/history, tabs, influence evidence and exports. These fixtures do not exercise real speech recognition. [Log](../../logs/maintenance_browser.log).
- The actual reorganized launcher served `/api/health` successfully using isolated validation state and reused the unchanged frontend build. That process was stopped afterward. No user's live server/data was modified. [Launcher](../../logs/maintenance_launcher.log), [health](../../logs/maintenance_live_health.json).
- Android JVM audio/input/progress/rules/analysis checks passed; no native app code was changed by this organization/performance update. Earlier emulator results are in chapter 19. No new physical-phone result is claimed. [Log](../../logs/maintenance_android_jvm.log).
- Local readiness confirmed installed speech/speaker/slide models and FFmpeg tooling. [Readiness](../../logs/maintenance_readiness.json).
- Submitted-report hash, archived file hashes and live database rows were verified. Markdown local links and Git whitespace checks are part of final organization checks.

## Remaining gaps and next evidence

| Area | Current boundary | Work needed before claiming it in a journal/product |
| --- | --- | --- |
| Historical slowdown | Added speaker/PPT work confirmed; historical stage cost absent | Compare identical audio/configuration on a quiet host using new timings; distinguish cold/warm/cached and queue time. |
| Hindi/Hinglish | Multilingual ASR and bilingual rules implemented | Natural consented code-switching recordings, human transcripts and speaker/event/decision labels; measure WER/CER/DER/F1 by language conditions. |
| Slide fusion | Python semantic/temporal or TF-IDF; Android native-text TF-IDF | Genuine paired PPT/audio/timing labels, same-data baseline/ablation evaluation. Images/plots without text are not understood. |
| Learned influence | Configured heuristic weights; CPU training/export CLI exists | Independent human labels, tie-aware ranking protocol, disjoint meeting splits, real training and held-out validation; no trained weights are deployed. |
| Novelty | Evidence/decision-linked explainable multimodal integration is implemented | Establish incremental value over prior work on identical labelled data; pretrained component use alone does not prove novelty. |
| Long meetings | Python global speaker clustering reads the entire waveform; Android speaker analysis has a one-hour limit | Bounded-memory global identity strategy, long-file tests and honest fallback for recordings beyond speaker limits. Six-hour recording support is not six-hour speaker-analysis support. |
| Android devices | JVM and previous emulator validation | ARM64 physical phones: performance, thermal/battery, interrupted I/O, codec/vendor behavior and long recordings. |
| Cloud | Workstation/HTTPS preparation and Android browser shortcut | Provision a real server, compatible GPU/runtime and domain; measure queue/network/cloud latency. Native upload/history synchronization is not implemented. |
| Release/authentication | Local accounts, ownership checks, history and loopback default | Deployment-specific registration/session/backups policies and release signing; archived/private runtime data must not be publicly served. |

These data/device/deployment gaps cannot be filled with invented outputs or untested model changes. The supplied project runs locally and preserves research traceability; [chapter 20](../research/20_TRAINING_DATA_AND_MULTIMODAL_RESEARCH.md) explains the experiments and training inputs still required.
