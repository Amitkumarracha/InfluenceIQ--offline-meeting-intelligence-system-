"""Build a scope-aware scorecard from preserved experiment measurements."""
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.compare_asr_quality import pooled
from scripts.optimize_discussion_quality import all_metrics
from scripts.improve_decision_discussions import sha256
from src.utils.cache import atomic_json
from src.utils.config import get
from src.utils.text import words
from src.evaluation.metrics import calculate_wer

FOLDER = ROOT / 'professor_guidelines'
EV = FOLDER / 'evaluation'
OUT = EV / 'quality_scorecard'


def table(headers, rows):
    return '| ' + ' | '.join(headers) + ' |\n| ' + ' | '.join(['---'] * len(headers)) + ' |\n' + ''.join(
        '| ' + ' | '.join(map(str, row)) + ' |\n' for row in rows)


def majority_metrics(metrics):
    truth = np.r_[np.zeros(metrics['negative_support']), np.ones(metrics['positive_support'])]
    return all_metrics(truth, np.zeros(len(truth)), .5)


def asr_release_eligible(turbo, small_indic):
    return turbo['passes_english_dev_gate'] and all(
        turbo['summary'][corpus][metric]['rate'] <= small_indic['summary'][corpus][metric]
        for corpus in ['hindi', 'hinglish'] for metric in ['wer', 'cer'])


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    load = lambda name: json.loads((EV / name).read_text())
    semantic = load('semantic_quality/summary.json')
    sequence = load('sequence_quality/summary.json')
    ensemble = load('ensemble_quality/summary.json')
    refit = load('refit_quality/summary.json')
    asr = load('asr_quality/summary.json')
    turbo = load('turbo_quality/summary.json')
    small_indic = load('indic_summary.json')
    medium_indic = load('medium/indic_summary.json')
    original_audio = load('audio_summary.json')
    audio = next(row for row in load('comparative_evaluation.json')['pooled_audio_comparison'] if row['threshold'] == .9)
    baseline = semantic['baseline_test']
    majority = majority_metrics(baseline)
    assert semantic['selection']['method'] == sequence['selection']['method'] == 'installed_baseline'
    assert not refit['passes_deployment_gate']
    assert ensemble['test']['f1'] < baseline['f1']
    eligible = asr_release_eligible(turbo, small_indic)
    installed_asr = get('asr.model_size')
    if installed_asr == 'large-v3-turbo':
        assert eligible, 'Shared ASR default cannot bypass the declared language regression gate'
    metrics = ['accuracy', 'balanced_accuracy', 'precision', 'recall', 'f1', 'specificity',
               'macro_f1', 'average_precision', 'roc_auc', 'mcc', 'brier']
    labels = ['Accuracy', 'Balanced accuracy', 'Precision', 'Recall', 'F1', 'Specificity',
              'Macro F1', 'Average precision', 'ROC AUC', 'MCC', 'Brier score']
    full_table = table(['Metric', 'Installed forest/linear', 'Always negative'], [
        [label, *(f'{row[key]:.4f}' if key in ['mcc', 'brier'] else f'{100*row[key]:.2f}%'
                   for row in [baseline, majority])] for key, label in zip(metrics, labels)])
    asr_rows = []
    for row in asr['models']:
        asr_rows.append({'cohort': 'English development (2 clips)', 'model': row['model'], **{key: row[key] for key in ['wer', 'cer']}})
        for meeting in ['ES2002a', 'ES2003a']:
            assert load('asr_quality/'+row['model']+'_'+meeting+'.json')['reference'] == load('turbo_quality/turbo_'+meeting+'.json')['reference']
    historical_small = []
    for row in original_audio['asr']:
        truth = ' '.join(words(row['reference']))
        hypothesis = ' '.join(words(row['hypothesis']))
        saved_turbo = load('turbo_quality/turbo_'+row['meeting']+'.json')
        assert truth == saved_turbo['reference'], 'Historical references must remain identical'
        historical_small.append({**row, 'cer': calculate_wer(
            ' '.join(truth.replace(' ', '')), ' '.join(hypothesis.replace(' ', '')))})
    atomic_json(OUT / 'historical_small_rescore.json', historical_small)
    asr_rows.append({'cohort': 'English historical (2 clips)', 'model': 'small',
                     'wer': pooled(historical_small, 'wer'), 'cer': pooled(historical_small, 'cer')})
    for corpus in ['hindi', 'hinglish']:
        for model, data in [('small', small_indic), ('medium', medium_indic)]:
            s = data['summary'][corpus]
            samples = [row for row in data['rows'] if row['language'] == corpus]
            assert len(samples) == 8
            for sample in samples:
                assert ' '.join(words(sample['reference'])) == load(f"turbo_quality/turbo_{corpus}_{sample['sample']}.json")['reference']
            asr_rows.append({'cohort': corpus.capitalize() + ' (8 samples)', 'model': model,
                            **{key: {'rate': s[key], 'errors': s[key+'_errors'], 'reference_length': s[key+'_reference_length']}
                               for key in ['wer', 'cer']}})
    for corpus, label in [('english_dev', 'English development (2 clips)'),
                          ('english_historical', 'English historical (2 clips)'),
                          ('hindi', 'Hindi (8 samples)'), ('hinglish', 'Hinglish (8 samples)')]:
        asr_rows.append({'cohort': label, 'model': 'large-v3-turbo',
                         **{key: turbo['summary'][corpus][key] for key in ['wer', 'cer']}})
    old_historical_wer = pooled(historical_small, 'wer')['rate']
    new_historical_wer = turbo['summary']['english_historical']['wer']['rate']
    default_reason = ('Historical English WER regressed; retain small as the shared default and expose turbo as an optional model.'
                      if installed_asr == 'small' and new_historical_wer > old_historical_wer else
                      'Use the declared development/pilot gate and report all language-specific trade-offs.')
    for cohort in {row['cohort'] for row in asr_rows}:
        for metric in ['wer', 'cer']:
            assert len({row[metric]['reference_length'] for row in asr_rows if row['cohort'] == cohort}) == 1
    asr_table = table(['Cohort', 'Speech model', 'WER ↓ (edits/words)', 'CER ↓ (edits/characters)'], [
        [row['cohort'], row['model'], *('Unavailable' if row[key] is None else
         f"{100*row[key]['rate']:.2f}% ({row[key]['errors']}/{row[key]['reference_length']})" for key in ['wer', 'cer'])]
        for row in asr_rows])
    trials = table(['Fixed trial', 'Development outcome', 'Historical F1', 'Historical AP', 'Installation'], [
        ['Frozen sentence embeddings + classifiers', 'No five-metric non-regression winner', 'Baseline retained', 'Baseline retained', 'No change'],
        ['Time-aware forward/backward smoothing', 'No five-metric non-regression winner', 'Baseline retained', 'Baseline retained', 'No change'],
        ['Calibrated forest/NB combination', f"F1 {100*ensemble['selection']['dev']['f1']:.2f}%", f"{100*ensemble['test']['f1']:.2f}%", f"{100*ensemble['test']['average_precision']:.2f}%", 'Rejected: historical regression'],
        ['Fixed train+development refit', 'No independent dev score after refit', f"{100*refit['test']['f1']:.2f}%", f"{100*refit['test']['average_precision']:.2f}%", 'Rejected: historical AP regression']])
    payload = {'discussion': {'installed': baseline, 'always_negative': majority,
                            'scope': '11,136 oracle AMI acts, 2,481 positives, 12 meetings / 3 project series; reused historical cohort'},
               'asr': asr_rows, 'installed_asr': installed_asr, 'turbo_passes_development_pilot_gate': eligible,
               'shared_default_decision': default_reason,
               'audio_diarization': audio,
               'unmeasured': ['ASR-passage discussion accuracy', 'Final-decision accuracy', 'Event taxonomy accuracy',
                              'Slide alignment accuracy', 'Human influence ranking accuracy'],
               'limits': 'All comparisons exploratory. No fresh final test, no full-project accuracy, no significance claim.'}
    atomic_json(OUT / 'summary.json', payload)
    sources = [EV / path for path in ['semantic_quality/summary.json', 'sequence_quality/summary.json',
        'ensemble_quality/summary.json', 'refit_quality/summary.json', 'asr_quality/summary.json', 'turbo_quality/summary.json']]
    atomic_json(OUT / 'sources.json', {str(path.relative_to(ROOT)): sha256(path) for path in sources})
    with (OUT / 'metrics.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['task', 'cohort', 'model', 'metric', 'value', 'direction', 'errors', 'reference_length'])
        for name, row in [('installed_forest_linear', baseline), ('always_negative', majority)]:
            for metric in metrics:
                writer.writerow(['discussion_membership', 'historical_oracle_acts', name, metric, row[metric],
                                 'lower' if metric == 'brier' else 'higher', '', 11136])
        for row in asr_rows:
            for metric in ['wer', 'cer']:
                if row[metric] is not None:
                    v = row[metric]
                    writer.writerow(['speech_recognition', row['cohort'], row['model'], metric, v['rate'], 'lower', v['errors'], v['reference_length']])
    report = f'''# Quality improvements and complete metric scorecard

The local speech default is **{installed_asr}**. The discussion stage retains the installed 75% random-forest / 25% logistic-regression model. This round tested stronger recognition and four NLP improvement paths; failed candidates are preserved rather than reported as gains. These experiments train small discussion classifiers; none fine-tunes Whisper or the frozen sentence encoder.

## Discussion membership: all measured metrics

{full_table}
All rows use the same 11,136 reference dialogue acts, including 2,481 positives and 8,655 negatives, from 12 AMI meetings in three project series. Inputs are human transcripts and dialogue-act boundaries. The installed threshold is 0.357740 with ±5-act smoothing. Its confusion matrix is TN=5,627, FP=3,028, FN=467, TP=2,014. Higher is better except Brier (lower). Scores are uncalibrated; Brier is descriptive, not evidence of correctness probabilities.

Always-negative accuracy exceeds the useful detector's accuracy because 77.72% of acts are negative; its positive F1 and recall are zero. Accuracy alone therefore cannot identify a useful discussion detector. These are task metrics, not whole-project accuracy. Actual ASR-passage accuracy, final-decision accuracy and human influence accuracy remain unmeasured.

## This round's NLP experiments

{trials}
The semantic study used the local frozen MiniLM encoder, context radii 5/15/40, optional timing features, logistic and gradient-boosted classifiers, and mixtures with the baseline. The continuity study estimated transitions on training labels and used elapsed-time forward/backward scores. Development selection required non-regression on precision, recall, F1, accuracy and AP. Neither study produced an eligible replacement. Full prespecified alternatives remain in the saved artifacts.

The calibrated trial used ComplementNB with project-group-separated calibration folds, blended with the forest. Shared vocabulary fitting on the complete training set is disclosed in its protocol. Development improvements did not transfer to the historical cohort. The final refit used 35 train+development meetings (24,078 acts), keeping vocabulary, model settings, mixture, smoothing and threshold fixed; historical meetings were excluded from fitting. Its higher recall/F1 came with lower precision, accuracy and AP. Training size differs from prior 29-meeting comparisons, so it is not a matched-data algorithm comparison. Both failed the fixed historical release gate; no historical-best substitution was made.

## Speech recognition comparison

{asr_table}
The shared-default eligibility gate requires no regression in both English-development WER/CER and both Hindi/Hinglish WER/CER versus small. Turbo passes this development/pilot gate: **{eligible}**. The installed default is **{installed_asr}**. {default_reason} Historical English WER changes from {100*old_historical_wer:.2f}% to {100*new_historical_wer:.2f}%. This regression is retained and prevents a universal upgrade claim. No alternative configuration was selected from historical results. Medium did not improve English development. All models used local CPU int8 inference, automatic language selection constrained by the existing English/Hindi configuration, the same beam setting, and unchanged reference normalization/boundaries. Historical-small CER is calculated from its saved unchanged transcript/reference, without rerunning recognition. No reference hints, reference edits or sample removals were used. Historical English scores remain exploratory; the TS3007d uncovered reference prefix stays included. The two English development excerpts and eight examples per Indic corpus are small, correlated pilots, not a full benchmark. Wall times include initialization/concurrent work and do not support a speed claim. Larger cached models require more memory/storage; physical-phone performance is unmeasured.

Turbo weights are pinned by revision and SHA-256 in `evaluation/turbo_quality/protocol.json`. Sources: [OpenAI model card](https://huggingface.co/openai/whisper-large-v3-turbo), [converted model card](https://huggingface.co/dropbox-dash/faster-whisper-large-v3-turbo). Existing reports retain their original outputs; reanalyse a recording to use a changed default. `MAI_ASR_MODEL` and per-recording choices override the default. Provisioning on another machine uses `scripts/download_models.py --asr-model large-v3-turbo`.

## Other project metrics and missing ground truth

The earlier custom two-excerpt audio pilot, unchanged in this round, has DER {100*audio['pooled_der']:.2f}%, JER {100*audio['pooled_jer']:.2f}%, speech precision {100*audio['speech_precision']:.2f}%, recall {100*audio['speech_recall']:.2f}%, F1 {100*audio['speech_f1']:.2f}% and speaker-count MAE {audio['speaker_count_mae']:.2f}. These are separate tasks with different denominators; they cannot be averaged into an overall accuracy. Reference-coverage and overlap limits in the original evaluation still apply.

No independent labels currently establish event-type accuracy, final-decision accuracy, slide-link accuracy or influence-ranking accuracy. A fresh meeting-level test with independent annotations is required before claiming general superiority or complete application accuracy. Repeated development and historical inspection mean the current results are exploratory.

## Artifacts and reproduction

`evaluation/quality_scorecard/summary.json` and `metrics.csv` contain unrounded values and denominators; `sources.json` pins source summaries. Individual protocols, selections, all alternatives and raw transcripts are under `evaluation/{{semantic_quality,sequence_quality,ensemble_quality,refit_quality,asr_quality,turbo_quality}}/`. Research model/cache artifacts remain under `.runtime/`; the installed discussion model remains `models/discussion/model.joblib` with its existing provenance manifest.

```bash
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 .venv/bin/python scripts/evaluate_turbo_quality.py
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 .venv/bin/python scripts/report_quality_improvements.py
MPLCONFIGDIR=/tmp/influenceiq-mpl .venv/bin/python scripts/build_research_documents.py
```
'''
    (FOLDER / 'QUALITY_IMPROVEMENTS.md').write_text(report)
    paper = f'''### 5.8 Further quality trials and complete discussion metrics

Table 12 expands the installed discussion model's metrics on the same historical oracle-act cohort. Majority-class accuracy is 77.72% with zero positive recall/F1, demonstrating why plain accuracy alone is insufficient. No whole-application accuracy is inferred.

Table 12. Installed discussion model versus an always-negative baseline.

{full_table}
Frozen semantic features and time-aware continuity failed the development non-regression gate. A calibrated forest/NB mixture improved development F1 but reduced historical F1 to {100*ensemble['test']['f1']:.2f}% and AP to {100*ensemble['test']['average_precision']:.2f}%. A single final train+development refit with all settings fixed produced F1 {100*refit['test']['f1']:.2f}% but AP {100*refit['test']['average_precision']:.2f}%; it lacks an independent development score and uses more training data. Neither replacement was installed. Full alternatives, gates and provenance are retained in the supplement. These negative results remain part of the exploratory study.

### 5.9 Stronger local speech recognition

Table 13 compares the cached recognition models without speech fine-tuning. The shared default is {installed_asr}; eligibility requires no WER/CER regression versus small on English development and the unchanged Hindi/Hinglish pilots. {default_reason} All samples, references and normalization remain fixed. Historical English scores are exploratory, and its uncovered reference prefix was retained. Concurrent execution prevents speed claims. Larger-model memory/storage requirements and small, correlated cohorts limit deployment/generalisation conclusions.

Table 13. Fixed-sample speech comparison; lower error is better.

{asr_table}
'''
    return paper


if __name__ == '__main__':
    print(build())
