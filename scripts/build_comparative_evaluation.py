"""Re-score saved predictions and publish measured comparisons plus labelled sensitivity."""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.evaluation.diagnostics import diarization_diagnostics, score_sensitivity
from src.utils.cache import atomic_json
from scripts.evaluate_research_audio import reference

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'professor_guidelines'
EV = OUT / 'evaluation'


def table(headers, rows):
    return '| ' + ' | '.join(headers) + ' |\n|' + '|'.join(['---'] * len(headers)) + '|\n' + ''.join('| ' + ' | '.join(map(str, row)) + ' |\n' for row in rows)


def csv_rows(path, rows):
    if not rows:
        return
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def build():
    audio = json.loads((EV / 'audio_summary.json').read_text())
    diagnostics = []
    for row in audio['test']:
        result = diarization_diagnostics(reference(row['meeting'])[1], row['hypothesis'], row['duration'])
        diagnostics.append(dict(meeting=row['meeting'], threshold=row['threshold'], der=row['der']['der'],
                                reference_speaker_seconds=row['der']['total_reference_duration'], **result))
    pooled = []
    for threshold in sorted({r['threshold'] for r in diagnostics}):
        rows = [r for r in diagnostics if r['threshold'] == threshold]
        relevant = sum(r['speech_reference_seconds'] for r in rows)
        retrieved = sum(r['speech_retrieved_seconds'] for r in rows)
        correct = sum(r['speech_correct_seconds'] for r in rows)
        precision, recall = correct / retrieved if retrieved else 0, correct / relevant if relevant else 0
        pooled.append({'threshold': threshold, 'meetings': len(rows),
            'pooled_der': sum(r['der'] * r['reference_speaker_seconds'] for r in rows) / sum(r['reference_speaker_seconds'] for r in rows),
            'pooled_jer': sum(r['jer_speaker_error'] for r in rows) / sum(r['jer_speaker_count'] for r in rows),
            'speech_precision': precision, 'speech_recall': recall,
            'speech_f1': 2 * precision * recall / (precision + recall) if precision + recall else 0,
            'speaker_count_mae': sum(r['speaker_count_absolute_error'] for r in rows) / len(rows)})
    small = json.loads((EV / 'indic_summary.json').read_text())
    medium = json.loads((EV / 'medium/indic_summary.json').read_text())
    speech_rows = []
    for corpus in ['hindi', 'hinglish']:
        for model, result in [('small', small), ('medium', medium)]:
            rows = [r for r in result['rows'] if r['language'] == corpus]
            speech_rows.append({'corpus': corpus, 'model': model, 'samples': len(rows),
                'reference_words': sum(r['wer']['reference_length'] for r in rows),
                **{key: sum(r['wer'][key] for r in rows) for key in ['substitutions', 'deletions', 'insertions']},
                'wer': result['summary'][corpus]['wer'], 'cer': result['summary'][corpus]['cer'],
                'wer_change_percentage_points_vs_small': 100 * (result['summary'][corpus]['wer'] - small['summary'][corpus]['wer']),
                'relative_wer_reduction_vs_small': 1 - result['summary'][corpus]['wer'] / small['summary'][corpus]['wer']})
    ablation_path = next((EV / 'downstream').glob('*_ablation.json'))
    payload = json.loads(ablation_path.read_text())
    control = next(r['influence_scores'] for r in payload['ablations'] if r['experiment'] == 'A1')
    ablations = []
    for row in payload['ablations']:
        changes = score_sensitivity(row['influence_scores'], control)
        if row['experiment'] == 'A8':
            changes.update(changed_scores=None, mean_absolute_score_change=None, max_absolute_score_change=None)
        counts = row.get('input_counts', {})
        ablations.append({'experiment': row['experiment'], 'variant': row['label'],
            'type': 'baseline' if row['experiment'] == 'A8' else 'control' if row['experiment'] == 'A1' else 'component_removal',
            'events': counts.get('events'), 'decisions': counts.get('decisions'),
            'slide_grounded_events': counts.get('slide_grounded_events'), **changes})
    baseline_path = next((EV / 'downstream').glob('*_baselines.json'))
    baseline_payload = json.loads(baseline_path.read_text())
    baselines = [{'method': r['baseline'], 'clusters': len(r['scores']),
        'nonzero_scores': sum(score > 0 for score in r['scores'].values()),
        'spearman_vs_human': None, 'kendall_vs_human': None,
        'human_accuracy_status': 'ground_truth_unavailable'} for r in baseline_payload['baselines']]
    baselines.append({'method': 'Proposed_decision_linked', 'clusters': len(control),
        'nonzero_scores': sum(score > 0 for score in control.values()),
        'spearman_vs_human': None, 'kendall_vs_human': None, 'human_accuracy_status': 'ground_truth_unavailable'})
    data = {'audio_diagnostics': diagnostics, 'pooled_audio_comparison': pooled, 'asr_comparison': speech_rows,
            'ablations': ablations, 'baselines': baselines, 'downstream_source': str(ablation_path.relative_to(ROOT)),
            'limits': ['Two held-out English meeting excerpts; descriptive pilot, not full-corpus benchmark.',
                       'Downstream ablation uses the original 139-cluster report; does not validate participant identities.',
                       'Component weights are renormalized after removal. Score movement is not an accuracy benefit.',
                       'A8 is a separate speaking-time baseline, not component-removal ablation.',
                       'No human influence, event, decision, lineage or slide references exist for this report.',
                       'ASR model comparison uses eight correlated samples per corpus; timing not controlled.'],
            'metric_reference': 'https://pyannote.github.io/pyannote-metrics/reference.html#diarization'}
    atomic_json(EV / 'comparative_evaluation.json', data)
    for name, rows in [('audio_diagnostics', diagnostics), ('audio_comparison', pooled), ('asr_comparison', speech_rows),
                       ('ablation_sensitivity', ablations), ('baseline_comparison', baselines)]:
        csv_rows(EV / (name + '.csv'), rows)
    plot(data)
    audio_table = table(['Threshold', 'DER %', 'JER %', 'Speech P %', 'Speech R %', 'Speech F1 %', 'Speaker count MAE'],
        [[r['threshold'], *[f'{100*r[k]:.2f}' for k in ['pooled_der', 'pooled_jer', 'speech_precision', 'speech_recall', 'speech_f1']], f"{r['speaker_count_mae']:.2f}"] for r in pooled])
    ablation_table = table(['ID', 'Variant', 'Slide-grounded events', 'Changed scores', 'Mean absolute score change'],
        [[r['experiment'], r['variant'], r['slide_grounded_events'] if r['slide_grounded_events'] is not None else 'N/A',
          r['changed_scores'] if r['changed_scores'] is not None else 'N/A', f"{r['mean_absolute_score_change']:.6f}" if r['mean_absolute_score_change'] is not None else 'N/A'] for r in ablations])
    baseline_table = table(['Method', 'Clusters', 'Nonzero scores', 'Human ranking accuracy'],
        [[r['method'], r['clusters'], r['nonzero_scores'], 'Unmeasured'] for r in baselines])
    md = '''# Comparative metrics and ablation study

All numeric results below are computed from saved observations. No additional model inference or human annotations were invented. CSV and JSON companions support reproduction and later analysis.

## Metrics and availability

| Component | Metrics | Current evidence |
|---|---|---|
| Speech recognition | WER, CER; substitutions/deletions/insertions; paired error differences | Measured English AMI and Hindi/Hinglish public pilots |
| Speaker diarization | DER, missed/false-alarm/confusion components, JER | Measured on two held-out AMI excerpts |
| Speech activity | Union-of-speech precision, recall and F1 | Measured from the same diarization output; ignores identity |
| Speaker count | Absolute count error and meeting-averaged MAE | Measured on the same two excerpts |
| Slide alignment | Precision, recall, F1 | Implemented; independent reference slide IDs needed |
| Event candidates | Precision, recall, F1 by event type | Implemented; independent reference events needed |
| Decisions and lineage | Decision P/R/F1; node/edge P/R/F1 | Implemented; independent references needed |
| Influence ranking | Spearman and Kendall against human ratings | Implemented; independent ratings needed |
| Efficiency | Stage runtime, RTF, process RSS | Existing runs measured; cache/concurrency scopes must be respected |
| Functional correctness | API, browser, Python and Android checks | Functional tests, separate from model accuracy |

## Measured audio comparison

''' + audio_table + '''
DER weights speaker-time, while JER averages reference-speaker errors; report both. Speech detection collapses identities to speech regions, so high speech F1 does not establish correct speakers. Count MAE also cannot establish correct attribution. The same 0.25-second collar and 120-second UEM are used. These are additional exploratory diagnostics; the original threshold was selected using development DER only. Definitions follow the [pyannote.metrics documentation](https://pyannote.github.io/pyannote-metrics/reference.html#diarization).

The new comparison is visualised below.

![Audio diagnostics](figures/audio_metric_comparison.png)

## Model comparison

''' + table(['Corpus', 'Model', 'Ref words', 'S', 'D', 'I', 'WER %', 'CER %', 'Relative WER reduction %'],
        [[r['corpus'], r['model'], r['reference_words'], r['substitutions'], r['deletions'], r['insertions'],
          f"{100*r['wer']:.2f}", f"{100*r['cer']:.2f}", f"{100*r['relative_wer_reduction_vs_small']:.2f}"] for r in speech_rows]) + '''
Each corpus comparison uses the same eight samples and normalisation. Do not pool Hindi and Hinglish into an overall product accuracy. Medium improves WER here but increases Hinglish CER. This is a model comparison; changing model size is not a component-removal ablation.

## Component ablation and sensitivity

''' + ablation_table + '''
A1 is the control. A2 removes presentation links and reruns downstream NLP. A3/A4 rerun alignment and downstream analysis after removing temporal/semantic evidence. A5–A7 remove feature weights, then renormalize the remaining weights. A8 replaces the scoring method with speaking time. Counts and score movement are descriptive. Human accuracy remains unmeasured in every row.

The chart below excludes A8 because its scoring definition differs. Mean change averages all 139 clusters, including zeros, which can make a change appear small. Consult changed-score counts and maximum change in the CSV. Fragmentation in this original report means these diagnostics must not support claims about real participants.

![Ablation sensitivity](figures/ablation_sensitivity.png)

A subsequent feature audit found that only decision contribution is active: proposed scores equal 0.15 times the decision-count baseline. A5/A6 changes are entirely weight renormalisation and preserve rankings; none of the 34 slides has recorded timing. Read `RESEARCH_VALIDITY_REVIEW.md` before interpreting these charts. A zero change is a legitimate result. It can indicate absent features or no usable temporal information, rather than successful ablation. Threshold tuning is a calibration study; A2–A7 are the component-removal study. Neither is evidence of superior influence accuracy without independent labels.

## Baseline comparison

''' + baseline_table + '''
Six baseline implementations and the proposed method are available. Nonzero-score coverage describes outputs, not correctness. Baseline score scales differ, so score magnitudes are not compared as accuracy. No comparison with commercial systems or published paper scores is made unless the same audio, references and protocol are actually run.

## Reproduce

From the project root:

```
.venv/bin/python scripts/build_comparative_evaluation.py
.venv/bin/python scripts/build_research_documents.py
.venv/bin/python scripts/check_research_package.py
```

The first command re-scores saved AMI predictions and reads completed downstream variants; it does not rerun neural inference. To recompute downstream variants for an independently annotated meeting:

```
.venv/bin/python scripts/run_evaluation.py --meeting-id YOUR_MEETING_ID --annotations YOUR_ANNOTATIONS.json --ablation --output-dir outputs/evaluation/YOUR_RUN
```

Human raters must annotate before inspecting model outputs. Keep speaker/session splits and report rater agreement. Missing reference fields remain null, and graphs must not plot them as zero.
'''
    (OUT / 'COMPARATIVE_AND_ABLATION.md').write_text(md)
    return data, audio_table, ablation_table


def plot(data):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    def save(fig, name):
        fig.tight_layout()
        for extension in ['png', 'svg', 'pdf']:
            fig.savefig(OUT / 'figures' / (name + '.' + extension), dpi=300, bbox_inches='tight')
        plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for index, row in enumerate(data['pooled_audio_comparison']):
        values = [100 * row[k] for k in ['pooled_der', 'pooled_jer', 'speech_f1']]
        bars = axes[0].bar([x + (index - .5) * .36 for x in range(3)], values, .36, label=str(row['threshold']))
        axes[0].bar_label(bars, fmt='%.1f', fontsize=8)
        axes[1].bar(index, row['speaker_count_mae'], .6)
    axes[0].set_xticks([0, 1, 2], ['DER ↓', 'JER ↓', 'Speech F1 ↑']); axes[0].set_ylabel('Percent'); axes[0].set_ylim(0, 110)
    axes[0].legend(title='Threshold'); axes[1].set_xticks([0, 1], ['0.5', '0.9']); axes[1].set_xlabel('Threshold'); axes[1].set_ylabel('Speaker count MAE ↓')
    save(fig, 'audio_metric_comparison')
    rows = data['ablations'][:7]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    labels = [r['experiment'] for r in rows]
    axes[0].bar(labels, [r.get('mean_absolute_score_change', 0) for r in rows]); axes[0].set_ylabel('Mean absolute score change vs A1')
    axes[1].bar(labels, [r.get('changed_scores', 0) for r in rows]); axes[1].set_ylabel('Clusters with changed scores')
    fig.suptitle('Sensitivity only · original 139 clusters · human accuracy unmeasured', fontsize=10)
    save(fig, 'ablation_sensitivity')


if __name__ == '__main__':
    result, _, _ = build()
    print(json.dumps({'audio_comparison': result['pooled_audio_comparison'], 'ablation_variants': len(result['ablations']), 'baseline_methods': len(result['baselines'])}, indent=2))
