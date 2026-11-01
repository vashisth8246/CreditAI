# CreditAI Phase 11 Final Engineering Report

**Date:** 2026-11-01
**Branch:** `main`
**Commit at inspection:** `932c63f` (`Add KNN model and provider-neutral CI/CD pipeline`)
**Final local commit:** `f7739f9af25d2983fd2d1da5737a9102d5aac1da` (`Complete Phase 11 research, batch evaluation and reproducibility`)
**Scope:** Final source-control audit, Phase 11 staging/commit, and CI readiness follow-through. No production deployment was performed.

## Stage status

| Stage | Scope | Final Status | Evidence |
|---|---|---|---|
| 1 | Repository audit and plan | PASS | `docs/phase11/IMPLEMENTATION_PLAN.md` and repository history. |
| 2 | UI, Gender labels, dashboard/API behavior | PARTIAL | Current source inspection confirms API snapshot flow, historical source date, retrieval timestamp, model-specific evaluation failures, display-only Gender label, and `/v1/score` safety state. Full frontend re-verification is blocked by dependency installation. |
| 3 | CSV/Excel batch evaluation | PARTIAL | Current seven-sheet synthetic acceptance test passed; complete Windows HTTP suite stalls at first health request. Prior WSL 22-test report is historical, not freshly rerun. |
| 4 | Controlled Taiwan research experiments | PARTIAL | Research helper tests pass; the experiment reproduced in an isolated output directory from the current dirty worktree and local dataset. Fresh UCI download and clean-Git-checkout reproduction remain blocked. |
| 5 | White paper, docs, full testing, Docker/CI preparation | PARTIAL | White paper, reproduction guide, final report, and test matrix created. Full verification, Docker runtime, and real Actions run remain unavailable. |

## Changes in this completion pass

- Added `docs/phase11/CREDITAI_RESEARCH_WHITEPAPER.md`, reporting saved metrics and methods with dataset, calibration, selective review, SHAP, architecture, and validation limitations.
- Added `docs/phase11/REPRODUCTION_GUIDE.md` with checked commands and explicit unverified labels.
- Added this report and `docs/phase11/FINAL_TEST_MATRIX.md`.
- Changed `frontend/package.json` lint command to target `src`, `tests`, and `vite.config.ts`. The prior reported count of 12,270 warnings came from scanning dependencies; the source-only scope addresses that waste without disabling rules. The new command could not be run because Oxlint dependencies were unavailable after clean installation failed.
- Changed `scripts/run_phase11_experiment.py` to accept `--output-dir`, enabling a reproducibility run without overwriting saved evidence.
- Audited and staged a 41-file Phase 11 set: Stage 2–3 app/test changes, research runner/module/tests, dataset verifier, dependency snapshot, required Phase 9 dashboard JSON, saved Phase 11 evidence, Stage 5 documentation, and Docker build files needed for the requested Docker check. The staged diff passes `git diff --cached --check`.
- Excluded the raw Taiwan workbook, virtual environments, node_modules, caches, temporary reproduction output, root `package-lock.json`, Phase 10 reports/assets, scratch files, and the separate Render deployment document. The staged set contains no model artifact changes; the calibration hash is unchanged.
- A high-confidence staged-file scan found no private keys, GitHub tokens, AWS access-key patterns, or bearer credentials. Raw-data directories remain ignored.
- No shipped model, calibration artifact, research output, or raw dataset was modified. No Azure/Render/AWS resource was created.

At inspection, pre-existing tracked modifications included `README.md`; `frontend/src/App.tsx`, `BatchEvaluation.tsx`, `PredictionWorkspace.tsx`, `analytics.ts`, `api.ts`, and `batch.ts`; `frontend/tests/analytics.test.ts` and `batch.test.ts`; `src/api/app.py` and `batch_service.py`; and `tests/test_api_integration.py` and `test_batch_workflow.py`. These changes were preserved and included where they belong to Phase 11. The staged set was reviewed file by file. Separate Phase 10, Render, and scratch changes remain unstaged and untouched.

## Verification and evidence

| Area | Result | Evidence |
|---|---|---|
| Focused research tests | PASS | `python -m pytest tests/test_phase11_research.py -v --tb=short` — 6 passed in 6.76s. |
| Non-HTTP backend tests | PASS | `python -m pytest tests/ --ignore=tests/test_api_integration.py --ignore=tests/test_batch_workflow.py --ignore=tests/test_phase23_benchmark.py --ignore=tests/test_phase8_features.py -v --tb=short` — 92 passed, 36 warnings in 38.69s. |
| Seven-sheet synthetic acceptance | PASS | `python -m pytest tests/test_batch_workflow.py -k synthetic_seven_sheet_workbook_inspects_and_scores_eligible_sheets -v --tb=short` — 1 passed, 21 deselected, 17 warnings in 9.43s. |
| Full backend suite | PARTIAL | `python -m pytest tests/ -v --tb=short` collected 148 tests and passed the first eight contract tests, then stalled at `test_health_endpoint`; interrupted. No final pytest summary was produced. |
| CSV/XLSX HTTP acceptance | PARTIAL | The focused XLSX export endpoint test similarly stalled at its first TestClient request. Earlier `docs/phase11/STAGE_3_4_BLOCKER_RESOLUTION.md` records 22 batch tests passing under WSL; WSL was inaccessible in this pass, so not counted as a fresh pass. |
| Frontend clean install | FAIL | `npm ci` in existing tree failed with `EPERM` unlinking Rolldown's Windows native binary. In an isolated copy it ended with npm `Exit handler never called`; offline retry failed `ENOTCACHED` for Vite. Registry DNS was unavailable. |
| Frontend tests | FAIL | Temporary-copy `npm test` showed 22 pass and one failed test file because React was missing after failed installation (`ERR_MODULE_NOT_FOUND`). This is an incomplete dependency environment, not a source pass. |
| Frontend lint | FAIL | `npm run lint` failed because the Oxlint executable was missing after clean installation failed. Lint target was narrowed; rerun required. |
| TypeScript | FAIL | `npx tsc -b` failed while resolving registry package `tsc` (`ENOTFOUND`) because the local TypeScript compiler was missing after installation failure. No TypeScript source diagnostic was produced. A previous Linux temp-copy report records this command passing after `npm ci`; GitHub Actions still has not confirmed it. |
| Frontend build | FAIL | `npm run build` failed because Vite/TypeScript binaries were missing after clean installation failed. |
| Dataset local SHA | PASS | `python scripts/fetch_phase11_dataset.py --verify-only` confirmed expected SHA-256 `21b3cf4e30878150ae8db9386780e23febb613921747dec9e59dccb32f6104d3`. |
| Dataset isolated download | NOT RUN | In an isolated empty path, fetch failed before download because DNS resolution failed (`getaddrinfo failed`). No dataset was written there. |
| Full research reproduction | PASS | The runner completed in an isolated output directory from the dirty worktree. Dataset/split hashes matched; selective JSON matched exactly; SHAP CSV was byte-identical; metric CSV values matched within `1e-12`; JSON float delta was at most `1.5e-14`. Saved evidence was preserved; temporary comparison outputs were removed. |
| Saved metric agreement | PASS | CSV and JSON each contain nine rows; field-by-field numeric values match within `1e-12`. |
| Staged source-control audit | PASS | 41 intended files only; staged diff check passed; no calibration/model files, raw dataset, secrets, logs, caches, or temporary outputs staged. |
| Docker | NOT RUN | `docker version` could not start the Windows system stub (`Access is denied`). No build or container runtime is claimed. |
| GitHub Actions | NOT RUN | `gh auth status` reports no logged-in account and `git ls-remote origin HEAD` failed on DNS. No real Actions run; workflow syntax and job logic were not externally validated. |
| Clean checkout source completeness | PASS | A temporary archive of commit `f7739f9af25d2983fd2d1da5737a9102d5aac1da` contains the app/tests, research code and evidence, Docker files, and all three dashboard assets; it excludes the Taiwan workbook. `frontend/dist` is absent as expected because CI builds it. |

Warnings were not suppressed. Model scoring emitted scikit-learn 1.9.0 artifact versus 1.9.1 runtime warnings, along with visible Starlette, Pydantic, and SHAP deprecations.

## Research results

The saved experiment uses seed 42 and stratified 70/15/15 splits (21,000/4,500/4,500 rows). It records dataset and split hashes, Python/package versions, Logistic Regression, Random Forest, XGBoost, raw/Platt/isotonic test metrics, a validation-selected review margin of 0.20, and SHAP perturbation results. The full table and method details are in the white paper.

Results are mixed: Random Forest has the highest ROC-AUC (0.7816); XGBoost has the highest average precision (0.5588); Platt-calibrated Random Forest has the lowest Brier score (0.1349), log loss (0.4288), and ECE (0.0083). The saved artifacts were not overwritten; a reproduced copy was written to an isolated temporary directory and removed after comparison. The dataset is Taiwan research/demo only and does not establish Indian borrower or production lending performance.

## Calibration limitation

`models/calibration_model.joblib` remains unchanged. SHA-256: `6b94f41d3521c37e22d41b91e505006f1c737d022c214f803a5b9a057f185cdc`; class `src.calibration.calibrate.PlattCalibrator`; slope `0.47414481616618126`; intercept `-1.2645029152597382`. Loading warns it was serialized under scikit-learn 1.9.0 while runtime is 1.9.1. The original fitting dataset, split, and script remain unknown, and the previously documented discrepancy remains unresolved.

## Git, clean-checkout, and release limitations

At initial inspection, working tree had 13 modified tracked files and numerous untracked files. The frontend lockfile is tracked at `frontend/package-lock.json`; the 87-byte root `package-lock.json` is unrelated and remains unstaged. The three required dashboard JSON inputs and Phase 11 research sources/evidence are tracked in local commit `f7739f9`. A postcommit Git archive verified these files and confirmed the raw Taiwan workbook is absent. Raw Taiwan and LendingClub data remain excluded by `/Data/` in `.gitignore`.

The CI workflow uses Python 3.11 and Node 24 and makes packaging depend on backend and frontend checks. Docker remains unverified. GitHub Actions remains not run because `gh` is unauthenticated and the remote DNS lookup failed. A normal push to `main` could enter the workflow's production deployment job if `vars.DEPLOYMENT_PROVIDER` is configured; that setting could not be inspected, and this task does not authorize deployment, so no push was made.

## Safety boundary

- `/health`, `/v1/status`, and `/v1/score` continue to state production scoring is `not_validated` in source.
- Taiwan XGBoost/KNN models remain research/demo assets.
- No Indian borrower validation or regulatory approval is claimed.
- Non-default complement is exactly `1 - PD` and is not guaranteed repayment.
- No shipped model, calibration artifact, or previous research evidence was replaced.

## Readiness classification

| Dimension | Status |
|---|---|
| Engineering readiness | PARTIAL |
| Research reproducibility | PARTIAL |
| Exhibition/demo readiness | PARTIAL |
| Indian lending validation | NOT APPLICABLE |
| Production lending readiness | NOT APPLICABLE |

**Phase 11 completion decision: PARTIAL.** Clean-checkout source completeness is resolved in the local commit, but no authenticated push or real Actions run is available. The failed Windows frontend install/TestClient checks remain unresolved pending clean Linux CI. Docker and fresh network dataset acquisition also remain unverified.

## Required next steps

1. When GitHub access and DNS are available, use a nondeploying PR path or confirm the production provider variable is unset before triggering CI; do not push to `main` while deployment behavior is unknown. The local commit is `f7739f9af25d2983fd2d1da5737a9102d5aac1da`.
2. Inspect a real GitHub Actions run. If it fails, fix only the demonstrated issue and rerun without disabling checks.
3. Run Docker build/runtime verification in a working Docker environment if available.
4. Keep calibration provenance unresolved until original evidence is recovered; continue to preserve `/v1/score` as `not_validated`.
