# Influence model and pipeline findings — 24 October 2026

The main target remains each participant's effect on meeting outcomes. This
round tested 50 prespecified development candidates after the original GAP test
cohort had already been examined. All historical evaluations are exploratory;
none establishes a fresh independent improvement in deployment accuracy.

## Production corrections

The production diff stays in the existing decision/influence code:

- Every observed proposal in a reconstructed cluster contributes to its actual
  speaker's proposal feature and proposer role, including secondary proposals.
  Previously only the first proposal received these attributions.
- A confirmed cluster no longer gives its first proposer an extra adoption
  bonus. A final decision can reject that proposal; cluster membership is not
  evidence of adoption. Base decision-linked proposal credit remains.
- Evidence lineage now says `evidence supports proposal`, preserving source
  and target. Previously the same endpoints were labelled `supported_by`, which
  expressed the reverse meaning.

These are semantic correctness fixes with regression tests, not measured
percentage improvements. Existing saved reports are preserved. New analysis
uses the corrected feature definitions; older candidate weights/feature files
must not be assumed to have been trained with these definitions.

## Tested model and feature changes

All experiments used the existing local CPU dependencies and cached
all-MiniLM-L6-v2 encoder. No large model was downloaded and no model was installed.
The same 16 training groups, six development groups and six historical groups
were retained from the [initial experiment](GAP_INFLUENCE_EXPERIMENT.md).

1. Lower the keyword confidence cutoff from 0.3 to 0.25. This admits common
   one-pattern proposals whose current heuristic score is 0.2727.
2. Add meeting-bounded semantic novelty, later reuse, proposal uptake,
   acknowledgments and distinct-adopter features, with a fixed 90-second window.
   These are observed textual relationships, not causal links.
3. Add centered speaker embeddings to represent what each participant said.
4. Train four contextual role classifiers on GAP's independent Proposal,
   Agreement, Disagreement and Confirmation annotations. Every training group's
   predicted role features are produced by a detector trained on other groups
   through four-fold group cross-fitting. Development/historical predictions
   use the detector fitted only to training groups. Influence AII labels do not
   enter the role detector.
5. Compare ridge regression, pairwise logistic ranking, Extra Trees and a fixed
   rank ensemble across the five feature sets. There are 45 learned trials and
   five simple baselines. Selection uses development meeting-average pairwise
   accuracy; historical results never substitute for that selection.

The cutoff change alone does not solve event extraction. On development data,
proposal F1 is 0 at the existing cutoff and 1.49% at 0.25, with 7.69% precision.
The fixed lower-cutoff candidate therefore was not applied to the app default.

The contextual detector's development proposal precision/recall/F1 are
28.17% / 82.64% / 42.02%. Agreement F1 is 31.78%, disagreement F1 is 5.43% and
confirmation F1 is 26.53%. These are separate event-role metrics, not presenter
influence accuracy. The proposal improvement did not make the downstream
influence ranker better than word count.

## Influence results

For each feature family, this table shows the variant chosen on development,
then its unchanged historical score. These experiments preceded the production
corrections above; they do not evaluate the corrected app.

| Feature family | Development pairwise accuracy | Historical pairwise accuracy |
| --- | ---: | ---: |
| Word-count baseline: selected primary | 82.78% | 63.89% |
| Lower keyword threshold | 80.00% | 52.78% |
| Semantic uptake summaries | 74.44% | 30.56% |
| Semantic summaries plus speaker embeddings | 65.00% | 50.00% |
| Learned-role summaries | 74.44% | 36.11% |
| Learned-role summaries plus speaker embeddings | 62.78% | 41.67% |

The original experiment's development-selected structure model remains a
separate result: 83.33% development and 61.11% historical pairwise accuracy. The
new alternatives do not justify replacing it or presenting a new high score.
All cohorts are too small for a strong generalization claim.

A separate training/development diagnostic supplied the manual role annotations
as privileged features. Its best tested development accuracy was 80.00%, still
below word count. This is not a mathematical upper bound: it shows that perfect
role tags alone did not rescue these particular aggregate-feature rankers. It
must never be reported as an automatic system result.

## Changes with the strongest remaining rationale

The main representation still counts participation in a cluster. It does not
reliably determine which alternative was adopted, which evidence changed the
choice, or which objection resulted in a substantive revision. More generic
sentence features and role counts did not resolve that gap in this study.

The next model should predict source-linked relationships from each proposal,
evidence passage or objection to an actual outcome: adopted, rejected, revised,
or unresolved. Learn presenter rankings from those relationships, with shared
credit, rather than assuming every event near a confirmed decision affected
it. That experiment needs independent outcome-link annotations; proximity-based
links can provide weak training supervision but cannot validate the method.

Evaluate the relationship model first with checked transcripts/speakers, then
with ASR/diarization. Train ranking parameters on complete independent groups,
compare word-count/speaking-time/decision-count baselines, and reserve fresh
groups for final confirmation. Preserve ties and report group-level uncertainty.
A larger speech model or different influence weights should be adopted only
when a matched influence evaluation demonstrates a benefit.

## Preserved artifacts

The experiment is retained locally under
`outputs/training/gap_influence_semantic_20261024/`:

- `protocol.json`, `development_search.json` and `selection.json` pin all trials
  and the development-selected primary.
- `role_diagnostics.json` contains role metrics and all detector cross-fitting
  group assignments.
- `historical_results.json` contains every frozen finalist's per-meeting result
  and prediction; `oracle_role_diagnostic.json` is explicitly privileged input.
- `frozen_models.joblib`, `role_model.joblib`, `features.npz` and
  `feature_rows.json` preserve candidate models and inputs.
- `source_snapshot/` preserves the exact experimental script, helper modules,
  tests and relevant production sources before the corrections above. Failed
  experimental modules were removed from the active app tree. To reproduce,
  restore these snapshots into an isolated checkout, retaining the pinned GAP
  JSON and cached semantic vectors; do not replace current app files.

The initial GAP experiment also has a matching `source_snapshot/`. Both sets of
sources were checked against their frozen SHA-256 manifests before archiving.
Research outputs and downloaded datasets remain excluded from Git.
