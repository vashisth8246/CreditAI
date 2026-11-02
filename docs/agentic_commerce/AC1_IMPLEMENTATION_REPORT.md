# Agentic Commerce AC-1 Implementation Report

## Delivered foundation

- Added typed, PII-minimized contracts, a future-tool protocol, and a static state-transition map. No tool or workflow executor is active.
- Added read-only status and workflow endpoints at `/v1/agentic-commerce/status` and `/v1/agentic-commerce/workflow`.
- Added separate Agentic Commerce and Commerce Audit Trail pages. They label all workflow stages planned/inactive and show an honest empty audit state.
- Added AC-1 backend and frontend tests.
- Kept Borrower Prediction, Batch Evaluation, model behavior, and calibration artifacts unchanged. `/v1/score` remains locked as `not_validated`.

## VERIFIED

Commands run from the repository root unless noted:

| Check | Actual result |
|---|---|
| `python -m pytest tests/ -v --tb=short -o faulthandler_timeout=90` (original workspace) | 172 passed, 2 skipped, 58 warnings in 76.37 seconds. The two skips are existing Windows-only HTTP guards for AC status/workflow and dashboard snapshot responses. |
| `python -m pytest tests/ -v --tb=short -o faulthandler_timeout=90` (clean committed checkout) | 164 passed, 10 skipped, 57 warnings in 26.46 seconds. The additional eight skips require untracked raw Taiwan/LendingClub datasets; the datasets are intentionally absent from the clean release checkout. The other two skips are the Windows-only AC and dashboard HTTP guards. |
| AC status/workflow requests through `httpx.ASGITransport` | Passed: both routes returned HTTP 200; status reported `agentic_commerce`, `AC-1`, `research_demo`, disabled real lending/transactions, and required human confirmation; all eight workflow stages were planned. |
| Backend coverage in the full suite | AC contracts and gates, Borrower Prediction, `/v1/score`, Batch Evaluation including seven-sheet workbook, API contracts, model tests, and deployment adapter tests passed. Existing scikit-learn version warnings were visible and not suppressed. |
| `python -m pytest tests/test_package_release.py -v --tb=short` | 1 passed; verifies that public batch test fixtures are excluded from frontend release entries while runtime assets remain included. |
| `npm test` (from `frontend/`) | 39 passed, 0 failed, 0 skipped, including all three AC-1 tests. |
| `npm run lint` (from `frontend/`) | Passed. |
| `node node_modules/typescript/bin/tsc -b` (from `frontend/`) | Passed. The direct compiler invocation is used because the `npx tsc -b` shim misparses this Windows workspace path containing `&`. |
| `npm run build` (from `frontend/`) | Passed; generated `frontend/dist/index.html` and hashed JS/CSS assets. |
| `/v1/score` safety contract | Passed through the full regression suite and direct contract test: `score_status=not_validated`, `score_type=none`, `default_probability=null`, `validated_risk_estimate=false`, and `model_version=null`. |
| Calibration artifact SHA-256 | `models/calibration_model.joblib` is `6b94f41d3521c37e22d41b91e505006f1c737d022c214f803a5b9a057f185cdc`, matching the previously recorded value. No calibration/model file was changed. |
| Static production-build inspection | Passed: built application includes the distinct Agentic Commerce section, both pages, the eight stages (including Comparison), research/demo and no-real-transaction warnings, human-confirmation notice, and no-event audit empty state. |
| Release ZIP inspection | Passed from a clean detached commit: valid CRC and manifest SHA, required backend/runtime/KNN files and frontend build present, extracted app import and model paths passed. The archive contains 81 files and excludes test fixtures, CSV/XLSX datasets, secrets, logs, caches, and tests. |
| Extracted ZIP startup command | Passed locally from a temporary extraction using `python -m uvicorn src.api.app:app --host 127.0.0.1 --port <ephemeral>`. `/`, `/health`, AC-1 status/workflow, and the valid dummy `/v1/score` safety response were verified. No Azure deployment was made. |

## ENVIRONMENT-LIMITED / NOT VERIFIED

- A first full backend run in the restricted Windows execution context stalled at the existing `/health` `TestClient` call while asyncio attempted to create a Windows socket pair. The complete rerun with normal socket access passed; this is recorded as an environment/tooling limitation, not an application failure.
- Two tests remain intentionally skipped by their Windows platform guards: the combined AC status/workflow HTTP test and dashboard snapshot HTTP test. AC routes were independently exercised with in-process ASGI requests; the full suite includes direct route/contract verification.
- Static/build verification was performed; no browser/manual visual acceptance was completed.
- Azure CLI is unavailable and no Azure authentication or deployment was attempted.
- The first package candidate was rejected after inspection found tracked synthetic batch test fixtures copied into the Vite build. That candidate was removed and not used. The release packager now excludes those fixtures, with a regression test, and the final clean-checkout archive passed the checks above. The two pre-existing rejected ZIPs (`release/creditai-8ca9881.zip` and `release/creditai-8ca98819af970b12e613e4d87ab349edef80a354.zip`) remain untouched and unused.
- GitHub Actions has not yet validated the AC-1 commits. The latest visible workflow run, `41422816270`, used the earlier `b37d670` commit and is not evidence for AC-1. No deployment was attempted.
- Azure deployment was not attempted. Any package upload to the existing App Service remains a manual user action, followed by live verification.

## Route compatibility correction

With FastAPI 0.143.0, `include_router()` placed a lazy `_IncludedRouter` in `app.routes`. An existing dashboard contract test iterates that collection and expects each entry to expose `.path`; it failed with `AttributeError`. The two AC read-only routes are now registered directly with `add_api_route()` and their explicit response models. Their OpenAPI paths and direct contract tests pass, and the existing dashboard route-inspection test now passes. No borrower-scoring or batch calculations were changed.

## DEFERRED TO AC-2

Tool execution/orchestration, purchase-intent submission, affordability and research-risk calculations, financing-option discovery, comparison/recommendation, confirmation UI, simulated transactions, durable audit storage, and external-provider integration remain inactive and require separate design and review.

## Release and deployment status

The Azure ZIP is **verified and ready for manual upload**. Build manifest SHA must match the exact commit used to create the archive; use the newest `release/creditai-<full-commit-sha>.zip` output from the clean release checkout. Azure deployment remains **not performed** and requires the user to upload that verified ZIP to the existing App Service described in [the upload handoff](AC1_AZURE_APP_SERVICE_UPLOAD.md). No live Azure health or application verification is claimed.
