"""Calibration and selective-review metrics for controlled Phase 11 research."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.calibration import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score


def _validated_arrays(y_true: Any, probabilities: Any) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(y_true, dtype=int).reshape(-1)
    p = np.asarray(probabilities, dtype=float).reshape(-1)
    if y.size == 0 or y.size != p.size:
        raise ValueError("Labels and probabilities must be non-empty arrays of equal length.")
    if not np.isin(y, [0, 1]).all():
        raise ValueError("Labels must be binary values 0 and 1.")
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Probabilities must be finite values in [0, 1].")
    if np.unique(y).size < 2:
        raise ValueError("Both binary classes must be present.")
    return y, p


def reliability_bins(y_true: Any, probabilities: Any, n_bins: int = 10) -> list[dict[str, float | int]]:
    """Equal-width reliability bins; empty bins are omitted."""
    if n_bins < 1:
        raise ValueError("n_bins must be at least 1.")
    y, p = _validated_arrays(y_true, probabilities)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins: list[dict[str, float | int]] = []
    indices = np.minimum(np.floor(p * n_bins).astype(int), n_bins - 1)
    for index in range(n_bins):
        mask = indices == index
        if not mask.any():
            continue
        bins.append({
            "bin": index + 1,
            "lower": float(edges[index]),
            "upper": float(edges[index + 1]),
            "count": int(mask.sum()),
            "mean_predicted": float(p[mask].mean()),
            "observed_rate": float(y[mask].mean()),
        })
    return bins


def expected_calibration_error(y_true: Any, probabilities: Any, n_bins: int = 10) -> float:
    """Weighted absolute gap between mean predicted risk and observed rate."""
    y, p = _validated_arrays(y_true, probabilities)
    return float(sum(
        (item["count"] / len(y)) * abs(item["observed_rate"] - item["mean_predicted"])
        for item in reliability_bins(y, p, n_bins)
    ))


def probability_metrics(y_true: Any, probabilities: Any, n_bins: int = 10) -> dict[str, float]:
    y, p = _validated_arrays(y_true, probabilities)
    clipped = np.clip(p, 1e-15, 1 - 1e-15)
    return {
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc_average_precision": float(average_precision_score(y, p)),
        "brier_score": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, clipped, labels=[0, 1])),
        "ece_10_equal_width": expected_calibration_error(y, p, n_bins),
    }


def fit_platt(raw_probabilities: Any, y_validation: Any) -> LogisticRegression:
    """Fit sigmoid calibration on clipped raw-probability logits and validation labels."""
    y, p = _validated_arrays(y_validation, raw_probabilities)
    logits = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
    calibrator = LogisticRegression(C=1e6, solver="lbfgs", max_iter=1000, random_state=42)
    calibrator.fit(logits.reshape(-1, 1), y)
    return calibrator


def apply_platt(calibrator: LogisticRegression, raw_probabilities: Any) -> np.ndarray:
    p = np.asarray(raw_probabilities, dtype=float).reshape(-1)
    logits = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
    return calibrator.predict_proba(logits.reshape(-1, 1))[:, 1]


def fit_isotonic(raw_probabilities: Any, y_validation: Any) -> IsotonicRegression:
    y, p = _validated_arrays(y_validation, raw_probabilities)
    return IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip").fit(p, y)


def apply_isotonic(calibrator: IsotonicRegression, raw_probabilities: Any) -> np.ndarray:
    p = np.asarray(raw_probabilities, dtype=float).reshape(-1)
    return np.asarray(calibrator.predict(p), dtype=float)


def selective_metrics(y_true: Any, probabilities: Any, review_margin: float) -> dict[str, float | int]:
    """Defer cases within |PD - 0.5| < margin; report accepted-set 0.5-threshold error."""
    y, p = _validated_arrays(y_true, probabilities)
    if not 0.0 <= review_margin < 0.5:
        raise ValueError("review_margin must be in [0, 0.5).")
    accepted = np.abs(p - 0.5) >= review_margin
    if not accepted.any():
        raise ValueError("The review rule deferred every observation.")
    predicted = (p[accepted] >= 0.5).astype(int)
    errors = int(np.count_nonzero(predicted != y[accepted]))
    coverage = float(accepted.mean())
    return {
        "review_margin": float(review_margin),
        "n_total": int(len(y)),
        "n_accepted": int(accepted.sum()),
        "n_referred": int((~accepted).sum()),
        "coverage": coverage,
        "referred_fraction": float(1.0 - coverage),
        "selective_risk_error_rate": float(errors / accepted.sum()),
        "accepted_errors": errors,
    }


def select_review_margin(
    y_validation: Any,
    probabilities: Any,
    min_coverage: float = 0.80,
    candidates: Any | None = None,
) -> tuple[float, list[dict[str, float | int]]]:
    """Choose the lowest validation error among candidate rules meeting fixed coverage."""
    y, p = _validated_arrays(y_validation, probabilities)
    if not 0.0 < min_coverage <= 1.0:
        raise ValueError("min_coverage must be in (0, 1].")
    grid = np.asarray(candidates if candidates is not None else np.linspace(0.0, 0.49, 50), dtype=float)
    if grid.size == 0 or not np.isfinite(grid).all() or ((grid < 0) | (grid >= 0.5)).any():
        raise ValueError("Candidate margins must be finite values in [0, 0.5).")
    eligible = []
    for margin in grid:
        try:
            row = selective_metrics(y, p, float(margin))
        except ValueError:  # A candidate that refers everyone cannot meet positive coverage.
            continue
        if row["coverage"] >= min_coverage:
            eligible.append(row)
    if not eligible:
        raise ValueError("No candidate review margin meets the minimum validation coverage.")
    chosen = min(eligible, key=lambda row: (row["selective_risk_error_rate"], -row["coverage"], row["review_margin"]))
    return float(chosen["review_margin"]), eligible
