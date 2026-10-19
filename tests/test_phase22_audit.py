"""Unit tests for Phase 2.2 Dataset Qualification & LendingClub Label Audit."""

import os
import pandas as pd
import pytest

from scripts.phase_2_2_audit import run_audit, COLUMN_METADATA

REPORTS_DIR = "reports"
LABEL_CSV = os.path.join(REPORTS_DIR, "phase_2_2_lendingclub_label_audit.csv")
LEAKAGE_CSV = os.path.join(REPORTS_DIR, "phase_2_2_feature_leakage_audit.csv")


def test_label_audit_csv_schema_and_integrity():
    assert os.path.exists(LABEL_CSV), f"Label audit CSV missing at {LABEL_CSV}"
    df = pd.read_csv(LABEL_CSV)
    required_cols = {"loan_status_value", "count", "percentage", "proposed_classification", "inclusion_status", "rationale"}
    assert required_cols.issubset(df.columns)

    # Check that counts add up to 2,260,701
    assert df["count"].sum() == 2260701

    # Check key status classifications
    fully_paid_row = df[df["loan_status_value"] == "Fully Paid"].iloc[0]
    assert fully_paid_row["proposed_classification"] == "Good / Non-Default"
    assert fully_paid_row["inclusion_status"] == "Included"

    charged_off_row = df[df["loan_status_value"] == "Charged Off"].iloc[0]
    assert charged_off_row["proposed_classification"] == "Bad / Default"
    assert charged_off_row["inclusion_status"] == "Included"

    current_row = df[df["loan_status_value"] == "Current"].iloc[0]
    assert current_row["proposed_classification"] == "Ambiguous / Active"
    assert current_row["inclusion_status"] == "Excluded"


def test_feature_leakage_csv_schema_and_column_count():
    assert os.path.exists(LEAKAGE_CSV), f"Feature leakage CSV missing at {LEAKAGE_CSV}"
    df = pd.read_csv(LEAKAGE_CSV)
    required_cols = {"column", "meaning", "availability_time", "leakage_risk", "recommended_action", "missing_pct", "reason"}
    assert required_cols.issubset(df.columns)

    # All 151 columns must be audited
    assert len(df) == 151, f"Expected 151 audited columns, found {len(df)}"

    # Ensure no unclassified features remain
    unclassified = df[df["meaning"] == "Unclassified feature"]
    assert len(unclassified) == 0, f"Found unclassified columns: {unclassified['column'].tolist()}"


def test_leakage_classification_rules():
    df = pd.read_csv(LEAKAGE_CSV).set_index("column")

    # Post-origination fields must be excluded as target leakage
    for post_col in ["recoveries", "total_pymnt", "last_pymnt_d", "last_fico_range_high", "debt_settlement_flag"]:
        assert df.loc[post_col, "recommended_action"] == "Exclude"
        assert df.loc[post_col, "leakage_risk"] == "High (Target Leakage)"

    # PII/Identifiers must be excluded
    for pii_col in ["id", "member_id", "emp_title", "url", "desc"]:
        assert df.loc[pii_col, "recommended_action"] == "Exclude"
        assert df.loc[pii_col, "leakage_risk"] == "Identifier/PII"

    # Application-time features must be included
    for app_col in ["loan_amnt", "term", "int_rate", "annual_inc", "dti", "fico_range_low"]:
        assert df.loc[app_col, "recommended_action"] == "Include"
        assert df.loc[app_col, "leakage_risk"] == "None/Low"


def test_no_raw_borrower_pii_in_reports():
    # Verify report files do not contain sample borrower names or raw text snippets
    for filepath in [LABEL_CSV, LEAKAGE_CSV]:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            # Ensure no mock PII strings or raw text quotes exist
            assert "John Doe" not in content
            assert "SSN" not in content
