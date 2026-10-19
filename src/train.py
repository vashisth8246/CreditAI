"""
CreditAI: Model Training, Selection, and Serialization Pipeline
Orchestrates:
1. Data loading and validation
2. Preprocessing and feature engineering
3. Stratified 70/15/15 splitting
4. Training 3 models (Logistic Regression, Random Forest, XGBoost)
5. Validation set benchmarking
6. XGBoost selected as the primary model
7. Probability calibration
8. Final evaluation on the untouched test set
9. Model artifact serialization (joblib, json metadata)
10. Visualization generation (ROC, PR, Deciles, SHAP)
"""

import json
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score, average_precision_score, roc_curve, precision_recall_curve
from xgboost import XGBClassifier
import shap

from src.config import (
    RANDOM_STATE,
    TRAIN_RATIO,
    SAVED_MODEL_PATH,
    FEATURE_NAMES_PATH,
    MODEL_METADATA_PATH,
    FIGURES_DIR,
    TARGET_COLUMN,
)
from src.data_loader import load_uci_credit_card_data
from src.preprocessing import preprocess_data
from src.feature_engineering import engineer_credit_features
from src.evaluate import (
    calculate_credit_metrics,
    compute_risk_deciles,
    format_model_comparison_table,
)
from src.calibration import fit_probability_calibrator, generate_calibration_plot


# ---------------------------------------------------------------------------
# JSON Serialization Helper
# Converts numpy types (int64, float64, bool_) to native Python types so
# json.dump() does not raise TypeError.
# ---------------------------------------------------------------------------
class NumpyJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        return super().default(obj)


# ---------------------------------------------------------------------------
# Visualization Functions
# ---------------------------------------------------------------------------

def generate_target_distribution_plot(y: pd.Series, save_path: Path):
    """Bar chart of default vs. non-default class counts."""
    counts = y.value_counts().sort_index()
    pcts = y.value_counts(normalize=True).sort_index() * 100.0

    plt.figure(figsize=(6, 5))
    bars = plt.bar(
        ["No Default (0)", "Default (1)"],
        counts,
        color=["#2b5c8f", "#d95f02"],
        width=0.5,
    )
    plt.title("Credit Default Target Distribution", fontsize=12, fontweight="bold")
    plt.ylabel("Number of Borrowers", fontsize=10)
    plt.grid(axis="y", linestyle=":", alpha=0.6)

    for bar, pct, count in zip(bars, pcts, counts):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 400,
            f"{count:,}\n({pct:.1f}%)",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    plt.ylim(0, counts.max() * 1.18)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"[Plot] Saved target distribution plot -> {save_path.name}")


def generate_roc_curves_plot(models_preds: dict, y_val: np.ndarray, save_path: Path):
    """Overlaid ROC curves for all 3 models on the validation set."""
    plt.figure(figsize=(7, 6))
    plt.plot([0, 1], [0, 1], "k--", label="Random Classifier (AUC = 0.5000)", alpha=0.6)

    for name, probs in models_preds.items():
        fpr, tpr, _ = roc_curve(y_val, probs)
        auc = roc_auc_score(y_val, probs)
        plt.plot(fpr, tpr, linewidth=2, label=f"{name} (AUC = {auc:.4f})")

    plt.xlabel("False Positive Rate", fontsize=10)
    plt.ylabel("True Positive Rate", fontsize=10)
    plt.title("Validation Set -- ROC Curves (All Models)", fontsize=12, fontweight="bold")
    plt.legend(loc="lower right", fontsize=9)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"[Plot] Saved ROC curves -> {save_path.name}")


def generate_pr_curves_plot(models_preds: dict, y_val: np.ndarray, save_path: Path):
    """Overlaid Precision-Recall curves for all 3 models."""
    plt.figure(figsize=(7, 6))
    no_skill = float(y_val.mean())
    plt.plot([0, 1], [no_skill, no_skill], "k--",
             label=f"No-Skill Baseline ({no_skill:.3f})", alpha=0.6)

    for name, probs in models_preds.items():
        prec, rec, _ = precision_recall_curve(y_val, probs)
        ap = average_precision_score(y_val, probs)
        plt.plot(rec, prec, linewidth=2, label=f"{name} (PR-AUC = {ap:.4f})")

    plt.xlabel("Recall", fontsize=10)
    plt.ylabel("Precision", fontsize=10)
    plt.title("Validation Set -- Precision-Recall Curves (All Models)", fontsize=12, fontweight="bold")
    plt.legend(loc="upper right", fontsize=9)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"[Plot] Saved PR curves -> {save_path.name}")


def generate_deciles_plot(deciles_df: pd.DataFrame, model_name: str, save_path: Path):
    """Bar chart of actual default rate per predicted risk decile."""
    plt.figure(figsize=(10, 5))
    bars = plt.bar(
        deciles_df["Decile"],
        deciles_df["Actual Default Rate (%)"],
        color="#c51b7d",
        edgecolor="black",
        alpha=0.85,
    )
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.ylabel("Actual Default Rate (%)", fontsize=10)
    plt.title(
        f"Risk Decile Monotonicity Check -- {model_name}",
        fontsize=12,
        fontweight="bold",
    )
    plt.grid(axis="y", linestyle=":", alpha=0.6)

    for bar, val in zip(bars, deciles_df["Actual Default Rate (%)"]):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            f"{val:.1f}%",
            ha="center",
            va="bottom",
            fontsize=8.5,
            fontweight="bold",
        )

    plt.ylim(0, max(deciles_df["Actual Default Rate (%)"].max() * 1.18, 10))
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"[Plot] Saved risk decile chart -> {save_path.name}")


def generate_shap_summary_plot(
    model, X_sample: pd.DataFrame, feature_names: list, save_path: Path
):
    """SHAP summary beeswarm plot for top 15 features across many samples."""
    print("[SHAP] Computing SHAP values for summary plot (1,000 samples)...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)

    # XGBoost TreeExplainer returns a 2-D array (n_samples x n_features)
    if isinstance(shap_values, list):
        # Some older versions return list[neg_class, pos_class]
        vals = shap_values[1]
    else:
        vals = shap_values

    plt.figure(figsize=(10, 8))
    shap.summary_plot(
        vals,
        X_sample,
        feature_names=feature_names,
        show=False,
        max_display=15,
    )
    plt.title("CreditAI (XGBoost) -- Top 15 SHAP Risk Drivers", fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[Plot] Saved SHAP summary plot -> {save_path.name}")


# ---------------------------------------------------------------------------
# Main Training Pipeline
# ---------------------------------------------------------------------------

def run_training_pipeline():
    """Full Phase 1 ML training, evaluation, calibration, and artifact saving."""
    print("\n" + "=" * 75)
    print(" CREDITAI -- STAGE 1 CORE ML ENGINE  (XGBoost Primary Model)")
    print("=" * 75)

    # ------------------------------------------------------------------
    # 1. Load & Diagnose Raw Data
    # ------------------------------------------------------------------
    raw_df = load_uci_credit_card_data(verbose=True)
    generate_target_distribution_plot(
        raw_df[TARGET_COLUMN], FIGURES_DIR / "target_distribution.png"
    )

    # ------------------------------------------------------------------
    # 2. Preprocess + Feature Engineering
    # ------------------------------------------------------------------
    X_pre, y = preprocess_data(raw_df, is_training=True, verbose=True)
    X_features = engineer_credit_features(X_pre, verbose=True)
    feature_names = list(X_features.columns)
    print(f"  Final feature matrix: {X_features.shape[0]:,} rows x {X_features.shape[1]} features")

    # ------------------------------------------------------------------
    # 3. Stratified 70 / 15 / 15 Split
    # ------------------------------------------------------------------
    print("\n[Split] 70% Train | 15% Validation | 15% Test (stratified)...")
    X_train, X_temp, y_train, y_temp = train_test_split(
        X_features, y,
        train_size=TRAIN_RATIO,
        random_state=RANDOM_STATE,
        stratify=y,
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp,
        test_size=0.50,
        random_state=RANDOM_STATE,
        stratify=y_temp,
    )

    for split_name, X_sp, y_sp in [
        ("Train     ", X_train, y_train),
        ("Validation", X_val,   y_val),
        ("Test      ", X_test,  y_test),
    ]:
        print(
            f"  {split_name}: {len(X_sp):,} samples | "
            f"Defaults: {y_sp.sum():,} ({y_sp.mean()*100:.2f}%)"
        )
    print("  Test set is now LOCKED -- not touched again until final evaluation.")

    # ------------------------------------------------------------------
    # 4. Train Three Models
    # ------------------------------------------------------------------
    print("\n[Training] Fitting 3 models on training data...")

    # Model 1 -- Logistic Regression (with scaling, balanced weights)
    print("  [1/3] Logistic Regression...")
    lr_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            random_state=RANDOM_STATE,
            solver="lbfgs",
        )),
    ])
    lr_pipeline.fit(X_train, y_train)

    # Model 2 -- Random Forest
    print("  [2/3] Random Forest...")
    rf_model = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_leaf=20,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    rf_model.fit(X_train, y_train)

    # Model 3 -- XGBoost  <- PRIMARY MODEL
    print("  [3/3] XGBoost (primary model)...")
    neg_count = int((y_train == 0).sum())
    pos_count = int((y_train == 1).sum())
    scale_pos = neg_count / pos_count   # ~ 3.52

    xgb_model = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos,
        random_state=RANDOM_STATE,
        eval_metric="logloss",
        n_jobs=-1,
    )
    xgb_model.fit(X_train, y_train)
    print("  All 3 models trained successfully.")

    # ------------------------------------------------------------------
    # 5. Validation Benchmarking
    # ------------------------------------------------------------------
    print("\n[Validation] Evaluating all 3 models on validation set...")

    p_lr  = lr_pipeline.predict_proba(X_val)[:, 1]
    p_rf  = rf_model.predict_proba(X_val)[:, 1]
    p_xgb = xgb_model.predict_proba(X_val)[:, 1]

    val_preds = {
        "Logistic Regression": p_lr,
        "Random Forest":       p_rf,
        "XGBoost":             p_xgb,
    }

    m_lr  = calculate_credit_metrics(y_val, p_lr,  model_name="Logistic Regression")
    m_rf  = calculate_credit_metrics(y_val, p_rf,  model_name="Random Forest")
    m_xgb = calculate_credit_metrics(y_val, p_xgb, model_name="XGBoost")
    val_metrics_list = [m_lr, m_rf, m_xgb]

    print("\n" + "=" * 75)
    print("VALIDATION SET -- MODEL COMPARISON TABLE")
    print("=" * 75)
    print(format_model_comparison_table(val_metrics_list))
    print("=" * 75)

    generate_roc_curves_plot(val_preds, y_val.values, FIGURES_DIR / "roc_curves.png")
    generate_pr_curves_plot(val_preds,  y_val.values, FIGURES_DIR / "pr_curves.png")

    # ------------------------------------------------------------------
    # 6. Model Selection  ->  XGBoost is the chosen model
    # ------------------------------------------------------------------
    best_model      = xgb_model
    best_model_name = "XGBoost"
    p_val_best      = p_xgb

    print(f"\n[Model Selected] {best_model_name.upper()}")
    print(f"  Validation ROC-AUC : {m_xgb['roc_auc']:.4f}")
    print(f"  Validation PR-AUC  : {m_xgb['pr_auc']:.4f}")
    print(f"  Validation KS Stat : {m_xgb['ks_stat']:.4f}")
    print(f"  Validation Gini    : {m_xgb['gini']:.4f}")

    val_deciles = compute_risk_deciles(y_val, p_val_best)
    print(f"\n[Validation Risk Deciles -- {best_model_name}]:")
    print(val_deciles.to_string(index=False))

    # ------------------------------------------------------------------
    # 7. Probability Calibration  (on Validation set only)
    # ------------------------------------------------------------------
    print(f"\n[Calibration] Platt scaling on validation data...")
    calibrated_model, brier_raw, brier_cal = fit_probability_calibrator(
        best_model, X_val, y_val, method="sigmoid", verbose=True
    )
    p_val_calibrated = calibrated_model.predict_proba(X_val)[:, 1]

    generate_calibration_plot(
        y_val,
        {
            f"Raw {best_model_name}":        p_val_best,
            f"Calibrated {best_model_name}": p_val_calibrated,
        },
        save_path=FIGURES_DIR / "calibration_curve.png",
    )

    # ------------------------------------------------------------------
    # 8. Final Test Set Evaluation  (executed exactly once)
    # ------------------------------------------------------------------
    print("\n" + "=" * 75)
    print(" FINAL TEST SET EVALUATION (untouched 4,500 samples)")
    print("=" * 75)

    p_test_raw = best_model.predict_proba(X_test)[:, 1]
    p_test_cal = calibrated_model.predict_proba(X_test)[:, 1]

    test_metrics_raw = calculate_credit_metrics(
        y_test, p_test_raw, model_name=f"{best_model_name} -- Raw"
    )
    test_metrics_cal = calculate_credit_metrics(
        y_test, p_test_cal, model_name=f"{best_model_name} -- Calibrated"
    )

    print(format_model_comparison_table([test_metrics_raw, test_metrics_cal]))

    test_deciles = compute_risk_deciles(y_test, p_test_cal)
    print(f"\n[Test Risk Decile Table -- {best_model_name} Calibrated]:")
    print(test_deciles.to_string(index=False))

    generate_deciles_plot(test_deciles, best_model_name, FIGURES_DIR / "risk_deciles.png")

    # ------------------------------------------------------------------
    # 9. SHAP Explainability
    # ------------------------------------------------------------------
    print("\n[SHAP] Preparing explainability layer...")

    # 9a. Summary plot across 1,000 validation samples
    shap_sample = X_val.iloc[:1000].reset_index(drop=True)
    generate_shap_summary_plot(
        best_model, shap_sample, feature_names, FIGURES_DIR / "feature_importance_shap.png"
    )

    # 9b. Single-borrower waterfall explanation (first validation sample)
    print("[SHAP] Computing single-borrower explanation...")
    sample_idx = 0
    borrower_x  = X_val.iloc[[sample_idx]].reset_index(drop=True)   # shape (1, n_features)
    borrower_pd = float(p_val_calibrated[sample_idx])

    explainer_single = shap.TreeExplainer(best_model)
    shap_output      = explainer_single.shap_values(borrower_x)      # shape (1, n_features)

    # Flatten to 1-D array of length n_features
    if isinstance(shap_output, list):
        shap_flat = np.array(shap_output[1]).flatten()
    else:
        shap_flat = np.array(shap_output).flatten()

    feat_vals = borrower_x.values.flatten()   # also 1-D, same length

    shap_df = pd.DataFrame({
        "Feature":    feature_names,
        "Value":      feat_vals,
        "SHAP_Value": shap_flat,
    })

    top_pos = shap_df.nlargest(3, "SHAP_Value")
    top_neg = shap_df.nsmallest(3, "SHAP_Value")

    print("\n--- SAMPLE BORROWER EXPLAINABILITY ---")
    print(f"  Calibrated PD : {borrower_pd:.4f}  ({borrower_pd*100:.1f}%)")
    print("  Top 3 Risk-Increasing Factors:")
    for _, r in top_pos.iterrows():
        print(f"    [+] {r['Feature']:<30} = {r['Value']:>10.2f}  (SHAP: +{r['SHAP_Value']:.4f})")
    print("  Top 3 Risk-Decreasing Factors:")
    for _, r in top_neg.iterrows():
        print(f"    [-] {r['Feature']:<30} = {r['Value']:>10.2f}  (SHAP: {r['SHAP_Value']:.4f})")
    print("-" * 50)

    # ------------------------------------------------------------------
    # 10. Save Artifacts
    # ------------------------------------------------------------------
    print("\n[Saving] Persisting model artifacts...")

    model_bundle = {
        "base_model":       best_model,
        "calibrated_model": calibrated_model,
        "model_name":       best_model_name,
        "feature_names":    feature_names,
        "target_column":    TARGET_COLUMN,
        "trained_date":     datetime.now().isoformat(),
        "random_state":     RANDOM_STATE,
    }
    joblib.dump(model_bundle, SAVED_MODEL_PATH)
    print(f"  Model bundle  -> {SAVED_MODEL_PATH}")

    with open(FEATURE_NAMES_PATH, "w", encoding="utf-8") as fh:
        json.dump(feature_names, fh, indent=2)
    print(f"  Feature names -> {FEATURE_NAMES_PATH}")

    # Convert any numpy scalars before JSON serialization
    def _sanitize(obj):
        if isinstance(obj, dict):
            return {k: _sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_sanitize(v) for v in obj]
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        return obj

    metadata = {
        "project":          "CreditAI",
        "stage":            "Stage 1 -- Core ML Engine",
        "dataset":          "UCI Default of Credit Card Clients",
        "training_timestamp": datetime.now().isoformat(),
        "random_seed":      RANDOM_STATE,
        "selected_model":   best_model_name,
        "total_borrowers":  int(len(raw_df)),
        "split_counts": {
            "train":      int(len(X_train)),
            "validation": int(len(X_val)),
            "test":       int(len(X_test)),
        },
        "feature_count":    int(len(feature_names)),
        "target_name":      TARGET_COLUMN,
        "validation_metrics":          _sanitize(val_metrics_list),
        "final_test_metrics_raw":      _sanitize(test_metrics_raw),
        "final_test_metrics_calibrated": _sanitize(test_metrics_cal),
        "test_risk_deciles": _sanitize(test_deciles.to_dict(orient="records")),
        "calibration": {
            "method":           "sigmoid (Platt scaling)",
            "val_brier_before": float(brier_raw),
            "val_brier_after":  float(brier_cal),
        },
        "version": "1.0.0",
    }

    with open(MODEL_METADATA_PATH, "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2, cls=NumpyJSONEncoder)
    print(f"  Model metadata -> {MODEL_METADATA_PATH}")

    print("\n" + "=" * 75)
    print(" CREDITAI STAGE 1 PIPELINE COMPLETE")
    print("=" * 75)
    return metadata


if __name__ == "__main__":
    run_training_pipeline()
