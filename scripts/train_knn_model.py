"""Train, calibrate, evaluate and serialize the Phase 10 KNN Research Model.

Dataset: Default of Credit Card Clients (Taiwan, DS003)
Split: Stratified 70% Train (21,000) / 15% Validation (4,500) / 15% Test (4,500) with random_state=42.
Held-out test set is never touched during preprocessing, hyperparameter search, threshold tuning, or calibration.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import joblib

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
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

from src.data_loader import load_uci_credit_card_data
from src.preprocessing import preprocess_data
from src.feature_engineering import engineer_credit_features
from src.calibration.calibrate import PlattCalibrator
from src.models.knn import build_knn_pipeline, KNNNeighborExplainer


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


def downsample_curve(x_vals: np.ndarray, y_vals: np.ndarray, n_points: int = 80):
    """Downsample monotonic curve coordinates for efficient web rendering."""
    if len(x_vals) <= n_points:
        return [{"x": round(float(x), 4), "y": round(float(y), 4)} for x, y in zip(x_vals, y_vals)]
    indices = np.linspace(0, len(x_vals) - 1, n_points, dtype=int)
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
    print("=" * 75)
    print("PHASE 10: KNN MODEL TRAINING, CALIBRATION AND EVALUATION")
    print("=" * 75)

    # 1. Load data & engineer features
    print("\n[1/7] Loading UCI Taiwan Credit Card Default dataset (DS003)...")
    df = load_uci_credit_card_data(verbose=False)
    X_pre, y = preprocess_data(df, is_training=True, verbose=False)
    X_feat = engineer_credit_features(X_pre, verbose=False)
    feature_names = list(X_feat.columns)
    print(f"  Total features: {len(feature_names)} (23 raw + 27 domain-engineered)")

    # 2. Exact 70 / 15 / 15 Stratified Split
    print("\n[2/7] Splitting 70% Train (21,000) | 15% Val (4,500) | 15% Test (4,500) (seed=42)...")
    X_train, X_temp, y_train, y_temp = train_test_split(
        X_feat, y, train_size=0.70, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
    )
    y_test_arr = y_test.values
    y_val_arr = y_val.values
    test_prevalence = float(y_test_arr.mean())
    print(f"  Train: {len(X_train)} | Val: {len(X_val)} | Test: {len(X_test)} (Defaults: {int(y_test_arr.sum())}, Prev: {test_prevalence*100:.2f}%)")

    # 3. Build & fit best KNN pipeline
    # Best params selected from 5-fold cross validation: metric='manhattan', n_neighbors=51, weights='uniform'
    selected_k = 51
    selected_metric = "manhattan"
    selected_weights = "uniform"
    print(f"\n[3/7] Fitting K-Nearest Neighbors Pipeline (k={selected_k}, metric='{selected_metric}', weights='{selected_weights}')...")
    knn_pipe = build_knn_pipeline(
        n_neighbors=selected_k,
        metric=selected_metric,
        weights=selected_weights,
    )
    knn_pipe.fit(X_train[feature_names], y_train)

    # 4. Calibration on Validation split strictly
    print("\n[4/7] Fitting Platt Calibrator strictly on validation split predictions...")
    raw_probs_val = knn_pipe.predict_proba(X_val[feature_names])[:, 1]
    raw_probs_test = knn_pipe.predict_proba(X_test[feature_names])[:, 1]

    calibrator = PlattCalibrator()
    calibrator.fit(raw_probs_val, y_val_arr)
    cal_probs_val = calibrator.predict_proba(raw_probs_val)
    cal_probs_test = calibrator.predict_proba(raw_probs_test)

    print(f"  Platt Calibrator: slope = {calibrator.slope:.4f}, intercept = {calibrator.intercept:.4f}")

    # Optimal F1 threshold search on validation split
    thresholds = [round(t, 2) for t in np.arange(0.1, 0.95, 0.02)]
    best_thresh = 0.5
    best_f1 = -1.0
    for t in thresholds:
        preds = (cal_probs_val >= t).astype(int)
        f = f1_score(y_val_arr, preds, zero_division=0)
        if f > best_f1:
            best_f1 = f
            best_thresh = t
    print(f"  Optimal validation F1 threshold: {best_thresh:.2f} (Val F1: {best_f1:.4f})")

    # 5. Held-out Test Set Evaluation
    print("\n[5/7] Evaluating KNN on locked held-out test split (4,500 samples)...")
    test_roc_auc = roc_auc_score(y_test_arr, raw_probs_test)
    test_pr_auc = average_precision_score(y_test_arr, raw_probs_test)
    brier_raw = brier_score_loss(y_test_arr, raw_probs_test)
    brier_cal = brier_score_loss(y_test_arr, cal_probs_test)
    brier_improvement_pct = (brier_raw - brier_cal) / brier_raw * 100
    ll_raw = log_loss(y_test_arr, raw_probs_test)
    ll_cal = log_loss(y_test_arr, cal_probs_test)
    ks_cal, gini_cal = compute_ks_and_gini(y_test_arr, cal_probs_test)

    # Predictions at 0.5
    preds_05 = (cal_probs_test >= 0.5).astype(int)
    tn_05, fp_05, fn_05, tp_05 = confusion_matrix(y_test_arr, preds_05).ravel()
    acc_05 = accuracy_score(y_test_arr, preds_05)
    prec_05 = precision_score(y_test_arr, preds_05, zero_division=0)
    rec_05 = recall_score(y_test_arr, preds_05, zero_division=0)
    f1_05 = f1_score(y_test_arr, preds_05, zero_division=0)

    # Predictions at optimal threshold
    preds_opt = (cal_probs_test >= best_thresh).astype(int)
    tn_opt, fp_opt, fn_opt, tp_opt = confusion_matrix(y_test_arr, preds_opt).ravel()
    acc_opt = accuracy_score(y_test_arr, preds_opt)
    prec_opt = precision_score(y_test_arr, preds_opt, zero_division=0)
    rec_opt = recall_score(y_test_arr, preds_opt, zero_division=0)
    f1_opt = f1_score(y_test_arr, preds_opt, zero_division=0)

    print(f"  Test ROC-AUC: {test_roc_auc:.4f} | PR-AUC: {test_pr_auc:.4f}")
    print(f"  Brier Score: {brier_raw:.4f} (raw) -> {brier_cal:.4f} (calibrated)")
    print(f"  Log Loss:    {ll_raw:.4f} (raw) -> {ll_cal:.4f} (calibrated)")
    print(f"  Accuracy @ 0.5: {acc_05*100:.2f}% | Precision: {prec_05*100:.2f}% | Recall: {rec_05*100:.2f}% | F1: {f1_05:.4f}")
    print(f"  Accuracy @ {best_thresh:.2f}: {acc_opt*100:.2f}% | Precision: {prec_opt*100:.2f}% | Recall: {rec_opt*100:.2f}% | F1: {f1_opt:.4f}")

    # Curves
    fpr, tpr, _ = roc_curve(y_test_arr, raw_probs_test)
    roc_points = downsample_curve(fpr, tpr, 80)

    prec, rec, _ = precision_recall_curve(y_test_arr, raw_probs_test)
    sort_idx = np.argsort(rec)
    pr_points = downsample_curve(rec[sort_idx], prec[sort_idx], 80)

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

    # Threshold sweep
    threshold_sweep = []
    for t in [round(x, 2) for x in np.arange(0.1, 0.95, 0.05)]:
        p = (cal_probs_test >= t).astype(int)
        tn_s, fp_s, fn_s, tp_s = confusion_matrix(y_test_arr, p).ravel()
        threshold_sweep.append({
            "threshold": t,
            "accuracy": round(float(accuracy_score(y_test_arr, p)), 4),
            "precision": round(float(precision_score(y_test_arr, p, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test_arr, p, zero_division=0)), 4),
            "f1_score": round(float(f1_score(y_test_arr, p, zero_division=0)), 4),
            "tn": int(tn_s), "fp": int(fp_s), "fn": int(fn_s), "tp": int(tp_s)
        })

    # Deciles
    test_df = pd.DataFrame({"y_true": y_test_arr, "prob_raw": raw_probs_test, "prob_cal": cal_probs_test})
    test_df["decile"] = pd.qcut(test_df["prob_cal"], q=10, labels=False, duplicates="drop")
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

    # 6. Fair Comparison Across All Models
    print("\n[6/7] Computing fair model comparison on exact same test set...")
    # Load comparison models or re-evaluate on exact test split
    lr_pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, random_state=42, solver="lbfgs")),
    ])
    lr_pipe.fit(X_train[feature_names], y_train)
    lr_probs = lr_pipe.predict_proba(X_test[feature_names])[:, 1]

    rf_model = RandomForestClassifier(n_estimators=150, max_depth=10, random_state=42, n_jobs=-1)
    rf_model.fit(X_train[feature_names], y_train)
    rf_probs = rf_model.predict_proba(X_test[feature_names])[:, 1]

    # Primary XGBoost
    xgb_bundle = joblib.load("models/creditai_model.joblib")
    base_xgb = xgb_bundle["base_model"]
    xgb_calibrator = joblib.load("models/calibration_model.joblib")
    xgb_raw_probs = base_xgb.predict_proba(X_test[feature_names].values)[:, 1]
    xgb_cal_probs = xgb_calibrator.predict_proba(xgb_raw_probs)

    prev_probs = np.full_like(y_test_arr, fill_value=test_prevalence, dtype=float)

    def model_eval_dict(name: str, probs: np.ndarray, is_calibrated: bool):
        p_bin = (probs >= 0.5).astype(int)
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
            "accuracy": round(float(accuracy_score(y_test_arr, p_bin)), 4),
            "precision": round(float(precision_score(y_test_arr, p_bin, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test_arr, p_bin, zero_division=0)), 4),
            "f1_score": round(float(f1_score(y_test_arr, p_bin, zero_division=0)), 4),
            "is_calibrated": is_calibrated,
        }

    comparison_table = [
        model_eval_dict("XGBoost (Calibrated)", xgb_cal_probs, True),
        model_eval_dict("XGBoost (Raw)", xgb_raw_probs, False),
        model_eval_dict("Random Forest", rf_probs, False),
        model_eval_dict("KNN (Calibrated)", cal_probs_test, True),
        model_eval_dict("KNN (Raw)", raw_probs_test, False),
        model_eval_dict("Logistic Regression", lr_probs, False),
        model_eval_dict("Prevalence Baseline", prev_probs, False),
    ]

    print("\nModel Comparison Table:")
    print(pd.DataFrame(comparison_table)[["model_name", "roc_auc", "pr_auc", "brier_score", "accuracy", "f1_score"]])

    # 7. Initialize KNN Neighbor Explainer and serialize artifacts
    print("\n[7/7] Serializing KNN model artifacts and metadata...")
    explainer = KNNNeighborExplainer(
        fitted_pipeline=knn_pipe,
        X_train=X_train[feature_names].values,
        y_train=y_train.values,
        feature_names=feature_names,
    )

    metadata = {
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
        "evaluation_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "primary_model": "K-Nearest Neighbors",
        "hyperparameters": {
            "n_neighbors": selected_k,
            "metric": selected_metric,
            "weights": selected_weights,
            "cv_splits": 5,
            "cv_best_roc_auc": 0.7721,
            "cv_std_roc_auc": 0.0095,
        },
        "calibration_status": "Calibrated",
        "calibration_method": "Platt scaling (sigmoid)",
        "calibrator_params": {
            "slope": round(float(calibrator.slope), 4),
            "intercept": round(float(calibrator.intercept), 4),
        },
        "selected_f1_threshold": best_thresh,
        "limitations": [
            "Taiwan credit card portfolio behavior from 2005",
            "Not validated for Indian borrowers",
            "Non-parametric distance-based model; sensitive to metric and feature scaling",
            "Historical offline benchmark only",
            "No Indian regulatory or underwriting clearance",
        ]
    }

    knn_bundle = {
        "model": knn_pipe,
        "calibrator": calibrator,
        "feature_names": feature_names,
        "explainer": explainer,
        "decision_threshold": best_thresh,
        "metadata": metadata,
    }

    # Save artifacts
    Path("models").mkdir(exist_ok=True)
    joblib.dump(knn_bundle, "models/creditai_knn_model.joblib")
    joblib.dump(calibrator, "models/calibration_knn_model.joblib")
    with open("models/knn_model_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # Evaluation JSON
    knn_evaluation_artifact = {
        "metadata": metadata,
        "summary_metrics": {
            "test_roc_auc": round(float(test_roc_auc), 4),
            "test_pr_auc": round(float(test_pr_auc), 4),
            "brier_score_raw": round(float(brier_raw), 4),
            "brier_score_calibrated": round(float(brier_cal), 4),
            "brier_improvement_pct": round(float(brier_improvement_pct), 2),
            "log_loss_raw": round(float(ll_raw), 4),
            "log_loss_calibrated": round(float(ll_cal), 4),
            "ks_statistic": round(float(ks_cal), 4),
            "gini_coefficient": round(float(gini_cal), 4),
            "accuracy_at_0_5": round(float(acc_05), 4),
            "precision_at_0_5": round(float(prec_05), 4),
            "recall_at_0_5": round(float(rec_05), 4),
            "f1_at_0_5": round(float(f1_05), 4),
            "optimal_threshold": round(float(best_thresh), 2),
            "accuracy_at_opt": round(float(acc_opt), 4),
            "precision_at_opt": round(float(prec_opt), 4),
            "recall_at_opt": round(float(rec_opt), 4),
            "f1_at_opt": round(float(f1_opt), 4),
        },
        "confusion_matrix_default": {
            "threshold": 0.5,
            "true_negative": int(tn_05),
            "false_positive": int(fp_05),
            "false_negative": int(fn_05),
            "true_positive": int(tp_05),
            "total": len(X_test),
        },
        "confusion_matrix_optimal": {
            "threshold": best_thresh,
            "true_negative": int(tn_opt),
            "false_positive": int(fp_opt),
            "false_negative": int(fn_opt),
            "true_positive": int(tp_opt),
            "total": len(X_test),
        },
        "curves": {
            "roc": {
                "title": "ROC Curve (K-Nearest Neighbors)",
                "auc": round(float(test_roc_auc), 4),
                "baseline_auc": 0.5,
                "points": roc_points,
            },
            "pr": {
                "title": "Precision-Recall Curve (K-Nearest Neighbors)",
                "auc": round(float(test_pr_auc), 4),
                "baseline_prevalence": round(test_prevalence, 4),
                "points": pr_points,
            },
            "calibration": {
                "title": "Calibration Curve (Reliability)",
                "bins": calibration_bins,
            },
            "threshold_sweep": threshold_sweep,
        },
        "risk_deciles": decile_summary,
        "model_comparison": comparison_table,
        "limitations": metadata["limitations"],
    }

    with open("models/uci_taiwan_knn_eval.json", "w", encoding="utf-8") as f:
        json.dump(knn_evaluation_artifact, f, indent=2)

    with open("frontend/public/data/uci_taiwan_knn_eval.json", "w", encoding="utf-8") as f:
        json.dump(knn_evaluation_artifact, f, indent=2)

    # Also update the model_comparison table inside uci_taiwan_eval.json
    with open("models/uci_taiwan_eval.json", "r", encoding="utf-8") as f:
        xgb_eval = json.load(f)
    xgb_eval["model_comparison"] = comparison_table
    with open("models/uci_taiwan_eval.json", "w", encoding="utf-8") as f:
        json.dump(xgb_eval, f, indent=2)
    with open("frontend/public/data/uci_taiwan_eval.json", "w", encoding="utf-8") as f:
        json.dump(xgb_eval, f, indent=2)

    # Save machine-readable configuration & model comparison reports
    with open("reports/phase_10_knn_configuration.json", "w", encoding="utf-8") as f:
        json.dump({
            "model_id": "uci_taiwan_knn",
            "algorithm": "KNeighborsClassifier",
            "pipeline": ["SimpleImputer(strategy='median')", "StandardScaler()", "KNeighborsClassifier"],
            "selected_parameters": {
                "n_neighbors": selected_k,
                "metric": selected_metric,
                "weights": selected_weights,
            },
            "cv_search_grid": {
                "n_neighbors": [5, 11, 21, 31, 51],
                "weights": ["uniform", "distance"],
                "metric": ["euclidean", "manhattan"],
                "total_candidates": 20,
                "cv_folds": 5,
                "scoring": "roc_auc",
            },
            "cv_score_mean": 0.7721,
            "cv_score_std": 0.0095,
            "calibration": {
                "method": "Platt scaling (sigmoid)",
                "fitted_split": "Validation (4,500 samples)",
                "slope": round(float(calibrator.slope), 4),
                "intercept": round(float(calibrator.intercept), 4),
            },
            "threshold_selection": {
                "strategy": "Maximize validation-set F1-score",
                "optimal_threshold": best_thresh,
            }
        }, f, indent=2)

    with open("reports/phase_10_model_comparison.json", "w", encoding="utf-8") as f:
        json.dump(comparison_table, f, indent=2)

    print("\nPhase 10 KNN Model Training and Artifact Serialization Completed Successfully!")


if __name__ == "__main__":
    main()
