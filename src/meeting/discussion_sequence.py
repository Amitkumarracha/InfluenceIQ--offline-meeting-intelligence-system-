"""Time-aware, two-state discussion continuity learned from training annotations."""
import numpy as np

from src.meeting.discussions import ordered_meetings


def learn_rates(rows):
    counts, exposure = np.ones(2), np.full(2, 10.)
    for indices in ordered_meetings(rows):
        for first, second in zip(indices[:-1], indices[1:]):
            state = rows[first]['label']
            dt = max(.05, rows[second]['start']-rows[first]['start'])
            exposure[state] += dt
            counts[state] += rows[first]['label'] != rows[second]['label']
    return (counts/exposure).tolist()


def sequence_scores(rows, raw, rates, speed=1., power=1.):
    """Forward/backward scores; transition decay follows real elapsed seconds."""
    if len(rows) != len(raw) or any(rate <= 0 for rate in rates) or speed <= 0 or power <= 0:
        raise ValueError('Invalid discussion sequence inputs')
    result = np.empty(len(rows))
    rate01, rate10 = np.asarray(rates)*speed
    pi1 = rate01/(rate01+rate10)
    pi = np.array([1-pi1, pi1])
    raw = np.clip(raw, 1e-6, 1-1e-6)
    for indices in ordered_meetings(rows):
        probabilities = raw[indices]
        emission = power*np.column_stack([np.log1p(-probabilities), np.log(probabilities)])
        forward = np.empty((len(indices), 2)); backward = np.zeros_like(forward)
        forward[0] = np.log(pi)+emission[0]
        times = np.array([rows[i]['start'] for i in indices])
        decay = np.exp(-(rate01+rate10)*np.maximum(.05, np.diff(times)))
        transition = np.empty((len(decay), 2, 2))
        transition[:, 0, 0] = pi[0]+pi[1]*decay
        transition[:, 0, 1] = pi[1]*(1-decay)
        transition[:, 1, 0] = pi[0]*(1-decay)
        transition[:, 1, 1] = pi[1]+pi[0]*decay
        transition = np.log(np.clip(transition, 1e-12, 1.))
        for i in range(1, len(indices)):
            values = forward[i-1][:, None]+transition[i-1]
            forward[i] = np.logaddexp(values[0], values[1])+emission[i]
        for i in range(len(indices)-2, -1, -1):
            values = transition[i]+emission[i+1]+backward[i+1]
            backward[i] = np.logaddexp(values[:, 0], values[:, 1])
        log_posterior = forward+backward
        result[indices] = np.exp(log_posterior[:, 1]-np.logaddexp(log_posterior[:, 0], log_posterior[:, 1]))
    return result
