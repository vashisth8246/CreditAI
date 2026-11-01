# CreditAI Phase 11 implementation plan

**Prepared:** 2026-11-01
**Stage:** 1 — repository audit and plan
**Implementation status:** No Phase 11 product, API, model, research, or deployment implementation has started.

## 1. Repository baseline

- Working branch: `main`.
- Local `HEAD`: `932c63f98ab5de87c32ba08d4ded55068324ef55` (`Add KNN model and provider-neutral CI/CD pipeline`). The local `origin/main` tracking ref points to the same commit.
- The working tree is dirty. Existing user work must be preserved; do not reset, clean, or replace it. The two modified tracked files are `frontend/src/App.tsx` and `src/api/app.py`. Existing untracked work includes the current `Dockerfile`, `.dockerignore`, `docs/RENDER_DEPLOYMENT.md`, `frontend/public/data/`, `scripts/train_knn_model.py`, Phase 10 reports, `check_batch.py`, and the root `package-lock.json`. This plan is newly added by Stage 1.
- A read-only `git ls-remote origin refs/heads/main` could not resolve GitHub in this environment (`getaddrinfo thread failed to start`). The local tracking ref is current only as of the local repository metadata; remote freshness could not be independently confirmed. No fetch or pull was run, so local changes were not at risk of overwrite.
- No `AGENTS.md` repository instructions were found.

## 2. Current architecture and behavior

### Application

- React, TypeScript, and Vite frontend in `frontend/`; existing scripts are `npm test`, `npm run lint`, `npx tsc -b`, and `npm run build`.
- FastAPI entry point is `src/api/app.py`; model/inference code is under `src/inference/`; CSV/XLSX handling is in `src/api/batch_service.py`.
- Research models in the registry are Taiwan XGBoost (`uci_taiwan_xgb`) and KNN (`uci_taiwan_knn`). Model paths are relative to the repository root. Required artifacts are tracked under `models/`, including both joblib bundles, calibration artifacts, feature names, metadata, and Taiwan evaluation JSON. The KNN bundle depends on the tracked `src/models/knn.py` class for deserialization.
- `/health` returns `{"status":"ok","scoring":"not_validated"}`. `/v1/status` reports backend connectivity, model availability, and `indian_production_scoring: not_validated`. `/v1/score` remains a contract-gated endpoint and does not return a borrower probability. Research inference is separate at `/v1/predict` and batch evaluation is under `/v1/research/taiwan/...`.
- Existing Docker work is present but untracked: the Dockerfile builds the frontend and runs Uvicorn, and `src/api/app.py` has a conditional static-file mount. The current deployment notes target Render; Phase 11 calls for Azure documentation. Stage 5 should extend or clarify these files rather than overwrite them. A Docker image build has not been verified because the Docker CLI could not connect to the local Linux engine in the prior check.

### Dashboard freshness finding

The dashboard’s overview is sourced from bundled files, not a dashboard data API:

- `frontend/src/App.tsx` loads `/data/phase_9_lendingclub_summary.json`, `/data/phase_9_dataset_inventory.json`, and `/data/phase_9_feature_inventory.json` on mount. `retryLoad()` fetches those same files again; it does not request dashboard data from FastAPI.
- The loaded summary has `generated_at: "2026-10-13"` and `source_label: "HISTORICAL RESEARCH DATA"`. The top bar independently hardcodes “Snapshot · 13 Oct 2026.” The summary aligns with the Phase 6.1 artifact history and is a historical LendingClub aggregate, not a live portfolio feed.
- API status is checked separately through `/health`. An “API online” indicator therefore does not mean the displayed portfolio summary came from the API or was refreshed from a current source.
- `frontend/src/api.ts` does use same-origin relative requests in production, and `frontend/vite.config.ts` proxies `/health` and `/v1` during development. `App.tsx` still contains a pre-existing local URL fallback in the working tree diff; Stage 2 should preserve the current same-origin change and inspect other callers.
- `researchApi.evaluation()` catches API errors and falls back to `/data/uci_taiwan_eval.json` regardless of selected model. That can mask an API failure and can return the XGBoost artifact while KNN is selected.
- No service worker, React Query client, or dashboard local/session-storage cache was found. Prediction history uses local storage, but it is separate from the overview snapshot.
- No backend endpoint currently serves the dashboard summary/inventory/feature files. The current `frontend/public/data/` files are untracked, so a clean checkout will not contain them unless they are deliberately committed or replaced by a tracked/backend-delivered source.

**Safe interpretation:** the available overview artifacts are historical and do not become live portfolio data when fetched again. Stage 2 must keep the snapshot date/source explicit, separately show the time of the latest successful API response, and never label snapshot content as current borrower or portfolio activity. There is no connected source for new LendingClub or Indian borrower records in the current backend.

### UI and Gender terminology

- The requested hero text is still present in `App.tsx`: “Make risk evidence work harder.”
- `PredictionWorkspace.tsx` displays feature names using `fieldLabel(key)`, which only replaces underscores. Thus raw `SEX` appears as `SEX`; error text and feature-contribution labels use the same helper. Model schema metadata already describes raw `SEX` as “Gender”, but the UI helper does not use that description for its label.
- `SEX` is part of the trained feature contract, `feature_names.json`, backend schema, batch mapping, test data, and saved joblib artifacts. Keep this canonical key and encoding intact; add display-only mapping to “Gender.” Some old inventory text uses “sex” in dataset sensitivity descriptions and should be reviewed for user visibility. Research-source quotations and dataset column names should remain technically accurate where changing them would misrepresent the source.

### Batch CSV and Excel

- The backend accepts CSV, `.xlsx`, and `.xls` through pandas/openpyxl/xlrd. It analyzes worksheets independently and provides inspect, analyze, predict, CSV export, and XLSX export routes.
- Current limits are 10 MiB upload size, 5,000 data rows per worksheet, 20 worksheets, and 200 columns. Formula cells are explicitly rejected in `.xlsx`; headers can be normalized and mapped; validation does not silently impute missing values; references and source worksheet/row are returned.
- Frontend batch UI already supports worksheet selection/mapping, preview, row errors, results, charts, and CSV/XLSX/report export. Existing backend `tests/test_batch_workflow.py` covers CSV, malformed/oversized files, multiple/blank/invalid sheets, mapping, formula handling, predictions, and export. Frontend has batch/analytics helper tests.
- Stage 3 should verify the seven-sheet acceptance workbook and unsupported edge cases against the current behavior before changing it. If requirements are already met, preserve the implementation and add only evidence/tests for gaps. The output should make repayment probability an explicitly computed complement of returned PD, with no repayment guarantee language.

### Research and dataset state

- Local `Data/` contains the Taiwan UCI `.xls` (30,000 rows; 23 raw predictors plus ID and target) and LendingClub source files, along with other audited datasets and synthetic fixtures. `/Data/` is ignored. Do not add the raw LendingClub CSV, Taiwan workbook, borrower data, or generated caches to Git.
- The dataset audit describes DS003 (Taiwan, 2005, next-month default) as suitable for historical research and explicitly not representative of Indian borrowers. It describes DS001 LendingClub as a U.S. historical benchmark, not Indian evidence. Synthetic records remain software test/demo data only.
- Existing `src/train.py` implements Logistic Regression, Random Forest, and XGBoost. `scripts/generate_evaluation_artifacts.py` and the KNN training script reproduce same-split comparisons and generate evaluation JSON. There is no selective prediction or SHAP perturbation-stability module in the current source.
- Prior Phase 9 research documents a calibration provenance issue: the shipped custom XGBoost calibrator’s coefficients (`slope 0.4741`) do not reproduce from the documented current fitting procedure (`slope 0.8580`). The documented held-out Brier for the shipped custom artifact is `0.14412`; an alternative sklearn calibration number is not the shipped artifact’s result. Phase 11 must first rerun and reconcile this provenance rather than treating prior values as new evidence.
- Current requirements pin scikit-learn 1.9.1, while previous XGBoost/calibration artifacts were serialized with scikit-learn 1.9.0 and generate `InconsistentVersionWarning`. Do not suppress warnings or overwrite artifacts without a reproducible comparison and explicit artifact provenance.

### Existing verification evidence

The latest recorded local checks after the current static serving/same-origin changes were: backend **138 passed, 0 failed, 0 skipped** with 55 warnings; frontend **26 passed, 0 failed, 0 skipped**, lint/typecheck/build passed in a temporary copy; FastAPI smoke checks passed for `/`, `/health`, `/v1/status`, and both Taiwan evaluation endpoints. Docker build was not run because the Linux engine was unavailable. These are baseline evidence, not Phase 11 results.

## 3. Staged implementation plan

### Stage 1 — repository audit and plan (this stage)

- Read assignment, README, Python/frontend configuration, API routes, model registry/artifact paths, dataset audit, prior phase reports, frontend behavior, and current tests.
- Record branch/working tree and preserve all existing edits.
- Deliver this file. No Phase 11 app/research changes or tests were made during Stage 1.
- **Exit gate:** findings and risks documented; user reviews this plan before moving to Stage 2.

### Stage 2 — UI, Gender labels, and dashboard/API freshness

Candidate scope: `frontend/src/App.tsx`, `frontend/src/PredictionWorkspace.tsx`, display-label helpers and relevant components, `frontend/src/api.ts`, a small dashboard API route/service and its tests in `src/api/` and `tests/`, the relevant frontend tests, and source labels in user-facing content.

- Remove the requested slogan without replacing it with another marketing line.
- Map `SEX` to display label “Gender” in forms, validation messages, feature contributions, dataset/batch presentation, and supported exports while preserving the raw API/model key and values.
- Replace the hardcoded snapshot date with artifact provenance. Decide on a backend route for sanitized historical dashboard artifacts only after confirming authoritative source files and tracking status. On refresh, request the configured API, show request loading/error/status and actual successful-response time, and separately identify the source snapshot date. Do not make the static DS001 summary appear live.
- Remove the cross-model evaluation fallback or make it model-specific and clearly historical; API failures must remain visible.
- Test online/offline, loading/empty/error/refresh, cancellation or duplicate-refresh behavior, timestamp/source labeling, model-specific evaluation failure, `/health`, `/v1/status`, and `/v1/score` safety contract.
- **Exit gate:** one selected, documented source contract; no false freshness; raw feature/model compatibility tests pass.

### Stage 3 — CSV/Excel and batch evaluation

Candidate scope: `src/api/batch_service.py`, `src/api/app.py` only where needed, `frontend/src/BatchEvaluation.tsx`, `frontend/src/batch.ts`, `frontend/src/BatchCharts.tsx`, existing batch tests, and a generated synthetic seven-worksheet fixture kept separate from real borrower data.

- Re-run the existing matrix first. Add coverage for valid sheets with different column orders, missing values, extra metadata, invalid/missing-feature sheets, summary and empty sheets, duplicate IDs, malformed/incorrect extensions, mixed types, oversize limits, and row-level errors. Do not silently drop rows/sheets.
- Verify per-borrower PD, `1 - PD` as a mathematical complement, category/status, reference and worksheet provenance, portfolio metrics/charts, and safe CSV/Excel export. Label synthetic fixture records in test context, never as actual borrowers.
- Preserve existing upload/row/sheet limits unless evidence justifies a separate decision; test resource use and Excel parser behavior.
- **Exit gate:** seven-sheet fixture has explicit outcomes for every sheet and row; current endpoint contracts and existing batch tests remain valid.

### Stage 4 — controlled research experiments and artifacts

Candidate scope: a dedicated `src/research/phase11/` module and reproducible experiment scripts/config; tests; `reports/phase11/` metrics/figures/metadata; white paper and reproduction guide under `docs/phase11/`.

- Audit and hash the local DS003 source and document rows, columns, target, class counts, preprocessing, missingness, and limitations. Do not include raw data. No Indian borrower-level repayment dataset is currently established.
- Freeze a reproducible stratified train/validation/test plan before final holdout evaluation. Train Logistic Regression, Random Forest, and XGBoost under comparable preprocessing. Document model and dependency versions; reconcile existing artifact/calibration provenance first.
- Fit Platt and justified isotonic calibration on validation only; compare raw/calibrated ROC-AUC, PR-AUC, Brier, log loss, ECE, and reliability diagrams on a locked test split.
- Choose and justify a configurable selective rule on validation (candidate: calibrated probability distance from a review boundary). Report coverage, referred fraction, and selective risk on the locked test set; expose research status only and keep `/v1/score` not_validated.
- Measure SHAP explanation stability on valid, constrained perturbations of held-out observations; never perturb category codes into invalid values. Publish actual metrics and uncertainty/limitations.
- Generate only artifacts produced by the experiment. White paper references must be real and verified; conclusions may be negative or mixed.
- **Exit gate:** reproducible commands, saved configs/seeds/split hashes, tests for metrics and decision behavior, and no test-set tuning.

### Stage 5 — white paper, full testing, docs, and Azure preparation

Candidate scope: `README.md`, API/user documentation, `docs/phase11/CreditAI_Reliability_Aware_Credit_Risk_Research_Paper.md`, `docs/phase11/EXPERIMENT_REPRODUCTION.md`, `docs/phase11/AZURE_DEPLOYMENT.md`, and `docs/phase11/PHASE_11_FINAL_REPORT.md`; update existing Docker configuration only if validation shows a gap.

- Run the complete existing and added backend/frontend/integration checks, lint, TypeScript, build, security/input/upload checks, and a Linux Docker build if the engine is available. Record commands and actual pass/fail/skip counts and warnings.
- Verify container startup, static frontend/API routing, model artifact availability, health/status safety values, and representative CSV/XLSX requests. Keep `/v1/score` `not_validated`; do not claim Indian validation or production readiness.
- Research and document the current Azure deployment option, environment variables, health check, costs/credits, and rollback from current official Azure documentation. Do not provision paid resources or deploy.
- Review `git diff`, untracked files, secrets, raw/large data, and user-owned changes. Stage/commit/push only under a later explicit instruction; none is authorized by this Phase 11 staging request.
- **Exit gate:** all claims match evidence; all blockers and unverified items are explicit; no remote deploy or release claim without real verification.

## 4. Stage-wide safety gates

- Keep all Taiwan models marked historical research/demo only; never imply applicability to Indian borrowers or lending decisions.
- Keep `/v1/score` and health/status production scoring values at `not_validated`.
- Preserve canonical feature names, encodings, and model artifacts unless a controlled experiment and compatibility tests justify a change.
- Never use synthetic data as real borrower performance evidence. Keep datasets, secrets, borrower records, logs, caches, and unrelated generated files out of Git/release.
- Do not suppress scikit-learn serialization warnings. Do not commit, push, create cloud resources, or deploy during these stages unless separately authorized.

## 5. Open decisions and blockers

1. Remote `origin/main` could not be queried due to DNS/network failure; confirm remote freshness when connectivity is available before any release.
2. The dashboard’s present data is a historical static snapshot, not a live data source. A fresh API retrieval timestamp must not be confused with a newer source dataset.
3. Dashboard JSON assets are untracked in this checkout. Their intended source and inclusion/serving path need review; do not discard them.
4. Shipped XGBoost calibration provenance is unresolved and must be reconciled before publishing new comparative calibration claims.
5. Local Docker daemon access was unavailable; container build/runtime and memory are unverified.
6. No validated Indian borrower repayment data is established. Research conclusions must remain specific to the Taiwan 2005 dataset.

## 6. Stage 2 implementation result — UI, Gender, dashboard/API

**Status:** Implemented locally; no files were staged, committed, pushed, or deployed.

- Added `GET /v1/dashboard/snapshot`. It loads only the three named, sanitized Phase 9 dashboard artifacts and returns `source: historical_research_snapshot`, the source snapshot date, a request retrieval timestamp, and `Cache-Control: no-store`. If those artifacts are missing or unreadable, it returns a clear 503 instead of substituting data.
- The overview now fetches its summary, inventory, and feature profile from that configured backend route. Refresh makes a new no-cache request, aborts an obsolete request, prevents duplicate refreshes, and presents the source date separately from the retrieval time. API connectivity remains a distinct `/health` check.
- Removed the “Make risk evidence work harder” slogan. Added display-only `SEX` → “Gender” mapping in the borrower form, model contributions, dataset feature labels, batch mapping/validation views, generated validation exports/reports, and README. The raw feature key and input values remain `SEX`.
- Removed the model-evaluation fallback to `uci_taiwan_eval.json`; a failed evaluation request now stays an error for the selected model.
- Kept `/health`, `/v1/status`, and `/v1/score` implementation and safety values unchanged.

**Checks run:** frontend 27 tests passed; lint passed; `npm run build` passed (it runs `tsc -b` before Vite); the focused backend snapshot loader/handler tests passed (2 passed). Direct `npx tsc -b` still fails in this Windows workspace because the `&` in `ML&DS` is parsed by the Windows command launch path; the exact TypeScript build through `npm run build` succeeds. An HTTP-level TestClient run could not be completed because this environment stalls while creating the Windows Proactor event loop (`socketpair`); the handler logic and response headers were exercised directly. Existing Pydantic and SHAP warnings were left visible.

**Release dependency:** the three dashboard artifact files in `frontend/public/data/` are currently untracked in this checkout. The endpoint intentionally fails closed if they are absent. They must be included in a later clean checkout/release or replaced with a committed backend data source before the dashboard can load there. No asset files were modified in Stage 2.

**Stage 2 exit note:** code and frontend checks are complete. Keep HTTP-level verification and the dashboard-artifact tracking decision open for Stage 5/release readiness. Stage 3 has not started.

## 7. Stage 3 implementation result — CSV/Excel and batch evaluation

**Status:** Implemented locally; no files were staged, committed, pushed, or deployed.

- Preserved the existing CSV, `.xlsx`, and `.xls` parser, explicit per-sheet mapping, upload/row/sheet/column limits, formula checks, row-level failures, worksheet provenance, charts, and safe export workflow.
- Added a duplicate borrower-reference warning during worksheet validation. Duplicate records remain separate and keep their original sheet/row; none are silently deduplicated.
- Added an explicitly labeled estimated non-default complement (`1 − PD`) per successful borrower in the results table and both CSV and Excel exports. Invalid or unavailable PD values produce no complement. The UI, Markdown report, and Excel summary state that this mathematical complement is not an observed repayment or guarantee. Model/API prediction payloads and scoring behavior were not changed.
- Added an in-memory, synthetic seven-worksheet acceptance workbook test covering valid `Portfolio_A`, reordered `Portfolio_B`, missing-value `Portfolio_C`, metadata `Portfolio_D`, unmappable `Invalid_Sheet`, non-borrower `Summary`, and `Empty_Sheet`. The fixture also includes repeated synthetic references to verify warning and retention behavior.

**Checks run:** focused backend service/export tests: **2 passed** (seven-sheet validation plus actual Taiwan model predictions for eligible rows, and CSV/XLSX complement export). Frontend tests: **28 passed**, lint passed, and `npm run build` (including TypeScript project build) passed. Existing warnings, including scikit-learn artifact-version warnings, were not suppressed. `git diff --check` is run at the Stage 3 final audit.

**Verification limit:** the full `tests/test_batch_workflow.py` FastAPI `TestClient` suite did not complete in this Windows workspace. The process stalls creating the loopback `socketpair` needed by the Proactor event loop; the Windows selector loop also stalls here. The direct service tests exercise parsing, the seven-sheet workbook, actual model inference, row references, and exports without that HTTP harness. Run the complete endpoint suite in GitHub Actions or another environment with functioning loopback sockets before release.

**Stage 3 exit note:** the requested batch behavior and service-level acceptance tests are complete. HTTP endpoint regression verification remains open. Stage 4 is recorded below.

## 8. Stage 4 implementation result — controlled research experiments

**Status:** Completed locally as research-only work. No files were staged, committed, pushed, or deployed. Production model artifacts and API scoring behavior were not changed.

- Added `src/research/phase11/core.py` with validated binary-probability metrics, equal-width reliability bins/ECE, validation-fitted Platt and isotonic calibrators, and validation-only threshold selection for a confidence-based referral rule. Added `scripts/run_phase11_experiment.py` and focused tests in `tests/test_phase11_research.py`.
- The experiment loads the existing UCI Taiwan Default of Credit Card Clients workbook, applies the existing preprocessing and feature engineering, and uses a deterministic stratified 70/15/15 split (21,000 train; 4,500 validation; 4,500 locked test; seed 42). Split index hashes and dataset SHA-256 are recorded. The checkout was dirty during the run; metadata records `HEAD` and that limitation.
- Logistic Regression, Random Forest, and XGBoost were trained with the current Phase 1 research hyperparameters. Platt and isotonic were fit only on validation predictions and labels. The locked test was used for final evaluation. Actual model results are in `reports/phase11/probability_metrics.csv` and JSON; reliability bin values and diagrams are also saved there.
- Test ROC-AUC / average precision / Brier / log loss / ECE (10 equal-width bins) were, respectively: Logistic Regression raw 0.7550 / 0.4903 / 0.1934 / 0.5804 / 0.2175; Platt 0.7550 / 0.4903 / 0.1436 / 0.4518 / 0.0124; isotonic 0.7514 / 0.4733 / 0.1440 / 0.4553 / 0.0134. Random Forest raw 0.7816 / 0.5568 / 0.1756 / 0.5339 / 0.1917; Platt 0.7816 / 0.5568 / 0.1349 / 0.4288 / 0.0083; isotonic 0.7803 / 0.5371 / 0.1351 / 0.4504 / 0.0123. XGBoost raw 0.7807 / 0.5588 / 0.1709 / 0.5205 / 0.1696; Platt 0.7807 / 0.5588 / 0.1355 / 0.4305 / 0.0145; isotonic 0.7800 / 0.5394 / 0.1359 / 0.4451 / 0.0111. This is a single fixed-split research comparison; calibration did not improve ranking, and these metrics do not establish deployment validity.
- The XGBoost Platt review margin was selected on validation under at least 80% coverage. The locked-test result at margin 0.20 was 80.24% accepted coverage, 19.76% referred, and 13.10% error among accepted cases (473 / 3,611). This is a simple confidence screen, not a guarantee of epistemic uncertainty or safe credit decisions.
- SHAP stability was measured for 100 fixed test rows under replacement of 12 individual features with values sampled from the corresponding training feature column. Across 1,200 perturbations, mean absolute-SHAP rank Spearman correlation was 0.9671 and mean top-10 Jaccard overlap was 0.8893. Perturbations preserve the replaced feature's observed marginal value support, but can create implausible feature combinations; this is not causal validation.
- Artifacts: `reports/phase11/run_metadata.json`, metrics CSV/JSON, reliability bins/plot, selective review JSON, SHAP row-level and grouped CSV, and SHAP stability plot. Raw data and trained experiment models were not copied into outputs. Experiment models remained in memory; no file was written under `models/`.
- Focused helper tests: **6 passed**. Full experiment command: `.venv\\Scripts\\python.exe scripts/run_phase11_experiment.py` completed successfully. Dataset hash: `21b3cf4e30878150ae8db9386780e23febb613921747dec9e59dccb32f6104d3` (case-insensitive SHA-256).

**Limitations and open items:** results are specific to historical Taiwan 2005 data and must not be presented as Indian borrower or production validation. The dirty-worktree provenance means this is not yet a clean-checkout reproducibility proof. Shipped calibration artifact provenance remains unresolved; this experiment does not reconcile or replace those artifacts. `/v1/score` remains `not_validated`. Stage 5 has not started.
