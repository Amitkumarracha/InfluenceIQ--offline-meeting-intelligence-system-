# IEEE manuscript: format and reproduction

The main manuscript has been rewritten as **InfluenceIQ: Offline Decision-Discussion Detection with Source-Linked Meeting Review**. It uses a standard IEEE **conference** layout because a specific conference or journal has not been selected. The user's IEEE-format request takes precedence over the earlier MTAP draft instructions. The previous expanded manuscript remains in `RESEARCH_SUPPLEMENT.*`; raw experiments and negative results remain in their original supplements.

## Files

- `RESEARCH_PAPER.md`: authored manuscript; edit this source first.
- `RESEARCH_PAPER.tex`: generated LaTeX using `\documentclass[conference,a4paper]{IEEEtran}`.
- `RESEARCH_PAPER.pdf`: canonical typeset paper, compiled with IEEEtran.
- `RESEARCH_PAPER.docx`: editable Word version with a full-width title/author block followed by two columns, Times New Roman styles, A4 geometry, numbered headings and embedded figures. Word pagination depends on installed fonts and can differ from LaTeX.
- `RESEARCH_PAPER.doc`: legacy Word companion generated from the editable Word file.
- `RESEARCH_PAPER.html`: self-contained reading copy with embedded figures and a two-column desktop layout.
- `IEEEtran.cls`: unmodified class from CTAN; original support and license information is retained in the file and `templates/README`.

The rewritten paper contains seven numbered sections, a single-paragraph abstract, five index terms, four numbered tables, two figures, two displayed equations and fifteen references ordered by first citation. The initial implementation report's thirteen overlapping result tables and eight figures remain in the supplement. No experiment was rerun, removed or relabelled for this formatting change.

## Build

From the project root:

```bash
MPLCONFIGDIR=/tmp/influenceiq-mpl OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 \
  .venv/bin/python scripts/build_ieee_paper.py --pdf
.venv/bin/python scripts/check_ieee_paper.py
```

The local compiler is pinned to Tectonic 0.15.0 under `.runtime/ieee-tools/tectonic`. Its initial build downloads standard TeX packages/fonts; subsequent builds reuse the compiler cache. No system package installation is required. To compile on another machine with a standard TeX installation, run `pdflatex RESEARCH_PAPER.tex` twice inside `professor_guidelines/`, with the included IEEEtran class and `figures/` assets present. The `scripts/build_research_documents.py` package build regenerates the supplementary reader formats and then calls the IEEE renderer; it preserves the authored main Markdown instead of replacing it with the older report.

Checks in `scripts/check_ieee_paper.py` compare every table with saved measurements, check citation order and layout structure, verify embedded Word figures, and inspect PDF text/fonts. The original application regression results remain separate from document validation.

## Author details and remaining input

The supplied project-cover screenshot, `Screenshot_20261019_231611.png`, identifies the authors in this order: Anushka Chatterjee (23070126015), Amitkumar Racha (24070126501), Sahil Awatramani (23070126112) and Shriyans Sahoo (23070126125). Their affiliation is the Department of Artificial Intelligence & Machine Learning, Symbiosis Institute of Technology, Pune, Pune 412115, Maharashtra, India; institutional website: https://www.sitpune.edu.in/. The work is a B.Tech project by Group 12 in academic year 2026–27.

Dr. Nivedita Mishra is credited as faculty guide in the author-area guidance line and acknowledgment. The screenshot lists her under guidance, so she has not been automatically added as a coauthor. Student identifiers, degree, group and academic year are retained in the acknowledgment rather than crowding the IEEE author-name line. The user supplied these contact emails:

| Name | Email |
| --- | --- |
| Anushka Chatterjee | anushkac2311@gmail.com |
| Amitkumar Racha | rachaamitkumar@gmail.com |
| Sahil Awatramani | sahilawatramani@gmail.com |
| Shriyans Sahoo | shriyanssahoo2005@gmail.com |
| Dr. Nivedita Mishra, faculty guide | nivedita.mishra@sitpune.edu.in |

No corresponding author has been designated and no ORCID was supplied. Funding, contribution and applicable consent/ethics statements still need author confirmation. AI assistance remains disclosed in the acknowledgment.

A selected venue can impose its own page limit, anonymity policy, paper size and required declarations. IEEE PDF eXpress certification and a plagiarism/similarity check have not been performed. The new format does not resolve the study's independent-evaluation gaps or establish broad superiority.

## Format sources

- [IEEE conference template guidance](https://cai.ieee.org/2025/manuscript-templates-for-conference-proceedings/).
- [IEEE Author Center: paper structure](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/structure-your-paper/).
- [IEEEtran distribution](https://ctan.org/pkg/ieeetran).

The official Word-template download returned an empty response, so the Word version is generated with matching conference geometry and styles. The canonical PDF uses the actual IEEEtran class. No IEEE logo, conference name, copyright assignment or acceptance statement is added.
