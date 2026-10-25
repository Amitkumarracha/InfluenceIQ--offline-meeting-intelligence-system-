# AI-annotated outcome-link pilot — 24 October 2026

The assistant completed this pilot without requesting human annotation. All new
relationship labels are explicitly **AI-generated**, not independently verified
human references. The experiment did not improve over its majority baseline.
No application model or influence-score default was replaced.

## Annotation and provenance

The assistant inspected manual AMI transcript passages surrounding all 38
original candidates, along with the corresponding human-written meeting
summaries. Six candidates were judged repairable by recovering complete source
or outcome passages; the remaining 32 were unsuitable or ambiguous. These are
single-assistant audit judgments, not measured candidate precision or recall.
Common problems were ASR fragments, jokes, acknowledgments, logistical remarks,
unrelated topics and conditional statements mistaken for final decisions.

The assistant purposively curated 53 reference-linked contribution/outcome
judgments from the surrounding discussions. Three ambiguous judgments were
excluded from fitting, leaving 50: 31 training, eight development and 11
historical evaluation pairs. The allocation uses eight/three/three complete
project series, seed 20261024, recorded before fitting. There are no new human
annotations, repeated independent annotators or inter-annotator agreement scores.

Every pair retains the manual speaker, verbatim text, timestamps, word IDs or
summary sentence IDs, rationale, inclusion flag and AI label provenance. Some
inputs are human-written meeting summaries, which are privileged outcome inputs:
this experiment does not automatically reconstruct those outcomes from audio.
Reported designs and external requirements express outcome alignment without
establishing who originated an idea. Acceptance of an objection means the
objection was addressed in the observed response; it does not prove causation.

The frozen split was not rearranged to improve class coverage. The revised class
has only two included training instances and no development/test instances.
Therefore this pilot cannot validate four-class performance. The structural
requirements of the independent-human workflow remain intact; it still rejects
these AI labels. They are handled by a separate, explicitly scoped trainer.

## Model and results

Training-only word/bigram and character TF-IDF features feed class-balanced
Logistic Regression. The paired model selects C from 0.1, 1 and 10 using
development macro F1. Source-only and outcome-only controls use C=1; a fixed
training-majority baseline is also eligible for selection. Annotation rationales,
speaker IDs, reference IDs and relationship labels never enter input features.

The development-selected primary is the paired model, C=1: six of eight labels
agree (75.00%), with four-class macro F1 37.50%. This is development agreement,
not a final accuracy claim. The frozen historical results are:

| Method | Agreement with AI labels | Four-class macro F1 |
| --- | ---: | ---: |
| Training-majority baseline | 7/11 = 63.64% | 19.44% |
| Source-only control | 7/11 = 63.64% | 19.44% |
| Outcome-only control | 4/11 = 36.36% | 13.33% |
| Paired model: selected primary | 6/11 = 54.55% | 17.65% |

No revised examples occur in the historical reference, and rare-class detection
fails. Macro F1 retains all four declared labels, assigning zero F1 where
appropriate; it must be reported with class counts. This tiny purposive cohort
supports no superiority or broad generalization claim. All project cohorts are
historical AMI material, not fresh deployment observations.

## Local deliverables

`outputs/training/outcome_ai_review_20261024/` contains:

- `AI_reviewed_pairs.csv` and `ai_labels.jsonl`: all 53 judgments, with three
  explicitly excluded; AI provenance is retained in both formats.
- `original_38_candidate_audit.csv` / `.json`: a disposition and explanation for
  every original candidate, with links to corrected curated pairs where available.
- `curation_specs.json`, `annotation_protocol.json` and
  `annotation_provenance.json`: exact reference spans, frozen split and hashes.

`outputs/training/outcome_ai_model_20261024/` contains `protocol.json`,
`development_search.json`, `selection.json`, `models.joblib` and
`ai_agreement_evaluation.json`. Sources and annotation snapshots are preserved
alongside the experiment. Local outputs remain excluded from Git; keep a copy
with the paper's research records. The previous human review CSVs are untouched.

## Paper wording and next decision

A defensible description is: “We conducted an exploratory weak-supervision
pilot using 50 included source-linked pairs annotated by a single AI assistant.
Project-disjoint evaluation measured agreement with these AI-generated labels.
The development-selected paired classifier achieved 54.55% agreement on 11
historical pairs, below the 63.64% majority baseline. Independent human validity
and causal presenter influence were not established.”

The paper can report this as an exploratory ablation and error analysis. Do not
describe it as 75%+ presenter-influence accuracy, human annotation, a validated
four-class relation system, or evidence of Q1 acceptance. No additional model
search was launched after viewing these results. Stronger claims still require
broader representative data and independent reference validation; another model
trained against the same judgments cannot supply that validation by itself.
