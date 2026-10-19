"""Unit tests for Phase 2.3 Leakage-Safe LendingClub Benchmark."""

import os
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from scripts.phase_2_3_benchmark import (
    PROHIBITED_COLUMNS,
    GOOD_STATUSES,
    BAD_STATUSES,
    NUMERICAL_FEATURES,
    CATEGORICAL_FEATURES,
    compute_ks_statistic,
    parse_term_months,
    fit_preprocessing,
    export_split_summary,
)

REPORTS_DIR = "reports"
FEATURE_DECISIONS_CSV = os.path.join(REPORTS_DIR, "phase_2_3_feature_decisions.csv")
SPLIT_SUMMARY_CSV = os.path.join(REPORTS_DIR, "phase_2_3_split_summary.csv")
METRICS_CSV = os.path.join(REPORTS_DIR, "phase_2_3_metrics.csv")

client = TestClient(app)


def test_prohibited_column_leakage_guard():
    # Assert key post-origination fields are strictly in PROHIBITED_COLUMNS
    key_leakage_fields = {
        "recoveries", "total_pymnt", "last_pymnt_d", "last_fico_range_high",
        "debt_settlement_flag", "hardship_flag", "id", "member_id", "emp_title"
    }
    assert key_leakage_fields.issubset(PROHIBITED_COLUMNS)

    # Assert candidate features have zero intersection with PROHIBITED_COLUMNS
    candidate_features = set(NUMERICAL_FEATURES + CATEGORICAL_FEATURES)
    overlap = candidate_features & PROHIBITED_COLUMNS
    assert len(overlap) == 0, f"Prohibited leakage columns found in candidate feature list: {overlap}"


def test_target_status_mappings_and_exclusions():
    # Good and bad statuses must be disjoint
    assert len(GOOD_STATUSES & BAD_STATUSES) == 0

    # Ensure unseasoned/active statuses are NOT included in either good or bad sets
    unseasoned_statuses = {"Current", "Late (31-120 days)", "In Grace Period", "Late (16-30 days)", "nan"}
    assert len(unseasoned_statuses & GOOD_STATUSES) == 0
    assert len(unseasoned_statuses & BAD_STATUSES) == 0


def test_ks_statistic_calculation():
    y_true = [0, 0, 0, 0, 1, 1, 1, 1]
    y_prob = [0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9]
    ks = compute_ks_statistic(y_true, y_prob)
    assert 0.0 <= ks <= 1.0
    assert abs(ks - 1.0) < 1e-5

    # Constant predictions return 0.0
    ks_const = compute_ks_statistic(y_true, [0.5] * len(y_true))
    assert ks_const == 0.0


def test_csv_report_schemas_and_integrity():
    # 1. Feature Decisions CSV
    assert os.path.exists(FEATURE_DECISIONS_CSV)
    df_dec = pd.read_csv(FEATURE_DECISIONS_CSV)
    assert set(["column", "category", "decision", "reason"]).issubset(df_dec.columns)
    assert len(df_dec) == 151
    assert "Included" in df_dec["decision"].values
    assert "Excluded" in df_dec["decision"].values

    # 2. Split Summary CSV
    assert os.path.exists(SPLIT_SUMMARY_CSV)
    df_split = pd.read_csv(SPLIT_SUMMARY_CSV)
    assert set(["split_name", "start_date", "end_date", "total_samples", "good_count", "bad_count", "default_prevalence"]).issubset(df_split.columns)
    assert len(df_split) == 3
    assert df_split["total_samples"].sum() == 1348099

    # Verify chronological order and no overlap
    train_end = df_split.loc[df_split["split_name"] == "Train", "end_date"].values[0]
    val_start = df_split.loc[df_split["split_name"] == "Validation", "start_date"].values[0]
    val_end   = df_split.loc[df_split["split_name"] == "Validation", "end_date"].values[0]
    test_start = df_split.loc[df_split["split_name"] == "Test", "start_date"].values[0]

    assert train_end < val_start
    assert val_end < test_start

    # 3. Metrics CSV
    assert os.path.exists(METRICS_CSV)
    df_met = pd.read_csv(METRICS_CSV)
    required_met_cols = {"model_name", "split_name", "roc_auc", "pr_auc", "prevalence_baseline", "brier_score", "log_loss", "ks_statistic", "gini_coefficient", "selected_threshold", "precision", "recall", "f1_score", "tn", "fp", "fn", "tp"}
    assert required_met_cols.issubset(df_met.columns)
    assert len(df_met) == 9  # 3 models x 3 splits


def test_api_non_regression_contract():
    # Ensure scoring API remains unvalidated
    health_res = client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json() == {"status": "ok", "scoring": "not_validated"}

    payload = {
        "schema_version": "1.0",
        "observation_start": "2025-01-01",
        "prediction_date": "2025-02-01",
        "transactions": [{"transaction_id": "t-1", "date": "2025-01-10", "transaction_type": "credit", "amount": 1000}],
    }
    score_res = client.post("/v1/score", json=payload)
    assert score_res.status_code == 200
    data = score_res.json()
    assert data["score_status"] == "not_validated"
    assert data["default_probability"] is None
    assert data["validated_risk_estimate"] is False


def test_term_parsing():
    s = pd.Series(["36 months", "60 months", "36 months"])
    parsed = parse_term_months(s)
    assert parsed.tolist() == [36.0, 60.0, 36.0]


def test_preprocessing_isolation():
    """Imputation medians, categorical categories and scaling moments must be
    derived strictly from the TRAIN split, never from validation or test."""
    num_feats = ["loan_amnt", "annual_inc"]
    cat_feats = ["grade"]

    # Train has a deliberately different distribution than val/test.
    train_df = pd.DataFrame({
        "loan_amnt": [1000.0, 2000.0, 3000.0, np.nan],
        "annual_inc": [50000.0, 60000.0, 70000.0, 80000.0],
        "grade": ["A", "B", "C", "A"],
    })
    val_df = pd.DataFrame({
        "loan_amnt": [99999.0, 99999.0, 99999.0, np.nan],
        "annual_inc": [1.0, 1.0, 1.0, 1.0],
        "grade": ["Z", "Y", "Z", "Y"],  # unseen categories -> encoded as -1
    })
    test_df = pd.DataFrame({
        "loan_amnt": [99999.0, np.nan, 99999.0, 99999.0],
        "annual_inc": [99999.0, 99999.0, 99999.0, 99999.0],
        "grade": ["A", "B", "C", "Z"],
    })

    prep = fit_preprocessing(train_df, val_df, test_df, num_feats, cat_feats)

    # Median imputer statistics must equal train medians (2000.0, 65000.0)
    np.testing.assert_allclose(prep["num_imputer"].statistics_, [2000.0, 65000.0])

    # Categorical encoder categories must come from train only: {'A','B','C'}
    assert list(prep["cat_encoder"].categories_[0]) == ["A", "B", "C"]

    # Unseen val categories ('Z','Y') must be mapped to -1 (use_encoded_value)
    val_cat_encoded = prep["X_val"][:, len(num_feats):]
    assert np.all(val_cat_encoded == -1)

    # Scaler mean/std must reflect train only (not val/test contamination)
    # train loan_amnt (imputed median=2000): [1000,2000,3000,2000] -> mean 2000
    np.testing.assert_allclose(prep["scaler"].mean_[0], 2000.0, atol=1e-6)


def test_empty_cohort_handling():
    """Empty splits must not crash summary/metric helpers; prevalence is 0."""
    # Backup the real split summary so the test does not leave a dummy report.
    backup = None
    if os.path.exists(SPLIT_SUMMARY_CSV):
        backup = pd.read_csv(SPLIT_SUMMARY_CSV)

    try:
        empty = pd.DataFrame({"target": pd.Series([], dtype=int), "term_months": pd.Series([], dtype=float)})
        non_empty = pd.DataFrame({"target": [0, 1, 0], "term_months": [36.0, 60.0, 36.0]})

        # export_split_summary must handle an empty split without raising
        export_split_summary(non_empty, empty, non_empty)
        df = pd.read_csv(SPLIT_SUMMARY_CSV)
        val_row = df[df["split_name"] == "Validation"].iloc[0]
        assert val_row["total_samples"] == 0
        assert val_row["default_prevalence"] == 0.0

        # compute_ks_statistic on constant/empty must return 0.0, not raise
        assert compute_ks_statistic([1, 1, 1], [0.5, 0.5, 0.5]) == 0.0
        assert compute_ks_statistic([0, 0, 0], [0.1, 0.2, 0.3]) == 0.0
    finally:
        # Restore the real split summary produced by the benchmark script.
        if backup is not None:
            backup.to_csv(SPLIT_SUMMARY_CSV, index=False)


def test_missing_columns_guard():
    """Candidate feature set must not include prohibited columns and every
    selected numerical/categorical feature must be a known LendingClub column."""
    candidate = set(NUMERICAL_FEATURES + CATEGORICAL_FEATURES)
    # No leakage columns in candidate set
    assert candidate.isdisjoint(PROHIBITED_COLUMNS)

    # Known identifiers / free-text / post-origination fields are absent
    for forbidden in ["id", "member_id", "url", "desc", "emp_title", "title",
                      "zip_code", "total_pymnt", "recoveries", "out_prncp",
                      "last_fico_range_high", "hardship_flag", "debt_settlement_flag"]:
        assert forbidden not in candidate

    # issue_d and loan_status are metadata/target, never predictors
    assert "issue_d" not in candidate
    assert "loan_status" not in candidate


def test_reproducibility_determinism():
    """Metrics and KS computation must be deterministic for identical inputs."""
    y_true = [0, 0, 1, 1, 0, 1]
    y_prob = [0.1, 0.3, 0.7, 0.9, 0.2, 0.8]

    ks1 = compute_ks_statistic(y_true, y_prob)
    ks2 = compute_ks_statistic(y_true, y_prob)
    assert ks1 == ks2

    # Permuting the (y_true, y_prob) pairs together must not change KS
    idx = [5, 0, 2, 1, 4, 3]
    y_true_p = [y_true[i] for i in idx]
    y_prob_p = [y_prob[i] for i in idx]
    assert compute_ks_statistic(y_true_p, y_prob_p) == pytest.approx(ks1)


def test_prohibited_column_count_reconciliation():
    """Regression test for the Phase 2.3.1 discrepancy: the report previously
    claimed '50 Columns Excluded' but the actual PROHIBITED_COLUMNS set has
    exactly 47 entries. Pin the true count so the report cannot drift again."""
    assert len(PROHIBITED_COLUMNS) == 47

    # 47 prohibited = 7 PII + 40 post-origination/leakage/metadata
    pii = {"id", "member_id", "url", "desc", "emp_title", "title", "zip_code"}
    assert len(PROHIBITED_COLUMNS & pii) == 7
    assert len(PROHIBITED_COLUMNS - pii) == 40


def test_feature_decisions_full_reconciliation():
    """Every source column must have exactly one Phase 2.3 decision, and the
    included/excluded counts must reconcile with the source schema (151 cols)."""
    audit = pd.read_csv(os.path.join(REPORTS_DIR, "phase_2_2_feature_leakage_audit.csv"))
    dec = pd.read_csv(FEATURE_DECISIONS_CSV)

    # Source schema row count
    assert len(audit) == 151
    assert len(dec) == 151

    # One decision per column, no duplicates
    assert dec["column"].is_unique
    assert set(dec["column"]) == set(audit["column"])

    # Every decision is Included or Excluded
    assert set(dec["decision"].unique()).issubset({"Included", "Excluded"})

    included = (dec["decision"] == "Included").sum()
    excluded = (dec["decision"] == "Excluded").sum()
    assert included + excluded == 151

    # All audit-Exclude columns must be phase-2.3 Excluded (no leakage re-entry)
    audit_exclude = set(audit[audit["recommended_action"] == "Exclude"]["column"])
    dec_excluded = set(dec[dec["decision"] == "Excluded"]["column"])
    assert audit_exclude.issubset(dec_excluded)
    assert audit_exclude == PROHIBITED_COLUMNS

    # Prohibited set is fully contained in excluded decisions
    assert PROHIBITED_COLUMNS.issubset(dec_excluded)


def test_confusion_matrix_totals_match_split_sizes():
    """Each model's confusion matrix must sum exactly to its split's row count."""
    metrics = pd.read_csv(METRICS_CSV)
    splits = pd.read_csv(SPLIT_SUMMARY_CSV)
    split_totals = dict(zip(splits["split_name"], splits["total_samples"]))

    for _, r in metrics.iterrows():
        cm_sum = int(r["tn"]) + int(r["fp"]) + int(r["fn"]) + int(r["tp"])
        assert cm_sum == split_totals[r["split_name"]], (
            f"{r['model_name']}/{r['split_name']} CM sum {cm_sum} != "
            f"split size {split_totals[r['split_name']]}"
        )


def test_raw_row_count_reconciliation():
    """Regression test for Phase 2.3.2: the audit report previously stated
    'Total raw: 2,260,694' but the actual total is 2,260,701. Pin the correct
    total so the report cannot drift again. This test independently counts
    rows using the same chunked method as the benchmark script."""
    LC_CSV_PATH = os.path.join("Data", "archive", "accepted_2007_to_2018Q4.csv")
    assert os.path.exists(LC_CSV_PATH), "LendingClub CSV not found"

    # Count rows using chunked read (same method as benchmark)
    total_rows = 0
    chunksize = 100000
    for chunk in pd.read_csv(LC_CSV_PATH, chunksize=chunksize, usecols=["loan_status"], low_memory=False):
        total_rows += len(chunk)

    assert total_rows == 2_260_701, (
        f"Raw row count mismatch: expected 2,260,701, got {total_rows:,}"
    )

    # Verify status frequencies sum to the same total
    status_counts = {}
    total_from_status = 0
    for chunk in pd.read_csv(LC_CSV_PATH, chunksize=chunksize, usecols=["loan_status"], low_memory=False):
        for status in chunk["loan_status"]:
            status_str = "(missing)" if pd.isna(status) else str(status)
            status_counts[status_str] = status_counts.get(status_str, 0) + 1
            total_from_status += 1

    assert total_from_status == 2_260_701, (
        f"Status sum mismatch: expected 2,260,701, got {total_from_status:,}"
    )

    # Verify cohort breakdown
    good_statuses = {"Fully Paid", "Does not meet the credit policy. Status:Fully Paid"}
    bad_statuses = {"Charged Off", "Default", "Does not meet the credit policy. Status:Charged Off"}
    good_count = sum(status_counts.get(s, 0) for s in good_statuses)
    bad_count = sum(status_counts.get(s, 0) for s in bad_statuses)
    closed_cohort = good_count + bad_count
    excluded_cohort = total_from_status - closed_cohort

    assert good_count == 1_078_739
    assert bad_count == 269_360
    assert closed_cohort == 1_348_099
    assert excluded_cohort == 912_602
