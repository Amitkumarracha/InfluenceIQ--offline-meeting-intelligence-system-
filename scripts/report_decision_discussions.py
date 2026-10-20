"""Report the frozen NLP pilot without tuning on test results or installing models."""
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.utils.cache import atomic_json


def build():
    folder = ROOT / 'professor_guidelines/evaluation/decision_discussion'
    data = json.loads((folder / 'summary.json').read_text())
    counts = json.loads((folder / 'dataset_counts.json').read_text())
    n = sum(data['models'][0]['test']['confusion_matrix_tn_fp_fn_tp'])
    support = data['models'][0]['test']['positive_support']
    # Add the trivial positive baseline to the saved pilot without retraining.
    if not any(row['method'] == 'always_positive' for row in data['baselines']):
        data['baselines'].insert(0, {'method': 'always_positive', 'test': {
            'precision': support/n, 'recall': 1., 'f1': 2*support/(n+support),
            'positive_support': support, 'average_precision': None,
            'confusion_matrix_tn_fp_fn_tp': [0, n-support, 0, support]}})
    rows = data['baselines'] + data['models']
    table = '| Method | Precision % | Recall % | F1 % | AP % |\n|---|---|---|---|---|\n'
    for row in rows:
        m = row['test']
        values = [f"{100*m[k]:.2f}" for k in ['precision', 'recall', 'f1']]
        values.append(f"{100*m['average_precision']:.2f}" if m['average_precision'] is not None else 'N/A')
        table += '| ' + row['method'] + ' | ' + ' | '.join(values) + ' |\n'
    # Coarsest independent unit is the project series (3 test groups), not individual acts.
    chosen = next(row for row in data['models'] if row['method'] == data['dev_selected_variant'])
    groups = sorted({row['meeting'][:-1] for row in chosen['per_meeting']})
    grouped = np.array([np.sum([row['confusion_matrix_tn_fp_fn_tp'] for row in chosen['per_meeting'] if row['meeting'][:-1] == group], axis=0) for group in groups])
    rng = np.random.default_rng(42); draws = []
    for _ in range(3000):
        tn, fp, fn, tp = grouped[rng.integers(0, len(groups), len(groups))].sum(axis=0)
        draws.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0)
    interval = np.quantile(draws, [.025, .975]).tolist()
    atomic_json(folder / 'bootstrap_diagnostic.json', {'unit': 'meeting/project series', 'groups': groups,
        'n_groups': len(groups), 'draws':3000, 'seed':42, 'descriptive_percentile_interval_f1':interval,
        'warning':'Only three independent test series: this is a coarse uncertainty diagnostic, not a significance claim.'})
    atomic_json(folder / 'summary.json', data)
    with (folder / 'comparison.csv').open('w', newline='') as stream:
        writer=csv.writer(stream); writer.writerow(['method','precision','recall','f1','average_precision'])
        for row in rows:writer.writerow([row['method'],*[row['test'][k] for k in ['precision','recall','f1','average_precision']]])
    text = '''# First supervised decision-discussion experiment

This experiment measures a real NLP task against independent manual decision spans. It is research-only and does not replace the application's rules or validate influence.

Task: classify whether a reference dialogue act belongs to a manually annotated decision discussion. An act is positive when at least 50% of its lexical word IDs are inside annotated decision spans. This detects discussion membership, not final decisions or action ownership. Outside-span acts are assumed negative; annotation completeness requires review.

Inputs are oracle reference text and dialogue-act boundaries. Annotator dialogue-act class labels are excluded from features. Data are separated by project/meeting series: 29 training meetings (20,339 acts), six development meetings (3,739 acts), and 12 test meetings (11,136 acts, 2,481 positive). The test set contains only three independent series. No matching manual decision annotations were found in the official BUT test partition, so this is explicitly a custom group-separated split.

Linear TF-IDF classifiers use current-act word n-grams, character n-grams and neighbouring-act context. C and decision thresholds are selected on development only. All prespecified variants are reported. No generative model, new speech-model download or production model installation was used.

''' + table + '''
The explicit-decision rule is a narrow cue baseline on a broader discussion-membership task, so beating it alone would be weak evidence. Word-only, character-only and always-positive baselines are needed. Context produces a measurable improvement over word-only here, but precision remains low and performance varies substantially by meeting. These results are an initial experiment, not sufficient to claim robust decision extraction.

The study supports two nested comparisons: word+character+context versus word+character tests context given both lexical features; word+character versus word-only tests character features without context. Character-only is a separate baseline. Full-minus-character and full-minus-word are not tested, so this is not a complete factorial ablation. Each variant is retrained and selected on the same development split. No comparison uses renormalised influence-score magnitudes.

''' + f"A descriptive series-level bootstrap interval for the dev-selected model's F1 is {100*interval[0]:.2f}%–{100*interval[1]:.2f}%. With only three independent series this cannot justify a strong significance claim.\n\n" + '''The main failure is false positives. Read the confusion matrices and per-meeting results in `evaluation/decision_discussion/summary.json`. Improving precision is the next development objective; do not adjust thresholds using this test set. Any new model iteration must be reported transparently as further development, with a fresh independent final evaluation before confirmatory claims.

![Decision discussion comparison](figures/decision_discussion_comparison.png)

Reproduce from the project root:

```
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 .venv/bin/python scripts/evaluate_decision_discussions.py
.venv/bin/python scripts/report_decision_discussions.py
```

Model artifacts and full text examples are under `.runtime/research-decision-model/`; they have not been loaded by the app. The prespecified split and selection description are in `evaluation/decision_discussion/protocol.json`. Provenance hashes are in the summary.
'''
    (ROOT / 'professor_guidelines/DECISION_DISCUSSION_EXPERIMENT.md').write_text(text)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(9,4))
    labels=['Always positive','Explicit rule','Word','Character','Word + char','Word + char + context']
    names=['always_positive','current_explicit_decision_rule','word','char','word_char','word_char_context']
    values=[next(row['test']['f1']*100 for row in rows if row['method']==name) for name in names]
    bars=ax.barh(labels,values,color=['#aaa','#aaa','#477da7','#477da7','#477da7','#176b87']);ax.bar_label(bars,fmt='%.2f',padding=3)
    ax.set_xlim(0,60);ax.set_xlabel('Positive-class F1 (%) · oracle transcript and act boundaries');ax.invert_yaxis();fig.tight_layout()
    for suffix in ['png','pdf','svg']:fig.savefig(ROOT/f'professor_guidelines/figures/decision_discussion_comparison.{suffix}',dpi=300,bbox_inches='tight')
    plt.close(fig)
    return table


if __name__=='__main__':
    print(build())
