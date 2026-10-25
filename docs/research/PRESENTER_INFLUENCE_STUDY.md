# Presenter influence on meeting outcomes

Research objective agreed on 24 October 2026: estimate whose ideas, evidence,
or objections shaped the final meeting outcomes. Meeting intelligence stages
support this objective. Discussion-detection F1 and ASR scores do not measure
presenter influence accuracy.

The saved pilot has no independent influence ratings and six inactive feature
categories. It cannot establish ranking accuracy or justify learned weights.
No new accuracy improvement is claimed by the changes described here.

The subsequent [GAP influence experiment](GAP_INFLUENCE_EXPERIMENT.md) tests 35
development candidates on real outcome-alignment labels. The frozen primary
scores 61.11% test pairwise accuracy, below the word-count baseline's 63.89%;
the higher 83.33% development score did not generalize. The app model was retained.

The [subsequent pipeline findings](INFLUENCE_PIPELINE_FINDINGS.md) record 50
additional candidate trials, learned role detection, semantic uptake experiments
and small corrections to proposal credit and evidence direction. No new
influence-accuracy improvement is established by those production fixes.

## Small implementation corrections

Decision reconstruction now retains secondary proposals and decision statements
in the discussion records. Previously only the first proposal and final decision
survived in the event IDs used for influence attribution, which could omit other
speakers' contributions. Evidence-provider roles no longer require a separately
detected proposal. These changes preserve the existing score formula, weights,
model settings, API and report schema. Existing reports remain unchanged;
new analyses use the corrected reconstruction. Preserved events still depend on
heuristic clustering; membership alone does not prove an idea was adopted.

## Prepare the annotation pilot

From the repository root, select complete saved meetings with usable recordings
and transcripts. Use a new output directory each time; preparation refuses to
overwrite an existing directory.

```bash
.venv/bin/python scripts/prepare_influence_annotations.py \
  --influence data/processed/influence/ES2005a_influence.json \
              data/processed/influence/ES2006b_influence.json \
              data/processed/influence/IS1004a_influence.json \
  --output-dir outputs/training/influence_pilot_20261024
```

These historical artifacts are an annotation-workflow pilot, not a new final
test set. They retain their original extraction outputs and coverage limits.
No saved transcript, prediction or report is rewritten by preparation.
The prepared local pilot has three meetings, 12 predicted speaker IDs and 36
blank rater records. All seven extracted features are zero in these saved files;
they cannot train useful influence weights, even after ratings are supplied.
Use them to check the annotation workflow, then prepare independently selected
full meetings with verified speakers and evaluated contribution extraction.

- `blind_ratings.csv`: blank independent worksheets for three raters, sorted by
  participant ID, without model scores or feature values.
- `training_template.jsonl`: raw features with null label, group and split
  fields. This deliberately cannot train until humans complete it.
- `diagnostics.json`: source hashes, speaker counts and active features. Accuracy
  remains null; inactive features remain zero.

Before rating, verify that speaker IDs map consistently to real participants and
that the full participant roster is included. Fragmented IDs must be resolved
using the recording, followed by recomputing features; renaming IDs is insufficient.
Do not interpret zero extracted evidence as proof of zero real influence.

Give each rater the original recording and independently checked transcript,
including final outcomes, and only their own worksheet. Keep model predictions,
feature templates and other raters' judgments hidden. Ask for a 1–5 outcome-impact
rating for every participant, supporting timestamps and a short explanation.
Allow tied ratings; leave unjudgeable participants unscored rather than assigning
zero. Record missingness and do not silently drop difficult meetings.

Credit adopted ideas, consequential evidence, objections followed by supported
changes, and contributions incorporated in the outcome. Mere speaking volume,
slide use, seniority or announcing a decision does not establish outcome impact.
Record both positive and negative effects on outcomes; influential does not mean
correct or helpful. Preserve original independent ratings and report agreement
before a documented adjudication. Do not generate reference labels from the
system's contribution features or predicted ordering.

## Train and evaluate after independent labels exist

Make a completed copy of the training template. Use a verified `group_id` for
each team/project series, consistent across its meetings. Assign whole groups to
train, validation or test before inspecting outcomes. The trainer rejects groups
that cross splits. Legacy manifests without group IDs remain supported but are
explicitly marked as having unverified group separation.
The script checks declared groups; reviewers must verify the underlying team
identities independently.

After independent review, fill `label_source` with `human` and `human_score`
with the documented consensus rating converted by `(rating - 1) / 4`. Retain
individual ratings and adjudication separately. Include every participant in
each meeting so feature normalization remains comparable. Choose a defensible
sample size after the annotation pilot; the script's four-meeting execution
minimum is not a publication sample-size recommendation.

```bash
.venv/bin/python scripts/train_influence_weights.py \
  --manifest outputs/training/completed_human_influence.jsonl \
  --output outputs/training/influence_weights_candidate.json
```

The existing trainer fits nonnegative weights to human scores. It now also
reports decision-count and equal-weight baselines, per-meeting Spearman/Kendall,
meeting-average pairwise accuracy, exact top-set accuracy and feature-deletion
ablations. Human-tied pairs are excluded from pairwise accuracy; predicted ties
receive half credit. All-human-tied meetings have unavailable ordering accuracy.
Top-set accuracy requires the entire predicted top set to match the human top
set, preventing an all-tied prediction from automatically winning. A correlation
of 0.75 is not 75% accuracy. Model weights are research artifacts and are not
automatically installed in the application.

Treat above-75% pairwise accuracy as a research target, not a promised result.
Compare against speaking-time and word-count baselines on the same verified
participant roster in the final study; the current trainer only has contribution
features and cannot compute these audio/text baselines. Report uncertainty by
independent team/project groups, not correlated participant pairs. The current
trainer reports point estimates, not confidence intervals or rater reliability.
Freeze model choices on development groups before a fresh final evaluation.

## Next model experiment

First annotate a few development decision chains and measure extraction errors
with verified transcripts/speakers. Check whether each claimed contribution
feature is present when it should be; do not force every feature to be nonzero.
If relationships are the limiting error, train a contextual relation classifier
on independently labelled proposal/evidence/objection-to-outcome connections.
Only then compare learned ranking weights against the unchanged baselines.
Repeat on actual ASR/diarization outputs and test slides through a matched
audio-only versus audio-plus-slides experiment. This establishes which stage
improves outcome-influence agreement without redesigning the application.
