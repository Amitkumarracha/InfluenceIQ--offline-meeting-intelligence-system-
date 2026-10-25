# Current main-paper figures

All seven current figures have vector PDF, editable SVG and raster PNG exports.
They are placed across both columns to keep labels readable in IEEE journal mode.

| Figure | File stem | Content / input |
| --- | --- | --- |
| 1 | architecture | Implemented audio/optional slide pipeline, supplied GAP input boundary, participant features, separate application and research outputs |
| 2 | trace_examples | Three source-checked GAP role cases; analysis/cases.json |
| 3 | nested_design | Seven outer and three inner complete-meeting folds; analysis/protocol.json |
| 4 | controlled_results | All seven matched methods, including 68.93% combined Ridge, and descriptive intervals |
| 5 | feature_coverage | Active participants/meetings, counts and percentages for seven categories |
| 6 | paired_differences | Three within-meeting paired contrasts and descriptive intervals |
| 7 | ablation_results | Refitted 6/7/13-input Ridge comparison and separate fixed-weight deletions |

Numerical plots use frozen analysis/results.json. Main figures do not imply a
fresh test, verified adoption, causal influence or evaluated slide benefit.
The two ablation panels use different full references and interventions.

From the repository root, run in this order:

```bash
.venv/bin/python docs/paper_20261024/build_revision_figures.py
.venv/bin/python docs/paper_20261024/update_comparisons.py
.venv/bin/python docs/paper_20261024/build_presentation_figures.py
```

The first script creates cases/design and an earlier controlled plot; the last
script replaces that plot and architecture and creates the three added graphs.
It does no training. presentation_manifest.json records numerical input and
script hashes. Earlier gap_results, exploration and evaluation_design figures
and their CSVs/manifests remain historical artifacts and are not current figures.
Do not rerun build_figures.py after these scripts: it would replace architecture
with the previous drawing.
