# CreditAI Phase 5 — Target and Temporal Validation

**Date:** October 12, 2026
**Purpose:** Specify point-in-time and target validation infrastructure

---

## Overview

This document specifies the temporal validation infrastructure implemented in Phase 5. The infrastructure ensures that features are available at the prediction timestamp and that target construction follows documented temporal rules.

---

## Temporal Definitions

### Observation Window
The period during which features are observed for each borrower.

- **Start field:** `observation_window_definition.start_field` (e.g., `application_date`)
- **End field:** `observation_window_definition.end_field` (e.g., `decision_date`)
- **Requirement:** All features must be observable within this window.

### Prediction Timestamp
The point in time at which the prediction is made.

- **Field:** `prediction_timestamp_definition.field_name` (e.g., `decision_date`)
- **Requirement:** All features must be available by this timestamp.

### Outcome Window
The period during which the target event is observed.

- **Start:** Prediction timestamp
- **End:** `prediction_timestamp + horizon_months`
- **Requirement:** Target must be based on events in this window.

### Target Event
The event that defines the positive class.

- **Field:** `outcome_definition.target_field` (e.g., `default_flag`)
- **Event:** `outcome_definition.target_event` (e.g., "90_plus_dpd")
- **Horizon:** `outcome_definition.horizon_months` (e.g., 12 months)

### Label Maturity Date
The date by which the target label is fully observable.

- **Calculation:** `prediction_timestamp + horizon_months`
- **Requirement:** Records with observation windows shorter than this have immature labels.

---

## Censoring and Competing Outcomes

### Censoring
Records that do not reach a terminal outcome within the observation window.

- **Field:** `outcome_definition.censoring_field`
- **Types:**
  - **Right-censoring:** Loan still active at observation end
  - **Prepayment:** Loan paid off early before horizon
  - **Restructuring:** Loan terms modified before horizon

### Competing Outcomes
Outcomes that preclude the target event.

- **Prepayment:** Loan paid off before default can occur
- **Settlement:** Debt settled for less than full amount
- **Restructuring:** Loan terms modified

### Treatment in Analysis

Censored records must be explicitly flagged and handled:

- **Exclusion:** Remove censored records from analysis (may introduce bias)
- **Survival analysis:** Use time-to-event methods (appropriate for censoring)
- **Separate analysis:** Analyze censored and uncensored separately

The chosen treatment must be documented in the manifest.

---

## Validation Checks

### Feature Availability Validation

#### Check: Future Feature Leakage
- **Severity:** ERROR
- **Code:** `future_feature_leakage`
- **Description:** Feature observation timestamp is after the prediction timestamp.
- **Implication:** Using future information to predict past outcomes (leakage).
- **Action:** Exclude the feature or correct the observation timestamp.

#### Check: Invalid Prediction Dates
- **Severity:** ERROR
- **Code:** `invalid_prediction_dates`
- **Description:** Prediction timestamp values are invalid or cannot be parsed.
- **Action:** Review and correct prediction timestamp values.

#### Check: Missing Prediction Timestamp
- **Severity:** ERROR
- **Code:** `missing_prediction_timestamp`
- **Description:** Manifest does not specify prediction_timestamp_definition.field_name.
- **Action:** Update the manifest to specify the prediction timestamp field.

---

### Target Definition Validation

#### Check: Target Field Not Found
- **Severity:** ERROR
- **Code:** `target_field_not_found`
- **Description:** Target field specified in manifest is not found in the dataset.
- **Action:** Update the manifest or request the target field from the data provider.

#### Check: Missing Target Event
- **Severity:** WARNING
- **Code:** `missing_target_event`
- **Description:** Manifest does not specify outcome_definition.target_event.
- **Action:** Update the manifest to specify the target event (e.g., "90_plus_dpd").

#### Check: Invalid Horizon
- **Severity:** ERROR
- **Code:** `invalid_horizon`
- **Description:** Manifest does not specify a valid positive integer for outcome_definition.horizon_months.
- **Action:** Update the manifest to specify the target horizon in months.

#### Check: Immature Labels
- **Severity:** WARNING
- **Code:** `immature_labels`
- **Description:** Observation windows are shorter than the target horizon, leading to immature labels.
- **Implication:** Some records may not have had time to reach the target event.
- **Action:** Exclude immature records or adjust the target horizon.

#### Check: Contradictory Labels
- **Severity:** ERROR
- **Code:** `contradictory_labels`
- **Description:** Records have contradictory labels (e.g., default=1 but closure_status="fully_paid").
- **Action:** Review with the data provider to resolve contradictions.

---

### Censoring Validation

#### Check: Missing Censoring Field
- **Severity:** WARNING
- **Code:** `missing_censoring_field`
- **Description:** Outcome definition does not specify a censoring_field.
- **Action:** Update the manifest to specify a censoring field to flag right-censored or excluded records.

#### Check: Censored Records
- **Severity:** INFORMATION
- **Code:** `censored_records`
- **Description:** Count of records flagged as censored.
- **Action:** Review censoring treatment and confirm it is appropriate.

#### Check: Prepayment Records
- **Severity:** INFORMATION
- **Code:** `prepayment_records`
- **Description:** Count of records flagged as prepaid.
- **Action:** Review prepayment treatment and confirm it is appropriate.

#### Check: Restructuring Records
- **Severity:** INFORMATION
- **Code:** `restructuring_records`
- **Description:** Count of records flagged as restructured.
- **Action:** Review restructuring treatment and confirm it is appropriate.

---

### Outcome Window Leakage Validation

#### Check: Target Historical Events
- **Severity:** INFORMATION
- **Code:** `target_historical_events`
- **Description:** Target definition does not explicitly use historical events.
- **Implication:** Ensure target is constructed from post-prediction outcomes only.
- **Action:** Confirm target construction logic excludes pre-prediction events.

---

## Target Construction Rules

### Rule 1: Feature Availability
A feature must not be included if it was not available by the prediction timestamp.

**Implementation:**
- Check `observation_timestamp` for each feature
- Reject features with `observation_timestamp > prediction_timestamp`

### Rule 2: Target Temporal Boundary
A target must not use information from before the prediction timestamp unless the documented target definition explicitly requires historical events.

**Implementation:**
- Check `outcome_definition.uses_historical_events` flag
- If False, target must be based on post-prediction events only
- If True, historical events are explicitly documented and justified

### Rule 3: No Default Horizon
Do not hard-code a default horizon without justification.

**Implementation:**
- Require `outcome_definition.horizon_months` in manifest
- Reject manifests without explicit horizon
- Make target construction configurable

### Rule 4: Target Definition Explicitity
Do not assume that a loan marked "Fully Paid" is equivalent to every possible default target definition.

**Implementation:**
- Require explicit `outcome_definition.target_event` in manifest
- Reject manifests without explicit target event
- Document the relationship between closure_status and target

---

## Configurable Target Construction

The infrastructure supports configurable target construction:

### Target Types
- **Fixed-horizon default:** Default within N months of prediction
- **Closed-loan outcome:** Did the loan reach a terminal bad state at any observed point?
- **Time-to-default:** Time until default event (survival analysis)
- **Multi-state:** Multiple competing outcomes (default, prepayment, current)

### Horizon Specification
- **Fixed horizon:** All loans evaluated over the same time window (e.g., 12 months)
- **Loan-specific horizon:** Horizon varies by loan tenure (e.g., full loan term)
- **Maturity-based:** Horizon ends at loan maturity date

### Censoring Treatment
- **Exclude censored:** Remove censored records from analysis
- **Survival analysis:** Use time-to-event methods
- **Separate analysis:** Analyze censored and uncensored separately

The chosen approach must be documented in the manifest.

---

## Testing Requirements

The temporal validation infrastructure includes tests for:

1. **Future-feature leakage:** Features with observation timestamps after prediction timestamp
2. **Outcome-window leakage:** Targets using pre-prediction information without explicit documentation
3. **Immature labels:** Records with observation windows shorter than target horizon
4. **Censored records:** Proper flagging and handling of censored records
5. **Contradictory labels:** Detection of label inconsistencies
6. **Missing timestamps:** Detection of missing or invalid timestamp fields

All tests use synthetic fixtures—no real borrower data.

---

## Aggregate Reporting

Temporal validation produces aggregate counts:

- Future feature violations
- Rows with invalid dates
- Censored record counts
- Prepayment counts
- Restructuring counts
- Immature label counts
- Contradictory label counts

No raw borrower records are included in reports.

---

## Summary

The target and temporal validation infrastructure provides:

1. **Explicit temporal definitions:** Observation window, prediction timestamp, outcome window, target event
2. **Feature availability checks:** Ensures no future feature leakage
3. **Target definition validation:** Ensures targets are properly defined and documented
4. **Censoring handling:** Explicit treatment of censored, prepaid, and restructured records
5. **Configurable construction:** Support for multiple target types and horizons
6. **Comprehensive testing:** Tests for leakage, immature labels, and contradictions
7. **Aggregate reporting:** No raw records in output

This infrastructure ensures that temporal integrity is maintained throughout the analysis pipeline.

---

*End of Phase 5 Target and Temporal Validation*
