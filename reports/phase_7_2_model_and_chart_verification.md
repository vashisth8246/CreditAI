# Phase 7.2 Model and Chart Verification

**Date:** 17 October 2026

## Registered research model

- **ID:** `uci_taiwan_xgb`
- **Artifact:** `models/creditai_model.joblib`; dictionary bundle containing a fitted XGBoost `base_model` and `calibrated_model` entry.
- **Dataset:** UCI Default of Credit Card Clients (DS003), Taiwan, credit-card records from April–September 2005.
- **Target:** next-month default (`1 = default`, `0 = repaid`).
- **Inputs:** 23 raw features returned by the existing model-schema endpoint; engineered features are computed server-side.
- **Inference:** verified in browser against the live local API with a documented synthetic request. The response was uncalibrated.
- **Calibration:** `models/calibration_model.joblib` deserializes as `src.calibration.calibrate.PlattCalibrator` containing a `LogisticRegression` without fitted parameters. The predictor's fitted-parameter check returns no calibrator, so raw XGBoost output is used. Registry status now says uncalibrated.
- **Record-level explanation:** unavailable. The inference response currently returns `feature_contributions: null`; no fabricated contributions are displayed.

## Chart provenance

The performance page displays the top 12 global feature importances read from the fitted artifact's native `base_model.feature_importances_`, aligned to `models/feature_names.json`. This is global model behavior, not a single-record explanation or a causal effect. The UI identifies the dataset, geography, model and that an evaluation split is not persisted with the artifact.

No prediction/label rows, split-linked scores, ROC/PR coordinates, confusion-matrix evaluation rows, threshold sweep, calibration bins, or actual/predicted evaluation cohort were found in the model artifact or inference implementation. Therefore ROC, precision–recall, confusion matrix, metric comparison, threshold sensitivity, reliability, and actual-versus-predicted charts are marked unavailable. Historical scalar metrics in the model registry are not repurposed as chart points. Evaluation must be regenerated from a reproducible split manifest before those charts can be shown.
