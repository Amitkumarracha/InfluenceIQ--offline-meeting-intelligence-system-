# Critical reviewer-style assessment of InfluenceIQ

**Historical review:** This assessment concerns the before-revision manuscript.
See `REVISION_RESPONSE.md` and the revised analysis records for changes made in
response; the original assessment is preserved rather than rewritten as approval.

Reviewed: 24 October 2026. Manuscript: **InfluenceIQ: A Multimodal Framework
for Assessing Participant Contributions to Meeting Decisions**. This is a
simulated research review, not an IEEE editorial decision or an acceptance
prediction. The manuscript and experimental outputs were inspected without
changing the paper, models, or application.

## Overall recommendation

**For a research-journal submission, I would recommend rejection in its present
form, with encouragement to resubmit after substantial empirical work.** The
current draft is an honest exploratory prototype study. Its main weakness is
that the intended research question, implemented score, available reference
target, and evaluated input modalities do not yet align closely enough to
establish a substantial validated contribution.

A lower score than word count is not, by itself, a rejection reason. Negative
results can be valuable. Here, however, the small single-task cohort, repeated
historical evaluation, weak construct validation, and incomplete mechanism
analysis also limit the strength of the negative finding.

The 190 passing checks establish document consistency, correct transcription
of saved measurements, valid citations, and successful builds. They do not
certify construct validity, novelty, methodological completeness, or research
quality.

## Critical findings

### 1. The reference target does not directly measure the central construct

**Location:** III-A, especially manuscript.md:69–73; IV-A; VII.

The intended question is whose contributions shaped a decision. GAP AII measures
distance between a person's initial item ranking and the group's final ranking.
An initially aligned but silent member can score favorably on that target.
Consequently, even substantially higher AII-ranking accuracy would not establish
that the system identifies adopted proposals or consequential objections.

The manuscript discloses this distinction accurately, but disclosure does not
validate the intended construct. A reviewer can reasonably conclude that the
paper evaluates a different question from its main motivation.

**Needed:** independent, source-supported contribution/outcome judgments or
participant contribution rankings on representative meetings. Report annotation
agreement, uncertainty, shared credit, and unjudgeable cases. This need not
establish experimental causality; it must at least validate the observational
contribution construct. Keep AII as a separate external proxy comparison.

### 2. The multimodal claim has no matched multimodal outcome evaluation

**Location:** title; III-B, manuscript.md:77–85; VI-B, manuscript.md:295.

Audio processing and slide matching are implemented. The main ranking study
instead supplies English transcripts and speaker identities, and contains no
slides. Therefore neither the effect of audio errors nor the contribution of
presentation information is measured on participant contribution assessment.

The title can describe a framework's capabilities, so it is not automatically
false. Nevertheless, it sets an expectation that the central multimodal aspect
is investigated. Saying that it is outside the evaluation leaves that expectation
unfulfilled.

**Needed:** matched meetings with a verified reference, comparing transcript-only,
transcript-plus-slides, and actual audio-derived conditions. Check slide timing
and relevance separately. Preserve the approved title while marking the
evaluation boundary prominently; wording alone cannot establish a modality gain.

### 3. The incremental research contribution remains weakly demonstrated

**Location:** I, contribution paragraph; II and Table I; VI-A.

The contribution combines established components, transparent heuristics,
source references, and exploratory comparisons. The paper correctly avoids
claiming to invent influence analysis, but does not demonstrate a sufficiently
distinct new inference method, validated resource, user benefit, or robust
empirical discovery to replace that algorithmic novelty claim.

Source links are useful engineering, but their correctness and practical value
are not evaluated. Table I describes neighboring tasks rather than isolating a
specific unresolved capability that InfluenceIQ demonstrably addresses.

**Needed:** make one measurable contribution central. Possibilities include
independently validated contribution-to-outcome attribution, a carefully
evaluated review workflow, or a stronger diagnostic study isolating why aggregate
features fail. A new model architecture is not mandatory; demonstrated research
value is.

### 4. The effective evaluation sample is extremely small and repeatedly used

**Location:** IV-A–D; V-A; VI-C.

The main evaluation contains six meetings and 19 participants. The frozen JSON
contains only **21 comparable within-meeting participant pairs**, and these are
correlated within six meetings, not 21 independent observations. The primary
model's 95% meeting-bootstrap interval spans 33.33–83.33%.

Inspection of the frozen per-meeting scores shows that the primary and word-count
baseline agree in pairwise accuracy on four of six meetings. The primary is
better on one meeting and worse on one. That does not establish a stable
difference in either direction.

Later model development also reuses the historical cohort after inspecting its
results. The paper discloses this correctly, but those comparisons cannot become
fresh confirmation. Ten thousand bootstrap samples do not create additional
independent meetings.

**Needed:** preserve current results as exploratory; use development-only
group-respecting analyses for subsequent choices and reserve new independent
groups for confirmation. Justify sample size using the expected variation and
effect of interest rather than selecting an arbitrary number of meetings.

## Major findings

### 5. The seven-feature method has little demonstrated participant discrimination

**Location:** III-D, Table II; V-A.

The weights and internal bonuses are unvalidated. A proposal can receive credit
merely for appearing in a cluster, regardless of adoption. The objection bonus
requires only a later revision start in the same cluster. Several feature
categories can credit the same event. The decision feature also rewards the
number of a participant's events in a cluster, potentially reintroducing volume.

The prototype produces complete participant ties in five of six evaluation
meetings. Its 52.78% pairwise score is consequently close to the 50% half-credit
result of a constant prediction. That should be analyzed as a coverage and
representation failure, not merely described as a modest prediction score.

**Needed:** a feature-activity/coverage table, missing-speaker and zero-feature
rates, predicted-tie rates, and independently evaluated event/relation quality.
Explain the scoring design and study weight sensitivity on development data.
Adding learned weights to unreliable features alone would not solve the issue.

### 6. The ablations do not isolate the main claimed contribution

**Location:** Table IV; Table V; IV-D; V-B.

The paper compares many models, but does not cleanly establish the value of
decision-linked features beyond ordinary participation variables. The headline
structural model includes words, timing, lexical markers, event counts, and
contribution features. Its behavior could be driven mainly by participation.
Comparing it with the heuristic score does not isolate the contribution features.

The topic toggle is a useful limited diagnostic. It is not a full ablation of
source links, the seven contribution categories, verified outcome relationships,
or the multimodal branch. Models and feature versions also vary across rounds.

**Needed:** controlled participation-only, contribution-only, and combined
comparisons with the same model family, capacity, split, and selection budget.
Distinguish automatic extraction from independently verified input conditions.
Evaluate the slide branch separately when matched data exist. Do not retune
these analyses on the already inspected evaluation groups.

### 7. The described current method and headline evaluated method differ

**Location:** III-C–D; IV-D; Table IV versus Table V.

The method section explains corrected attribution rules, whereas the primary
61.11% result and initial prototype score use earlier source snapshots. The
paper acknowledges this, so it is not a concealed discrepancy. However, readers
must reconstruct which formula, event reconstruction, and feature set belong
to each result. The primary learned Extra Trees model is also different from
the transparent weighted score highlighted in the architecture.

**Needed:** a compact version/method matrix identifying each evaluated system,
feature definitions, source hash, training procedure, and result table. Identify
one canonical implementation for the main methodological description. Retain
historical results with explicit version labels rather than imply that the
headline score evaluates every current feature.

### 8. AI-label agreement cannot validate the proposed relationship task

**Location:** IV-E; V-D, Table VII.

Only 11 historical pairs are evaluated, with labels from one assistant and
purposive selection. The revised class is absent from development and evaluation.
Some outcome inputs are human-written summaries. Thus the pilot neither
validates four-class relationship extraction nor establishes independent human
contribution validity. Group-separated fitting does not remove annotator bias.

Reporting four-class macro F1 with an absent class is a disclosed metric choice,
not a calculation error, but it cannot establish detection of that class. The
paired model also remains below its majority baseline.

**Needed:** independent review, a representative sampling procedure, a documented
rubric and annotation protocol, and meaningful reference coverage of every
claimed class. Until then, present this as an annotation feasibility study or
supplementary pilot. Avoid spending the abstract and substantial main-paper space
on evidence that cannot answer the principal question.

### 9. The central interpretability benefit is not evaluated or demonstrated by a case

**Location:** III-B–D; VI-A; all four figures.

The manuscript repeatedly highlights inspectable sources, yet provides no
worked real-meeting example tracing a participant through an utterance, inferred
relationship, final decision, feature value, and ranking. The figures show
architecture, protocol, and aggregate scores, not the core attribution artifact.
There is also no measurement of source correctness, reviewer effort, or
explanation usefulness.

The decision-level display uses event share multiplied by an unweighted feature
mean, whereas the meeting score uses a weighted sum. These are legitimately
different definitions, but their practical interpretation is not justified or
validated.

**Needed:** one fully sourced success example and one failure example, with
independent review and AI provenance disclosed where relevant. Distinguish a
pointer to evidence from a validated explanation. If usefulness is a main
contribution, evaluate review correctness or effort in an appropriately designed
study. Explain the two score definitions or reduce the emphasis on the
unvalidated decision-level display.

### 10. Method and artifact detail is insufficient for external reproduction

**Location:** III-B–C; IV-D–E; VI-D.

The paper names model families and several ranking settings, but omits important
operational details from the manuscript/supplement: event confidence cutoffs,
evidence/decision/interaction windows, slide fusion settings and missing-time
behavior, and complete neural training settings such as optimizer, learning
rate, batch size, seed, and checkpoint revision. Some are present in local code
or protocol files, but a reviewer does not receive those automatically.

The LaTeX ZIP reproduces the document, not the research experiments. Source
hashes identify an artifact but do not give an external reviewer access to it.
The AI pilot also needs a sufficiently documented annotation process to make
its provenance auditable.

**Needed:** a concise configuration appendix and a shareable, versioned artifact
package containing permitted code, configurations, split IDs, predictions,
evaluation scripts, and annotation metadata. Reference datasets subject to their
licenses rather than redistribute private recordings. Do not promise public
availability before it exists.

## Writing and presentation findings

### 11. The manuscript reads partly as an experiment history

**Location:** III-C; IV-D; V-B–D; VI.

Bug-fix chronology, rejected trials, component training history, and repeated
warnings occupy substantial space. The discussion detector is explicitly a
parallel review aid, so its model comparison has a weak connection to the main
participant-contribution claim. The resulting narrative feels broader than the
evidence supporting the central question.

**Needed:** retain important negative findings, but consolidate chronology and
implementation corrections into the supplement. Move peripheral discussion
classification details and the AI feasibility pilot there unless their role in
answering a main research question is established. Organize the main paper by
research question, experimental comparison, and supported conclusion.

### 12. Related work does not yet establish a precise competitive gap

**Location:** II, Table I.

The references are relevant and include recent work, but Table I mostly explains
why other papers are different tasks. This avoids false comparisons, yet leaves
the closest alternative contribution-assessment approaches underexamined.
Method descriptions and dataset citations also do not substitute for a critical
comparison of attribution mechanisms and validation practices.

**Needed:** focus the comparison on how close approaches define influence,
link evidence to decisions, allocate participant credit, and validate those
links. Clearly separate system papers, datasets, and model components. Reproduce
an applicable baseline only where inputs, labels, and licensing support a fair
comparison; do not copy incomparable published scores into Table IV.

### 13. Several smaller presentation issues reduce clarity

- The abstract foregrounds multiple unsuccessful peripheral experiments before
  establishing one concrete validated contribution. Rewrite after the main
  evidence and claim are settled; do not hide negative results.
- Define the score difference delta(p,q) explicitly as a subtraction in the
  mathematical notation, and identify the evaluable meeting set. The current
  verbal direction convention is understandable but underformalized.
- Label every result row with an unambiguous system/version identifier instead
  of relying on labels such as “earlier source.”
- Report comparable-pair counts and tie/coverage diagnostics next to headline
  ranking percentages. Two decimal places are not evidence of high precision.
- The four figures do not show uncertainty for paired method differences.
  Showing the existing interval and per-meeting paired differences would help
  interpretation, while retaining the warning that six units are inadequate
  for strong inference.
- The PDF is readable, but wide floats can appear apart from the relevant
  method/result discussion. Recheck placement after structural revision.
- Corresponding author, applicable declarations, archival availability, and
  the selected venue's specific template requirements remain unresolved.
  These are submission-completeness issues, not substitutes for empirical work.

## What should be retained

The manuscript reports unfavorable results rather than selecting a convenient
historical winner. It distinguishes development from evaluation, keeps whole
groups together, handles reference and predicted ties explicitly, identifies
AI labels honestly, and separates reference-transcript scores from deployment
accuracy. The PDF, citations, tables, and figures are mechanically consistent.
Those strengths should survive revision.

## Recommended order of repair

1. Settle the operational definition and independent reference for individual
   contribution; keep AII as a separately identified proxy.
2. Pin a canonical implementation and publishable configuration/provenance
   record. Produce source-checked cases and feature-coverage diagnostics.
3. Design a controlled comparison and informative ablations, with fresh groups
   reserved for confirmation and a justified sample-size plan.
4. Evaluate multimodal inputs and actual audio-derived attribution if these
   remain central to the paper's claim and title.
5. Rewrite the contribution statement and main narrative around the demonstrated
   findings; move peripheral pilots and development history to a supplement.

Steps 2 and 5 contain documentation changes that can be made now. Steps 1, 3,
and 4 require additional research evidence; a prose rewrite cannot complete them.
Changing only the classifier or increasing epochs would not fix the main flaws.

## Review basis and limits

Reviewed the current manuscript and PDF, its evidence audit and validation
record, frozen GAP per-meeting results and selection, AI pilot protocols, and
relevant current extraction/configuration code. No new training, participant
annotation, external peer review, plagiarism check, or fresh scientific
evaluation was performed.

General criteria concerning a clear research question, contextualized novelty,
reproducible methods, interpretable results, and restrained conclusions are
consistent with the [IEEE Author Center article-structure guidance](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-the-text-of-your-article/structure-your-article/).
That guidance is not a journal-specific scoring rubric. The recommendation
above is an assessment of this draft's evidence, not an official IEEE decision.
