# Evaluation results — 19 October 2026

These are measured pilot results, not full-corpus benchmarks or deployment certification.

## Speaker calibration

Development: two 120-second AMI excerpts; held-out: two different meeting groups. Minimum pooled development DER selected threshold 0.9. Full protocol and individual results are in `evaluation/audio_protocol.json` and `evaluation/ami_*.json`.

| Meeting | Threshold | Groups | Reference speakers | DER |
|---|---|---|---|---|
| IS1001b | 0.5 | 12 | 4 | 46.01% |
| TS3007d | 0.5 | 13 | 4 | 83.54% |
| IS1001b | 0.9 | 4 | 4 | 26.90% |
| TS3007d | 0.9 | 7 | 4 | 56.01% |


The 42-minute private recording fell from 139 groups to 37 in a separate diagnostic. Its true count remains unknown. This reduces fragmentation but does not establish correct attribution. Original saved meeting data was not overwritten. Diagnostic processing took 1047.6 seconds with other evaluation workloads active; peak process RSS was 1108.2 MiB.

## Speech recognition

| Model | Corpus | Samples | WER | CER |
|---|---|---|---|---|
| small | hindi | 8 | 50.96% | 20.09% |
| small | hinglish | 8 | 66.13% | 50.00% |
| medium | hindi | 8 | 37.02% | 14.98% |
| medium | hinglish | 8 | 57.26% | 52.25% |


English AMI held-out WER: IS1001b 41.59%; TS3007d 81.00%. Distant audio, overlap, spelling and reference conventions matter. Hindi/Hinglish measurements use eight samples each. Hinglish samples are consecutive technical-lecture segments; some hypotheses include neighbouring speech, so boundary/reference mismatch requires manual audit. Keep these strict scores; do not silently fix references after seeing predictions. Medium improves this small pilot but does not deliver reliable accuracy. The small default remains a latency trade-off.

## Functional evidence

The earlier audio-pilot software regression passed 563 tests with seven dependency warnings. Focused comparative metric checks are recorded in `evaluation/comparative_metric_tests.log`; that regression log is `evaluation/final_pytest.log`. Browser tests verify synthetic microphone previews, recovery, pause/resume, uploads, search, edits, evidence and responsive layouts. Real local preview inference is recorded separately in `evaluation/live_preview_real_model.json`. Android Java tests and APK build completed; no physical-phone accuracy or thermal certification is implied. Later pipeline validation is recorded separately with the new experiment.

## Downstream evaluation

Eight ablation variants ran against the existing long meeting. Human influence rankings and event/decision/slide references are missing, so those accuracy metrics remain unavailable. The outputs under `evaluation/downstream/` include private source-derived content: review before sharing. Score differences are sensitivity analysis, not proof of improved influence accuracy.

## Limits

No speech-model training/fine-tuning was performed in this audio pilot; a separately reported linear decision-discussion classifier has now been trained on manual AMI annotations. Public dataset provenance and SHA-256 values are in the two manifests. Neither benchmark contamination nor generalisation to Indian meetings has been ruled out. Timing with concurrent evaluation jobs is not a controlled latency comparison. Full recordings, additional languages, independent human labels, physical Android tests and confidence intervals remain future validation.

## Decision-discussion continued development

The dev-selected `context_40` configuration scores 34.13% precision, 90.12% recall and 49.51% F1 on the same historical cohort as the initial 42.35% F1 pilot. This is exploratory continued development with oracle transcripts/act boundaries, not independent confirmation or app accuracy. See `DECISION_DISCUSSION_IMPROVEMENTS.md` and `evaluation/decision_discussion_v2/` for all variants, the smoothing ablation, frozen selection and provenance. Production rules are unchanged.

## Matched classifier comparison

Four classifier families were trained with both current-act and context-40 features, using the same split and development selection rule. All eight results are reported in `CLASSIFIER_COMPARISON.md` and Table 10 of the manuscript. The new development-selected pipeline, `random_forest__context_40`, scores 52.08% historical F1. This task-level exploratory study does not benchmark complete meeting assistants or establish general superiority.

## Pipeline integration

The development-selected forest/linear combination scores 53.54% historical discussion-membership F1, with 39.94% precision and 81.18% recall. It is installed locally for English discussion review and included in new report exports and the decision-review screen. See `PIPELINE_IMPROVEMENTS.md` for measured comparisons, runtime checks and limits. Actual recording/ASR-passage accuracy remains unmeasured.

## Further quality experiments and complete scorecard

The local speech default is `small` after fixed-sample evaluation. `QUALITY_IMPROVEMENTS.md` reports all recognition cohorts, the installed discussion model's accuracy/balanced accuracy/precision/recall/F1/AP and other metrics, negative NLP trials, and missing ground truth. No new NLP candidate met the release criteria; the installed forest/linear model is retained. Unrounded values and reference denominators are in `evaluation/quality_scorecard/`. These are exploratory task scores, not complete application accuracy.
