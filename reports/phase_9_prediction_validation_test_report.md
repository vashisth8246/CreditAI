# Phase 9 - Session 4: Prediction Validation Test Report

**Date:** 2026-10-18T16:50:24.900197
**Test Suite:** Reproducible Prediction Test Cases

## Summary

- Total Tests: 15
- Passed: 15
- Failed: 0
- Errors: 0
- Skipped: 0

## Test Results

### TC001: low_delinquency

- **Status:** PASS
- Raw Probability: N/A
- Calibrated Probability: 0.071114
- Predicted Class: Lower predicted default risk
- Risk Category: Low
- SHAP Status: PASS
- SHAP Output Space: log_odds
- SHAP Reconstruction Error: N/A

### TC002: moderate_delinquency

- **Status:** PASS
- Raw Probability: N/A
- Calibrated Probability: 0.419664
- Predicted Class: Lower predicted default risk
- Risk Category: Medium
- SHAP Status: PASS
- SHAP Output Space: log_odds
- SHAP Reconstruction Error: N/A

### TC003: severe_delinquency

- **Status:** PASS
- Raw Probability: N/A
- Calibrated Probability: 0.179628
- Predicted Class: Lower predicted default risk
- Risk Category: Low
- SHAP Status: PASS
- SHAP Output Space: log_odds
- SHAP Reconstruction Error: N/A

### TC004: zero_balances

- **Status:** PASS
- Raw Probability: N/A
- Calibrated Probability: 0.143250
- Predicted Class: Lower predicted default risk
- Risk Category: Low
- SHAP Status: PASS
- SHAP Output Space: log_odds
- SHAP Reconstruction Error: N/A

### TC005: high_limit_good_payment

- **Status:** PASS
- Raw Probability: N/A
- Calibrated Probability: 0.063719
- Predicted Class: Lower predicted default risk
- Risk Category: Low
- SHAP Status: PASS
- SHAP Output Space: log_odds
- SHAP Reconstruction Error: N/A

### TC006: boundary_age_low

- **Status:** PASS
- Raw Probability: N/A
- Calibrated Probability: 0.066473
- Predicted Class: Lower predicted default risk
- Risk Category: Low
- SHAP Status: PASS
- SHAP Output Space: log_odds
- SHAP Reconstruction Error: N/A

### TC007: boundary_age_high

- **Status:** PASS
- Raw Probability: N/A
- Calibrated Probability: 0.066952
- Predicted Class: Lower predicted default risk
- Risk Category: Low
- SHAP Status: PASS
- SHAP Output Space: log_odds
- SHAP Reconstruction Error: N/A

### TC008: boundary_threshold_low

- **Status:** PASS
- Raw Probability: N/A
- Calibrated Probability: 0.071114
- Predicted Class: Lower predicted default risk
- Risk Category: Low
- SHAP Status: PASS
- SHAP Output Space: log_odds
- SHAP Reconstruction Error: N/A

### TC009: boundary_threshold_mid

- **Status:** PASS
- Raw Probability: N/A
- Calibrated Probability: 0.071114
- Predicted Class: Lower predicted default risk
- Risk Category: Low
- SHAP Status: PASS
- SHAP Output Space: log_odds
- SHAP Reconstruction Error: N/A

### TC010: boundary_threshold_high

- **Status:** PASS
- Raw Probability: N/A
- Calibrated Probability: 0.071114
- Predicted Class: Lower predicted default risk
- Risk Category: Low
- SHAP Status: PASS
- SHAP Output Space: log_odds
- SHAP Reconstruction Error: N/A

### TC006: Invalid SEX value (0)

- **Status:** PASS
- Raw Probability: N/A
- Calibrated Probability: N/A
- Predicted Class: N/A
- Risk Category: N/A
- SHAP Status: N/A
- SHAP Output Space: N/A
- SHAP Reconstruction Error: N/A

### TC007: Invalid EDUCATION value (10)

- **Status:** PASS
- Raw Probability: N/A
- Calibrated Probability: N/A
- Predicted Class: N/A
- Risk Category: N/A
- SHAP Status: N/A
- SHAP Output Space: N/A
- SHAP Reconstruction Error: N/A

### TC011: Missing LIMIT_BAL field

- **Status:** PASS
- Raw Probability: N/A
- Calibrated Probability: N/A
- Predicted Class: N/A
- Risk Category: N/A
- SHAP Status: N/A
- SHAP Output Space: N/A
- SHAP Reconstruction Error: N/A

### TC012: Negative AGE value

- **Status:** PASS
- Raw Probability: N/A
- Calibrated Probability: N/A
- Predicted Class: N/A
- Risk Category: N/A
- SHAP Status: N/A
- SHAP Output Space: N/A
- SHAP Reconstruction Error: N/A

### TC013: Unexpected field EXTRA_FIELD

- **Status:** PASS
- Raw Probability: N/A
- Calibrated Probability: N/A
- Predicted Class: N/A
- Risk Category: N/A
- SHAP Status: N/A
- SHAP Output Space: N/A
- SHAP Reconstruction Error: N/A


## Conclusions

All tests passed. The prediction pipeline is functioning correctly.

## Reproducibility Statement

These test results are reproducible. The same inputs will produce the same outputs
given the same model artifacts and calibration parameters.

## Limitations

- Test cases are synthetic examples, not real borrower profiles
- The model was trained on Taiwan credit card data, not Indian borrower data
- Risk tier labels are descriptive, not validated lending categories
- These tests verify pipeline correctness, not predictive accuracy for any population

