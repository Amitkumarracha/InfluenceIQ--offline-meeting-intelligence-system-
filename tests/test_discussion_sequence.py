import numpy as np

from src.meeting.discussion_sequence import learn_rates, sequence_scores


def test_sequence_scores_respect_meeting_boundaries_and_ignore_outcome_labels():
    rows = [{'meeting':'A','start':0.,'end':1.,'label':0},
            {'meeting':'B','start':0.,'end':1.,'label':1}]
    scores = sequence_scores(rows,np.array([.8,.2]),[.1,.1])
    np.testing.assert_allclose(scores,[.8,.2])
    for row in rows:row['label']=1
    np.testing.assert_allclose(sequence_scores(rows,np.array([.8,.2]),[.1,.1]),scores)


def test_continuity_strength_decays_with_real_elapsed_time():
    close = [{'meeting':'A','start':t,'end':t+1} for t in [0.,1.,2.]]
    distant = [{'meeting':'A','start':t,'end':t+1} for t in [0.,1000.,2000.]]
    raw=np.array([.9,.4,.9])
    assert sequence_scores(close,raw,[.1,.1])[1] > raw[1]
    np.testing.assert_allclose(sequence_scores(distant,raw,[.1,.1]),raw,atol=1e-6)
    assert np.isfinite(sequence_scores(close,np.array([0.,1.,1.]),[.1,.1])).all()


def test_transition_rates_learn_only_within_meetings_and_remain_positive():
    rows=[{'meeting':'A','start':0.,'label':0},{'meeting':'B','start':0.,'label':1}]
    np.testing.assert_allclose(learn_rates(rows),[.1,.1])
