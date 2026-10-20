# Evaluation protocol and submission checklist

## 1. Evidence levels

Functional tests establish that code paths behave as asserted. A synthetic microphone browser test establishes capture/UI integration, not speech accuracy. A real-model smoke check establishes that local inference returns output. Accuracy requires a reference created independently of model output. The pilot scores in `EVALUATION_RESULTS.md` apply only to the listed excerpts; they are not full AMI, FLEURS or MUCS challenge scores.

## 2. Frozen audio pilot

AMI development: ES2002a and ES2003a. Held-out: IS1001b and TS3007d. Each excerpt uses Array1-01 from 60 to 180 seconds. The four clustering thresholds 0.5, 0.7, 0.9 and 1.1 were specified before inference. Select minimum pooled development DER, with lower-threshold tie-breaking. Test meetings use different meeting groups and do not select the threshold. Speech-segment boundaries come from manual AMI annotations; internal silence and overlap affect this pilot. Score DER on the explicit 120-second interval, include overlapping speech, use optimal label mapping and a 0.25-second collar. Report each meeting, components and speaker counts. Two held-out meetings are too few for convincing significance claims.

Hindi: eight official FLEURS hi_in test archive entries, selected in archive order before inference. Hinglish: first eight MUCS mirror test rows, also selected before inference. Manifests record revisions, IDs, hashes and selection. These Hinglish examples are consecutive technical lecture excerpts, not independent speakers or meetings. References are used only for scoring, never as vocabulary hints. Compare small and medium models on exactly the same samples; this is exploratory model comparison, not training or selection against an unseen deployment test set.

WER = (substitutions + deletions + insertions) / reference words. CER uses Unicode code points after the same normalisation, excluding spaces. Both can exceed 100%. Normalisation is NFKC, case folding, and Unicode letters/numbers/marks; punctuation is removed. No transliteration, number conversion or spelling correction is silently applied. A correct English word written in Devanagari can still differ from the reference Latin spelling. Publish both strict WER and examples; add a separately labelled equivalence-aware score only after defining its rules without inspecting test errors.

Real-time factor = processing seconds / audio seconds. Specify whether timing includes model loading, caching, other jobs, decoding and diarization. Current Indic timing was collected while other evaluation jobs ran, so it must not support speed superiority claims. Peak process RSS is cumulative and is not Android memory consumption or total system RAM.

## 3. Required next natural-meeting study

Collect consented Hindi, English and Hinglish meetings across rooms, microphone positions, participant counts and noise/overlap levels. Split by speaker/group and recording session before tuning. Keep development and final test audio separate. For a pilot extension, aim for at least ten independent test meetings per language condition, then justify a larger sample size from observed variance; this is a proposed plan, not data already collected.

Two fluent annotators should independently mark verbatim text, language changes, speaker activity including overlap, explicit decisions, action ownership/deadlines, and slide references. They must not see model predictions while creating references. Resolve disagreements with a third reviewer or documented consensus. Retain pre-adjudication labels to report agreement. Randomise model labels for human comparison.

Influence is subjective: define a rubric for proposal uptake, supporting evidence, revisions and decision contribution. Ask raters to score evidence-backed contributions rather than status, seniority or speaking time. Preserve ties. Evaluate ranking against independent human ratings with Spearman/Kendall; compare speaking-time-only and word-count baselines. Report rater agreement and bootstrap confidence intervals by meeting, not by correlated transcript word. Do not label heuristic scores as causal influence.

For event/decision extraction, document class definitions, one-to-one matching and timestamp tolerance. Report precision, recall and F1 by class and language, plus macro/micro summaries. Alignment needs real slide timestamps or independent annotated slide IDs. Decision lineage needs reference nodes and relations. Missing annotation fields must remain null/unavailable; empty lists mean the annotator actively found no events and are not equivalent to missing labels.

## 4. Annotation template

`annotation_template.json` contains null reference fields deliberately. Copy it per meeting, fill only independently annotated fields, and retain consent/annotator provenance separately. See the metric docstrings in `src/evaluation/metrics.py` for exact accepted schemas. Speaker turns use `{start, end, speaker}` in seconds; transcript truth is a string. Use stable IDs for events and graph relationships. Do not infer speaker IDs from the system's clusters without independently aligning identities.

## 5. Ablation interpretation

The calibrated-vs-default clustering experiment has reference DER and is the measured ablation in the paper. The eight downstream variants are executable sensitivity analyses: full system, no PPT, no temporal alignment, no semantic alignment, no evidence features, no interaction features, no decision-impact features, and speaking-time baseline. The 42-minute recording lacks human rankings. Its ablation outputs therefore have unavailable ranking metrics. They show changes in scores under removed components, not proof that a component improves influence accuracy. Review speaker fragmentation before interpreting any participant result.

## 6. Professor instructions mapped to deliverables

| Requirement | Deliverable / action |
|---|---|
| Springer MTAP manuscript | `RESEARCH_PAPER.md`, editable `.docx`, legacy `.doc`, PDF preview |
| Around 10–15 relevant recent papers | Fifteen related works: eleven from 2023–2025 plus foundational system/dataset sources; source links and numbered references |
| Comparison table | Table 1 compares tasks, presentation/decision scope and local-processing relevance; unspecified features are not asserted absent |
| Novelty | Section 2 states engineering contributions and explicitly limits novelty claims |
| Small ablation | Threshold calibration with separate development/test meetings, Table 2 and Fig. 4 |
| Supported claims only | Pilot scope, raw JSON and unmeasured metrics stated explicitly |
| Citations starting at [1] | Numbered references, CALO first |
| No citations in abstract/results/conclusion | Manuscript keeps references in introduction, related work and methods |
| Reference every figure/table | Body introduces Table 1, Table 2, Table 3, Figs. 1–6 |
| Short captions | Caption text separate from explanatory prose |
| Implemented/tested focus | Limitations and future evaluation separated from completed implementation |

The journal's current [submission guidance](https://link.springer.com/journal/11042/submission-guidelines) asks for editable source, a 150–250 word abstract, 4–6 keywords and declarations. It does not supply a mandatory Word template. The Word file here is a review draft, not publisher approval. Verify the journal requirements again at submission.

## 7. Before submission

- Replace author, affiliation, corresponding-email and optional ORCID placeholders with verified details.
- Read and verify every cited paper, especially before claiming priority over prior work. The literature review is a starting point, not a patent search.
- Review all results against raw JSON. Keep failed or unavailable measurements visible and do not convert error rates into an unsupported overall “accuracy.”
- Supply truthful funding, conflicts, consent/ethics and data/code availability statements. Do not invent an ethics approval number.
- Disclose AI assistance as required by the journal/institution; human authors remain responsible for methods, code, claims and citations.
- Obtain consent before sharing private audio, transcripts, PPTs or downstream ablation artifacts. The public paper contains aggregate diagnostics, not private meeting excerpts.
- Expand evaluation and revise the paper's conclusions before claiming deployment reliability. User testing and independent human annotations cannot be completed by automated unit tests.
