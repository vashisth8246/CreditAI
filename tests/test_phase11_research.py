import numpy as np
import pytest

from src.research.phase11.core import (
    apply_isotonic,
    apply_platt,
    expected_calibration_error,
    fit_isotonic,
    fit_platt,
    probability_metrics,
    reliability_bins,
    select_review_margin,
    selective_metrics,
)


def test_reliability_metrics_are_bounded_and_bins_cover_data():
    y = np.array([0, 0, 1, 1])
    p = np.array([0.1, 0.4, 0.6, 0.9])
    bins = reliability_bins(y, p, n_bins=4)
    assert sum(row["count"] for row in bins) == len(y)
    assert expected_calibration_error(y, p, n_bins=4) == pytest.approx(0.25)
    result = probability_metrics(y, p)
    assert set(result) == {"roc_auc", "pr_auc_average_precision", "brier_score", "log_loss", "ece_10_equal_width"}
    assert all(0 <= result[key] <= 1 for key in ("roc_auc", "pr_auc_average_precision", "brier_score", "ece_10_equal_width"))


def test_calibrators_fit_validation_and_return_valid_probabilities():
    y = np.array([0, 0, 0, 1, 1, 1] * 10)
    raw = np.tile(np.array([0.1, 0.3, 0.4, 0.6, 0.7, 0.9]), 10)
    assert np.all((apply_platt(fit_platt(raw, y), raw) >= 0) & (apply_platt(fit_platt(raw, y), raw) <= 1))
    isotonic = apply_isotonic(fit_isotonic(raw, y), raw)
    assert np.all((isotonic >= 0) & (isotonic <= 1))
    assert np.all(np.diff(isotonic[np.argsort(raw)]) >= 0)


def test_review_margin_meets_validation_coverage_and_reports_test_risk():
    y = np.array([0, 0, 1, 1, 0, 1])
    p = np.array([0.1, 0.45, 0.55, 0.9, 0.51, 0.49])
    margin, candidates = select_review_margin(y, p, min_coverage=2 / 3, candidates=[0.0, 0.05, 0.1])
    assert margin in {0.0, 0.05, 0.1}
    assert all(row["coverage"] >= 2 / 3 for row in candidates)
    result = selective_metrics(y, p, margin)
    assert result["n_accepted"] + result["n_referred"] == len(y)
    assert 0 <= result["selective_risk_error_rate"] <= 1


@pytest.mark.parametrize("bad", [[], [0.1, np.nan], [0.1, 1.2]])
def test_invalid_probability_inputs_are_rejected(bad):
    with pytest.raises(ValueError):
        probability_metrics([0, 1] if len(bad) != 0 else [], bad)
