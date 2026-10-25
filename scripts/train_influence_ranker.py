"""Compare CPU XGBoost rankers on independent GAP outcome-alignment labels."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.benchmark_gap_influence import score, save, digest, records, seconds
from src.meeting.events import KeywordEventExtractor
from src.meeting.evidence import extract_evidence
from src.meeting.decisions import reconstruct_decisions
from src.meeting.interaction import extract_interactions
from src.meeting.influence import compute_influence
from src.meeting.topics import infer_event_topics
from src.meeting.ranking import FEATURE_NAMES, participant_features, xgb_ranker_class


def feature_rows(data):
    speakers = json.loads((data/'speakers.json').read_text())
    grouped = {}
    for line in (data/'utterances.jsonl').read_text().splitlines():
        row = json.loads(line); group = str(speakers[row['speaker']]['Group Number'])
        turns = grouped.setdefault(group, [])
        turns.append({'segment_id': len(turns), 'speaker': row['speaker'], 'text': row['text'].strip('"'),
                      'start': seconds(row['timestamp']), 'end': seconds(row['meta']['End'])})
    result = []
    for group, turns in sorted(grouped.items()):
        events = KeywordEventExtractor().extract(turns, group)
        evidence = extract_evidence(events)
        topics = infer_event_topics(events.events)
        variants = {}
        for name, topic_ids in [('full', None), ('topic', topics)]:
            decisions = reconstruct_decisions(events, evidence, topic_ids=topic_ids)
            interactions = extract_interactions(events, evidence, decisions)
            influence = compute_influence(events, evidence, decisions, interactions, transcript_segments=turns)
            variants[name] = participant_features(events, influence, turns)
        for speaker in sorted(variants['full']):
            result.append({'meeting_id': group, 'participant': speaker,
                           'aii': float(speakers[speaker]['AII']),
                           'full': variants['full'][speaker], 'topic': variants['topic'][speaker]})
    return result


def train(args):
    args.output_dir.mkdir(parents=True, exist_ok=False)
    splits = json.loads((ROOT/'outputs/training/gap_influence_20261024/protocol.json').read_text())['splits']
    protocol = {'status': 'Exploratory GAP outcome-alignment ranking; historical cohort previously examined',
                'splits': splits, 'feature_sets': ['seven', 'full', 'topic'],
                'grid': {'max_depth': [1, 2, 3], 'n_estimators': [50, 150], 'reg_lambda': [1, 10]},
                'objective': 'rank:pairwise', 'learning_rate': .05, 'seed': 42,
                'source_sha256': {name: digest(ROOT/name) for name in ['scripts/train_influence_ranker.py',
                    'src/meeting/ranking.py', 'src/meeting/topics.py', 'src/meeting/decisions.py',
                    'src/meeting/influence.py', 'src/meeting/events.py', 'src/meeting/evidence.py',
                    'src/meeting/interaction.py', 'scripts/benchmark_gap_influence.py', 'scripts/train_influence_weights.py']},
                'input_sha256': {name: digest(args.data/name) for name in ['speakers.json', 'utterances.jsonl']},
                'installed_in_application': False}
    save(args.output_dir/'protocol.json', protocol)
    rows = feature_rows(args.data)
    for meeting in sorted({r['meeting_id'] for r in rows}):
        current = [row for row in rows if row['meeting_id'] == meeting]
        ordered = sorted(set(-row['aii'] for row in current))
        for row in current:
            row['target'] = ordered.index(-row['aii'])/max(1, len(ordered)-1)
    save(args.output_dir/'feature_rows.json', rows)
    training = [row for row in rows if row['meeting_id'] in splits['train']]
    development = [row for row in rows if row['meeting_id'] in splits['development']]
    group_ids = {name:i for i, name in enumerate(sorted(splits['train']))}
    training.sort(key=lambda row: (group_ids[row['meeting_id']], row['participant']))
    qids = np.array([group_ids[row['meeting_id']] for row in training])
    labels = np.array([row['target'] for row in training])
    model_class = xgb_ranker_class()
    search, best, best_model = [], None, None
    for feature_set in protocol['feature_sets']:
        names = FEATURE_NAMES[-7:] if feature_set == 'seven' else FEATURE_NAMES
        key = 'topic' if feature_set == 'topic' else 'full'
        x = np.array([[row[key][name] for name in names] for row in training])
        xd = np.array([[row[key][name] for name in names] for row in development])
        for depth in protocol['grid']['max_depth']:
            for estimators in protocol['grid']['n_estimators']:
                for regularization in protocol['grid']['reg_lambda']:
                    model = model_class(objective='rank:pairwise', max_depth=depth, n_estimators=estimators,
                        reg_lambda=regularization, learning_rate=.05, n_jobs=2, random_state=42,
                        tree_method='hist', lambdarank_pair_method='mean', lambdarank_num_pair_per_sample=4)
                    model.fit(x, labels, qid=qids)
                    candidate = {'feature_set': feature_set, 'features': names, 'max_depth': depth,
                                 'n_estimators': estimators, 'reg_lambda': regularization,
                                 'development': score(development, model.predict(xd))}
                    search.append(candidate)
                    if best is None or candidate['development']['meeting_macro_pairwise_accuracy'] > best['development']['meeting_macro_pairwise_accuracy']:
                        best, best_model = candidate, model
    best_model.save_model(args.output_dir/'ranker.ubj')
    metadata = {**best, 'topic_aware': best['feature_set'] == 'topic',
                'model_sha256': digest(args.output_dir/'ranker.ubj'), 'installed_in_application': False}
    save(args.output_dir/'ranker.json', metadata)
    save(args.output_dir/'development_search.json', search)
    print('Frozen XGBoost candidate:', json.dumps(best), flush=True)


def evaluate(args):
    path = args.output_dir/'historical_evaluation.json'
    if path.exists():
        raise ValueError('Historical evaluation already exists; preserve it')
    protocol = json.loads((args.output_dir/'protocol.json').read_text())
    for name, expected in protocol['source_sha256'].items():
        if digest(ROOT/name) != expected:
            raise ValueError('Frozen feature/evaluation source changed')
    metadata = json.loads((args.output_dir/'ranker.json').read_text())
    if digest(args.output_dir/'ranker.ubj') != metadata['model_sha256']:
        raise ValueError('Frozen ranker changed')
    rows = [row for row in json.loads((args.output_dir/'feature_rows.json').read_text())
            if row['meeting_id'] in protocol['splits']['test']]
    key = 'topic' if metadata['topic_aware'] else 'full'
    matrix = np.array([[row[key][name] for name in metadata['features']] for row in rows])
    model = xgb_ranker_class()(); model.load_model(args.output_dir/'ranker.ubj'); model.set_params(n_jobs=2)
    result = {'status': protocol['status'], 'candidate': score(rows, model.predict(matrix)),
              'word_count': score(rows, np.array([row['full']['words'] for row in rows])),
              'installed_in_application': False}
    save(path, result)
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT/'.runtime/research-influence-gap')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--evaluate', action='store_true')
    args = parser.parse_args()
    evaluate(args) if args.evaluate else train(args)


if __name__ == '__main__':
    main()
