# CreditAI Phase 5 — Data Quality Specification

**Date:** October 12, 2026
**Purpose:** Specify data quality validation checks for research datasets

---

## Overview

This document specifies the data quality validation checks implemented in Phase 5. These checks are designed to surface data quality issues before any model development occurs, with severity levels (ERROR, WARNING, INFORMATION) to guide action.

All checks use aggregate statistics only—no raw borrower records are printed or logged.

---

## Validation Severity Levels

### ERROR
Dataset must not proceed. Critical requirements are not met.

### WARNING
Requires human review. Material questions or potential issues exist.

### INFORMATION
Descriptive diagnostic. Provides context about the dataset.

---

## Schema Validation

### Check: Missing Required Columns
- **Severity:** ERROR
- **Code:** `missing_required_columns`
- **Description:** Required columns specified in the manifest are absent from the dataset.
- **Action:** Request the missing columns from the data provider or update the manifest.

### Check: Unexpected Columns
- **Severity:** WARNING
- **Code:** `unexpected_columns`
- **Description:** Columns not in the allowed set are present in the dataset.
- **Action:** Review with the data provider to confirm these columns are intentional.

---

## Data Type Validation

### Check: Invalid Data Types
- **Severity:** WARNING
- **Code:** `invalid_data_type`
- **Description:** Column values do not match the expected data type (numeric, categorical, date, boolean).
- **Action:** Review type mismatches and confirm whether they are data quality issues or manifest errors.

---

## Duplicate Validation

### Check: Duplicate IDs
- **Severity:** ERROR
- **Code:** `duplicate_ids`
- **Description:** Duplicate values found in the ID column (e.g., borrower_id).
- **Action:** Review with the data provider to confirm whether duplicates are errors or intentional (e.g., repeated applications).

---

## Chronology Validation

### Check: Invalid Dates
- **Severity:** ERROR
- **Code:** `invalid_dates`
- **Description:** Date values cannot be parsed or are in invalid format.
- **Action:** Review date format and correct parsing errors.

### Check: Chronology Violation
- **Severity:** ERROR
- **Code:** `chronology_violation`
- **Description:** Date ordering is invalid (e.g., application_date > decision_date).
- **Action:** Review temporal logic and correct date values.

---

## Monetary Value Validation

### Check: Invalid Monetary Type
- **Severity:** ERROR
- **Code:** `invalid_monetary_type`
- **Description:** Monetary columns contain non-numeric values.
- **Action:** Review and correct non-numeric monetary values.

### Check: Non-Finite Monetary
- **Severity:** ERROR
- **Code:** `non_finite_monetary`
- **Description:** Monetary columns contain NaN or Inf values.
- **Action:** Review and handle non-finite values (imputation or exclusion).

### Check: Negative Monetary
- **Severity:** WARNING
- **Code:** `negative_monetary`
- **Description:** Monetary columns contain negative values, which may be invalid per field definition.
- **Action:** Review with the data provider—negative values may be valid (e.g., refunds) or errors.

---

## Missingness Validation

### Check: Missing in Required Column
- **Severity:** ERROR
- **Code:** `missing_in_required_column`
- **Description:** Required columns have missing values.
- **Action:** Review missingness and confirm whether imputation is appropriate or data should be excluded.

### Check: Excessive Missingness
- **Severity:** WARNING
- **Code:** `excessive_missingness`
- **Description:** Non-required columns have missingness exceeding the threshold (default 50%).
- **Action:** Review whether the column should be excluded or if missingness is expected.

---

## Target Balance Validation

### Check: No Valid Targets
- **Severity:** ERROR
- **Code:** `no_valid_targets`
- **Description:** Target column has no valid values (all missing or invalid).
- **Action:** Review target column definition and data extraction.

### Check: Extreme Imbalance
- **Severity:** WARNING
- **Code:** `extreme_imbalance`
- **Description:** Target prevalence is less than 1%, which may make evaluation challenging.
- **Action:** Consider oversampling, different evaluation metrics, or collecting more positive examples.

---

## Temporal Validation

### Check: Future Feature Leakage
- **Severity:** ERROR
- **Code:** `future_feature_leakage`
- **Description:** Feature observation timestamp is after the prediction timestamp.
- **Action:** Exclude the feature or correct the observation timestamp.

### Check: Invalid Prediction Dates
- **Severity:** ERROR
- **Code:** `invalid_prediction_dates`
- **Description:** Prediction timestamp values are invalid or cannot be parsed.
- **Action:** Review and correct prediction timestamp values.

### Check: Missing Prediction Timestamp
- **Severity:** ERROR
- **Code:** `missing_prediction_timestamp`
- **Description:** Manifest does not specify prediction_timestamp_definition.field_name.
- **Action:** Update the manifest to specify the prediction timestamp field.

### Check: Target Field Not Found
- **Severity:** ERROR
- **Code:** `target_field_not_found`
- **Description:** Target field specified in manifest is not found in the dataset.
- **Action:** Update the manifest or request the target field from the data provider.

### Check: Missing Target Event
- **Severity:** WARNING
- **Code:** `missing_target_event`
- **Description:** Manifest does not specify outcome_definition.target_event.
- **Action:** Update the manifest to specify the target event (e.g., "90_plus_dpd").

### Check: Invalid Horizon
- **Severity:** ERROR
- **Code:** `invalid_horizon`
- **Description:** Manifest does not specify a valid positive integer for outcome_definition.horizon_months.
- **Action:** Update the manifest to specify the target horizon in months.

### Check: Immature Labels
- **Severity:** WARNING
- **Code:** `immature_labels`
- **Description:** Observation windows are shorter than the target horizon, leading to immature labels.
- **Action:** Exclude immature records or adjust the target horizon.

### Check: Contradictory Labels
- **Severity:** ERROR
- **Code:** `contradictory_labels`
- **Description:** Records have contradictory labels (e.g., default=1 but closure_status="fully_paid").
- **Action:** Review with the data provider to resolve contradictions.

### Check: Missing Censoring Field
- **Severity:** WARNING
- **Code:** `missing_censoring_field`
- **Description:** Outcome definition does not specify a censoring_field.
- **Action:** Update the manifest to specify a censoring field to flag right-censored or excluded records.

---

## Aggregate Reporting

All validation checks produce aggregate counts and diagnostic summaries:

- Total rows validated
- Total columns
- Missing column counts
- Invalid type counts
- Duplicate counts
- Chronology violation counts
- Monetary validation counts
- Missingness counts
- Target prevalence
- Censored record counts
- Prepayment counts
- Restructuring counts

No raw borrower records are included in reports.

---

## Handling Ambiguous Values

The validation framework interprets values according to documented field semantics:

- **Negative balances:** May be valid (refunds, credits) or invalid depending on field definition
- **Zero amounts:** May be valid (no transaction) or invalid depending on field definition
- **Missing values:** Handled per missing-value conventions in the manifest
- **Repeated borrower IDs:** May be valid (repeated applications) or invalid (duplicates)

Context is provided in validation messages to guide human review.

---

## Non-Reporting of Raw Data

The following are never printed or logged:

- Individual borrower records
- Transaction details
- Counterparty names
- Account numbers
- Identifying information

Only aggregate statistics and diagnostic summaries are reported.

---

## Extending Validation Checks

Additional validation checks can be added by:

1. Creating a new validation function in `src/data_quality/validator.py`
2. Returning a `ValidationReport` with appropriate severity levels
3. Adding the check to `run_full_validation()`
4. Documenting the check in this specification

All checks must follow the aggregate-reporting principle—no raw records in output.

---

## Summary

The data quality specification provides:

1. **Comprehensive checks:** Schema, types, duplicates, chronology, monetary values, missingness, target balance
2. **Severity levels:** ERROR (block), WARNING (review), INFORMATION (context)
3. **Aggregate reporting:** No raw borrower records in output
4. **Contextual guidance:** Actionable messages for each issue
5. **Extensibility:** Framework for adding new checks

These checks ensure that datasets are thoroughly validated before any model development occurs.

---

*End of Phase 5 Data Quality Specification*
