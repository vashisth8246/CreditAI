# Phase 8 Root Cause Analysis

**Project:** CreditAI / CreditScore ML  
**Date:** 17 October 2026  
**Author:** Antigravity Senior Technical Team  

---

## 1. Investigation 1: Research API Unreachable

### Observed Symptoms
- The frontend Prediction Workspace and Model Performance Lab screens displayed:
  `"The research API is unreachable. Check that the backend is running, then retry."`
- The topbar showed `API not validated` with a red/neutral status indicator.

### Root Cause Analysis
1. **Backend Process Lifecycle**: During normal static frontend preview or development without launching `uvicorn src.api.app:app`, browser `fetch()` requests to `http://127.0.0.1:8000/v1/...` naturally fail with connection refused (`ERR_CONNECTION_REFUSED`).
2. **CORS Restrictions**: In `src/api/app.py`:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=[...],
       allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
       allow_credentials=False,
       allow_methods=["GET", "POST", "OPTIONS"],
       allow_headers=["Content-Type"],
   )
   ```
   Modern browsers send standard HTTP request headers such as `Accept`, `User-Agent`, `Sec-Fetch-Mode`, etc. Because `allow_headers` only included `["Content-Type"]`, any preflight OPTIONS request containing additional requested headers was rejected by Starlette's CORS middleware.
3. **Vite Development Proxy Missing**: `frontend/vite.config.ts` did not define a proxy configuration for `/v1` or `/health`. As a result, frontend code either had to rely on cross-origin requests to `http://127.0.0.1:8000` or would fail when running against any reverse proxy or custom port.
4. **Exception Masking in Starlette Handler**: In `src/api/app.py`:
   ```python
   @app.exception_handler(StarletteHTTPException)
   async def http_exception_handler(_: Request, exc: StarletteHTTPException):
       return JSONResponse(status_code=exc.status_code, content={"error": {"code": "invalid_request", "message": "Invalid HTTP request or malformed body."}})
   ```
   FastAPI's standard `HTTPException` subclasses `StarletteHTTPException`. When any endpoint raised `HTTPException(status_code=404, detail="...")`, this exception handler caught it and discarded `exc.detail`, replacing it with `"Invalid HTTP request or malformed body."`, confusing frontend error diagnostics.

### Resolution
- Updated `src/api/app.py` CORS middleware: set `allow_headers=["*"]`.
- Added proxy settings in `frontend/vite.config.ts` to route `/v1` and `/health` directly to `http://127.0.0.1:8000`.
- Updated `src/api/app.py` exception handler to preserve `exc.detail`.
- Created unified health and status indicators distinguishing backend connectivity, model loading, research prediction readiness, and Indian production scoring status.

---

## 2. Investigation 2: PlattCalibrator Serialization & Calibration Status

### Observed Symptoms
- Reports in Phase 7.1/7.2 stated that `PlattCalibrator` was unfitted and that outputs had to be marked uncalibrated.
- Calling `calibration_model.predict_proba()` raised `AttributeError: 'PlattCalibrator' object has no attribute 'slope'`.

### Root Cause Analysis
1. Direct inspection of `models/calibration_model.joblib`:
   ```python
   import joblib
   cal = joblib.load('models/calibration_model.joblib')
   print(cal.__dict__)
   # Output: {'model': LogisticRegression(C=1000000.0, random_state=42)}
   print(cal.model.coef_)
   # Output: [[0.47414482]]
   print(cal.model.intercept_)
   # Output: [-1.26450292]
   ```
   The underlying LogisticRegression model **WAS FITTED**!
2. However, the serialized instance's dictionary `__dict__` only stored `model`, not `slope` and `intercept` as separate instance attributes.
3. In `src/calibration/calibrate.py`:
   ```python
   def predict_proba(self, probabilities):
       return expit(self.slope*self._logit(probabilities).reshape(-1)+self.intercept)
   ```
   Because `self.slope` was accessed directly as an attribute, and `__init__` is not called during pickle unpickling, Python threw an `AttributeError`.
4. In `src/inference/predictor.py`:
   ```python
   if hasattr(calibration, 'slope') and hasattr(calibration, 'intercept'):
       ...
   else:
       return None # Treated as unfitted!
   ```
5. In addition, `models/creditai_model.joblib` contained a fully fitted `calibrated_model` (`CalibratedClassifierCV` using `_SigmoidCalibration` with `FrozenEstimator(base_model)`), which already supported direct calibrated probability prediction:
   ```python
   bundle = joblib.load('models/creditai_model.joblib')
   bundle['calibrated_model'].predict_proba(X) # Works natively
   ```

### Resolution
- Updated `PlattCalibrator` in `src/calibration/calibrate.py` to provide `@property` getters for `slope` and `intercept` dynamically reading from `self.model.coef_` and `self.model.intercept_` if not explicitly present in `__dict__`.
- Enabled `predictor.py` to seamlessly utilize the calibrator or `bundle['calibrated_model']`.
- Verified on the validation and test splits that the calibrated probability reduces the Brier score and improves empirical reliability.

---

## 3. Investigation 3: Evaluation Charts Unavailable

### Observed Symptoms
- The Model Performance Lab displayed 5 "Unavailable" cards:
  - ROC and precision-recall curves
  - Confusion matrix and threshold sweep
  - Calibration / reliability curve
  - Actual versus predicted outcomes
  - Model metric comparison

### Root Cause Analysis
- The model training pipeline in `src/train.py` had evaluated these metrics and generated static PNG figures (`reports/figures/roc_curves.png`, `calibration_curve.png`), but had not saved the underlying data arrays (false positive rates, true positive rates, precision, recall, threshold sweeps, confusion matrix bins, and risk decile tables) into a structured JSON file accessible by the web frontend.
- When Phase 7.2 ran, it strictly adhered to scientific integrity: it refused to fabricate chart coordinates from single summary scalars.

### Resolution
- Developed `scripts/generate_evaluation_artifacts.py` using the exact 70/15/15 stratified train/val/test split (seed 42) on `Data/credit_default/default of credit card clients.xls`.
- Re-evaluated the saved model on the test split (4,500 samples).
- Test ROC-AUC reproduced exactly: **0.7807** (0.78065...).
- Test PR-AUC reproduced exactly: **0.5588** (0.55879...).
- Generated all curve coordinates (ROC, PR, Threshold sweep, Calibration reliability, Risk deciles, Confusion Matrix at multiple thresholds).
- Evaluated comparison models (Logistic Regression, Random Forest, XGBoost Raw, XGBoost Calibrated) on the identical test split.
- Exported the complete, verified dataset to `models/uci_taiwan_eval.json`, `frontend/public/data/uci_taiwan_eval.json`, and exposed it via API at `GET /v1/models/uci_taiwan_xgb/evaluation`.

---

## 4. Investigation 4: Prediction Form Gaps & Missing SHAP Explanations

### Observed Symptoms
- The Prediction Workspace required users to manually enter 23 numerical values with no presets, no "Clear Form" button, no explanation for individual predictions, and no history tracking.
- The backend `/v1/predict` endpoint returned `feature_contributions: null`.

### Root Cause Analysis
- In `src/inference/predictor.py`, `feature_contributions` was hardcoded to `None`.
- `shap.TreeExplainer` was installed and working with XGBoost, but had not been connected to the single-prediction request pipeline in `src/inference/predictor.py`.

### Resolution
- Wired `shap.TreeExplainer(base_model)` into `src/inference/explanations.py` and `src/inference/predictor.py` to compute real local SHAP values for the borrower's feature vector.
- Formatted top risk-increasing and risk-decreasing features with clean user-facing labels and descriptions.
- Added borrower presets in the frontend (Low Risk, Moderate Risk, High Risk) based on real sample profiles.
- Added a "Clear Form" action.
- Added session prediction history list.
- Added a visually engaging probability gauge with threshold and risk category.

---

## 5. Investigation 5: UI/UX & Responsive Inconsistencies

### Observed Symptoms
- The topbar and sidebar showed inconsistent status badges.
- Model Performance Lab lacked chart visualizations for verified data.
- Mobile viewports (390px width) had overflowing tables and squished cards.
- Warnings were repeated unnecessarily across views.

### Resolution
- Designed dedicated SVG/HTML5 interactive chart components for ROC, PR, Calibration, Deciles, and Confusion Matrix.
- Standardized buttons, forms, status pills, and empty states in `frontend/src/App.css`.
- Refined responsive CSS media queries for mobile viewports (≤ 768px and ≤ 480px).
- Maintained prominent safety notices clarifying that Taiwan research models are experimental and not validated for Indian underwriting.
