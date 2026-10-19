"""Dataset manifest and metadata validation for research datasets.

This module validates that a proposed research dataset has the required
metadata before any processing occurs. It does NOT validate legal permission—
that requires documented human review of the actual authorization and agreement.

All validation fails closed: if required metadata is absent, contradictory, or invalid,
the dataset is rejected for processing.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
import re


class ContractError(ValueError):
    """Raised when dataset manifest or metadata is invalid."""
    def __init__(self, code: str, message: str, field: str | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field


DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_strict_date(val: Any, field_name: str | None = None) -> date:
    """Parse a date string in strict YYYY-MM-DD format."""
    if not isinstance(val, str) or not DATE_REGEX.match(val):
        raise ContractError("invalid_date", "Dates must use exact YYYY-MM-DD format.", field_name)
    try:
        return datetime.strptime(val, "%Y-%m-%d").date()
    except ValueError:
        raise ContractError("invalid_date", "Dates must use exact YYYY-MM-DD format.", field_name)


def _validate_permission_status(status: Any, field_name: str) -> str:
    """Validate that permission status is one of the allowed values."""
    allowed_statuses = {
        "pending_review",
        "under_review",
        "authorized_documented",
        "authorized_pending_legal_signoff",
        "rejected",
        "revoked",
    }
    if not isinstance(status, str):
        raise ContractError("invalid_type", f"{field_name} must be a string.", field_name)
    if status not in allowed_statuses:
        raise ContractError(
            "invalid_permission_status",
            f"{field_name} must be one of: {', '.join(sorted(allowed_statuses))}.",
            field_name
        )
    return status


def _validate_sensitive_field_names(field_names: list[str]) -> list[str]:
    """Check for potentially sensitive field names that should not be in the modeling view."""
    sensitive_patterns = [
        "pan", "aadhaar", "passport", "voter", "mobile", "phone", "email",
        "account_number", "account_no", "acc_no", "ifsc", "upi_id",
        "password", "credential", "secret", "token", "api_key",
    ]
    warnings = []
    for field_name in field_names:
        field_lower = field_name.lower()
        for pattern in sensitive_patterns:
            if pattern in field_lower:
                warnings.append(f"Field '{field_name}' may contain sensitive information ({pattern}).")
                break
    return warnings


def validate_dataset_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate a dataset manifest before processing.

    Args:
        manifest: Dictionary containing dataset metadata.

    Returns:
        The validated manifest (unchanged if valid).

    Raises:
        ContractError: If required metadata is missing, invalid, or contradictory.
    """
    if not isinstance(manifest, dict):
        raise ContractError("invalid_type", "Dataset manifest must be an object.")

    # Required top-level fields
    required_fields = {
        "dataset_id",
        "dataset_version",
        "schema_version",
        "source_organization",
        "provenance_reference",
        "permission_status",
        "prediction_timestamp_definition",
        "observation_window_definition",
        "outcome_definition",
        "field_definitions",
    }
    missing = sorted(required_fields - set(manifest.keys()))
    if missing:
        raise ContractError(
            "missing_field",
            f"Required manifest fields are missing: {', '.join(missing)}.",
            missing[0]
        )

    # Validate dataset_id
    dataset_id = manifest["dataset_id"]
    if not isinstance(dataset_id, str) or not dataset_id.strip():
        raise ContractError("invalid_dataset_id", "dataset_id must be a non-empty string.", "dataset_id")

    # Validate dataset_version
    dataset_version = manifest["dataset_version"]
    if not isinstance(dataset_version, str) or not dataset_version.strip():
        raise ContractError("invalid_dataset_version", "dataset_version must be a non-empty string.", "dataset_version")

    # Validate schema_version
    schema_version = manifest["schema_version"]
    if not isinstance(schema_version, str) or not schema_version.strip():
        raise ContractError("invalid_schema_version", "schema_version must be a non-empty string.", "schema_version")

    # Validate source_organization
    source_organization = manifest["source_organization"]
    if not isinstance(source_organization, str) or not source_organization.strip():
        raise ContractError("invalid_source_organization", "source_organization must be a non-empty string.", "source_organization")

    # Validate provenance_reference
    provenance_reference = manifest["provenance_reference"]
    if not isinstance(provenance_reference, str) or not provenance_reference.strip():
        raise ContractError("invalid_provenance_reference", "provenance_reference must be a non-empty string.", "provenance_reference")

    # Validate permission_status (NOTE: This is metadata only, NOT proof of legal permission)
    permission_status = _validate_permission_status(manifest["permission_status"], "permission_status")

    # Validate prediction_timestamp_definition
    prediction_def = manifest["prediction_timestamp_definition"]
    if not isinstance(prediction_def, dict):
        raise ContractError("invalid_type", "prediction_timestamp_definition must be an object.", "prediction_timestamp_definition")
    if "field_name" not in prediction_def:
        raise ContractError("missing_field", "prediction_timestamp_definition must specify field_name.", "prediction_timestamp_definition.field_name")
    if not isinstance(prediction_def["field_name"], str) or not prediction_def["field_name"].strip():
        raise ContractError("invalid_field_name", "prediction_timestamp_definition.field_name must be a non-empty string.", "prediction_timestamp_definition.field_name")

    # Validate observation_window_definition
    obs_window = manifest["observation_window_definition"]
    if not isinstance(obs_window, dict):
        raise ContractError("invalid_type", "observation_window_definition must be an object.", "observation_window_definition")
    if "start_field" not in obs_window or "end_field" not in obs_window:
        raise ContractError("missing_field", "observation_window_definition must specify start_field and end_field.", "observation_window_definition")
    if not isinstance(obs_window["start_field"], str) or not obs_window["start_field"].strip():
        raise ContractError("invalid_field_name", "observation_window_definition.start_field must be a non-empty string.", "observation_window_definition.start_field")
    if not isinstance(obs_window["end_field"], str) or not obs_window["end_field"].strip():
        raise ContractError("invalid_field_name", "observation_window_definition.end_field must be a non-empty string.", "observation_window_definition.end_field")

    # Validate outcome_definition
    outcome_def = manifest["outcome_definition"]
    if not isinstance(outcome_def, dict):
        raise ContractError("invalid_type", "outcome_definition must be an object.", "outcome_definition")
    required_outcome_fields = {"target_field", "target_event", "horizon_months"}
    missing_outcome = sorted(required_outcome_fields - set(outcome_def.keys()))
    if missing_outcome:
        raise ContractError(
            "missing_field",
            f"outcome_definition must specify: {', '.join(missing_outcome)}.",
            f"outcome_definition.{missing_outcome[0]}"
        )
    if not isinstance(outcome_def["target_field"], str) or not outcome_def["target_field"].strip():
        raise ContractError("invalid_field_name", "outcome_definition.target_field must be a non-empty string.", "outcome_definition.target_field")
    if not isinstance(outcome_def["target_event"], str) or not outcome_def["target_event"].strip():
        raise ContractError("invalid_target_event", "outcome_definition.target_event must be a non-empty string.", "outcome_definition.target_event")
    if not isinstance(outcome_def["horizon_months"], int) or outcome_def["horizon_months"] <= 0:
        raise ContractError("invalid_horizon", "outcome_definition.horizon_months must be a positive integer.", "outcome_definition.horizon_months")

    # Validate field_definitions
    field_definitions = manifest["field_definitions"]
    if not isinstance(field_definitions, list) or len(field_definitions) == 0:
        raise ContractError("invalid_field_definitions", "field_definitions must be a non-empty array.", "field_definitions")

    field_names = []
    for idx, field_def in enumerate(field_definitions):
        field_path = f"field_definitions[{idx}]"
        if not isinstance(field_def, dict):
            raise ContractError("invalid_type", f"{field_path} must be an object.", field_path)

        required_field_def = {"field_name", "data_type", "observation_timestamp"}
        missing_field_def = sorted(required_field_def - set(field_def.keys()))
        if missing_field_def:
            raise ContractError(
                "missing_field",
                f"{field_path} must specify: {', '.join(missing_field_def)}.",
                f"{field_path}.{missing_field_def[0]}"
            )

        field_name = field_def["field_name"]
        if not isinstance(field_name, str) or not field_name.strip():
            raise ContractError("invalid_field_name", f"{field_path}.field_name must be a non-empty string.", f"{field_path}.field_name")
        field_names.append(field_name)

        data_type = field_def["data_type"]
        allowed_types = {"numeric", "categorical", "date", "boolean", "array"}
        if not isinstance(data_type, str) or data_type not in allowed_types:
            raise ContractError(
                "invalid_data_type",
                f"{field_path}.data_type must be one of: {', '.join(sorted(allowed_types))}.",
                f"{field_path}.data_type"
            )

        obs_timestamp = field_def["observation_timestamp"]
        if not isinstance(obs_timestamp, str) or not obs_timestamp.strip():
            raise ContractError("invalid_observation_timestamp", f"{field_path}.observation_timestamp must be a non-empty string.", f"{field_path}.observation_timestamp")

    # Check for sensitive field names (WARNING only, not ERROR)
    sensitive_warnings = _validate_sensitive_field_names(field_names)
    if sensitive_warnings:
        # Log warnings but do not fail - this is for human review
        pass  # In a real implementation, these would be logged

    # Optional fields with validation if present
    if "borrower_id_field" in manifest:
        borrower_id_field = manifest["borrower_id_field"]
        if not isinstance(borrower_id_field, str) or not borrower_id_field.strip():
            raise ContractError("invalid_borrower_id_field", "borrower_id_field must be a non-empty string.", "borrower_id_field")

    if "extraction_date" in manifest:
        extraction_date = manifest["extraction_date"]
        _parse_strict_date(extraction_date, "extraction_date")

    if "retention_date" in manifest:
        retention_date = manifest["retention_date"]
        _parse_strict_date(retention_date, "retention_date")

    return manifest


def check_processing_permission(permission_status: str) -> bool:
    """Check if the permission status allows processing.

    IMPORTANT: This is a metadata check only. It does NOT constitute
    legal proof of permission. Human review of the actual authorization
    and agreement is required before any real-data processing.

    Args:
        permission_status: The permission_status value from the manifest.

    Returns:
        True if the status indicates processing may proceed subject to human review.
        False if processing is blocked.
    """
    processable_statuses = {
        "authorized_documented",
        "authorized_pending_legal_signoff",
    }
    return permission_status in processable_statuses
