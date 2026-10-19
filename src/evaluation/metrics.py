"""Metric computation utilities for credit risk evaluation.

This module provides interfaces for computing standard credit risk metrics
without fitting any models. Metrics are computed from pre-existing predictions
and labels.

This phase does NOT train models—it only computes metrics on provided predictions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import numpy as np
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    log_loss,
    confusion_matrix,
    precision_recall_curve,
)


@dataclass
class MetricResult:
    """Result of metric computation."""
    metric_name: str
    value: float | None
    available: bool
    details: dict[str, Any] | None = None


def compute_roc_auc(y_true: np.ndarray, y_score: np.ndarray) -> MetricResult:
    """Compute ROC-AUC.

    Args:
        y_true: True binary labels (0 or 1).
        y_score: Predicted probabilities or scores.

    Returns:
        MetricResult with ROC-AUC value or None if unavailable.
    """
    try:
        # Check if there are both classes present
        if len(np.unique(y_true)) < 2:
            return MetricResult(
                metric_name="roc_auc",
                value=None,
                available=False,
                details={"reason": "Only one class present in y_true"}
            )

        value = roc_auc_score(y_true, y_score)
        return MetricResult(
            metric_name="roc_auc",
            value=float(value),
            available=True
        )
    except Exception as e:
        return MetricResult(
            metric_name="roc_auc",
            value=None,
            available=False,
            details={"reason": str(e)}
        )


def compute_pr_auc(y_true: np.ndarray, y_score: np.ndarray) -> MetricResult:
    """Compute average precision (PR-AUC).

    Args:
        y_true: True binary labels (0 or 1).
        y_score: Predicted probabilities or scores.

    Returns:
        MetricResult with PR-AUC value or None if unavailable.
    """
    try:
        # Check if there are both classes present
        if len(np.unique(y_true)) < 2:
            return MetricResult(
                metric_name="pr_auc",
                value=None,
                available=False,
                details={"reason": "Only one class present in y_true"}
            )

        value = average_precision_score(y_true, y_score)
        return MetricResult(
            metric_name="pr_auc",
            value=float(value),
            available=True
        )
    except Exception as e:
        return MetricResult(
            metric_name="pr_auc",
            value=None,
            available=False,
            details={"reason": str(e)}
        )


def compute_brier_score(y_true: np.ndarray, y_score: np.ndarray) -> MetricResult:
    """Compute Brier score.

    Args:
        y_true: True binary labels (0 or 1).
        y_score: Predicted probabilities.

    Returns:
        MetricResult with Brier score value or None if unavailable.
    """
    try:
        value = brier_score_loss(y_true, y_score)
        return MetricResult(
            metric_name="brier_score",
            value=float(value),
            available=True
        )
    except Exception as e:
        return MetricResult(
            metric_name="brier_score",
            value=None,
            available=False,
            details={"reason": str(e)}
        )


def compute_log_loss(y_true: np.ndarray, y_score: np.ndarray) -> MetricResult:
    """Compute log loss.

    Args:
        y_true: True binary labels (0 or 1).
        y_score: Predicted probabilities (must be in (0, 1) range).

    Returns:
        MetricResult with log loss value or None if unavailable.
    """
    try:
        # Check for probabilities at exact 0 or 1 boundaries
        if np.any((y_score <= 0) | (y_score >= 1)):
            return MetricResult(
                metric_name="log_loss",
                value=None,
                available=False,
                details={"reason": "Probabilities must be in (0, 1) range for log loss"}
            )

        value = log_loss(y_true, y_score)
        return MetricResult(
            metric_name="log_loss",
            value=float(value),
            available=True
        )
    except Exception as e:
        return MetricResult(
            metric_name="log_loss",
            value=None,
            available=False,
            details={"reason": str(e)}
        )


def compute_ks_statistic(y_true: np.ndarray, y_score: np.ndarray) -> MetricResult:
    """Compute Kolmogorov-Smirnov statistic.

    Args:
        y_true: True binary labels (0 or 1).
        y_score: Predicted probabilities or scores.

    Returns:
        MetricResult with KS statistic value or None if unavailable.
    """
    try:
        # Check if there are both classes present
        if len(np.unique(y_true)) < 2:
            return MetricResult(
                metric_name="ks_statistic",
                value=None,
                available=False,
                details={"reason": "Only one class present in y_true"}
            )

        # Sort by score
        sorted_indices = np.argsort(y_score)[::-1]
        y_true_sorted = y_true[sorted_indices]

        # Cumulative sums
        cumulative_good = np.cumsum(y_true_sorted == 0)
        cumulative_bad = np.cumsum(y_true_sorted == 1)

        # Normalize
        total_good = np.sum(y_true == 0)
        total_bad = np.sum(y_true == 1)

        if total_good == 0 or total_bad == 0:
            return MetricResult(
                metric_name="ks_statistic",
                value=None,
                available=False,
                details={"reason": "One class has zero samples"}
            )

        cumulative_good_pct = cumulative_good / total_good
        cumulative_bad_pct = cumulative_bad / total_bad

        # Maximum separation
        ks = np.max(np.abs(cumulative_good_pct - cumulative_bad_pct))

        return MetricResult(
            metric_name="ks_statistic",
            value=float(ks),
            available=True
        )
    except Exception as e:
        return MetricResult(
            metric_name="ks_statistic",
            value=None,
            available=False,
            details={"reason": str(e)}
        )


def compute_gini_coefficient(y_true: np.ndarray, y_score: np.ndarray) -> MetricResult:
    """Compute Gini coefficient (2 * ROC-AUC - 1).

    Args:
        y_true: True binary labels (0 or 1).
        y_score: Predicted probabilities or scores.

    Returns:
        MetricResult with Gini coefficient value or None if unavailable.
    """
    roc_result = compute_roc_auc(y_true, y_score)
    if not roc_result.available or roc_result.value is None:
        return MetricResult(
            metric_name="gini_coefficient",
            value=None,
            available=False,
            details={"reason": "ROC-AUC unavailable"}
        )

    gini = 2 * roc_result.value - 1
    return MetricResult(
        metric_name="gini_coefficient",
        value=float(gini),
        available=True
    )


def compute_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Compute confusion matrix at a given threshold.

    Args:
        y_true: True binary labels (0 or 1).
        y_pred: Predicted probabilities.
        threshold: Classification threshold.

    Returns:
        Dictionary with confusion matrix components and derived metrics.
    """
    try:
        # Convert probabilities to binary predictions
        y_pred_binary = (y_pred >= threshold).astype(int)

        cm = confusion_matrix(y_true, y_pred_binary)

        tn, fp, fn, tp = cm.ravel()

        # Compute derived metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else None
        recall = tp / (tp + fn) if (tp + fn) > 0 else None
        f1 = 2 * (precision * recall) / (precision + recall) if (precision is not None and recall is not None and (precision + recall) > 0) else None
        specificity = tn / (tn + fp) if (tn + fp) > 0 else None

        return {
            "confusion_matrix": {
                "true_negatives": int(tn),
                "false_positives": int(fp),
                "false_negatives": int(fn),
                "true_positives": int(tp),
            },
            "threshold": threshold,
            "precision": float(precision) if precision is not None else None,
            "recall": float(recall) if recall is not None else None,
            "f1_score": float(f1) if f1 is not None else None,
            "specificity": float(specificity) if specificity is not None else None,
            "available": True,
        }
    except Exception as e:
        return {
            "confusion_matrix": None,
            "threshold": threshold,
            "precision": None,
            "recall": None,
            "f1_score": None,
            "specificity": None,
            "available": False,
            "reason": str(e),
        }


def compute_all_metrics(
    y_true: np.ndarray,
    y_score: np.ndarray,
    threshold: float = 0.5,
) -> dict[str, MetricResult | dict[str, Any]]:
    """Compute all standard credit risk metrics.

    Args:
        y_true: True binary labels (0 or 1).
        y_score: Predicted probabilities.
        threshold: Classification threshold for confusion matrix.

    Returns:
        Dictionary with all metric results.
    """
    return {
        "roc_auc": compute_roc_auc(y_true, y_score),
        "pr_auc": compute_pr_auc(y_true, y_score),
        "brier_score": compute_brier_score(y_true, y_score),
        "log_loss": compute_log_loss(y_true, y_score),
        "ks_statistic": compute_ks_statistic(y_true, y_score),
        "gini_coefficient": compute_gini_coefficient(y_true, y_score),
        "confusion_matrix": compute_confusion_matrix(y_true, y_score, threshold),
    }


def compute_prevalence(y_true: np.ndarray) -> float:
    """Compute the prevalence of the positive class.

    Args:
        y_true: True binary labels (0 or 1).

    Returns:
        Prevalence (ratio of positive class).
    """
    return float(np.mean(y_true))
