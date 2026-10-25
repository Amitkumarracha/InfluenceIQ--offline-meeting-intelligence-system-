# Contextual influence experiments — 24 October 2026

Later follow-up: the [AI-annotated pilot](AI_OUTCOME_PILOT.md) completes a
separate assistant-labelled experiment. It does not supply the independent
human outcome references discussed below, and it does not replace app models.

The target is whose proposals, evidence and objections shaped the outcome.
Discussion detection, contribution roles, speaker attribution and participant
ranking have separate labels and metrics. None of their percentages establishes
end-to-end presenter-influence accuracy. There is no universal Q1 accuracy cutoff.

This round adds optional research paths and preserves application defaults.
Candidates live under `outputs/training/`, not `models/`. These historical test
cohorts were already examined: subsequent comparisons are exploratory. Reserve
fresh independent groups for a final publication claim.

## Model experiments

The installed discussion model combines 25% Logistic Regression and 75% Random
Forest. Historical AMI accuracy is 68.62%, positive F1 53.54%, recall 81.18% and
average precision 53.40%. Always predicting negative gives 77.72% accuracy and
zero positive F1 on these same acts. Accuracy alone rewards missing every
decision-discussion passage.

`scripts/train_contextual_model.py` fine-tunes all layers of the cached English
[all-MiniLM-L6-v2 encoder](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
and a new classification head. Each original passage has two neighboring turns
on either side, bounded by meeting. This offline analysis uses later context.
Inputs are truncated at 96 tokens. It is a compact CPU experiment, not a claim
that this encoder is the strongest available model.

- Discussion: 20,339 training and 3,739 development acts; compare neural
  predictions and fixed blends with the installed ensemble. Select checkpoint,
  threshold, smoothing radius and blend using development F1 only.
- Contribution roles: independently supplied GAP Proposal, Agreement,
  Disagreement and Confirmation labels; original group split. A separate
  development calibration searches exact precision/recall thresholds, including
  scores below 0.1. It preserves the coarse selection and model weights.
  Checkpoint selection itself still uses the original coarse grid.
- Outcome links: adopted/rejected/revised/unresolved passage pairs. Training
  requires independently checked human labels and group-disjoint splits.
  **No model is trained**, because these independent labels are unavailable.

Protocols preserve seed, source/input hashes and group IDs. Training and
historical evaluation are separate commands. Exact source snapshots accompany
the candidates; models never overwrite the installed application model.

The discussion run completed both epochs. Epoch 1 neural development F1 was
53.10%; epoch 2 was 52.74%, versus the existing ensemble's 59.79%. Every
development-selected blend assigns zero neural weight. The retained epoch-1
checkpoint's historical neural F1 is 46.32%, below the ensemble's 53.54%.
Consequently the frozen primary blend is simply the original ensemble:
68.62% accuracy, 39.94% precision, 81.18% recall and 53.54% positive F1.
No model is promoted. Sources, probabilities and history are preserved under
`outputs/training/contextual_discussion_20261024/`.

The paired comparison resamples three complete historical AMI project series,
not individual acts. The frozen primary equals the baseline, so its paired
difference interval is zero by construction. The baseline's exploratory 95%
interval is 57.21%–77.74% accuracy and 38.27%–65.93% positive F1. Three projects
are insufficient for a strong generalization claim; these are not fresh test
results. See `paired_baseline_comparison.json`.

The unweighted role candidate selected epoch 1. After development-only threshold
calibration, historical Proposal/Agreement/Disagreement/Confirmation F1 scores
are 14.35% / 6.77% / 5.45% / 18.40%, with macro F1 11.24%. It is not promoted.
Its artifacts are in `outputs/training/contextual_roles_20261024/`.

A separate balanced variant uses per-role negative/positive training-count
ratios as BCE positive weights and exact development F1 thresholds for both
checkpoint and operating-point selection. It runs in an isolated copy under
`.runtime/contextual_balanced_workspace/`; its full changed training source is
preserved in `outputs/training/contextual_roles_balanced_20261024/source_snapshot/`.
The original active trainer remains unchanged so ongoing frozen experiments
can be evaluated against their exact source hashes. No additional runs are
scheduled beyond the original discussion run and this balanced variant.

The balanced variant selected epoch 2: development macro F1 27.45%, historical
macro F1 21.25%. Historical Proposal/Agreement/Disagreement/Confirmation F1 is
29.31% / 22.34% / 0.00% / 33.33%. Weighting helps some roles but does not solve
rare disagreement detection. This is not presenter-influence accuracy.

A no-fitting downstream evaluation reuses the frozen development/historical
role probabilities, verifies their context pairs against runtime inputs, merges
confirmation into agreement, and runs the corrected fixed influence pipeline.
Pairwise accuracy is 71.11% development and 38.89% historical, versus word count
82.78% and 63.89%. This candidate is not promoted. Detailed scores and the exact
evaluation script are retained beside `fixed_influence_evaluation.json`.
The one GAP utterance with zero duration keeps its original timestamps; no
timing is fabricated or example silently removed.

## Ranking result

CPU `XGBRanker(objective='rank:pairwise')` uses meetings as query groups, as
described in the [upstream documentation](https://xgboost.readthedocs.io/en/release_3.1.0/tutorials/learning_to_rank.html).
AII supplies labels, never features. The 36-candidate development search compares
seven-feature, full-feature and semantic-topic variants; depth 1/2/3, 50/150 trees
and regularization 1/10. Features include activity, lexical markers, automatic
event counts and corrected decision-linked influence features.

The selected full-feature candidate has depth 1, 50 trees and regularization 1:

| Method | Development pairwise accuracy | Historical pairwise accuracy | Historical exact top-set accuracy |
| --- | ---: | ---: | ---: |
| Selected XGBoost | 86.11% | 50.00% | 33.33% |
| Word-count baseline | 82.78% | 63.89% | 50.00% |

Pairwise accuracy excludes human ties, gives predicted ties half credit and
weights each meeting equally. Only six historical meetings are available. This
candidate does not beat the baseline and is not promoted. A first trial had a
duplicate feature-name schema and was invalidated before historical scoring;
its diagnostic and original sources are preserved separately.

A fixed-weight ablation of the corrected keyword pipeline scores 56.11% on
development and 52.78% historically. Adding semantic topics gives 58.33% and
47.22%, respectively. Topic grouping has not demonstrated an influence-ranking
gain; the default remains off. Details: `corrected_pipeline_baselines.json`.

The valid run is `outputs/training/xgb_influence_20261024_v2/`. GAP AII measures
alignment between a person's initial ranking and the final group ranking, not
whose argument caused a decision. See the [GAP study](GAP_INFLUENCE_EXPERIMENT.md).
CPU XGBoost 3.1.2 is isolated in `.runtime/research-ranking-deps/`; wheel URL,
SHA-256 and size are in `package_provenance.json`. No global/app dependency was
changed. Provision `xgboost-cpu==3.1.2` when reproducing in a clean environment.

## Optional pipeline changes

- Semantic grouping separates unrelated nearby decisions; short responses
  inherit the preceding topic. This fixed heuristic needs external validation.
- Contextual Proposal/Agreement/Disagreement replace their keyword roles.
  Confirmation also maps to agreement, merged per passage, rather than a final
  decision. Explicit decision rules and other roles remain. Original speaker,
  time, text and source IDs are retained. English models are skipped for
  unsupported languages.
- Outcome candidates retain source/outcome IDs and text. Future predictions
  occupy separate fields from human labels; clustering never proves adoption.
- Speaker margin can return `UNKNOWN` when overlap totals are too close.
  Attribution changes reuse the original speech observations.
- Optional ranking exports raw margins separately from ordinary influence
  scores. They are not correctness probabilities. Topic settings must match.

The margin diagnostic uses four previously examined 120-second AMI clips with
**oracle reference word timing**. On the two historical clips pooled, margin 0
assigns 390/426 words and correctly attributes 353; margin 0.1 assigns 385 and
correctly attributes 352. Accepted precision rises 90.51% to 91.43%, coverage
falls 91.55% to 90.38%, and accuracy counting unknown as wrong falls 82.86% to
82.63%. This excludes transcription errors and supports no default change.
Per-clip curves and input hashes: `outputs/training/speaker_margin_20261024.json`.

## Independent annotation work

`outputs/training/outcome_annotations_20261024/` has 38 blank candidates across
21 existing AMI meetings, with source hashes. The old pipeline selected them;
they can omit real contributions/outcomes and are not a complete gold corpus.

Annotators must inspect original context, correct invalid pairs, add missing
pairs and independently label relationships. Preserve shared credit. Do not
infer adoption from proximity. Use multiple annotators and adjudication, and
report agreement. Set `label_source: "human"` only after checking. Assign splits
by complete team/project series, keeping repeated sessions together. The final
reference cohort must be independent of model suggestions.

These 38 candidates are insufficient evidence for reliable relationship
training. Collect more representative meetings and rejected/revised alternatives.
Act/role tags cannot substitute for relationship labels. Separately obtain
human influence rankings that measure the intended construct, not only GAP AII.

The local AMI argumentation annotations were also inspected: 94 relation files
use Positive, Negative, Uncertain, Option, Elaboration, Specialization,
Subject-to, Option-exclusion and Request. These are potential auxiliary
supervision for dialogue relationships. They do not directly label final
adoption/rejection/revision/unresolved outcomes, so they were not relabelled as
outcome ground truth. The ontology is in
`AMI_dataset/annotations/ami_public_manual_1.6.2/ontologies/ar-types.xml`.

## Reproduction

Use new output directories; historical evaluation refuses to overwrite results.
The next annotation stage has a [local command guide](../guides/OUTCOME_ANNOTATION_COMMANDS.md)
for preparing human review sheets, validating checked labels and running the
outcome-link experiment without additional chat orchestration.

```bash
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false \
  .venv/bin/python scripts/train_contextual_model.py --task discussion \
  --output-dir outputs/training/contextual_discussion_NEW --epochs 2
.venv/bin/python scripts/train_contextual_model.py --task discussion \
  --output-dir outputs/training/contextual_discussion_NEW --evaluate

.venv/bin/python scripts/train_contextual_model.py --task roles \
  --output-dir outputs/training/contextual_roles_NEW --epochs 2
.venv/bin/python scripts/calibrate_contextual_roles.py \
  --output-dir outputs/training/contextual_roles_NEW
.venv/bin/python scripts/train_contextual_model.py --task roles \
  --output-dir outputs/training/contextual_roles_NEW --evaluate

.venv/bin/python scripts/train_contextual_model.py --task links \
  --manifest PATH_TO_INDEPENDENT_HUMAN_LABELS.jsonl \
  --output-dir outputs/training/contextual_links_NEW

.venv/bin/python scripts/process_meeting.py --audio PATH_TO_AUDIO \
  --meeting-id UNIQUE_RESEARCH_ID --topic-aware --outcome-links --speaker-margin 0.1
.venv/bin/python -m pytest tests -q
```

`--event-model DIR`, `--discussion-model DIR`, `--outcome-model DIR` and
`--ranker-model DIR` explicitly enable frozen candidates. Supply the directory
containing the protocol/selection, not its internal `model/` subdirectory.
Do not automatically combine every flag: this ranker was trained on keyword
events; replacing their extractor changes its feature distribution. A joint
upgrade requires matched training/evaluation. Use a new research meeting ID
because ordinary analysis outputs for an existing ID can be overwritten.
