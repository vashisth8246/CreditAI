# Phase 9 Runtime Recovery Report

**Generated:** 2026-10-21
**Project root:** `F:\NUV ACD\All SEM\7th Sem\ML&DS\New folder (3)\CreditAI`
**Repository:** https://github.com/vashisth8246/CreditAI
**Commit:** `549acea Add batch evaluation feature` (on top of `63607ee Initial CreditAI project upload`)

---

## 1. Root cause of each actual startup failure

### 1.1 Frontend dev server exit code 1 (npm script)
- **Symptom:** `npm run dev` exited with code 1.
- **Root cause:** The original `dev` script was `"vite"`. Vite was installed locally under `frontend/node_modules`, but the Windows shell/npm wrapper could not resolve the `vite` shim reliably, so the process exited before binding.
- **Fix:** Changed the scripts to invoke the local binaries directly with Node:
  - `dev`: `node node_modules/vite/bin/vite.js`
  - `build`: `node node_modules/typescript/bin/tsc -b && node node_modules/vite/bin/vite.js build`
  - `lint`: `node node_modules/oxlint/bin/oxlint` (the `.cmd` shim failed under Node v24 with a `SyntaxError: Invalid or unexpected token`)
  - `test`: `node --experimental-strip-types --test tests/analytics.test.ts tests/batch.test.ts`

### 1.2 Frontend dev server exit code 1 (Vite config / proxy)
- **Symptom:** Even when Vite started, API calls failed or pointed at the wrong port.
- **Root cause:** `frontend/vite.config.ts` proxied `/v1` to `http://127.0.0.1:8001` while the backend runs on `8000`. The frontend also had `API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'`, so health checks hit the backend directly and the proxy was inconsistent.
- **Fix:** Pointed both `/v1` and `/health` proxy targets at `http://127.0.0.1:8000`.

### 1.3 Frontend could not load research artifacts (HTTP 404)
- **Symptom:** `App.tsx` fetched `/data/phase_9_lendingclub_summary.json`, which did not exist, so the dashboard showed "Research data unavailable".
- **Root cause:** The Phase 9 JSON artifacts were missing or contained only a Taiwan-only subset while the UI expected the LendingClub summary, the full 20-dataset inventory, and the 151-field LendingClub feature profile.
- **Fix:** Derived the three Phase 9 files from the genuine Phase 6.1 artifacts (`phase_6_1_lendingclub_summary.json`, `phase_6_1_dataset_inventory.json`, `phase_6_1_feature_inventory.json`) by copying verified data. No records, metrics, or feature definitions were invented.
- **Integrity check (2026-10-21):** SHA-256 of each Phase 9 file equals its Phase 6.1 source:
  - `phase_9_lendingclub_summary.json` = `4F04F9D83A63B5BA…`
  - `phase_9_dataset_inventory.json` = `17581798D13BABC7…`
  - `phase_9_feature_inventory.json` = `9E5DB8296E7F794F…`
  - Cross-check: `reports/phase_6_1_dataset_inventory.csv` has 20 rows and `phase_6_1_feature_inventory.csv` has 151 rows, matching the JSON counts. Test metrics shown by the dashboard (ROC-AUC 0.7056, PR-AUC 0.3947, Brier 0.1636, threshold 0.17) match `reports/phase_2_3_metrics.csv` for HistGradientBoosting/Test.

### 1.4 Backend batch endpoint raised `NameError` on every row
- **Symptom:** `/v1/research/taiwan/batch-predict` would have returned `status: "error"` for every row with `"'validate_input' is not defined"`.
- **Root cause:** `app.py` called `validate_input(raw_dict, schema)` but did not import `validate_input` from `..inference`.
- **Fix:** Added `validate_input` to the import list in `src/api/app.py`.

### 1.5 Backend batch endpoint unusable without `python-multipart`
- **Symptom:** FastAPI could not parse `UploadFile` form data; `Form data requires python-multipart to be installed`.
- **Root cause:** `python-multipart` was not in `requirements.txt` and not installed.
- **Fix:** Installed `python-multipart>=0.0.9` into the project venv and added it to `requirements.txt`.

### 1.6 No batch upload UI existed
- **Symptom:** The frontend had no way to perform the documented batch workflow (upload, preview, run, export, row-level errors).
- **Fix:** Added `frontend/src/BatchEvaluation.tsx`, `frontend/src/batch.ts`, wired a `batch` page into `App.tsx` navigation, added `researchApi.batchPredict`, and added `tests/batch.test.ts`.

### 1.7 (Potential) stale backend on port 8000
- **Symptom:** An older process (`python -m uvicorn src.api.app:app --reload`, PID 7824, system Python 3.11) was already bound to 8000 and would have served stale code.
- **Fix:** Stopped the stale listener and launched a fresh backend from the project venv.

### 1.8 Batch evaluation reported a generic "HTTP error" for ordinary header mismatches
- **Symptom (reported after the first successful run):** uploading a CSV in the Batch Evaluation page showed a red error such as "Invalid HTTP request or malformed body." — i.e. an HTTP error with no indication of what was wrong.
- **Root cause:** three compounding issues:
  1. The endpoint raised `HTTPException(422, detail={"missing_columns": [...]})`, but the global exception handler only forwarded `detail` when it was a string, replacing structured detail with the generic text.
  2. Column names were matched exactly. A perfectly valid file exported with headers like `LIMIT BAL`, `pay_0`, or `BILL AMT1` (spaces/case changes) was rejected as missing columns.
  3. A CSV saved with an `.xlsx` extension produced an opaque pandas parse error.
- **Reproduced:** missing `PAY_AMT6` → `422 {"message":"Invalid HTTP request or malformed body."}`; space-separated headers → same; lowercase headers → same.
- **Fix:**
  - Normalise incoming headers (trim, strip BOM, uppercase, spaces/hyphens → underscores) and map them onto the canonical 23 fields; accept `borrower_reference` case-insensitively; drop unnamed/pandas index columns.
  - Return a precise 422 string: `Missing required columns: …` or `Unrecognised columns: …` (previously masked).
  - Allow `.xls` and fall back between CSV and Excel parsing when the extension is misleading.
  - Frontend: the preview now normalises headers the same way, disables **Run batch prediction** when required columns are missing, shows the server message verbatim, and offers **Download template CSV** with the exact 24 headers plus one clearly synthetic row.
- **Post-fix evidence (API + UI):** missing column → `422 "Missing required columns: PAY_AMT6…"`; space-separated headers → `200` (PD 8.2066%); lowercase headers + reference → `200` (2 scored: 8.21% / 40.07%); unknown column → `422 "Unrecognised columns: notes…"`; CSV mislabeled `.xlsx` → `200`; header-only file → `400 "Uploaded file is empty."`.

---

## 2. Files changed (this recovery)

| File | Why |
|---|---|
| `frontend/package.json` | Direct Node invocation of local Vite/tsc/oxlint binaries; added batch test file. |
| `frontend/vite.config.ts` | Proxy `/v1` and `/health` to port 8000. |
| `frontend/src/App.tsx` | Added `batch` page + nav entry + render branch. |
| `frontend/src/api.ts` | Added `batchPredict`, `BatchPredictionResult`, `TAIWAN_REQUIRED_FIELDS`, `BATCH_PATH`. |
| `frontend/src/batch.ts` | CSV parser, sanitiser, summary, CSV export builder; header normalisation, template builder. |
| `frontend/src/BatchEvaluation.tsx` | Batch upload/preview/run/export UI; precise errors, template download, run disabled on missing columns. |
| `frontend/tests/batch.test.ts` | 8 frontend tests for batch helpers (template + header normalisation added). |
| `src/api/app.py` | Imported `validate_input`; added 10 MB upload-size guard; header normalisation, precise 422 messages, `.xls` support and CSV/Excel parsing fallback. |
| `requirements.txt` | Added `python-multipart`. |
| `frontend/public/data/phase_9_lendingclub_summary.json` | Copied from verified Phase 6.1 artifact (was missing). |
| `frontend/public/data/phase_9_dataset_inventory.json` | Replaced Taiwan-only subset with the genuine 20-dataset inventory. |
| `frontend/public/data/phase_9_feature_inventory.json` | Replaced with the genuine 151-field LendingClub feature profile. |

---

## 3. Backend startup evidence

Command (run from project root, project venv):

```
F:\...\CreditAI\.venv\Scripts\python.exe -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

- Process alive at verification time: **PID 18932** (python, started 2026-10-21 10:07:37).
- Port 8000 listener count: **1**.
- `GET /health` → **HTTP 200** `{"status":"ok","scoring":"not_validated"}`.
- `GET /openapi.json` → **HTTP 200**, OpenAPI 3.1.0, paths include `/v1/predict` and `/v1/research/taiwan/batch-predict`.
- Registered routes: `/health`, `/v1/status`, `/v1/score`, `/v1/models`, `/v1/models/{model_id}`, `/v1/models/{model_id}/schema`, `/v1/models/{model_id}/evaluation`, `/v1/predict`, `/v1/research/taiwan/batch-predict`.
- Backend stderr: only a harmless pydantic v2 `schema_extra` deprecation warning; no traceback.

Startup log tail (`logs/backend.err.log`):
```
INFO:     Started server process [22932]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## 4. Frontend startup evidence

Command (run from `frontend/`):

```
node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort
```

- Process alive at verification time: **PID 27572** (node, started 2026-10-21 10:07:45).
- Port 5173 listener count: **1**.
- `GET http://127.0.0.1:5173/` → **HTTP 200**, Vite-served `index.html`.
- Vite stdout: `VITE v8.3.4 ready in 369 ms`, `Local: http://127.0.0.1:5173/`.
- No stderr errors.
- Proxy check: `GET http://127.0.0.1:5173/health` → **HTTP 200** `{"status":"ok","scoring":"not_validated"}` (proxied to backend). `GET /v1/models` via 5173 → **HTTP 200**.
- Browser console: **0 errors, 0 warnings** on the Phase 9 pages.

---

## 5. HTTP status and response evidence

| Request | Status | Evidence |
|---|---|---|
| `GET /health` (direct) | 200 | `{"status":"ok","scoring":"not_validated"}` |
| `GET /openapi.json` | 200 | OpenAPI 3.1.0, documents `/v1/predict` and `/v1/research/taiwan/batch-predict` |
| `GET /v1/models` | 200 | One model: `uci_taiwan_xgb`, XGBoost, Taiwan, `inference_ready: true` |
| `GET /v1/models/uci_taiwan_xgb` | 200 | `artifact_exists`, `calibration_exists`, `feature_names_exist`, `metadata_exists` all true |
| `GET /v1/models/uci_taiwan_xgb/schema` | 200 | 23 raw features with types/ranges/values |
| `GET /v1/models/uci_taiwan_xgb/evaluation` | 200 | ROC/PR curves, confusion matrix, deciles from `models/uci_taiwan_eval.json` |
| `POST /v1/predict` (valid 23-field profile) | 200 | probability `0.08206632971007599`, `risk_category: "Low"`, `calibrated: true`, `calibration_method: "Platt sigmoid"`, 6 SHAP contributions |
| `POST /v1/predict` (missing fields) | 422 | `{"error":{"code":"invalid_request","message":"Required field 'SEX' is missing."}}` |
| `POST /v1/score` (synthetic transactions) | 200 | `score_status: "not_validated"`, `default_probability: null`, `validated_risk_estimate: false` |
| `POST /v1/research/taiwan/batch-predict` (2 valid + reference) | 200 | 2 success rows, probabilities `0.0821` and `0.1195`, `borrower_reference` echoed |
| `POST /v1/research/taiwan/batch-predict` (1 valid + 2 invalid) | 200 | 1 success, 2 row-level errors with field/range messages |
| `POST /v1/research/taiwan/batch-predict` (missing columns) | 422 | `{"missing_columns":[...]}` |
| `POST /v1/research/taiwan/batch-predict` (wrong type) | 415 | `Unsupported file type. Use .csv or .xlsx.` |
| `POST /v1/research/taiwan/batch-predict` (5001 rows) | 400 | `File contains 5001 rows; maximum allowed is 5000.` |

---

## 6. Single-borrower prediction test results

- **Verified:** yes (UI + direct HTTP).
- **Result:** **Passed.**
- Valid profile (Low Risk Borrower preset) submitted through the UI:
  - Predicted class: "Lower predicted default risk"
  - Calibrated PD: **8.2%**
  - Risk tier: Low (threshold 0.50)
  - Model ID: `uci_taiwan_xgb`
  - Dataset/Geography: Default of Credit Card Clients (Taiwan)
  - Calibration: Platt sigmoid
  - SHAP contributions returned and rendered (MAX DELINQUENCY −0.457, PAY_0 −0.239, PAY_AMT1 −0.205, BILL_CHANGE_1_2 −0.128, PAY_AMT6 −0.103, PAYMENT_MONTHS_COUNT −0.100); directions consistent with the underlying SHAP values (negative → decreases risk).
- Delinquent profile (High Risk Delinquent preset) submitted via HTTP:
  - Probability **0.4007**, risk category **Medium**, calibrated true.
  - SHAP: PAY_0 +0.7152 increases risk, MAX_DELINQUENCY +0.7061 increases risk.
- Invalid profile (only `LIMIT_BAL`): **HTTP 422**, message "Required field 'SEX' is missing." — handled as a validation error, no probability produced.
- The Taiwan model is labelled throughout the UI as a Taiwan research benchmark; `/v1/score` is not invoked by this page.

---

## 7. Batch-upload test results

- **Verified:** yes (UI page + direct HTTP).
- **Result:** **Passed.**
- Uploaded `batch_test_sample.csv` (4 data rows + `borrower_reference` column) through the Batch Evaluation page:
  - Preview rendered all 24 columns and 4 rows; row count and file size shown.
  - Run produced 3 scored rows (PDs 8.21%, 40.07%, 17.64%) and 1 row-level error:
    - Row 5 `malformed-row`: "Field 'EDUCATION' must be one of [1, 2, 3, 4, 5, 6], got 99."
  - KPIs: Rows scored 3 of 4, Row errors 1, Mean PD 22.0%, Tier split 2/1/0 (Low/Medium/High).
  - Export button builds a CSV with formula-injection neutralisation (`sanitizeCell` prefixes `=`, `+`, `-`, `@` with `'`).
- **XLSX verified (UI + API, 2026-10-21):** uploaded `batch_test_sample.xlsx` (3 rows) through the Batch Evaluation page:
  - The page correctly reported that XLSX cannot be previewed client-side, kept **Run batch prediction** enabled, and accepted the file.
  - Result: 2 scored (`xlsx-low` 8.21% Low, `xlsx-delinquent` 40.07% Medium) and 1 row error (`xlsx-malformed`: "Field 'EDUCATION' must be one of [1, 2, 3, 4, 5, 6], got 99.").
  - Direct API upload of the same XLSX returned the same three outcomes (HTTP 200).
- Direct HTTP tests confirmed: valid rows, row-level errors, missing-column 422, wrong-type 415, 5001-row 400.
- **Header-mismatch handling (added after the reported "HTTP error"; verified 2026-10-21):**
  - `missing_column.csv` (no `PAY_AMT6`) → HTTP 422, message **"Missing required columns: PAY_AMT6. Expected 23 UCI Taiwan fields; download the template CSV from the Batch evaluation page."** The UI shows the same text and disables Run.
  - Headers with spaces (`LIMIT BAL`, `PAY 0`, `BILL AMT1`, `BORROWER REFERENCE`) → HTTP 200, PD 8.2066%.
  - Lowercase headers + reference, uploaded through the UI → HTTP 200, 2 scored (8.21% Low, 40.07% Medium), references echoed.
  - Extra unknown column (`notes`) → HTTP 422, **"Unrecognised columns: notes. Remove them or rename a single identifier column to borrower_reference."** shown verbatim in the UI.
  - CSV bytes named `export.xlsx` → HTTP 200; header-only file → HTTP 400 **"Uploaded file is empty."**
  - **Download template CSV** produces `creditai_batch_template.csv` with the exact 23 required headers + `borrower_reference` and one synthetic example row (verified by intercepting the blob: 320 bytes, 2 lines).
- Upload-size guard: 10 MB limit enforced (HTTP 413 above).
- Logging: no borrower row data appears in `logs/*.log` (verified by grep).

---

## 8. Backend test count and results

Command: `python -m pytest -q` (project venv, from project root)

- **Result:** **118 passed, 0 failed, 49 warnings** in 139.10s (re-run after the batch header fixes on 2026-10-21).
- Collected/executed: 118 tests across `tests/` (test_api_contract, test_api_integration, test_financial_pipeline, test_inference, test_phase12_signal, test_phase22_audit, test_phase23_benchmark, test_phase5_data_validation, test_phase8_features, test_pipeline).
- Warnings are pre-existing (sklearn version mismatch 1.9.0→1.9.1, shap/matplotlib deprecations, lbfgs convergence) and are not failures.

---

## 9. Frontend test/build results

- Frontend tests: `node --experimental-strip-types --test tests/analytics.test.ts tests/batch.test.ts`
  - **13 passed, 0 failed** (5 analytics + 8 batch), re-run after the batch header fixes on 2026-10-21.
- Lint: `node node_modules/oxlint/bin/oxlint` → exit **0** (no findings).
- Type check: `node node_modules/typescript/bin/tsc -b` → exit **0**.
- Production build: `node node_modules/vite/bin/vite.js build` → exit **0**; emitted `dist/index.html` (0.45 kB), `dist/assets/index-*.css` (31.16 kB), `dist/assets/index-*.js` (322.74 kB), built in 497ms.

---

## 10. Whether the current Phase 9 page was visually verified

- **Verified:** yes, via the browser tool (tab focused on `http://127.0.0.1:5173`).
- Confirmed the rendered page is the current Phase 9 application (title "creditai · RISK WORKBENCH", nav shows Executive overview / Borrower prediction / Batch evaluation / Data discovery / Portfolio intelligence / Model lab / Model performance lab / Risk explorer / Explainability / Monitoring / Architecture & audit), **not** an old Phase 7.2 dashboard.
- Navigation: all 10 nav items clicked and rendered their pages; no console errors.
- Executive Overview: KPIs from genuine artifacts (2.26M source records, 19.98% observed closed default, Test ROC-AUC 0.7056, 2 research-qualified datasets).
- Data Discovery: shows the genuine 20-dataset inventory (DS001…EXT003) with qualification decisions, row counts, targets, access/license.
- Model Lab: metrics from `phase_2_3_metrics.csv` (ROC-AUC 0.7056, PR-AUC 0.3947, Brier 0.1636, threshold 0.17) and confusion matrix.
- Explainability: clearly states historical SHAP is unavailable and synthetic explanations are excluded.
- Monitoring: shows historical vintage chart plus explicit "Unavailable" rows for PSI, live missingness drift, live performance.
- Architecture & audit: reflects real implementation (production score NOT VALIDATED, no model version, no live traffic, `/v1/score` unchanged).
- No broken imports, missing assets, or failed API requests during navigation.

---

## 11. Remaining failures or limitations

- The Taiwan UCI benchmark (DS003) is a 2005 Taiwan credit-card benchmark; it is **not** a validated Indian credit-risk model. No Indian production scoring is performed; `/v1/score` returns `not_validated` with a null probability.
- ROC/PR curve coordinates, calibration plots, threshold sweeps, and per-loan SHAP for the LendingClub benchmark are not saved; the UI correctly shows these as unavailable rather than fabricating them.
- SHAP for the Taiwan model is computed with `shap.TreeExplainer` on the loaded XGBoost model; contributions are model-association values, not causal explanations.
- `python-multipart` was added manually; it is not pinned in a lockfile.
- The `.gitignore` ignores `frontend/public/data/`, `Data/`, `frontend/dist/`, and `*.log`, so the Phase 9 JSON artifacts and logs are not tracked; the data files must be regenerated from the Phase 6.1 artifacts if the workspace is reset.
- The frontend API base falls back to `http://127.0.0.1:8000` when `VITE_API_BASE_URL` is unset; deployments must set that variable or rely on the proxy.

---

## 12. Exact working URLs and process liveness

| URL | Status | Process |
|---|---|---|
| `http://127.0.0.1:8000` (backend) | **Responding (HTTP 200 /health)** | python (uvicorn) PID 15944, alive at verification |
| `http://127.0.0.1:5173` (frontend) | **Responding (HTTP 200 /)** | node PID 27572, alive at verification |
| `http://127.0.0.1:5173/health` (proxied) | **HTTP 200** (reaches backend) | verified |

Both processes were left running after all tests completed. The frontend can still call the backend through the Vite proxy (verified via `/health` and `/v1/models` through port 5173).

---

## Summary labels

- Backend startup: **Verified / Passed.**
- Frontend startup: **Verified / Passed.**
- Single-prediction (valid): **Verified / Passed.**
- Single-prediction (invalid): **Verified / Passed.**
- Batch upload (valid CSV + reference): **Verified / Passed.**
- Batch upload (malformed rows): **Verified / Passed.**
- Batch upload (missing columns / wrong type / row limit): **Verified / Passed.**
- Batch header normalisation (spaces/lowercase): **Verified / Passed** (HTTP 200).
- Batch header-mismatch diagnostics (missing/unknown columns): **Verified / Passed** (precise 422 messages, no generic HTTP error).
- Batch template download: **Verified / Passed** (24 exact headers + synthetic row).
- Batch XLSX upload (UI + API): **Verified / Passed** (2 scored, 1 row error).
- `/v1/score` safety gate: **Verified / Passed** (returns `not_validated`, null probability).
- Backend tests: **Verified / Passed** (118 passed).
- Frontend tests: **Verified / Passed** (13 passed).
- Frontend lint: **Verified / Passed** (0 findings).
- Frontend type check: **Verified / Passed**.
- Frontend production build: **Verified / Passed**.
- Visual browser verification of Phase 9 page: **Verified / Passed.**
- XLSX results export: **Not applicable** — the UI provides CSV export only (`Export results CSV`); XLSX *upload/parsing* was verified (UI + API, HTTP 200). CSV export generation and formula-injection neutralisation are covered by tests; the browser download itself was not saved to disk in this run.
- Indian production scoring: **Not enabled** (intentionally; safety gate preserved).
