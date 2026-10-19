# CreditAI Phase 7 — Inference Verification Report

**Date:** 17 October 2026
**Status:** COMPLETED
**Phase:** Backend Inference Pipeline

---

## Executive Summary

Phase 7.1 (Inference Backend) has been successfully implemented. A working inference service has been created for the UCI Taiwan XGBoost model, allowing actual predictions to be generated from verified model artifacts. All 111 tests pass (98 existing + 13 new inference tests). The `/v1/score` endpoint remains unchanged and still returns `not_validated` with null probability.

**Verification Status: COMPLETED**

---

## 1. What Was Implemented

### 1.1 Backend Modules Created

**New Inference Service (`src/inference/`):**
- `__init__.py` - Module initialization with exports
- `model_registry.py` - Registry of verified models with metadata
- `predictor.py` - Prediction pipeline with feature engineering
- `schemas.py` - Pydantic schemas for request/response validation
- `explanations.py` - SHAP explanation service (structure only, not yet integrated)

**API Extensions (`src/api/app.py`):**
- `GET /v1/models` - List available models
- `GET /v1/models/{model_id}` - Get model information
- `GET /v1/models/{model_id}/schema` - Get feature schema
- `POST /v1/predict` - Run prediction (research inference only)

**Preserved Endpoints:**
- `GET /health` - Unchanged
- `POST /v1/score` - Unchanged, still returns `not_validated`

### 1.2 Model Registry

**Verified Model:**
- **Model ID:** `uci_taiwan_xgb`
- **Dataset:** UCI Default of Credit Card Clients (DS003)
- **Geography:** Taiwan (April-September 2005)
- **Target:** `default payment next month` (1 = Default, 0 = Repaid)
- **Target Prevalence:** 22.12% (6,636/30,000)
- **Feature Count:** 50 (23 raw + 27 engineered)
- **Model Type:** XGBoost
- **Artifact:** `models/creditai_model.joblib` ✅ VERIFIED
- **Feature Names:** `models/feature_names.json` ✅ VERIFIED
- **Metadata:** `models/model_metadata.json` ✅ VERIFIED
- **Calibration:** `models/calibration_model.joblib` (unfitted, not used)
- **Inference Ready:** YES
- **SHAP Available:** YES (not yet integrated)

**Historical Metrics (from Phase 1 report):**
- Test ROC-AUC: ~0.7807 (to be re-verified in Phase 7.2)
- Test PR-AUC: ~0.5588 (to be re-verified in Phase 7.2)

**Limitations:**
- Taiwan credit card data from 2005
- Not validated for Indian borrowers
- Cross-sectional benchmark, not time-series
- Historical evaluation only
- Target is next-month default, not fixed-horizon
- No Indian transfer claim or regulatory approval

### 1.3 Feature Schema

**Raw Features (23):**
- Demographics: LIMIT_BAL, SEX, EDUCATION, MARRIAGE, AGE
- Repayment Status: PAY_0, PAY_2, PAY_3, PAY_4, PAY_5, PAY_6
- Bill Amounts: BILL_AMT1 to BILL_AMT6
- Payment Amounts: PAY_AMT1 to PAY_AMT6

**Engineered Features (27, computed server-side):**
- Credit utilization: UTIL_1 to UTIL_6, AVG_UTILIZATION, MAX_UTILIZATION
- Payment ratios: PAY_TO_BILL_1 to PAY_TO_BILL_6, AVG_PAY_TO_BILL
- Delinquency: MAX_DELINQUENCY, AVG_DELINQUENCY, DELINQUENT_MONTHS_COUNT, RECENT_DELINQUENCY_FLAG
- Trends: DELINQUENCY_TREND_SHORT, DELINQUENCY_TREND_LONG
- Bill changes: BILL_CHANGE_1_2, BILL_GROWTH_OVER_LIMIT
- Payment behavior: PAYMENT_MONTHS_COUNT, TOTAL_PAY_TO_TOTAL_BILL, PAYMENT_AMOUNT_STD, TIMELY_PAYMENT_COUNT

### 1.4 Prediction Pipeline

**Flow:**
1. Validate input against feature schema
2. Load model and feature names from artifacts
3. Apply feature engineering (27 engineered features from 23 raw)
4. Compute raw probability from XGBoost model
5. Apply calibration (disabled - model unfitted)
6. Determine class and risk category
7. Return structured response with provenance

**Calibration Status:**
- Calibration model exists but is unfitted (slope/intercept not set)
- Predictions return as uncalibrated model scores
- Clearly labeled as `calibrated: false` in response

---

## 2. Test Results

### 2.1 Inference Tests (New)

**File:** `tests/test_inference.py`

**Test Coverage (13 tests):**
- Model registry: 6 tests
- Prediction pipeline: 4 tests
- Schemas: 3 tests

**Results:**
```
tests/test_inference.py::TestModelRegistry::test_model_registry_lists_available_models PASSED
tests/test_inference.py::TestModelRegistry::test_get_model_info_returns_correct_metadata PASSED
tests/test_inference.py::TestModelRegistry::test_get_model_info_includes_artifact_existence PASSED
tests/test_inference.py::TestModelRegistry::test_get_feature_schema_returns_feature_schema PASSED
tests/test_inference.py::TestModelRegistry::test_feature_schema_includes_field_types_and_constraints PASSED
tests/test_inference.py::TestModelRegistry::test_validate_model_artifact_checks_existence PASSED
tests/test_inference.py::TestPrediction::test_predict_with_valid_input_returns_probability PASSED
tests/test_inference.py::TestPrediction::test_predict_with_missing_required_field_raises_error PASSED
tests/test_inference.py::TestPrediction::test_predict_with_invalid_value_raises_error PASSED
tests/test_inference.py::TestPrediction::test_predict_returns_correct_provenance PASSED
tests/test_inference.py::TestSchemas::test_uci_taiwan_request_validates_correctly PASSED
tests/test_inference.py::TestSchemas::test_uci_taiwan_request_rejects_invalid_range PASSED
tests/test_inference.py::TestSchemas::test_prediction_request_rejects_extra_fields PASSED
```

**Status:** 13/13 PASSED

### 2.2 Existing Tests (Preserved)

**Total Test Suite:** 111 tests
- Existing tests: 98 tests
- New inference tests: 13 tests

**Results:**
```
111 passed, 23 warnings in 82.18s
```

**Status:** ALL TESTS PASSED

### 2.3 API Contract Verification

**`/v1/score` Endpoint:**
- Still returns `score_status: "not_validated"`
- Still returns `default_probability: null`
- Still returns `validated_risk_estimate: false`
- Still returns `model_version: null`
- All 20 API contract tests pass

**New Endpoints:**
- `/v1/models` - Returns list of available models
- `/v1/models/uci_taiwan_xgb` - Returns model metadata
- `/v1/models/uci_taiwan_xgb/schema` - Returns feature schema
- `/v1/predict` - Returns actual prediction from UCI model

**Status:** BACKWARD COMPATIBLE

---

## 3. Prediction Example

### 3.1 Sample Request

```json
{
  "model_id": "uci_taiwan_xgb",
  "features": {
    "LIMIT_BAL": 200000,
    "SEX": 2,
    "EDUCATION": 2,
    "MARRIAGE": 1,
    "AGE": 35,
    "PAY_0": 0,
    "PAY_2": 0,
    "PAY_3": 0,
    "PAY_4": 0,
    "PAY_5": 0,
    "PAY_6": 0,
    "BILL_AMT1": 50000,
    "BILL_AMT2": 45000,
    "BILL_AMT3": 40000,
    "BILL_AMT4": 35000,
    "BILL_AMT5": 30000,
    "BILL_AMT6": 25000,
    "PAY_AMT1": 5000,
    "PAY_AMT2": 5000,
    "PAY_AMT3": 5000,
    "PAY_AMT4": 5000,
    "PAY_AMT5": 5000,
    "PAY_AMT6": 5000
  }
}
```

### 3.2 Sample Response

```json
{
  "model_id": "uci_taiwan_xgb",
  "dataset_id": "DS003",
  "dataset_name": "Default of Credit Card Clients",
  "geography": "Taiwan",
  "target": "default payment next month",
  "target_meaning": "1 = Default next month, 0 = Repaid",
  "prediction_timestamp": "2026-10-17T10:30:00Z",
  "predicted_class": "Lower predicted default risk",
  "probability": 0.0599,
  "risk_category": "Low",
  "threshold": 0.5,
  "calibrated": false,
  "calibration_method": null,
  "limitations": [
    "Taiwan credit card data from 2005",
    "Not validated for Indian borrowers",
    "Cross-sectional benchmark, not time-series",
    "Historical evaluation only",
    "Target is next-month default, not fixed-horizon",
    "Population is credit card holders, not general borrowers",
    "No Indian transfer claim or regulatory approval"
  ],
  "feature_contributions": null
}
```

**Key Observations:**
- Probability is a raw model score (uncalibrated)
- Risk category derived from threshold (0.5)
- Limitations clearly listed
- Provenance clearly identifies dataset and geography
- No SHAP explanations yet (to be added in Phase 7.4)

---

## 4. Known Limitations

### 4.1 Calibration Model

**Issue:** The calibration model artifact exists but is unfitted (slope and intercept not set).

**Impact:** Predictions return as uncalibrated model scores.

**Root Cause:** The artifact was saved without fitting the calibration parameters.

**Mitigation:**
- Clearly label predictions as `calibrated: false`
- Document in response that probability is uncalibrated
- Future work: Re-fit calibration on validation set

### 4.2 Historical Metrics

**Issue:** Historical ROC-AUC and PR-AUC values from Phase 1 report are not re-verified.

**Impact:** Metrics are historical claims, not current verification.

**Mitigation:**
- Clearly label as historical in model registry
- Phase 7.2 will re-evaluate on test set to verify
- Do not claim verified performance until re-evaluated

### 4.3 SHAP Explanations

**Issue:** SHAP explainer code is written but not yet integrated into prediction pipeline.

**Impact:** No feature contributions returned in prediction response.

**Mitigation:**
- Return `feature_contributions: null` in response
- Phase 7.4 will integrate SHAP
- Until then, explanations unavailable

### 4.4 Model Artifact Format

**Issue:** Model artifact is saved as a dictionary (CalibratedClassifierCV wrapper), not raw XGBoost.

**Impact:** Had to extract `base_model` from dictionary for prediction.

**Mitigation:**
- Added logic to extract base model if artifact is dict
- Works correctly with current artifact format
- Document in code comments

---

## 5. Indian Deployment Readiness

**Status: NOT VALIDATED**

**Blockers:**
1. ❌ No authorized Indian borrower dataset
2. ❌ No lender partnership established
3. ❌ No consent evidence documented
4. ❌ No commercial-use rights verified
5. ❌ No regulatory compliance review
6. ❌ No demographic fairness testing
7. ❌ No temporal validation on Indian data

**Display Requirements:**
- Banner in frontend: "Indian deployment readiness: NOT VALIDATED"
- Clearly label all predictions as research-only
- Do not present Taiwan predictions as Indian-calibrated
- Do not claim regulatory approval

---

## 6. LendingClub Model Status

**Status:** NOT AVAILABLE FOR INFERENCE

**Reasons:**
- Phase 2.3 benchmark saved only evaluation metrics, not fitted model artifact
- Would require refitting model from scratch
- Refitting would require running full benchmark script
- Decision: Do not refit in Phase 7 (out of scope)

**Alternative:**
- Keep existing metrics display in frontend
- Add "Model artifact not saved" notice to Model Lab
- Future work: Re-evaluate and save model artifact if needed

---

## 7. Next Steps (Phase 7.2 - UCI Model Verification)

**Objective:** Re-verify UCI Taiwan model metrics by re-evaluating on test set.

**Tasks:**
1. Load UCI dataset (`Data/credit_default/default of credit card clients.xls`)
2. Apply preprocessing and feature engineering (reuse Phase 1 pipeline)
3. Load model artifact and verify it loads correctly
4. Split data into train/validation/test (70/15/15, stratified, seed=42)
5. Run inference on test set
6. Compute ROC-AUC, PR-AUC, Brier score, log loss
7. Compare to historical metrics (~0.7807 ROC-AUC, ~0.5588 PR-AUC)
8. Generate per-loan prediction scores for charts
9. Save scores to `models/uci_taiwan_predictions.csv`
10. Document results in verification report

**Success Criteria:**
- Test ROC-AUC within reasonable range of historical value
- Prediction scores generated successfully
- Scores saved for chart generation
- Verification report complete

---

## 8. Files Created or Modified

### 8.1 Created Files

**Backend:**
- `src/inference/__init__.py` - Module initialization
- `src/inference/model_registry.py` - Model registry (338 lines)
- `src/inference/predictor.py` - Prediction pipeline (398 lines)
- `src/inference/schemas.py` - Pydantic schemas (344 lines)
- `src/inference/explanations.py` - SHAP explanations (176 lines)
- `tests/test_inference.py` - Inference tests (257 lines)

**Documentation:**
- `reports/phase_7_implementation_plan.md` - Implementation plan (1105 lines)
- `reports/phase_7_inference_verification.md` - This report

### 8.2 Modified Files

**Backend:**
- `src/api/app.py` - Added new API endpoints (4 new routes)

**Total Lines Added:**
- Backend code: ~1,433 lines
- Tests: ~257 lines
- Documentation: ~1,105 lines
- **Total: ~2,795 lines**

---

## 9. Verification Checklist

- ✅ Model artifact exists and can be loaded
- ✅ Feature names JSON exists and matches
- ✅ Feature schema documented and validated
- ✅ Model registry populates correctly
- ✅ Prediction pipeline end-to-end works
- ✅ Feature engineering computes all 50 features
- ✅ Prediction returns probability in [0, 1]
- ✅ Prediction returns class and risk category
- ✅ Prediction returns provenance and limitations
- ✅ Input validation rejects invalid fields
- ✅ Input validation rejects out-of-range values
- ✅ Unknown model IDs are rejected
- ✅ All 111 tests pass
- ✅ `/v1/score` contract unchanged
- ✅ Backward compatibility preserved
- ✅ Indian deployment clearly marked as NOT VALIDATED
- ✅ No fabricated predictions or metrics
- ⚠️ Calibration model unfitted (documented)
- ⚠️ Historical metrics not re-verified (documented)
- ⚠️ SHAP not yet integrated (documented)

---

## 10. Conclusion

Phase 7.1 (Inference Backend) has been successfully implemented. A working inference service now exists for the UCI Taiwan XGBoost model, allowing actual predictions to be generated from verified model artifacts. All 111 tests pass, and the `/v1/score` endpoint remains unchanged with its safe `not_validated` behavior.

The inference pipeline correctly:
- Loads the model artifact
- Validates input against the feature schema
- Applies feature engineering (27 engineered features from 23 raw)
- Computes predictions from the XGBoost model
- Returns structured responses with provenance and limitations

The next phase (7.2) will re-verify the UCI model's historical metrics by re-evaluating on the test set and generating prediction scores for chart generation.

**Verification Status: COMPLETED**

**Indian Deployment Readiness: NOT VALIDATED**

---

*End of Phase 7 Inference Verification Report*
