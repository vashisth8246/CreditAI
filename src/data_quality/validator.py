"""Data quality validation for research datasets.

This module performs comprehensive data-quality checks on datasets,
returning structured reports with ERROR, WARNING, and INFORMATION levels.

All checks are designed to fail closed for critical issues and surface
human-reviewable warnings for potential problems.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal
import re


@dataclass
class ValidationIssue:
    """A single validation issue."""
    severity: Literal["ERROR", "WARNING", "INFORMATION"]
    code: str
    message: str
    field: str | None = None
    details: dict[str, Any] | None = None


@dataclass
class ValidationReport:
    """Structured report of data quality validation results."""
    issues: list[ValidationIssue] = field(default_factory=list)
    aggregate_counts: dict[str, Any] = field(default_factory=dict)
    passed: bool = True

    def add_error(self, code: str, message: str, field: str | None = None, details: dict[str, Any] | None = None):
        self.issues.append(ValidationIssue("ERROR", code, message, field, details))
        self.passed = False

    def add_warning(self, code: str, message: str, field: str | None = None, details: dict[str, Any] | None = None):
        self.issues.append(ValidationIssue("WARNING", code, message, field, details))

    def add_info(self, code: str, message: str, field: str | None = None, details: dict[str, Any] | None = None):
        self.issues.append(ValidationIssue("INFORMATION", code, message, field, details))


DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_date(val: Any) -> date | None:
    """Attempt to parse a date string, returning None if invalid."""
    if isinstance(val, str) and DATE_REGEX.match(val):
        try:
            return datetime.strptime(val, "%Y-%m-%d").date()
        except ValueError:
            pass
    return None


def validate_schema(
    df_rows: list[dict[str, Any]],
    required_columns: set[str],
    allowed_columns: set[str] | None = None,
) -> ValidationReport:
    """Validate that the dataset has the expected schema.

    Args:
        df_rows: List of row dictionaries (sample of the dataset).
        required_columns: Set of column names that must be present.
        allowed_columns: Optional set of allowed column names. If None, any columns are allowed.

    Returns:
        ValidationReport with schema validation results.
    """
    report = ValidationReport()

    if not df_rows:
        report.add_error("empty_dataset", "Dataset contains no rows.")
        return report

    # Get actual columns from first row
    actual_columns = set(df_rows[0].keys())

    # Check for missing required columns
    missing = sorted(required_columns - actual_columns)
    if missing:
        report.add_error(
            "missing_required_columns",
            f"Required columns are missing: {', '.join(missing)}.",
            details={"missing_columns": missing}
        )

    # Check for unexpected columns
    if allowed_columns is not None:
        unexpected = sorted(actual_columns - allowed_columns)
        if unexpected:
            report.add_warning(
                "unexpected_columns",
                f"Unexpected columns found: {', '.join(unexpected)}.",
                details={"unexpected_columns": unexpected}
            )

    report.aggregate_counts["total_columns"] = len(actual_columns)
    report.aggregate_counts["required_columns"] = len(required_columns)
    report.aggregate_counts["missing_columns"] = len(missing)
    if allowed_columns is not None:
        report.aggregate_counts["unexpected_columns"] = len(unexpected)

    return report


def validate_data_types(
    df_rows: list[dict[str, Any]],
    type_expectations: dict[str, str],
) -> ValidationReport:
    """Validate that columns have the expected data types.

    Args:
        df_rows: List of row dictionaries.
        type_expectations: Mapping of column name to expected type ("numeric", "categorical", "date", "boolean").

    Returns:
        ValidationReport with data type validation results.
    """
    report = ValidationReport()

    invalid_type_counts = {}

    for col, expected_type in type_expectations.items():
        if col not in df_rows[0]:
            continue  # Already caught by schema validation

        invalid_count = 0
        sample_size = min(100, len(df_rows))

        for row in df_rows[:sample_size]:
            val = row.get(col)
            if val is None:
                continue  # Missing values handled separately

            is_valid = False
            if expected_type == "numeric":
                is_valid = isinstance(val, (int, float)) and not isinstance(val, bool)
            elif expected_type == "categorical":
                is_valid = isinstance(val, str)
            elif expected_type == "date":
                is_valid = _parse_date(val) is not None
            elif expected_type == "boolean":
                is_valid = isinstance(val, bool)

            if not is_valid:
                invalid_count += 1

        if invalid_count > 0:
            invalid_type_counts[col] = invalid_count
            report.add_warning(
                "invalid_data_type",
                f"Column '{col}' has {invalid_count} invalid values for expected type '{expected_type}'.",
                field=col,
                details={"expected_type": expected_type, "invalid_count": invalid_count}
            )

    report.aggregate_counts["invalid_type_columns"] = len(invalid_type_counts)

    return report


def validate_duplicates(
    df_rows: list[dict[str, Any]],
    id_column: str,
) -> ValidationReport:
    """Validate that there are no duplicate IDs.

    Args:
        df_rows: List of row dictionaries.
        id_column: Name of the column containing unique identifiers.

    Returns:
        ValidationReport with duplicate validation results.
    """
    report = ValidationReport()

    if id_column not in df_rows[0]:
        report.add_error("missing_id_column", f"ID column '{id_column}' not found in dataset.", field=id_column)
        return report

    seen_ids = set()
    duplicate_ids = set()

    for row in df_rows:
        row_id = row.get(id_column)
        if row_id is None:
            continue
        if row_id in seen_ids:
            duplicate_ids.add(row_id)
        else:
            seen_ids.add(row_id)

    if duplicate_ids:
        report.add_error(
            "duplicate_ids",
            f"Found {len(duplicate_ids)} duplicate {id_column} values.",
            field=id_column,
            details={"duplicate_count": len(duplicate_ids)}
        )

    report.aggregate_counts["total_unique_ids"] = len(seen_ids)
    report.aggregate_counts["duplicate_ids"] = len(duplicate_ids)

    return report


def validate_chronology(
    df_rows: list[dict[str, Any]],
    date_columns: dict[str, str],
) -> ValidationReport:
    """Validate date fields and chronological ordering.

    Args:
        df_rows: List of row dictionaries.
        date_columns: Mapping of column name to role (e.g., {"application_date": "start", "decision_date": "decision"}).

    Returns:
        ValidationReport with chronology validation results.
    """
    report = ValidationReport()

    invalid_date_counts = {}
    chronology_violations = []

    for row in df_rows:
        parsed_dates = {}
        for col, role in date_columns.items():
            if col not in row:
                continue
            parsed = _parse_date(row[col])
            if parsed is None:
                invalid_date_counts[col] = invalid_date_counts.get(col, 0) + 1
            else:
                parsed_dates[role] = parsed

        # Check chronological ordering if we have multiple dates
        if "start" in parsed_dates and "decision" in parsed_dates:
            if parsed_dates["start"] > parsed_dates["decision"]:
                chronology_violations.append("start > decision")

    for col, count in invalid_date_counts.items():
        report.add_error(
            "invalid_dates",
            f"Column '{col}' has {count} invalid date values.",
            field=col,
            details={"invalid_count": count}
        )

    if chronology_violations:
        report.add_error(
            "chronology_violation",
            f"Found {len(chronology_violations)} rows with invalid chronological ordering.",
            details={"violation_count": len(chronology_violations)}
        )

    report.aggregate_counts["invalid_date_columns"] = len(invalid_date_counts)
    report.aggregate_counts["chronology_violations"] = len(chronology_violations)

    return report


def validate_monetary_values(
    df_rows: list[dict[str, Any]],
    monetary_columns: set[str],
    allow_negative: bool = False,
) -> ValidationReport:
    """Validate monetary fields for validity.

    Args:
        df_rows: List of row dictionaries.
        monetary_columns: Set of column names containing monetary values.
        allow_negative: Whether negative values are allowed.

    Returns:
        ValidationReport with monetary value validation results.
    """
    report = ValidationReport()

    invalid_monetary_counts = {}

    for col in monetary_columns:
        if col not in df_rows[0]:
            continue

        invalid_count = 0
        non_finite_count = 0
        negative_count = 0

        for row in df_rows:
            val = row.get(col)
            if val is None:
                continue

            if not isinstance(val, (int, float)) or isinstance(val, bool):
                invalid_count += 1
            else:
                # Check for non-finite values
                if not (val >= 0 or val <= 0):  # NaN check
                    non_finite_count += 1
                # Check for negative values if not allowed
                elif not allow_negative and val < 0:
                    negative_count += 1

        if invalid_count > 0:
            invalid_monetary_counts[col] = invalid_count
            report.add_error(
                "invalid_monetary_type",
                f"Column '{col}' has {invalid_count} non-numeric values.",
                field=col,
                details={"invalid_count": invalid_count}
            )

        if non_finite_count > 0:
            report.add_error(
                "non_finite_monetary",
                f"Column '{col}' has {non_finite_count} non-finite values (NaN/Inf).",
                field=col,
                details={"non_finite_count": non_finite_count}
            )

        if negative_count > 0 and not allow_negative:
            report.add_warning(
                "negative_monetary",
                f"Column '{col}' has {negative_count} negative values (negative values not allowed per field definition).",
                field=col,
                details={"negative_count": negative_count}
            )

    report.aggregate_counts["invalid_monetary_columns"] = len(invalid_monetary_counts)

    return report


def validate_missingness(
    df_rows: list[dict[str, Any]],
    required_columns: set[str] | None = None,
    max_missing_ratio: float = 0.5,
) -> ValidationReport:
    """Validate missing value patterns.

    Args:
        df_rows: List of row dictionaries.
        required_columns: Columns that must not have missing values.
        max_missing_ratio: Maximum allowed ratio of missing values for non-required columns.

    Returns:
        ValidationReport with missingness validation results.
    """
    report = ValidationReport()

    if not df_rows:
        return report

    total_rows = len(df_rows)
    missingness_by_column = {}

    for col in df_rows[0].keys():
        missing_count = sum(1 for row in df_rows if row.get(col) is None)
        missing_ratio = missing_count / total_rows
        missingness_by_column[col] = {"count": missing_count, "ratio": missing_ratio}

        # Check required columns
        if required_columns and col in required_columns and missing_count > 0:
            report.add_error(
                "missing_in_required_column",
                f"Required column '{col}' has {missing_count} missing values ({missing_ratio:.1%}).",
                field=col,
                details={"missing_count": missing_count, "missing_ratio": missing_ratio}
            )

        # Check excessive missingness for non-required columns
        elif (not required_columns or col not in required_columns) and missing_ratio > max_missing_ratio:
            report.add_warning(
                "excessive_missingness",
                f"Column '{col}' has {missing_count} missing values ({missing_ratio:.1%}), exceeding threshold {max_missing_ratio:.1%}.",
                field=col,
                details={"missing_count": missing_count, "missing_ratio": missing_ratio}
            )

    report.aggregate_counts["total_rows"] = total_rows
    report.aggregate_counts["columns_with_missing"] = len([c for c, m in missingness_by_column.items() if m["count"] > 0])

    return report


def validate_target_balance(
    df_rows: list[dict[str, Any]],
    target_column: str,
) -> ValidationReport:
    """Validate target class balance.

    Args:
        df_rows: List of row dictionaries.
        target_column: Name of the target column.

    Returns:
        ValidationReport with target balance validation results.
    """
    report = ValidationReport()

    if target_column not in df_rows[0]:
        report.add_error("missing_target_column", f"Target column '{target_column}' not found.", field=target_column)
        return report

    positive_count = sum(1 for row in df_rows if row.get(target_column) == 1)
    negative_count = sum(1 for row in df_rows if row.get(target_column) == 0)
    total = positive_count + negative_count

    if total == 0:
        report.add_error("no_valid_targets", f"Target column '{target_column}' has no valid values.", field=target_column)
        return report

    prevalence = positive_count / total

    report.add_info(
        "target_prevalence",
        f"Target prevalence: {prevalence:.4f} ({positive_count} positive, {negative_count} negative).",
        field=target_column,
        details={"positive_count": positive_count, "negative_count": negative_count, "prevalence": prevalence}
    )

    # Warn on extreme imbalance
    if prevalence < 0.01:
        report.add_warning(
            "extreme_imbalance",
            f"Target prevalence is {prevalence:.4f} (<1%), which may make evaluation challenging.",
            field=target_column,
            details={"prevalence": prevalence}
        )

    report.aggregate_counts["positive_count"] = positive_count
    report.aggregate_counts["negative_count"] = negative_count
    report.aggregate_counts["prevalence"] = prevalence

    return report


def run_full_validation(
    df_rows: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> ValidationReport:
    """Run all applicable data quality validations.

    Args:
        df_rows: List of row dictionaries (sample or full dataset).
        manifest: Dataset manifest from data_intake.contract.

    Returns:
        Combined ValidationReport from all checks.
    """
    report = ValidationReport()

    # Extract validation parameters from manifest
    field_definitions = manifest.get("field_definitions", [])
    required_columns = {fd["field_name"] for fd in field_definitions if fd.get("required", False)}
    type_expectations = {fd["field_name"]: fd["data_type"] for fd in field_definitions}

    # Identify column types
    monetary_columns = {fd["field_name"] for fd in field_definitions if fd.get("is_monetary", False)}
    date_columns = {}
    for fd in field_definitions:
        if fd["data_type"] == "date":
            role = fd.get("role", "other")
            date_columns[fd["field_name"]] = role

    # Identify target column
    outcome_def = manifest.get("outcome_definition", {})
    target_column = outcome_def.get("target_field")

    # Identify ID column
    id_column = manifest.get("borrower_id_field")

    # Run validations
    report.aggregate_counts["total_rows_validated"] = len(df_rows)

    # Schema validation
    schema_report = validate_schema(df_rows, required_columns)
    report.issues.extend(schema_report.issues)
    report.aggregate_counts.update(schema_report.aggregate_counts)

    # Data type validation
    if type_expectations:
        type_report = validate_data_types(df_rows, type_expectations)
        report.issues.extend(type_report.issues)
        report.aggregate_counts.update(type_report.aggregate_counts)

    # Duplicate validation
    if id_column:
        dup_report = validate_duplicates(df_rows, id_column)
        report.issues.extend(dup_report.issues)
        report.aggregate_counts.update(dup_report.aggregate_counts)

    # Chronology validation
    if date_columns:
        chrono_report = validate_chronology(df_rows, date_columns)
        report.issues.extend(chrono_report.issues)
        report.aggregate_counts.update(chrono_report.aggregate_counts)

    # Monetary validation
    if monetary_columns:
        monetary_report = validate_monetary_values(df_rows, monetary_columns, allow_negative=False)
        report.issues.extend(monetary_report.issues)
        report.aggregate_counts.update(monetary_report.aggregate_counts)

    # Missingness validation
    missing_report = validate_missingness(df_rows, required_columns)
    report.issues.extend(missing_report.issues)
    report.aggregate_counts.update(missing_report.aggregate_counts)

    # Target balance validation
    if target_column:
        target_report = validate_target_balance(df_rows, target_column)
        report.issues.extend(target_report.issues)
        report.aggregate_counts.update(target_report.aggregate_counts)

    # Child checks append issues without calling add_error on this report.
    report.passed = not any(issue.severity == "ERROR" for issue in report.issues)
    return report
