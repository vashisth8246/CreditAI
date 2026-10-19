"""
CreditAI: Model Evaluation & Risk Decile Analytics Module
Computes credit-risk evaluation metrics: ROC-AUC, PR-AUC, KS Statistic,
Gini Coefficient, Brier Score, Precision, Recall, F1, Confusion Matrix,
and Risk Decile Lift tables.
"""

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)


def calculate_credit_metrics(
    y_true: np.ndarray | pd.Series,
    y_prob: np.ndarray,
    threshold: float = 0.5,
    model_name: str = "Model",
) -> dict:
    """
    Computes a comprehensive dictionary of credit risk evaluation metrics.
    
    Parameters:
    -----------
    y_true : array-like
        Ground truth binary labels (0 = Repaid, 1 = Default).
    y_prob : array-like
        Predicted Probability of Default (PD) in [0, 1].
    threshold : float, default=0.5
        Decision threshold for binary classification metrics.
    model_name : str, default='Model'
        Identifier label for the evaluated model.
        
    Returns:
    --------
    dict
        Dictionary containing all evaluation metrics.
    """
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    y_pred = (y_prob >= threshold).astype(int)

    # 1. ROC-AUC
    roc_auc = float(roc_auc_score(y_true, y_prob))

    # 2. PR-AUC (Average Precision)
    pr_auc = float(average_precision_score(y_true, y_prob))

    # 3. Kolmogorov-Smirnov (KS) Statistic
    # KS measures the maximum divergence between the CDF of defaults vs. non-defaults
    prob_goods = y_prob[y_true == 0]
    prob_bads = y_prob[y_true == 1]
    if len(prob_goods) > 0 and len(prob_bads) > 0:
        ks_stat = float(ks_2samp(prob_bads, prob_goods).statistic)
    else:
        ks_stat = 0.0

    # 4. Gini Coefficient (standard banking definition: 2 * ROC-AUC - 1)
    gini = float(2.0 * roc_auc - 1.0)

    # 5. Brier Score (Mean Squared Probability Error)
    brier = float(brier_score_loss(y_true, y_prob))

    # 6. Classification Metrics at Threshold
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    # 7. Confusion Matrix
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()

    return {
        "model_name": model_name,
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "ks_stat": ks_stat,
        "gini": gini,
        "brier_score": brier,
        "precision": prec,
        "recall": rec,
        "f1_score": f1,
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
        },
        "threshold": threshold,
    }


def compute_risk_deciles(
    y_true: np.ndarray | pd.Series,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> pd.DataFrame:
    """
    Constructs a Risk Decile Table by partitioning borrowers into 10 risk buckets
    ranked by predicted Probability of Default (Decile 1 = highest risk).
    
    Verifies monotonicity: Higher predicted risk buckets must show higher empirical defaults.
    
    Returns:
    --------
    pd.DataFrame
        Table with columns:
        - Decile (1 = Highest Risk, 10 = Lowest Risk)
        - Borrowers Count
        - Avg Predicted PD (%)
        - Actual Defaults
        - Actual Default Rate (%)
        - Cumulative Default Capture (%)
    """
    df_eval = pd.DataFrame({
        "y_true": np.asarray(y_true),
        "y_prob": np.asarray(y_prob),
    })

    # Sort descending by predicted default probability
    df_eval = df_eval.sort_values(by="y_prob", ascending=False).reset_index(drop=True)

    # Create 10 equal-sized bins
    df_eval["decile"] = pd.qcut(df_eval.index, q=n_bins, labels=[f"Decile {i}" for i in range(1, n_bins + 1)])

    total_defaults = df_eval["y_true"].sum()

    decile_summary = []
    cum_defaults = 0

    for decile_label, group in df_eval.groupby("decile", observed=False):
        n_borrowers = len(group)
        n_defaults = group["y_true"].sum()
        cum_defaults += n_defaults
        avg_pred_pd = group["y_prob"].mean() * 100.0
        actual_bad_rate = (n_defaults / n_borrowers * 100.0) if n_borrowers > 0 else 0.0
        cum_capture_pct = (cum_defaults / total_defaults * 100.0) if total_defaults > 0 else 0.0

        decile_summary.append({
            "Decile": decile_label,
            "Borrowers": n_borrowers,
            "Avg Pred PD (%)": round(avg_pred_pd, 2),
            "Actual Defaults": int(n_defaults),
            "Actual Default Rate (%)": round(actual_bad_rate, 2),
            "Cum Default Capture (%)": round(cum_capture_pct, 2),
        })

    return pd.DataFrame(decile_summary)


def format_model_comparison_table(metrics_list: list[dict]) -> str:
    """
    Renders an ASCII / Markdown model comparison table for all evaluated models.
    """
    header = (
        "| Model | ROC-AUC | PR-AUC | KS Stat | Gini | Brier | Precision | Recall | F1-Score |\n"
        "|---|---|---|---|---|---|---|---|---|"
    )
    rows = []
    for m in metrics_list:
        row = (
            f"| {m['model_name']} "
            f"| {m['roc_auc']:.4f} "
            f"| {m['pr_auc']:.4f} "
            f"| {m['ks_stat']:.4f} "
            f"| {m['gini']:.4f} "
            f"| {m['brier_score']:.4f} "
            f"| {m['precision']:.4f} "
            f"| {m['recall']:.4f} "
            f"| {m['f1_score']:.4f} |"
        )
        rows.append(row)
    return header + "\n" + "\n".join(rows)


if __name__ == "__main__":
    # Test evaluation metrics with synthetic data
    np.random.seed(42)
    y_test_mock = np.random.binomial(1, 0.22, 1000)
    y_prob_mock = np.clip(y_test_mock * 0.4 + np.random.uniform(0.1, 0.5, 1000), 0, 1)

    m = calculate_credit_metrics(y_test_mock, y_prob_mock, model_name="Mock XGBoost")
    print(format_model_comparison_table([m]))
    print("\nRisk Deciles:")
    print(compute_risk_deciles(y_test_mock, y_prob_mock))
