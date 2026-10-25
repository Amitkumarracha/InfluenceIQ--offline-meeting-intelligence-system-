"""Learn nonnegative fusion/influence weights from human ratings; never self-label.

Input: JSONL, one row per participant, with meeting_id, participant, split
(train/validation/test), label_source='human', human_score in [0,1], and
features containing the seven raw feature counts. Include every participant
in each meeting so max-normalization matches inference. Output is a research
artifact; neither application installs these weights automatically.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.stats import spearmanr, kendalltau

KEYS = ['proposal', 'evidence', 'objection', 'revision', 'decision', 'interaction', 'slide_grounding']
DEFAULT = np.array([.15, .20, .15, .20, .15, .05, .10])


def load_rows(path):
    rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    meetings, seen, groups, meeting_groups = {}, set(), {}, {}
    grouped = any('group_id' in row for row in rows)
    for row in rows:
        meeting, participant, split = row.get('meeting_id'), row.get('participant'), row.get('split')
        if not isinstance(meeting, str) or not meeting or not isinstance(participant, str) or not participant:
            raise ValueError('Every row needs a meeting_id and participant')
        if split not in {'train', 'validation', 'test'} or meetings.setdefault(meeting, split) != split:
            raise ValueError('Keep each complete meeting in exactly one split')
        if grouped:
            group = row.get('group_id')
            if not isinstance(group, str) or not group.strip():
                raise ValueError('Supply a verified group_id for every participant')
            if groups.setdefault(group, split) != split:
                raise ValueError('Keep each team/project group in exactly one split')
            if meeting_groups.setdefault(meeting, group) != group:
                raise ValueError('Participants in one meeting must share one group_id')
        if (meeting, participant) in seen:
            raise ValueError('Duplicate meeting/participant')
        seen.add((meeting, participant))
        if row.get('label_source') != 'human':
            raise ValueError('Independent human labels are required; pipeline outputs are not ground truth')
        score = row.get('human_score')
        if isinstance(score, bool) or not isinstance(score, (float, int)) or not np.isfinite(score) or not 0 <= score <= 1:
            raise ValueError('human_score must be a finite rating normalized to [0,1]')
        features = row.get('features', {})
        if set(features) != set(KEYS):
            raise ValueError('Supply all seven named feature counts')
        vector = np.array([features[key] for key in KEYS], dtype=float)
        if not np.all(np.isfinite(vector)) or np.any(vector < 0):
            raise ValueError('Feature counts must be finite and nonnegative')
        row['vector'] = vector
    for split, minimum in [('train', 2), ('validation', 1), ('test', 1)]:
        if sum(value == split for value in meetings.values()) < minimum:
            raise ValueError(f'{split} needs at least {minimum} complete meeting(s); these are smoke minimums, not a publication sample size')
    for meeting in meetings:
        group = [row for row in rows if row['meeting_id'] == meeting]
        maximum = np.max([row['vector'] for row in group], axis=0)
        for row in group:
            row['vector'] = np.divide(row['vector'], maximum, out=np.zeros(7), where=maximum > 0)
    if not any(np.any(row['vector']) for row in rows if row['split'] == 'train'):
        raise ValueError('Training data has no observed contributions')
    return rows


def metrics(rows, weights):
    errors, ranks = [], []
    for meeting in sorted({row['meeting_id'] for row in rows}):
        group = [row for row in rows if row['meeting_id'] == meeting]
        reference = np.array([row['human_score'] for row in group])
        prediction = np.array([row['vector'] @ weights for row in group])
        errors.extend((reference - prediction) ** 2)
        usable = len(group) >= 2 and np.ptp(reference) > 0 and np.ptp(prediction) > 0
        pairs = [(i, j) for i in range(len(group)) for j in range(i+1, len(group))
                 if reference[i] != reference[j]]
        correct = sum(0.5 if prediction[i] == prediction[j] else
                      float((prediction[i] > prediction[j]) == (reference[i] > reference[j]))
                      for i, j in pairs)
        top_match = (set(np.flatnonzero(prediction == prediction.max())) ==
                     set(np.flatnonzero(reference == reference.max()))) if pairs else None
        ranks.append({'meeting_id': meeting, 'participants': len(group),
                      'spearman': float(spearmanr(reference, prediction).statistic) if usable else None,
                      'kendall_tau': float(kendalltau(reference, prediction).statistic) if usable else None,
                      'comparable_pairs': len(pairs),
                      'human_tied_pairs': len(group)*(len(group)-1)//2 - len(pairs),
                      'pairwise_accuracy': correct / len(pairs) if pairs else None,
                      'top_set_correct': top_match,
                      'rank_status': 'ok' if usable else 'insufficient_or_tied_ratings'})
    pairwise = [r['pairwise_accuracy'] for r in ranks if r['pairwise_accuracy'] is not None]
    top = [r['top_set_correct'] for r in ranks if r['top_set_correct'] is not None]
    return {'participant_mse': float(np.mean(errors)), 'meetings': ranks,
            'meeting_macro_pairwise_accuracy': float(np.mean(pairwise)) if pairwise else None,
            'top_set_accuracy': float(np.mean(top)) if top else None,
            'pairwise_policy': 'Human ties excluded; predicted ties receive half credit; equal meeting weighting',
            'top_policy': 'Predicted top set must exactly match human top set; all-human-tied meetings excluded'}


def train(rows):
    training = [row for row in rows if row['split'] == 'train']
    x = np.array([row['vector'] for row in training]); y = np.array([row['human_score'] for row in training])
    fit = minimize(lambda weights: np.mean((x @ weights - y) ** 2), DEFAULT,
                   jac=lambda weights: 2 * x.T @ (x @ weights - y) / len(y),
                   method='SLSQP', bounds=[(0, 1)] * 7,
                   constraints=[{'type': 'eq', 'fun': lambda weights: weights.sum() - 1,
                                 'jac': lambda weights: np.ones(7)}],
                   options={'maxiter': 1000, 'ftol': 1e-10})
    if not fit.success:
        raise ValueError('Weight optimization failed: ' + fit.message)
    result = {'method': 'human_supervised_nonnegative_sum_one_weights_v1',
              'feature_keys': KEYS, 'weights': dict(zip(KEYS, map(float, fit.x))),
              'normalization': 'Max per feature across all observed participants within a meeting',
              'training_meetings': sorted({row['meeting_id'] for row in training}),
              'group_separation': 'declared_groups_disjoint' if all('group_id' in row for row in rows)
                                  else 'not_verified_meeting_separation_only',
              'active_training_features': [key for i, key in enumerate(KEYS) if np.any(x[:, i])],
              'metrics': {}, 'installed_in_application': False,
              'limitations': ['Human ratings measure annotated influence, not causal truth.',
                              'Split complete meetings; additionally separate speakers/teams/sites for stronger generalization.',
                              'Features depend on ASR, diarization, events and fusion quality.',
                              'Android and server feature extraction differ; train/evaluate each method separately.']}
    for split in ['train', 'validation', 'test']:
        group = [row for row in rows if row['split'] == split]
        ablations = {}
        for i, key in enumerate(KEYS):
            weights = fit.x.copy(); weights[i] = 0
            ablations['without_' + key] = metrics(group, weights)
        result['metrics'][split] = {'learned': metrics(group, fit.x), 'prototype_weights': metrics(group, DEFAULT),
                                   'decision_count_baseline': metrics(group, np.eye(7)[4]),
                                   'equal_weights_baseline': metrics(group, np.ones(7)/7),
                                   'ablations_zero_feature_no_renormalization': ablations}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = train(load_rows(args.manifest))
    except (ValueError, TypeError, KeyError) as error:
        parser.error(str(error))
    result['manifest_sha256'] = hashlib.sha256(args.manifest.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print('Saved research weights and held-out evaluation:', args.output)


if __name__ == '__main__':
    main()
