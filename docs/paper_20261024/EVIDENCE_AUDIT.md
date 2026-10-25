# Evidence audit for the new IEEE manuscript

Reviewed 24 October 2026. This is a manuscript evidence ledger, not an additional experiment. Application sources and saved research outputs were read; no training or application changes were made.

**Version note:** This ledger describes the earlier draft's experiment tables.
The revised main paper adds the controlled exploratory analysis under
`analysis/`; its protocol, results and replay are the authority for the new
Tables III–V. Historical measurements below remain unchanged in the supplement.
See `REVISION_RESPONSE.md` for the new evidence and unresolved validation gaps.

## Governing scope

The intended construct is each participant's contribution to meeting decisions and outcomes. GAP AII is an available **outcome-alignment proxy**, not a direct causal influence label. Discussion membership, dialogue roles, audio accuracy and agreement with AI relation labels are separate tasks; their percentages must never be combined into one system-accuracy figure.

`professor_guidelines/guidlines.txt` requests Springer MTAP, 10–15 relevant papers, an implemented-feature comparison, clear novelty, restrained claims, informative ablations, first citation [1], no citations in abstract/conclusion, and in-text discussion of every figure/table. The user's later explicit request chooses IEEE format; use IEEE while retaining the substantive evidence requirements. The user subsequently approved the paper title **InfluenceIQ: A Multimodal Framework for Assessing Participant Contributions to Meeting Decisions**; this supersedes the earlier title-preservation instruction for the new manuscript.

## 1. Primary GAP experiment: frozen before first final scoring

Authoritative artifacts: `outputs/training/gap_influence_20261024/{protocol,selection,development_search,test_results}.json`. Explanation: `docs/research/GAP_INFLUENCE_EXPERIMENT.md`.

- Corpus: 28 meetings, 84 participants, 8,009 utterances. English reference transcripts, supplied speaker IDs/timestamps; no ASR, diarization or slide errors enter this evaluation. GAP release CC BY-NC 4.0.
- AII: distance between individual pre-meeting ranking and final group ranking; **lower means greater alignment**. It can reflect initial agreement rather than a participant causing change. It is not independent ratings of presenter influence.
- Complete-group split, seed 20261024: training 16 groups/45 participants; development 6/20; first final cohort 6/19. Final IDs: 3, 26, 9, 12, 17, 7.
- Within-meeting training target is `(rankdata(-AII)-1)/(n_participants-1)`, preserving ties. Structure variables are within-meeting max normalized, then standardized on training participants. Word/bigram TF-IDF uses `min_df=2`, `max_features=2500`, sublinear TF, fit on training only.
- Search: 30 learned configurations across ridge, pairwise logistic and Extra Trees × structure/text/combined, plus five baselines = 35 eligible candidates. Parameters selected using development meeting-average pairwise accuracy; fixed candidate order breaks ties. Primary: **structure Extra Trees**, 150 trees, minimum leaf size 5.
- Primary development pairwise accuracy **83.3333%**; word-count development **82.7778%**. These are not final results.

| Frozen method | Final pairwise accuracy (%) | Exact top-set accuracy (%) |
|---|---:|---:|
| Speaking time | 52.7778 | 33.3333 |
| Word count | 63.8889 | 50.0000 |
| Utterance count | 41.6667 | 33.3333 |
| Decision-linked event count | 52.7778 | 16.6667 |
| Original prototype influence | 52.7778 | 16.6667 |
| Structure ridge | 55.5556 | 16.6667 |
| Structure pairwise logistic | 47.2222 | 16.6667 |
| **Structure Extra Trees: selected primary** | **61.1111** | **33.3333** |
| Text ridge | 41.6667 | 16.6667 |
| Text pairwise logistic | 47.2222 | 16.6667 |
| Text Extra Trees | 58.3333 | 50.0000 |
| Combined ridge | 55.5556 | 16.6667 |
| Combined pairwise logistic | 47.2222 | 16.6667 |
| Combined Extra Trees: nonprimary | 66.6667 | 50.0000 |

Pairwise accuracy excludes reference ties, awards predicted ties 0.5 and weights meetings equally. Exact top-set accuracy requires equality of the full predicted/reference top sets. An all-tied prediction therefore does not automatically succeed. Primary 95% percentile meeting-bootstrap interval: **33.3333–83.3333%**, 10,000 resamples of just six meetings. No superiority claim is supported. The primary is 2.7778 percentage points below word count. Selecting the 66.6667% combined model after inspecting final scores would invalidate the original selection.

**Important diagnostic:** prototype and decision count predict complete ties in five of six final meetings; their 52.7778% mainly reflects tie half-credit. Both have only one meeting with defined Spearman correlation. Their stored mean Spearman 0.5 must not be compared without reporting this 1/6 coverage. Avoid an unqualified mean-correlation table.

**Version boundary:** this initial experiment predates current attribution corrections. `source_snapshot/` contains its exact sources; all source hashes listed in its protocol were checked against the snapshot and match. Re-running current app sources does not reproduce this version. The initial feature-name list contains repeated descriptive labels for event counts and influence counts; do not confuse this positional representation with the separately invalidated first XGBoost schema.

## 2. Later GAP experiments: historical exploratory evaluations

The same six final GAP meetings were already inspected. Later results are historical/exploratory, not repeated fresh tests. Never pool their candidate count as independent evidence or present the largest observed percentage as primary.

### Semantic and role summaries

Sources: `outputs/training/gap_influence_semantic_20261024/`, especially protocol, development search, selection, historical results, role diagnostics and oracle diagnostic. Summary: `docs/research/INFLUENCE_PIPELINE_FINDINGS.md`.

50 candidates: 45 learned trials and five baselines. Cached MiniLM embeddings, 90-second bounded semantic reuse/uptake summaries, speaker embeddings and four group-cross-fitted contextual role detectors were explored. **These features also predate production attribution corrections.** The selected primary is word count.

| Development-selected representative | Development pairwise (%) | Historical pairwise (%) |
|---|---:|---:|
| Word count: selected primary | 82.7778 | 63.8889 |
| Lower keyword threshold | 80.0000 | 52.7778 |
| Semantic summaries | 74.4444 | 30.5556 |
| Semantic + speaker embeddings | 65.0000 | 50.0000 |
| Learned-role summaries | 74.4444 | 36.1111 |
| Learned roles + speaker embeddings | 62.7778 | 41.6667 |

Development proposal F1: keyword threshold 0.30 = 0%; 0.25 = 1.49%; contextual role detector = **42.02%** (precision 28.17%, recall 82.64%). This is a supporting role metric, not influence accuracy. Privileged manual-role features reached 80% best tested development pairwise accuracy, below word count; this is neither an automatic-system score nor a mathematical upper bound.

### Corrected pipeline, topics and XGBoost

Sources: `outputs/training/xgb_influence_20261024_v2/{protocol,ranker,development_search,historical_evaluation,corrected_pipeline_baselines}.json` and `docs/research/CONTEXTUAL_INFLUENCE_UPGRADE.md`.

- Corrected fixed keyword pipeline: development **56.1111%**, historical **52.7778%**.
- Fixed pipeline plus semantic topics: development **58.3333%**, historical **47.2222%**.
- 36-candidate XGBoost grid: seven/full/topic features; depth 1/2/3, 50/150 trees, lambda 1/10. Selected full-feature model: depth 1, 50 trees, lambda 1; development **86.1111%**, historical **50.0000%**, exact top set **33.3333%**.
- Original `outputs/training/xgb_influence_20261024/` was invalidated for a feature-name collision before historical evaluation. It is not a valid comparison row. Use only `..._v2`.

### Neural contribution roles

Sources: `outputs/training/contextual_roles_20261024/` and `contextual_roles_balanced_20261024/`.

Each ran two epochs; unweighted historical macro F1 **11.24%**. Balanced selected epoch 2, development macro F1 **27.45%**, historical **21.2468%** on 1,525 utterances. Historical role F1: Proposal **29.3103%**, Agreement **22.3433%**, Disagreement **0%**, Confirmation **33.3333%**. Confirmation is merged into agreement, not treated as a final decision. With the corrected fixed influence scorer, downstream development pairwise accuracy **71.1111%**, historical **38.8889%**, versus word count 82.7778% / 63.8889%. No candidate was installed.

## 3. AMI discussion classifier: a supporting task

Installed model `models/discussion/model.joblib`, SHA-256 `1db06c011c554b056528a02c08a379d3aa88835aa28d78e312d6c801d12725bf`. Direct bundle inspection confirms **25% Logistic Regression + 75% Random Forest**, context radius 40, baseline smoothing radius 5, threshold 0.3577398635496262. Classifiers use training-fitted word/character/context TF-IDF. This is binary discussion membership, not the participant influence model.

Data counts independently checked in `.runtime/research-decision-model/{train,dev,test}.jsonl`: 20,339 training acts/29 meetings/12 project series; 3,739 development acts/6 meetings/2 series; 11,136 historical acts/12 meetings/3 series. Historical project series ES2016, IS1006, TS3005; 2,481 positives and 8,655 negatives.

Installed historical metrics: accuracy **68.6153%**, balanced accuracy **73.0957%**, positive precision **39.9445%**, recall **81.1769%**, positive F1 **53.5425%**, AP **53.3985%**. All-negative baseline accuracy **77.7209%**, positive F1 zero. This directly shows why a single high accuracy percentage would be misleading.

Two-epoch full-encoder MiniLM fine-tuning selected epoch 1. Historical neural F1 **46.3167%**. Development-selected blend gives neural weight **zero**, reproducing the original ensemble exactly. Its nested `metrics` field inside historical `frozen_blend` retains DEVELOPMENT precision/recall/F1 (F1 59.7931%); do not accidentally report that nested field as historical performance. Use the top-level frozen-blend historical F1 53.5425%.

Sources: `outputs/training/contextual_discussion_20261024/{protocol,selection,historical_evaluation,paired_baseline_comparison}.json`; detailed original bundle selection available via saved classifier reports. Exploratory project-bootstrap 95% interval: accuracy **57.2070–77.7357%**, F1 **38.2710–65.9328%**. Three project groups offer very weak uncertainty resolution; paired candidate-baseline interval is zero because the selected blend is identical.

## 4. AI-generated contribution–outcome pilot

Latest authoritative sources: `outputs/training/outcome_ai_review_20261024/`, `outputs/training/outcome_ai_model_20261024/{protocol,selection,summary,ai_agreement_evaluation}.json`, and `docs/research/AI_OUTCOME_PILOT.md`.

- All 38 original automatic candidates/21 meetings were inspected by one assistant; 6 judged repairable, 32 unsuitable/ambiguous. These are qualitative audit dispositions, not measured extraction precision/recall.
- 53 purposively curated judgments, 3 uncertain excluded, 50 included. Train/development/historical counts **31/8/11**, complete project series **8/3/3**, allocation seed 20261024. Model seed 42 is separate from the allocation seed.
- Labels explicitly `ai_generated`, `independent_human_review=false`. No human annotation, independent adjudication or inter-rater agreement. Class order: adopted/rejected/revised/unresolved. Counts: train 19/5/2/5; development 5/1/0/2; historical 7/3/0/1. No revised instances in development/historical references: four-class validity is unestablished.
- Inputs include manual transcripts and supplied outcomes; some outcomes are human-written abstractive summaries. This pilot does not automatically extract those outcomes from speech. Origin credit and causal impact are not verified.
- Class-balanced Logistic Regression, word/bigram + character TF-IDF, paired C in 0.1/1/10 selected by development four-class macro F1. Rationales, reference IDs, speaker IDs and relation labels excluded from features.
- Selected paired C=1: development agreement **6/8 = 75%**, macro F1 **37.5%**. Historical figures below; all four labels retained in macro F1 with zero where appropriate.

| Method | Historical AI-label agreement (%) | Four-class macro F1 (%) |
|---|---:|---:|
| Training-majority | 63.6364 (7/11) | 19.4444 |
| Source-only | 63.6364 (7/11) | 19.4444 |
| Outcome-only | 36.3636 (4/11) | 13.3333 |
| Paired: selected primary | 54.5455 (6/11) | 17.6471 |

The earlier `research_upgrade_summary_20261024.json` says outcome links were not trained. This reflects the state **before** the later separate AI pilot and must not override these newer artifacts. Independent human-labelled outcome training remains unperformed. Regression-test counts (624 earlier full suite, 28 later targeted) measure software checks, never research accuracy.

## 5. Exact active influence scoring

Source: current `src/meeting/influence.py`, `extract_features`, `_max_normalise`, `compute_influence`, `compute_decision_contributions`. This describes the **corrected active implementation**; the initial/semantic experiment snapshots differ as noted below.

For participant p, let x[p,k] be one of seven nonnegative raw features. Let C[d] be the unique event IDs retained in decision cluster d, s(e) its speaker, and t(e) its start. Event-to-cluster association is heuristic; its presence is not verified adoption. For features using an event-to-decision map, later cluster insertion overwrites a repeated event assignment. Accurate prose should describe the implementation's associations rather than assume a gold partition.

1. **Proposal P:** sum, over each decision cluster, of proposal events in C[d] spoken by p. Every observed proposal receives one unit. Current code gives no automatic adoption bonus to the first proposer.
2. **Evidence E:** each decision-linked evidence event by p contributes `1 + 0.5 × indicator(slide_id present)`.
3. **Objection O:** each decision-linked objection/disagreement by p contributes `0.5 + indicator(any revision in associated cluster starts later)`. The later-revision bonus is temporal association; it does not demonstrate triggering or causation.
4. **Revision R:** one unit for each p revision in a cluster with status confirmed or probable.
5. **Decision D:** each event by p in a confirmed cluster contributes 1; in a probable cluster 0.5; in other clusters 0.
6. **Interaction I:** each interaction with a non-null related decision contributes one unit to its **source** speaker, provided that speaker has a feature vector.
7. **Slide G:** each event by p with a slide ID and a decision link contributes one unit. A grounded evidence event therefore contributes to both E and G, an intentional correlated proxy in this implementation.

Normalization and score:

`z[p,k] = x[p,k]/max_q x[q,k]` if the maximum is positive, otherwise zero.

`S[p] = round_6(sum_k w[k] z[p,k])`, weights `(P,E,O,R,D,I,G) = (0.15,0.20,0.15,0.20,0.15,0.05,0.10)`.

Config-loaded weights are clipped nonnegative and normalized to sum one. These are **unvalidated prototype weights**, not learned calibrated probabilities. Scores need not sum one across people and are meeting-relative. Ties share ranks. Non-event transcript speakers are retained with zero features when transcript segments are supplied; UNKNOWN is excluded. Thus a zero score can mean missed evidence rather than lack of real influence.

Decision-level display contribution:

`c[p,d] = round_4((number of p events in C[d] / max(1, |C[d]|)) × mean_k z[p,k])`.

This reuses the unweighted mean of the **seven meeting-normalized features**, not S[p] and not a separately normalized per-decision model. It cannot be described as independent validation of decision-level influence. Supporting event IDs and roles are retained to inspect the score.

**Historical formula distinction:** initial and semantic source snapshots count only the designated first proposal, with +1 for a confirmed cluster having a final decision. This bonus did not establish adoption. Reconstruction also formerly omitted secondary proposals/decisions; evidence-provider role assignment and evidence edge direction were later corrected. The current corrected method description needs an explicit version note beside historical results.

## 6. Older-draft claims to remove or confine

`professor_guidelines/RESEARCH_VALIDITY_REVIEW.md` documents the original recording's degeneracy: six raw feature categories inactive, only decision feature active; the proposed ranking collapses to the decision-event baseline. A5/A6 score movements are uniform weight-renormalization effects, not accuracy gains. All 34 slides lacked timing, so temporal deletion was uninformative. These are findings from the preserved written review: its referenced `evaluation/research_validity_audit.json` is absent in the current checkout, so this audit did not independently rerun those older numerical checks. In a separate three-meeting annotation-workflow pilot, all seven features were zero and ratings remained blank.

The four 120-second AMI audio excerpts are local diagnostic splits, not the official AMI test set. DER uses a custom segment-reference protocol; prefix-exclusion diagnostics are post-hoc sensitivity analyses, not corrected benchmark scores. Strict Hinglish WER also contains script disagreement and tiny, correlated samples. Oracle-timed speaker-margin precision is not end-to-end ASR/diarization accuracy. Keep these peripheral diagnostics out of the central claim, or state their protocols explicitly.

Avoid: “75%+ influence accuracy,” “state-of-the-art,” causal attribution, proven multimodal benefit, proven privacy/security guarantees, fresh final testing after iterative historical inspection, independent human outcome labels, validated Hindi/Hinglish influence, new gold dataset, and publication/acceptance guarantees. A defensible manuscript reports a source-linked prototype and a small, reproducible diagnostic evaluation with negative comparisons and clear construct limits.
