# Final report files and evidence

The primary submission is [Group12_Multimodal_AI_Final_Report_CA4.pdf](../Group12_Multimodal_AI_Final_Report_CA4.pdf): one cumulative Group 12 report covering CA1–CA4, group names/PRNs, implementation, fusion comparisons and measured results.

The [editable source](../Multimodal%20AI%20Mini%20Project%20Continuous%20Assessment%204.md) is the previously empty CA4 file. [Group12_Complete_CA1_to_CA4_Record.pdf](../Group12_Complete_CA1_to_CA4_Record.pdf) is an optional record: the final report followed by the original Report 1, Report 2, CA3 and individual literature review. Submit the primary cumulative report as the one group report; the combined record is for supporting history if requested.

Six figures are available as PNG and standalone PDF. `evidence/` contains the controlled fixture, per-method outputs, real unlabelled coverage, corrected EDA and processing evidence. `report_manifest.json` records page counts and source/output hashes. `headings.json` records the primary PDF contents pages. `Group12_Final_Report.html` is the local print layout.

The numerical fusion comparison uses temporal-only, semantic-only and combined temporal–semantic alignment, the configurations of the implemented temporal/content components. Section 6 maps them to the actual source code and describes the default application path. Early/intermediate/late architecture taxonomy is compared separately with explicit implementation status. The fixture's labels are author-designed; they are not independent human labels for real meetings. No real influence-ranking agreement or natural Hindi/Hinglish accuracy was fabricated.

Rebuild from the project root with `.venv/bin/python scripts/build_final_report.py`. This uses the existing Markdown parser, Matplotlib, Playwright/Chromium and Poppler tools; it does not install a new PDF service or change app models/settings. To rerun the three-way experiment separately, use `OMP_NUM_THREADS=4 .venv/bin/python scripts/compare_fusion_ca4.py` and review/update the report narrative before rebuilding.
