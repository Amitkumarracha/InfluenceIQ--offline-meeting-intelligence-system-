# Comparative metrics and ablation study

All numeric results below are computed from saved observations. No additional model inference or human annotations were invented. CSV and JSON companions support reproduction and later analysis.

## Metrics and availability

| Component | Metrics | Current evidence |
|---|---|---|
| Speech recognition | WER, CER; substitutions/deletions/insertions; paired error differences | Measured English AMI and Hindi/Hinglish public pilots |
| Speaker diarization | DER, missed/false-alarm/confusion components, JER | Measured on two held-out AMI excerpts |
| Speech activity | Union-of-speech precision, recall and F1 | Measured from the same diarization output; ignores identity |
| Speaker count | Absolute count error and meeting-averaged MAE | Measured on the same two excerpts |
| Slide alignment | Precision, recall, F1 | Implemented; independent reference slide IDs needed |
| Event candidates | Precision, recall, F1 by event type | Implemented; independent reference events needed |
| Decisions and lineage | Decision P/R/F1; node/edge P/R/F1 | Implemented; independent references needed |
| Influence ranking | Spearman and Kendall against human ratings | Implemented; independent ratings needed |
| Efficiency | Stage runtime, RTF, process RSS | Existing runs measured; cache/concurrency scopes must be respected |
| Functional correctness | API, browser, Python and Android checks | Functional tests, separate from model accuracy |

## Measured audio comparison

| Threshold | DER % | JER % | Speech P % | Speech R % | Speech F1 % | Speaker count MAE |
|---|---|---|---|---|---|---|
| 0.5 | 64.08 | 69.60 | 81.68 | 90.57 | 85.89 | 8.50 |
| 0.9 | 40.91 | 60.45 | 81.70 | 90.73 | 85.98 | 1.50 |

DER weights speaker-time, while JER averages reference-speaker errors; report both. Speech detection collapses identities to speech regions, so high speech F1 does not establish correct speakers. Count MAE also cannot establish correct attribution. The same 0.25-second collar and 120-second UEM are used. These are additional exploratory diagnostics; the original threshold was selected using development DER only. Definitions follow the [pyannote.metrics documentation](https://pyannote.github.io/pyannote-metrics/reference.html#diarization).

The new comparison is visualised below.

![Audio diagnostics](figures/audio_metric_comparison.png)

## Model comparison

| Corpus | Model | Ref words | S | D | I | WER % | CER % | Relative WER reduction % |
|---|---|---|---|---|---|---|---|---|
| hindi | small | 208 | 88 | 6 | 12 | 50.96 | 20.09 | 0.00 |
| hindi | medium | 208 | 72 | 2 | 3 | 37.02 | 14.98 | 27.36 |
| hinglish | small | 124 | 60 | 4 | 18 | 66.13 | 50.00 | 0.00 |
| hinglish | medium | 124 | 49 | 8 | 14 | 57.26 | 52.25 | 13.41 |

Each corpus comparison uses the same eight samples and normalisation. Do not pool Hindi and Hinglish into an overall product accuracy. Medium improves WER here but increases Hinglish CER. This is a model comparison; changing model size is not a component-removal ablation.

## Component ablation and sensitivity

| ID | Variant | Slide-grounded events | Changed scores | Mean absolute score change |
|---|---|---|---|---|
| A1 | full_system | 6 | 0 | 0.000000 |
| A2 | without_ppt | 0 | 0 | 0.000000 |
| A3 | without_temporal_alignment | 6 | 0 | 0.000000 |
| A4 | without_semantic_alignment | 0 | 0 | 0.000000 |
| A5 | without_evidence_features | 6 | 8 | 0.001484 |
| A6 | without_interaction_features | 6 | 8 | 0.000312 |
| A7 | without_decision_impact_features | 6 | 8 | 0.005935 |
| A8 | speaking_time_only_baseline | N/A | N/A | N/A |

A1 is the control. A2 removes presentation links and reruns downstream NLP. A3/A4 rerun alignment and downstream analysis after removing temporal/semantic evidence. A5–A7 remove feature weights, then renormalize the remaining weights. A8 replaces the scoring method with speaking time. Counts and score movement are descriptive. Human accuracy remains unmeasured in every row.

The chart below excludes A8 because its scoring definition differs. Mean change averages all 139 clusters, including zeros, which can make a change appear small. Consult changed-score counts and maximum change in the CSV. Fragmentation in this original report means these diagnostics must not support claims about real participants.

![Ablation sensitivity](figures/ablation_sensitivity.png)

A subsequent feature audit found that only decision contribution is active: proposed scores equal 0.15 times the decision-count baseline. A5/A6 changes are entirely weight renormalisation and preserve rankings; none of the 34 slides has recorded timing. Read `RESEARCH_VALIDITY_REVIEW.md` before interpreting these charts. A zero change is a legitimate result. It can indicate absent features or no usable temporal information, rather than successful ablation. Threshold tuning is a calibration study; A2–A7 are the component-removal study. Neither is evidence of superior influence accuracy without independent labels.

## Baseline comparison

| Method | Clusters | Nonzero scores | Human ranking accuracy |
|---|---|---|---|
| B1_speaking_time | 139 | 139 | Unmeasured |
| B2_speaking_time_turns | 139 | 139 | Unmeasured |
| B3_decision_event_count | 139 | 8 | Unmeasured |
| B5_transcript_only | 139 | 8 | Unmeasured |
| B4_decision_evidence_count | 139 | 0 | Unmeasured |
| B6_audio_ppt_no_decision | 139 | 139 | Unmeasured |
| Proposed_decision_linked | 139 | 8 | Unmeasured |

Six baseline implementations and the proposed method are available. Nonzero-score coverage describes outputs, not correctness. Baseline score scales differ, so score magnitudes are not compared as accuracy. No comparison with commercial systems or published paper scores is made unless the same audio, references and protocol are actually run.

## Reproduce

From the project root:

```
.venv/bin/python scripts/build_comparative_evaluation.py
.venv/bin/python scripts/build_research_documents.py
.venv/bin/python scripts/check_research_package.py
```

The first command re-scores saved AMI predictions and reads completed downstream variants; it does not rerun neural inference. To recompute downstream variants for an independently annotated meeting:

```
.venv/bin/python scripts/run_evaluation.py --meeting-id YOUR_MEETING_ID --annotations YOUR_ANNOTATIONS.json --ablation --output-dir outputs/evaluation/YOUR_RUN
```

Human raters must annotate before inspecting model outputs. Keep speaker/session splits and report rater agreement. Missing reference fields remain null, and graphs must not plot them as zero.
