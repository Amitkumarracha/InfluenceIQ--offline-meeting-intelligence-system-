# InfluenceIQ — MAI presentation

**25 October preparation:** start with the [one-page rehearsal card](PRESENTATION_ONE_PAGE_20261025.pdf), then the [current spoken script, backend/frontend reference, and 80 viva answers](PRESENTATION_CRASH_PACK_20261025.pdf). Editable sources: [rehearsal card](PRESENTATION_ONE_PAGE_20261025.md) and [full preparation pack](PRESENTATION_CRASH_PACK_20261025.md). These handouts retain historical metric scopes and incorporate the latest 656-test website validation; the existing slide deck is unchanged.

The final PowerPoint has **exactly 18 slides**, with **no backup slides**. Headings and slide order match the teammate's original PPT. The cover follows the supplied reference and reads **MAI Project AY 2026–27**.

- [Final PowerPoint](InfluenceIQ_ESE_Final.pptx) — editable text, tables, result chart and detailed architecture; notes on all 18 slides.
- [Final slide PDF](InfluenceIQ_ESE_Final.pdf) — 18 pages, for offline display and sharing.
- [Cover preview](COVER_PREVIEW.png).
- [Presenter guide PDF](PRESENTER_GUIDE.pdf) · [Markdown](PRESENTER_GUIDE.md) — scripts, handoffs, viva answers and contacts.
- [Detailed architecture PowerPoint](Architecture_Detailed.pptx) · [PDF](Architecture_Detailed.pdf) · [SVG](Architecture_Detailed.svg) · [PNG](Architecture_Detailed.png).
- [Review and changes](REVIEW_AND_CHANGES.md).

| Presenter | Slides | Speaking time | Focus |
| --- | --- | --- | --- |
| Anushka Chatterjee | 1–4 | 2:45 | Cover, introduction, problem and objectives |
| Amitkumar Racha | 5–8 | 3:40 | Plan, literature, gap and architecture |
| Sahil Awatramani | 9–12 | 3:45 | Requirements, technology, detector and implementation |
| Shriyans Sahoo | 13–18 | 3:50 | Testing, outcomes, conclusion and references |

The speaking plan takes 14 minutes, leaving one minute for transitions within the requested 15-minute slot. Speaking blocks are suggestions, not implementation-ownership declarations. All four names and student identifiers appear on the cover; supplied email addresses are retained in its notes and the presenter guide.

Slide 8 retains the full editable architecture. Slides 14–15 retain the matched discussion comparison and speech/speaker results. Extra appendix slides and repeated explanations have been removed. Detailed experiments remain in the research report and explanatory notes. Reported metrics are labelled by task and cohort; no overall project accuracy is invented.

Slide 17 contains selected references; all 15 full entries remain in its notes and the paper. Slide 18 retains the original **Photograph of the Presentation** heading and has a clearly labelled slot for the real post-event photograph. It takes no speaking time. For questions, return to the conclusion on slide 16, architecture on slide 8, or results on slide 14.

The [original rough deck](InfluenceIQ_ESE_Presentation.pptx.pptx) is preserved. The plan uses documented completed phases rather than invented month-by-month dates.

## Rebuild and verify

From the repository root, using the existing environment:

```bash
.venv/bin/python presentation/build_presentation.py
libreoffice -env:UserInstallation=file:///tmp/influenceiq-presentation-final --headless --convert-to pdf --outdir presentation presentation/InfluenceIQ_ESE_Final.pptx presentation/Architecture_Detailed.pptx presentation/PRESENTER_GUIDE.html
pdftoppm -singlefile -scale-to 2400 -png presentation/Architecture_Detailed.pdf presentation/Architecture_Detailed
pdftoppm -f 1 -l 1 -singlefile -scale-to 1600 -png presentation/InfluenceIQ_ESE_Final.pdf presentation/COVER_PREVIEW
.venv/bin/python presentation/validate_presentation.py
```

The build uses existing python-pptx, Pillow and Markdown-It packages, plus Noto Sans and Noto Serif fonts. LibreOffice and Poppler create and check the exports.

[Validation](validation.json) checks the 18-slide limit, original heading order, MAI label, text bounds and rendered text retention, notes, timing, absence of obsolete slide links, metric consistency and [source hashes](source_manifest.json). All 18 rendered slides were visually reviewed. The recorded 597-test application run was not repeated for these document changes.

Before presenting, rehearse with all four members and check the physical projector and live audio output. Add the actual presentation photograph after the session.
