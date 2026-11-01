# Phase 11 Stage 3–4 Verification Audit

**Audit date:** 2026-11-01
**Scope:** Independent source/output/test review of Stages 3 and 4 in the current Windows worktree.
**Actions:** Read-only inspection and test execution, plus creation of this audit report. No feature implementation, output regeneration, staging, commit, push, merge, or deployment was performed.

## Executive result

- **Stage 3: PARTIAL.** Batch service behavior is substantially verified, including the seven-sheet acceptance test and a direct CSV service-to-export flow. HTTP upload/export endpoints could not be verified because the Windows `TestClient` suite hung at its first request. Frontend verification is currently blocked by an incomplete, locked `node_modules` installation; the attempted frontend commands did not all complete successfully.
- **Stage 4: PARTIAL.** Source, saved metrics, metadata, split hashes, and calibration provenance were inspected. The six research-helper tests pass, and saved metrics match the previous rounded report. The experiment was not rerun, as requested. It cannot be reproduced from a clean checkout in the present repository state because the dataset and Stage 4 implementation/evidence are not tracked, and the frontend lock/data assets are also untracked.
- **No evidence from this audit changes `/v1/score` from `not_validated`.** Taiwan research is not production or India validation.

## Stage 3 — Batch Evaluation

| Verification item | Result | Evidence and limits |
|---|---|---|
| CSV upload/parsing and validation | **PARTIAL** | `read_workbook` recognizes CSV and parses BOM/encoding/delimiter variants. A direct service-flow check passed for CSV parse, schema validation, prediction, invalid-row error, references, counts, and export generation. The HTTP upload route was not verified in this Windows run. |
| XLSX and XLS upload behavior | **PARTIAL** | XLSX parsing, sheet handling, and formula detection are implemented in `src/api/batch_service.py`; the seven-sheet XLSX acceptance test passed. The XLS parser successfully opened the existing local UCI `.xls` workbook (one worksheet). The HTTP upload route remains unverified. `.xls` formula detection is explicitly unavailable in source. |
| Seven-sheet synthetic workbook acceptance | **PASS** | `tests/test_batch_workflow.py::test_synthetic_seven_sheet_workbook_inspects_and_scores_eligible_sheets` passed independently. It exercised direct service functions and actual model scoring without using HTTP. |
| Worksheet detection/classification | **PASS** | The acceptance test confirmed `Portfolio_A`, reordered `Portfolio_B`, incomplete-value `Portfolio_C`, and metadata-bearing `Portfolio_D` as usable; `Invalid_Sheet` and `Summary` need mapping; `Empty_Sheet` is blank. |
| Valid and invalid borrower rows | **PASS** | The seven-sheet test confirmed four successful predictions and one invalid row due to missing required `AGE`, preserving row order and source rows. The direct CSV flow also confirmed one successful and one rejected row. |
| Duplicate borrower references | **PASS** | The seven-sheet test used duplicate `synthetic-a` references, asserted warnings on both rows, and asserted both records remain in predictions. No deduplication occurs. |
| PD, complement, and risk category | **PARTIAL** | `predict_workbook` delegates scoring to `src.inference.predictor.predict` and returns probability/class/risk category. `build_export_rows` computes `1 - PD` only for finite numeric probabilities in `[0,1]`; the focused complement test passed, including invalid and failed rows. The full route-level response and risk-category API contract were not exercised because HTTP tests hung. |
| Row errors and worksheet provenance | **PASS** | Direct acceptance assertions confirmed `sheet_name`, original spreadsheet `source_row`, borrower references, result status, and an error for the missing value. The CSV service-flow check confirmed the invalid row’s reference, error, source row, and `CSV` sheet name. |
| CSV and Excel exports | **PARTIAL** | Direct service calls to `build_csv` and `build_xlsx` succeeded; CSV contained the complement column and the XLSX output had a ZIP signature. The focused complement/export helper test passed. Endpoint response headers, HTTP payload limits, and download responses remain unverified. |
| Counts and rejected-row reasons | **PARTIAL** | Direct CSV flow asserted 2 total / 1 scored / 1 failed and retained a row-level error message. Seven-sheet assertions verified result count/order/status but did not assert every per-sheet summary count. Route-level counts remain unverified. |

### Stage 3 commands and actual results

1. `.venv\Scripts\python.exe -m pytest tests/test_batch_workflow.py -v --tb=short`
   **Result:** Collected 22 tests, then remained at the first test (`test_inspect_valid_csv_with_bom_and_reference`) for 30 seconds without completing. I interrupted the process; it exited 1 and did not produce an HTTP exception trace. Earlier runs in this workspace identified the Windows TestClient/Proactor loopback `socketpair` stall. This audit did not obtain a more specific traceback.

2. `.venv\Scripts\python.exe -m pytest tests/test_batch_workflow.py -k synthetic_seven_sheet_workbook_inspects_and_scores_eligible_sheets -v --tb=short`
   **Result:** **1 passed, 21 deselected**. Existing sklearn serialization warnings (artifact 1.9.0, runtime 1.9.1), Pydantic deprecations, and SHAP deprecations were visible and not suppressed.

3. `.venv\Scripts\python.exe -m pytest tests/test_batch_workflow.py -k exports_compute_non_default_complement -v --tb=short`
   **Result:** **1 passed, 21 deselected**; warnings as above.

4. Direct in-process service check using `read_workbook`, `inspect_workbook`, `predict_workbook`, `build_csv`, and `build_xlsx`
   **Result:** PASS for CSV parsing, one valid plus one invalid row, duplicate-reference warnings, row reference/error/provenance, summary counts, CSV output, and XLSX byte output. The same check opened the local `.xls` UCI workbook successfully. This bypasses HTTP and is not a substitute for endpoint integration testing.

**Linux/CI command for the blocked HTTP suite:** `python -m pytest tests/test_batch_workflow.py -v --tb=short` from the repository root, on a runner with functioning loopback sockets. The complete upload-to-export route must pass there before Stage 3 is called fully verified.

### Frontend checks

Attempted from `frontend/`:

- `npm ci`: **failed twice** with `EPERM: operation not permitted, unlink ...\node_modules\@rolldown\binding-win32-x64-msvc\rolldown-binding.win32-x64-msvc.node`.
- `npm test`: **failed overall**. The batch tests reported 22 passing; `analytics.test.ts` failed to import `react` (`ERR_MODULE_NOT_FOUND`). This run overlapped the first `npm ci`, so it is not a clean frontend test result.
- `npm run lint`: failed because `node_modules/oxlint/bin/oxlint` was missing.
- `npm run build`: failed because `node_modules/typescript/bin/tsc` was missing.

The checks were initially launched while `npm ci` was also running; therefore the test/lint/build outcomes reflect an inconsistent dependency tree and cannot establish source failures or a pass. A sequential reinstall was then attempted and still failed on the locked Rolldown binary. No tracked package files were modified by `npm ci`, but the ignored local `node_modules` tree is incomplete. Re-run sequentially in a clean environment: `npm ci`, `npm test`, `npm run lint`, `npm run build`.

## Stage 4 — Research Verification

| Verification item | Result | Evidence and limits |
|---|---|---|
| Dataset loading, target, and feature selection | **PASS** | `src/data_loader.py` reads the UCI workbook with `header=1`; target is `default payment next month`. `src/preprocessing.py` separates target, drops `ID`, and consolidates documented categorical codes. `src/feature_engineering.py` adds deterministic row-derived features. The run metadata records 30,000 rows, 25 input columns, zero nulls, and target counts 23,364 / 6,636. |
| Train/validation/locked-test separation | **PASS** | Runner uses seed 42, stratified 70/15/15 index splits: 21,000 / 4,500 / 4,500. Three split-index SHA-256 hashes are saved in `reports/phase11/run_metadata.json`. |
| Leakage prevention | **PASS, with caveat** | Target is extracted and `ID` dropped before modeling; feature engineering is row-wise/deterministic with no fitted global statistics. The split is made after these deterministic transforms. No test labels enter training, calibration, model configuration, or threshold-selection calls in source. This is a source-level finding; it does not independently prove no prior exploratory human tuning occurred. |
| Model configurations | **PASS** | Runner uses scaled, balanced Logistic Regression (`max_iter=1000`); Random Forest (200 trees, depth 10, leaf minimum 20, balanced); XGBoost (300 estimators, depth 5, learning rate .05, subsample/column sample .8, train-derived positive weight). The configurations are fixed in code; all three are reported, with no best-model selection based on test results. |
| Platt/isotonic fit split | **PASS** | Both calibrators receive only validation predictions and `y_val`. Platt fits logistic regression on clipped logit probabilities; isotonic fits `IsotonicRegression` on raw probabilities. Each is then applied to test predictions. |
| Locked-test metric calculations | **PASS** | `probability_metrics` computes ROC-AUC, average precision, Brier, clipped log loss, and ECE. CSV and JSON results match each other and match the prior report to its published four-decimal rounding. |
| ECE definition | **PASS** | Ten equal-width bins on `[0,1]`, index `floor(p * n_bins)` with `p=1` assigned to the last bin; empty bins omitted. ECE is the sample-count-weighted absolute difference between observed rate and mean predicted probability. |
| Selective-review selection and referral formula | **PASS** | The validation grid is 50 margins over `[0, 0.49]`. A row is referred when `abs(p - 0.5) < margin`; accepted when `>= margin`; accepted class is `p >= 0.5`. Candidate is chosen by lowest validation accepted-set error among candidates meeting 80% minimum validation coverage, then higher coverage, then smaller margin. The selected margin is 0.20. |
| Coverage and accepted-case error | **PASS** | Coverage = accepted count / total; referred fraction = 1 − coverage; selective risk = accepted classification errors / accepted count. Saved validation result: 3,655/4,500 accepted (81.22%), 505 accepted errors (13.82%). Locked test: 3,611/4,500 accepted (80.24%), 473 errors (13.10%). |
| SHAP method and stability calculations | **PASS, narrow interpretation** | Uses `shap.TreeExplainer` on the in-memory XGBoost model and the first 100 fixed test rows. For 12 selected features, replaces one feature at a time with empirical training-column values using RNG seed 42. Compares absolute SHAP rank vectors using Spearman correlation and top-10 sets using Jaccard intersection/union. Saved row-level CSV has 1,200 perturbations; its grouped summary yields mean Spearman 0.9671 and mean Jaccard 0.8893. These marginal replacements can create invalid joint feature combinations; result is not causal or broad robustness validation. |
| Dataset/split hashes, seed, versions | **PASS as recorded** | Metadata contains dataset SHA-256 `21b3cf4e30878150ae8db9386780e23febb613921747dec9e59dccb32f6104d3`; seed 42; three split hashes; Python 3.11.9, NumPy 2.4.6, pandas 3.0.6, scikit-learn 1.9.1, XGBoost 3.2.0, SHAP 0.51.0. Worktree is explicitly recorded dirty. |
| Saved outputs versus previous report | **PASS for numerical consistency** | `probability_metrics.csv` and `.json` contain identical nine rows. Metric values match the prior report rounded to four decimals. `selective_review.json` matches the reported 0.20 margin, 80.24% test coverage, and 13.10% accepted error. Grouped SHAP CSV reproduces the reported means. This audit did not rerun the experiment or modify outputs. |
| Holdout influence on tuning | **PASS by static code-path inspection** | The selected rule receives `y_val` and validation-calibrated XGBoost probabilities only. The calibrators receive validation only. Hyperparameters and all three model configurations are fixed in source. Test labels are passed only to metric/reliability/selective evaluation. The code does not compare metrics to choose a model/calibrator. This finding is limited to the current runner; earlier unrecorded exploratory work cannot be ruled out. |

### Shipped calibration artifact provenance

**Result: PARTIAL; exact provenance remains unresolved.** The tracked `models/calibration_model.joblib` loads as `src.calibration.calibrate.PlattCalibrator`, with slope `0.47414481616618126`, intercept `-1.2645029152597382`, and SHA-256 `6b94f41d3521c37e22d41b91e505006f1c737d022c214f803a5b9a057f185cdc`. The registry points the serving model to this separate artifact. The visible sklearn `InconsistentVersionWarning` says the embedded `LogisticRegression` was saved under 1.9.0 and is loaded under 1.9.1.

`reports/phase_9_brier_discrepancy_review.md` documents that a fresh current-code fit on the documented validation split has different parameters (slope 0.85795861, intercept -1.09014010), and attributes the discrepancy to a different/difficult-to-trace calibrator fit or artifact history. The present audit confirms the artifact’s class and parameters but cannot establish the original training commit/data/fitting procedure. The artifact was not replaced or edited.

## Clean-checkout reproducibility and untracked inputs

**Result: FAIL for reproduction from the currently tracked tree.**

- `Data/credit_default/default of credit card clients.xls` is ignored by root `.gitignore` (`/Data/`; the lowercase configured `data/...` pattern is also ignored). It is present locally and its SHA matches metadata, but is not tracked. `scripts/run_phase11_experiment.py` calls `find_dataset_path()` and requires the file; a clean checkout cannot run this experiment without a separately supplied dataset. No fetch-and-hash reproduction script is included.
- `scripts/run_phase11_experiment.py`, `src/research/phase11/`, `tests/test_phase11_research.py`, and generated `reports/phase11/` are untracked. They must be deliberately included in a future source/evidence change if the experiment is to be available in a clean checkout.
- `frontend/package-lock.json` is untracked. A clean checkout containing only tracked files cannot reliably run the Dockerfile’s `npm ci` copy/build steps until the lockfile is committed or otherwise provided.
- `frontend/public/data/` is untracked. It contains `phase_10_dataset_inventory.json`, `phase_6_1_dataset_inventory.json`, `phase_6_1_feature_inventory.json`, `phase_6_1_lendingclub_summary.json`, `phase_9_dataset_inventory.json`, `phase_9_feature_inventory.json`, `phase_9_lendingclub_summary.json`, `uci_taiwan_eval.json`, and `uci_taiwan_knn_eval.json`. The current dashboard API needs the three Phase 9 summary/inventory JSON files; current frontend/model evaluation flows may need the Taiwan evaluation JSON. Their absence in a clean checkout can break those views even though the Docker ignore file allowlists the four Phase 9/Taiwan files.
- `requirements.txt` pins scikit-learn 1.9.1 but leaves XGBoost, SHAP, NumPy, pandas, and several other packages on ranges. Metadata records the versions used, but those ranges do not by themselves guarantee the same environment on a future clean install.
- Git status did not show any modified tracked model artifact. The research runner was not rerun during this audit, so existing research outputs were left untouched.

## Source inspected

Stage 3: `src/api/batch_service.py`, relevant routes in `src/api/app.py`, `tests/test_batch_workflow.py`, `tests/test_api_integration.py`, `frontend/src/batch.ts`, `frontend/src/BatchEvaluation.tsx`, `frontend/tests/batch.test.ts`, `frontend/package.json`, `frontend/package-lock.json`, root and frontend `.gitignore` files.

Stage 4: `scripts/run_phase11_experiment.py`, `src/research/phase11/core.py`, `tests/test_phase11_research.py`, `src/config.py`, `src/data_loader.py`, `src/preprocessing.py`, `src/feature_engineering.py`, `src/inference/model_registry.py`, `src/inference/predictor.py`, `src/calibration/calibrate.py`, `reports/phase11/run_metadata.json`, `probability_metrics.csv`/`.json`, `reliability_bins.json`, `selective_review.json`, `shap_stability.csv`, `shap_stability_summary.csv`, and `reports/phase_9_brier_discrepancy_review.md`.

## Discrepancies from previous reports

1. Previous Stage 3 reports described focused backend and frontend/lint/build checks as passing at earlier points. In this audit, the isolated seven-sheet and complement tests passed, but the complete HTTP suite stalled at its first request. Current frontend checks are blocked by the locked Rolldown file and incomplete `node_modules`; the test invocation reported 22 passing batch tests but failed the analytics test import. Therefore the earlier frontend pass is historical evidence, not independently reproduced here.
2. The previous Stage 4 numeric summary is consistent with saved files. This audit confirms the exact saved values but did **not** independently rerun model fitting; it is not a clean-checkout replication.
3. Earlier wording described the SHAP perturbations as constrained/valid. More precisely, each changed feature is sampled from that column’s training values, but the resulting multi-feature row is not constrained to the empirical joint data manifold and may be implausible.
4. The previous reports already noted dirty-worktree and shipped calibration provenance limitations. This audit confirms they remain unresolved.

## Remaining blockers and Stage 5 prerequisites

1. Run the entire batch HTTP workflow in Linux/CI with a functioning loopback implementation; include upload, inspect, predict, export, and error cases.
2. Restore a usable frontend dependency tree in a clean environment, track/verify the lockfile, then run `npm ci`, `npm test`, `npm run lint`, and `npm run build` sequentially.
3. Decide how the Taiwan research dataset will be obtained in a clean environment without committing raw data; document/license-check the acquisition and enforce the saved SHA-256 before running.
4. Decide which untracked dashboard/evaluation JSON files are intended production/frontend inputs and ensure clean Docker/GitHub builds include exactly those needed files.
5. Make research code, tests, metadata, and generated evidence reproducible from a clean commit. Pin or otherwise record all dependencies that materially affect results.
6. Resolve or prominently preserve the shipped calibration artifact’s unknown provenance. Do not replace it silently; keep scikit-learn warnings visible.
7. Complete Stage 5 citations, paper/reproduction documentation, full test matrix, clean build/runtime checks, and final safety review. Keep all research/demo labels and `/v1/score: not_validated` intact.

No Stage 5 work was started during this verification audit.
