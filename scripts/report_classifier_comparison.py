"""Report every matched classifier result, including results above the frozen v2 model."""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.improve_decision_discussions import sha256
from scripts.report_discussion_improvements import paired_interval
from src.utils.cache import atomic_json

NAMES = {'logistic_regression': 'Logistic regression', 'complement_nb': 'Complement Naive Bayes',
         'linear_svm': 'Calibrated linear SVM', 'random_forest': 'Random forest'}


def comparison_table(rows, reference):
    result = '| Method | Features | Precision % | Recall % | F1 % | AP % | Dev F1 % |\n|---|---|---|---|---|---|---|\n'
    for name, feature, row in [('Frozen v2 reference', 'Context ±40', reference)] + [
            (NAMES[r['family']], 'Current act' if r['features'] == 'local' else 'Context ±40', r) for r in rows]:
        result += '| ' + name + ' | ' + feature + ' | ' + ' | '.join(
            f"{100*row['test'][key]:.2f}" for key in ['precision', 'recall', 'f1', 'average_precision'])
        result += f" | {100*row['dev']['f1']:.2f} |\n"
    return result


def build():
    folder = ROOT / 'professor_guidelines'
    out = folder / 'evaluation/classifier_comparison'
    data = json.loads((out / 'summary.json').read_text())
    protocol = json.loads((out / 'protocol.json').read_text())
    selection = json.loads((out / 'selection.json').read_text())
    old = json.loads((folder / 'evaluation/decision_discussion_v2/summary.json').read_text())
    assert sha256(folder / 'evaluation/decision_discussion_v2/summary.json') == protocol['v2_summary_sha256']
    assert sha256(folder / 'evaluation/decision_discussion/summary.json') == protocol['v1_summary_sha256']
    reference = next(r for r in old['models'] if r['method'] == old['primary'])
    chosen = next(r for r in data['models'] if r['method'] == data['primary'])
    assert len(data['models']) == 8
    assert chosen['dev']['f1'] == max(r['dev']['f1'] for r in data['models'])
    intervals = []
    for row in data['models']:
        assert sum(row['test']['confusion_matrix_tn_fp_fn_tp']) == 11136
        assert row['test']['positive_support'] == 2481
        intervals.append({'method': row['method'],
            'f1_difference_vs_frozen_v2': row['test']['f1'] - reference['test']['f1'],
            **paired_interval(reference['test_per_meeting'], row['test_per_group'])})
    atomic_json(out / 'paired_bootstrap.json', intervals)
    primary_intervals = [{'method': row['method'],
        'primary_minus_method_f1': chosen['test']['f1'] - row['test']['f1'],
        **paired_interval(row['test_per_meeting'], chosen['test_per_group'])} for row in data['models']]
    atomic_json(out / 'paired_bootstrap_primary.json', primary_intervals)
    wins = sum(reference['test']['f1'] > r['test']['f1'] for r in data['models'])
    losses = sum(reference['test']['f1'] < r['test']['f1'] for r in data['models'])
    main_table = comparison_table(data['models'], reference)
    outcome = f"The frozen v2 reference has higher historical F1 than {wins} of the eight matched pipelines and lower F1 than {losses}."
    primary_rank = 1 + sum(r['test']['f1'] > chosen['test']['f1'] for r in data['models'])
    tradeoff = f"The development-selected pipeline ranks {primary_rank} of eight by historical F1. Relative to the frozen v2 reference, its precision changes from {100*reference['test']['precision']:.2f}% to {100*chosen['test']['precision']:.2f}%, recall from {100*reference['test']['recall']:.2f}% to {100*chosen['test']['recall']:.2f}%, and average precision from {100*reference['test']['average_precision']:.2f}% to {100*chosen['test']['average_precision']:.2f}%. Higher F1 therefore does not imply improvement on every metric."
    methods = '''### 4.3 Matched classifier comparison

A subsequent fixed search compares logistic regression, Complement Naive Bayes, a linear SVM and random forest, each using either current-act word/character TF-IDF or those same features plus context within 40 neighbouring acts on each side. All families reuse the same train-fitted vocabulary and IDF. Three prespecified model parameters, smoothing radii 0/5/15, and thresholds from 13 fixed development-score quantiles plus 0.5 are searched for each pipeline. Duplicated thresholds are removed. Every pipeline selects by pooled development F1; all eight are evaluated after model/selection hashes are frozen. The previously frozen v2 model is an additional reference, with its earlier search budget disclosed separately.

The linear SVM uses sigmoid calibration with three project-separated training folds and a final fit on all training rows. The vocabulary/IDF is shared across these inner training folds, but no development or historical-test text fits the representation. Class balancing uses class weights for the linear models, sample weights for Naive Bayes, and balanced bootstrap-sample weights for the forest. Forests use 100 trees and three maximum depths. Equal search counts do not imply equal compute or globally optimal tuning. No complete external meeting-assistant implementation is benchmarked.

'''
    results = f'''### 5.6 Matched classifier comparison

Table 10 reports every model/feature combination from the fixed comparative search. The new study selects **{NAMES[chosen['family']]} with {'current-act features' if chosen['features'] == 'local' else 'context ±40'}** by development F1 ({100*chosen['dev']['f1']:.2f}%); its historical F1 is {100*chosen['test']['f1']:.2f}%. {outcome} Results therefore support specific task-level comparisons, rather than a claim that the complete InfluenceIQ pipeline outperforms all alternatives. The selected method is not changed to the highest historical-test scorer.

Table 10. Matched classifier and feature comparison.

{main_table}
{tradeoff}

The same 11,136 acts and 2,481 positives are scored for every row. Historical scores use oracle reference transcripts and dialogue-act boundaries on the previously examined cohort. Only three test project series and two development series are available. Project-series paired bootstrap diagnostics, per-meeting scores, all search candidates and timing scope are retained in the supplementary comparison. Differences are descriptive and require fresh independent confirmation.

'''
    report = f'''# Comparative classifier analysis

This study trains four classifier families with two feature conditions each. It preserves the previous model and reports every result, including alternatives that beat it. Model selection uses development data; the existing historical cohort is scored only after this round's settings are frozen.

{main_table}
**Development-selected pipeline:** {chosen['method']}. Development F1: {100*chosen['dev']['f1']:.2f}%; historical F1: {100*chosen['test']['f1']:.2f}%. {outcome} A ranking observed on this cohort is not a demonstration of population superiority.

{tradeoff}

## Models and fair comparison

Both feature conditions use the same train-fitted word/character TF-IDF. The wider condition adds the same context-40 representation used by the frozen v2 pipeline. This gives alternatives access to that context rather than reserving it for our preferred method. Each family gets three hyperparameter values, the same smoothing choices, and the same quantile-based threshold selection rule. The frozen v2 reference used the previous development search and is not part of the new matched search budget.

- Logistic regression: C = 0.3, 1, 3; balanced classes.
- Complement Naive Bayes: alpha = 0.1, 1, 10; balanced sample weights.
- Linear SVM: C = 0.3, 1, 3; balanced classes; training-only sigmoid calibration.
- Random forest: 100 trees, minimum leaf size 2, maximum depth 10, 30 or unrestricted; balanced bootstrap-sample weights.

Smoothing radius is selected from 0, 5 and 15 acts. Each candidate's threshold search uses 13 prespecified quantiles of its development scores plus 0.5, removing duplicates. This allows sharply concentrated probability scores to be thresholded rather than advantaging one classifier's probability scale. Pooled development F1 selects each pipeline and the study's primary pipeline; fixed loop order resolves ties. No historical-score-based model replacement is performed.

The SVM calibration uses three project-separated training folds. Vocabulary/IDF remains shared across these inner folds, an unsupervised inner-calibration limitation; it sees no dev/test text during fitting. Calibration groups are recorded in `evaluation/classifier_comparison/calibration_groups.json`. The methods follow the installed scikit-learn 1.6.1 interfaces; see its [sparse-text comparison example](https://scikit-learn.org/1.6/auto_examples/text/plot_document_classification_20newsgroups.html) and [calibration documentation](https://scikit-learn.org/1.6/modules/generated/sklearn.calibration.CalibratedClassifierCV.html). Those examples' datasets and scores are not reused here.

![Matched classifier comparison](figures/classifier_comparison.png)

Fig. 1. Historical F1 under matched feature conditions.

## Runtime scope

| Pipeline | Three-parameter fitting total (s) | One warm classification + smoothing pass (s) |
|---|---|---|
'''
    for row in data['models']:
        report += f"| {row['method']} | {row['fit_grid_seconds']:.3f} | {row['classification_and_smoothing_seconds']:.4f} |\n"
    report += f'''
Fitting totals cover all three parameter fits for each pipeline. SVM totals include its grouped calibration and final training. They exclude shared text transforms, model selection/scoring overhead and artifact I/O. A single warm classification pass is descriptive; it is not a repeated controlled latency benchmark. Shared train/dev text transformation took {selection['shared_transform_seconds']:.2f}s; historical-test transformation took {data['shared_test_transform_seconds']:.2f}s. These are classifier experiments, not full recording processing timings.

## What can be claimed

Report exact task, cohort, metric, feature condition and selected configuration with each comparison. {outcome} The complete meeting application, ASR, diarization, presentation alignment, influence rankings and Hindi/Hinglish recognition were not compared by this experiment. These are common classifier implementations on our task, not replications of published decision-extraction systems or commercial meeting assistants.

The old historical cohort had already informed previous development. This is an exploratory comparative extension, even though this round freezes selections before scoring. All rows use the same 12 meetings from only three independent project series; the 11,136 acts are not independent observations. Outside-span negatives keep the original annotation-completeness assumption. Human reference text and act boundaries are oracle inputs. A new independently annotated evaluation cohort is necessary for confirmatory claims. These models were research artifacts at comparison time; the subsequent learned-review integration is reported separately in `PIPELINE_IMPROVEMENTS.md`.

## Paired uncertainty against the frozen reference

| Pipeline | F1 difference (percentage points) | Descriptive paired-series interval |
|---|---|---|
'''
    for row in intervals:
        lo, hi = row['descriptive_f1_delta_interval']
        report += f"| {row['method']} | {100*row['f1_difference_vs_frozen_v2']:+.2f} | {100*lo:+.2f} to {100*hi:+.2f} |\n"
    report += '''
These 3,000-draw bootstrap diagnostics resample the same project series in each pair. With only three independent groups and multiple descriptive comparisons, they do not establish significance. They must not be interpreted as act-level confidence intervals.

Paired differences between the new primary pipeline and every matched alternative are also retained in `evaluation/classifier_comparison/paired_bootstrap_primary.json`.

## Reproduce

After preparing the original pilot and v2 train-fitted vectorizers:

```bash
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 .venv/bin/python scripts/compare_discussion_models.py
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 .venv/bin/python scripts/compare_discussion_models.py --evaluate
MPLCONFIGDIR=/tmp/influenceiq-mpl .venv/bin/python scripts/report_classifier_comparison.py
```

The protocol, complete development search, frozen selection, comparison CSV, source/model hashes and per-group/meeting scores are in `evaluation/classifier_comparison/`. Trained models and row-level predictions are in `.runtime/research-classifier-comparison/`. No additional dependencies or model downloads are required.
'''
    (folder / 'CLASSIFIER_COMPARISON.md').write_text(report)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 4))
    families = list(NAMES)
    xs = np.arange(len(families))
    for offset, feature, label, color in [(-.2, 'local', 'Current act', '#7d8c9b'),
                                         (.2, 'context_40', 'Context ±40', '#176b87')]:
        values = [100*next(r['test']['f1'] for r in data['models']
            if r['family'] == family and r['features'] == feature) for family in families]
        bars = ax.bar(xs + offset, values, .4, label=label, color=color)
        ax.bar_label(bars, fmt='%.2f', padding=3)
    ax.axhline(100*reference['test']['f1'], color='#b25532', linestyle='--', label='Frozen v2 reference')
    ax.set_xticks(xs, ['Logistic regression', 'Complement NB', 'Calibrated SVM', 'Random forest'])
    ax.set_ylabel('Historical-cohort positive-class F1 (%)')
    ax.set_ylim(0, 100)
    ax.set_title('Oracle inputs · all models selected on development · exploratory')
    ax.legend(loc='upper right')
    fig.tight_layout()
    for suffix in ['png', 'svg', 'pdf']:
        fig.savefig(folder / f'figures/classifier_comparison.{suffix}', dpi=300)
    plt.close(fig)
    return methods, results


if __name__ == '__main__':
    print(build()[1])
