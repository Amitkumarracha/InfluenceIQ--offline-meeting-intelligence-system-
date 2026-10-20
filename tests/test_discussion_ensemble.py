from types import SimpleNamespace

import numpy as np
import pytest

from src.meeting.discussion_ensemble import ProbabilityEnsemble


def test_ensemble_preserves_class_order_and_weighted_probabilities():
    def model(prob):return SimpleNamespace(classes_=np.array([0,1]),predict_proba=lambda x:np.tile([1-prob,prob],(len(x),1)))
    result=ProbabilityEnsemble([model(.2),model(.8)],[.25,.75]).predict_proba([1,2])
    np.testing.assert_allclose(result,[[.35,.65],[.35,.65]])
    with pytest.raises(ValueError):ProbabilityEnsemble([model(.2)],[.5])
    with pytest.raises(ValueError):ProbabilityEnsemble([SimpleNamespace(classes_=np.array([1,0]))],[1.])
