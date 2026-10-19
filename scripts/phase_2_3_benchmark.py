"""Reproducible, leakage-safe historical benchmarking experiment on LendingClub dataset."""

import os
import sys
import math
import numpy as np
import pandas as pd

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OrdinalEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    log_loss,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
)

# File Paths
LC_CSV_PATH = os.path.join("Data", "archive", "accepted_2007_to_2018Q4.csv")
REPORTS_DIR = "reports"

# Random Seed for Reproducibility
RANDOM_SEED = 42

# Strict Prohibited Column Set (Post-Origination Leakage + PII / Identifiers)
PROHIBITED_COLUMNS = {
    # Post-origination payment & recovery leakage
    "pymnt_plan", "out_prncp", "out_prncp_inv", "total_pymnt", "total_pymnt_inv",
    "total_rec_prncp", "total_rec_int", "total_rec_late_fee", "recoveries",
    "collection_recovery_fee", "last_pymnt_d", "last_pymnt_amnt", "next_pymnt_d",
    "last_credit_pull_d", "last_fico_range_high", "last_fico_range_low",
    "collections_12_mths_ex_med", "policy_code",
    # Post-default debt settlement leakage
    "debt_settlement_flag", "debt_settlement_flag_date", "settlement_status",
    "settlement_date", "settlement_amount", "settlement_percentage", "settlement_term",
    # Post-origination hardship program leakage
    "hardship_flag", "hardship_type", "hardship_reason", "hardship_status",
    "deferral_term", "hardship_amount", "hardship_start_date", "hardship_end_date",
    "payment_plan_start_date", "hardship_length", "hardship_dpd", "hardship_loan_status",
    "orig_projected_additional_accrued_interest", "hardship_payoff_balance_amount",
    "hardship_last_payment_amount",
    # PII & Unstructured Identifiers
    "id", "member_id", "url", "desc", "emp_title", "title", "zip_code"
}

# Good and Bad Target Status Sets
GOOD_STATUSES = {"Fully Paid", "Does not meet the credit policy. Status:Fully Paid"}
BAD_STATUSES = {"Charged Off", "Default", "Does not meet the credit policy. Status:Charged Off"}

# Candidate Point-in-Time Feature Specifications
NUMERICAL_FEATURES = [
    "loan_amnt", "funded_amnt", "funded_amnt_inv", "int_rate", "installment",
    "annual_inc", "dti", "delinq_2yrs", "fico_range_low", "fico_range_high",
    "inq_last_6mths", "open_acc", "pub_rec", "revol_bal", "revol_util",
    "total_acc", "tot_cur_bal", "total_rev_hi_lim", "acc_open_past_24mths",
    "avg_cur_bal", "bc_open_to_buy", "bc_util", "chargeoff_within_12_mths",
    "delinq_amnt", "mo_sin_old_il_acct", "mo_sin_old_rev_tl_op",
    "mo_sin_rcnt_rev_tl_op", "mo_sin_rcnt_tl", "mort_acc", "mths_since_recent_bc",
    "num_accts_ever_120_pd", "num_actv_bc_tl", "num_actv_rev_tl", "num_bc_sats",
    "num_bc_tl", "num_il_tl", "num_op_rev_tl", "num_rev_accts",
    "num_rev_tl_bal_gt_0", "num_sats", "num_tl_120dpd_2m", "num_tl_30dpd",
    "num_tl_90g_dpd_24m", "num_tl_op_past_12m", "pct_tl_nvr_dlq",
    "percent_bc_gt_75", "pub_rec_bankruptcies", "tax_liens", "tot_hi_cred_lim",
    "total_bal_ex_mort", "total_bc_limit", "total_il_high_credit_limit"
]

CATEGORICAL_FEATURES = [
    "term", "grade", "sub_grade", "emp_length", "home_ownership",
    "verification_status", "purpose", "addr_state", "initial_list_status",
    "application_type", "disbursement_method"
]


def compute_ks_statistic(y_true, y_prob):
    """Compute Kolmogorov-Smirnov (KS) statistic."""
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    if len(np.unique(y_true)) < 2 or len(np.unique(y_prob)) <= 1:
        return 0.0
    idx = np.argsort(y_prob)
    y_true_sorted = y_true[idx]
    
    n_pos = np.sum(y_true_sorted == 1)
    n_neg = np.sum(y_true_sorted == 0)
    if n_pos == 0 or n_neg == 0:
        return 0.0
        
    cum_pos = np.cumsum(y_true_sorted == 1) / n_pos
    cum_neg = np.cumsum(y_true_sorted == 0) / n_neg
    return float(np.max(np.abs(cum_pos - cum_neg)))


def parse_term_months(term_series):
    """Extract integer term in months from strings like '36 months' / '60 months'."""
    return term_series.str.extract(r"(\d+)")[0].astype(float)


def load_and_preprocess_data():
    print(f"Loading data from {LC_CSV_PATH} in chunked stream ...")
    if not os.path.exists(LC_CSV_PATH):
        raise FileNotFoundError(f"LendingClub CSV not found at {LC_CSV_PATH}")

    all_features = NUMERICAL_FEATURES + CATEGORICAL_FEATURES
    # Verify no prohibited feature is included
    prohibited_intersection = set(all_features) & PROHIBITED_COLUMNS
    if prohibited_intersection:
        raise ValueError(f"PROHIBITED LEAKAGE COLUMNS FOUND IN FEATURE SET: {prohibited_intersection}")

    load_cols = ["issue_d", "loan_status"] + all_features

    chunks = []
    chunksize = 100000
    for chunk in pd.read_csv(LC_CSV_PATH, chunksize=chunksize, usecols=load_cols, low_memory=False):
        # Filter to closed loans only (terminal statuses: Fully Paid / Charged Off / Default / policy variants)
        closed = chunk[chunk["loan_status"].isin(GOOD_STATUSES | BAD_STATUSES)].copy()
        if len(closed) == 0:
            continue
        closed["target"] = closed["loan_status"].isin(BAD_STATUSES).astype(int)
        closed["issue_year"] = closed["issue_d"].str.extract(r"(\d{4})")[0].astype(float)
        closed["term_months"] = parse_term_months(closed["term"])
        chunks.append(closed)

    df_all = pd.concat(chunks, ignore_index=True)
    print(f"Total Closed Loan Cohort Loaded: {len(df_all):,} records.")

    # Chronological Splitting
    # Train: 2007 - 2013
    # Val:   2014 - 2015
    # Test:  2016 - 2018 (closed loans only)
    train_df = df_all[(df_all["issue_year"] >= 2007) & (df_all["issue_year"] <= 2013)].copy()
    val_df   = df_all[(df_all["issue_year"] >= 2014) & (df_all["issue_year"] <= 2015)].copy()
    test_df  = df_all[(df_all["issue_year"] >= 2016) & (df_all["issue_year"] <= 2018)].copy()

    print(f"Train split (2007-2013): {len(train_df):,} samples")
    print(f"Val split   (2014-2015): {len(val_df):,} samples")
    print(f"Test split  (2016-2018): {len(test_df):,} samples")

    # Report issue-year and term distributions
    _print_cohort_distributions(train_df, val_df, test_df)

    return train_df, val_df, test_df, all_features


def _print_cohort_distributions(train_df, val_df, test_df):
    """Print issue-year and term distributions for each split, plus maturity caveat."""
    for name, df in [("Train", train_df), ("Validation", val_df), ("Test", test_df)]:
        print(f"\n--- {name} split distributions ---")
        year_dist = df["issue_year"].value_counts().sort_index()
        print(f"Issue-year counts (n={len(df):,}):")
        for yr, cnt in year_dist.items():
            print(f"  {int(yr)}: {cnt:,}")
        term_dist = df["term_months"].value_counts(dropna=False).sort_index()
        print(f"Term (months) counts:")
        for tm, cnt in term_dist.items():
            print(f"  {tm}: {cnt:,}")
    print("\nMaturity note: 'term' is the contractual loan length at origination "
          "(36 or 60 months). The target is the FINAL observed closed-loan status "
          "(Fully Paid / Charged Off / Default), NOT a fixed-horizon default flag. "
          "Closed loans issued in 2016-2018 may have reached a terminal state before "
          "their full contractual term (early payoff or early charge-off); this is a "
          "historical closed-loan outcome, not a 12/36-month fixed-horizon default.")


def export_feature_decisions(all_features):
    leakage_audit_path = os.path.join(REPORTS_DIR, "phase_2_2_feature_leakage_audit.csv")
    if os.path.exists(leakage_audit_path):
        df_audit = pd.read_csv(leakage_audit_path)
    else:
        df_audit = pd.DataFrame({"column": all_features, "recommended_action": "Include", "meaning": "Candidate feature", "reason": "Application feature"})

    decisions = []
    for col in df_audit["column"]:
        if col in all_features:
            decisions.append({
                "column": col,
                "category": df_audit.loc[df_audit["column"] == col, "availability_time"].values[0] if "availability_time" in df_audit else "Origination",
                "decision": "Included",
                "reason": df_audit.loc[df_audit["column"] == col, "reason"].values[0] if "reason" in df_audit else "Point-in-time origination feature"
            })
        else:
            decisions.append({
                "column": col,
                "category": df_audit.loc[df_audit["column"] == col, "availability_time"].values[0] if "availability_time" in df_audit else "Post-Origination/PII",
                "decision": "Excluded",
                "reason": df_audit.loc[df_audit["column"] == col, "reason"].values[0] if "reason" in df_audit else "Post-origination leakage or PII"
            })

    df_decisions = pd.DataFrame(decisions)
    out_path = os.path.join(REPORTS_DIR, "phase_2_3_feature_decisions.csv")
    df_decisions.to_csv(out_path, index=False)
    print(f"Saved feature decisions to {out_path}")


def export_split_summary(train_df, val_df, test_df):
    splits = [
        ("Train", "2007-01-01", "2013-12-31", train_df),
        ("Validation", "2014-01-01", "2015-12-31", val_df),
        ("Test", "2016-01-01", "2018-12-31", test_df),
    ]

    summary_rows = []
    for name, start_d, end_d, df in splits:
        tot = len(df)
        bad = int(df["target"].sum())
        good = tot - bad
        prev = round(bad / tot, 4) if tot > 0 else 0.0
        term_counts = df["term_months"].value_counts(dropna=False)
        n_36 = int(term_counts.get(36.0, 0))
        n_60 = int(term_counts.get(60.0, 0))
        summary_rows.append({
            "split_name": name,
            "start_date": start_d,
            "end_date": end_d,
            "total_samples": tot,
            "good_count": good,
            "bad_count": bad,
            "default_prevalence": prev,
            "term_36m_count": n_36,
            "term_60m_count": n_60,
        })

    df_summary = pd.DataFrame(summary_rows)
    out_path = os.path.join(REPORTS_DIR, "phase_2_3_split_summary.csv")
    df_summary.to_csv(out_path, index=False)
    print(f"Saved split summary to {out_path}")


def fit_preprocessing(train_df, val_df, test_df, num_features, cat_features):
    """Fit imputers, encoder and scaler STRICTLY on train data; transform all splits.

    Returns a dict with transformed matrices (X_train, X_val, X_test,
    X_train_scaled, X_val_scaled, X_test_scaled) and the fitted artifacts.
    This isolation is critical: no validation/test statistics may leak into
    imputation medians, categorical mappings or scaling moments.
    """
    # Numerical median imputation — fit on train only
    num_imputer = SimpleImputer(strategy="median")
    X_train_num = num_imputer.fit_transform(train_df[num_features])
    X_val_num = num_imputer.transform(val_df[num_features])
    X_test_num = num_imputer.transform(test_df[num_features])

    # Categorical ordinal encoding — fit on train only; unknown -> -1
    train_cat_str = train_df[cat_features].fillna("Missing").astype(str)
    val_cat_str = val_df[cat_features].fillna("Missing").astype(str)
    test_cat_str = test_df[cat_features].fillna("Missing").astype(str)

    cat_encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    X_train_cat = cat_encoder.fit_transform(train_cat_str)
    X_val_cat = cat_encoder.transform(val_cat_str)
    X_test_cat = cat_encoder.transform(test_cat_str)

    X_train = np.hstack([X_train_num, X_train_cat])
    X_val = np.hstack([X_val_num, X_val_cat])
    X_test = np.hstack([X_test_num, X_test_cat])

    # Standardization — fit on train only (used by Logistic Regression)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    return {
        "X_train": X_train,
        "X_val": X_val,
        "X_test": X_test,
        "X_train_scaled": X_train_scaled,
        "X_val_scaled": X_val_scaled,
        "X_test_scaled": X_test_scaled,
        "num_imputer": num_imputer,
        "cat_encoder": cat_encoder,
        "scaler": scaler,
    }


def fit_and_evaluate():
    train_df, val_df, test_df, candidate_features = load_and_preprocess_data()
    os.makedirs(REPORTS_DIR, exist_ok=True)

    # Filter features based on Train set missingness (>50% missing in 2007-2013 train set -> drop)
    train_num_nulls = train_df[NUMERICAL_FEATURES].isna().mean()
    valid_num_features = [col for col in NUMERICAL_FEATURES if train_num_nulls[col] < 0.50]

    train_cat_nulls = train_df[CATEGORICAL_FEATURES].isna().mean()
    valid_cat_features = [col for col in CATEGORICAL_FEATURES if train_cat_nulls[col] < 0.50]

    selected_features = valid_num_features + valid_cat_features
    print(f"Selected {len(selected_features)} features after Train missingness filter ({len(valid_num_features)} numerical, {len(valid_cat_features)} categorical).")

    export_feature_decisions(selected_features)
    export_split_summary(train_df, val_df, test_df)

    # Separate X and y
    y_train = train_df["target"].values
    y_val = val_df["target"].values
    y_test = test_df["target"].values

    # Preprocessing Pipeline (Fit strictly on Train)
    print("Fitting imputers and encoders on Train split only ...")
    prep = fit_preprocessing(train_df, val_df, test_df, valid_num_features, valid_cat_features)
    X_train = prep["X_train"]
    X_val = prep["X_val"]
    X_test = prep["X_test"]
    X_train_scaled = prep["X_train_scaled"]
    X_val_scaled = prep["X_val_scaled"]
    X_test_scaled = prep["X_test_scaled"]

    train_prev = np.mean(y_train)

    metrics_rows = []

    # Helper function to evaluate model predictions
    def evaluate_model(model_name, y_true, y_prob, threshold, is_baseline=False):
        if is_baseline:
            roc_auc = None
            pr_auc = round(float(np.mean(y_true)), 4)
            ks_stat = None
            gini = None
        else:
            roc_auc = round(float(roc_auc_score(y_true, y_prob)), 4)
            pr_auc  = round(float(average_precision_score(y_true, y_prob)), 4)
            ks_stat = round(float(compute_ks_statistic(y_true, y_prob)), 4)
            gini    = round(2.0 * roc_auc - 1.0, 4)

        brier = round(float(brier_score_loss(y_true, y_prob)), 4)
        loss  = round(float(log_loss(y_true, y_prob)), 4)

        y_pred = (y_prob >= threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        prec = round(float(precision_score(y_true, y_pred, zero_division=0)), 4)
        rec  = round(float(recall_score(y_true, y_pred, zero_division=0)), 4)
        f1   = round(float(f1_score(y_true, y_pred, zero_division=0)), 4)

        return {
            "model_name": model_name,
            "roc_auc": roc_auc,
            "pr_auc": pr_auc,
            "prevalence_baseline": round(float(np.mean(y_true)), 4),
            "brier_score": brier,
            "log_loss": loss,
            "ks_statistic": ks_stat,
            "gini_coefficient": gini,
            "selected_threshold": round(float(threshold), 4),
            "precision": prec,
            "recall": rec,
            "f1_score": f1,
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        }

    # 1. Prevalence Baseline Model
    print("Evaluating Prevalence Baseline ...")
    for split_name, y_s in [("Train", y_train), ("Validation", y_val), ("Test", y_test)]:
        probs = np.full(len(y_s), train_prev)
        m = evaluate_model("Prevalence Baseline", y_s, probs, threshold=0.5, is_baseline=True)
        m["split_name"] = split_name
        metrics_rows.append(m)

    # 2. Logistic Regression Model
    print("Training Logistic Regression ...")
    lr = LogisticRegression(C=1.0, max_iter=500, solver="lbfgs", random_state=RANDOM_SEED)
    lr.fit(X_train_scaled, y_train)

    val_probs_lr = lr.predict_proba(X_val_scaled)[:, 1]
    
    # Select threshold on Validation set to maximize F1
    best_thresh_lr = 0.5
    best_f1_lr = -1.0
    for t in np.linspace(0.1, 0.9, 81):
        f = f1_score(y_val, (val_probs_lr >= t).astype(int), zero_division=0)
        if f > best_f1_lr:
            best_f1_lr = f
            best_thresh_lr = t

    print(f"Logistic Regression Validation Selected Threshold: {best_thresh_lr:.2f} (F1: {best_f1_lr:.4f})")

    for split_name, y_s, X_s in [("Train", y_train, X_train_scaled), ("Validation", y_val, X_val_scaled), ("Test", y_test, X_test_scaled)]:
        probs = lr.predict_proba(X_s)[:, 1]
        m = evaluate_model("Logistic Regression", y_s, probs, threshold=best_thresh_lr)
        m["split_name"] = split_name
        metrics_rows.append(m)

    # 3. HistGradientBoostingClassifier Model
    print("Training HistGradientBoostingClassifier ...")
    hgb = HistGradientBoostingClassifier(max_iter=100, random_state=RANDOM_SEED)
    hgb.fit(X_train, y_train)

    val_probs_hgb = hgb.predict_proba(X_val)[:, 1]

    # Select threshold on Validation set to maximize F1
    best_thresh_hgb = 0.5
    best_f1_hgb = -1.0
    for t in np.linspace(0.1, 0.9, 81):
        f = f1_score(y_val, (val_probs_hgb >= t).astype(int), zero_division=0)
        if f > best_f1_hgb:
            best_f1_hgb = f
            best_thresh_hgb = t

    print(f"HistGradientBoosting Validation Selected Threshold: {best_thresh_hgb:.2f} (F1: {best_f1_hgb:.4f})")

    for split_name, y_s, X_s in [("Train", y_train, X_train), ("Validation", y_val, X_val), ("Test", y_test, X_test)]:
        probs = hgb.predict_proba(X_s)[:, 1]
        m = evaluate_model("HistGradientBoosting", y_s, probs, threshold=best_thresh_hgb)
        m["split_name"] = split_name
        metrics_rows.append(m)

    df_metrics = pd.DataFrame(metrics_rows)
    metrics_cols = ["model_name", "split_name", "roc_auc", "pr_auc", "prevalence_baseline", "brier_score", "log_loss", "ks_statistic", "gini_coefficient", "selected_threshold", "precision", "recall", "f1_score", "tn", "fp", "fn", "tp"]
    df_metrics = df_metrics[metrics_cols]
    
    out_metrics_path = os.path.join(REPORTS_DIR, "phase_2_3_metrics.csv")
    df_metrics.to_csv(out_metrics_path, index=False)
    print(f"Saved benchmark metrics to {out_metrics_path}")

    print("\n=== Benchmark Results Summary (Test Split) ===")
    test_metrics = df_metrics[df_metrics["split_name"] == "Test"]
    print(test_metrics[["model_name", "roc_auc", "pr_auc", "brier_score", "ks_statistic", "f1_score"]].to_string(index=False))


if __name__ == "__main__":
    fit_and_evaluate()
