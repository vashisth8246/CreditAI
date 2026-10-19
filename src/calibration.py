"""
CreditAI: Probability Calibration Module
Evaluates and refines predicted Probability of Default (PD) so that
estimated default rates match empirical empirical delinquency rates.
Supports Platt Scaling (sigmoid) and Isotonic Calibration.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.calibration import calibration_curve, CalibratedClassifierCV
from sklearn.metrics import brier_score_loss

from src.config import FIGURES_DIR


def fit_probability_calibrator(
    base_model,
    X_val: pd.DataFrame | np.ndarray,
    y_val: pd.Series | np.ndarray,
    method: str = "sigmoid",
    verbose: bool = True,
):
    """
    Fits a probability calibrator on the validation dataset (untouched test set is never used).
    
    Parameters:
    -----------
    base_model : trained classifier
        The pre-trained base model (e.g. XGBoost, Random Forest, or Logistic Regression).
    X_val : pd.DataFrame or np.ndarray
        Validation feature matrix.
    y_val : pd.Series or np.ndarray
        Validation ground-truth binary default labels.
    method : str, default='sigmoid'
        Calibration algorithm: 'sigmoid' (Platt scaling) or 'isotonic'.
    verbose : bool, default=True
        Whether to report Brier score improvement.
        
    Returns:
    --------
    calibrated_model : CalibratedClassifierCV
        The calibrated model instance.
    brier_before : float
    brier_after : float
    """
    if verbose:
        print(f"[Calibration] Fitting probability calibrator using method='{method}'...")

    # Calculate uncalibrated Brier score on validation data
    if hasattr(base_model, "predict_proba"):
        raw_probs = base_model.predict_proba(X_val)[:, 1]
    else:
        raw_probs = base_model.decision_function(X_val)
        raw_probs = 1.0 / (1.0 + np.exp(-raw_probs))

    brier_before = float(brier_score_loss(y_val, raw_probs))

    # Initialize CalibratedClassifierCV with cross-version compatibility
    try:
        from sklearn.calibration import FrozenEstimator

        calibrated_model = CalibratedClassifierCV(
            estimator=FrozenEstimator(base_model),
            method=method,
        )
    except ImportError:
        # Fallback for scikit-learn < 1.4
        calibrated_model = CalibratedClassifierCV(
            estimator=base_model,
            cv="prefit",
            method=method,
        )

    # Fit calibration mapping strictly on validation set
    calibrated_model.fit(X_val, y_val)

    # Calculate post-calibration Brier score
    cal_probs = calibrated_model.predict_proba(X_val)[:, 1]
    brier_after = float(brier_score_loss(y_val, cal_probs))

    if verbose:
        print(f"  Validation Brier Score Before Calibration : {brier_before:.5f}")
        print(f"  Validation Brier Score After Calibration  : {brier_after:.5f}")
        improvement = (brier_before - brier_after) / brier_before * 100.0
        print(f"  Brier Score Improvement                   : {improvement:+.2f}%")

    return calibrated_model, brier_before, brier_after


def generate_calibration_plot(
    y_true: np.ndarray | pd.Series,
    prob_dict: dict[str, np.ndarray],
    save_path: str | Path | None = None,
    n_bins: int = 10,
):
    """
    Plots calibration curves (reliability curves) for uncalibrated vs calibrated probabilities.
    
    Parameters:
    -----------
    y_true : array-like
        Ground truth binary default labels.
    prob_dict : dict
        Mapping of model labels to predicted probabilities.
        e.g., {'Raw XGBoost': probs_raw, 'Calibrated XGBoost': probs_cal}
    save_path : str or Path, optional
        Destination image path. If None, saves to reports/figures/calibration_curve.png.
    n_bins : int, default=10
        Number of quantile/uniform bins for the calibration curve.
    """
    if save_path is None:
        save_path = FIGURES_DIR / "calibration_curve.png"
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 6))

    # Plot diagonal reference line for perfect calibration
    plt.plot([0, 1], [0, 1], "k--", label="Perfect Calibration (Ideal)", alpha=0.7)

    for label, probs in prob_dict.items():
        prob_true, prob_pred = calibration_curve(y_true, probs, n_bins=n_bins, strategy="uniform")
        plt.plot(prob_pred, prob_true, marker="o", linewidth=2, label=label)

    plt.xlabel("Mean Predicted Probability of Default (PD)", fontsize=11)
    plt.ylabel("Fraction of True Defaults (Empirical Bad Rate)", fontsize=11)
    plt.title("Credit Risk Probability Calibration Curves", fontsize=13, fontweight="bold")
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(loc="upper left", fontsize=10)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"[Calibration Plot] Saved calibration curve to: {save_path}")


if __name__ == "__main__":
    # Test script standalone
    from sklearn.linear_model import LogisticRegression

    np.random.seed(42)
    X_mock = np.random.randn(500, 5)
    y_mock = np.random.binomial(1, 0.22, 500)

    clf = LogisticRegression()
    clf.fit(X_mock[:350], y_mock[:350])

    cal_clf, b_bef, b_aft = fit_probability_calibrator(
        clf, X_mock[350:], y_mock[350:], method="sigmoid", verbose=True
    )
    raw_p = clf.predict_proba(X_mock[350:])[:, 1]
    cal_p = cal_clf.predict_proba(X_mock[350:])[:, 1]

    generate_calibration_plot(
        y_mock[350:],
        {"Raw Logistic Regression": raw_p, "Calibrated Logistic Regression": cal_p},
    )
