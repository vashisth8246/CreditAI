# Phase 7.2 Frontend Verification

**Date:** 17 October 2026

## Styling root cause and repair

The entry point correctly imports `index.css`, `App.tsx` correctly imports `App.css`, and Vite compiled CSS. The failure was a truncated `App.css`: it was 1,269 bytes and contained only a few ending utility/modal rules, leaving almost all JSX selectors without styles. The global stylesheet was valid. Vite/PostCSS/Tailwind configuration was not responsible; the project does not use Tailwind. Replaced the incomplete app stylesheet with the missing shell, navigation, layout, card, chart, state, input, accessibility, and responsive rules.

## Browser checks

- Opened the live Vite application in the in-app browser and visually inspected the executive overview at desktop width. The sidebar, wide content area, hero, alert, KPI cards, and dashboard grid were styled and aligned.
- Opened Borrower Risk Prediction; the backend returned the registered `uci_taiwan_xgb` model and all 23 supported raw inputs.
- Submitted the documented synthetic schema example to the local `/v1/predict` endpoint through the UI. The page displayed the actual backend response, including class, 6.0% **uncalibrated model score**, 0.50 threshold, risk category, timestamp, Taiwan/DS003 provenance, and calibration status. This synthetic check is not a real borrower prediction.
- Opened Model Performance Lab and verified its real global feature-importance bars and explicit unavailable states.
- Set the browser to 390 × 844 and inspected the performance page and prediction form. The content collapsed to a single column and the nav remained horizontally scrollable. Reset the viewport afterward.
- The first browser attempt exposed missing local-development CORS behavior. Added a loopback-only origin rule; the model schema and prediction then loaded successfully.

## Remaining frontend limits

There is no backend historical-example route, so no prefilled borrower example is offered. SHAP is not integrated in the prediction response, and the UI reports record-level explanations unavailable. Navigation, invalid-input, and retry behavior are implemented; a dedicated browser-driven invalid-input run is not recorded here.
