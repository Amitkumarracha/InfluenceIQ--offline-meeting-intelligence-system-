# Local outcome-link annotation and training

Earlier discussion/role/ranking experiments are complete. The next stage needs
independent human labels. These commands prepare the worksheets, validate checked
labels and train/evaluate an outcome-link classifier. They do not guarantee a
percentage improvement or complete a new presenter-ranking model.

## Prepare once

```bash
cd '/home/amitkumar/Music/MAI Project'
export OPENBLAS_NUM_THREADS=2
export OMP_NUM_THREADS=2
export TOKENIZERS_PARALLELISM=false
.venv/bin/python scripts/outcome_annotation_workflow.py prepare \
  --output outputs/training/outcome_review_v1
xdg-open outputs/training/outcome_review_v1
```

The directory contains `reviewer_A.csv`, `reviewer_B.csv`, `adjudicated.csv`,
`provenance.json` and manual AMI transcript context under `context/`.
Open CSV files as UTF-8 spreadsheets. Preserve CSV column names and quotation
marks by saving with your spreadsheet application's CSV export.

## Human work before running training

1. Two people review A/B sheets independently using the manual transcript context
   and recording where needed. Candidate sources/outcomes are existing model
   suggestions. Check both text and actual speaker, and add missed pairs.
   Predicted `SPEAKER_*` IDs do not establish the manual A–D speaker mapping.
2. Use `relationship` values `adopted`, `rejected`, `revised`, `unresolved`.
   Adopted requires evidence that the final choice incorporates the contribution;
   rejected requires evidence against it; revised requires a substantive change;
   unresolved means the available outcome leaves that contribution undecided.
   Nearby passages alone do not prove a relationship. A missing detected outcome
   may indicate extraction failure; inspect the transcript before assigning a label.
3. Resolve disagreements in `adjudicated.csv`; retain the independent A/B copies
   for agreement analysis. Set `include=yes` for verified pairs or `include=no`
   for invalid pairs. Record reasons/corrections in `review_note`. Set
   `label_source=human` only after checking. Included pairs need source/outcome
   text and unique traceable IDs. Add missing outcome text/ID only from a verified
   passage; exclude invalid candidates.
4. Keep the AMI project-series `group` (for example `ES2002`) intact across all
   its sessions. Assign `split=train`, `dev` or `test`, keeping every group in
   exactly one split. Freeze this allocation before model fitting. Reserve fresh
   independent meetings for final paper confirmation, using compatible group
   splits across upstream and downstream models.
5. Expand beyond this 38-pair pilot. The converter requires all four relationship
   classes in every split and rejects group leakage. Passing this validation is
   a structural check, not proof that a small dataset is adequate or labels are
   independent. Retain shared contribution credit and add rejected/revised
   alternatives; record separate human presenter-impact rankings for the intended
   paper task.

## Validate and convert

Run after the manual work and dataset expansion:

```bash
.venv/bin/python scripts/outcome_annotation_workflow.py convert \
  --csv outputs/training/outcome_review_v1/adjudicated.csv \
  --output outputs/training/outcome_links_labels_v1.jsonl
```

The command prints class counts or explains missing/invalid data. Fix the input
and repeat if it fails. Existing review directories and training-label files are
never overwritten; use `v2`, `v3`, etc. for new versions.

## Train, then evaluate once

Run only after conversion succeeds and the labels/cohort are adequate. Use a
new model directory. The training command selects on development data; it does
not read test labels. Wait until training exits successfully before evaluation.

```bash
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false \
  .venv/bin/python scripts/train_contextual_model.py \
  --task links \
  --manifest outputs/training/outcome_links_labels_v1.jsonl \
  --output-dir outputs/training/outcome_links_model_v1 \
  --epochs 2 --threads 2
```

```bash
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 \
  .venv/bin/python scripts/train_contextual_model.py \
  --task links \
  --manifest outputs/training/outcome_links_labels_v1.jsonl \
  --output-dir outputs/training/outcome_links_model_v1 \
  --evaluate --threads 2
```

Inspect `protocol.json`, `history.json`, `selection.json` and
`historical_evaluation.json` in the model directory. Preserve these files and
the exact labels. Repeated test-informed changes make the cohort historical;
reserve fresh groups for confirmation. These are relationship-classification
scores, not presenter-influence accuracy.

Afterwards, measured relationship quality will determine the next integration
step. A ranker using learned outcome links still needs matched feature training
and independent presenter-impact labels; the current XGBoost script uses keyword
features. Existing experimental relation predictions are exported separately
and do not automatically change influence scores or application defaults.
