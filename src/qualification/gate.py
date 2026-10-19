"""Dataset qualification gate for research readiness.

This module orchestrates all validation checks and returns a final qualification
status for a dataset: BLOCKED, REVIEW_REQUIRED, or QUALIFIED_FOR_RESEARCH.

IMPORTANT: QUALIFIED_FOR_RESEARCH does NOT mean production-ready or legally certified.
It means the dataset passes documented checks for the specified research purpose.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from src.data_intake.contract import ContractError, validate_dataset_manifest, check_processing_permission
from src.data_quality.validator import ValidationReport, run_full_validation
from src.temporal_audit.audit import TemporalAuditReport, run_full_temporal_audit


@dataclass
class QualificationResult:
    """Result of dataset qualification."""
    status: Literal["BLOCKED", "REVIEW_REQUIRED", "QUALIFIED_FOR_RESEARCH"]
    message: str
    manifest_valid: bool
    data_quality_passed: bool
    temporal_audit_passed: bool
    permission_status: str
    issues: list[dict[str, Any]] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


def qualify_dataset(
    df_rows: list[dict[str, Any]],
    manifest: dict[str, Any],
    require_human_permission_review: bool = True,
) -> QualificationResult:
    """Run full qualification pipeline on a dataset.

    Args:
        df_rows: List of row dictionaries (sample or full dataset).
        manifest: Dataset manifest from data_intake.contract.
        require_human_permission_review: If True, require explicit human review of permission status.

    Returns:
        QualificationResult with final status and details.
    """
    issues = []
    details = {}

    # Step 1: Validate manifest
    manifest_valid = True
    try:
        validate_dataset_manifest(manifest)
        details["manifest_validation"] = "passed"
    except ContractError as e:
        manifest_valid = False
        details["manifest_validation"] = "failed"
        issues.append({
            "stage": "manifest_validation",
            "severity": "ERROR",
            "code": e.code,
            "message": e.message,
            "field": e.field,
        })

    # Step 2: Check permission status (metadata only, NOT legal proof)
    permission_status = manifest.get("permission_status", "pending_review")
    processing_permitted = check_processing_permission(permission_status)

    if require_human_permission_review and not processing_permitted:
        issues.append({
            "stage": "permission_check",
            "severity": "ERROR",
            "code": "permission_not_ready",
            "message": f"Permission status is '{permission_status}'. Human review of authorization and agreement is required before processing.",
            "field": "permission_status",
        })

    details["permission_status"] = permission_status
    details["processing_permitted"] = processing_permitted

    # Step 3: Run data quality validation (only if manifest is valid)
    data_quality_report = None
    data_quality_passed = True

    if manifest_valid:
        data_quality_report = run_full_validation(df_rows, manifest)
        data_quality_passed = data_quality_report.passed

        details["data_quality"] = {
            "passed": data_quality_passed,
            "total_issues": len(data_quality_report.issues),
            "error_count": sum(1 for i in data_quality_report.issues if i.severity == "ERROR"),
            "warning_count": sum(1 for i in data_quality_report.issues if i.severity == "WARNING"),
            "aggregate_counts": data_quality_report.aggregate_counts,
        }

        for issue in data_quality_report.issues:
            issues.append({
                "stage": "data_quality",
                "severity": issue.severity,
                "code": issue.code,
                "message": issue.message,
                "field": issue.field,
                "details": issue.details,
            })
    else:
        details["data_quality"] = {
            "skipped": True,
            "reason": "Manifest validation failed",
        }

    # Step 4: Run temporal audit (only if manifest is valid)
    temporal_report = None
    temporal_audit_passed = True

    if manifest_valid:
        temporal_report = run_full_temporal_audit(df_rows, manifest)
        temporal_audit_passed = temporal_report.passed

        details["temporal_audit"] = {
            "passed": temporal_audit_passed,
            "total_issues": len(temporal_report.issues),
            "error_count": sum(1 for i in temporal_report.issues if i.severity == "ERROR"),
            "warning_count": sum(1 for i in temporal_report.issues if i.severity == "WARNING"),
            "aggregate_counts": temporal_report.aggregate_counts,
        }

        for issue in temporal_report.issues:
            issues.append({
                "stage": "temporal_audit",
                "severity": issue.severity,
                "code": issue.code,
                "message": issue.message,
                "field": issue.field,
                "details": issue.details,
            })
    else:
        details["temporal_audit"] = {
            "skipped": True,
            "reason": "Manifest validation failed",
        }

    # Step 5: Determine final qualification status
    error_count = sum(1 for i in issues if i["severity"] == "ERROR")
    warning_count = sum(1 for i in issues if i["severity"] == "WARNING")

    if error_count > 0:
        # Critical requirements failed
        status = "BLOCKED"
        message = f"Dataset is BLOCKED: {error_count} critical error(s) found. Processing cannot proceed."
    elif warning_count > 0 or not processing_permitted:
        # Material questions remain
        status = "REVIEW_REQUIRED"
        if not processing_permitted:
            message = f"Dataset requires REVIEW: Permission status is '{permission_status}' and requires human review of authorization."
        else:
            message = f"Dataset requires REVIEW: {warning_count} warning(s) require human review before proceeding."
    else:
        # All checks passed
        status = "QUALIFIED_FOR_RESEARCH"
        message = "Dataset is QUALIFIED_FOR_RESEARCH: All documented checks passed for the specified research purpose."

    return QualificationResult(
        status=status,
        message=message,
        manifest_valid=manifest_valid,
        data_quality_passed=data_quality_passed,
        temporal_audit_passed=temporal_audit_passed,
        permission_status=permission_status,
        issues=issues,
        details=details,
    )


def check_qualification_criteria(
    manifest: dict[str, Any],
) -> dict[str, bool]:
    """Check individual qualification criteria from the manifest.

    This is a lightweight check of whether the manifest documents
    the required criteria. It does NOT validate the actual data.

    Args:
        manifest: Dataset manifest from data_intake.contract.

    Returns:
        Dictionary mapping criterion names to boolean status.
    """
    criteria = {}

    # Provenance and source identity
    criteria["provenance_documented"] = bool(
        manifest.get("source_organization") and
        manifest.get("provenance_reference")
    )

    # Documented authorization and permitted use
    criteria["authorization_documented"] = bool(
        manifest.get("permission_status") and
        manifest.get("permission_status") != "pending_review"
    )

    # Suitable borrower-level records
    criteria["borrower_id_documented"] = bool(manifest.get("borrower_id_field"))

    # Point-in-time feature availability
    criteria["prediction_timestamp_documented"] = bool(
        manifest.get("prediction_timestamp_definition", {}).get("field_name")
    )

    # Meaningful repayment outcome
    criteria["outcome_documented"] = bool(
        manifest.get("outcome_definition", {}).get("target_field") and
        manifest.get("outcome_definition", {}).get("target_event")
    )

    # Defensible prediction horizon
    criteria["horizon_documented"] = bool(
        manifest.get("outcome_definition", {}).get("horizon_months")
    )

    # Explicit treatment of censoring
    criteria["censoring_documented"] = bool(
        manifest.get("outcome_definition", {}).get("censoring_field")
    )

    # Feature definitions with timestamps
    field_definitions = manifest.get("field_definitions", [])
    criteria["features_with_timestamps"] = all(
        fd.get("observation_timestamp") for fd in field_definitions
    ) if field_definitions else False

    # Schema version
    criteria["schema_version_documented"] = bool(manifest.get("schema_version"))

    return criteria
