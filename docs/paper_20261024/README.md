# New IEEE manuscript — 24 October 2026

**Approved title:** InfluenceIQ: A Multimodal Framework for Assessing Participant
Contributions to Meeting Decisions.

This is a new influence-centered manuscript. Earlier drafts in
`professor_guidelines/` are preserved. No application model, training run,
pipeline default, recording, or existing experiment was changed to produce it.

## Read and edit

- [InfluenceIQ_comparative_revision.pdf](InfluenceIQ_comparative_revision.pdf):
  updated PDF with expanded comparisons; identical to canonical [paper.pdf](paper.pdf).
- [paper.docx](paper.docx): editable Word companion, with embedded figures and
  full-width diagram/table sections. Pagination depends on the Word processor;
  the PDF is the canonical layout.
- [paper.html](paper.html): self-contained, single-column reading copy.
- [manuscript.md](manuscript.md): authored text with stable reference keys; edit
  this source before rebuilding.
- [paper.md](paper.md): generated numbered-citation reading source.
- [paper.tex](paper.tex): generated LaTeX with equations and embedded bibliography.
- [paper_latex.zip](paper_latex.zip): standalone LaTeX/Overleaf package,
  including IEEEtran, vector figures, and reference files.
- [supplement.pdf](supplement.pdf): complete earlier experiments, training
  provenance, target/version matrix, AI pilot and fixed-score sensitivity.
- [research_package.zip](research_package.zip): local research record with
  derived features, frozen folds, outer predictions, code snapshots and replay.
- [REVISION_RESPONSE.md](REVISION_RESPONSE.md): completed reviewer responses
  and scientific limitations that still require new evidence.

The expanded comparative-analysis build has 15 pages, a 199-word abstract, 10 tables, seven original
figures, four numbered equations, and 23 cited references. The bibliography
catalog also contains one unused entry; unused entries are not printed.

## Expanded results and presentation

- Table IV places the latest **68.93%** combined model first, with descriptive
  intervals, exact winner-set agreement and nonconstant prediction coverage.
- Table V gives paired differences and counts of improved, unchanged and worse
  meetings. Tables VI–VII list all 14 original finalists and 24 later ranking
  pipelines with separate development and historical scores and source versions.
- Table VIII separates nested refitted feature-family ablations from fixed-score
  weight deletions, with each system's own full reference and accuracy changes.
- Table IX lists all 12 supporting discussion/role models and labels their distinct
  F1 targets. The four AI-label pilot methods remain in the supplement.
- Figures 4–7 show matched model results, feature coverage, paired differences and
  the two ablation groups. The architecture is redrawn with application/research
  branches and the supplied-input evaluation boundary.
- [analysis/model_pipeline_inventory.csv](analysis/model_pipeline_inventory.csv)
  lists 61 evaluated methods or variants across tasks and protocols;
  [analysis/development_search_inventory.csv](analysis/development_search_inventory.csv)
  preserves all 121 ranking development-search records, including their parameters.
  These are historical records, not 121 independent evaluation experiments.
- [authors.json](authors.json) records the four authors' named email mappings and
  full shared affiliation. Journal-mode LaTeX uses IEEE's first-page affiliation
  footnote; Word/HTML give named contacts. The guide remains acknowledged.

The latest model has the highest observed mean in the matched 28-meeting
comparison. Neither cross-protocol numerical ordering nor the inconclusive
paired intervals establish that it reliably beats every historical pipeline.
No additional model training was run for this presentation revision.

## Scientific scope

The central question is each person's contribution to meeting decisions and
outcomes. The principal experiment measures GAP **outcome alignment**, a narrower
proxy, using supplied English transcripts and speaker identities. It does not
establish complete audio/slide influence accuracy or causal impact.

The revision adds a protocol-frozen exploratory nested group comparison across
all 28 existing meetings. Combined Ridge reaches 68.93%, participation Ridge
61.79%, and word count 66.55%. The declared paired contrast is 7.14 points,
with a descriptive interval of −1.79 to 17.86 points; a reliable gain is not
established. All corpus groups were already available during development, so
this is not fresh confirmation. Seventy of 84 participants have no contribution
features, and all 537 supplied proposal tags are missed by the fixed rules.
The original 61.11% selected-model versus 63.89% word-count result remains
separate historical evidence. Full negative results and AI-label provenance
are retained in the supplement.

The implemented multimodal branches are shown in the architecture, with the
reference-input evaluation boundary marked. No evaluated slide benefit is
claimed. ASR configuration sweeps, Android UI, and peripheral platform results
from earlier drafts are not used to support the influence claim.

## Reproduce the documents

From the repository root:

```bash
.venv/bin/python docs/paper_20261024/build_revision_figures.py
.venv/bin/python docs/paper_20261024/update_comparisons.py
.venv/bin/python docs/paper_20261024/build_presentation_figures.py
.venv/bin/python docs/paper_20261024/build_paper.py
.venv/bin/python docs/paper_20261024/build_research_package.py
.venv/bin/python docs/paper_20261024/check_paper.py
```

The build uses the installed Python packages, reuses the existing project's Word
renderer, and compiles with the cached local Tectonic binary. No model fitting
is performed by the document build. A machine with ordinary LaTeX can compile `paper.tex` twice with
pdfLaTeX, or upload `paper_latex.zip` to Overleaf. `references.bib` is provided for
future editing; the current PDF uses an embedded bibliography and requires no
BibTeX run.

To independently replay the controlled Ridge comparison from derived features,
without downloading the corpus or starting neural training, run:

```bash
.venv/bin/python docs/paper_20261024/reproduce_controlled.py \
  --output-dir /tmp/influenceiq-replay-NEW
```

Choose a fresh output directory. In the extracted research package, invoke
`reproduce_controlled.py` from its package directory instead. The record uses
NumPy, SciPy and scikit-learn 1.6.1. Regenerating extraction and role diagnostics
requires the original GAP corpus and corresponding project code. The original
analysis runner refuses to overwrite successful results. Its protocol records
seven outer/three inner group folds, four Ridge alphas and no neural epochs.

The Word companion uses readable linear equations; the PDF and LaTeX contain
the canonical mathematical typesetting. Word has structural XML checks;
automatic LibreOffice preview was unavailable in this environment, so its
rendered pagination has not been visually certified.

## Evidence and checks

- [EVIDENCE_AUDIT.md](EVIDENCE_AUDIT.md): exact results, source files, formula
  details, and feature-version boundaries.
- [REFERENCES_VERIFIED.md](REFERENCES_VERIFIED.md): checked primary sources,
  relevance, and remaining bibliographic caveats.
- [figures/README.md](figures/README.md): figure descriptions and input provenance.
- [analysis/protocol.json](analysis/protocol.json): frozen feature source,
  fitting partitions, targets, model settings and exploratory limitations.
- [analysis/results.json](analysis/results.json): coverage, confusion counts,
  paired differences, sensitivity and per-meeting results.
- [analysis/predictions.csv](analysis/predictions.csv): one outer prediction
  per participant for each method.
- [analysis/cases.json](analysis/cases.json): short source-linked examples and
  existing manual role tags, with corpus/code hashes.
- [research_manifest.json](research_manifest.json): checksums for the assembled
  research package. Older plot manifests remain historical records.
- [build_manifest.json](build_manifest.json): source hash, format, counts, and
  first-citation order.
- [validation.json](validation.json): document and measurement validation result.

The PDF has been rendered for visual inspection. Text extraction and font
inspection verify readable content and embedded fonts. Local compiler notes
about initial Times font-shape fallback are distinct from missing glyphs;
the final PDF uses embedded Nimbus Roman and mathematics/figure fonts.

## Author review before submission

The before-revision draft is preserved in
`archive/paper_before_review_revision_20261024.zip`. The preceding presentation
build is separately preserved in `archive/paper_before_visual_revision_20261024.zip`.
The reviewer report refers
to that draft; the response matrix records what changed. The analysis preflight
and serialization-only failures are archived without overwriting successful
results or changing the declared comparison to improve its scores.

This is a complete research draft, not a journal acceptance or a declaration
that the empirical study is ready for a Q1 venue. The largest scientific gap
remains independent validation of actual contribution-to-outcome influence on
fresh, representative meetings.

The author team should review all content and results, agree authorship and
contributions, designate a corresponding author, and supply accurate funding,
institutional ethics/secondary-data determinations, and conflict declarations
required by the chosen venue. Those details were not invented. The author
names, order, affiliation, and emails follow the earlier project records.
Dr. Nivedita Mishra remains acknowledged as faculty guide; she has not been
automatically made a coauthor.

The AI contribution is disclosed, including the assistant-generated pilot
labels. Confirm the target journal's current disclosure requirements. A
public code/artifact archive, DOI, and definitive data-availability statement
have not been created. Existing dataset licenses still apply; the package
does not redistribute private recordings or downloaded corpora.

The professor's original instruction specifies Springer MTAP, but the latest
user instruction explicitly requests IEEE. The new canonical PDF therefore
uses IEEEtran journal mode without claiming a particular journal identity,
received/accepted dates, publisher copyright, or membership status. A selected
venue may require its own template, anonymity policy, page limit, declarations,
or supplementary files. Similarity screening, publisher PDF certification,
external peer review, and venue-specific compliance checks have not been run.

Formatting follows the [IEEE journal authoring guidance](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/authoring-tools-and-templates/)
and [article structure guidance](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-the-text-of-your-article/structure-your-article/).
