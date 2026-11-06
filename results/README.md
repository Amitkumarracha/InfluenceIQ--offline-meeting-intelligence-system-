# Model and fusion results

28 graphs, each available as PNG, SVG and PDF. Open `index.html` for the gallery or `ALL_MODEL_AND_FUSION_ANALYSIS.pdf` for the complete figure collection.

Regenerate from the project root: `.venv/bin/python scripts/generate_results.py`. Existing source result files are read, not modified. No training, audio processing or new accuracy experiment is performed.

## Main conclusions

- Controlled alignment: semantic-only 83.33%, hybrid 66.67%, temporal-only 50% on 24 constructed cases. This does not establish universal superiority.
- Real untimed example: 39/1,008 links, 3.87% coverage; relevance accuracy and F1 are unavailable.
- Installed English discussion model: 53.54% F1, 39.94% precision, 81.18% recall on historical human reference acts.
- Speech pilots show mixed changes across small language/cohort samples; lower WER/CER is better.
- Speaker threshold 0.9: small held-out pooled DER 40.91%; limited excerpts and explicit protocol.
- GAP combined Ridge: 68.93% mean meeting-level pairwise agreement with an outcome-alignment proxy. Difference intervals include zero.
- The default UI contribution score is fixed-weight aggregation, distinct from research Ridge models.
- The main cross-source fusion is temporal/semantic score combination. TF-IDF concatenation and forest/logistic ensembling operate within text. Neural cross-attention/tensor/graph fusion is not implemented.

## How to use the figures

Graphs 01–06 explain the system and fusion; 07–09 discuss classification; 10–13 cover speech/speakers; 14–19 explain model weights and ranking limitations; 20–23 cover runtime, data and historical failures; 24–26 inspect trained model features; 27 adds speaker diagnostics; 28 diagrams the exact fusion rule.

## Figure index

### 01_model_pipeline: Implemented models and information flow
Conceptual dependency diagram, not measured performance. Speech and document contents are related through derived representations; no jointly trained raw-audio/image fusion network.
Sources: `config/config.yaml`, `src/pipeline/orchestrator.py`

### 02_fusion_methods_used: Which fusion methods have actually been used?
The temporal–semantic hybrid combines cues at the score level. It is not an architecture combining early and late neural fusion. Within-text concatenation/ensembling does not create extra input modalities.
Sources: `src/fusion/multimodal_representation.py`, `src/meeting/discussions.py`, `config/config.yaml`

### 03_controlled_fusion_top1: Controlled fusion diagnostic: semantic-only performs best
24 author-designed cases / six constructed slides. Expected NO_CONFIDENT_SLIDE is included in correctness. This is not independent real-meeting accuracy; no claim of universal hybrid superiority.
Sources: `outputs/evaluation/final_ca4/controlled_comparison.json`

### 04_controlled_fusion_metrics: Fusion quality and coverage measure different things
Constructed diagnostic only. Macro F1 includes the no-slide class. Hybrid coverage is 100% because it also links unrelated cases; higher coverage is not automatically better.
Sources: `outputs/evaluation/final_ca4/controlled_comparison.json`

### 05_fusion_case_heatmap: Where each alignment strategy succeeds and fails
Four cases per constructed group. Timing helps vague references but hurts offscreen/unrelated cases under the fixed 0.5/0.5 score rule and threshold 0.3.
Sources: `outputs/evaluation/final_ca4/controlled_comparison.json`

### 06_real_unlabelled_coverage: Real example: 39 / 1,008 passages linked; accuracy unknown
1008 passages / 34 slides / 0 valid timed slides. Semantic and hybrid agree because of the missing-timing fallback. Independent relevance labels are unavailable; coverage is not accuracy.
Sources: `outputs/evaluation/final_ca4/real_unlabelled_comparison.json`

### 07_discussion_model_vs_baseline: Discussion review: high recall, limited precision
11,136 oracle AMI acts, 2,481 positives, 12 meetings / 3 project series; reused historical cohort. Always-negative accuracy is high because of imbalance, but it retrieves no positives. These results do not measure final decisions or raw-audio application accuracy.
Sources: `professor_guidelines/evaluation/quality_scorecard/summary.json`

### 08_discussion_confusion_matrix: Installed discussion classifier: historical confusion counts
11,136 human reference dialogue acts: TN 5,627; FP 3,028; FN 467; TP 2,014. Reference text/boundaries differ from deployed ASR passages. Historical cohort was repeatedly inspected.
Sources: `professor_guidelines/evaluation/quality_scorecard/summary.json`

### 09_classifier_family_comparison: Saved discussion classifiers: local versus context features
Previously examined AMI reference-act cohort. Model-specific development selections differ; this is an exploratory comparison, not independent evidence of ensemble superiority. Installed blend is a separately selected configuration.
Sources: `professor_guidelines/evaluation/classifier_comparison/comparison.csv`, `professor_guidelines/evaluation/quality_scorecard/summary.json`

### 10_speech_wer: Speech models: WER across separate small cohorts
English development/historical each contain two clips; Hindi and Hinglish each contain eight samples. Missing medium historical bar means unrecorded, not zero. Cohorts are separate; no full-meeting multilingual accuracy claim.
Sources: `professor_guidelines/evaluation/quality_scorecard/summary.json`

### 11_speech_cer: Speech models: CER across separate small cohorts
English development/historical each contain two clips; Hindi and Hinglish each contain eight samples. Missing medium historical bar means unrecorded, not zero. Cohorts are separate; no full-meeting multilingual accuracy claim.
Sources: `professor_guidelines/evaluation/quality_scorecard/summary.json`

### 12_speaker_threshold_development: Speaker clustering threshold selection
Small development pilot only; threshold 0.9 was selected before the separate held-out excerpt comparison. This is not a full-corpus calibration curve.
Sources: `professor_guidelines/evaluation/audio_summary.json`

### 13_speaker_heldout_der: Diarization: two held-out excerpts and pooled errors
Two 120-second AMI excerpts; 0.25s collar, overlap included, optimal speaker mapping. Pool by reference speaker-time. Excerpt pilot only; no streaming or physical-device performance claim.
Sources: `professor_guidelines/evaluation/audio_summary.json`, `professor_guidelines/evaluation/quality_scorecard/summary.json`

### 14_discussion_ensemble_weights: Discussion classifier: 75% forest + 25% logistic
Installed model configuration, not accuracy or modality importance. Context radius 40 units; smoothing radius 5; threshold 0.35774. These combine text-classifier outputs.
Sources: `models/discussion/manifest.json`, `models/discussion/model.joblib`

### 15_contribution_feature_weights: Default contribution-score weights
Configuration values, not empirically learned feature importance. Features are max-normalized across participants, then weighted. Missing categories stay zero; the highest participant score need not be one.
Sources: `config/config.yaml`

### 16_gap_participant_rankings: GAP research ranking: outcome alignment, not causal influence
28 previously examined meetings / 84 people / 87 comparable pairs. Reference transcripts/speakers, no slides. Ridge research models are separate from the default UI score. Cross-validated exploratory point estimates.
Sources: `docs/paper_20261024/analysis/results.json`

### 17_gap_difference_intervals: Ranking differences: descriptive intervals include zero
Intervals are copied from the saved paired bootstrap, not newly estimated. Previously examined corpus and overlapping CV training sets limit interpretation; no reliable-superiority or fresh-confirmation claim.
Sources: `docs/paper_20261024/analysis/results.json`

### 18_gap_feature_coverage: Historical extraction coverage is sparse
Historical snapshot: 70 / 84 participants and 22 / 28 meetings had no contribution features. No slides were supplied. Later rule fixes were not rerun as a new GAP benchmark.
Sources: `docs/paper_20261024/analysis/results.json`

### 19_gap_feature_deletions: Fixed-score deletion diagnostic
Saved delete-one-feature results on the same historical GAP representation; not retraining or causal feature importance. Inactive features can be removed without changing predictions. No confidence intervals are available.
Sources: `docs/paper_20261024/analysis/results.json`

### 20_pipeline_stage_runtime: Stage timing: 90-second English functional recording
Warm models with uncached meeting inputs; two audio parts, two decks, four-speaker constraint. Excludes upload, queue, decode and final persistence. One laptop run; not a general latency benchmark.
Sources: `outputs/evaluation/website_regression_20261025.json`

### 21_runtime_conditions: Different runtime conditions must remain separate
Independent panels use different scales and input/cache/resource conditions. These are functional timing records, not a matched comparison of models or cloud hosts. Cached repeat is not fresh inference speed.
Sources: `outputs/evaluation/website_regression_20261025.json`, `outputs/evaluation/huggingface_backend_20261026.json`

### 22_ami_discussion_split: AMI discussion subset: meeting split and reference acts
47 selected meetings, not the entire AMI corpus. Related series stay together. Historical evaluation contains 12 meetings / three series and was repeatedly examined; act counts are not independent-meeting counts.
Sources: `professor_guidelines/evaluation/decision_discussion/dataset_counts.json`

### 23_gap_role_diagnostic: Historical event-role coverage: a known failure finding
8,009 reference utterances. The evaluated historical snapshot emitted no proposals among 537 reference-positive proposal acts. Later keyword fixes do not retroactively update this diagnostic. Roles are not contribution/outcome links.
Sources: `docs/paper_20261024/analysis/results.json`

### 24_logistic_feature_coefficients: Installed logistic component: strongest signed coefficients
Top ten negative and positive coefficients of the actual trusted installed model. Prefix identifies word/character/context feature space. Coefficients depend on correlated TF-IDF features; not causal explanations or full-ensemble probabilities.
Sources: `models/discussion/model.joblib`

### 25_forest_feature_importance: Installed random forest: top impurity-based feature importances
Actual forest component, not permutation importance or causal contribution. Correlated features and impurity-based biases limit interpretation; these importances do not measure the importance of physical input modalities.
Sources: `models/discussion/model.joblib`

### 26_discussion_feature_dimensions: Discussion input: concatenated word, character and context features
Actual feature dimensions supplied to the installed classifiers. Stored unused context variants are excluded. Feature count is not model accuracy or an extra physical modality.
Sources: `models/discussion/model.joblib`

### 27_speaker_additional_diagnostics: Speaker pilot: complementary diagnostic measures
Selected threshold 0.9; only two held-out excerpts. DER/JER and count MAE are lower-is-better; precision/recall/F1 are higher-is-better. Speech detection metrics concern speech activity, not word transcription correctness.
Sources: `professor_guidelines/evaluation/quality_scorecard/summary.json`

### 28_temporal_semantic_fusion_flow: The actual alignment fusion rule and missing-timing fallback
Configuration/implementation diagram, not measured accuracy. Pure temporal-only and semantic-only settings serve as single-cue baselines. Fixed weighted cue fusion is not learned cross-attention or a neural early-plus-late hybrid architecture.
Sources: `config/config.yaml`, `src/fusion/multimodal_representation.py`

## Interpretation limits

- Constructed fusion cases are not independent real-meeting accuracy.
- Real slide-link coverage is not accuracy; ground-truth relevance labels missing.
- Discussion results use historical human text/boundaries, not full ASR application outputs.
- GAP is previously inspected outcome-proxy research with reference speakers and no slides.
- Historical role/coverage snapshots were not rerun after later extraction fixes.
- No matched TF-IDF/MiniLM, learned cross-attention or full end-to-end multimodal accuracy result is claimed.
- No ROC/PR curves or uncertainty estimates were fabricated from summary metrics.

Top model coefficients and impurity importances are model-specific associations, not causal explanations. Configuration weights are not measured accuracy. Individual probabilities are not used to fabricate ROC or PR curves. Sources and SHA-256 fingerprints are recorded in `analysis.json`.

This report covers the current selected pipeline and its main saved comparisons, not every archived experimental variant. No recordings, account databases, credentials or full private transcripts are copied into this folder.

## Separate new early/intermediate/late prototypes

Open `fusion_architecture_experiment/index.html` for the new small constructed-case experiment. It is separate from the deployed pipeline and original temporal/semantic diagnostic. All metrics are computed from saved out-of-fold prototype predictions; no fake showcase values are used. Read its limitations before presenting.
