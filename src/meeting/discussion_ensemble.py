"""Small probability ensemble compatible with the existing discussion pipeline."""
import numpy as np


class ProbabilityEnsemble:
    def __init__(self, estimators, weights):
        self.estimators = estimators
        self.weights = np.asarray(weights, dtype=float)
        if (len(estimators) != len(weights) or not np.isfinite(self.weights).all()
                or np.any(self.weights < 0) or not np.isclose(self.weights.sum(), 1.)):
            raise ValueError('Ensemble weights must be nonnegative and sum to one')
        self.classes_ = np.array([0, 1])
        if any(not np.array_equal(model.classes_, self.classes_) for model in estimators):
            raise ValueError('Ensemble class order must be [0, 1]')

    def predict_proba(self, matrix):
        return sum(weight*model.predict_proba(matrix) for weight, model in zip(self.weights, self.estimators))
