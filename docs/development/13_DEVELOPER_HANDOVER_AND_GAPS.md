# New developer handover and ranked remaining work

Layout update, 8 October 2026: use the [master documentation](../README.md) and [structure/performance update](../validation/22_STRUCTURE_PERFORMANCE_AND_GAPS.md). Historical comparisons and measurements below describe their stated audit date. The older working tree is now archived; current paths and runtime are described in the update.

**18 October update:** [Current readiness work](../validation/23_READINESS_2026_10_18.md) fixes strict-final/duplicate decision behavior, semantic candidate filtering, full-transcript/tied-rank baselines, structural ablations, order-independent metric matching, the OCR stub and Android import/memory limits. Both Gradle and direct-build version metadata were updated to 0.6.1/code 7. Local generative notes were removed in the earlier scope update. The historical observations below are retained for provenance; use the new report for current remaining work and verification.

[Handbook index](../handbook/README.md)

## First day

Read [01](../research/01_PROJECT_HISTORY_AND_COMPARISON.md), [03](03_ENVIRONMENT_AND_SETUP.md), and [04](04_ARCHITECTURE_AND_PIPELINE.md). Trace `api.run_pipeline_background()` → `decode_parts()` → `run_meeting()` → `run_asr()` → events/evidence/decisions/interactions/influence → report export. Use [15](15_SOURCE_CODE_REFERENCE.md) to locate definitions.

Inspect local status before touching code:

```bash
git status --short
.venv/bin/python --version
.venv/bin/python scripts/validate_setup.py
```

Keep existing working-tree Android changes and the older snapshot. Do not reset the project to HEAD just to obtain a clean audit; current 0.4.0 Android changes are partly uncommitted.

When deliberately starting the app:

```bash
bash scripts/start_app.sh
```

Open `http://127.0.0.1:8000`, create a local account, and use a small recording you are authorized to process. Check reported language/speaker availability and inspect original audio before treating candidates as meeting facts. For a server-free run, use `scripts/process_meeting.py` with a unique ID.

## Testing guide

```bash
OMP_NUM_THREADS=4 bash scripts/check.sh -q
npm --prefix frontend run build
npm --prefix frontend run lint
bash android/test.sh
bash android/build.sh
```

Commands are instructions, not new test executions from this audit. Python tests mock neural boundaries where appropriate; actual integration and dataset results are separate. Android build needs prepared SDK/JDK/NDK tools. JVM tests run WAV/progress/rule logic, not native speech accuracy.

| Suite | Main responsibility |
| --- | --- |
| `test_audio.py` | Audio/VAD/speaker attribution and audio data contracts |
| `test_ppt.py` | Native slide extraction/embeddings interfaces |
| `test_alignment.py` | Score combination/candidates/abstention |
| `test_meeting.py` | Event/evidence/decision/interaction/influence logic |
| `test_evaluation.py` | Metric semantics, including corrected DER |
| `test_report.py` | Structured reports/export |
| `test_api.py` | Ownership/uploads/retries/exports and job behavior |
| `test_laptop_workflow.py` | Complete workflow/checkpoint/portable audio behavior |
| `test_local_notes.py` | Quote checks, chunk coverage, retrieval, local-model restrictions |
| `test_efficiency.py` | Silence, Unicode, lightweight alignment, graph serialization, optional ONNX boundary |

Browser `.cjs` checks use a separate Playwright installation under `.runtime/browser` or `MAI_PLAYWRIGHT`; it is not installed by the frontend package lock. Some historical scripts use outdated selectors and mutate accounts/meetings against a live API. Inspect them and use isolated test state. The current offline fixture check is `scripts/test_browser_offline.cjs`.

## Extension contracts

- Return existing transcript/event/decision shapes when changing models. Preserve absolute timestamps, segment IDs, UNKNOWN labels, original source text, and method metadata.
- Version changed ASR behavior/settings in the cache identity. Record actual model revisions for experiments; model name alone is insufficient after weight replacement.
- Change event rules in Python, regenerate assets with `.venv/bin/python scripts/export_event_rules.py`, then run Python and Android rule checks. Android multi-label matching and laptop highest-score matching remain different.
- Keep diarization globally consistent across chunks. Independent chunk clustering can silently reset speaker IDs.
- Implement real OCR/vision behind existing PPT interfaces only when required; current image metadata and OCR stubs are not learned vision.
- Separate evidence relevance from entailment; do not relabel a slide match as validated support without a new method/evaluation.
- Use current SQLite payload/API exports when inspecting user edits/notes, and raw stage artifacts when studying algorithm output. Record the choice.

## Debugging common issues

| Symptom | Check / meaning |
| --- | --- |
| Model missing offline | Confirm model snapshots under `models/hf`; provision explicitly while online |
| All speakers UNKNOWN | pyannote model unavailable/disabled, attribution insufficient, or Android's expected limitation |
| No influence participants | Correct withholding for UNKNOWN; verify real speaker model and extracted events |
| Delayed first transcript preview | Ingestion/preprocessing/diarization precedes ASR; preview follows completed chunks |
| Retry does not recompute every chunk | Expected matching-cache reuse; use a fresh tag/ID and recorded settings for cold benchmarks |
| Empty transcript | Inspect signal diagnostics/original audio; exact digital silence intentionally skips inference |
| Wrong detected language | Inspect allowed-language selection and model; compare explicit en/hi versus auto on labelled samples |
| Missing slides | PPT omitted, local embedding weights absent, native text absent, or relevance below threshold |
| Temporal scores are null | No display timing supplied; PPT slide order does not establish timings |
| Notes unavailable | Ollama not running or no permitted installed completion model; transcript/search remain available |
| Disk report lacks latest notes/aliases | API edits saved in SQLite; use authenticated export |
| Legacy evaluation crash on a decision | Proposal timestamp field bug; see [11](../research/11_EVALUATION_BASELINES_AND_ABLATIONS.md) |
| Android model import fails | Wrong model format, corrupt GGML, or insufficient memory; preserve original audio |
| Android pause waits | Current native chunk finishes before pause; saved completed chunks resume |
| Android version differs | Direct manifest 0.4.0 versus stale alternate Gradle 0.3.1 |

## Remaining work ordered by research impact

| Priority | Work | Why it matters |
| --- | --- | --- |
| P0 | Repair/validate evaluation runner inputs and matching; replace mislabeled ablations | Current CLI can yield incomplete/misleading or crashing scientific results |
| P0 | Freeze reproducible current/older artifacts and recover missing workstation provenance | Needed for an honest old/current comparison |
| P1 | Provision and evaluate real diarization; define stable anonymous speaker mapping | Participant influence requires reliable speakers |
| P1 | Collect independent Hindi/English/Hinglish and decision/slide/lineage labels | Current intended domain is not empirically validated |
| P1 | Implement genuine transcript-only/no-PPT/temporal/semantic reruns | Establishes what fusion actually contributes |
| P1 | Validate influence with human rubric, agreement, meaningful baselines, uncertainty | Scores are currently heuristic and noncausal |
| P2 | Improve decision topic/negation/coreference and required-final behavior | Reduces temporal-cluster and phrase-only errors |
| P2 | Evaluate local notes entailment/coverage and Q&A context truncation | Quotes alone cannot validate generated meaning |
| P2 | Isolated long-real-meeting cold/warm/recovery/resource experiments | Synthetic silence smoke test is insufficient |
| P2 | Physical ARM64 phone tests for bilingual speech, energy/thermal/lifecycle | Emulator/compiled ARM64 evidence is incomplete |
| P3 | Reconcile Android alternate build versions, historical guides/scripts, tracked `.cxx` files | Prevents new-developer confusion and bloated source archives |

## Findings that remain unresolved

`require_final_decision` fallback, evaluator speaker/status omission, decision timestamp lookup, A3/A4 labeling, B1/B2 subset bias, incomplete no-PPT baseline, fixed timing candidate prefilter, note entailment, and Q&A bounded-context coverage are documented observations. This task created documentation, not implementation fixes.

Before a future algorithm change, define one concrete failing input or labelled benchmark and validate the real caller path. Passing a standalone helper test does not prove the scientific runner reads the right artifacts.
