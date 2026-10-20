# Quality improvements and complete metric scorecard

The local speech default is **small**. The discussion stage retains the installed 75% random-forest / 25% logistic-regression model. This round tested stronger recognition and four NLP improvement paths; failed candidates are preserved rather than reported as gains. These experiments train small discussion classifiers; none fine-tunes Whisper or the frozen sentence encoder.

## Discussion membership: all measured metrics

| Metric | Installed forest/linear | Always negative |
| --- | --- | --- |
| Accuracy | 68.62% | 77.72% |
| Balanced accuracy | 73.10% | 50.00% |
| Precision | 39.94% | 0.00% |
| Recall | 81.18% | 0.00% |
| F1 | 53.54% | 0.00% |
| Specificity | 65.01% | 100.00% |
| Macro F1 | 64.92% | 43.73% |
| Average precision | 53.40% | 22.28% |
| ROC AUC | 80.03% | 50.00% |
| MCC | 0.3861 | 0.0000 |
| Brier score | 0.1625 | 0.2228 |

All rows use the same 11,136 reference dialogue acts, including 2,481 positives and 8,655 negatives, from 12 AMI meetings in three project series. Inputs are human transcripts and dialogue-act boundaries. The installed threshold is 0.357740 with ±5-act smoothing. Its confusion matrix is TN=5,627, FP=3,028, FN=467, TP=2,014. Higher is better except Brier (lower). Scores are uncalibrated; Brier is descriptive, not evidence of correctness probabilities.

Always-negative accuracy exceeds the useful detector's accuracy because 77.72% of acts are negative; its positive F1 and recall are zero. Accuracy alone therefore cannot identify a useful discussion detector. These are task metrics, not whole-project accuracy. Actual ASR-passage accuracy, final-decision accuracy and human influence accuracy remain unmeasured.

## This round's NLP experiments

| Fixed trial | Development outcome | Historical F1 | Historical AP | Installation |
| --- | --- | --- | --- | --- |
| Frozen sentence embeddings + classifiers | No five-metric non-regression winner | Baseline retained | Baseline retained | No change |
| Time-aware forward/backward smoothing | No five-metric non-regression winner | Baseline retained | Baseline retained | No change |
| Calibrated forest/NB combination | F1 60.75% | 52.93% | 45.91% | Rejected: historical regression |
| Fixed train+development refit | No independent dev score after refit | 53.72% | 48.70% | Rejected: historical AP regression |

The semantic study used the local frozen MiniLM encoder, context radii 5/15/40, optional timing features, logistic and gradient-boosted classifiers, and mixtures with the baseline. The continuity study estimated transitions on training labels and used elapsed-time forward/backward scores. Development selection required non-regression on precision, recall, F1, accuracy and AP. Neither study produced an eligible replacement. Full prespecified alternatives remain in the saved artifacts.

The calibrated trial used ComplementNB with project-group-separated calibration folds, blended with the forest. Shared vocabulary fitting on the complete training set is disclosed in its protocol. Development improvements did not transfer to the historical cohort. The final refit used 35 train+development meetings (24,078 acts), keeping vocabulary, model settings, mixture, smoothing and threshold fixed; historical meetings were excluded from fitting. Its higher recall/F1 came with lower precision, accuracy and AP. Training size differs from prior 29-meeting comparisons, so it is not a matched-data algorithm comparison. Both failed the fixed historical release gate; no historical-best substitution was made.

## Speech recognition comparison

| Cohort | Speech model | WER ↓ (edits/words) | CER ↓ (edits/characters) |
| --- | --- | --- | --- |
| English development (2 clips) | small | 29.98% (164/547) | 20.32% (437/2151) |
| English development (2 clips) | medium | 31.44% (172/547) | 21.80% (469/2151) |
| English historical (2 clips) | small | 61.61% (268/435) | 46.97% (774/1648) |
| Hindi (8 samples) | small | 50.96% (106/208) | 20.09% (173/861) |
| Hindi (8 samples) | medium | 37.02% (77/208) | 14.98% (129/861) |
| Hinglish (8 samples) | small | 66.13% (82/124) | 50.00% (267/534) |
| Hinglish (8 samples) | medium | 57.26% (71/124) | 52.25% (279/534) |
| English development (2 clips) | large-v3-turbo | 28.15% (154/547) | 19.76% (425/2151) |
| English historical (2 clips) | large-v3-turbo | 63.91% (278/435) | 53.52% (882/1648) |
| Hindi (8 samples) | large-v3-turbo | 28.85% (60/208) | 9.41% (81/861) |
| Hinglish (8 samples) | large-v3-turbo | 57.26% (71/124) | 48.31% (258/534) |

The shared-default eligibility gate requires no regression in both English-development WER/CER and both Hindi/Hinglish WER/CER versus small. Turbo passes this development/pilot gate: **True**. The installed default is **small**. Historical English WER regressed; retain small as the shared default and expose turbo as an optional model. Historical English WER changes from 61.61% to 63.91%. This regression is retained and prevents a universal upgrade claim. No alternative configuration was selected from historical results. Medium did not improve English development. All models used local CPU int8 inference, automatic language selection constrained by the existing English/Hindi configuration, the same beam setting, and unchanged reference normalization/boundaries. Historical-small CER is calculated from its saved unchanged transcript/reference, without rerunning recognition. No reference hints, reference edits or sample removals were used. Historical English scores remain exploratory; the TS3007d uncovered reference prefix stays included. The two English development excerpts and eight examples per Indic corpus are small, correlated pilots, not a full benchmark. Wall times include initialization/concurrent work and do not support a speed claim. Larger cached models require more memory/storage; physical-phone performance is unmeasured.

Turbo weights are pinned by revision and SHA-256 in `evaluation/turbo_quality/protocol.json`. Sources: [OpenAI model card](https://huggingface.co/openai/whisper-large-v3-turbo), [converted model card](https://huggingface.co/dropbox-dash/faster-whisper-large-v3-turbo). Existing reports retain their original outputs; reanalyse a recording to use a changed default. `MAI_ASR_MODEL` and per-recording choices override the default. Provisioning on another machine uses `scripts/download_models.py --asr-model large-v3-turbo`.

## Other project metrics and missing ground truth

The earlier custom two-excerpt audio pilot, unchanged in this round, has DER 40.91%, JER 60.45%, speech precision 81.70%, recall 90.73%, F1 85.98% and speaker-count MAE 1.50. These are separate tasks with different denominators; they cannot be averaged into an overall accuracy. Reference-coverage and overlap limits in the original evaluation still apply.

No independent labels currently establish event-type accuracy, final-decision accuracy, slide-link accuracy or influence-ranking accuracy. A fresh meeting-level test with independent annotations is required before claiming general superiority or complete application accuracy. Repeated development and historical inspection mean the current results are exploratory.

## Artifacts and reproduction

`evaluation/quality_scorecard/summary.json` and `metrics.csv` contain unrounded values and denominators; `sources.json` pins source summaries. Individual protocols, selections, all alternatives and raw transcripts are under `evaluation/{semantic_quality,sequence_quality,ensemble_quality,refit_quality,asr_quality,turbo_quality}/`. Research model/cache artifacts remain under `.runtime/`; the installed discussion model remains `models/discussion/model.joblib` with its existing provenance manifest.

```bash
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 .venv/bin/python scripts/evaluate_turbo_quality.py
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 .venv/bin/python scripts/report_quality_improvements.py
MPLCONFIGDIR=/tmp/influenceiq-mpl .venv/bin/python scripts/build_research_documents.py
```
