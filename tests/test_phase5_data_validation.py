"""Synthetic-only unit tests for Phase 5 data validation infrastructure.

All tests use deterministic synthetic fixtures. No real borrower data is used.
"""

import pytest
import numpy as np

from src.data_intake.contract import ContractError, validate_dataset_manifest, check_processing_permission
from src.data_quality.validator import (
    ValidationReport,
    validate_schema,
    validate_data_types,
    validate_duplicates,
    validate_chronology,
    validate_monetary_values,
    validate_missingness,
    validate_target_balance,
    run_full_validation,
)
from src.temporal_audit.audit import (
    TemporalAuditReport,
    validate_feature_availability,
    validate_target_definition,
    validate_outcome_window_leakage,
    validate_censoring_handling,
    run_full_temporal_audit,
)
from src.qualification.gate import qualify_dataset, check_qualification_criteria
from src.evaluation.metrics import (
    compute_roc_auc,
    compute_pr_auc,
    compute_brier_score,
    compute_log_loss,
    compute_ks_statistic,
    compute_gini_coefficient,
    compute_confusion_matrix,
    compute_all_metrics,
    compute_prevalence,
)
from src.evaluation.splitting import (
    chronological_split,
    grouped_chronological_split,
    check_train_test_overlap,
    random_split,
)


# =============================================================================
# Synthetic Test Fixtures
# =============================================================================

def valid_manifest():
    """Return a valid synthetic dataset manifest."""
    return {
        "dataset_id": "synthetic_test_dataset_001",
        "dataset_version": "1.0",
        "schema_version": "1.0",
        "source_organization": "Synthetic Lender Ltd.",
        "provenance_reference": "Synthetic test data for unit testing",
        "permission_status": "authorized_documented",
        "prediction_timestamp_definition": {
            "field_name": "decision_date",
        },
        "observation_window_definition": {
            "start_field": "application_date",
            "end_field": "observation_end_date",
        },
        "outcome_definition": {
            "target_field": "default_flag",
            "target_event": "90_plus_dpd",
            "horizon_months": 12,
            "censoring_field": "censoring_flag",
            "closure_status_field": "closure_status",
        },
        "borrower_id_field": "borrower_pseudo_id",
        "field_definitions": [
            {
                "field_name": "borrower_pseudo_id",
                "data_type": "categorical",
                "observation_timestamp": "application_date",
                "required": True,
            },
            {
                "field_name": "application_date",
                "data_type": "date",
                "observation_timestamp": "application_date",
                "role": "start",
            },
            {
                "field_name": "decision_date",
                "data_type": "date",
                "observation_timestamp": "decision_date",
            },
            {
                "field_name": "observation_end_date",
                "data_type": "date",
                "observation_timestamp": "observation_end_date",
            },
            {
                "field_name": "loan_amount",
                "data_type": "numeric",
                "observation_timestamp": "decision_date",
                "is_monetary": True,
            },
            {
                "field_name": "default_flag",
                "data_type": "numeric",
                "observation_timestamp": "outcome",
            },
            {
                "field_name": "censoring_flag",
                "data_type": "numeric",
                "observation_timestamp": "outcome",
            },
            {
                "field_name": "closure_status",
                "data_type": "categorical",
                "observation_timestamp": "outcome",
            },
        ],
    }


def valid_synthetic_rows():
    """Return valid synthetic row data.

    Loan flags use 0/1 integers, which is typical for credit tables.
    Manifest field types for those columns are numeric so type checks
    do not emit warnings on otherwise valid research rows.
    Observation windows are at least the 12-month target horizon so
    mature labels can qualify.
    """
    return [
        {
            "borrower_pseudo_id": "borrower_001",
            "application_date": "2023-01-01",
            "decision_date": "2023-01-05",
            "observation_end_date": "2024-02-01",
            "loan_amount": 100000,
            "default_flag": 0,
            "censoring_flag": 0,
            "closure_status": "fully_paid",
        },
        {
            "borrower_pseudo_id": "borrower_002",
            "application_date": "2023-01-02",
            "decision_date": "2023-01-06",
            "observation_end_date": "2024-02-01",
            "loan_amount": 150000,
            "default_flag": 1,
            "censoring_flag": 0,
            "closure_status": "charged_off",
        },
        {
            "borrower_pseudo_id": "borrower_003",
            "application_date": "2023-01-03",
            "decision_date": "2023-01-07",
            "observation_end_date": "2024-02-01",
            "loan_amount": 200000,
            "default_flag": 0,
            "censoring_flag": 1,
            "closure_status": "active",
        },
    ]


# =============================================================================
# Data Intake Contract Tests
# =============================================================================

def test_valid_manifest_passes():
    manifest = valid_manifest()
    result = validate_dataset_manifest(manifest)
    assert result == manifest


def test_missing_required_field_fails():
    manifest = valid_manifest()
    del manifest["dataset_id"]
    with pytest.raises(ContractError, match="Required manifest fields are missing"):
        validate_dataset_manifest(manifest)


def test_invalid_permission_status_fails():
    manifest = valid_manifest()
    manifest["permission_status"] = "invalid_status"
    with pytest.raises(ContractError, match="must be one of"):
        validate_dataset_manifest(manifest)


def test_check_processing_permission():
    assert check_processing_permission("authorized_documented") is True
    assert check_processing_permission("authorized_pending_legal_signoff") is True
    assert check_processing_permission("pending_review") is False
    assert check_processing_permission("rejected") is False


# =============================================================================
# Data Quality Validation Tests
# =============================================================================

def test_schema_validation_missing_required_column():
    rows = [{"col1": 1, "col2": 2}]
    required = {"col1", "col2", "col3"}
    report = validate_schema(rows, required)
    assert not report.passed
    assert any(i.code == "missing_required_columns" for i in report.issues)


def test_schema_validation_unexpected_column():
    rows = [{"col1": 1, "col2": 2, "col3": 3}]
    required = {"col1", "col2"}
    allowed = {"col1", "col2"}
    report = validate_schema(rows, required, allowed)
    assert any(i.code == "unexpected_columns" for i in report.issues)


def test_duplicate_ids_detected():
    rows = [
        {"id": "001", "value": 1},
        {"id": "002", "value": 2},
        {"id": "001", "value": 3},  # Duplicate
    ]
    report = validate_duplicates(rows, "id")
    assert not report.passed
    assert any(i.code == "duplicate_ids" for i in report.issues)


def test_chronology_violation_detected():
    rows = [
        {"start_date": "2024-01-10", "decision_date": "2024-01-05"},  # start > decision
    ]
    report = validate_chronology(rows, {"start_date": "start", "decision_date": "decision"})
    assert not report.passed
    assert any(i.code == "chronology_violation" for i in report.issues)


def test_monetary_validation_negative_values():
    rows = [
        {"amount": -100},
        {"amount": 200},
    ]
    report = validate_monetary_values(rows, {"amount"}, allow_negative=False)
    assert any(i.code == "negative_monetary" for i in report.issues)


def test_target_balance_extreme_imbalance():
    rows = [{"target": 0}] * 100 + [{"target": 1}] * 1
    report = validate_target_balance(rows, "target")
    assert any(i.code == "extreme_imbalance" for i in report.issues)


def test_full_validation_integration():
    manifest = valid_manifest()
    rows = valid_synthetic_rows()
    report = run_full_validation(rows, manifest)
    assert report.passed
    assert not any(i.severity == "ERROR" for i in report.issues)


def test_combined_validation_propagates_child_errors():
    manifest = valid_manifest()
    rows = valid_synthetic_rows()
    rows.append(dict(rows[0]))
    report = run_full_validation(rows, manifest)
    assert not report.passed
    assert any(i.code == "duplicate_ids" and i.severity == "ERROR" for i in report.issues)


# =============================================================================
# Temporal Audit Tests
# =============================================================================

def test_future_feature_leakage_detected():
    manifest = valid_manifest()
    rows = [
        {
            "borrower_pseudo_id": "borrower_001",
            "decision_date": "2024-01-05",
            "feature_date": "2024-01-10",  # After decision
        },
    ]
    # Add field definition with observation timestamp from data
    manifest["field_definitions"].append({
        "field_name": "feature_date",
        "data_type": "date",
        "observation_timestamp": "feature_date",
    })
    report = validate_feature_availability(rows, manifest)
    assert not report.passed
    assert any(i.code == "future_feature_leakage" for i in report.issues)


def test_immature_labels_detected():
    manifest = valid_manifest()
    rows = [
        {
            "borrower_pseudo_id": "borrower_001",
            "decision_date": "2024-01-05",
            "observation_end_date": "2024-06-01",  # Only 5 months, less than 12-month horizon
            "default_flag": 0,
            "censoring_flag": 0,
            "closure_status": "active",
        },
    ]
    manifest["observation_window_definition"]["end_field"] = "observation_end_date"
    report = validate_target_definition(rows, manifest)
    assert any(i.code == "immature_labels" for i in report.issues)


def test_contradictory_labels_detected():
    manifest = valid_manifest()
    rows = [
        {
            "default_flag": 1,
            "closure_status": "fully_paid",  # Contradictory
        },
    ]
    report = validate_target_definition(rows, manifest)
    assert not report.passed
    assert any(i.code == "contradictory_labels" for i in report.issues)


def test_full_temporal_audit_integration():
    manifest = valid_manifest()
    rows = valid_synthetic_rows()
    report = run_full_temporal_audit(rows, manifest)
    assert report.passed
    assert not any(i.severity == "ERROR" for i in report.issues)


def test_combined_temporal_audit_propagates_child_errors():
    manifest = valid_manifest()
    rows = [
        {
            "borrower_pseudo_id": "borrower_001",
            "decision_date": "2024-01-05",
            "feature_date": "2024-01-10",
            "default_flag": 0,
        },
    ]
    manifest["field_definitions"].append({
        "field_name": "feature_date",
        "data_type": "date",
        "observation_timestamp": "feature_date",
    })
    report = run_full_temporal_audit(rows, manifest)
    assert not report.passed
    assert any(i.code == "future_feature_leakage" and i.severity == "ERROR" for i in report.issues)


# =============================================================================
# Qualification Gate Tests
# =============================================================================

def test_qualified_for_research_with_valid_data():
    manifest = valid_manifest()
    rows = valid_synthetic_rows()
    result = qualify_dataset(rows, manifest, require_human_permission_review=False)
    assert result.status == "QUALIFIED_FOR_RESEARCH"
    assert result.manifest_valid
    assert result.data_quality_passed
    assert result.temporal_audit_passed


def test_blocked_with_invalid_manifest():
    manifest = valid_manifest()
    del manifest["dataset_id"]
    rows = valid_synthetic_rows()
    result = qualify_dataset(rows, manifest)
    assert result.status == "BLOCKED"
    assert not result.manifest_valid


def test_review_required_with_pending_permission():
    manifest = valid_manifest()
    manifest["permission_status"] = "pending_review"
    rows = valid_synthetic_rows()
    result = qualify_dataset(rows, manifest, require_human_permission_review=True)
    # Fail-closed: unauthorized metadata is an ERROR, so the gate blocks.
    assert result.status == "BLOCKED"
    assert result.status != "QUALIFIED_FOR_RESEARCH"


def test_pending_permission_without_forced_review_is_not_qualified():
    manifest = valid_manifest()
    manifest["permission_status"] = "pending_review"
    rows = valid_synthetic_rows()
    result = qualify_dataset(rows, manifest, require_human_permission_review=False)
    assert result.status == "REVIEW_REQUIRED"
    assert result.status != "QUALIFIED_FOR_RESEARCH"


def test_missing_manifest_evidence_is_not_qualified():
    manifest = valid_manifest()
    del manifest["dataset_id"]
    result = qualify_dataset(valid_synthetic_rows(), manifest)
    assert result.status != "QUALIFIED_FOR_RESEARCH"
    assert result.status == "BLOCKED"


def test_check_qualification_criteria():
    manifest = valid_manifest()
    criteria = check_qualification_criteria(manifest)
    assert criteria["provenance_documented"]
    assert criteria["authorization_documented"]
    assert criteria["borrower_id_documented"]
    assert criteria["prediction_timestamp_documented"]
    assert criteria["outcome_documented"]
    assert criteria["horizon_documented"]


# =============================================================================
# Evaluation Metrics Tests
# =============================================================================

def test_roc_auc_computation():
    y_true = np.array([0, 0, 1, 1])
    y_score = np.array([0.1, 0.4, 0.35, 0.8])
    result = compute_roc_auc(y_true, y_score)
    assert result.available
    assert result.value is not None
    assert 0 <= result.value <= 1


def test_roc_auc_unavailable_for_one_class():
    y_true = np.array([0, 0, 0, 0])
    y_score = np.array([0.1, 0.2, 0.3, 0.4])
    result = compute_roc_auc(y_true, y_score)
    assert not result.available
    assert result.value is None


def test_pr_auc_computation():
    y_true = np.array([0, 0, 1, 1])
    y_score = np.array([0.1, 0.4, 0.35, 0.8])
    result = compute_pr_auc(y_true, y_score)
    assert result.available
    assert result.value is not None


def test_brier_score_computation():
    y_true = np.array([0, 0, 1, 1])
    y_score = np.array([0.1, 0.4, 0.35, 0.8])
    result = compute_brier_score(y_true, y_score)
    assert result.available
    assert result.value is not None
    assert 0 <= result.value <= 1


def test_log_loss_computation():
    y_true = np.array([0, 0, 1, 1])
    y_score = np.array([0.1, 0.4, 0.35, 0.8])
    result = compute_log_loss(y_true, y_score)
    assert result.available
    assert result.value is not None


def test_log_loss_unavailable_for_boundary_probabilities():
    y_true = np.array([0, 0, 1, 1])
    y_score = np.array([0.0, 0.5, 0.5, 1.0])  # 0 and 1 boundaries
    result = compute_log_loss(y_true, y_score)
    assert not result.available


def test_ks_statistic_computation():
    y_true = np.array([0, 0, 1, 1])
    y_score = np.array([0.1, 0.4, 0.35, 0.8])
    result = compute_ks_statistic(y_true, y_score)
    assert result.available
    assert result.value is not None


def test_gini_coefficient_computation():
    y_true = np.array([0, 0, 1, 1])
    y_score = np.array([0.1, 0.4, 0.35, 0.8])
    result = compute_gini_coefficient(y_true, y_score)
    assert result.available
    assert result.value is not None


def test_confusion_matrix_uses_caller_threshold_not_test_labels():
    """Phase 5 does not select a threshold from labels; callers must pass it."""
    y_true = np.array([0, 0, 1, 1])
    y_pred = np.array([0.1, 0.2, 0.8, 0.9])
    result = compute_confusion_matrix(y_true, y_pred, threshold=0.7)
    assert result["threshold"] == 0.7
    assert result["threshold"] != float(np.median(y_pred))


def test_confusion_matrix_computation():
    y_true = np.array([0, 0, 1, 1])
    y_pred = np.array([0.1, 0.4, 0.35, 0.8])
    result = compute_confusion_matrix(y_true, y_pred, threshold=0.5)
    assert result["available"]
    assert "confusion_matrix" in result
    assert "precision" in result
    assert "recall" in result


def test_all_metrics_computation():
    y_true = np.array([0, 0, 1, 1])
    y_score = np.array([0.1, 0.4, 0.35, 0.8])
    result = compute_all_metrics(y_true, y_score)
    assert "roc_auc" in result
    assert "pr_auc" in result
    assert "brier_score" in result
    assert "log_loss" in result
    assert "ks_statistic" in result
    assert "gini_coefficient" in result
    assert "confusion_matrix" in result


def test_prevalence_computation():
    y_true = np.array([0, 0, 1, 1])
    prevalence = compute_prevalence(y_true)
    assert prevalence == 0.5


# =============================================================================
# Splitting Tests
# =============================================================================

def test_chronological_split():
    dates = ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01"]
    result = chronological_split(dates, "2024-02-01", "2024-03-01", "2024-05-01")
    assert len(result.train_indices) > 0
    assert len(result.validation_indices) > 0
    assert len(result.test_indices) > 0
    train_dates = [dates[i] for i in result.train_indices]
    val_dates = [dates[i] for i in result.validation_indices]
    test_dates = [dates[i] for i in result.test_indices]
    assert max(train_dates) <= "2024-02-01"
    assert min(val_dates) > "2024-02-01" and max(val_dates) <= "2024-03-01"
    assert min(test_dates) > "2024-03-01" and max(test_dates) <= "2024-05-01"
    assert set(result.train_indices).isdisjoint(result.validation_indices)
    assert set(result.train_indices).isdisjoint(result.test_indices)


def test_chronological_split_invalid_order():
    dates = ["2024-01-01", "2024-02-01"]
    with pytest.raises(ValueError, match="chronological order"):
        chronological_split(dates, "2024-03-01", "2024-02-01", "2024-04-01")


def test_grouped_chronological_split():
    dates = ["2024-01-01", "2024-01-15", "2024-02-15", "2024-03-01", "2024-04-01", "2024-05-01"]
    group_ids = ["A", "A", "B", "B", "C", "C"]
    result = grouped_chronological_split(dates, group_ids, "2024-02-01", "2024-03-01", "2024-05-01")
    assert len(result.train_indices) > 0
    assert len(result.validation_indices) > 0
    assert len(result.test_indices) > 0
    train_groups = {group_ids[i] for i in result.train_indices}
    val_groups = {group_ids[i] for i in result.validation_indices}
    test_groups = {group_ids[i] for i in result.test_indices}
    assert train_groups.isdisjoint(val_groups)
    assert train_groups.isdisjoint(test_groups)
    assert val_groups.isdisjoint(test_groups)


def test_check_train_test_overlap():
    train_indices = np.array([0, 1, 2])
    test_indices = np.array([3, 4, 5])
    result = check_train_test_overlap(train_indices, test_indices)
    assert result["index_overlap"]


def test_check_train_test_group_overlap():
    train_indices = np.array([0, 1, 2])
    test_indices = np.array([3, 4, 5])
    group_ids = ["A", "B", "C", "A", "B", "C"]
    result = check_train_test_overlap(train_indices, test_indices, group_ids)
    assert not result["group_overlap"]  # Different groups


def test_random_split():
    result = random_split(100, train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15, random_seed=42)
    assert len(result.train_indices) == 70
    assert len(result.validation_indices) == 15
    assert len(result.test_indices) == 15


# =============================================================================
# API Regression Tests
# =============================================================================

def test_api_non_regression_contract():
    """Verify that the API contract remains unchanged."""
    from src.api.contract import not_validated_response
    response = not_validated_response("test-request-123")
    assert response["score_status"] == "not_validated"
    assert response["default_probability"] is None
    assert response["validated_risk_estimate"] is False
    assert response["model_version"] is None
    assert response["provenance"] == {"source": "no_validated_model", "synthetic_demo": False}
    assert response["request_id"] == "test-request-123"


# =============================================================================
# Safe Error Message Tests
# =============================================================================

def test_error_messages_do_not_expose_record_contents():
    """Verify that error messages do not expose raw record data."""
    manifest = valid_manifest()
    rows = valid_synthetic_rows()
    rows[0]["borrower_pseudo_id"] = "sensitive_id_12345"
    
    # Run validation
    report = run_full_validation(rows, manifest)
    
    # Check that no error message contains the sensitive ID
    for issue in report.issues:
        assert "sensitive_id_12345" not in issue.message
        if issue.details:
            assert "sensitive_id_12345" not in str(issue.details)


# =============================================================================
# Unauthorized Dataset Status Tests
# =============================================================================

def test_unauthorized_dataset_blocked():
    manifest = valid_manifest()
    manifest["permission_status"] = "rejected"
    rows = valid_synthetic_rows()
    result = qualify_dataset(rows, manifest)
    assert result.status == "BLOCKED"
    assert any(i["code"] == "permission_not_ready" for i in result.issues)
    assert "permission" in " ".join(i["message"].lower() for i in result.issues)


# =============================================================================
# Test that no model training occurs
# =============================================================================

def test_no_model_training_in_validation():
    """Verify that validation pipeline does not train any models."""
    manifest = valid_manifest()
    rows = valid_synthetic_rows()
    
    # Run qualification
    result = qualify_dataset(rows, manifest)
    
    # Verify no model artifacts are created
    assert "model" not in str(result.details).lower()
    assert "training" not in str(result.details).lower()
    assert "fit" not in str(result.details).lower()
