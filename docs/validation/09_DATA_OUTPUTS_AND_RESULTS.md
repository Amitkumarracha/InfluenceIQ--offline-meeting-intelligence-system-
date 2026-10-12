# Data, output artifacts, and measured results

Layout update, 8 October 2026: use the [master documentation](../README.md) and [structure/performance update](../validation/22_STRUCTURE_PERFORMANCE_AND_GAPS.md). Historical comparisons and measurements below describe their stated audit date. The older working tree is now archived; current paths and runtime are described in the update.

[Handbook index](../handbook/README.md)

## Local data inventory

Counts describe the filesystem inspected on 7 October 2026, before adding this handbook. They count paths, not independent meetings/experiments; logical bytes can count symlink targets more than once.

| Location | Current files / logical bytes | Older supplied copy |
| --- | --- | --- |
| `AMI_dataset/` | 25,660 / 140,266,099,389 | Absent |
| `data/` | 3,419 / 13,153,478,556 | Absent |
| `models/` | 65 / 4,364,676,630 | 1 zero-byte placeholder; no weights |
| `outputs/` | 669 / 4,450,667 | 565 / 2,642,248 |
| `logs/` | 91 / 251,245 | Empty |

AMI is an established multimodal meeting corpus with synchronized recordings and annotations; its [official corpus description](https://groups.inf.ed.ac.uk/ami/corpus/) explains the dataset. The current project does not consume every AMI modality. The benchmark uses one array channel and manual word XML. Native slide files are staged/converted separately.

`prepare_batch_data.py` symlinks `AMI_dataset/audio/Array1-01/*/audio/*.wav` into `data/raw/audio/` and converts legacy `.ppt` to `.pptx` using LibreOffice. It has historical unchecked conversion behavior: converted-file existence must be verified. Do not run it merely to inspect the repository.

`data/annotations/` contains `.gitkeep` and two **templates**: `annotation_schema.json` and `human_influence_template.json`. Templates are not filled human labels. AMI manual word XML is real external ground truth for the scoped ASR benchmark; this does not provide ground truth for the project's custom influence definition automatically.

## Processed-stage counts

| Directory | Files found | Interpretation |
| --- | --- | --- |
| `data/processed/audio/` | 1,135 | Transcripts, decoded/preprocessed WAVs, diarization/VAD/previews/chunk artifacts, placeholders |
| `slides/` | 160 | 80 JSON, 79 NPY, 1 placeholder |
| `alignment/` | 157 | 156 JSON, 1 placeholder |
| `events/` | 183 | 182 JSON, 1 placeholder |
| `decisions/` | 183 | 182 JSON, 1 placeholder |
| `interactions/` | 183 | 182 JSON, 1 placeholder |
| `influence/` | 183 | 182 JSON, 1 placeholder |
| `transcripts/` | 1 | Placeholder; main transcripts are in `audio/` |

Counts are not evidence that all files came from the current commit or were successfully evaluated. Preserve meeting IDs, model revisions, settings, cache state, and source hashes when assigning artifacts to a research result.

## Output schema map

| Artifact | Important fields and use |
| --- | --- |
| `<id>_transcript.json` | meeting_id/language/duration/speakers/segments, recording_quality/cache_key; each segment has ID/start/end/speaker/text/model score |
| `<id>_diarization.json` | backend/cache_key/speaker clusters and timed intervals |
| `<id>_unknown_diarization.json` | Empty speaker intervals for disabled/unavailable separation |
| `<id>_preview.json` | Latest saved passages/events, completed/total seconds, review flag |
| `<id>_slides.json`, `_embeddings.npy` | Native slide content/metadata; optional embedding matrix |
| `<id>_alignment.json` | Ranked slide candidates, selected slide, individual scores, alignment_method |
| `<id>_multimodal.json` | Joined transcript/slide record consumed by events |
| `<id>_events.json`, `_evidence.json` | Source-linked candidate events and relation endpoints |
| `<id>_decisions.json`, `_decision_graph.json` | Clusters/status/roles/lineage and graph node/edge lists |
| `<id>_interactions.json`, `_interaction_graph.json` | Interaction records and participant graph |
| `<id>_influence.json`, `_baselines.json` | Ranked weighted features and separate baseline values |
| `outputs/reports/<id>_report.json` | Report sections and, for complete current runner, processing metadata/full transcript |
| `_report.md`, `_report.html`, CSVs | Human-readable pipeline artifacts; CSVs cover separate report sections |
| `outputs/evaluation/*_benchmark.json` | Scoped reference/hypothesis, WER edits, timing/RSS/config fields |
| `*_metrics.json`, `*_baselines.json`, `*_ablation.json` | Legacy evaluation outputs; inspect missing-label status and runner caveats |
| SQLite `Meeting.report_data` | Current application report, optional notes/title/speaker edits through API |

API JSON/Markdown/TXT/SRT/VTT/CSV export is based on saved SQLite data. Pipeline HTML/section CSV export is a separate path. Do not assume edited application notes are reflected in previously generated disk HTML.

## Inherited reports are preserved outputs

`outputs/reports/` contains **645 files** in the current copy and **561** in the older one. All **561 shared files are byte-identical**; there are **84 current-only** files. JSON report count is **92 current versus 80 older**, with 12 current-only reports. Those include benchmark/integration/smoke/demo artifacts; they are not necessarily 12 new independent research meetings.

All 80 older report JSONs retain the same 16 report-section keys and lack the current `processing` and full `transcript_segments` fields. The 12 current-only reports include those two additions.

`outputs/evaluation/` has eight JSON files currently and two older files. The two shared files are also identical. They literally use filenames `*_metrics.json` and `*_baselines.json`; the star is a filename character here, not proof of a completed per-meeting batch evaluation. The metrics file marks all scientific quality metrics `ground_truth_unavailable` and efficiency `error`.

Do not cite the 80 inherited reports as new current-code experiments, nor interpret artifact counts as accuracy, generalization, or successful whole-corpus evaluation.

## Recorded ASR results: all available runs

All five saved ASR runs below use **AMI ES2002a, Array1-01, seconds 30–630 (600 seconds)** and the same 1,357-word reference. They are current-project validation/profile experiments, not old-workstation-versus-current benchmarks.

| Saved artifact in `outputs/evaluation/` | Profile | WER | Elapsed s | RTF | Peak RSS field, MiB |
| --- | --- | ---: | ---: | ---: | ---: |
| [benchmark_ES2002a_30_600_benchmark.json](../../outputs/evaluation/benchmark_ES2002a_30_600_benchmark.json) | small, historical validation | 45.8364% | 174.973 | 0.2916 | 890.1 |
| [benchmark_ES2002a_30_600_medium_benchmark.json](../../outputs/evaluation/benchmark_ES2002a_30_600_medium_benchmark.json) | medium, earlier unscoped run | 66.7649% | 329.049 | 0.5484 | 3,008.0 |
| [benchmark_ES2002a_30_600_medium_language_scope_benchmark.json](../../outputs/evaluation/benchmark_ES2002a_30_600_medium_language_scope_benchmark.json) | medium, language-scoped run | 40.8254% | 357.776 | 0.5963 | 2,309.2 |
| [benchmark_ES2002a_30_600_small_efficiency_v5_300_benchmark.json](../../outputs/evaluation/benchmark_ES2002a_30_600_small_efficiency_v5_300_benchmark.json) | small, 300-second chunks | 45.8364% | 82.254 | 0.1371 | 1,516.7 |
| [benchmark_ES2002a_30_600_small_efficiency_v5_120_benchmark.json](../../outputs/evaluation/benchmark_ES2002a_30_600_small_efficiency_v5_120_benchmark.json) | small, 120-second chunks | 41.4886% | 115.043 | 0.1917 | 1,479.7 |

The RSS field is named `process_peak_rss_mb`, but Linux `ru_maxrss / 1024` gives MiB. These are process peaks, not GPU RAM or total machine memory. They may include non-ASR stages and dependencies.

120-second versus 300-second observations: **4.3478 percentage points lower WER**, approximately **2.44% lower peak RSS**, and **39.86% longer elapsed processing**. This is one English sample with some concurrent local testing and recorded cache cautions. It does not establish a general accuracy gain, isolated speed advantage, Hindi/Hinglish performance, or 70% RAM reduction.

The early medium result must remain in the experiment history. Do not select the later better result without recording its changed language scope. Historical small/medium timings came from different runs; compare them descriptively, not as a controlled model-size speed study.

The benchmark sorts manually annotated words by start time across speakers and uses NFKC/lowercase/punctuation-to-space normalization. Concurrent speech is flattened to one sequence. References and hypotheses are present in local artifacts; avoid copying private/user transcripts into public supplements.

## Recorded integration and software validation

| Evidence | Recorded result | What it establishes |
| --- | --- | --- |
| `validation-results.json`, 5 October | 461 Python tests, build/lint, 20-second emulator inference | Prior software and scoped integration evidence |
| `efficiency-results.json` / `logs/tests_efficiency_release.log`, 6 October | 494 tests passed, 7 warnings, 7.41 s | Regression behavior; not real-data accuracy |
| Real speech + two-slide TF-IDF fixture | 90 s speech, 21 segments, 16.362 s, 1,073.3 MiB, no socket attempts | Specific offline integration, no duplicate processed WAV |
| `two_hour_offline_smoke.json` | 7,290 s timeline, 17.896 s processing, 19 segments, first at 7,202.05 s, 1,008.4 MiB, no socket attempts | Absolute timestamps/recovery over 2 h silence + 90 s real speech |
| `android/DESIGN.md`, later 6 October | 0.4.0 native screens, JVM/build/emulator workflows | Later Android application behavior |

The synthetic long timeline is not two hours of conversational speech. Its fast result depends heavily on exact silence handling. Zero network attempts are evidence for those fixtures, not formal proof that every optional application dependency can never contact a network.

**Missing outcome evidence:** real DER on provisioned speakers, Hindi/Hinglish WER, independently annotated slide accuracy, event/decision/action/lineage F1, influence rank validity, LLM notes entailment/coverage, controlled old/current runtime, and physical-phone energy/thermal/accuracy results.
