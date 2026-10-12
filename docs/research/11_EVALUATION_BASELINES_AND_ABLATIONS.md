# Evaluation, baselines, ablations, and publication blockers

Layout update, 8 October 2026: use the [master documentation](../README.md) and [structure/performance update](../validation/22_STRUCTURE_PERFORMANCE_AND_GAPS.md). Historical comparisons and measurements below describe their stated audit date. The older working tree is now archived; current paths and runtime are described in the update.

[Handbook index](../handbook/README.md)

## What the metric code implements

[`src/evaluation/metrics.py`](../../src/evaluation/metrics.py) offers the following primitives. Missing/empty ground truth produces an explicit unavailable result instead of a fabricated score.

| Metric | Actual implemented matching | Important limit |
| --- | --- | --- |
| WER | `(substitutions + deletions + insertions) / reference_words`; lowercased whitespace tokens | Rich normalization must be supplied by caller; WER can exceed 100% |
| DER | pyannote.metrics, optimal label mapping, configured collar (default 0.25 s), overlap included | Requires real predicted/reference speaker intervals; no real local DER result exists |
| Slide alignment | Exact segment ID and slide ID matching; PRF/accuracy | Timestamp-tolerance argument is recorded but unused |
| Events | Same event type and start within tolerance, greedy one-to-one matching | Ignores speaker, text semantics, end/duration; docstring's overlap wording is broader than actual matcher |
| Decisions | Timestamp proximity OR topic-token Jaccard >= 0.3 | Ignores status; same-time unrelated decisions can match; missing timestamps default to zero |
| Lineage | Exact node labels and `(source,relation,target)` edges | Must align annotation/system event IDs; otherwise IDs can dominate the score |
| Influence | Spearman/Kendall on ordered participant lists; missing participants placed at bottom | Sorting lists loses score ties unless a tie-aware evaluation is added |
| Efficiency | Stage timings/RTF and metadata | No automatically collected end-to-end timing/memory unless caller supplies measurements |

The corrected DER primitive is a current improvement over the old approximate label-sensitive metric. The official [pyannote.metrics documentation](https://pyannote.github.io/pyannote-metrics/) describes the upstream metric package; project behavior above was verified from local source.

## Inherited runner problems: do not publish these as clean results

[`scripts/run_evaluation.py`](../../scripts/run_evaluation.py) is byte-identical across both copies. Audit findings:

| Problem | Executable behavior | Required evaluation work |
| --- | --- | --- |
| WER hypothesis is event text | Joins `event_result.events`, omitting ordinary non-event speech | Load full `audio/<id>_transcript.json`; normalize reference/hypothesis consistently |
| DER never loads system diarization | `hyp_diarization = None`, then calls DER | Load actual diarization JSON, declare scoring region/collar/overlap policy |
| Alignment uses only event-selected passages | Predictions derive from event source IDs, not all alignment records | Evaluate full alignment artifact on independently annotated segment mapping |
| Decision timestamp assumes nonexistent field | Accesses `d.proposal['start']`, while reconstructed proposal stores ID/speaker/text | Resolve timestamp from proposal/final event index; test annotated runner end to end |
| Decisions without proposal use zero | Can generate false temporal matches | Explicitly map candidate time interval or abstain from temporal score |
| Comparison CSV overwritten per invocation | Every run writes `comparison.csv` | Use per-run directories and explicit aggregation |
| Provenance is weak | Metadata records config source name rather than full effective configuration/revisions | Save full config, model/audio/source/annotation digests, hardware and timing policy |

The new AMI and phone-recording benchmark scripts avoid event-only WER by reading the complete report transcript. Prefer them for ASR. Their scoped results still do not evaluate speakers or meeting semantics.

No evaluation source was repaired during this documentation task. These are handover blockers, not claimed fixes.

## Baselines currently present

[`baselines.py`](../../src/evaluation/baselines.py) is inherited:

| ID | Existing implementation |
| --- | --- |
| B1 | Max-normalized sum of extracted-event durations per speaker |
| B2 | Average of normalized event duration and event count |
| B3 | Decision-cluster event count |
| B4 | Count of participant evidence relations targeting decision-cluster events |
| B5 | Counts decision-linked events whose slide association is absent |
| B6 | Average of event-duration and slide-grounded-event signals without decision restriction |

B1/B2 do not currently measure all speech in this evaluation module. B5 **filters ungrounded events from an already grounded run**; it does not rerun a transcript-only system. B6 likewise uses event subsets. UNKNOWN participants may remain.

The main influence runner's separate baseline output uses the full transcript when available; that is a different caller behavior. Publication requires harmonized baseline definitions and the same participant universe and verified speaker mapping.

## Existing A1–A8 are influence-weight ablations

[`ablation.py`](../../src/evaluation/ablation.py) reuses the same events/evidence/decisions/interactions and changes feature weights. It does not rerun upstream extraction/fusion.

| ID / code label | What it actually removes |
| --- | --- |
| A1 full system | No weight removed |
| A2 without PPT | Zeroes `slide_grounding` only; evidence slide bonus and slide-derived relationships can remain |
| A3 without temporal alignment | Zeroes **revision weight**, not temporal slide alignment |
| A4 without semantic alignment | Zeroes **evidence weight**, not semantic alignment |
| A5 without evidence features | Same evidence-weight removal as A4 |
| A6 without interaction | Zeroes interaction weight only |
| A7 without decision impact | Zeroes decision, objection, and revision weights |
| A8 speaking time only | Uses event-duration baseline, not complete speaking time |

A4/A5 identical flags were confirmed with a runtime assertion. Label these as weight-sensitivity experiments if used. They cannot substantiate a temporal/semantic fusion or truly no-PPT comparison.

## Small diagnostics performed during this audit

No model was loaded. Assertions confirmed that:

- A proposal-only input yields an unresolved decision even with `require_final_decision=True`.
- A4 and A5 both disable only evidence weight.
- Event predictions with the wrong speaker still score F1=1 when type/start match.
- Unrelated decision topics/statuses still score F1=1 when timestamps match.

These checks reveal evaluator semantics and a decision-option defect. They are not dataset experiments.

## Proposed comparative evaluation protocol

1. Freeze current and older source manifests and effective settings. Rebuild isolated environments separately. The supplied old snapshot needs missing data/models/environment and may need documented compatibility repair before it can run.
2. Define participant/meeting/series splits before tuning. AMI design-series meetings share participants/topics; avoid leaking a series between tuning and test. Keep phone speakers/meetings held out. Treat noise/language/duration/channel as reported strata.
3. Independently annotate transcripts, speakers, displayed/relevant slides, events, decisions/status, tasks/owners/deadlines, evidence/lineage, and contribution rankings according to a written rubric. Measure inter-rater agreement and adjudicate disagreements.
4. Compare old/current on the **same hardware** to isolate implementation effects. A GPU-workstation-versus-CPU-laptop deployment comparison is a separate hardware/system study. Where old code fails, record the failure rather than invent a metric.
5. Use fresh meeting IDs/cache directories for cold runs; measure warm-cache/recovery separately. Record model digest/revision, beam/VAD/language/chunk/threads, input hashes, resource limits, and concurrent load. Repeat isolated runs and report variability.
6. Score complete transcripts, valid speaker mappings, annotated slide matches, event/status-aware decisions, task owner/deadline correctness, semantic relation validity, and human contribution agreement. Separate oracle-transcript/speaker experiments from end-to-end ASR error propagation.
7. Aggregate by meeting and language group, and report confidence intervals (for example, resampling independent meetings). One excerpt is not enough for statistical superiority claims.

## Actual fusion/analysis ablations to run

| Proposed experiment | Necessary intervention |
| --- | --- |
| No PPT | Rerun transcript-only events/evidence/decisions/influence; remove all slide-derived effects |
| Semantic only | Rerun alignment without timing filtering/contribution |
| Temporal only | Evaluate genuinely timed slides using only overlap |
| Timing + semantic | Rerun current scoring on same timed slides |
| TF-IDF only / timing + TF-IDF | Rerun lexical scorer on identical inputs |
| No evidence / interaction / lineage | Remove component output and rerun affected downstream stages |
| Weight sensitivities | Keep same upstream artifacts and explicitly label feature-weight changes |
| Notes with/without quote check | Compare coverage and independently adjudicated entailment, including rejected items |
| Chunk profiles | Same model/input/settings except central chunk length; record first-preview and total time |

Do not make a “semantic-only” run by setting temporal weight to zero while leaving timed candidate prefiltering active: that still uses temporal information.

## Runnable ASR commands

```bash
# Fresh tags; same model/sample, different central chunk length:
MAI_ASR_CHUNK_SECONDS=300 OMP_NUM_THREADS=4 .venv/bin/python scripts/benchmark_ami.py \
  --meeting ES2002a --start 30 --seconds 600 --channel Array1-01 --tag paper_300_run1
MAI_ASR_CHUNK_SECONDS=120 OMP_NUM_THREADS=4 .venv/bin/python scripts/benchmark_ami.py \
  --meeting ES2002a --start 30 --seconds 600 --channel Array1-01 --tag paper_120_run1

# Human phone-transcript manifest, grouped by language:
.venv/bin/python scripts/evaluate_recordings.py \
  --manifest /path/to/human_phone_manifest.jsonl \
  --output outputs/evaluation/phone_small_run1.json --model small
```

Phone manifest row shape:

```json
{"id":"heldout_room1","audio":"room1.wav","reference":"independently checked transcript","group":"hinglish","language":"auto"}
```

Manifest groups are hindi/english/hinglish; language options auto/hi/en. Aggregation is word-count-weighted WER per group. The supplied example is a schema example, not usable ground truth. The script does not compute CER, semantic quality, DER, or isolated speed. Additional desired metrics need explicit implementation/evaluation.
