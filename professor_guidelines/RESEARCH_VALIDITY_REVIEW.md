# Why the current paper is weak: evidence audit

Reviewed the complete manuscript, saved predictions, baseline/ablation outputs, scoring code and feature vectors. The central problem is a mismatch between the intended research claim and the evidence. Several experiments also have validity problems. Adding plots does not resolve these.

## 1. The proposed influence method collapses to an existing baseline in the reported case

**Confirmed, highest priority.** All six raw features other than decision contribution are zero across the original 139 clusters. Only eight clusters have nonzero decision contribution. Exactly:

`proposed_score(cluster) = 0.15 × B3_decision_event_count(cluster)`

The maximum residual is zero. Therefore the proposed method and this simple baseline have the same ranking, including ties, on this recording. No human labels are needed to establish this mathematical degeneracy. Human labels are needed to decide whether either ranking is useful. The paper currently has no evidence that its additional influence machinery adds value.

Trace: `data/processed/influence/meeting_9af97509bd1a48739b5736accf903a1e_influence.json`; `src/meeting/influence.py:334`; `evaluation/research_validity_audit.json`.

## 2. Two ablation bars measure weight renormalisation, not feature contribution

**Confirmed.** The evidence feature is identically zero, yet A5 changes scores because its 0.20 weight is removed and remaining weights are rescaled. Every score becomes its previous value divided by 0.80. A6 similarly divides scores by 0.95 despite zero interaction contribution. Residuals are zero and below 0.000001 respectively (rounding).

These are uniform rescalings. Neither changes ranking. Mean absolute score-change bars therefore do not demonstrate evidence or interaction usefulness. A7 produces zeros because it removes the only active feature. It proves the algebraic dependence of this particular score, not accurate decision influence.

Trace: `src/meeting/influence.py:760`; `evaluation/ablation_sensitivity.csv`; audit residual checks.

**Action:** move these plots to diagnostics/appendix, or replace them with controlled studies where each removed feature is active, reference outcomes exist, and the same scorer/protocol is used. Report fixed-weight deletion and renormalised deletion separately if score magnitudes matter. Do not change production weights merely to obtain attractive results.

## 3. The temporal ablation has no temporal input

**Confirmed.** All 34 uploaded slides lack start/end timestamps. Removing a temporal component that had no usable signal is not an informative component experiment. Six detected events are slide-grounded, but none contributes a nonzero decision-linked slide feature. This explains why removing slides changes some links but not influence.

**Action:** collect actual slide display/change timestamps and independently annotate discussed slides; distinguish “not applicable” from a zero performance delta. Test slide alignment directly before claiming it improves influence. Unknown timing must remain unknown.

## 4. Audio reference coverage needs investigation before interpreting the worst numbers

**Confirmed observation; cause not fully established.** TS3007d uses a clip from 60–180 seconds, but its earliest supplied manual segment starts at 99.5 seconds and first word at 100.08 seconds. The ASR emits coherent introductory text before that. Matching runs later in the clip have a median word-time difference of about 0.05 seconds over 44 matched words, so a large global timing offset is unlikely.

A post-hoc sensitivity diagnostic that excludes the first 39.5 seconds changes calibrated segment-reference DER from 56.01% to 18.41%. This shows the score is highly dependent on that prefix. **It is not a corrected benchmark result.** The standard [BUT/pyannote AMI setup](https://github.com/BUTSpeechFIT/AMI-diarization-setup) explicitly uses whole-recording UEMs. Therefore it would be unjustified to drop the interval just because that improves the score. Audit the audio and the task's intended speech/reference coverage first; alternatively run a newly prespecified window comfortably inside annotation coverage and label it a new experiment.

The current DER reference uses transcriber segments, while the standard setup derives speech from word boundaries and preserves pauses. These are different protocols. Current DER figures are custom pilot scores, not comparable official AMI scores. The [AMI transcription guidelines](https://groups.inf.ed.ac.uk/ami/corpus/transcription.shtml) also describe verbatim disfluencies and forced word alignment, which differ from the speech model's tendency to produce fluent text.

All four selected AMI meetings belong to the **train partition of the referenced BUT/pyannote setup**. They are locally separated for threshold selection, but must not be described as the official benchmark's test set. A pretrained component's exposure to these recordings needs a separate training-data check; exposure is not proven here.

**Action:** pin a published split and RTTM/UEM recipe; verify audio identity, timestamps and annotation coverage; use the official reference construction; then calibrate on development and evaluate on the published test meetings. Preserve current results as an exploratory pilot. Do not retune using the published test set.

## 5. Hinglish WER includes script disagreement as well as recognition errors

**Confirmed examples.** A reference writes `impress`, `window` or `normal` in Latin script while hypotheses often use Devanagari transliterations. Strict WER treats these as different words. The current normaliser removes punctuation/case but does not reconcile scripts. This partly inflates apparent errors, while actual phonetic/lexical errors remain visible in both Hindi and Hinglish. Medium's higher Hinglish CER is genuine under the declared strict scoring rule and cannot be ignored.

The additional four-example test contains only 47 reference words. One short example exceeds 100% WER because insertions are possible; this is mathematically valid but a poor headline about system quality. The first eight Hinglish clips are consecutive lecture excerpts, not a representative meeting sample. Some hypotheses contain neighbouring-sentence text; whether this is a segmentation/reference defect or recognition error needs listening-based adjudication.

**Action:** keep strict WER/CER and add a separately declared, independently specified transliteration/variant-aware evaluation if justified. Freeze equivalence rules before evaluating a new test set. Do not rewrite references to fit predictions. Evaluate more independent speakers, sessions, noise levels and natural meetings.

## 6. The central research outcomes are still unmeasured

The application aims to detect decisions, evidence and influence. Yet there is no independently annotated event/decision/lineage/slide test set and no human influence ratings. Table 7 is output coverage, not an accuracy comparison. The baseline columns marked “unmeasured” are honest but cannot support superiority claims. Clusters are not people; 139→37 does not establish correct attribution. Relabelling a cluster with a person's name does not repair clustering.

**Action:** make core event/decision/evidence accuracy the primary outcome. First evaluate on reference transcripts and verified speakers to isolate NLP errors, then on recognised transcripts to quantify propagation. Rate contributions independently, with ties and inter-rater agreement, before testing influence rankings against speaking-time and decision-count baselines. Existing AMI dialogue/summary annotations can help, but do not assume their label definitions are identical to the project's event taxonomy or to influence.

## 7. Many plots repeat evidence rather than answer new questions

Table 2/Fig. 4 and Table 5/Fig. 7 substantially reuse two recordings. The threshold sweep has two development excerpts. Fig. 8 shows the degenerate score mechanism above. A large metric count makes the paper longer without increasing independent evidence.

**Action:** retain one compact audio diagnostic figure, one direct core-task comparison, one genuine component ablation with reference outcomes, and one measured latency/memory figure under controlled conditions. Place exploratory per-sample diagnostics and algebraic checks in a supplement. Do not plot unavailable metrics as zero.

## 8. The manuscript is still a prototype report, not a complete research argument

The introduction is too short to establish a specific unresolved problem. The novelty paragraph mostly lists integration features and limitations. The comparison table mixes models, datasets and full meeting systems in one two-column list; these are not interchangeable competitors. No research question, primary outcome, justified sample size, uncertainty estimate or independently measured benefit currently establishes the proposed contribution. Wording such as “Like the supplied CALO paper” belongs in working notes, not the submitted manuscript. The score equation is simplified: actual features include bonuses and decision gating, not just plain event counts. Android capabilities are discussed without phone-level evaluation.

I previously prioritised adding metrics and figures too early. That made the document more complete in appearance without resolving these core issues. This review corrects that interpretation; no failed result has been replaced or concealed.

## Recommended order of work

1. **Validate the evaluation data and protocol:** published AMI split/word-derived RTTM/UEM; clip/reference coverage; script conventions; preserve a provenance manifest. Do this before changing recognition models.
2. **Define one defensible primary contribution:** e.g. evidence-backed decision/contribution extraction with local processing. Define what “better” means using independent labels and task-specific metrics.
3. **Separate stages:** reference-transcript/verified-speaker NLP evaluation, recognised-transcript NLP evaluation, then full pipeline. Include the simple decision-count baseline that currently equals the proposed ranking.
4. **Create informative ablations:** ensure removed features are present; record actual slide timings; compare extraction/ranking accuracy, not arbitrary score movement. Include negative findings.
5. **Measure engineering benefits:** isolated cold/warm runtimes, RTF, peak RSS and cache re-attribution latency on the same machine; real-phone tests separately. Current concurrent timing cannot establish speed superiority.
6. **Rewrite the paper around those results:** fewer useful figures, a clear question, methods faithful to code, appropriate baselines, uncertainty and limitations. Do not describe the current draft as Q1-ready.

## Reproduce this review

```
.venv/bin/python scripts/audit_research_validity.py
.venv/bin/python -m pytest -c config/pytest.ini tests/test_research_validity.py -q
```

Machine-readable evidence: `evaluation/research_validity_audit.json`. Original audio scores, source hypotheses, user meetings and model settings are preserved. The prefix-exclusion values are explicitly post-hoc sensitivity diagnostics and must not replace the original scores.
