"""Publish the frozen continued-development experiment alongside the original pilot."""
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.utils.cache import atomic_json


def f1(counts):
    tn, fp, fn, tp = np.asarray(counts).sum(axis=0)
    return 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.


def paired_interval(old, new):
    groups = sorted({row['meeting'][:-1] for row in old})
    assert set(groups) == {row['group'] for row in new}
    before = np.array([np.sum([r['confusion_matrix_tn_fp_fn_tp'] for r in old
        if r['meeting'][:-1] == group], axis=0) for group in groups])
    after = np.array([next(r['confusion_matrix_tn_fp_fn_tp'] for r in new
        if r['group'] == group) for group in groups])
    rng = np.random.default_rng(42)
    draws = []
    for _ in range(3000):
        indices = rng.integers(0, len(groups), len(groups))
        draws.append(f1(after[indices]) - f1(before[indices]))
    return {'unit': 'meeting/project series', 'groups': groups, 'draws': 3000, 'seed': 42,
        'descriptive_f1_delta_interval': np.quantile(draws, [.025, .975]).tolist(),
        'warning': 'Only three independent historical test series; not a significance claim.'}


def table(rows):
    result = '| Method | Precision % | Recall % | F1 % | AP % |\n|---|---|---|---|---|\n'
    for name, scores in rows:
        result += '| ' + name + ' | ' + ' | '.join(f'{100*scores[k]:.2f}'
            for k in ['precision', 'recall', 'f1', 'average_precision']) + ' |\n'
    return result


def build():
    folder = ROOT / 'professor_guidelines'
    out = folder / 'evaluation/decision_discussion_v2'
    baseline = json.loads((folder / 'evaluation/decision_discussion/summary.json').read_text())
    data = json.loads((out / 'summary.json').read_text())
    selection = json.loads((out / 'selection.json').read_text())
    old = next(r for r in baseline['models'] if r['method'] == baseline['dev_selected_variant'])
    chosen = next(r for r in data['models'] if r['method'] == data['primary'])
    before, after = old['test'], chosen['test']
    assert sum(before['confusion_matrix_tn_fp_fn_tp']) == sum(after['confusion_matrix_tn_fp_fn_tp']) == 11136
    assert before['positive_support'] == after['positive_support'] == 2481
    delta = {k: after[k] - before[k] for k in ['precision', 'recall', 'f1', 'average_precision']}
    old_fp = before['confusion_matrix_tn_fp_fn_tp'][1]
    new_fp = after['confusion_matrix_tn_fp_fn_tp'][1]
    interval = paired_interval(old['per_meeting'], chosen['test_per_group'])
    atomic_json(out / 'paired_bootstrap.json', interval)
    main_rows = [('Original three-act context', before), ('Dev-selected v2: ' + chosen['method'], after)]
    if data['precision_operating_point']:
        main_rows.append(('V2 precision operating point', data['precision_operating_point']['test']))
    main_table = table(main_rows)
    comparisons = [(r['method'], r['test']) for r in data['models']]
    comparisons.append((chosen['method'] + ' without smoothing (same classifier; dev-tuned threshold)',
                        chosen['unsmoothed_test']))
    with (out / 'comparison.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['method', 'precision', 'recall', 'f1', 'average_precision'])
        for name, scores in main_rows + comparisons:
            writer.writerow([name, *[scores[k] for k in ['precision', 'recall', 'f1', 'average_precision']]])
    excerpt = f'''### 5.5 Continued development with wider context

Table 9 compares the original pilot with a second, frozen development search on the same labels and split. The primary method ({chosen['method']}, C={chosen['C']}, smoothing radius {chosen['smoothing_radius']}, threshold {chosen['threshold']}) was selected exclusively by pooled development F1 before scoring this cohort. It changes historical-cohort F1 from {100*before['f1']:.2f}% to {100*after['f1']:.2f}% ({100*delta['f1']:+.2f} percentage points), precision from {100*before['precision']:.2f}% to {100*after['precision']:.2f}%, and recall from {100*before['recall']:.2f}% to {100*after['recall']:.2f}%. False positives change from {old_fp:,} to {new_fp:,}. The secondary precision operating point is selected on development with a recall floor of 50%; that floor is not guaranteed on new data.

Table 9. Continued development on the historical cohort.

{main_table}
The primary classifier without smoothing, with its threshold reselected on development, scores {100*chosen['unsmoothed_test']['f1']:.2f}% historical F1. Smoothing therefore does not improve this model's historical F1, despite being selected on development; the ablation is retained as a negative result.

The original test results had already informed the decision to investigate false positives and context. This is therefore exploratory continued development, not fresh independent confirmation. Only three independent project series are available. A paired series bootstrap gives a descriptive F1-difference interval of {100*interval['descriptive_f1_delta_interval'][0]:+.2f} to {100*interval['descriptive_f1_delta_interval'][1]:+.2f} percentage points; it cannot establish population significance. Reference text and dialogue-act boundaries remain oracle inputs. All searched variants, per-group errors, frozen selection hashes and the same-classifier smoothing ablation are retained in the supplementary experiment. The models are research artifacts and do not replace the application's explicit-decision rules.

'''
    report = f'''# Decision-discussion improvements — continued development

The original experiment is preserved. This second experiment uses exactly the same reference labels and project-separated train/development/historical-test cohorts. No examples are removed or relabelled.

{main_table}
Primary historical-cohort F1 difference: **{100*delta['f1']:+.2f} percentage points**. False positives: **{old_fp:,} → {new_fp:,}**. Development F1: **{100*old['dev']['f1']:.2f}% → {100*chosen['dev']['f1']:.2f}%**.

## What changed

The fixed search compares current-act word/character features with symmetric context radii of 1, 5, 15 and 40 acts. A separate radius-15 variant adds relative recording position and its square/cube. It uses no meeting identifier, participant role, dialogue-act type or reference decision label as a feature. TF-IDF is fitted on training only. The model remains class-balanced logistic regression. Each configuration selects C, a probability threshold and smoothing radius on development F1. Smoothing averages predicted probabilities over neighbouring acts, never across meetings. This requires offline access to subsequent speech.

The primary variant is **{chosen['method']}**; C={chosen['C']}, context radius={None if chosen['method'] == 'local' else chosen['method'].split('_')[1]}, smoothing radius={chosen['smoothing_radius']}, threshold={chosen['threshold']}. Its model and selection were saved and hashed before the separate historical evaluation invocation. A precision-oriented threshold is also frozen on development for this same model, requiring development recall of at least 50%. It is not chosen on historical-test performance.

## All dev-selected variants and smoothing ablation

{table(comparisons)}
Each feature variant is independently selected on development. The no-smoothing row holds the primary fitted classifier fixed and reselects only its threshold on development; the same raw classifier probabilities are used. The full grid is retained in `evaluation/decision_discussion_v2/dev_search.csv`. This is not an exhaustive factorial study: the position feature is tested only at context radius 15.

Smoothing does not improve the primary classifier's historical F1 ({100*chosen['unsmoothed_test']['f1']:.2f}% without smoothing versus {100*after['f1']:.2f}% with it). The primary selection remains frozen even though another configuration scores better on historical data. Neither the smoothing hypothesis nor the largest context window is consistently superior across cohorts.

![Continued-development comparison](figures/decision_discussion_improvement.png)

Fig. 1. Original versus dev-selected tagging.

## Per-series results for the primary model

| Series | Precision % | Recall % | F1 % | False positives |
|---|---|---|---|---|
'''
    for row in chosen['test_per_group']:
        report += f"| {row['group']} | {100*row['precision']:.2f} | {100*row['recall']:.2f} | {100*row['f1']:.2f} | {row['confusion_matrix_tn_fp_fn_tp'][1]} |\n"
    report += f'''
## Evidence limits

The old test cohort had already been examined before this work. The development search is separated from this round's historical scoring, but that does not make this a new confirmatory test. No final model is selected using historical-test scores. Only three independent test series and two development series exist. The paired project-series bootstrap F1-difference interval is {100*interval['descriptive_f1_delta_interval'][0]:+.2f} to {100*interval['descriptive_f1_delta_interval'][1]:+.2f} percentage points; it is descriptive, not evidence of population significance. Variation across series remains material.

Inputs are human reference transcripts and dialogue-act boundaries. These scores do not establish final-decision extraction, ASR accuracy, speaker attribution, influence ranking, Hindi/Hinglish performance or application accuracy. Outside-span negatives retain the original annotation-completeness assumption. Larger context and smoothing can blur short discussion boundaries. The position-feature variant may rely on scenario-specific meeting structure. Independent full-recording annotation and end-to-end evaluation remain necessary before installation in the application.

## Reproduce

From the project root, after preparing the original pilot's cached rows:

```bash
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 .venv/bin/python scripts/improve_decision_discussions.py
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 .venv/bin/python scripts/improve_decision_discussions.py --evaluate
.venv/bin/python scripts/report_discussion_improvements.py
```

The full protocol, development search, frozen selection, hashes, comparison CSV, per-meeting/group scores and paired bootstrap are in `evaluation/decision_discussion_v2/`. Trained models and row-level predictions are in `.runtime/research-decision-model-v2/`. Training/vectorisation/selection took {selection['train_and_selection_seconds']:.1f} seconds in this run; this is not an inference or end-to-end recording latency benchmark. There were no new dependencies, model downloads, cloud inference or changes to production event extraction.
'''
    (folder / 'DECISION_DISCUSSION_IMPROVEMENTS.md').write_text(report)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 4))
    xs = np.arange(3)
    for offset, values, label, color in [(-.19, before, 'Original', '#7d8c9b'),
                                        (.19, after, 'Dev-selected v2', '#176b87')]:
        bars = ax.bar(xs + offset, [100*values[k] for k in ['precision', 'recall', 'f1']],
                      .38, label=label, color=color)
        ax.bar_label(bars, fmt='%.2f', padding=3)
    ax.set_xticks(xs, ['Precision', 'Recall', 'F1'])
    ax.set_ylim(0, 105)
    ax.set_ylabel('Historical-cohort score (%)')
    ax.set_title('Oracle transcript and act boundaries · exploratory')
    ax.legend()
    fig.tight_layout()
    for suffix in ['png', 'svg', 'pdf']:
        fig.savefig(folder / f'figures/decision_discussion_improvement.{suffix}', dpi=300)
    plt.close(fig)
    return excerpt


if __name__ == '__main__':
    print(build())
