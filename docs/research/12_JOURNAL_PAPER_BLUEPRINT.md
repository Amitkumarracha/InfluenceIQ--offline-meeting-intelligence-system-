# Journal paper blueprint and comparison material

Layout update, 8 October 2026: use the [master documentation](../README.md) and [structure/performance update](../validation/22_STRUCTURE_PERFORMANCE_AND_GAPS.md). Historical comparisons and measurements below describe their stated audit date. The older working tree is now archived; current paths and runtime are described in the update.

[Handbook index](../handbook/README.md)

## Current writing status

There is enough verified implementation detail to draft introduction, architecture, methods, implementation, and limitations. Existing empirical evidence supports a **preliminary English ASR profile observation** and software/offline integration checks. It does not yet support a full journal claim of better multimodal decision/influence quality or bilingual deployment accuracy.

Choose the paper's main research question from [10](10_RESEARCH_NOVELTY_AND_RELATED_WORK.md), complete its matched experiments in [11](11_EVALUATION_BASELINES_AND_ABLATIONS.md), and then finalize the abstract/conclusions.

Possible working title: **“A Local Meeting-Intelligence Pipeline with Transcript–Slide Grounding, Decision Lineage, and Recoverable Inference.”** If the study focuses on bilingual phone deployment instead, use a narrower title and do not imply Android has the laptop research features.

## Suggested manuscript sections

| Section | Material available | Evidence still needed |
| --- | --- | --- |
| Abstract | System, intended task, limited scope | Main completed experiment and defensible conclusion |
| Introduction | Need for reviewable local meeting artifacts and traceable candidates | Clearly bounded research question |
| Related work | Pretrained speech, sentence similarity, meeting decision detection, document linking, query summarization | Expanded recent/full-paper review and precise gap |
| Problem formulation | Inputs: audio, optional slide text/timing; outputs: events/lineage/contribution estimates | Human-label definitions, no-slide and unknown-speaker rules |
| Method | Exact fusion equations, event/evidence rules, anchor clusters, influence feature formula | Tuned thresholds/weights if claiming effectiveness |
| Implementation | Environment, decoder/ASR caches, one-worker API, optional notes and native mobile subset | Reproducible release/model hashes |
| Experimental design | AMI excerpt extraction and phone-manifest evaluator | Held-out multi-meeting data/annotations, correct scientific runner |
| Results | Existing preliminary WER and integration table | Main task results, matched baselines, variance/statistical analysis |
| Ablation/error analysis | Audit identifies necessary component removals | Genuine reruns, measured failure categories |
| Limitations | Missing diarization/labels, rule context limits, phone parity, model/corpus scope | Update after completed experiments |
| Reproducibility/data availability | Source/config/model/evidence manifests | Curated shareable artifacts and dataset citation |
| Conclusion | Architecture summary | Conclusions tied to measured research question |

## Draft method paragraph

> Audio is converted to 16 kHz mono PCM and transcribed locally with a pretrained multilingual Whisper runtime. Optional diarization provides anonymous speaker clusters; unavailable attribution remains explicitly unknown. Native slide text, tables, and notes are represented using sentence embeddings, or an optional sparse TF-IDF index. Transcript–slide relevance is combined with available display-time overlap using fixed normalized weights and threshold-based abstention. Source-linked phrase candidates are connected through temporal/type rules, reconstructed into decision clusters and lineage, and used to compute interpretable weighted participant contribution estimates. Completed transcription chunks are cached using audio/settings identity to support recovery.

This describes implemented behavior. Add named models, settings, exact cache semantics, and formulas from [05](../development/05_AUDIO_IMPLEMENTATION.md)–[07](../development/07_EVENTS_DECISIONS_INTERACTIONS_INFLUENCE.md). Describe optional local LLM notes in a separate subsection. The base pipeline is deterministic given model outputs/settings, but that does not mean its upstream transcription or heuristic interpretation is error-free.

## Comparison table: implementation, ready to adapt

| Capability | Supplied older MAI | Current laptop MAI | Current Android |
| --- | --- | --- | --- |
| Complete shared orchestrator | Empty | Implemented | Independent native workflow |
| ASR configured profile | base / CPU int8; historical CUDA attempts | small / CPU int8 / 120 s | GGML base / whisper.cpp / 120 s |
| Content-validated chunk recovery | No | Yes | Yes, audio/model-byte identity |
| Default transcript–slide fusion | Embedding + optional temporal | Same inherited method | Absent |
| Optional TF-IDF slide matching | Absent | Implemented | Absent |
| Event rules | English | English/Hindi/Hinglish | Shared banks, different selection rule |
| Decision lineage / weighted influence | Implemented | Inherited with reporting/UNKNOWN fixes | Absent |
| Local source-quoted notes/Q&A | Absent | Optional | Absent |
| Accurate new-vs-old outcome comparison | No saved paired benchmark | Not yet performed | Not comparable feature-for-feature |

This is a code capability comparison, not an accuracy table. Cite old/current source hashes and include partly uncommitted current Android code in the release manifest.

## Results table templates: leave unmeasured cells explicit

### Paired system evaluation

| System/profile | Test meetings | WER % | DER % | Slide accuracy / coverage | Event F1 | Decision/status F1 | Lineage edge F1 | Human-rank correlation | RTF / peak RSS |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | --- |
| Older MAI, reproducible matched setup | Not run | Not measured | Not measured | Not measured | Not measured | Not measured | Not measured | Not measured | Not measured |
| Current laptop, same inputs/hardware | Not run | Not measured | Not measured | Not measured | Not measured | Not measured | Not measured | Not measured | Not measured |
| Transcript-only baseline | Not run | Not measured | Not measured | N/A | Not measured | Not measured | Not measured | Not measured | Not measured |
| Genuine no-PPT rerun | Not run | Not measured | Not measured | N/A | Not measured | Not measured | Not measured | Not measured | Not measured |

### Preliminary chunk observation already recorded

| small/int8 central chunk | Sample | WER % | End-to-end processing s | Peak process RSS MiB |
| --- | --- | ---: | ---: | ---: |
| 300 s | ES2002a Array1-01, 30–630 s | 45.8364 | 82.254 | 1,516.7 |
| 120 s | Same excerpt | 41.4886 | 115.043 | 1,479.7 |

Label this as preliminary, one English excerpt, concurrent-load/cache caveats, diarization disabled. The observation is a 4.3478 percentage-point WER reduction and longer processing. It is not a GPU-to-laptop gain. Present the earlier medium failure/configuration result in the experiment history in [09](../validation/09_DATA_OUTPUTS_AND_RESULTS.md).

### Phone study to complete

| Device/RAM/OS/model | Language | Noise/distance/overlap | WER/CER | RTF | Peak RAM | Energy/thermal | Recovery |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Physical device, details pending | Hindi/English/Hinglish separately | Defined test strata | Not measured | Not measured | Not measured | Not measured | Not measured |

Emulator smoke tests do not fill physical-device performance cells.

## Figures and artifacts

Use [04](../development/04_ARCHITECTURE_AND_PIPELINE.md)'s pipeline diagram as a draft architecture figure. Make a second figure showing a **human-checked** transcript/slide/event/decision lineage example with source timestamps and explicit uncertain links. A third can compare full-transcript speaking time with contribution estimates only after speakers/rankings are validated.

Plot resource/recognition tradeoffs across multiple repeated matched runs, not just two observations. Plot language-group results and recovery cost separately. Current [Android screenshots](../android/DESIGN.md) demonstrate UI; their generated transcript fixtures must be labelled if used.

Supplement should include effective configs, first-party source hashes, model revisions/digests, machine profile, scripts, annotations/rubric, raw metric tables, normalization/overlap policy, and cold/warm/recovery definitions. Reference external corpora rather than implying authorship. Do not package local credentials, private databases, recordings without appropriate sharing authorization, or debug signing keys.

## Final submission readiness

- Correct and integration-test evaluation wiring before collecting paper numbers.
- Complete task-relevant held-out annotations and publish the annotation protocol.
- Run meaningful baselines and actual upstream fusion ablations.
- Report failed/configuration-sensitive runs and all predeclared result groups.
- Separate source provenance from semantic validity and contribution estimates from causality.
- Supply uncertainty and per-meeting results; avoid turning WER into a universal “accuracy” percentage.
- Verify figures/screenshots represent measured data or clearly identified illustrations.
- Tie abstract/conclusion claims to completed experiments, not the application feature list.

This file is a manuscript plan, not a finished journal article or a claim of acceptance/readiness.
