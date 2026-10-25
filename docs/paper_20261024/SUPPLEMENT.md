# InfluenceIQ — Supplementary Research Records

This supplement preserves complete earlier comparisons, provenance, and scope distinctions for the revised manuscript. Main-paper Tables III–V describe the new controlled exploratory analysis. Numbers below retain their original splits and feature versions. No historical score is promoted to a fresh final result.

## S1. Version and target matrix

| Record | Features and labels | Evaluation role |
| --- | --- | --- |
| A: initial GAP snapshot | Pre-correction events and contribution definitions; average-tie AII rank target | 16 training / 6 development / 6 original evaluation meetings; selected structure Extra Trees |
| B: semantic/role snapshot | Earlier attribution definitions; semantic uptake and group-cross-fitted role features | Same historical GAP groups, already examined |
| C: corrected v2 snapshot | Corrected proposal credit, evidence direction, and reconstruction; XGBoost uses dense unique-AII ranks | Stored full features of all 84 people; original v2 historical ranker comparison |
| D: controlled revision | C's six normalized activity and seven contribution features; average-tie target recomputed from AII | Seven outer / three inner group folds; exploratory prior-corpus reuse |
| E: AMI discussion | Binary discussion-membership labels on manual acts | Separate component task, not participant contribution |
| F: AI outcome-link pilot | Single-assistant relationship labels and supplied outcome passages | AI-label agreement, not human-validated influence |

The canonical decision and influence source SHA-256 values are 6c009a0ce0f8588e88d7a8e6817ad2714a6d921dd0c40dd05386a30e44fd11c8 and 05f79c26e6f3fc1546ea1d1e97a003fd60688bcb440a74b2d2b183facb9e1d9b, respectively. All relevant hashes and the original feature-source digest are retained in analysis/protocol.json and historical_records. Names that previously repeated in positional feature arrays are not confused with the separately invalidated first XGBoost schema.

The initial learned target used average-tie participant ranks. The corrected XGBoost feature export used dense unique-AII ranks; the controlled Ridge study recomputes its declared average-tie target from supplied AII. An explicit preflight assertion caught this distinction before fitting; the aborted preparation was archived. A later serialization-only failure was corrected without changing the protocol's models, folds, features, or selection criteria. No successful scientific result was overwritten.

## S2. Original group splits and full ranking comparison

The GAP split seed is 20261024. Training comprises meetings 11,18,13,25,2,19,1,24,16,23,28,10,14,5,20,22; development 6,21,15,8,27,4; original evaluation 3,26,9,12,17,7. These are complete meetings, with 45/20/19 people respectively. Reference English transcripts and identities are supplied. No slides or speech-recognition outputs enter this task.

| Branch | Training | Development | Historical evaluation |
| --- | --- | --- | --- |
| GAP participant ordering | 16 meetings / 45 people | 6 meetings / 20 people | 6 meetings / 19 people |
| AMI discussion membership | 29 meetings / 20,339 acts | 6 meetings / 3,739 acts | 12 meetings / 11,136 acts |
| AI-labelled AMI outcome links | 8 project series / 31 pairs | 3 series / 8 pairs | 3 series / 11 pairs |

The initial selection compares 30 learned configurations and five fixed baselines using development meeting-average pairwise accuracy. Structural Extra Trees with 150 trees and minimum leaf size five is selected. Its development score is 83.33% versus 82.78% for word count. The table retains all finalists, including the nonselected combined Extra Trees candidate.

| Method | Pairwise accuracy (%) | Exact top-set accuracy (%) |
| --- | --- | --- |
| Speaking duration | 52.78 | 33.33 |
| Word count | 63.89 | 50.00 |
| Utterance count | 41.67 | 33.33 |
| Decision-event count | 52.78 | 16.67 |
| Prototype influence score | 52.78 | 16.67 |
| Structure: ridge | 55.56 | 16.67 |
| Structure: pairwise logistic | 47.22 | 16.67 |
| Structure: Extra Trees, selected primary | 61.11 | 33.33 |
| Text: ridge | 41.67 | 16.67 |
| Text: pairwise logistic | 47.22 | 16.67 |
| Text: Extra Trees | 58.33 | 50.00 |
| Combined: ridge | 55.56 | 16.67 |
| Combined: pairwise logistic | 47.22 | 16.67 |
| Combined: Extra Trees | 66.67 | 50.00 |

The primary model has a 33.33–83.33% interval from 10,000 resamples of six complete meetings. Only 21 reference-comparable participant pairs exist, clustered within those meetings. The prototype and decision-count predictions are constant in five meetings. A mean Spearman value over only the single nonconstant meeting is not a valid general ranking summary.

## S3. Later exploratory feature and model comparisons

All later GAP trials reuse historical groups. Semantic uptake features use a fixed 90-second window and frozen sentence representations; participant-text embeddings are not acoustic identity embeddings. Four logistic role detectors use group cross-fitting on training meetings. The 50-candidate round selects word count overall.

| Method | Development pairwise (%) | Historical pairwise (%) |
| --- | --- | --- |
| Word-count baseline | 82.78 | 63.89 |
| Lower keyword threshold, earlier source | 80.00 | 52.78 |
| Semantic uptake, earlier source | 74.44 | 30.56 |
| Uptake plus participant-text embeddings, earlier source | 65.00 | 50.00 |
| Learned-role summaries, earlier source | 74.44 | 36.11 |
| Roles plus embeddings, earlier source | 62.78 | 41.67 |
| Corrected keyword fixed score | 56.11 | 52.78 |
| Corrected score plus semantic topics | 58.33 | 47.22 |
| Balanced contextual roles, corrected fixed score | 71.11 | 38.89 |
| Selected XGBoost, corrected features | 86.11 | 50.00 |

The corrected XGBoost grid has 36 candidates: seven/full/topic features, depths 1/2/3, 50/150 trees, and regularization 1/10. Its selected full-feature candidate uses depth one, 50 trees, regularization one, learning rate 0.05, and seed 42. A schema-invalid earlier trial was not historically evaluated. The privileged manual-role diagnostic reaches 80.00% development pairwise accuracy among tested settings, below word count; this is neither an automatic system score nor a mathematical upper bound.

## S4. Discussion and contextual-role components

The discussion target is membership in a manually annotated decision-discussion span, not the adoption of a proposal. Acts with at least half of their lexical word IDs inside a span are positive. The training/development/historical counts are 20,339/3,739/11,136 acts and 29/6/12 meetings. Historical meetings belong to only three project series. The installed combination is 75% Random Forest and 25% Logistic Regression, with context radius 40, smoothing radius five, and threshold 0.3577398635496262. Historical accuracy is 68.62%, positive precision 39.94%, recall 81.18%, F1 53.54%, and average precision 53.40%. An all-negative predictor has 77.72% accuracy and zero positive F1.

| Component or variant | Historical metric | Score (%) |
| --- | --- | --- |
| Existing discussion combination | Positive F1 | 53.54 |
| Neural discussion candidate | Positive F1 | 46.32 |
| Unweighted neural roles | Four-role macro F1 | 11.24 |
| Balanced neural roles | Four-role macro F1 | 21.25 |
| Balanced roles: proposal | Role F1 | 29.31 |
| Balanced roles: agreement | Role F1 | 22.34 |
| Balanced roles: disagreement | Role F1 | 0.00 |
| Balanced roles: confirmation | Role F1 | 33.33 |

The neural discussion, unweighted-role, and balanced-role runs each last two epochs. They fine-tune all MiniLM layers and a new head, with two neighboring turns on either side and a 96-token limit. Discussion selects epoch one and no neural blend weight; balanced roles select epoch two. Confirmation is mapped to agreement in the downstream fixed-score experiment, not converted into a final decision. The role and participant-ranking percentages remain distinct. The recorded protocols specify batch size 24, learning rate 0.00002, seed 42, and two epochs. The preserved trainer uses AdamW, weight decay 0.01, gradient clipping at one, and its recorded warmup/decay schedule. Complete effective protocols are included in historical_records; unavailable checkpoint revision details are not invented.

## S5. AI-labelled outcome-link feasibility pilot

A single assistant inspected all 38 original candidates across 21 meetings: six were judged repairable and 32 unsuitable or ambiguous. It purposively curated 53 source-linked judgments, excluded three uncertain pairs, and fitted 50. This is not extraction precision/recall or independent human annotation. Some outcome inputs are human-written meeting summaries rather than automatically extracted decisions. Rationales, speaker IDs, reference IDs, and labels are excluded from model features.

| Method | Agreement (%) | Four-class macro F1 (%) |
| --- | --- | --- |
| Training-majority baseline | 63.64 | 19.44 |
| Source-only control | 63.64 | 19.44 |
| Outcome-only control | 36.36 | 13.33 |
| Paired source/outcome model, selected primary | 54.55 | 17.65 |

Training classes adopted/rejected/revised/unresolved have counts 19/5/2/5; development 5/1/0/2; historical evaluation 7/3/0/1. The missing revised class prevents four-class validation. Macro F1 includes all four declared classes, assigning zero as specified. Class-balanced paired Logistic Regression selects C=1 from 0.1/1/10 using development macro F1. Development agreement is 6/8 (75%), not a final influence score. Historical agreement is 6/11 (54.55%), below majority 7/11 (63.64%). Source-only and outcome-only controls use C=1.

The group allocation seed is 20261024, separate from the model seed 42. Eight/three/three project series supply training/development/evaluation pairs. Labels retain ai_generated provenance and independent_human_review=false. This pilot supplies no human influence ratings, independent adjudication, inter-annotator agreement, or causal reference. It is retained as feasibility evidence only.

## S6. Decision-display definition and weight sensitivity

The meeting score is the weighted sum in the main paper. A distinct decision-level display uses the participant share of events in that cluster multiplied by the unweighted mean of that participant's seven meeting-normalized features, rounded to four decimals. It is not a separately learned per-decision contribution model. Both definitions retain source IDs but lack independent personal-impact validation.

| Deleted fixed-score feature | Pairwise (%) | Constant meetings / 28 |
| --- | --- | --- |
| proposal | 55.77 | 22 |
| evidence | 55.77 | 22 |
| objection | 55.77 | 22 |
| revision | 55.77 | 22 |
| decision | 50.30 | 24 |
| interaction | 56.96 | 22 |
| slide_grounding | 55.77 | 22 |

Deletion sets only the chosen weight to zero, with no renormalization or model fitting. No gain is claimed from uniform score rescaling. Inactive slide features reflect absent inputs, while missing proposals/evidence/revisions may reflect extraction or relation failures.

## S7. New analysis reproducibility and inference limits

The frozen protocol and derived input records are in analysis/. Each of seven outer folds evaluates four complete meetings; three inner group folds select among four Ridge alphas. The three feature families share fold assignments, estimator family, and tuning budget. Scalers fit inside their relevant training partitions. Every participant receives one outer prediction. Group identities, selected parameters, per-meeting scores, and paired resampling results are retained. Constant-prediction metrics have explicit scoring self-checks.

This is review-motivated exploratory reuse of previously examined data. Group-disjoint fitting does not create independent construct labels or reverse prior researcher exposure. Overlapping outer training sets make intervals conditional descriptive summaries rather than formal population guarantees. A new corpus and independent outcome-contribution references remain needed for confirmation. The analysis does not fit neural models, replace application defaults, or claim a multimodal gain.

The source-linked case records use existing manual GAP role labels; their selection is purposive and their influence/outcome relationships are unlabelled. A correct role match is not a complete-system success. No private recording or full corpus is distributed. Derived GAP records remain subject to the original CC BY-NC 4.0 terms, with citation to Braley and Murray (2018) and the ConvoKit GAP release. AMI records are referenced rather than redistributed.
