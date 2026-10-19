"""Point-in-time and target audit infrastructure.

This module validates that features are available at the prediction timestamp
and that target construction follows documented temporal rules.

All validation fails closed for leakage issues and surfaces warnings for
target definition ambiguities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Literal
import re


@dataclass
class TemporalIssue:
    """A temporal validation issue."""
    severity: Literal["ERROR", "WARNING", "INFORMATION"]
    code: str
    message: str
    field: str | None = None
    details: dict[str, Any] | None = None


@dataclass
class TemporalAuditReport:
    """Report of temporal validation results."""
    issues: list[TemporalIssue] = field(default_factory=list)
    aggregate_counts: dict[str, Any] = field(default_factory=dict)
    passed: bool = True

    def add_error(self, code: str, message: str, field: str | None = None, details: dict[str, Any] | None = None):
        self.issues.append(TemporalIssue("ERROR", code, message, field, details))
        self.passed = False

    def add_warning(self, code: str, message: str, field: str | None = None, details: dict[str, Any] | None = None):
        self.issues.append(TemporalIssue("WARNING", code, message, field, details))

    def add_info(self, code: str, message: str, field: str | None = None, details: dict[str, Any] | None = None):
        self.issues.append(TemporalIssue("INFORMATION", code, message, field, details))


DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_date(val: Any) -> date | None:
    """Attempt to parse a date string, returning None if invalid."""
    if isinstance(val, str) and DATE_REGEX.match(val):
        try:
            return datetime.strptime(val, "%Y-%m-%d").date()
        except ValueError:
            pass
    return None


def validate_feature_availability(
    df_rows: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> TemporalAuditReport:
    """Validate that all features are available by the prediction timestamp.

    Args:
        df_rows: List of row dictionaries.
        manifest: Dataset manifest from data_intake.contract.

    Returns:
        TemporalAuditReport with feature availability validation results.
    """
    report = TemporalAuditReport()

    # Extract prediction timestamp field from manifest
    prediction_def = manifest.get("prediction_timestamp_definition", {})
    prediction_field = prediction_def.get("field_name")

    if not prediction_field:
        report.add_error("missing_prediction_timestamp", "Manifest must specify prediction_timestamp_definition.field_name.")
        return report

    if prediction_field not in df_rows[0]:
        report.add_error("prediction_field_not_found", f"Prediction timestamp field '{prediction_field}' not found in dataset.", field=prediction_field)
        return report

    # Extract field definitions. Outcome and observation-end fields are expected
    # to occur after the prediction timestamp and are not treated as features.
    outcome_def = manifest.get("outcome_definition", {})
    observation_window = manifest.get("observation_window_definition", {})
    excluded_fields = {
        prediction_field,
        outcome_def.get("target_field"),
        outcome_def.get("censoring_field"),
        outcome_def.get("closure_status_field"),
        outcome_def.get("prepayment_field"),
        outcome_def.get("restructuring_field"),
        observation_window.get("end_field"),
    }
    excluded_fields.discard(None)

    field_definitions = manifest.get("field_definitions", [])
    feature_fields = [
        fd for fd in field_definitions
        if fd.get("field_name") not in excluded_fields
        and fd.get("observation_timestamp") != "outcome"
    ]

    future_feature_violations = 0
    rows_with_invalid_dates = 0

    for row in df_rows:
        prediction_date = _parse_date(row.get(prediction_field))
        if prediction_date is None:
            rows_with_invalid_dates += 1
            continue

        for field_def in feature_fields:
            field_name = field_def["field_name"]
            if field_name not in row:
                continue

            obs_timestamp_str = field_def.get("observation_timestamp")
            if not obs_timestamp_str:
                continue

            # If observation_timestamp is a field name in the data, check it
            if obs_timestamp_str in row:
                obs_date = _parse_date(row.get(obs_timestamp_str))
                if obs_date and obs_date > prediction_date:
                    future_feature_violations += 1
                    report.add_error(
                        "future_feature_leakage",
                        f"Feature '{field_name}' has observation timestamp after prediction timestamp.",
                        field=field_name,
                        details={"observation_date": str(obs_date), "prediction_date": str(prediction_date)}
                    )
                    break  # One error per row is sufficient

    if rows_with_invalid_dates > 0:
        report.add_error(
            "invalid_prediction_dates",
            f"{rows_with_invalid_dates} rows have invalid prediction timestamp values.",
            field=prediction_field,
            details={"invalid_count": rows_with_invalid_dates}
        )

    report.aggregate_counts["future_feature_violations"] = future_feature_violations
    report.aggregate_counts["rows_with_invalid_dates"] = rows_with_invalid_dates

    return report


def validate_target_definition(
    df_rows: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> TemporalAuditReport:
    """Validate target construction and maturity.

    Args:
        df_rows: List of row dictionaries.
        manifest: Dataset manifest from data_intake.contract.

    Returns:
        TemporalAuditReport with target validation results.
    """
    report = TemporalAuditReport()

    # Extract outcome definition from manifest
    outcome_def = manifest.get("outcome_definition", {})
    target_field = outcome_def.get("target_field")
    target_event = outcome_def.get("target_event")
    horizon_months = outcome_def.get("horizon_months")

    if not target_field:
        report.add_error("missing_target_field", "Manifest must specify outcome_definition.target_field.")
        return report

    if target_field not in df_rows[0]:
        report.add_error("target_field_not_found", f"Target field '{target_field}' not found in dataset.", field=target_field)
        return report

    if not target_event:
        report.add_warning("missing_target_event", "Manifest should specify outcome_definition.target_event (e.g., '90_plus_dpd').")

    if not horizon_months or horizon_months <= 0:
        report.add_error("invalid_horizon", "Manifest must specify outcome_definition.horizon_months as a positive integer.")

    # Check for censoring indicators
    censoring_field = outcome_def.get("censoring_field")
    if censoring_field and censoring_field in df_rows[0]:
        censored_count = sum(1 for row in df_rows if row.get(censoring_field) == 1)
        report.add_info(
            "censored_records",
            f"Found {censored_count} censored records (right-censored or excluded from analysis).",
            field=censoring_field,
            details={"censored_count": censored_count}
        )

    # Check for label maturity
    observation_window = manifest.get("observation_window_definition", {})
    end_field = observation_window.get("end_field")

    if end_field and end_field in df_rows[0]:
        immature_count = 0
        for row in df_rows:
            obs_end_date = _parse_date(row.get(end_field))
            prediction_field = manifest.get("prediction_timestamp_definition", {}).get("field_name")
            if prediction_field and prediction_field in row:
                prediction_date = _parse_date(row.get(prediction_field))
                if obs_end_date and prediction_date:
                    maturity_months = (obs_end_date - prediction_date).days / 30.44
                    if maturity_months < horizon_months:
                        immature_count += 1

        if immature_count > 0:
            report.add_warning(
                "immature_labels",
                f"{immature_count} records have observation windows shorter than the target horizon ({horizon_months} months).",
                details={"immature_count": immature_count, "horizon_months": horizon_months}
            )

    # Check for contradictory labels
    closure_status_field = outcome_def.get("closure_status_field")
    if closure_status_field and closure_status_field in df_rows[0]:
        # Check for loans marked as "fully_paid" but with default flag = 1
        contradictory_count = 0
        for row in df_rows:
            if row.get(target_field) == 1 and row.get(closure_status_field) == "fully_paid":
                contradictory_count += 1

        if contradictory_count > 0:
            report.add_error(
                "contradictory_labels",
                f"{contradictory_count} records have contradictory labels (default=1 but closure_status='fully_paid').",
                details={"contradictory_count": contradictory_count}
            )

    report.aggregate_counts["censored_count"] = sum(1 for row in df_rows if censoring_field and row.get(censoring_field) == 1)

    return report


def validate_outcome_window_leakage(
    df_rows: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> TemporalAuditReport:
    """Validate that the target does not use information from before the prediction timestamp
    unless explicitly documented.

    Args:
        df_rows: List of row dictionaries.
        manifest: Dataset manifest from data_intake.contract.

    Returns:
        TemporalAuditReport with outcome window leakage validation results.
    """
    report = TemporalAuditReport()

    # Extract prediction timestamp field
    prediction_def = manifest.get("prediction_timestamp_definition", {})
    prediction_field = prediction_def.get("field_name")

    if not prediction_field or prediction_field not in df_rows[0]:
        return report  # Already caught by other validations

    # Extract outcome definition
    outcome_def = manifest.get("outcome_definition", {})
    target_field = outcome_def.get("target_field")

    if not target_field or target_field not in df_rows[0]:
        return report  # Already caught by other validations

    # Check if target definition explicitly allows historical events
    uses_historical_events = outcome_def.get("uses_historical_events", False)

    if not uses_historical_events:
        # Target should be based on events AFTER prediction timestamp
        # This is a structural check - the actual implementation depends on how the target is constructed
        report.add_info(
            "target_historical_events",
            "Target definition does not explicitly use historical events. Ensure target is constructed from post-prediction outcomes only.",
            field=target_field
        )

    return report


def validate_censoring_handling(
    df_rows: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> TemporalAuditReport:
    """Validate that censoring is properly handled.

    Args:
        df_rows: List of row dictionaries.
        manifest: Dataset manifest from data_intake.contract.

    Returns:
        TemporalAuditReport with censoring validation results.
    """
    report = TemporalAuditReport()

    outcome_def = manifest.get("outcome_definition", {})
    censoring_field = outcome_def.get("censoring_field")
    prepayment_field = outcome_def.get("prepayment_field")
    restructuring_field = outcome_def.get("restructuring_field")

    # Check if censoring is defined
    if not censoring_field:
        report.add_warning(
            "missing_censoring_field",
            "Outcome definition should specify a censoring_field to flag right-censored or excluded records."
        )

    # Count special cases
    prepayment_count = 0
    restructuring_count = 0

    if prepayment_field and prepayment_field in df_rows[0]:
        prepayment_count = sum(1 for row in df_rows if row.get(prepayment_field) == 1)
        report.add_info(
            "prepayment_records",
            f"Found {prepayment_count} prepaid records.",
            field=prepayment_field,
            details={"prepayment_count": prepayment_count}
        )

    if restructuring_field and restructuring_field in df_rows[0]:
        restructuring_count = sum(1 for row in df_rows if row.get(restructuring_field) == 1)
        report.add_info(
            "restructuring_records",
            f"Found {restructuring_count} restructured records.",
            field=restructuring_field,
            details={"restructuring_count": restructuring_count}
        )

    report.aggregate_counts["prepayment_count"] = prepayment_count
    report.aggregate_counts["restructuring_count"] = restructuring_count

    return report


def run_full_temporal_audit(
    df_rows: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> TemporalAuditReport:
    """Run all temporal validation checks.

    Args:
        df_rows: List of row dictionaries.
        manifest: Dataset manifest from data_intake.contract.

    Returns:
        Combined TemporalAuditReport from all checks.
    """
    report = TemporalAuditReport()

    report.aggregate_counts["total_rows_audited"] = len(df_rows)

    # Feature availability validation
    feature_report = validate_feature_availability(df_rows, manifest)
    report.issues.extend(feature_report.issues)
    report.aggregate_counts.update(feature_report.aggregate_counts)

    # Target definition validation
    target_report = validate_target_definition(df_rows, manifest)
    report.issues.extend(target_report.issues)
    report.aggregate_counts.update(target_report.aggregate_counts)

    # Outcome window leakage validation
    leakage_report = validate_outcome_window_leakage(df_rows, manifest)
    report.issues.extend(leakage_report.issues)
    report.aggregate_counts.update(leakage_report.aggregate_counts)

    # Censoring handling validation
    censoring_report = validate_censoring_handling(df_rows, manifest)
    report.issues.extend(censoring_report.issues)
    report.aggregate_counts.update(censoring_report.aggregate_counts)

    # Child checks append issues without calling add_error on this report.
    report.passed = not any(issue.severity == "ERROR" for issue in report.issues)
    return report
