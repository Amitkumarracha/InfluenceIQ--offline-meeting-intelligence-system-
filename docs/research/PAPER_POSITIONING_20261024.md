# Paper positioning after the experimental review

Review date: 24 October 2026. This is a writing decision memo, not a new
experiment or a claim of submission readiness. It updates the research focus of
the older [journal blueprint](12_JOURNAL_PAPER_BLUEPRINT.md).

## Approved paper title

**InfluenceIQ: A Multimodal Framework for Assessing Participant Contributions
to Meeting Decisions** is the user's subsequently approved title. It replaces
the earlier title-preservation instruction for the new paper package. Previous
submitted project reports retain their historical titles.

## Central question and defensible position

Center the paper on evidence-linked assessment of participants' contributions
to meeting decisions, and the empirical limits of estimating outcome influence
from participation and automatically extracted contribution proxies.

Main question: **How well do source-linked decision-contribution estimates
reflect participants' alignment with meeting outcomes, compared with simple
participation baselines?**

The intended application asks whose ideas, evidence or objections shaped a
decision. The current quantitative study measures a narrower outcome-alignment
proxy. Keep these constructs distinct throughout. GAP group members are not
necessarily formal presenters; transfer to presentation-led meetings remains
unvalidated.

The strongest supported paper is an interpretable system and exploratory
empirical study. Current results do not support a superior influence predictor,
causal attribution, or a demonstrated multimodal improvement in influence.
Source references make estimates inspectable; they do not establish that the
relationships or explanations are semantically correct.

## Evidence reviewed and its role in the manuscript

| Evidence | Observed result | Manuscript role |
| --- | --- | --- |
| Source-linked events, evidence, decision reconstruction and seven-feature contribution score | Implemented; prototype weights remain unvalidated | Main method, with exact rules and limitations |
| Initial GAP experiment | Development-selected structure Extra Trees: 61.11% historical pairwise accuracy; word count: 63.89%; prototype: 52.78% | Main quantitative comparison |
| Initial GAP uncertainty | Primary 95% meeting-bootstrap interval: 33.33–83.33%, only six evaluation meetings | Report uncertainty and limited generalization |
| Initial combined-feature Extra Trees | 66.67% historical pairwise accuracy, but not the development-selected primary | Report transparently as another candidate, not a replacement primary |
| Later model/feature experiments | Semantic uptake, learned roles, topics and XGBoost did not establish improvement; latest XGBoost 50.00%, contextual-role fixed score 38.89% | Compact exploratory comparison; full trials in supplement |
| Discussion classifier | Existing blend: accuracy 68.62%, F1 53.54%; neural alternative F1 46.32% | Secondary component result, not influence accuracy |
| AI outcome-link pilot | 50 included AI-labelled pairs; paired model agreement 54.55% on 11 historical pairs versus majority 63.64% | Optional exploratory subsection or supplement; never human ground truth |
| Audio and slide implementation/diagnostics | Separately scoped recognition and alignment checks; no matched slide/no-slide influence study | Architecture and supporting evidence, not multimodal influence superiority |
| Attribution correctness fixes | Preserve secondary proposals, correct evidence direction, remove unsupported adoption bonus | Describe current implementation; no measured gain claimed |

GAP uses reference English transcripts and supplied speaker identities. Its
Absolute Individual Influence target compares pre-discussion individual item
rankings with the final group ranking. This is not an independently rated
contribution-to-decision reference. Neither GAP numbers nor discussion F1 are
complete audio-to-influence accuracy.

The first GAP evaluation was frozen before scoring. Later experiments reused
those groups after their results had been seen and must be labelled exploratory.
Older runs have different feature versions; cite their preserved source
snapshots rather than representing every number as the current application.
The earlier research-upgrade summary predates the completed AI pilot; use the
pilot's own report for that experiment's final status.

## Research questions and contributions

1. How can contribution estimates retain an inspectable path to utterances,
   speakers, optional slide matches and candidate decisions? Describe the
   implemented representation; do not equate traceability with correctness.
2. Do these estimates and learned alternatives outperform participation
   baselines on independent outcome-alignment labels? The selected model did
   not outperform word count in the small GAP evaluation.
3. What failure patterns limit the approach, and do better intermediate role
   predictions transfer to better participant rankings? Separate observed
   errors and measured results from hypotheses about their causes.

Potential contributions are the concrete source-linked system design, the
reproducible group-separated comparison, and a documented diagnostic account
of unsuccessful extensions and attribution errors. Their novelty must be
established against related systems; integration alone does not establish a
new research method. Do not claim to introduce meeting influence analysis as
a new task.

## Manuscript structure and emphasis

Use: introduction; focused related work; task and target definitions; method;
datasets and evaluation protocol; results; error analysis and discussion;
limitations and ethics; conclusion. Include reproducibility and data
availability according to the eventual journal's format.

Keep the main narrative on contribution estimation and its validation. Explain
ASR, diarization and optional slide alignment sufficiently to understand inputs
and error propagation. Put detailed deployment/UI features, unrelated audio
configuration studies and complete model grids in supplementary material when
relevant. Do not use application screenshots as evidence of model accuracy.

Core figures: a source-to-contribution pipeline with the evaluated transcript
boundary marked; historical per-meeting method comparisons; and an actual
source-referenced decision example with inferred links and uncertainty clearly
identified. AI-reviewed examples must retain that provenance.

## Write in this order

1. Build the claim/result table from the frozen artifacts. Record each target,
   metric, cohort, baseline, input conditions, feature version and limitation.
2. Draft task definitions, datasets, protocol and methods. State exactly what
   is scored and how ties, absent speakers and missing evidence are handled.
3. Draft results and error analysis, including the baseline that won and
   unsuccessful alternatives. Distinguish original selection from exploration.
4. Complete a focused related-work comparison, then write the introduction
   around the specific supported contribution.
5. Write abstract and conclusion after the claims and tables are fixed.

Suggested opening idea, to develop with literature citations:

> Assessing individual contributions to a meeting requires examining how
> proposals, evidence and objections relate to its decisions. We study an
> offline pipeline that retains source references for these contribution
> estimates and compare its participant rankings with simple participation
> baselines on a group-decision corpus. Our evaluation examines both the
> usefulness and limitations of these estimates as proxies for outcome influence.

## What would strengthen a later submission

The current evidence is suitable for an honest exploratory manuscript draft.
It does not establish a strong Q1 submission or a 75%+ influence result.
The main unresolved need is independent validation of the intended construct:
representative meetings with verified speakers, independently assessed
contribution/outcome links or participant rankings, documented annotation
agreement, and fresh evaluation groups. If claiming a multimodal benefit,
also evaluate matched input conditions with and without slides on that task.
An AI-only annotation pass cannot supply independent human validation.

No additional model search is justified merely to obtain a higher number on
the already examined groups. Model extensions remain hypotheses until a
relevant, independent comparison supports them.

## Sources and local evidence

- [GAP experiment](GAP_INFLUENCE_EXPERIMENT.md).
- [Pipeline and semantic/role findings](INFLUENCE_PIPELINE_FINDINGS.md).
- [Contextual model upgrade](CONTEXTUAL_INFLUENCE_UPGRADE.md).
- [AI outcome-link pilot](AI_OUTCOME_PILOT.md).
- [Presenter influence study](PRESENTER_INFLUENCE_STUDY.md).
- [Submitted project report](../submitted/Multimodal%20AI%20Mini%20Project%20Continuous%20Assessment%204.md).
- [GAP corpus documentation](https://convokit.cornell.edu/documentation/gap.html).
- [Rienks, Nijholt and Heylen, 2007: verbal behavior and perceived meeting influence](https://doi.org/10.1145/1330588.1330589).
- [Mayfield and Black, 2019: stance, outcomes and individual impact](https://aclanthology.org/W19-2108/).

These literature examples establish relevant precedents, not an exhaustive
related-work review or a matched numerical comparison with this project.
