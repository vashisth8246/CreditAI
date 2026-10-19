"""Generate reproducible evaluation artifacts for the Model Performance Lab.

This script evaluates the verified UCI Taiwan XGBoost model (and comparison models)
on the untouched 15% stratified test split (4,500 samples) and computes:
- ROC curve coordinates
- Precision-Recall curve coordinates
- Confusion matrices across decision thresholds
- Calibration / reliability curves (raw vs. calibrated vs. ideal)
- Risk deciles (actual vs. predicted)
- Metric comparison across models on the exact same split
- Provenance and metadata
"""

import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_curve,
    precision_recall_curve,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    brier_score_loss,
    log_loss,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)
from sklearn.calibration import calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import joblib

from src.data_loader import load_uci_credit_card_data
from src.preprocessing import preprocess_data
from src.feature_engineering import engineer_credit_features
from src.calibration.calibrate import PlattCalibrator


def compute_ks_and_gini(y_true: np.ndarray, y_prob: np.ndarray):
    """Compute Kolmogorov-Smirnov statistic and Gini coefficient."""
    df = pd.DataFrame({"y": y_true, "p": y_prob}).sort_values(by="p", ascending=False)
    total_pos = df["y"].sum()
    total_neg = len(df) - total_pos
    if total_pos == 0 or total_neg == 0:
        return 0.0, 0.0

    df["cum_pos"] = df["y"].cumsum() / total_pos
    df["cum_neg"] = (1 - df["y"]).cumsum() / total_neg
    ks_stat = float((df["cum_pos"] - df["cum_neg"]).abs().max())
    auc = roc_auc_score(y_true, y_prob)
    gini = float(2 * auc - 1)
    return ks_stat, gini


def downsample_curve(x_vals: np.ndarray, y_vals: np.ndarray, n_points: int = 100):
    """Downsample monotonic curve coordinates for efficient web rendering."""
    if len(x_vals) <= n_points:
        return [{"x": round(float(x), 4), "y": round(float(y), 4)} for x, y in zip(x_vals, y_vals)]
    indices = np.linspace(0, len(x_vals) - 1, n_points, dtype=int)
    # Ensure start and end points are included
    indices[0] = 0
    indices[-1] = len(x_vals) - 1
    points = []
    seen = set()
    for idx in indices:
        if idx not in seen:
            seen.add(idx)
            points.append({"x": round(float(x_vals[idx]), 4), "y": round(float(y_vals[idx]), 4)})
    return points


def main():
    print("=" * 70)
    print("GENERATING REPRODUCIBLE EVALUATION ARTIFACTS")
    print("=" * 70)

    # 1. Load data
    print("\n[1/6] Loading UCI Default of Credit Card Clients dataset...")
    df = load_uci_credit_card_data()
    X, y = preprocess_data(df)
    X_features = engineer_credit_features(X)

    # 2. Replicate exact stratified split
    print("\n[2/6] Splitting 70% Train | 15% Validation | 15% Test (stratified, random_state=42)...")
    X_train, X_temp, y_train, y_temp = train_test_split(
        X_features, y, train_size=0.70, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
    )

    y_test_arr = y_test.values
    test_prevalence = float(y_test_arr.mean())
    print(f"  Test samples: {len(X_test):,} | Defaults: {y_test_arr.sum():,} ({test_prevalence*100:.2f}%)")

    # 3. Load primary XGBoost model and calibrator
    print("\n[3/6] Loading trained model artifacts...")
    model_bundle = joblib.load("models/creditai_model.joblib")
    base_xgb = model_bundle["base_model"]
    feature_names = model_bundle["feature_names"]

    # Align columns
    X_test_aligned = X_test[feature_names].values
    X_val_aligned = X_val[feature_names].values

    # Predictions
    raw_probs_test = base_xgb.predict_proba(X_test_aligned)[:, 1]
    raw_probs_val = base_xgb.predict_proba(X_val_aligned)[:, 1]

    # Load / Fit Platt Calibrator on validation set
    calibrator_path = Path("models/calibration_model.joblib")
    if calibrator_path.exists():
        calibrator = joblib.load(calibrator_path)
    else:
        calibrator = PlattCalibrator().fit(raw_probs_val, y_val.values)
        joblib.dump(calibrator, calibrator_path)

    cal_probs_test = calibrator.predict_proba(raw_probs_test)

    # Re-verify Phase 1 metric match
    test_roc_auc = roc_auc_score(y_test_arr, raw_probs_test)
    test_pr_auc = average_precision_score(y_test_arr, raw_probs_test)
    cal_roc_auc = roc_auc_score(y_test_arr, cal_probs_test)
    cal_pr_auc = average_precision_score(y_test_arr, cal_probs_test)

    print(f"  [XGBoost Raw]        Test ROC-AUC: {test_roc_auc:.4f} | Test PR-AUC: {test_pr_auc:.4f}")
    print(f"  [XGBoost Calibrated] Test ROC-AUC: {cal_roc_auc:.4f} | Test PR-AUC: {cal_pr_auc:.4f}")
    assert round(test_roc_auc, 4) == 0.7807, f"ROC-AUC mismatch: {test_roc_auc}"
    assert round(test_pr_auc, 4) == 0.5588, f"PR-AUC mismatch: {test_pr_auc}"
    print("  -> Confirmed exact match with Phase 1 reported benchmark metrics!")

    # 4. Generate curves and evaluation metrics
    print("\n[4/6] Computing curve coordinates and threshold sweeps...")

    # ROC curve
    fpr, tpr, _ = roc_curve(y_test_arr, raw_probs_test)
    roc_points = downsample_curve(fpr, tpr, 80)

    # PR curve
    prec, rec, _ = precision_recall_curve(y_test_arr, raw_probs_test)
    # precision_recall_curve returns recall decreasing; sort by recall ascending
    sort_idx = np.argsort(rec)
    pr_points = downsample_curve(rec[sort_idx], prec[sort_idx], 80)

    # Calibration / Reliability curve
    prob_true_raw, prob_pred_raw = calibration_curve(y_test_arr, raw_probs_test, n_bins=10, strategy="uniform")
    prob_true_cal, prob_pred_cal = calibration_curve(y_test_arr, cal_probs_test, n_bins=10, strategy="uniform")

    calibration_bins = []
    for i in range(len(prob_pred_raw)):
        calibration_bins.append({
            "bin": i + 1,
            "pred_raw": round(float(prob_pred_raw[i]), 4),
            "true_raw": round(float(prob_true_raw[i]), 4),
            "pred_cal": round(float(prob_pred_cal[i]), 4) if i < len(prob_pred_cal) else None,
            "true_cal": round(float(prob_true_cal[i]), 4) if i < len(prob_true_cal) else None,
        })

    # Threshold sweep and confusion matrices
    threshold_sweep = []
    thresholds = [round(t, 2) for t in np.arange(0.1, 0.95, 0.05)]
    for t in thresholds:
        preds = (cal_probs_test >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_test_arr, preds).ravel()
        p = precision_score(y_test_arr, preds, zero_division=0)
        r = recall_score(y_test_arr, preds, zero_division=0)
        f1 = f1_score(y_test_arr, preds, zero_division=0)
        acc = accuracy_score(y_test_arr, preds)
        threshold_sweep.append({
            "threshold": t,
            "accuracy": round(float(acc), 4),
            "precision": round(float(p), 4),
            "recall": round(float(r), 4),
            "f1_score": round(float(f1), 4),
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        })

    # Default threshold 0.5 confusion matrix
    cm_preds_cal = (cal_probs_test >= 0.5).astype(int)
    tn_cal, fp_cal, fn_cal, tp_cal = confusion_matrix(y_test_arr, cm_preds_cal).ravel()

    # Risk Deciles
    test_df = pd.DataFrame({"y_true": y_test_arr, "prob_raw": raw_probs_test, "prob_cal": cal_probs_test})
    test_df["decile"] = pd.qcut(test_df["prob_cal"], q=10, labels=False, duplicates="drop")
    # Invert so Decile 1 is highest risk
    test_df["decile"] = 10 - test_df["decile"]
    decile_summary = []
    for d, group in test_df.groupby("decile"):
        decile_summary.append({
            "decile": int(d),
            "borrowers": int(len(group)),
            "defaults": int(group["y_true"].sum()),
            "empirical_default_rate": round(float(group["y_true"].mean()), 4),
            "mean_calibrated_pd": round(float(group["prob_cal"].mean()), 4),
            "mean_raw_score": round(float(group["prob_raw"].mean()), 4),
        })
    decile_summary.sort(key=lambda x: x["decile"])

    # Scalar Metrics
    brier_raw = brier_score_loss(y_test_arr, raw_probs_test)
    brier_cal = brier_score_loss(y_test_arr, cal_probs_test)
    logloss_raw = log_loss(y_test_arr, raw_probs_test)
    logloss_cal = log_loss(y_test_arr, cal_probs_test)
    ks_raw, gini_raw = compute_ks_and_gini(y_test_arr, raw_probs_test)
    ks_cal, gini_cal = compute_ks_and_gini(y_test_arr, cal_probs_test)

    # 5. Fit comparison models on identical split for genuine model comparison
    print("\n[5/6] Benchmarking comparison models on identical training and test split...")
    lr_pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, random_state=42, solver="lbfgs")),
    ])
    lr_pipe.fit(X_train[feature_names], y_train)
    lr_probs = lr_pipe.predict_proba(X_test_aligned)[:, 1]

    rf_model = RandomForestClassifier(n_estimators=150, max_depth=10, random_state=42, n_jobs=-1)
    rf_model.fit(X_train[feature_names], y_train)
    rf_probs = rf_model.predict_proba(X_test_aligned)[:, 1]

    # Prevalence baseline
    prev_probs = np.full_like(y_test_arr, fill_value=test_prevalence, dtype=float)

    def model_eval_dict(name: str, probs: np.ndarray, is_calibrated: bool):
        preds = (probs >= 0.5).astype(int)
        auc = roc_auc_score(y_test_arr, probs) if len(np.unique(probs)) > 1 else 0.5
        pr_auc = average_precision_score(y_test_arr, probs) if len(np.unique(probs)) > 1 else test_prevalence
        brier = brier_score_loss(y_test_arr, probs)
        ll = log_loss(y_test_arr, probs)
        ks, gini = compute_ks_and_gini(y_test_arr, probs)
        return {
            "model_name": name,
            "roc_auc": round(float(auc), 4),
            "pr_auc": round(float(pr_auc), 4),
            "brier_score": round(float(brier), 4),
            "log_loss": round(float(ll), 4),
            "ks_statistic": round(float(ks), 4),
            "gini_coefficient": round(float(gini), 4),
            "accuracy": round(float(accuracy_score(y_test_arr, preds)), 4),
            "precision": round(float(precision_score(y_test_arr, preds, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test_arr, preds, zero_division=0)), 4),
            "f1_score": round(float(f1_score(y_test_arr, preds, zero_division=0)), 4),
            "is_calibrated": is_calibrated,
        }

    model_comparison = [
        model_eval_dict("XGBoost (Calibrated)", cal_probs_test, True),
        model_eval_dict("XGBoost (Raw)", raw_probs_test, False),
        model_eval_dict("Random Forest", rf_probs, False),
        model_eval_dict("Logistic Regression", lr_probs, False),
        model_eval_dict("Prevalence Baseline", prev_probs, False),
    ]

    # Global feature importances
    importances = getattr(base_xgb, "feature_importances_", None)
    feature_importance_list = []
    if importances is not None:
        raw_list = sorted(
            [{"feature": name, "importance": round(float(imp), 4)} for name, imp in zip(feature_names, importances)],
            key=lambda x: x["importance"],
            reverse=True,
        )
        feature_importance_list = raw_list[:15]

    # 6. Assemble complete evaluation artifact
    print("\n[6/6] Writing evaluation artifacts...")
    evaluation_artifact = {
        "metadata": {
            "dataset_id": "DS003",
            "dataset_name": "Default of Credit Card Clients",
            "geography": "Taiwan",
            "time_coverage": "April - September 2005",
            "target": "default payment next month",
            "target_meaning": "1 = Default, 0 = Repaid",
            "split_design": "Stratified 70% Train (21,000) / 15% Validation (4,500) / 15% Test (4,500)",
            "random_seed": 42,
            "test_sample_count": len(X_test),
            "test_defaults": int(y_test_arr.sum()),
            "test_prevalence": round(test_prevalence, 4),
            "evaluation_date": "2026-10-17",
            "primary_model": "XGBoost",
            "calibration_status": "Calibrated",
            "calibration_method": "Platt scaling (sigmoid)",
            "calibrator_params": {
                "slope": round(float(calibrator.slope), 4),
                "intercept": round(float(calibrator.intercept), 4),
            },
        },
        "summary_metrics": {
            "test_roc_auc": round(float(test_roc_auc), 4),
            "test_pr_auc": round(float(test_pr_auc), 4),
            "brier_score_raw": round(float(brier_raw), 4),
            "brier_score_calibrated": round(float(brier_cal), 4),
            "brier_improvement_pct": round(float((brier_raw - brier_cal) / brier_raw * 100), 2),
            "log_loss_raw": round(float(logloss_raw), 4),
            "log_loss_calibrated": round(float(logloss_cal), 4),
            "ks_statistic": round(float(ks_cal), 4),
            "gini_coefficient": round(float(gini_cal), 4),
            "accuracy_at_0_5": round(float(accuracy_score(y_test_arr, cm_preds_cal)), 4),
            "precision_at_0_5": round(float(precision_score(y_test_arr, cm_preds_cal, zero_division=0)), 4),
            "recall_at_0_5": round(float(recall_score(y_test_arr, cm_preds_cal, zero_division=0)), 4),
            "f1_at_0_5": round(float(f1_score(y_test_arr, cm_preds_cal, zero_division=0)), 4),
        },
        "confusion_matrix_default": {
            "threshold": 0.5,
            "true_negative": int(tn_cal),
            "false_positive": int(fp_cal),
            "false_negative": int(fn_cal),
            "true_positive": int(tp_cal),
            "total": len(X_test),
        },
        "curves": {
            "roc": {
                "title": "ROC Curve (Receiver Operating Characteristic)",
                "auc": round(float(test_roc_auc), 4),
                "baseline_auc": 0.5,
                "points": roc_points,
            },
            "pr": {
                "title": "Precision-Recall Curve",
                "auc": round(float(test_pr_auc), 4),
                "baseline_prevalence": round(test_prevalence, 4),
                "points": pr_points,
            },
            "calibration": {
                "title": "Probability Calibration (Reliability Curve)",
                "bins": calibration_bins,
            },
            "threshold_sweep": threshold_sweep,
        },
        "risk_deciles": decile_summary,
        "model_comparison": model_comparison,
        "global_feature_importance": feature_importance_list,
        "limitations": [
            "UCI Taiwan credit card dataset from 2005",
            "Not validated for Indian borrowers or UPI/banking underwriting",
            "Cross-sectional benchmark; does not evaluate longitudinal macro cycles",
            "Historical research artifact; score API (/v1/score) remains unvalidated",
        ],
    }

    # Save to models/
    out_path1 = Path("models/uci_taiwan_eval.json")
    with open(out_path1, "w", encoding="utf-8") as f:
        json.dump(evaluation_artifact, f, indent=2)
    print(f"  Saved -> {out_path1}")

    # Copy to frontend/public/data/ for zero-latency direct access
    public_data_dir = Path("frontend/public/data")
    public_data_dir.mkdir(parents=True, exist_ok=True)
    out_path2 = public_data_dir / "uci_taiwan_eval.json"
    with open(out_path2, "w", encoding="utf-8") as f:
        json.dump(evaluation_artifact, f, indent=2)
    print(f"  Saved -> {out_path2}")

    print("\nREPRODUCIBLE EVALUATION ARTIFACTS GENERATED SUCCESSFULLY.")
    print("=" * 70)


if __name__ == "__main__":
    main()
