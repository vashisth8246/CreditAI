# Phase 11.1 — Frontend Runtime Recovery

**Date:** 2026-11-01
**Branch:** `phase11-final-verification`
**Scope:** Diagnose and recover the running local frontend/backend integration. No application behavior, model, research output, or calibration artifact was changed.

## Root cause

Before recovery, the frontend requested `GET /v1/dashboard/snapshot`; the request passed through the correct Vite `/v1` proxy to `http://127.0.0.1:8000`, and the backend returned `404 Not Found`. The browser showed `Research data unavailable` and `Not Found`.

The backend source on this branch already registered `GET /v1/dashboard/snapshot`, but the live Uvicorn process was created on October 30 and its `/openapi.json` route list did not include that route. The backend process was stale relative to the current checkout. The shared snapshot load gates Executive Overview and several other sections, so one missing route made those whole pages show the same error. This was not caused by a bad frontend path, Vite proxy, missing dashboard artifact, or incorrect repository-relative path.

All three required Phase 9 artifacts existed in the current checkout, were Git-tracked, contained valid non-empty JSON, and were readable by the backend loader. The backend loads the fixed Phase 9 filenames from the absolute repository path derived from `src/api/app.py`; it does not substitute Phase 6 or Taiwan model files.

The stale backend and frontend processes were stopped. `npm ci` restored the incomplete ignored `frontend/node_modules` tree. FastAPI and Vite were then started from this branch using the documented development commands. No tracked dependency lockfile changed.

## Endpoint and asset verification

| Request | Before restart | After restart | Result |
|---|---:|---:|---|
| `GET http://127.0.0.1:8000/health` | 200 | 200 | `{"status":"ok","scoring":"not_validated"}` |
| `GET http://127.0.0.1:8000/v1/status` | 200 | 200 | Connected; 2 models registered; production scoring `not_validated` |
| `GET http://127.0.0.1:8000/v1/dashboard/snapshot` | **404** | **200** | 95,451-byte historical snapshot response |
| `GET http://127.0.0.1:5173/v1/dashboard/snapshot` | **404** | **200** | Vite proxy reaches the same backend route |
| `GET http://127.0.0.1:5173/data/phase_9_lendingclub_summary.json` | — | 200 | 19,120 bytes |
| `GET http://127.0.0.1:5173/data/phase_9_dataset_inventory.json` | — | 200 | 26,345 bytes |
| `GET http://127.0.0.1:5173/data/phase_9_feature_inventory.json` | — | 200 | 72,099 bytes |

The snapshot reports `source=historical_research_snapshot`, source date `2026-10-13`, dataset `DS001` (`LendingClub accepted loans`), 20 inventory rows, and 151 feature rows. A direct request recorded retrieval time `2026-11-01T08:48:07.699989+00:00`. The UI presents that retrieval time separately from the historical source date.

Required files:

| File | Exists | Git-tracked | Valid, non-empty JSON | Backend-readable |
|---|---|---|---|---|
| `frontend/public/data/phase_9_lendingclub_summary.json` | Yes | Yes | Yes | Yes |
| `frontend/public/data/phase_9_dataset_inventory.json` | Yes | Yes | Yes | Yes |
| `frontend/public/data/phase_9_feature_inventory.json` | Yes | Yes | Yes | Yes |

## Frontend-to-backend request inventory

| Frontend call | Backend route | Runtime result |
|---|---|---|
| `GET /health` | `/health` | 200 |
| `GET /v1/status` | `/v1/status` | 200 |
| `GET /v1/dashboard/snapshot` | `/v1/dashboard/snapshot` | 404 before restart; 200 after restart |
| `GET /v1/models` | `/v1/models` | 200 |
| `GET /v1/models/{model_id}` | `/v1/models/{model_id}` | 200 for Taiwan XGBoost and KNN |
| `GET /v1/models/{model_id}/schema` | `/v1/models/{model_id}/schema` | 200 for Taiwan XGBoost and KNN |
| `GET /v1/models/{model_id}/evaluation` | `/v1/models/{model_id}/evaluation` | 200 for Taiwan XGBoost and KNN |
| `POST /v1/predict` | `/v1/predict` | 200 in the Borrower Prediction page using its built-in synthetic low-risk example |
| `POST /v1/score` | `/v1/score` | 200; `score_status=not_validated`, probability `null` |
| `POST /v1/research/taiwan/batch/inspect` | Same | 200 with 1 valid synthetic template row |
| `POST /v1/research/taiwan/batch/analyze` | Same | 200 with 1 valid synthetic template row |
| `POST /v1/research/taiwan/batch-predict` | Same | 200; one result, status `success` |
| `POST /v1/research/taiwan/batch/export/csv` | Same | 200; 372-byte CSV |
| `POST /v1/research/taiwan/batch/export/xlsx` | Same | 200; 6,847-byte XLSX |

The batch HTTP smoke test used the application's one-row synthetic template in memory. It did not write a dataset or use real borrower information.

## Manual runtime page matrix

`Loads` refers to the page route and its actual data behavior, not merely its React shell.

| Page | UI shell | Real page data / runtime result | API errors after restart | Notes |
|---|---|---|---|---|
| Executive Overview | Loaded | **Loaded** historical summary, KPIs, vintage chart, and saved comparison metrics | None | Source date `2026-10-13`; retrieval time shown separately |
| Borrower Prediction | Loaded | **Loaded** model list, XGBoost schema, metadata; synthetic sample inference returned 8.2% calibrated model output | None | Taiwan 2005 research/demo only; this is not lending validation |
| Batch Evaluation | Loaded | **Verified by live API workflow**: inspect, analyze, predict, CSV export, and XLSX export all returned 200 | None | Initial screen awaits user file selection, as designed |
| Data Discovery | Loaded | **Loaded** 20 dataset records and 151 feature metadata rows | None | External unavailable records remain explicitly marked unavailable |
| Portfolio Intelligence | Loaded | **Loaded** historical loan totals, terminal outcomes, vintage and segment metrics | None | Closed-loan historical cohort; not live activity |
| Model Lab | Loaded | **Loaded** saved LendingClub metrics, split, confusion matrix, and evidence metadata | None | Curves/calibration views remain explicitly unavailable where evidence is absent |
| Model Performance Lab | Loaded | **Loaded** Taiwan XGBoost evaluation artifact and metrics | None | Taiwan research/demo model; distinct from the LendingClub dashboard data |
| Risk Explorer | Loaded | **Loaded honest empty-state evidence**: no saved individual historical risk scores | None | Does not invent prediction rows; synthetic contract check remains `not_validated` |
| Explainability | Loaded | **Loaded honest empty-state evidence**: no LendingClub-linked explanations are saved | None | Does not display unrelated synthetic SHAP output as historical explanations |
| Monitoring | Loaded | **Loaded** historical cohort/split metrics | None | Live traffic, PSI, and matured labels are explicitly unavailable |
| Architecture & Audit | Loaded | **Loaded** audit facts, data scope, and safety state | None | `/v1/score` remains `not_validated` |

The deliberate empty states in Risk Explorer and Explainability are successful, truthful page results; they are not API failures.

## Regression and frontend checks

Commands and results from this recovery:

| Command | Result |
|---|---|
| `python -m pytest tests/test_api_integration.py -k dashboard -v --tb=short` | **5 passed, 1 skipped, 11 deselected.** The skipped test is the real `TestClient` HTTP request on Windows because the known Windows TestClient loopback stall persists. The live HTTP route was verified directly after restart. The test runs on non-Windows CI. |
| `python -m pytest tests/test_batch_workflow.py -k synthetic_seven_sheet_workbook_inspects_and_scores_eligible_sheets -v --tb=short` | **1 passed, 21 deselected** (17 warnings, including visible scikit-learn artifact-version warnings) |
| `npm ci` | **Passed**; restored 27 packages, audit reported 0 vulnerabilities |
| `npm test` | **28 passed, 0 failed** |
| `npm run lint` | **Passed** |
| `npx tsc -b` | **Failed in this Windows path** before source checking: `npx` resolved a malformed path ending at `F:\NUV ACD\All SEM\7th Sem\typescript\bin\tsc`. It produced no TypeScript source diagnostic. |
| `npm run build` | **Passed**; this existing script ran `node node_modules/typescript/bin/tsc -b` successfully, then Vite 8.3.4 built the production bundle (25 modules). |
| `git diff --check` | **Passed** |

The `npx` failure is specific to this Windows workspace path containing `&` and spaces. The project's build script invokes the same TypeScript compiler directly and passed. The prior successful GitHub Actions run also verified TypeScript and production build on Linux. No TypeScript check was weakened or removed.

## Files changed

- `tests/test_api_integration.py` — adds coverage for route registration and frontend/backend path agreement, required valid Phase 9 assets and correct dataset identity, no fallback to unrelated Phase 6/Taiwan JSON, explicit missing-artifact failure, and an HTTP provenance test for non-Windows CI. The Windows skip is limited to the TestClient HTTP request; direct runtime HTTP was verified separately.
- `docs/phase11/PHASE_11_1_RUNTIME_RECOVERY.md` — this separate recovery record.

No source application behavior, model artifacts, calibration, experiment metrics, or existing Phase 11 completion documentation was changed. `models/calibration_model.joblib` SHA-256 remains `6b94f41d3521c37e22d41b91e505006f1c737d022c214f803a5b9a057f185cdc`. No retraining or dashboard data fabrication occurred.

## Remaining limitations

- The Windows `TestClient` localhost stall remains; the live FastAPI HTTP service and frontend proxy were reachable and verified directly.
- A fresh GitHub Actions run for this recovery commit has not yet been observed.
- Risk Explorer has no saved historical per-borrower score outputs; Explainability has no Phase 2.3-linked explanation artifact; live monitoring has no production traffic or matured labels.
- Taiwan models and data remain research/demo only. Indian borrower validation and production lending readiness remain not validated. `/v1/score` remains `not_validated`.
- Docker remains unverified, as recorded in the Phase 11 final report.

No merge, main-branch push, or deployment occurred during this recovery.
