# Phase 9 — Calibration and SHAP Audit Report

**Date:** 18 October 2026
**Model:** uci_taiwan_xgb
**Status:** VERIFIED

---

## Executive Summary

This report documents the independent verification of the calibration model and SHAP explanation system for the CreditAI prediction pipeline. Both components have been verified to function correctly.

**Overall Status:** ✓ VERIFIED

---

## Part 1 — Calibration Audit

### 1.1 Calibration Artifact

**Artifact Location:** `models/calibration_model.joblib`

**Calibration Type:** Platt scaling (sigmoid)

**Calibration Model:** `PlattCalibrator` from `src/calibration/calibrate.py`

**Underlying Model:** `sklearn.linear_model.LogisticRegression`

**Parameters:**
- Slope: 0.47414481616618126
- Intercept: -1.2645029152597382

**Verification:**
- ✓ Artifact exists and is loadable
- ✓ Slope and intercept attributes present (indicates fitted model)
- ✓ Parameters match evaluation JSON (`models/uci_taiwan_eval.json`)

### 1.2 Calibration Fitting Process

**Fitting Location:** `src/models/train.py` line 52

**Fitting Data:** Validation split predictions (not test labels)

**Code Verification:**
```python
# Line 52: Fit calibration on validation predictions
calibrator = PlattCalibrator()
calibrator.fit(val_pred_logits, y_val)

# Line 56: Apply calibration to test predictions
test_pred_calibrated = calibrator.predict_proba(test_pred_logits)
```

**Verification:**
- ✓ Calibration fitted on validation set predictions
- ✓ Calibration NOT fitted on test labels (no label leakage)
- ✓ Calibration applied to test predictions after fitting
- ✓ Calibration applied exactly once in inference pipeline

### 1.3 Calibration Formula

**Raw Model Output:** Probability (0-1 range)

**Calibration Process:**
1. Convert raw probability to log-odds: `logit_p = log(p / (1 - p))`
2. Apply Platt scaling: `scaled_logit = slope * logit_p + intercept`
3. Convert back to probability: `calibrated_p = sigmoid(scaled_logit)`

**Formula:**
```
calibrated_p = 1 / (1 + exp(-(slope * log(p / (1 - p)) + intercept)))
```

### 1.4 Calibration Verification Test

**Test Input:** Raw probability = 0.193

**Expected Output:**
- Logit: log(0.193 / 0.807) = -1.4306
- Scaled logit: 0.4741 * (-1.4306) + (-1.2645) = -1.9432
- Calibrated probability: sigmoid(-1.9432) = 0.1253

**Actual Output:** 0.12533724078265934

**Verification:** ✓ PASS - Calibrated probability is finite and between 0 and 1

### 1.5 Calibration in Inference Pipeline

**Location:** `src/inference/predictor.py` function `apply_calibration()`

**Verification:**
- ✓ Calibration model loaded correctly
- ✓ Fitted status checked (slope and intercept attributes)
- ✓ Calibration applied via `predict_proba()` method
- ✓ Calibration applied exactly once (not applied to already-calibrated output)
- ✓ Uncalibrated probability returned if calibration model not fitted

### 1.6 Calibration Compatibility

**Model Version:** Current model artifact

**Calibration Model:** Fitted on same model version

**Verification:**
- ✓ Calibration parameters match evaluation JSON from training
- ✓ Calibration was fitted on predictions from the same model architecture
- ✓ No version mismatch detected

### 1.7 Calibration Status

**Status:** ✓ VERIFIED

**Summary:**
- Calibration artifact exists and is properly fitted
- Calibration was fitted on appropriate data (validation split, not test labels)
- Calibration formula is correctly implemented
- Calibration is applied exactly once in the inference pipeline
- Calibration produces finite probabilities in [0, 1] range
- Calibration is compatible with current model version

---

## Part 2 — SHAP Audit

### 2.1 SHAP Implementation

**Location:** `src/inference/explanations.py`

**Explainer Type:** `shap.TreeExplainer`

**Explainer Target:** Base XGBoost model (not CalibratedClassifierCV wrapper)

**SHAP Library Version:** Available in environment

**Verification:**
- ✓ SHAP library is available
- ✓ TreeExplainer correctly instantiated
- ✓ Base model extracted from saved artifact (handles dictionary wrapper)

### 2.2 SHAP Input Verification

**Model:** XGBoost base model

**Feature Vector:** 50 features (23 raw + 27 engineered)

**Feature Names:** Matches model input features from `models/feature_names.json`

**Verification:**
- ✓ Feature vector passed to SHAP has correct length (50)
- ✓ Feature names match model input features
- ✓ Feature order matches model expectations

### 2.3 SHAP Output Space Verification

**Test:** Baseline + SHAP contributions reconstruction

**Test Input:** Zero-feature example (all features = 0)

**Results:**
- Baseline (expected value): 0.054526861757040024
- SHAP values sum: -0.09975165128707886
- Reconstructed output: 0.054526861757040024 + (-0.09975165128707886) = -0.045224789530038834
- Model log-odds: -0.04522474482655525
- Reconstruction error: 4.47e-8 (within 1e-6 tolerance)

**Verification:** ✓ PASS - SHAP values reconstruct model log-odds within numerical tolerance

**Output Space:** Log-odds (margin) space

**Explanation:**
- SHAP values are contributions to the model's raw output (log-odds)
- NOT contributions to the calibrated probability
- Baseline is the expected log-odds of the average prediction
- Positive SHAP value → increases log-odds of default
- Negative SHAP value → decreases log-odds of default

### 2.4 SHAP Contribution Direction

**Direction Labeling:**
- Positive SHAP value → "increases_risk"
- Negative SHAP value → "decreases_risk"

**Verification:**
- ✓ Direction labels are consistent with output space (log-odds)
- ✓ Positive contribution correctly labeled as increasing risk
- ✓ Negative contribution correctly labeled as decreasing risk

### 2.5 SHAP in Inference Pipeline

**Location:** `src/inference/predictor.py` function `predict()`

**Process:**
1. Load or create cached TreeExplainer
2. Extract base model if saved as dictionary
3. Convert feature dictionary to array in correct order
4. Call `explainer.shap_values(feat_array)`
5. Handle binary classification (extract class 1 values)
6. Convert to FeatureContribution objects
7. Sort by absolute contribution descending
8. Return top K contributions (default K=6)

**Verification:**
- ✓ SHAP explanation computed for all valid test cases
- ✓ SHAP values successfully extracted and formatted
- ✓ Top 6 contributions returned (as configured)
- ✓ No errors in SHAP computation pipeline

### 2.6 SHAP Test Case Results

**Test Cases:** 10 valid input profiles

**SHAP Status:** PASS for all 10 cases

**SHAP Output Space:** log_odds for all 10 cases

**Reconstruction Error:** Not measured in test suite (requires additional verification)

**Verification:**
- ✓ SHAP explanations generated successfully for all valid inputs
- ✓ SHAP output space identified as log-odds
- ✓ No SHAP computation errors

### 2.7 SHAP Frontend Display

**Status:** ⚠ UNVERIFIED

**Concerns:**
- Not verified whether frontend correctly describes SHAP output space (log-odds vs probability)
- Not verified whether frontend describes SHAP values as percentage-point changes
- Not verified whether frontend displays tooltip explaining SHAP meaning

**Recommendations:**
- Add tooltip: "SHAP values represent contributions to the model's log-odds output, not to the calibrated probability"
- Ensure labels distinguish between log-odds contributions and probability changes
- Display SHAP output space explicitly in the UI

### 2.8 SHAP Status

**Status:** ✓ VERIFIED (backend implementation)

**Summary:**
- SHAP library is available and correctly instantiated
- SHAP values reconstruct model output (log-odds) within numerical tolerance
- SHAP output space is verified as log-odds (margin) space
- SHAP contribution directions are correctly labeled
- SHAP explanations generated successfully for all test cases
- Frontend display of SHAP values remains unverified

---

## Part 3 — Integrated Verification

### 3.1 Calibration + SHAP Consistency

**Verification:**
- ✓ Calibration applied after SHAP computation (SHAP uses raw model output)
- ✓ SHAP explains raw model output (log-odds), not calibrated probability
- ✓ No circular dependency between calibration and SHAP

### 3.2 Test Case Verification

**Total Test Cases:** 15 (10 valid, 5 invalid)

**Calibration Status:** PASS for all 10 valid cases
- All calibrated probabilities are finite and in [0, 1] range
- Calibration method reported as "Platt sigmoid"

**SHAP Status:** PASS for all 10 valid cases
- All SHAP explanations generated successfully
- SHAP output space identified as log_odds

**Input Validation:** PASS for all 5 invalid cases
- All invalid inputs correctly rejected with validation errors

### 3.3 Reproducibility

**Verification:**
- ✓ Same inputs produce same outputs across multiple runs
- ✓ Calibration parameters are deterministic
- ✓ SHAP values are deterministic (TreeExplainer with tree models)
- ✓ Test suite produces consistent results

---

## Part 4 — Known Limitations

### 4.1 Calibration Limitations

1. **Temporal Validity:** Calibration was fitted on 2005 Taiwan data. May not generalize to current populations or geographies.

2. **Population Validity:** Calibration was fitted on Taiwan credit card holders. Not validated for Indian borrowers.

3. **Method:** Platt scaling assumes sigmoid relationship between log-odds and true probability. May not hold for all distributions.

### 4.2 SHAP Limitations

1. **Output Space:** SHAP values are in log-odds space, not probability space. Users may misinterpret contributions.

2. **Linearity Assumption:** SHAP additive explanations assume linear contributions, which may not capture complex interactions fully.

3. **Frontend Display:** Frontend display of SHAP values has not been audited. May contain misleading labels or descriptions.

### 4.3 General Limitations

1. **Research-Only Status:** Model and calibration are for research benchmark only. Not validated for production lending decisions.

2. **Geographic Mismatch:** Taiwan data cannot validate accuracy for Indian borrowers.

3. **Temporal Mismatch:** 2005 data may not reflect current credit behavior patterns.

---

## Part 5 — Recommendations

### 5.1 Calibration Recommendations

1. ✓ **IMPLEMENTED:** Verify calibration was fitted on validation split (not test labels)
2. ✓ **IMPLEMENTED:** Verify calibration parameters match evaluation artifacts
3. ✓ **IMPLEMENTED:** Verify calibration is applied exactly once
4. ⚠ **RECOMMENDED:** Re-fit calibration on more recent data if deploying to production
5. ⚠ **RECOMMENDED:** Evaluate calibration quality on held-out test set (reliability diagrams, Brier score)

### 5.2 SHAP Recommendations

1. ✓ **IMPLEMENTED:** Verify SHAP values reconstruct model output
2. ✓ **IMPLEMENTED:** Verify SHAP output space (log-odds)
3. ⚠ **RECOMMENDED:** Audit frontend display of SHAP values
4. ⚠ **RECOMMENDED:** Add tooltip explaining SHAP output space
5. ⚠ **RECOMMENDED:** Ensure SHAP values are not described as percentage-point changes

### 5.3 General Recommendations

1. ⚠ **RECOMMENDED:** Complete Session 5 (Performance Metrics on Held-Out Test Set)
2. ⚠ **RECOMMENDED:** Complete Session 6 (Frontend Improvements)
3. ⚠ **RECOMMENDED:** Add research-only warning to frontend
4. ⚠ **RECOMMENDED:** Document calibration and SHAP limitations in user-facing documentation

---

## Part 6 — Conclusion

### 6.1 Calibration Status

**Status:** ✓ VERIFIED

**Verified:**
- Calibration artifact exists and is properly fitted
- Calibration was fitted on validation split (not test labels)
- Calibration formula is correctly implemented
- Calibration is applied exactly once
- Calibration produces valid probabilities
- Calibration is compatible with current model version

**Unverified:**
- Calibration quality on held-out test set (Brier score, reliability diagram)
- Calibration generalization to other populations or time periods

### 6.2 SHAP Status

**Status:** ✓ VERIFIED (backend implementation)

**Verified:**
- SHAP library is available and correctly instantiated
- SHAP values reconstruct model output within numerical tolerance
- SHAP output space is log-odds (margin) space
- SHAP contribution directions are correctly labeled
- SHAP explanations generated successfully for all test cases

**Unverified:**
- Frontend display of SHAP values
- Frontend interpretation of SHAP output space
- Frontend labels for SHAP contributions

### 6.3 Overall Status

**Status:** ✓ VERIFIED

**Summary:**
- Calibration model is verified as fitted and correctly implemented
- SHAP implementation is verified as correct in log-odds space
- Reproducible test cases confirm consistent behavior
- Frontend display of calibration and SHAP requires additional verification

**Next Steps:**
- Complete Session 5: Evaluate predictive performance on held-out test set
- Complete Session 6: Audit and improve frontend display
- Add research-only warnings and limitations to UI

---

*End of Calibration and SHAP Audit Report*
