# Phase 9 — Final Report

**Date:** 2026-10-22
**Project:** `F:\NUV ACD\All SEM\7th Sem\ML&DS\New folder (3)\CreditAI`
**Commit baseline:** `549acea727b19fedc37697a5d8bce1a9b9b69d05` (`Add batch evaluation feature`) plus uncommitted batch work
**Scope:** Phase 9 batch evaluation workflow, single prediction, dashboard/API integration, evaluation calibration review, and verification evidence.
**Status:** **Complete for the batch workflow.** Production scoring remains deliberately disabled. Phase 10 has not been started.

---

## 1. Outcome

The Phase 9 batch evaluation feature is working end to end in the live application:

- CSV upload → inspection → mapping/validation → prediction → KPI cards → charts → results table → exports.
- Multi-sheet XLSX upload → per-sheet selection → per-sheet mapping/validation → combined prediction preserving sheet and source row → charts → exports.
- Invalid rows are returned individually with actionable messages; they are never imputed or given fabricated predictions.
- Exports are injection-safe and preserve order, reference, worksheet and source row.
- The Indian production score endpoint remains `not_validated` and returns `default_probability: null`.

The blocking failure at the start of the session was a **truncated frontend module**, not an HTTP, CORS or file-format problem. `frontend/src/batch.ts` ended with `]` where `)` was required, so the Batch Evaluation route could not load. The fix was a single-token syntax repair; no logic changed. The previously reported backend header-normalisation and error-reporting fixes were re-verified.

---

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Upload `.csv` | **Met** | Live API 38/38; browser CSV flow; 21 frontend + 20 backend batch tests |
| Upload multi-sheet `.xlsx` | **Met** | Live inspect/predict; browser Portfolio A/B flow |
| Support `.xls` | **Not claimed** | Code path exists (`xlrd`) but no `.xls` fixture was exercised |
| Three-step UI | **Met** | Step 1 upload/select, Step 2 preview/map/validate, Step 3 predict/analyse |
| Compact paginated preview | **Met** | 15 rows/page, column search, column visibility, source-row numbers |
| Explicit column mapping | **Met** | Per-column target select; duplicate/missing targets surfaced; re-validation through `/batch/analyze` |
| Validation summary | **Met** | Total/valid/invalid/warning rows; required-found; missing; extra; duplicate headers |
| Downloadable template | **Met** | 23 features + `borrower_reference` + synthetic example row |
| Downloadable validation errors | **Met** | Real row/column issues; formula-neutralised CSV |
| Batch prediction against live backend | **Met** | Real probabilities `0.0821, 0.2482, 0.4113, 0.0821` |
| KPI cards with correct denominators | **Met** | Mean/median explicitly over scored rows; risk mix denominator stated |
| Charts | **Met** | Risk distribution, histogram, cumulative, status, risk by worksheet |
| Sortable/searchable/filterable results | **Met** | Sort on 5 keys; status/risk filters; free-text search; 25 rows/page |
| CSV export | **Met** | Preserves order/sheet/source row/reference; injection-safe |
| XLSX export | **Met** | Backend `Predictions` + `Summary` sheets; 5 rows matching results |
| Report export | **Met** | Markdown with denominators, calibration, validation errors, limitations |
| No imputation of missing financial values | **Met** | `test_predict_requires_complete_mapping_and_never_imputes`; row-level failures |
| No guessed mappings | **Met** | Duplicate targets rejected; ambiguous columns reported |
| No fabricated predictions for failed rows | **Met** | Failed rows have `error_message` and no `prediction` object |
| Preserve order/reference/sheet/source row | **Met** | `test_predict_preserves_sheet_order_rows_and_references`; browser evidence |
| Formula injection protection | **Met** | `=cmd|calc` exported as `'=cmd|calc`; numeric values preserved |
| `/v1/score` remains not validated | **Met** | Live valid payload returns `score_status: not_validated`, null probability |
| Executed tests and browser evidence | **Met** | 138 backend, 26 frontend, 38 live checks, browser CSV/XLSX flows |
| Phase 10 not started | **Met** | No Phase 10 files or work |

---

## 3. Verification results

| Check | Result | Log / evidence |
|---|---|---|
| Backend full suite | **138 passed**, 0 failed, 147.19 s | `logs/pytest_session6.out.log` |
| Backend batch suite | **20 passed** | `tests/test_batch_workflow.py` |
| Frontend tests | **26 passed**, 0 failed | `logs/fetest_session6.out.log` |
| Frontend build | **success**, 25 modules, 664 ms | `logs/build_session6.out.log` |
| Frontend lint | **exit 0**, no findings | `logs/lint_session6.out.log` |
| Live API contract | **38 / 38 checks** | `logs/verify_live_session6.out.log` |
| CSV browser flow | **4/6 scored**, 2 row errors | `phase_9_session6_frontend_report.md` §5 |
| XLSX browser flow | **4/5 scored** across two sheets | `phase_9_session6_frontend_report.md` §5 |
| Single prediction | `0.08206633`, `Low`, calibrated | Live `POST /v1/predict` |
| `/v1/score` gate | `not_validated`, null probability | Live valid payload check |
| Brier reproduction | raw `0.17094`; shipped `0.14412`; sklearn `0.13602` | `phase_9_brier_discrepancy_review.md` |
| Post-test reachability | backend `ok`; frontend HTTP `200` | `phase_9_session6_verification_report.md` §8 |

No test was skipped. The only non-zero process exit in the evidence set was the Brier diagnostic being reported as `1` by PowerShell because scikit-learn wrote a version warning to stderr; the diagnostic completed and wrote its JSON. This is documented in the verification report.

---

## 4. Root causes and fixes

### 4.1 Blocking frontend failure (fixed)

`frontend/src/batch.ts`, final statement of `buildAnalysisReport`:

```ts
lines.push(
  '',
  '## Limitations',
  ...
  '- The production `/v1/score` endpoint remains disabled ...',
]   // opened with ( but closed with ]
```

This produced `SyntaxError [ERR_INVALID_TYPESCRIPT_SYNTAX]: Expression expected` at line 615. Because `BatchEvaluation.tsx` imports the module, the route failed to render. The file also showed signs of an interrupted write (earlier trailing NUL padding).

**Fix:** changed the closing token to `)`. No business logic changed. Build, lint, tests and the browser flow then passed.

### 4.2 Earlier backend upload fixes (retained and re-verified)

1. **Header normalization** — BOM, whitespace, case and separators are normalized; a match is accepted only when unique.
2. **Structured validation detail** — missing columns are returned as `missing_fields` rather than a generic malformed-body message.
3. **Format fallback** — delimited text named `.xlsx` is parsed as CSV; corrupt workbooks raise a clear `400`.

These were not re-implemented in this session; they were confirmed through the live checks and the 20-test batch suite.

### 4.3 Brier discrepancy (resolved by explanation, not by changing the model)

The Phase 1 report's `0.1360` and the Phase 9 report's `0.1441` describe two different calibrators:

- `0.1360` — sklearn `CalibratedClassifierCV(FrozenEstimator, method='sigmoid')`, fitted on probabilities; reproduced at validation `0.13635`, test `0.13602`.
- `0.1441` — shipped custom `PlattCalibrator`, fitted on log-odds; reproduced at validation `0.14428`, test `0.14412`.

The data, split and base model are identical (test n=4,500; 996 defaults; prevalence 0.22133; raw test Brier `0.17094`). Two calibration artifacts also exist: the sklearn calibrator stored inside `creditai_model.joblib` (used by the Phase 1 report and `src/predict.py`) and the separate custom `models/calibration_model.joblib` loaded by the batch API. The shipped custom coefficients (`slope 0.4741`, `intercept -1.2645`) are **not reproducible** from a fresh fit of the current code on the canonical split (`slope 0.8580`), which indicates a stale or differently produced artifact. The correct metric for the deployed artifact is `0.14412`. See `phase_9_brier_discrepancy_review.md`.

No model artifact was replaced and no historical report was edited.

---

## 5. Deliverables

| Deliverable | Status |
|---|---|
| `reports/phase_9_session6_batch_upload_report.md` | Complete |
| `reports/phase_9_session6_batch_validation_test_report.md` | Complete |
| `reports/phase_9_session6_batch_api_contract.md` | Complete |
| `reports/phase_9_session6_frontend_report.md` | Complete |
| `reports/phase_9_session6_verification_report.md` | Complete |
| `reports/phase_9_brier_discrepancy_review.md` | Complete |
| `reports/phase_9_final_report.md` | This document |
| Step 1 screenshot | `reports/figures/phase_9_session6_batch_step1.png` |
| Session evidence logs | `logs/*_session6.*` |

---

## 6. Changed files

### Source files (uncommitted, inherited except the syntax fix)

| File | Change |
|---|---|
| `frontend/src/batch.ts` | One-token syntax repair (`]` → `)`); mapping/statistics/export/report helpers |
| `frontend/src/BatchEvaluation.tsx` | Three-step batch UI |
| `frontend/src/BatchCharts.tsx` | Chart components (new file, untracked) |
| `frontend/src/api.ts` | Batch endpoints and multipart helpers |
| `frontend/src/App.css` | Batch styling |
| `frontend/tests/batch.test.ts` | Restored/expanded to 21 batch tests |
| `src/api/app.py` | Batch routes, upload limits, export endpoints |
| `src/inference/predictor.py` | Calibration application |
| `src/api/batch_service.py` | New parser/validation/prediction/export service (untracked) |
| `tests/test_batch_workflow.py` | New 20-test batch suite (untracked) |

### New verification assets

| Path | Purpose |
|---|---|
| `frontend/public/testdata/` | Synthetic CSV/XLSX fixtures |
| `frontend/public/batch_test_sample.xlsx` | Downloadable sample workbook |
| `logs/` | Test/build/live evidence |
| `reports/phase_9_session6_*` | Session reports |
| `reports/phase_9_brier_discrepancy_review.md` | Calibration review |
| `reports/figures/phase_9_session6_batch_step1.png` | Browser evidence |
| `check_batch.py` | Six-line diagnostic helper left from the parse-fix investigation; not imported by the app |

No file was deleted, reset or stashed. No model artifact or historical evaluation report was overwritten.

---

## 7. How to run

```powershell
# backend (from the project root)
.\.venv\Scripts\python.exe -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000

# frontend (second terminal)
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173

# open
# http://127.0.0.1:5173  -> Batch evaluation
```

Health checks:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-WebRequest http://127.0.0.1:5173 -UseBasicParsing
```

Both were running at the end of verification:

```json
{"status":"ok","scoring":"not_validated"}
```

---

## 8. Residual limitations and risks

| Item | Impact | Handling |
|---|---|---|
| `.xls` untested | UI copy advertises it; only `.csv`/`.xlsx` verified | Disclosed in every report; narrow the copy or add a real `.xls` fixture before claiming support |
| Header-only direct predict returns `200` with `results: []` | API asymmetry; could confuse non-UI clients | UI blocks via `usable: false`; documented in API contract |
| Calibrator artifact not reproducible from current code | Deployed Brier `0.1441` vs fresh-fit `0.1355`; probabilities compressed at the top end | Documented in Brier review; regenerate with provenance if a model change is approved |
| Browser upload automation | Uses injected `File` + real React `change` event, not OS picker | Real handler and real HTTP path executed; limitation stated |
| Large-file performance | Not benchmarked near 10 MB / 5,000 rows | Limit enforcement tested; performance profiling remains open |
| Research-only model | Taiwan 2005 credit-card benchmark; not validated for Indian borrowers | Permanent warning in UI; `/v1/score` closed |
| Local servers only | No deployment, TLS, auth or multi-user isolation | Out of Phase 9 scope |

None of these invalidates the batch workflow, and none is hidden in the UI or the reports.

---

## 9. Final status

- **Batch workflow:** accepted and verified for CSV and multi-sheet XLSX.
- **Single prediction and dashboard integration:** verified.
- **Exports:** verified, including formula-injection protection.
- **Production score gate:** closed (`not_validated`, null probability).
- **Tests:** 138 backend + 26 frontend + 38 live checks, all passing.
- **Phase 9 session 6:** complete.
- **Phase 10:** not started.

The next decision is a product/model decision, not a bug fix: whether to keep the current calibration artifact (`0.1441`) or regenerate it with provenance and adopt the better fresh fit (`~0.1355`). Until that decision is made and evaluated, the deployed artifact and its reported metric remain unchanged.
