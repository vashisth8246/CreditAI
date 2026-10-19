"""Validation-set Platt scaling for probability outputs."""
import numpy as np
from scipy.special import expit
from sklearn.linear_model import LogisticRegression


class PlattCalibrator:
    """Validation-fit sigmoid constrained to be non-decreasing in raw PD."""

    def __init__(self):
        self._slope = 0.0
        self._intercept = 0.0
        self.model = None

    @property
    def slope(self) -> float:
        if hasattr(self, "_slope") and self._slope != 0.0:
            return self._slope
        if hasattr(self, "model") and self.model is not None and hasattr(self.model, "coef_"):
            return max(0.0, float(self.model.coef_[0, 0]))
        return getattr(self, "_slope", 0.0)

    @slope.setter
    def slope(self, value: float):
        self._slope = float(value)

    @property
    def intercept(self) -> float:
        if hasattr(self, "_intercept") and self._intercept != 0.0:
            return self._intercept
        if hasattr(self, "model") and self.model is not None and hasattr(self.model, "intercept_"):
            return float(self.model.intercept_[0])
        return getattr(self, "_intercept", 0.0)

    @intercept.setter
    def intercept(self, value: float):
        self._intercept = float(value)

    def __setstate__(self, state):
        self.__dict__.update(state)
        if "model" in state and hasattr(state["model"], "coef_"):
            self._slope = max(0.0, float(state["model"].coef_[0, 0]))
            self._intercept = float(state["model"].intercept_[0])
        else:
            if "_slope" not in self.__dict__:
                self._slope = getattr(self, "slope", 0.0)
            if "_intercept" not in self.__dict__:
                self._intercept = getattr(self, "intercept", 0.0)

    @staticmethod
    def _logit(p):
        p = np.clip(np.asarray(p, dtype=float), 1e-6, 1.0 - 1e-6)
        return np.log(p / (1.0 - p)).reshape(-1, 1)

    def fit(self, probabilities, y):
        y = np.asarray(y, dtype=int)
        z = self._logit(probabilities)
        model = LogisticRegression(C=1e6, solver="lbfgs", random_state=42).fit(z, y)
        self.slope = max(0.0, float(model.coef_[0, 0]))
        self.intercept = (
            float(model.intercept_[0])
            if self.slope > 0
            else float(
                np.log(
                    np.clip(y.mean(), 1e-6, 1 - 1e-6)
                    / (1 - np.clip(y.mean(), 1e-6, 1 - 1e-6))
                )
            )
        )
        self.model = model
        return self

    def predict_proba(self, probabilities):
        probs = np.asarray(probabilities, dtype=float)
        # Handle 2D inputs like [[p]] or (N, 1) or (N, 2)
        if probs.ndim == 2 and probs.shape[1] == 1:
            probs = probs.reshape(-1)
        elif probs.ndim == 2 and probs.shape[1] == 2:
            probs = probs[:, 1]
        z = self._logit(probs).reshape(-1)
        calibrated = expit(self.slope * z + self.intercept)
        return calibrated
