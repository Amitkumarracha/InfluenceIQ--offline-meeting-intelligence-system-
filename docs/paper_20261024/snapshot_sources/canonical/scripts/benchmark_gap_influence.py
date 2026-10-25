"""Isolated outcome-influence experiment on GAP; never installs an application model.

Train/development selection and final evaluation are separate invocations.
Only transcript text, speaker IDs and timing enter features. GAP's AII is an
outcome-alignment proxy (lower is more influential), not a causal annotation.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import re
import sys

import joblib
import numpy as np
from scipy.sparse import csr_matrix, hstack
from scipy.stats import rankdata
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler
import sklearn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.train_influence_weights import metrics, KEYS
from src.meeting.events import ALL_EVENT_TYPES, KeywordEventExtractor
from src.meeting.evidence import extract_evidence
from src.meeting.decisions import reconstruct_decisions
from src.meeting.interaction import extract_interactions
from src.meeting.influence import compute_influence

SEED = 20261024
FEATURES = ['duration', 'words', 'utterances', 'mean_words', 'early_words', 'late_words',
            'reason_markers', 'suggestion_markers', 'first_person', 'inclusive_pronouns'] + ALL_EVENT_TYPES + KEYS
GRID = [('ridge', value) for value in [.1, 1., 10., 100.]] + [
    ('pairwise_logistic', value) for value in [.01, .1, 1., 10.]] + [
    ('extra_trees', value) for value in [2, 5]]
RAW_KEYS = [key + '_contribution' for key in KEYS[:-1]] + ['slide_grounded_contribution']
SOURCES = ['https://convokit.cornell.edu/documentation/gap.html',
           'https://zissou.infosci.cornell.edu/convokit/datasets/gap-corpus/gap-corpus.zip',
           'https://doi.org/10.1145/3279981.3279985']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def seconds(value):
    parts = str(value).split(':')
    result = sum(float(part) * 60**i for i, part in enumerate(reversed(parts)))
    if not np.isfinite(result) or result < 0:
        raise ValueError('Invalid timestamp')
    return result


def split_groups(groups):
    groups = sorted(groups)
    if len(groups) != 28:
        raise ValueError('Expected the pinned 28-group GAP release; inspect a different version separately')
    shuffled = np.random.default_rng(SEED).permutation(groups).tolist()
    return dict(train=shuffled[:16], development=shuffled[16:22], test=shuffled[22:])


def records(data, allowed):
    """No manual Decision/Sentiment/Private/Survival Item metadata enters features."""
    speakers = json.loads((data / 'speakers.json').read_text())
    grouped = {group: [] for group in allowed}
    for line in (data / 'utterances.jsonl').read_text().splitlines():
        row = json.loads(line)
        group = str(speakers[row['speaker']]['Group Number'])
        if group not in grouped:
            continue
        start, end = seconds(row['timestamp']), seconds(row['meta']['End'])
        if end < start:
            raise ValueError('Negative utterance interval')
        grouped[group].append({'segment_id': len(grouped[group]), 'start': start, 'end': end,
                               'speaker': row['speaker'], 'text': row['text'].strip('"')})
    output = []
    extractor = KeywordEventExtractor()
    for group, segments in sorted(grouped.items()):
        segments.sort(key=lambda row: row['start'])
        roster = sorted(speaker for speaker, meta in speakers.items() if str(meta['Group Number']) == group)
        if set(roster) != {row['speaker'] for row in segments}:
            raise ValueError('Incomplete participant roster')
        events = extractor.extract(segments, group)
        evidence = extract_evidence(events)
        decisions = reconstruct_decisions(events, evidence)
        interactions = extract_interactions(events, evidence, decisions)
        influence = compute_influence(events, evidence, decisions, interactions, transcript_segments=segments)
        baselines = {row.participant: row for row in influence.baselines}
        total_time = max(row['end'] for row in segments)
        for speaker in roster:
            own = [row for row in segments if row['speaker'] == speaker]
            text = ' '.join(row['text'] for row in own)
            tokens = re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower())
            counts = Counter(event.event_type for event in events.events if event.speaker == speaker)
            participant = influence.for_participant(speaker)
            raw = [baselines[speaker].speaking_time, len(tokens), len(own), len(tokens)/max(1, len(own)),
                   sum(len(row['text'].split()) for row in own if row['start'] < total_time/3),
                   sum(len(row['text'].split()) for row in own if row['start'] >= total_time*2/3),
                   sum(token in {'because', 'since', 'reason', 'therefore', 'evidence'} for token in tokens),
                   len(re.findall(r"\b(?:i think|we should|how about|let's|i suggest|we need)\b", text.lower())),
                   sum(token in {'i', 'my', 'me'} for token in tokens),
                   sum(token in {'we', 'our', 'us'} for token in tokens)]
            raw += [counts[kind] for kind in ALL_EVENT_TYPES]
            raw += [participant.raw_features[key] for key in RAW_KEYS]
            aii = float(speakers[speaker]['AII'])
            if not np.isfinite(aii):
                raise ValueError('Missing AII label; do not silently remove participants')
            output.append({'meeting_id': group, 'participant': speaker, 'aii': aii, 'text': text,
                           'raw': raw, 'prototype': participant.influence_score,
                           'decision_count': baselines[speaker].decision_event_count})
        current = output[-len(roster):]
        x = np.asarray([row['raw'] for row in current], dtype=float)
        # Meeting-relative features require no fitted population or outcome labels.
        x = np.divide(x, x.max(axis=0), out=np.zeros_like(x), where=x.max(axis=0) > 0)
        target = (rankdata([-row['aii'] for row in current])-1) / (len(roster)-1)
        for row, vector, label in zip(current, x, target):
            row['vector'], row['target'] = vector, float(label)
    return output


def score(rows, predictions):
    scored = [{**row, 'human_score': row['target'], 'vector': np.array([prediction])}
              for row, prediction in zip(rows, predictions)]
    value = metrics(scored, np.ones(1))
    value.pop('participant_mse')  # Rankers have arbitrary score scales.
    correlations = [row['spearman'] for row in value['meetings'] if row['spearman'] is not None]
    value['mean_spearman'] = float(np.mean(correlations)) if correlations else None
    return value


def baseline_predictions(rows):
    return {'speaking_time': np.array([r['raw'][0] for r in rows]),
            'word_count': np.array([r['raw'][1] for r in rows]),
            'utterance_count': np.array([r['raw'][2] for r in rows]),
            'decision_count': np.array([r['decision_count'] for r in rows]),
            'prototype_influence': np.array([r['prototype'] for r in rows])}


def fit_model(family, parameter, x, rows):
    target = np.array([row['target'] for row in rows])
    if family == 'ridge':
        return Ridge(alpha=parameter, solver='lsqr').fit(x, target)
    if family == 'extra_trees':
        return ExtraTreesRegressor(n_estimators=150, min_samples_leaf=parameter,
                                   random_state=SEED, n_jobs=2).fit(x, target)
    differences, labels, weights = [], [], []
    for meeting in sorted({r['meeting_id'] for r in rows}):
        indices = [i for i, row in enumerate(rows) if row['meeting_id'] == meeting]
        pairs = [(i, j) for offset, i in enumerate(indices) for j in indices[offset+1:]
                 if target[i] != target[j]]
        for i, j in pairs:
            differences.extend([x[i]-x[j], x[j]-x[i]])
            labels.extend([int(target[i] > target[j]), int(target[j] > target[i])])
            weights.extend([1/max(1, len(pairs))]*2)
    from scipy.sparse import vstack
    return LogisticRegression(C=parameter, fit_intercept=False, solver='liblinear',
                              random_state=SEED).fit(vstack(differences), labels, sample_weight=weights)


def predict(model, x):
    return model.decision_function(x) if isinstance(model, LogisticRegression) else model.predict(x)


def train(data, output):
    groups = {str(meta['Group Number']) for meta in json.loads((data / 'speakers.json').read_text()).values()}
    splits = split_groups(groups)
    output.mkdir(parents=True, exist_ok=False)
    inputs = {name: digest(data/name) for name in ['speakers.json', 'conversations.json', 'utterances.jsonl']}
    protocol = {'task': 'Within-meeting ranking of GAP outcome influence; lower AII is more influence',
                'status': 'Exploratory external-corpus pilot; reference transcripts and speaker IDs',
                'sources': SOURCES, 'license': 'CC BY-NC 4.0', 'seed': SEED, 'splits': splits,
                'input_sha256': inputs, 'script_sha256': digest(Path(__file__)),
                'source_sha256': {str(path): digest(ROOT/path) for path in [
                    Path('src/meeting/events.py'), Path('src/meeting/decisions.py'),
                    Path('src/meeting/influence.py'), Path('src/meeting/evidence.py'),
                    Path('src/meeting/interaction.py'), Path('scripts/train_influence_weights.py'),
                    Path('config/config.yaml')]},
                'features': FEATURES, 'grid': GRID, 'feature_sets': ['structure', 'text', 'combined'],
                'selection': 'Maximum development meeting-macro pairwise accuracy; fixed loop order breaks ties',
                'forbidden_inputs': ['AII as feature', 'AIS', 'AGS', 'demographics', 'questionnaires',
                                     'manual Decision/Sentiment/Private/Survival Item annotations'],
                'aii_definition': 'Distance between individual pre-meeting and final group item rankings; lower is more aligned',
                'test_access': 'Separate --evaluate after development selection and artifact hashes are frozen',
                'python': platform.python_version(), 'sklearn': sklearn.__version__,
                'installed_in_application': False}
    save(output/'protocol.json', protocol)
    training, development = records(data, splits['train']), records(data, splits['development'])
    scaler = StandardScaler().fit([row['vector'] for row in training])
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=2500, sublinear_tf=True)
    text_train = vectorizer.fit_transform([row['text'] for row in training])
    text_dev = vectorizer.transform([row['text'] for row in development])
    structure_train = csr_matrix(scaler.transform([row['vector'] for row in training]))
    structure_dev = csr_matrix(scaler.transform([row['vector'] for row in development]))
    matrices = {'structure': (structure_train, structure_dev), 'text': (text_train, text_dev),
                'combined': (hstack([structure_train, text_train]).tocsr(), hstack([structure_dev, text_dev]).tocsr())}
    search, finalists, winner = [], {}, None
    for name, predictions in baseline_predictions(development).items():
        candidate = {'name': name, 'kind': 'baseline', 'development': score(development, predictions)}
        search.append(candidate)
        if winner is None or candidate['development']['meeting_macro_pairwise_accuracy'] > winner['development']['meeting_macro_pairwise_accuracy']:
            winner = candidate
    for features, (x_train, x_dev) in matrices.items():
        for family, parameter in GRID:
            model = fit_model(family, parameter, x_train, training)
            candidate = {'name': features+'__'+family, 'kind': 'learned', 'features': features,
                         'family': family, 'parameter': parameter, 'development': score(development, predict(model, x_dev))}
            search.append(candidate)
            previous = finalists.get(candidate['name'])
            if previous is None or candidate['development']['meeting_macro_pairwise_accuracy'] > previous[0]['development']['meeting_macro_pairwise_accuracy']:
                finalists[candidate['name']] = (candidate, model)
            if candidate['development']['meeting_macro_pairwise_accuracy'] > winner['development']['meeting_macro_pairwise_accuracy']:
                winner = candidate
    bundle = {'scaler': scaler, 'vectorizer': vectorizer, 'finalists': finalists, 'primary': winner}
    joblib.dump(bundle, output/'frozen_models.joblib')
    save(output/'development_search.json', search)
    save(output/'selection.json', {'primary': winner, 'model_sha256': digest(output/'frozen_models.joblib'),
                                  'development_groups': splits['development'], 'test_evaluated': False})
    print('Frozen primary:', winner['name'], 'development pairwise accuracy:', winner['development']['meeting_macro_pairwise_accuracy'])


def evaluate(data, output):
    if (output/'test_results.json').exists():
        raise ValueError('Final results already exist; do not adaptively retune on these test meetings')
    protocol = json.loads((output/'protocol.json').read_text())
    selection = json.loads((output/'selection.json').read_text())
    if selection['model_sha256'] != digest(output/'frozen_models.joblib') or protocol['script_sha256'] != digest(Path(__file__)):
        raise ValueError('Frozen model or evaluation code changed')
    for name, expected in protocol['input_sha256'].items():
        if digest(data/name) != expected:
            raise ValueError('Dataset changed')
    for name, expected in protocol['source_sha256'].items():
        if digest(ROOT/name) != expected:
            raise ValueError('Feature extraction source/config changed')
    rows = records(data, protocol['splits']['test'])
    bundle = joblib.load(output/'frozen_models.joblib')
    structure = csr_matrix(bundle['scaler'].transform([row['vector'] for row in rows]))
    text = bundle['vectorizer'].transform([row['text'] for row in rows])
    matrices = {'structure': structure, 'text': text, 'combined': hstack([structure, text]).tocsr()}
    predictions = baseline_predictions(rows)
    for name, (candidate, model) in bundle['finalists'].items():
        predictions[name] = predict(model, matrices[candidate['features']])
    results = {name: score(rows, values) for name, values in predictions.items()}
    primary = bundle['primary']['name']
    values = np.array([r['pairwise_accuracy'] for r in results[primary]['meetings'] if r['pairwise_accuracy'] is not None])
    rng = np.random.default_rng(SEED)
    boot = rng.choice(values, size=(10000, len(values)), replace=True).mean(axis=1)
    result = {'primary_selected_on_development': primary, 'test_meetings': len(protocol['splits']['test']),
              'test_participants': len(rows), 'results': results,
              'primary_pairwise_meeting_bootstrap_95_ci': np.quantile(boot, [.025, .975]).tolist(),
              'predictions': [{k: row[k] for k in ['meeting_id', 'participant', 'aii']} |
                            {'scores': {name: float(values[i]) for name, values in predictions.items()}}
                            for i, row in enumerate(rows)],
              'limitations': ['Six test groups; wide uncertainty and no significance claim.',
                             'AII measures outcome alignment, not causal influence or independent human judgments.',
                             'Oracle English text/speakers; no ASR, slides or app deployment accuracy established.',
                             'Only 28 groups overall; fresh groups required after further test-informed development.'],
              'installed_in_application': False}
    save(output/'test_results.json', result)
    print(json.dumps({name: value['meeting_macro_pairwise_accuracy'] for name, value in results.items()}, indent=2))
    print('Primary:', primary, '95% meeting bootstrap CI:', result['primary_pairwise_meeting_bootstrap_95_ci'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--evaluate', action='store_true')
    args = parser.parse_args()
    (evaluate if args.evaluate else train)(args.data, args.output_dir)


if __name__ == '__main__':
    main()
