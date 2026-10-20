"""Report measured discussion-pipeline changes separately from runtime validation."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.report_discussion_improvements import paired_interval, table
from src.utils.cache import atomic_json


def build():
    folder = ROOT / 'professor_guidelines'
    out = folder / 'evaluation/pipeline_improvement'
    data = json.loads((out / 'summary.json').read_text())
    comparison = json.loads((folder / 'evaluation/classifier_comparison/summary.json').read_text())
    forest = next(r for r in comparison['models'] if r['method'] == 'random_forest__context_40')
    linear = next(r for r in comparison['models'] if r['method'] == 'logistic_regression__context_40')
    prior = json.loads((folder / 'evaluation/decision_discussion_v2/summary.json').read_text())
    old = next(r for r in prior['models'] if r['method'] == prior['primary'])
    selected = data['selection']
    rows = [('Earlier v2 context model', old['test']), ('Matched context logistic regression', linear['test']),
            ('Matched context random forest', forest['test']), ('New discussion-review pipeline', data['test'])]
    measured = table(rows)
    uncertainty = paired_interval(forest['test_per_meeting'], data['test_per_group'])
    atomic_json(out / 'paired_bootstrap_vs_forest.json', uncertainty)
    results = f'''### 5.7 Learned discussion review in the pipeline

Table 11 reports a further fixed development search combining the previously trained context forest and linear classifier. Linear mixture weights 0/0.25/0.5/0.75/1, smoothing radii 0/5/15, and the same development-quantile threshold rule are searched; all mixture weights are retained in the supplement. Selection uses development F1 before historical scoring. The selected mixture uses {100*(1-selected['linear_weight']):.0f}% forest and {100*selected['linear_weight']:.0f}% linear scores, smoothing radius {selected['smoothing_radius']} and threshold {selected['threshold']:.6f}. Development F1 is {100*selected['dev']['f1']:.2f}%.

Table 11. Historical discussion-detection results.

{measured}
The new pipeline improves historical F1 over the matched forest by {100*(data['test']['f1']-forest['test']['f1']):.2f} percentage points. A paired three-series bootstrap difference interval is {100*uncertainty['descriptive_f1_delta_interval'][0]:+.2f} to {100*uncertainty['descriptive_f1_delta_interval'][1]:+.2f} points; it is descriptive and does not establish significance. Average precision remains below the earlier v2 and matched linear model, so the result is not a gain on every metric. This is another exploratory iteration on the previously examined cohort.

The selected model is now packaged for the local English discussion-review stage. The complete app runs it on final ASR passages, persists source text/segment IDs/speakers/timestamps and exposes suggested passages in the decision-review screen and JSON/Markdown/HTML reports. Suggested discussion membership does not create final-decision anchors or participant-influence contributions. Missing models and unsupported languages retain an explicit stage status. Real cached ASR smoke checks and pipeline/browser tests establish execution and traceability; the {100*data['test']['f1']:.2f}% score still uses oracle transcript/act boundaries and must not be assigned to recording-level application accuracy.

'''
    report = f'''# Pipeline improvement: learned discussion review

The app now includes a local learned discussion-review stage in addition to its event and final-decision rules. This closes the previous gap between the research classifiers and the running pipeline. The learned stage suggests source passages to inspect; it does not convert discussion membership into confirmed decisions or alter influence weights.

## Measured comparison

{measured}
All rows use the same 11,136 reference acts and 2,481 positives from the historical AMI cohort. This table measures discussion membership with oracle text and act boundaries. It is not end-to-end audio accuracy. The dev-selected mixture combines {100*(1-selected['linear_weight']):.0f}% forest with {100*selected['linear_weight']:.0f}% linear scores, then smooths within ±{selected['smoothing_radius']} acts and applies threshold {selected['threshold']:.6f}. It scores {100*selected['dev']['f1']:.2f}% development F1.

## All prespecified mixtures

''' + table([(f"Linear weight {r['linear_weight']:.2f}", r['test']) for r in data['variants']]) + f'''
For every mixture, its smoothing radius and threshold are selected on development only. The components reuse train-fitted, previously dev-selected context classifiers; this is a further development iteration, not new independent model discovery. Historical scores were inspected only after this round's selection was frozen. Selection/model/source hashes are retained in `evaluation/pipeline_improvement/`.

The forest-versus-new-pipeline paired series bootstrap interval for F1 difference is {100*uncertainty['descriptive_f1_delta_interval'][0]:+.2f} to {100*uncertainty['descriptive_f1_delta_interval'][1]:+.2f} percentage points. Three test series and two development series remain insufficient for strong significance/generalisation claims. Average precision remains lower than the matched linear baseline. No labels or examples were removed or changed.

## What changed in the app

- `src/meeting/discussions.py` performs batched sparse feature extraction and forest/linear scoring locally. Expanded context and feature matrices are bounded to one batch. It preserves source order and never crosses meetings.
- The complete audio-to-report orchestrator runs the learned stage after final transcription/speaker attribution. The preview remains a separate draft path.
- The decision-review screen shows verbatim suggested passages, speaker labels and audio seek buttons. All suggestions remain in report JSON/Markdown/HTML; the screen displays the first 100 for long recordings.
- English-only application is explicit. Mixed detected-language recordings and missing model assets do not receive unsupported learned labels. An optional-stage failure is reported without losing the transcript or other completed analysis.
- Scores are not calibrated correctness probabilities. The classifier's targets are discussion spans, not final decisions. Source-based decision reconstruction and influence weighting therefore remain separate.

## Validation and limits

Unit coverage compares batched runtime features and smoothing against the frozen experiment, checks meeting boundaries and label independence, verifies passage IDs/text/timestamps and tests invalid input/failure behaviour. An orchestrator integration test checks that the new stage reaches JSON/Markdown/HTML exports without inventing decision events. Browser coverage verifies the learned section in the existing workflow.

Real cached ASR transcripts are exercised separately in `evaluation/pipeline_improvement/asr_smoke.json`. These checks measure execution and source traceability only. Short introductory excerpts can yield no suggestions; this is retained rather than forcing positives. The mapping from human dialogue acts to longer ASR passages changes the input distribution and has not been accuracy-validated. Independent ASR-passage/recording annotations remain necessary. Hindi/Hinglish accuracy, final-decision accuracy and human influence rankings are not established by this experiment.

## Model installation and reproduction

The model is installed locally at `models/discussion/model.joblib`, with its provenance in `models/discussion/manifest.json`. Model binaries are ignored by Git. A fresh checkout needs the training/evaluation artifacts before packaging; a checkout without the model reports `model_unavailable` and keeps the existing rule pipeline operational. `discussion_review.enabled` and `discussion_review.model` in `config/config.yaml` control this stage.

```bash
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 .venv/bin/python scripts/improve_discussion_pipeline.py
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 .venv/bin/python scripts/improve_discussion_pipeline.py --evaluate
.venv/bin/python scripts/improve_discussion_pipeline.py --install
MPLCONFIGDIR=/tmp/influenceiq-mpl .venv/bin/python scripts/report_pipeline_improvement.py
```

The installation always packages the frozen development-selected mixture, irrespective of historical ranking. Prior experiment outputs and existing meeting reports are preserved. New analyses produce the additional discussion-review field; existing meetings need reanalysis to obtain it. No dependencies, neural downloads or cloud processing were added.
'''
    (folder / 'PIPELINE_IMPROVEMENTS.md').write_text(report)
    return results


if __name__ == '__main__':
    print(build())
