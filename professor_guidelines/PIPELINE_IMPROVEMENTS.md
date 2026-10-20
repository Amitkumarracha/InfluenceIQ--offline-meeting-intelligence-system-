# Pipeline improvement: learned discussion review

The app now includes a local learned discussion-review stage in addition to its event and final-decision rules. This closes the previous gap between the research classifiers and the running pipeline. The learned stage suggests source passages to inspect; it does not convert discussion membership into confirmed decisions or alter influence weights.

## Measured comparison

| Method | Precision % | Recall % | F1 % | AP % |
|---|---|---|---|---|
| Earlier v2 context model | 34.13 | 90.12 | 49.51 | 56.99 |
| Matched context logistic regression | 35.61 | 87.38 | 50.60 | 56.99 |
| Matched context random forest | 39.38 | 76.86 | 52.08 | 41.95 |
| New discussion-review pipeline | 39.94 | 81.18 | 53.54 | 53.40 |

All rows use the same 11,136 reference acts and 2,481 positives from the historical AMI cohort. This table measures discussion membership with oracle text and act boundaries. It is not end-to-end audio accuracy. The dev-selected mixture combines 75% forest with 25% linear scores, then smooths within ±5 acts and applies threshold 0.357740. It scores 59.79% development F1.

## All prespecified mixtures

| Method | Precision % | Recall % | F1 % | AP % |
|---|---|---|---|---|
| Linear weight 0.00 | 39.38 | 76.86 | 52.08 | 41.95 |
| Linear weight 0.25 | 39.94 | 81.18 | 53.54 | 53.40 |
| Linear weight 0.50 | 36.11 | 85.73 | 50.81 | 56.82 |
| Linear weight 0.75 | 33.72 | 92.14 | 49.37 | 57.09 |
| Linear weight 1.00 | 35.61 | 87.38 | 50.60 | 56.99 |

For every mixture, its smoothing radius and threshold are selected on development only. The components reuse train-fitted, previously dev-selected context classifiers; this is a further development iteration, not new independent model discovery. Historical scores were inspected only after this round's selection was frozen. Selection/model/source hashes are retained in `evaluation/pipeline_improvement/`.

The forest-versus-new-pipeline paired series bootstrap interval for F1 difference is -7.16 to +5.99 percentage points. Three test series and two development series remain insufficient for strong significance/generalisation claims. Average precision remains lower than the matched linear baseline. No labels or examples were removed or changed.

## What changed in the app

- `src/meeting/discussions.py` performs batched sparse feature extraction and forest/linear scoring locally. Expanded context and feature matrices are bounded to one batch. It preserves source order and never crosses meetings.
- The complete audio-to-report orchestrator runs the learned stage after final transcription/speaker attribution. The preview remains a separate draft path.
- The decision-review screen shows verbatim suggested passages, speaker labels and audio seek buttons. All suggestions remain in report JSON/Markdown/HTML; the screen displays the first 100 for long recordings.
- English-only application is explicit. Mixed detected-language recordings and missing model assets do not receive unsupported learned labels. An optional-stage failure is reported without losing the transcript or other completed analysis.
- Scores are not calibrated correctness probabilities. The classifier's targets are discussion spans, not final decisions. Source-based decision reconstruction and influence weighting therefore remain separate.

## Validation and limits

Unit coverage compares batched runtime features and smoothing against the frozen experiment, checks meeting boundaries and label independence, verifies passage IDs/text/timestamps and tests invalid input/failure behaviour. An orchestrator integration test checks that the new stage reaches JSON/Markdown/HTML exports without inventing decision events. Browser coverage verifies the learned section in the existing workflow.

Real cached ASR transcripts are exercised separately in `evaluation/pipeline_improvement/asr_smoke.json`. These checks measure execution and source traceability only. Short introductory excerpts can yield no suggestions; this is retained rather than forcing positives. The mapping from human dialogue acts to longer ASR passages changes the input distribution and has not been accuracy-validated. Independent ASR-passage/recording annotations remain necessary. Hindi/Hinglish accuracy, final-decision accuracy and human influence rankings are not established by this experiment.

## Model installation and reproduction

The model is installed locally at `models/discussion/model.joblib`, with its provenance in `models/discussion/manifest.json`. Model binaries are ignored by Git. A fresh checkout needs the training/evaluation artifacts before packaging; a checkout without the model reports `model_unavailable` and keeps the existing rule pipeline operational. `discussion_review.enabled` and `discussion_review.model` in `config/config.yaml` control this stage.

```bash
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 .venv/bin/python scripts/improve_discussion_pipeline.py
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 .venv/bin/python scripts/improve_discussion_pipeline.py --evaluate
.venv/bin/python scripts/improve_discussion_pipeline.py --install
MPLCONFIGDIR=/tmp/influenceiq-mpl .venv/bin/python scripts/report_pipeline_improvement.py
```

The installation always packages the frozen development-selected mixture, irrespective of historical ranking. Prior experiment outputs and existing meeting reports are preserved. New analyses produce the additional discussion-review field; existing meetings need reanalysis to obtain it. No dependencies, neural downloads or cloud processing were added.
