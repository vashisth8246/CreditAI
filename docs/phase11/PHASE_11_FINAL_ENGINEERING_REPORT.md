# CreditAI Phase 11 Final Engineering Report

**Date:** 2026-11-01
**Branch:** `phase11-final-verification`
**Commit at original inspection:** `932c63f` (`Add KNN model and provider-neutral CI/CD pipeline`)
**Phase 11 source commit:** `f7739f9af25d2983fd2d1da5737a9102d5aac1da` (`Complete Phase 11 research, batch evaluation and reproducibility`)
**Follow-up:** A documentation-only commit recorded the postcommit archive verification and final source-status matrix.
**Scope:** Final source-control audit, Phase 11 staging/commit, and CI readiness follow-through. No production deployment was performed.

## Stage status

| Stage | Scope | Final Status | Evidence |
|---|---|---|---|
| 1 | Repository audit and plan | PASS | `docs/phase11/IMPLEMENTATION_PLAN.md` and repository history. |
| 2 | UI, Gender labels, dashboard/API behavior | PASS | The clean GitHub Actions PR run passed frontend tests, lint, TypeScript, and production build. |
| 3 | CSV/Excel batch evaluation | PASS | Backend CI passed in the clean GitHub Actions PR run; earlier Windows TestClient stall and WSL result remain historical local-environment evidence. |
| 4 | Controlled Taiwan research experiments | PASS WITH LIMITATIONS | Research implementation and saved evidence were included in committed source validated by CI. Fresh UCI network acquisition remains unverified; Taiwan remains research/demo only. |
| 5 | White paper, docs, full testing, Docker/CI preparation | PASS WITH LIMITATIONS | Clean GitHub Actions verified backend, frontend, and immutable release packaging. Docker runtime and fresh UCI network acquisition remain unverified. |

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
| Full backend suite | PASS (GitHub Actions) | The Windows command collected 148 tests, passed the first eight, then stalled at `test_health_endpoint` and was interrupted without a summary. The later clean GitHub Actions Backend Tests job passed; exact test count was not included in supplied evidence. |
| CSV/XLSX HTTP acceptance | PASS (GitHub Actions) | Backend Tests passed on the clean GitHub Actions PR run. Historical WSL report recorded 22 passing batch tests; the Windows TestClient stall remains documented. |
| Frontend clean install | PASS (GitHub Actions) | Windows `npm ci` previously failed with `EPERM` unlinking Rolldown's Windows native binary; isolated retries were blocked by the local dependency environment. The clean GitHub Actions frontend job passed. |
| Frontend tests | PASS (GitHub Actions) | Historical temporary-copy run showed 22 passes and a failed test file because React was missing after failed install. The later clean GitHub Actions frontend job passed. |
| Frontend lint | PASS (GitHub Actions) | Historical local lint could not find Oxlint after dependency installation failed. The GitHub Actions frontend job passed lint. |
| TypeScript | PASS (GitHub Actions) | Historical Windows/isolated `npx tsc -b` lacked the local compiler and could not resolve npm registry DNS; no source diagnostic was produced. The GitHub Actions frontend job passed TypeScript. |
| Frontend build | PASS (GitHub Actions) | Historical local build lacked Vite/TypeScript executables after dependency installation failed. The clean GitHub Actions frontend job passed production build. |
| Dataset local SHA | PASS | `python scripts/fetch_phase11_dataset.py --verify-only` confirmed expected SHA-256 `21b3cf4e30878150ae8db9386780e23febb613921747dec9e59dccb32f6104d3`. |
| Dataset isolated download | NOT RUN | In an isolated empty path, fetch failed before download because DNS resolution failed (`getaddrinfo failed`). No dataset was written there. |
| Full research reproduction | PASS | The runner completed in an isolated output directory from the dirty worktree. Dataset/split hashes matched; selective JSON matched exactly; SHAP CSV was byte-identical; metric CSV values matched within `1e-12`; JSON float delta was at most `1.5e-14`. Saved evidence was preserved; temporary comparison outputs were removed. |
| Saved metric agreement | PASS | CSV and JSON each contain nine rows; field-by-field numeric values match within `1e-12`. |
| Staged source-control audit | PASS | 41 intended files only; staged diff check passed; no calibration/model files, raw dataset, secrets, logs, caches, or temporary outputs staged. |
| Immutable release packaging | PASS (GitHub Actions) | Package Immutable Release passed and produced `creditai-release-689ff1941a0aa29742eca6ddccd2d6fe450293b8` and `frontend-dist-689ff1941a0aa29742eca6ddccd2d6fe450293b8`. |
| Docker | NOT VERIFIED | `docker version` could not start the Windows system stub (`Access is denied`). No build or container runtime is claimed. |
| GitHub Actions | PASS | PR #1, branch `phase11-final-verification`, workflow `CreditAI CI and CD`, run `41286784346`, trigger `pull_request`, result SUCCESS. Backend Tests, Frontend Tests/Lint/TypeScript/Build, and Package Immutable Release passed. Both deployment jobs were skipped; no deployment occurred. |
| Clean checkout source completeness | PASS | A temporary archive of commit `f7739f9af25d2983fd2d1da5737a9102d5aac1da` contains the app/tests, research code and evidence, Docker files, and all three dashboard assets; it excludes the Taiwan workbook. `frontend/dist` is absent as expected because CI builds it. |

Warnings were not suppressed. Model scoring emitted scikit-learn 1.9.0 artifact versus 1.9.1 runtime warnings, along with visible Starlette, Pydantic, and SHAP deprecations.

## Research results

The saved experiment uses seed 42 and stratified 70/15/15 splits (21,000/4,500/4,500 rows). It records dataset and split hashes, Python/package versions, Logistic Regression, Random Forest, XGBoost, raw/Platt/isotonic test metrics, a validation-selected review margin of 0.20, and SHAP perturbation results. The full table and method details are in the white paper.

Results are mixed: Random Forest has the highest ROC-AUC (0.7816); XGBoost has the highest average precision (0.5588); Platt-calibrated Random Forest has the lowest Brier score (0.1349), log loss (0.4288), and ECE (0.0083). The saved artifacts were not overwritten; a reproduced copy was written to an isolated temporary directory and removed after comparison. The dataset is Taiwan research/demo only and does not establish Indian borrower or production lending performance.

## Calibration limitation

`models/calibration_model.joblib` remains unchanged. SHA-256: `6b94f41d3521c37e22d41b91e505006f1c737d022c214f803a5b9a057f185cdc`; class `src.calibration.calibrate.PlattCalibrator`; slope `0.47414481616618126`; intercept `-1.2645029152597382`. Loading warns it was serialized under scikit-learn 1.9.0 while runtime is 1.9.1. The original fitting dataset, split, and script remain unknown, and the previously documented discrepancy remains unresolved.

## Git, clean-checkout, and release limitations

At initial inspection, working tree had 13 modified tracked files and numerous untracked files. The frontend lockfile is tracked at `frontend/package-lock.json`; the 87-byte root `package-lock.json` is unrelated and remains unstaged. The three required dashboard JSON inputs and Phase 11 research sources/evidence are tracked in local commit `f7739f9`. A postcommit Git archive verified these files and confirmed the raw Taiwan workbook is absent. Raw Taiwan and LendingClub data remain excluded by `/Data/` in `.gitignore`.

The CI workflow uses Python 3.11 and Node 24 and makes packaging depend on backend and frontend checks. The successful PR run verified the committed code and immutable release package. Docker remains unverified. GitHub Actions reported Node.js 20 deprecation notices for some action versions being forced onto Node.js 24; the `ubuntu-latest` migration notice was informational. These warnings did not invalidate the successful run.

## Safety boundary

- `/health`, `/v1/status`, and `/v1/score` continue to state production scoring is `not_validated` in source.
- Taiwan XGBoost/KNN models remain research/demo assets.
- No Indian borrower validation or regulatory approval is claimed.
- Non-default complement is exactly `1 - PD` and is not guaranteed repayment.
- No shipped model, calibration artifact, or previous research evidence was replaced.

## Readiness classification

| Dimension | Status |
|---|---|
| Engineering clean CI | PASS |
| GitHub Actions | PASS |
| Backend CI | PASS |
| Frontend CI, lint, TypeScript, production build | PASS |
| Immutable release packaging | PASS |
| Deployment | NOT PERFORMED |
| Docker | NOT VERIFIED |
| Fresh UCI network acquisition | NOT VERIFIED |
| Calibration original provenance | UNKNOWN / DOCUMENTED LIMITATION |
| Indian lending validation | NOT VALIDATED |
| Production lending readiness | NOT VALIDATED |

**Phase 11 completion decision: COMPLETE WITH DOCUMENTED LIMITATIONS.** Clean committed-source CI passed on GitHub Actions PR #1. Earlier Windows TestClient and npm failures remain part of the record as local-environment limitations; the later clean runner verified backend, frontend, and packaging. No deployment occurred. Docker, fresh UCI network acquisition, and original calibration training provenance remain unverified or unknown. Indian lending validation and production lending readiness are not validated, and `/v1/score` remains `not_validated`.

## Required next steps

1. Keep calibration provenance unresolved until original evidence is recovered; do not replace the shipped artifact based on an undocumented discrepancy.
2. Verify Docker build/runtime separately when a working Docker environment is available.
3. Fresh UCI network acquisition remains unverified; preserve the dataset hash check before any future experiment.
4. Continue to preserve `/v1/score` as `not_validated`; do not claim Indian borrower validation or production lending readiness.
