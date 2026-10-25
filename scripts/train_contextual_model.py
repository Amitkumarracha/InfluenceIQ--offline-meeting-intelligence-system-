"""Fine-tune the cached compact encoder; preserve app models and select on development only."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
import time

import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, average_precision_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.utils.config import get
from src.meeting.contextual import context_pairs
from src.meeting.discussions import component_scores, combine_scores
from scripts.improve_decision_discussions import smooth_scores

ENCODER = 'sentence-transformers/all-MiniLM-L6-v2'
ROLE_LABELS = ['Proposal', 'Agreement', 'Disagreement', 'Confirmation']
RELATIONS = ['adopted', 'rejected', 'revised', 'unresolved']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def load_data(task, split, manifest=None):
    if task == 'discussion':
        path = ROOT/'.runtime/research-decision-model'/(split+'.jsonl')
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        return rows, np.array([[row['label']] for row in rows], dtype=np.float32), [path]
    if task == 'roles':
        root = ROOT/'.runtime/research-influence-gap'
        speakers = json.loads((root/'speakers.json').read_text())
        splits = json.loads((ROOT/'outputs/training/gap_influence_20261024/protocol.json').read_text())['splits']
        groups = splits['development' if split == 'dev' else split]
        rows, labels = [], []
        for line in (root/'utterances.jsonl').read_text().splitlines():
            row = json.loads(line)
            group = str(speakers[row['speaker']]['Group Number'])
            if group not in groups:
                continue
            minutes, seconds = row['timestamp'].split(':')
            annotation = str(row['meta']['Decision']).split(', ')
            rows.append({'meeting': group, 'group': group, 'act_id': row['id'],
                         'start': float(minutes)*60+float(seconds), 'text': row['text'].strip('"')})
            labels.append([int(label in annotation) for label in ROLE_LABELS])
        return rows, np.array(labels, dtype=np.float32), [root/'speakers.json', root/'utterances.jsonl']
    if manifest is None:
        raise ValueError('Outcome-link training needs an independently annotated --manifest')
    all_rows = [json.loads(line) for line in manifest.read_text().splitlines() if line.strip()]
    groups = {}
    for row in all_rows:
        if row.get('label_source') != 'human' or row.get('relationship') not in RELATIONS:
            raise ValueError('Outcome links require independent human adopted/rejected/revised/unresolved labels')
        if row.get('split') not in {'train', 'dev', 'test'} or not row.get('group'):
            raise ValueError('Each link needs a verified group and train/dev/test split')
        if groups.setdefault(row['group'], row['split']) != row['split']:
            raise ValueError('Team/project groups must not cross splits')
        if not all(isinstance(row.get(key), str) and row[key].strip() for key in ['source_text', 'outcome_text']):
            raise ValueError('Links require source and outcome text')
    rows = [row for row in all_rows if row['split'] == split]
    return rows, np.array([RELATIONS.index(row['relationship']) for row in rows]), [manifest]


def choose_thresholds(labels, scores):
    thresholds, values = [], []
    for column in range(labels.shape[1]):
        candidates = []
        for threshold in np.r_[np.arange(.1, .901, .05), .3577398635496262]:
            p, r, f, _ = precision_recall_fscore_support(labels[:, column], scores[:, column] >= threshold,
                                                       average='binary', zero_division=0)
            candidates.append({'threshold': float(threshold), 'precision': float(p), 'recall': float(r), 'f1': float(f)})
        best = max(candidates, key=lambda row: row['f1'])
        thresholds.append(best['threshold']); values.append(best)
    return thresholds, values


def train(args):
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    random.seed(42); np.random.seed(42); torch.manual_seed(42); torch.set_num_threads(args.threads)
    rows, y, paths = load_data(args.task, 'train', args.manifest)
    development, y_dev, dev_paths = load_data(args.task, 'dev', args.manifest)
    if not rows or not development:
        raise ValueError('Nonempty training and development groups are required')
    if {row['group'] for row in rows} & {row['group'] for row in development}:
        raise ValueError('Training and development groups overlap')
    args.output_dir.mkdir(parents=True, exist_ok=False)
    protocol = {'task': args.task, 'encoder': ENCODER, 'fine_tuning': 'All encoder layers plus new classification head',
                'epochs': args.epochs, 'batch_size': args.batch_size, 'max_length': args.max_length,
                'learning_rate': 2e-5, 'seed': 42, 'context_radius': 2,
                'training_groups': sorted({r['group'] for r in rows}), 'dev_groups': sorted({r['group'] for r in development}),
                'training_examples': len(rows), 'development_examples': len(development),
                'input_sha256': {str(path): sha(path) for path in set(paths+dev_paths)},
                'source_sha256': {name: sha(ROOT/name) for name in ['scripts/train_contextual_model.py', 'src/meeting/contextual.py']},
                'selection': 'Development F1; historical evaluation separate after freezing',
                'status': 'Exploratory development; earlier historical cohorts already examined',
                'installed_in_application': False, 'language': 'en'}
    save(args.output_dir/'protocol.json', protocol)
    tokenizer = AutoTokenizer.from_pretrained(ENCODER, local_files_only=True)
    n_labels = 4 if args.task in {'roles', 'links'} else 1
    model = AutoModelForSequenceClassification.from_pretrained(ENCODER, local_files_only=True, num_labels=n_labels)
    def pairs(values):
        return [(r['source_text'], r['outcome_text']) for r in values] if args.task == 'links' else context_pairs(values)
    def tokenize(values):
        pair = pairs(values)
        return tokenizer([p[0] for p in pair], [p[1] for p in pair], padding='max_length', truncation=True,
                         max_length=args.max_length, return_tensors='pt')
    tokens, dev_tokens = tokenize(rows), tokenize(development)
    labels = torch.tensor(y, dtype=torch.long if args.task == 'links' else torch.float32)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5, weight_decay=.01)
    steps = args.epochs*int(np.ceil(len(rows)/args.batch_size))
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda step: min((step+1)/max(1, steps*.1), max(0, (steps-step)/max(1, steps*.9))))
    baseline = None
    if args.task == 'discussion':
        import joblib
        bundle = joblib.load(ROOT/'models/discussion/model.joblib')
        baseline = combine_scores(development, component_scores(development, bundle),
                                  bundle['linear_weight'], bundle['smoothing_radius'])
        save(args.output_dir/'baseline.json', {'model_sha256': sha(ROOT/'models/discussion/model.joblib')})
    best_value, history, started = -1, [], time.perf_counter()
    for epoch in range(args.epochs):
        model.train(); order = torch.randperm(len(rows)); running = 0.
        for step, start in enumerate(range(0, len(rows), args.batch_size)):
            indices = order[start:start+args.batch_size]
            optimizer.zero_grad(set_to_none=True)
            logits = model(**{key: value[indices] for key, value in tokens.items()}).logits
            loss = (torch.nn.functional.cross_entropy(logits, labels[indices]) if args.task == 'links' else
                    torch.nn.functional.binary_cross_entropy_with_logits(logits, labels[indices]))
            loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.); optimizer.step(); scheduler.step()
            running += float(loss.detach())
            if step % 50 == 0:
                print(json.dumps({'epoch': epoch+1, 'examples': min(start+args.batch_size, len(rows)),
                                  'total': len(rows), 'mean_loss': running/(step+1),
                                  'elapsed_seconds': round(time.perf_counter()-started, 1)}), flush=True)
        model.eval(); predictions = []
        with torch.inference_mode():
            for start in range(0, len(development), args.batch_size):
                logits = model(**{key: value[start:start+args.batch_size] for key, value in dev_tokens.items()}).logits
                predictions.append((logits.softmax(-1) if args.task == 'links' else logits.sigmoid()).numpy())
        scores = np.vstack(predictions)
        if args.task == 'links':
            f1 = float(precision_recall_fscore_support(y_dev, scores.argmax(1), average='macro', zero_division=0)[2])
            selection = {'macro_f1': f1}
        else:
            thresholds, values = choose_thresholds(y_dev, scores)
            selection = {'thresholds': thresholds, 'per_label': values, 'macro_f1': float(np.mean([v['f1'] for v in values]))}
            f1 = selection['macro_f1']
            if baseline is not None:
                candidates = []
                for radius in [0, 5]:
                    smoothed = smooth_scores(development, scores[:, 0], radius)
                    for weight in [0., .25, .5, .75, 1.]:
                        blended = weight*smoothed+(1-weight)*baseline
                        thresholds, values = choose_thresholds(y_dev, blended[:, None])
                        candidates.append({'neural_weight': weight, 'smoothing_radius': radius,
                                           'threshold': thresholds[0], 'metrics': values[0]})
                blend = max(candidates, key=lambda v: v['metrics']['f1'])
                selection['blend'] = blend; f1 = blend['metrics']['f1']
        history.append({'epoch': epoch+1, 'development': selection})
        save(args.output_dir/'history.json', history)
        if f1 > best_value:
            best_value = f1
            model.save_pretrained(args.output_dir/'model', safe_serialization=True)
            tokenizer.save_pretrained(args.output_dir/'model')
            np.save(args.output_dir/'dev_scores.npy', scores)
            save(args.output_dir/'selection.json', {'epoch': epoch+1, 'development': selection,
                'labels': ROLE_LABELS if args.task == 'roles' else RELATIONS if args.task == 'links' else ['discussion'],
                'model_sha256': sha(args.output_dir/'model/model.safetensors'), 'installed_in_application': False})
        print('Epoch development selection:', json.dumps(history[-1]), flush=True)


def evaluate(args):
    import torch
    from src.meeting.contextual import predict_pairs
    torch.set_num_threads(args.threads)
    target = args.output_dir/'historical_evaluation.json'
    if target.exists():
        raise ValueError('Historical evaluation already exists; preserve it')
    protocol = json.loads((args.output_dir/'protocol.json').read_text())
    selection = json.loads((args.output_dir/'selection.json').read_text())
    if protocol['task'] != args.task or sha(args.output_dir/'model/model.safetensors') != selection['model_sha256']:
        raise ValueError('Task/model differs from frozen selection')
    for name, expected in protocol['source_sha256'].items():
        if sha(ROOT/name) != expected:
            raise ValueError('Evaluation source changed after freezing')
    rows, labels, _ = load_data(args.task, 'test', args.manifest)
    pairs = [(r['source_text'], r['outcome_text']) for r in rows] if args.task == 'links' else context_pairs(rows)
    scores = predict_pairs(args.output_dir/'model', pairs, protocol['max_length'], args.batch_size, args.task == 'links')
    np.save(args.output_dir/'historical_scores.npy', scores)
    if args.task == 'links':
        predicted = scores.argmax(1)
        result = {'accuracy': float(accuracy_score(labels, predicted)),
                  'macro_f1': float(precision_recall_fscore_support(labels, predicted, average='macro', zero_division=0)[2])}
    else:
        predictions = scores >= np.array(selection['development']['thresholds'])
        values = [precision_recall_fscore_support(labels[:, i], predictions[:, i], average='binary', zero_division=0)[:3]
                  for i in range(labels.shape[1])]
        result = {'per_label': {name: dict(zip(['precision', 'recall', 'f1'], map(float, values[i])))
                               for i, name in enumerate(selection['labels'])},
                  'macro_f1': float(np.mean([value[2] for value in values]))}
        if args.task == 'discussion':
            import joblib
            chosen = selection['development']['blend']
            bundle = joblib.load(ROOT/'models/discussion/model.joblib')
            baseline = combine_scores(rows, component_scores(rows, bundle), bundle['linear_weight'], bundle['smoothing_radius'])
            blended = chosen['neural_weight']*smooth_scores(rows, scores[:, 0], chosen['smoothing_radius'])+(1-chosen['neural_weight'])*baseline
            p, r, f, _ = precision_recall_fscore_support(labels[:, 0], blended >= chosen['threshold'], average='binary', zero_division=0)
            result['frozen_blend'] = {'accuracy': float(accuracy_score(labels[:, 0], blended >= chosen['threshold'])),
                                    'precision': float(p), 'recall': float(r), 'f1': float(f),
                                    'average_precision': float(average_precision_score(labels[:, 0], blended)), **chosen}
    save(target, {'status': protocol['status'], 'examples': len(rows), 'metrics': result, 'installed_in_application': False})
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', choices=['discussion', 'roles', 'links'], required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--epochs', type=int, default=2)
    parser.add_argument('--batch-size', type=int, default=24)
    parser.add_argument('--max-length', type=int, default=96)
    parser.add_argument('--threads', type=int, default=2)
    parser.add_argument('--evaluate', action='store_true')
    args = parser.parse_args()
    if min(args.epochs, args.batch_size, args.max_length, args.threads) < 1:
        parser.error('Training limits must be positive')
    evaluate(args) if args.evaluate else train(args)


if __name__ == '__main__':
    main()
