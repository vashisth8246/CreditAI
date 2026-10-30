# Phase 9 — Session 6: Verification Report

**Date:** 2026-10-22
**Project:** `F:\NUV ACD\All SEM\7th Sem\ML&DS\New folder (3)\CreditAI`
**Git commit:** `549acea727b19fedc37697a5d8bce1a9b9b69d05`
**Purpose:** Record the commands, environment, raw results and reachability evidence used to accept the batch workflow.

---

## 1. Acceptance summary

| Gate | Result |
|---|---|
| Backend full suite | **138 passed**, 0 failed |
| Backend batch suite | **20 passed**, 0 failed |
| Frontend tests | **26 passed**, 0 failed |
| Frontend production build | **success**, 25 modules |
| Frontend lint | **exit 0**, no findings |
| Live API contract | **38 / 38 checks passed** |
| Browser CSV flow | Complete: 4/6 scored, 2 failed, exports verified |
| Browser multi-sheet XLSX flow | Complete: 4/5 scored across 2 sheets, exports verified |
| Single prediction | `200`, calibrated probability returned |
| Dashboard pages | 9 navigation pages load without application errors (prior session evidence) |
| `/v1/score` gate | `not_validated`, null probability |
| Servers reachable after tests | Backend health `ok`; frontend HTTP `200` |

No gate was waived. The two residual gaps (`.xls` untested, header-only direct predict returns empty `200`) are documented limitations, not failures of a claimed capability.

---

## 2. Environment

| Item | Value |
|---|---|
| OS | Windows (win32) |
| Working tree | `F:\NUV ACD\All SEM\7th Sem\ML&DS\New folder (3)\CreditAI` |
| Python | 3.11.9 |
| Virtual environment | `.venv` |
| Node.js | v24.13.1 |
| npm | 11.8.0 |
| scikit-learn | 1.9.1 runtime; artifacts pickled with 1.9.0 |
| Backend | `uvicorn src.api.app:app --host 127.0.0.1 --port 8000` |
| Frontend | `node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort` |

Running processes observed during verification:

```text
PID 22460  .venv\Scripts\python.exe  -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
PID  5548  C:\...\Python311\python.exe -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
PID 14536  E:\Nodejs\node.exe node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort
```

PID 5548 is the base interpreter re-executed by the Windows venv launcher for PID 22460; it is not a second independently configured server. Only one process owns port 8000.

The live verification script was launched with the **system** Python because the venv does not contain the `requests` package:

```powershell
python C:\Users\Admin\AppData\Local\Temp\opencode\verify_live.py
```

It performs HTTP calls only; project code was executed by the running server, not by the script.

---

## 3. Commands and raw results

### 3.1 Backend full suite

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Result:

```text
138 passed, 55 warnings in 147.19s (0:02:27)
```

Log: `logs/pytest_session6.out.log`.

The 55 warnings are pre-existing: `ConvergenceWarning` from logistic-regression fits in pipeline tests and serialization/version warnings. No warning was promoted to an error and no test failed.

### 3.2 Backend batch suite

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_batch_workflow.py -q
```

Result:

```text
20 passed
```

This is the dedicated batch service/API suite; the full run above includes these 20.

### 3.3 Frontend tests

```powershell
cd frontend
npm test
```

Result:

```text
ℹ tests 26
ℹ suites 1
ℹ pass 26
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 900.2948
```

The script runs `tests/analytics.test.ts` (5 dashboard tests) and `tests/batch.test.ts` (21 batch tests). Log: `logs/fetest_session6.out.log`.

### 3.4 Frontend build

```powershell
npm run build
```

Result:

```text
✓ 25 modules transformed.
dist/index.html                   0.45 kB │ gzip:   0.29 kB
dist/assets/index-CFUlQD37.css   49.68 kB │ gzip:  11.21 kB
dist/assets/index-CuVOo2an.js   368.70 kB │ gzip: 105.52 kB
✓ built in 664ms
```

Log: `logs/build_session6.out.log`. The TypeScript project build (`tsc -b`) completed before Vite and emitted no diagnostics.

### 3.5 Frontend lint

```powershell
npm run lint
```

Result: oxlint exited `0` with no findings. Log: `logs/lint_session6.out.log` (npm preamble only, no diagnostics).

### 3.6 Live API contract

```powershell
python C:\Users\Admin\AppData\Local\Temp\opencode\verify_live.py
```

Result:

```text
SUMMARY: 38 passed / 38 checks
```

Log: `logs/verify_live_session6.out.log`. The 38 checks cover health, CSV inspect/predict, multi-sheet XLSX inspect/predict, XLSX/CSV exports, injection protection, `/v1/score`, single prediction, invalid category, missing column, header-only, corrupt XLSX and unsupported type.

### 3.7 Brier diagnostic

```powershell
.\.venv\Scripts\python.exe C:\Users\Admin\AppData\Local\Temp\opencode\brier_diagnostic.py
```

Result (values identical to the earlier run; sklearn patch level advanced from 1.9.0 to 1.9.1):

```text
test n 4500 defaults 996 prevalence 0.22133333333333333
shipped calibrator slope/intercept 0.47414481616618126 -1.2645029152597382
raw test Brier            0.17094272375106812
shipped test Brier        0.14412179090099117
shipped validation Brier  0.14428136715781856
sklearn sigmoid val Brier  0.1363537801926592
sklearn sigmoid test Brier 0.13602025323997152
```

The process exit code was `1` only because PowerShell surfaces a scikit-learn version warning written to stderr as a native-command error. The JSON artifact was written completely; see `C:\Users\Admin\AppData\Local\Temp\opencode\brier_diagnostic.json` and `logs/brier_diagnostic_session6.out.log`.

---

## 4. Live endpoint checks

### 4.1 Health and status

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/v1/status
```

Observed:

```json
{"status":"ok","scoring":"not_validated"}
{"backend_connectivity":"connected","models_registered":1,"research_inference_ready":true,"indian_production_scoring":"not_validated"}
```

### 4.2 `/v1/score` remains gated

A syntactically valid transaction payload was sent (not an empty body):

```json
{
  "schema_version": "1.0",
  "observation_start": "2025-01-01",
  "prediction_date": "2025-07-01",
  "request_id": "session6-check",
  "transactions": [
    {
      "transaction_id": "t1",
      "date": "2025-02-01",
      "transaction_type": "credit",
      "amount": 50000,
      "category": "salary"
    }
  ]
}
```

Response:

```json
{
  "score_status": "not_validated",
  "score_type": "none",
  "default_probability": null,
  "validated_risk_estimate": false,
  "model_version": null,
  "timestamp": "2026-10-22T10:57:39.804698+00:00",
  "provenance": {"source": "no_validated_model", "synthetic_demo": false},
  "request_id": "session6-check",
  "message": "No validated CreditAI model is available; no risk score was produced."
}
```

### 4.3 Single prediction

```json
{
  "model_id": "uci_taiwan_xgb",
  "probability": 0.08206632971007599,
  "risk_category": "Low",
  "threshold": 0.5,
  "calibrated": true,
  "calibration_method": "Platt sigmoid",
  "prediction_timestamp": "2026-10-22T10:58:10.923251+00:00"
}
```

Six feature contributions were returned; the top contribution was `MAX_DELINQUENCY` (`decreases_risk`). This confirms the single-borrower path and SHAP payload still work after the batch changes.

### 4.4 Batch endpoints

The 38-check script exercised:

- `POST /v1/research/taiwan/batch/inspect`
- `POST /v1/research/taiwan/batch-predict`
- `POST /v1/research/taiwan/batch/export/xlsx`
- `POST /v1/research/taiwan/batch/export/csv`

`/batch/analyze` is covered by the backend test suite (`test_analyze_explicit_mapping_accepts_spaces_and_case`, `test_analyze_duplicate_target_is_rejected_without_guessing`) and by the UI mapping-change flow.

---

## 5. Browser verification

**URL:** `http://127.0.0.1:5173/` → **Batch evaluation**.

### CSV

- Step 1: `portfolio_quirky.csv`, 819 B, CSV, 1 worksheet, Ready.
- Step 2: 6 total, 4 valid, 2 invalid, 23/23 required, 1 extra column.
- Step 3: 4 scored / 2 failed; probabilities `8.21%`, `24.82%`, `41.13%`, `8.21%`; mean `20.59%`, median `16.51%`; risk mix Low 3 / Medium 1 / High 0.
- Exports: predictions CSV, predictions XLSX, validation errors CSV and Markdown report all downloaded and opened.
- Formula reference displayed and exported as `'=cmd|calc`.

### Multi-sheet XLSX

- Step 1: four sheets listed; A and B selected.
- Step 2: separate tabs, separate mapping and validation.
- Step 3: `Portfolio A` 3/3 scored, mean 24.7%; `Portfolio B` 1/2 scored, mean 8.2%; total 4/5.
- Result rows preserved sheet name and source row; failed row carried the `EDUCATION` error.
- Charts populated from the returned summary; by-sheet chart showed both denominators.

### Fresh render after restart

The Batch Evaluation route was opened after the frontend restart and rendered Step 1 with the upload zone, progress control and research-only warning. Screenshot: `reports/figures/phase_9_session6_batch_step1.png`.

---

## 6. Console and network observations

- Successful flows produced no React runtime error and no unhandled promise rejection.
- On a fresh page load the console contained only the React DevTools development notice.
- Earlier negative tests produced deliberate `400` (header-only/corrupt) and `415` (unsupported) responses. These appear as browser network errors because 4xx responses are logged by the browser, but they were rendered as actionable UI messages and are the expected contract.
- No CORS failure was observed. The FastAPI CORS policy allows loopback origins and the Vite proxy forwards `/v1` to port 8000.
- No borrower row values appeared in server logs during verification; error handlers do not echo request bodies.

---

## 7. Repository state

`git status --short` at verification time:

```text
 M frontend/src/App.css
 M frontend/src/BatchEvaluation.tsx
 M frontend/src/api.ts
 M frontend/src/batch.ts
 M frontend/tests/batch.test.ts
 M src/api/app.py
 M src/inference/predictor.py
?? check_batch.py
?? frontend/public/batch_test_sample.xlsx
?? frontend/public/testdata/
?? frontend/src/BatchCharts.tsx
?? logs/
?? reports/phase_9_runtime_recovery_report.md
?? reports/phase_9_session6_batch_upload_report.md
?? src/api/batch_service.py
?? tests/test_batch_workflow.py
```

Plus the reports created in this session (untracked). Nothing was reset, rebased, stashed or committed. `check_batch.py` is a six-line diagnostic helper left from the parse-fix investigation; it is not imported by the application.

No historical report, model artifact or evaluation CSV was overwritten. The only source edit made in this session was the one-token syntax repair in `frontend/src/batch.ts`; the remaining source changes were inherited uncommitted work.

---

## 8. Reachability after the test runs

Final checks after the full suite, build and live script:

```text
GET http://127.0.0.1:8000/health   → 200 {"status":"ok","scoring":"not_validated"}
GET http://127.0.0.1:8000/v1/status → connected, 1 model, research inference ready
GET http://127.0.0.1:5173/        → 200 (615 bytes HTML shell)
```

The Vite dev server and backend remained up after the tests. The browser path itself was also checked through the proxy:

```text
GET http://127.0.0.1:5173/v1/status → {"backend_connectivity":"connected","models_registered":1,"research_inference_ready":true,"indian_production_scoring":"not_validated"}
GET http://127.0.0.1:5173/health   → {"status":"ok","scoring":"not_validated"}
```

The production build wrote to `frontend/dist/`; the dev server continues to serve from source, so the built assets do not affect the running session.

---

## 9. Evidence index

| Evidence | Path |
|---|---|
| Backend test log | `logs/pytest_session6.out.log` |
| Frontend test log | `logs/fetest_session6.out.log` |
| Build log | `logs/build_session6.out.log` |
| Lint log | `logs/lint_session6.out.log` |
| Live API log | `logs/verify_live_session6.out.log` |
| Brier diagnostic log | `logs/brier_diagnostic_session6.out.log` |
| Brier JSON | `C:\Users\Admin\AppData\Local\Temp\opencode\brier_diagnostic.json` |
| Calibrator comparison | `logs/brier_slope_compare.out.log` |
| Split-provenance check | `logs/brier_split_check.out.log` |
| Batch Step 1 screenshot | `reports/figures/phase_9_session6_batch_step1.png` |
| Synthetic fixtures | `frontend/public/testdata/`, `C:\Users\Admin\AppData\Local\Temp\opencode\creditai_fixtures\` |
| Exported artifacts | `C:\Users\Admin\AppData\Local\Temp\opencode\creditai_evidence\` |

---

## 10. Sign-off

- All executable test suites pass.
- The live contract checks pass against the running server, not a mock.
- The browser workflow completes for CSV and multi-sheet XLSX and exports real results.
- The production-score gate remains closed and unchanged.
- The only unverified advertised format is `.xls`, which is explicitly called out in every relevant report.
- Phase 9 batch work is verified; Phase 10 has not been started.
