# CreditAI Phase 7 — Implementation Plan

**Date:** 17 October 2026
**Status:** IMPLEMENTATION PLAN
**Phase:** Working ML Prediction Product + Advanced Interactive Frontend

---

## Executive Summary

This plan builds a working ML prediction application for CreditAI based on verified existing model artifacts. The application will allow users to select a supported dataset, enter borrower data, obtain actual predictions from trained models, and explore predictions through probability displays, charts, model explanations, and evaluation results.

**Critical Finding:** Only ONE model artifact is verified and suitable for inference: the UCI Taiwan XGBoost model (`models/creditai_model.joblib`). The LendingClub benchmark (Phase 2.3) has NO saved model artifact, only evaluation metrics. Synthetic models are weak and not suitable for production claims.

**Scope:** Phase 7 will implement a research inference service for the UCI Taiwan model only, with clear labeling of its limitations. Indian deployment remains blocked due to lack of authorized data.

---

## 1. Phase A: Audit Results — What Actually Exists

### 1.1 Verified Model Artifacts

| Model ID | Dataset | Artifact Path | Status | Test ROC-AUC | Test PR-AUC | Calibration | Inference Ready |
|----------|---------|--------------|--------|--------------|-------------|-------------|-----------------|
| **uci_taiwan_xgb** | UCI Default of Credit Card Clients (DS003) | `models/creditai_model.joblib` | ✅ VERIFIED | ~0.7807 (historical) | ~0.5588 (historical) | `models/calibration_model.joblib` | **YES** |
| lendingclub_hgb | LendingClub accepted loans (DS001) | NOT SAVED | ❌ MISSING | 0.7056 | 0.3947 | Not fitted | NO |
| synthetic_rf | Phase 1.1 synthetic | `models/synthetic_phase1_1/creditai_risk_engine.joblib` | ⚠️ WEAK | 0.5397 | 0.2357 | `models/synthetic_phase1_1/calibration_model.joblib` | BLOCKED (synthetic) |

### 1.2 Verified Datasets

| Dataset ID | Name | Path | Rows | Target | Geography | Qualification |
|------------|------|------|------|--------|-----------|---------------|
| DS003 | Default of Credit Card Clients | `Data/credit_default/default of credit card clients.xls` | 30,000 | default payment next month (22.12%) | Taiwan | QUALIFIED_FOR_RESEARCH |
| DS001 | LendingClub accepted loans | `Data/archive/accepted_2007_to_2018Q4.csv` | 2,260,701 | loan_status (19.98% closed) | U.S. | QUALIFIED_FOR_RESEARCH |

### 1.3 Existing Backend Components

- ✅ FastAPI app (`src/api/app.py`) with `/health` and `/v1/score` endpoints
- ✅ API contract validation (`src/api/contract.py`)
- ✅ Phase 5 data validation modules
- ✅ Phase 5 evaluation utilities
- ✅ Test suite: 98 tests passing

### 1.4 Existing Frontend Components

- ✅ React + TypeScript + Vite application
- ✅ 8 views: Overview, Discovery, Portfolio, Lab, Explorer, Explainability, Monitoring, Architecture
- ✅ Dataset inventory display
- ✅ Model comparison charts (LendingClub metrics)
- ✅ API health check (synthetic example only)
- ⚠️ No live prediction UI
- ⚠️ No borrower input forms
- ⚠️ No SHAP explanations displayed
- ⚠️ ROC/PR curves unavailable (no per-loan scores saved)

### 1.5 Critical Blockers

1. **LendingClub Model Artifact Missing:** Phase 2.3 benchmark saved only metrics, not the fitted model. Cannot run inference without refitting.
2. **No Per-Loan Scores Saved:** LendingClub evaluation did not save prediction probabilities, so ROC/PR curves cannot be regenerated.
3. **No Indian Data:** No authorized Indian borrower dataset available. Indian deployment blocked.
4. **UCI Model Features Not Exposed:** The UCI model requires 50 features (23 raw + 27 engineered). Need to expose feature schema and engineering pipeline.

---

## 2. Phase B: Inference Pipeline Design

### 2.1 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Executive    │  │ Borrower     │  │ Historical   │      │
│  │ Dashboard    │  │ Risk        │  │ Record       │      │
│  │              │  │ Prediction  │  │ Explorer     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Model        │  │ Predictor    │  │ Explanations │      │
│  │ Registry     │  │ Service     │  │ Service     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                Model Artifacts & Data                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ UCI Taiwan   │  │ Calibration  │  │ Feature      │      │
│  │ XGBoost      │  │ Model        │  │ Schema       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 New Backend Modules

#### 2.2.1 `src/inference/model_registry.py`

**Purpose:** Central registry of verified models and their metadata.

**Functions:**
- `get_available_models()` → List of model IDs with metadata
- `get_model_info(model_id)` → Model metadata (dataset, features, geography, limitations)
- `validate_model_artifact(model_id)` → Check if artifact exists and can load
- `get_feature_schema(model_id)` → Expected input features with types, ranges, constraints

**Model Registry Structure:**
```python
MODELS = {
    "uci_taiwan_xgb": {
        "artifact_path": "models/creditai_model.joblib",
        "calibration_path": "models/calibration_model.joblib",
        "dataset_id": "DS003",
        "dataset_name": "Default of Credit Card Clients",
        "geography": "Taiwan",
        "target": "default payment next month",
        "target_meaning": "1 = Default next month, 0 = Repaid",
        "feature_count": 50,
        "training_date": "2026-10-06",
        "test_roc_auc": 0.7807,  # Historical, to be verified
        "test_pr_auc": 0.5588,   # Historical, to be verified
        "calibration_status": "Platt scaling fitted on validation",
        "limitations": [
            "Taiwan credit card data from 2005",
            "Not validated for Indian borrowers",
            "Cross-sectional benchmark, not time-series",
            "Historical evaluation only"
        ],
        "inference_ready": True
    }
}
```

#### 2.2.2 `src/inference/predictor.py`

**Purpose:** Load model, apply preprocessing, compute predictions.

**Functions:**
- `load_model_and_preprocessing(model_id)` → Load model artifact and feature names
- `validate_input(record, schema)` → Validate record against feature schema
- `apply_feature_engineering(raw_record)` → Transform raw features to engineered features
- `predict_proba(model, features)` → Get raw probability from model
- `apply_calibration(proba, calibration_model)` → Apply Platt scaling if available
- `predict(model_id, input_record)` → End-to-end prediction pipeline

**Error Handling:**
- Artifact not found → 404 with clear message
- Invalid model ID → 400 with list of available models
- Missing required fields → 422 with field names
- Invalid values (out of range, wrong type) → 422 with details
- Model loading failure → 500 with technical details

#### 2.2.3 `src/inference/schemas.py`

**Purpose:** Pydantic schemas for request/response validation.

**Schemas:**
- `PredictionRequest` → Base schema for prediction requests
- `UCITaiwanRequest` → Specific schema for UCI Taiwan features
- `PredictionResponse` → Standardized prediction response
- `ModelInfoResponse` → Model metadata response
- `FeatureSchemaResponse` → Feature schema response

**Standard Response Format:**
```python
{
    "model_id": "uci_taiwan_xgb",
    "dataset_id": "DS003",
    "dataset_name": "Default of Credit Card Clients",
    "geography": "Taiwan",
    "target": "default payment next month",
    "prediction_timestamp": "2026-10-17T10:30:00Z",
    "predicted_class": "Default risk",
    "probability": 0.342,
    "risk_category": "Medium",
    "threshold": 0.5,
    "calibrated": True,
    "limitations": [...],
    "feature_contributions": [...]  # Optional, if SHAP available
}
```

#### 2.2.4 `src/inference/explanations.py`

**Purpose:** Generate SHAP explanations for predictions.

**Functions:**
- `load_shap_explainer(model, background_data)` → Load or create SHAP explainer
- `explain_prediction(explainer, features)` → Get feature contributions
- `format_explanations(contributions, feature_names)` → Format for response

**Notes:**
- Only implemented for tree models (XGBoost, RandomForest)
- Requires background data for TreeExplainer
- Returns top positive and negative contributors
- Clearly labels as "model association, not causation"

### 2.3 New API Endpoints

#### 2.3.1 Model Discovery Endpoints

```
GET /v1/models
→ List all available models with metadata

GET /v1/models/{model_id}
→ Get detailed model information

GET /v1/models/{model_id}/schema
→ Get feature schema for model (types, ranges, constraints)
```

#### 2.3.2 Prediction Endpoints

```
POST /v1/predict
→ Run prediction for a single borrower
Body: { "model_id": "uci_taiwan_xgb", "features": {...} }
Response: PredictionResponse
```

#### 2.3.3 Dataset Endpoints (Read-Only)

```
GET /v1/datasets
→ List available datasets (from inventory)

GET /v1/datasets/{dataset_id}
→ Get dataset metadata

GET /v1/datasets/{dataset_id}/sample
→ Get a sample record (non-sensitive fields only)
```

#### 2.3.4 Evaluation Endpoints

```
GET /v1/evaluation/{model_id}/metrics
→ Get saved evaluation metrics

GET /v1/evaluation/{model_id}/curves
→ Get ROC/PR curve coordinates (if available)
```

### 2.4 Preserved Endpoints

- `GET /health` → Unchanged
- `POST /v1/score` → Unchanged, still returns `not_validated` with null probability

---

## 3. Phase C: Inference Modes

### 3.1 Mode 1: Single Borrower Prediction

**Location:** Frontend "Borrower Risk Prediction" view

**Workflow:**
1. User selects model from dropdown (initially only UCI Taiwan available)
2. Form renders dynamically based on model's feature schema
3. User enters values for each field (numeric sliders, categorical dropdowns, etc.)
4. Client-side validation checks ranges and required fields
5. "Run Prediction" button sends POST to `/v1/predict`
6. Display results:
   - Predicted class (Default risk / Lower predicted default risk)
   - Probability gauge or bar
   - Risk category badge (Low / Medium / High)
   - Model and dataset provenance
   - Feature contributions (if SHAP available)
   - Limitations and warnings

**UCI Taiwan Form Fields (23 raw features):**
- LIMIT_BAL (numeric, 0-1M NT$)
- SEX (categorical: 1=male, 2=female)
- EDUCATION (categorical: 1=graduate, 2=university, 3=high school, 4=others, 5=unknown, 6=unknown)
- MARRIAGE (categorical: 1=married, 2=single, 3=others)
- AGE (numeric, 21-79)
- PAY_0 to PAY_6 (numeric: -2=pay duly, -1=partial pay, 0=revolving, 1-9=delay months)
- BILL_AMT1 to BILL_AMT6 (numeric, -335k to 1.68M NT$)
- PAY_AMT1 to PAY_AMT6 (numeric, 0-873k NT$)

**Engineered Features (computed server-side):**
- UTIL_1 to UTIL_6, AVG_UTILIZATION, MAX_UTILIZATION
- PAY_TO_BILL_1 to PAY_TO_BILL_6, AVG_PAY_TO_BILL
- MAX_DELINQUENCY, AVG_DELINQUENCY, DELINQUENT_MONTHS_COUNT
- RECENT_DELINQUENCY_FLAG, DELINQUENCY_TREND_SHORT/LONG
- BILL_CHANGE_1_2, BILL_GROWTH_OVER_LIMIT
- PAYMENT_MONTHS_COUNT, TOTAL_PAY_TO_TOTAL_BILL
- PAYMENT_AMOUNT_STD, TIMELY_PAYMENT_COUNT

### 3.2 Mode 2: Historical Record Explorer

**Location:** Frontend "Historical Record Explorer" tab within Borrower Risk Prediction

**Workflow:**
1. User selects dataset (UCI Taiwan only initially)
2. User selects a record from the dataset (random sample or by ID)
3. Display the record's features (read-only)
4. "Run Prediction" button sends POST to `/v1/predict`
5. Display prediction results
6. If dataset contains actual target, show actual outcome separately:
   - "Actual outcome: Repaid (0)" or "Actual outcome: Default (1)"
   - Clear separation: "This does not prove every prediction is correct"
7. Allow comparison across multiple records

**Data Access:**
- Load only non-sensitive fields from UCI dataset
- Exclude ID column
- Paginate results (e.g., 10 records per page)
- Search/filter by feature values

---

## 4. Phase D: Frontend Prediction Experience

### 4.1 Executive Dashboard Updates

**Add:**
- Active research model indicator (currently UCI Taiwan XGBoost)
- Dataset source and geography
- Test-set ROC-AUC and PR-AUC (with verification status)
- Calibration status badge
- "Live inference available" indicator (for UCI model only)
- Indian deployment readiness: NOT VALIDATED banner

**Preserve:**
- Historical LendingClub metrics
- All existing KPIs and charts
- Clear separation between historical benchmarks and live inference

### 4.2 Borrower Risk Prediction View (New Primary Screen)

**Layout:**
```
┌────────────────────────────────────────────────────────────┐
│  Left Panel — Borrower Data           Right Panel — Result  │
│  ┌──────────────────────────────┐    ┌──────────────────┐  │
│  │ Model Selection               │    │ Predicted Class │  │
│  │ [UCI Taiwan XGBoost ▼]        │    │ Default risk     │  │
│  │                              │    │                  │  │
│  │ Borrower Form                 │    │ Probability      │  │
│  │ LIMIT_BAL: [_____] NT$       │    │ ████████░░ 34%   │  │
│  │ SEX: [Male ▼]                │    │                  │  │
│  │ EDUCATION: [University ▼]    │    │ Risk Category    │  │
│  │ AGE: [35]                    │    │ Medium           │  │
│  │ PAY_0: [0]                   │    │                  │  │
│  │ ... (23 fields)              │    │ Model: UCI Taiwan │  │
│  │                              │    │ Dataset: DS003   │  │
│  │ [Load Historical Example]    │    │ Geography: Taiwan │  │
│  │                              │    │ Timestamp: ...    │  │
│  │ [Run Prediction]             │    │                  │  │
│  └──────────────────────────────┘    │ Limitations:     │  │
│                                     │ • Taiwan 2005    │  │
│                                     │ • Not India       │  │
│                                     └──────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

**Features:**
- Dynamic form generation from model schema
- Input validation (ranges, types, required)
- Multiple input types: sliders, dropdowns, number inputs
- "Load Historical Example" button loads a random record from dataset
- Clear error messages for invalid inputs
- Loading state during prediction
- Retry button on prediction failure

### 4.3 Prediction Explanation View

**Content:**
- SHAP waterfal plot or bar chart (if available)
- Top 5 risk-increasing features with contributions
- Top 5 risk-decreasing features with contributions
- Explanation of positive vs negative contributions
- Clear disclaimer: "Model association, not causation"

**Fallback:**
- If SHAP unavailable, display feature importance from model
- If neither available, display "Explanations unavailable for this model"

### 4.4 Model Performance Lab Updates

**Add:**
- ROC curve (recompute from saved scores or generate new predictions)
- PR curve (same as ROC)
- Calibration/reliability curve (if calibration model available)
- Threshold-versus-precision/recall chart
- Actual vs predicted outcome comparison

**Preserve:**
- Existing confusion matrix
- Existing model comparison table
- Existing metric tables

**Implementation Strategy:**
- For UCI model: Re-evaluate on test set to generate per-loan scores
- Save scores to `models/uci_taiwan_predictions.csv`
- Generate curves from saved scores
- For LendingClub: Keep existing "unavailable" state (no model artifact)

### 4.5 Portfolio Analytics

**Scope:**
- Only for datasets with actual data (UCI Taiwan)
- Show default/repayment distribution
- Feature distributions (age, credit limit, etc.)
- Missingness charts
- Segment performance (by education, marriage, etc.)

**Not Implemented:**
- LendingClub portfolio (already shown in existing views)
- Synthetic data (blocked)

### 4.6 Dataset Explorer Updates

**Enhance:**
- Add "Inference Ready" badge to qualified models
- Show feature count and schema availability
- Link to model registry if model exists
- Display calibration status

### 4.7 Model Comparison

**Scope:**
- Compare models on same dataset (UCI only has one model)
- Display: ROC-AUC, PR-AUC, Precision, Recall, F1, Brier, Log Loss
- Show calibration status
- Compare only when multiple models available for same dataset

### 4.8 Monitoring and Audit

**Current State:**
- Display "Live monitoring not connected"
- Show historical vintage data (already implemented)

**Future (Out of Scope for Phase 7):**
- Live prediction logs
- Drift detection
- PSI calculation
- Model version tracking

---

## 5. Phase E: Visualization Requirements

### 5.1 Chart Library

**Selection:** Rechart (React charting library)
- Already used in existing frontend
- Supports bar charts, line charts, area charts
- Responsive and interactive
- TypeScript support

### 5.2 Required Charts

#### 5.2.1 Probability Gauge
- Half-circle gauge showing 0-1 probability
- Color-coded: green (low), yellow (medium), red (high)
- Clear threshold markers

#### 5.2.2 ROC Curve
- Line chart with FPR on x-axis, TPR on y-axis
- Diagonal baseline (random classifier)
- Point at selected threshold
- AUC value in legend
- Tooltip showing (FPR, TPR) on hover

#### 5.2.3 PR Curve
- Line chart with Recall on x-axis, Precision on y-axis
- Baseline at prevalence
- AUC value in legend
- Tooltip showing (Recall, Precision) on hover

#### 5.2.4 Calibration Curve
- Scatter plot with predicted probability on x-axis, observed default rate on y-axis
- Diagonal perfect calibration line
- Binned points with confidence intervals
- Brier score in legend

#### 5.2.5 Confusion Matrix
- 2x2 heatmap with counts
- Color intensity based on count
- Labels: TN, FP, FN, TP
- Metrics: Precision, Recall, F1

#### 5.2.6 Feature Importance Bar Chart
- Horizontal bar chart
- Top 10 features
- SHAP values or model feature importance
- Color: blue (decreases risk), red (increases risk)

#### 5.2.7 Threshold Sensitivity Chart
- Line chart with threshold on x-axis
- Multiple lines: Precision, Recall, F1
- Selected threshold marker
- Tooltip showing metrics at threshold

### 5.3 Chart Styling

**Color Scheme:**
- Default/High risk: #E74C3C (red)
- Lower predicted risk: #27AE60 (green)
- Neutral/Unavailable: #95A5A6 (gray)
- Emphasis: #3498DB (blue)

**Common Elements:**
- Consistent font sizes and weights
- Clear axis labels with units
- Legends where applicable
- Tooltips with context
- Responsive containers
- Empty states with helpful messages
- Loading skeletons
- Error states with retry option

---

## 6. Phase F: FastAPI Integration

### 6.1 New Routes

#### 6.1.1 Model Registry

```python
@app.get("/v1/models")
async def list_models():
    """List all available models with metadata."""
    return get_available_models()

@app.get("/v1/models/{model_id}")
async def get_model_info(model_id: str):
    """Get detailed model information."""
    if model_id not in MODELS:
        raise HTTPException(404, f"Model {model_id} not found")
    return MODELS[model_id]

@app.get("/v1/models/{model_id}/schema")
async def get_model_schema(model_id: str):
    """Get feature schema for model."""
    if model_id not in MODELS:
        raise HTTPException(404, f"Model {model_id} not found")
    return get_feature_schema(model_id)
```

#### 6.1.2 Prediction

```python
@app.post("/v1/predict")
async def predict(request: PredictionRequest):
    """Run prediction for a single borrower."""
    try:
        result = predict(request.model_id, request.features)
        return result
    except ArtifactNotFoundError as e:
        raise HTTPException(404, str(e))
    except InvalidInputError as e:
        raise HTTPException(422, str(e))
    except ModelLoadError as e:
        raise HTTPException(500, str(e))
```

#### 6.1.3 Datasets

```python
@app.get("/v1/datasets")
async def list_datasets():
    """List available datasets from inventory."""
    return load_dataset_inventory()

@app.get("/v1/datasets/{dataset_id}")
async def get_dataset_info(dataset_id: str):
    """Get dataset metadata."""
    inventory = load_dataset_inventory()
    dataset = next((d for d in inventory if d["dataset_id"] == dataset_id), None)
    if not dataset:
        raise HTTPException(404, f"Dataset {dataset_id} not found")
    return dataset

@app.get("/v1/datasets/{dataset_id}/sample")
async def get_dataset_sample(dataset_id: str, limit: int = 10):
    """Get a sample of records (non-sensitive fields only)."""
    if dataset_id != "DS003":
        raise HTTPException(400, "Only UCI Taiwan dataset supports sampling")
    return get_uci_sample(limit)
```

### 6.2 Backward Compatibility

**Preserve:**
- `/v1/score` endpoint unchanged
- `not_validated_response()` unchanged
- All existing tests passing

**Add:**
- New endpoints in `/v1/` namespace
- Separate test file for new endpoints
- No changes to existing contracts

### 6.3 Input Validation

**Allowlist:**
- Only `uci_taiwan_xgb` model ID accepted initially
- Only feature names in schema accepted
- Value ranges enforced
- Required fields enforced

**Reject:**
- Unknown model IDs
- Arbitrary file paths
- Arbitrary dataset names
- Extra fields beyond schema

---

## 7. Phase G: Model Validation and Data Integrity

### 7.1 Pre-Inference Checks

**Before enabling a model for inference:**
1. ✅ Verify artifact exists at expected path
2. ✅ Verify artifact can be loaded with joblib
3. ✅ Verify feature names JSON exists and matches
4. ✅ Verify calibration model exists (if claimed)
5. ✅ Verify positive class mapping (1 = default)
6. ✅ Verify dataset source and license
7. ✅ Link metrics to correct evaluation report
8. ✅ Check for target leakage in features
9. ✅ Verify train/test separation
10. ✅ Document limitations

### 7.2 UCI Taiwan Model Verification

**To Verify:**
- Artifact path: `models/creditai_model.joblib` ✅ EXISTS
- Feature names: `models/feature_names.json` ✅ EXISTS
- Calibration: `models/calibration_model.joblib` ✅ EXISTS
- Metadata: `models/model_metadata.json` ✅ EXISTS
- Dataset: `Data/credit_default/default of credit card clients.xls` ✅ EXISTS
- Feature count: 50 (23 raw + 27 engineered) ✅ DOCUMENTED
- Target: `default payment next month` ✅ DOCUMENTED
- Positive class: 1 = default ✅ DOCUMENTED
- Geography: Taiwan ✅ DOCUMENTED
- License: CC BY 4.0 ✅ DOCUMENTED

**To Recompute:**
- Load test set and re-evaluate to verify historical metrics
- Generate per-loan prediction scores for charts
- Verify SHAP explainer works with loaded model

### 7.3 LendingClub Model Status

**Status:** NOT AVAILABLE FOR INFERENCE

**Reasons:**
- Phase 2.3 did not save fitted model artifact
- Only evaluation metrics saved
- Would require refitting model from scratch
- Refitting would require running full benchmark script
- Decision: Do not refit in Phase 7 (out of scope)

**Alternative:**
- Add "Model artifact not saved" notice to Model Lab
- Keep existing metrics display
- Add "Re-evaluate to enable inference" button (future work)

### 7.4 Synthetic Model Status

**Status:** BLOCKED FOR INFERENCE

**Reasons:**
- Weak performance (ROC-AUC ~0.54)
- Synthetic data, not real borrowers
- Cannot claim real-world validity
- Audit report explicitly states limitations

**Action:**
- Do not expose in model registry
- Keep for pipeline testing only
- Clearly label as synthetic in any display

---

## 8. Phase H: India-Specific Readiness

### 8.1 Current Status

**Indian Deployment Readiness: NOT VALIDATED**

**Blockers:**
1. ❌ No authorized Indian borrower dataset
2. ❌ No lender partnership established
3. ❌ No consent evidence documented
4. ❌ No commercial-use rights verified
5. ❌ No regulatory compliance review
6. ❌ No demographic fairness testing
7. ❌ No temporal validation on Indian data

### 8.2 Display Requirements

**Add to all views:**
- Banner: "Indian deployment readiness: NOT VALIDATED"
- Tooltip: "No authorized Indian borrower data available"
- Link to Architecture & Audit view for details

**Prohibited:**
- Do not present U.S./Taiwan predictions as Indian-calibrated
- Do not claim regulatory approval
- Do not claim system ready for lender deployment
- Do not claim partnership without evidence

### 8.3 Future Requirements (Out of Scope)

To enable Indian deployment:
1. Secure data-use agreement with lender
2. Define observed default (DPD/write-off, horizon)
3. Receive pseudonymized sample (application features + repayment events)
4. Run temporal validation (later holdout, prevalence baseline)
5. Calibrate on Indian validation set
6. Fairness and stability evaluation
7. Regulatory and governance review

---

## 9. Phase I: Testing

### 9.1 Backend Tests

**New Test File:** `tests/test_inference.py`

**Test Cases:**
1. `test_model_registry_lists_available_models`
2. `test_get_model_info_returns_correct_metadata`
3. `test_get_model_schema_returns_feature_schema`
4. `test_unknown_model_id_returns_404`
5. `test_predict_with_valid_input_returns_probability`
6. `test_predict_with_missing_required_field_returns_422`
7. `test_predict_with_invalid_value_returns_422`
8. `test_predict_with_unknown_model_returns_404`
9. `test_predict_applies_calibration_if_available`
10. `test_predict_returns_correct_provenance`
11. `test_dataset_sample_returns_non_sensitive_fields`
12. `test_dataset_sample_paginates_correctly`
13. `test_feature_engineering_computes_all_50_features`
14. `test_shap_explainer_generates_contributions`
15. `test_error_messages_do_not_expose_sensitive_data`

**Preserve:**
- All 98 existing tests
- API contract tests
- Integration tests

### 9.2 Frontend Tests

**New Test File:** `frontend/tests/Prediction.test.tsx`

**Test Cases:**
1. Model selection dropdown renders
2. Borrower form renders correct fields for UCI model
3. Input validation rejects out-of-range values
4. Run Prediction button sends correct API request
5. Prediction result displays probability and class
6. Risk category badge shows correct color
7. Model provenance displays correctly
8. Error state displays helpful message
9. Retry button works on prediction failure
10. Load Historical Example loads random record

**Preserve:**
- Existing component tests (if any)
- TypeScript compilation

### 9.3 Integration Tests

**Test File:** `tests/test_inference_integration.py`

**Test Cases:**
1. End-to-end prediction flow (API + inference service)
2. Schema validation end-to-end
3. Calibration application end-to-end
4. SHAP explanation generation end-to-end
5. Dataset sampling end-to-end

### 9.4 Verification Commands

```bash
# Backend tests
.venv/Scripts/python.exe -m pytest tests/ -v

# New inference tests
.venv/Scripts/python.exe -m pytest tests/test_inference.py -v

# Frontend TypeScript
cd frontend && node node_modules/typescript/bin/tsc -b

# Frontend build
cd frontend && node node_modules/vite/bin/vite.js build

# Frontend tests (if test framework added)
cd frontend && npm test
```

---

## 10. Phase J: Required Deliverables

### 10.1 Documentation

1. `reports/phase_7_implementation_plan.md` (this file)
2. `reports/phase_7_inference_verification.md` - Verification of UCI model
3. `reports/phase_7_frontend_verification.md` - Frontend implementation verification
4. `reports/phase_7_test_report.md` - Test execution results
5. `reports/phase_7_final_report.md` - Summary of what was built

### 10.2 Code Modules

**Backend:**
- `src/inference/__init__.py`
- `src/inference/model_registry.py`
- `src/inference/predictor.py`
- `src/inference/schemas.py`
- `src/inference/explanations.py`
- `src/api/routes_inference.py` (new routes)
- `tests/test_inference.py`
- `tests/test_inference_integration.py`

**Frontend:**
- `frontend/src/PredictionForm.tsx` (new component)
- `frontend/src/PredictionResult.tsx` (new component)
- `frontend/src/ProbabilityGauge.tsx` (new component)
- `frontend/src/ROCCurve.tsx` (new component)
- `frontend/src/PRCurve.tsx` (new component)
- `frontend/src/CalibrationCurve.tsx` (new component)
- `frontend/src/FeatureImportance.tsx` (new component)
- `frontend/src/ShapExplanation.tsx` (new component)
- `frontend/tests/Prediction.test.tsx`

**Data:**
- `models/uci_taiwan_predictions.csv` (generated from test set)
- `frontend/public/data/phase_7_uci_summary.json` (UCI metrics and predictions)

### 10.3 Updated Files

**Backend:**
- `src/api/app.py` - Add new routes
- `requirements.txt` - Add any new dependencies (if needed)

**Frontend:**
- `frontend/src/App.tsx` - Add new views and integrate prediction components
- `frontend/src/App.css` - Add new styles
- `frontend/README.md` - Update setup instructions

---

## 11. Implementation Sequence

### 11.1 Phase 7.1: Inference Backend (Priority 1)

**Tasks:**
1. Create `src/inference/model_registry.py` with UCI model metadata
2. Create `src/inference/schemas.py` with Pydantic models
3. Create `src/inference/predictor.py` with prediction pipeline
4. Verify UCI model loads and predicts correctly
5. Create `src/inference/explanations.py` with SHAP integration
6. Add new API routes to `src/api/app.py`
7. Write `tests/test_inference.py`
8. Run tests and verify

**Success Criteria:**
- POST `/v1/predict` returns probability for UCI model
- All new tests pass
- Existing tests still pass (98/98)

### 11.2 Phase 7.2: UCI Model Verification (Priority 1)

**Tasks:**
1. Load UCI test set
2. Run inference on test set
3. Compute ROC-AUC, PR-AUC, and compare to historical
4. Generate per-loan prediction scores
5. Save scores to `models/uci_taiwan_predictions.csv`
6. Generate SHAP explanations for sample records
7. Verify calibration model works
8. Document results in `reports/phase_7_inference_verification.md`

**Success Criteria:**
- Test ROC-AUC matches historical (~0.78)
- SHAP explainer generates contributions
- Calibration model improves Brier score
- Verification report complete

### 11.3 Phase 7.3: Frontend Prediction UI (Priority 2)

**Tasks:**
1. Create `PredictionForm.tsx` component
2. Create `PredictionResult.tsx` component
3. Create `ProbabilityGauge.tsx` component
4. Integrate into `App.tsx` as new "Borrower Risk Prediction" view
5. Add API client functions for new endpoints
6. Test form validation
7. Test prediction flow end-to-end
8. Update `frontend/README.md`

**Success Criteria:**
- Form renders all 23 UCI fields
- Prediction displays probability and class
- Error states show helpful messages
- TypeScript compiles without errors

### 11.4 Phase 7.4: Charts and Explanations (Priority 2)

**Tasks:**
1. Create `ROCCurve.tsx` component
2. Create `PRCurve.tsx` component
3. Create `CalibrationCurve.tsx` component
4. Create `FeatureImportance.tsx` component
5. Create `ShapExplanation.tsx` component
6. Integrate into appropriate views
7. Generate curve data from prediction scores
8. Test all charts render correctly

**Success Criteria:**
- ROC curve displays with AUC
- PR curve displays with AUC
- Calibration curve displays with Brier
- SHAP waterfall displays feature contributions

### 11.5 Phase 7.5: Historical Record Explorer (Priority 3)

**Tasks:**
1. Add dataset sampling endpoint to backend
2. Create historical record selector component
3. Integrate with prediction form
4. Test loading and prediction on historical records
5. Display actual vs predicted outcomes

**Success Criteria:**
- Can load random record from UCI dataset
- Can run prediction on loaded record
- Actual outcome displays separately from prediction

### 11.6 Phase 7.6: Testing and Documentation (Priority 1)

**Tasks:**
1. Write all test files
2. Run full test suite
3. Fix any failures
4. Write verification reports
5. Write final report
6. Update README files

**Success Criteria:**
- All tests pass (existing + new)
- All documentation complete
- Frontend builds successfully
- Indian deployment readiness clearly labeled

---

## 12. Risks and Mitigations

### 12.1 Risk: UCI Model Historical Metrics Don't Match

**Likelihood:** Medium
**Impact:** High

**Mitigation:**
- Recompute metrics from scratch in Phase 7.2
- If metrics differ significantly, investigate why
- Document actual computed metrics
- Do not fabricate metrics to match historical claims

### 12.2 Risk: SHAP Explainer Fails

**Likelihood:** Low
**Impact:** Medium

**Mitigation:**
- Test SHAP with loaded model early in Phase 7.1
- If fails, use model feature importance as fallback
- Clearly label explanations as unavailable if SHAP fails
- Do not fabricate feature contributions

### 12.3 Risk: Feature Engineering Pipeline Missing

**Likelihood:** Medium
**Impact:** High

**Mitigation:**
- Check `src/feature_engineering.py` for UCI pipeline
- If missing, reconstruct from Phase 1 report
- Verify engineered features match model's expected 50 features
- Test end-to-end prediction on known record

### 12.4 Risk: Calibration Model Incompatible

**Likelihood:** Low
**Impact:** Medium

**Mitigation:**
- Test calibration model in Phase 7.1
- If fails, return uncalibrated probability
- Clearly label as "uncalibrated model score"
- Do not claim calibration without verification

### 12.5 Risk: Frontend Performance Issues

**Likelihood:** Low
**Impact:** Medium

**Mitigation:**
- Keep chart data lightweight (aggregate, not per-loan)
- Use pagination for dataset sampling
- Implement loading states
- Optimize render cycles

### 12.6 Risk: Indian Deployment Confusion

**Likelihood:** Medium
**Impact:** High

**Mitigation:**
- Add "NOT VALIDATED" banner to all views
- Clearly label geography and dataset source
- Add disclaimer to every prediction
- Do not allow arbitrary geography selection
- Keep research and production separate

---

## 13. Success Criteria

### 13.1 Must Have (Blocking)

1. ✅ Working inference pipeline for UCI Taiwan model
2. ✅ Borrower input form for UCI features
3. ✅ Actual probability returned from model (not null)
4. ✅ Prediction result displays with class and probability
5. ✅ Model and dataset provenance clearly labeled
6. ✅ Indian deployment readiness marked as NOT VALIDATED
7. ✅ All existing tests still pass (98/98)
8. ✅ New backend tests pass
9. ✅ Frontend builds successfully
10. ✅ No fabricated predictions or metrics

### 13.2 Should Have (High Priority)

1. SHAP explanations for predictions
2. ROC and PR curves from actual prediction scores
3. Calibration curve
4. Historical record explorer
5. Feature importance chart
6. Risk category badge (Low/Medium/High)
7. Model comparison view
8. Error handling with retry

### 13.3 Nice to Have (Low Priority)

1. Threshold sensitivity chart
2. Portfolio analytics for UCI dataset
3. Advanced filtering in dataset explorer
4. Monitoring dashboard (placeholder)
5. Export prediction results to CSV

---

## 14. Non-Goals (Explicitly Out of Scope)

1. ❌ Retraining LendingClub model (no artifact saved)
2. ❌ Adding Indian borrower data (not available)
3. ❌ Claiming regulatory approval
4. ❌ Production deployment readiness
5. ❌ Real-time monitoring infrastructure
6. ❌ Multiple model comparison (only one model available)
7. ❌ Advanced model selection (only UCI available)
8. ❌ Changing `/v1/score` contract (preserve for backward compatibility)

---

## 15. Timeline Estimate

**Phase 7.1 (Inference Backend):** 4-6 hours
**Phase 7.2 (UCI Verification):** 2-3 hours
**Phase 7.3 (Frontend Prediction UI):** 6-8 hours
**Phase 7.4 (Charts and Explanations):** 4-6 hours
**Phase 7.5 (Historical Explorer):** 2-3 hours
**Phase 7.6 (Testing and Documentation):** 3-4 hours

**Total Estimated Time:** 21-30 hours

---

## 16. Conclusion

Phase 7 will deliver a working ML prediction application for CreditAI using the verified UCI Taiwan XGBoost model. The application will allow users to enter borrower data, obtain actual predictions, and explore predictions through visualizations and explanations. All predictions will be clearly labeled as research-only, and Indian deployment readiness will be explicitly marked as NOT VALIDATED.

The implementation follows an evidence-first approach: only verified model artifacts are used, only actual evaluation data is displayed, and no predictions or metrics are fabricated. The existing LendingClub benchmark metrics will remain visible as historical evidence, but live inference will only be available for the UCI model.

This phase establishes the foundation for future production deployment once authorized Indian data becomes available, while maintaining clear separation between research benchmarks and production credit scoring.

---

*End of Phase 7 Implementation Plan*
