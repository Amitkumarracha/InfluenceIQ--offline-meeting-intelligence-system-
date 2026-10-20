# Plan for a stronger, defensible submission

## The decision

Focus the paper on **offline decision-discussion detection and evidence review**, with measured runtime and memory. Keep broad participant influence as exploratory. The current study does not support a new accurate influence model or state-of-the-art speech recognition. A stronger paper needs a precise contribution and independent evidence, not a larger set of plots.

Suggested working title: **Offline Decision-Discussion Detection and Evidence Review for Meeting Recordings**. This is a scope recommendation; the application can retain its broader functionality.

## Continued development update

The latest extension in `PIPELINE_IMPROVEMENTS.md` combines forest/linear scores at a development-selected 75:25 ratio. Historical F1 is 53.54%, precision 39.94%, recall 81.18% and AP 53.40%. The selected model is now installed locally for English discussion-review suggestions, with transcript/audio traceability in the app and exports. This does not establish recording-level accuracy or turn discussion suggestions into final decisions. Previous experiment results below remain preserved.

The preceding matched comparison in `CLASSIFIER_COMPARISON.md` trains four classifier families with current-act and context-40 features. Random forest with context was selected on development before historical evaluation and scores 52.08% historical F1, compared with 50.60% for matched context logistic regression, 50.48% for context SVM and 47.12% for context Complement Naive Bayes. All eight pipelines are reported. That study's primary model has 39.38% precision and 76.86% recall; its average precision is 41.95%, below the frozen v2 reference's 56.99%. This is a task-specific F1 result with a recall/ranking trade-off, not evidence of complete-system superiority. The original v2 model remains preserved; the separately reported later extension packages components for review.

The context/smoothing search in `DECISION_DISCUSSION_IMPROVEMENTS.md` now raises historical-cohort F1 from 42.35% to 49.51%, precision from 28.18% to 34.13%, and recall from 85.17% to 90.12% for the configuration frozen on development. False positives fall from 5,384 to 4,315. A separately dev-selected precision operating point scores 51.69% F1 with 37.47% precision and 83.31% recall. The no-smoothing ablation scores 50.04% F1, so smoothing does not help the primary model on this historical cohort. All variants and negative results are preserved.

This is continued development on the previously examined cohort, not a new confirmatory test. Oracle reference transcripts/act boundaries and the lack of an independent final cohort still limit the claim. The original pilot below is preserved; production decision rules are unchanged.

## Initial supervised pilot (preserved)

Independent manual decision-span annotations were found for 47 AMI meetings. A research-only, non-generative linear NLP experiment was run using 29 training meetings, six development meetings and 12 test meetings separated by project series. Current-act words, character n-grams and neighbouring context were compared. The test cohort has only three independent series, not 12 independent participant groups. No model was installed into the application at that initial stage.

The outcome is **discussion membership**, using human transcript/act boundaries. It is not final-decision extraction or influence ranking. That distinction must remain explicit.

| Method | Test precision | Test recall | Test F1 |
|---|---|---|---|
| Always positive | 22.28% | 100.00% | 36.44% |
| Word TF-IDF | 23.69% | 93.87% | 37.83% |
| Word + character TF-IDF | 24.28% | 91.29% | 38.36% |
| Word + character + context | 28.18% | 85.17% | 42.35% |

Context adds 4.52 F1 percentage points over word-only, but false positives remain too frequent. Beating the application's explicit-decision rule on this broader task is not enough: the stronger lexical baselines are the relevant comparison. These results are a useful starting point, not a promised publication-quality outcome.

See `DECISION_DISCUSSION_EXPERIMENT.md`, its protocol, per-meeting scores and confusion matrices. Small supervised NLP training is useful here; speech-model fine-tuning and a generative LLM are not required for this experiment.

## 1. Fix the evaluation foundation

- Keep the old audio pilot and coverage audit as exploratory evidence. Pin a published AMI word-derived RTTM/UEM recipe and development/test split for new audio claims.
- Audit the TS3007d prefix before interpreting its scores. Do not trim it simply to improve numbers.
- Use a larger, independent Hindi/Hinglish cohort, with frozen script/normalisation conventions. Keep strict WER/CER; any variant-aware score needs independently defined rules.
- Retain source hashes, exact configuration, split membership, raw predictions and errors. Do not select the best test result across repeated model changes.

Deliverable: a reproducible benchmark protocol with unambiguous task and primary metric.

## 2. Improve the actual NLP failure

The new classifier's main error is false positives. Review false positives and false negatives on **training/development only**. Separate actual decision discussion from agenda statements, hypothetical suggestions, routine backchannels and unrelated technical explanation. Review whether outside-span negatives are fully annotated.

Candidate improvements are a local utterance classifier plus discussion continuity, context features, precision-oriented threshold selection on development, and explicit handling of negation/conditional or reported decisions. A conventional linear classifier or small discriminative model remains fully offline and non-generative. Do not assume these changes improve results until measured.

The current test results have now been examined. Further work on this same split must be labelled continued development; reserve fresh independent meetings/annotations for final confirmation. Do not re-label test examples or silently choose a new easier cohort.

Deliverable: higher task precision/F1 on a justified independent final test, compared with always-positive, lexical and current-rule baselines. No numerical improvement is guaranteed.

## 3. Separate transcript NLP from end-to-end audio

Run three conditions using the same reference outcomes:

1. Human transcript and verified speakers: isolates NLP quality.
2. Recognised transcript with verified speakers: estimates ASR error propagation.
3. Recognised transcript and automatic speakers: measures complete-system degradation.

Oracle dialogue-act boundaries in the new pilot must be replaced or independently evaluated before claiming recording-level performance. Report human-transcript results as an upper-bound input condition, not app accuracy.

Deliverable: a table explaining where errors enter the system. This is more informative than many overlapping audio charts.

## 4. Use informative ablations

For discussion detection: word-only, character-only, word+character, and word+character+context, each retrained on the same training data and selected only on development. These components are active, and outcomes have independent labels.

For the broader project: include PPT only after collecting real slide timestamps and reference links. Compare outcomes with/without presentation evidence on examples that actually require it. Evaluate evidence and decision accuracy directly. Include negative results.

For influence: the old example reduces exactly to decision-event counting. Do not claim a richer model until labelled examples activate the additional features and independent human rankings establish benefit. Avoid normalised score movement as a substitute for ranking accuracy.

Deliverable: one main ablation table tied to a reference outcome. Move algebraic/no-signal diagnostics to a supplement.

## 5. Measure the engineering contribution properly

Measure on the same laptop with competing inference jobs stopped: cold and warm model loading, ASR runtime, diarization runtime, total pipeline runtime, RTF and peak RSS. Compare full re-decoding versus reuse of saved word observations for the same speaker correction. State precisely which stages are included.

If memory/latency improve without degrading text, this supports a systems result even when recognition is inherited from pretrained models. Do not apply an ASR cache speedup to the whole pipeline or claim Android results from laptop timings. Phone heat/battery/long-recording recovery require physical tests.

Deliverable: one controlled efficiency chart and one quality/efficiency trade-off table.

## 6. Rewrite around the evidence

- Introduction: one concrete problem, one research question and a bounded contribution.
- Methods: explain data, split, labels, model, context, evidence trace and local execution. Match equations to the implemented features.
- Results: primary decision-discussion comparison, one genuine ablation, end-to-end error propagation, controlled efficiency. Include uncertainty at the independent project/session level.
- Discussion: identify actual limits and failed hypotheses. Do not make broad influence, Hindi/Hinglish or on-device accuracy claims from the English oracle-input experiment.
- Related work: compare full meeting systems separately from ASR/diarization components and datasets.
- Supplement: preserve old exploratory numbers, reference-coverage sensitivity and per-sample diagnostics.

The paper should contain fewer, more informative figures. All author details and submission declarations need human review. A deadline does not establish the missing evidence; if those studies cannot be finished, narrow the submission's claims and choose an appropriate venue with the professor.

## Immediate deliverables already available

- `evaluation/decision_discussion/protocol.json`: fixed task, group split and model-selection rule.
- `evaluation/decision_discussion/summary.json`: results, per-meeting confusion counts and source hashes.
- `evaluation/decision_discussion/comparison.csv`: baseline/model comparison.
- `DECISION_DISCUSSION_EXPERIMENT.md`: methods, results and limitations.
- `RESEARCH_VALIDITY_REVIEW.md`: reasons the previous paper was weak.

No new speech-model download or cloud processing was needed. The main remaining dependency is valid independent evaluation data and targeted improvement, rather than additional installations.
