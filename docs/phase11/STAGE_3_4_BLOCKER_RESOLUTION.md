# Phase 11 Stage 3–4 Blocker Resolution

**Date:** 2026-11-01
**Scope:** Resolve only blockers from `STAGE_3_4_VERIFICATION.md`.
**Restrictions observed:** No source-control staging, commit, push, merge, or deployment. Stage 5 was not started. No model/calibration artifacts or existing Phase 11 research outputs were changed.

## Result summary

| Priority | Result | Current state |
|---|---|---|
| Clean-checkout reproducibility | **PARTIAL** | Added a UCI fetch-and-SHA-verify script, made the experiment fail closed on SHA mismatch, and pinned the measured Python package set. Full clean-Git reproducibility remains blocked because the relevant files/assets are untracked and raw data is ignored; the no-stage rule prevents tracking them in this turn. |
| Backend Linux integration | **PASS locally; GitHub Actions unrun** | Full 22-test batch HTTP workflow passed in WSL Ubuntu. This is a local Linux run on Python 3.14.4, while the repository workflow specifies Python 3.11. It is not a GitHub Actions run. |
| Frontend clean environment | **PASS locally; Node-version caveat recorded** | Sequential clean-copy install, tests, lint, TypeScript check, and build succeeded on Node 24.13.1 in WSL. npm was 9.2.0. Lint exited 0 with 12,270 warnings and 0 errors. |
| Calibration provenance | **PARTIAL; origin unresolved** | Artifact class, parameters, hash, Git history, and generation code were inspected. It is unchanged since the initial import; its original training run/data provenance are absent. Artifact was not changed. |

## Exact changes made

1. Added `scripts/fetch_phase11_dataset.py`.
   - Uses the official [UCI Default of Credit Card Clients dataset page](https://archive.ics.uci.edu/dataset/350/default%2Bof%2Bcredit%2Bcard%2Bclients), which identifies 30,000 rows, 23 predictors, no missing values, and CC BY 4.0 licensing.
   - Downloads the official UCI dataset ZIP to memory, selects only the expected workbook member, checks archive/member size, verifies SHA-256 `21b3cf4e30878150ae8db9386780e23febb613921747dec9e59dccb32f6104d3`, and only then writes to ignored `Data/credit_default/default of credit card clients.xls`.
   - Existing mismatched local files are not overwritten. `--verify-only` checks the expected local workbook without downloading.
2. Changed `scripts/run_phase11_experiment.py` to call the same SHA verifier immediately after locating the dataset and before loading data or training. A changed or wrong dataset now fails before the experiment runs.
3. Added `requirements-phase11.lock.txt`, an exact dependency-version snapshot for the recorded Phase 11 environment, including the scientific, model, plotting, Excel, API-test, and pytest packages. The run metadata records CPython 3.11.9 and the specific versions. This is a version lock, not a wheel-hash lock.
4. Added this resolution report. No frontend code, batch behavior, dashboard behavior, model behavior, shipped artifact, or saved research output was modified.

## Priority 1 — Reproducibility

### Dataset source and SHA verification

The official UCI page links to `https://archive.ics.uci.edu/static/public/350/default%2Bof%2Bcredit%2Bcard%2Bclients.zip`. The workbook itself remains raw data and is not committed. The local workbook matched the SHA from Phase 11 metadata before this change and passed the new verifier twice.

Commands and actual result:

```text
.venv\Scripts\python.exe scripts/fetch_phase11_dataset.py --verify-only
PASS — SHA-256 21b3cf4e30878150ae8db9386780e23febb613921747dec9e59dccb32f6104d3

.venv\Scripts\python.exe -c "from scripts.fetch_phase11_dataset import verify_file; verify_file()"
PASS — same path and SHA verified
```

The ZIP download branch was not exercised because the verified local copy already exists. The UCI page’s official download link was inspected, but a clean machine download and extraction have not yet been observed end to end. For a clean machine, run `python scripts/fetch_phase11_dataset.py`, then `python scripts/run_phase11_experiment.py`; the runner independently checks the SHA before training.

### Research sources and outputs

The experiment runner, research module, research tests, metadata, metrics, plots, and prior reports are present in the worktree, but **remain untracked**. The new dataset script and dependency lock are also untracked. Since staging and committing are explicitly prohibited, no clean Git checkout can contain these additions yet. The same applies to `docs/phase11/IMPLEMENTATION_PLAN.md`, `STAGE_3_4_VERIFICATION.md`, this report, and `PHASE_11_FULL_REPORT.md`.

### Frontend lockfile and public data

`frontend/package-lock.json` exists and was successfully used by Linux `npm ci`, but it remains untracked. `frontend/public/data/` also remains untracked. Required dashboard inputs currently present there are:

- `phase_9_lendingclub_summary.json`
- `phase_9_dataset_inventory.json`
- `phase_9_feature_inventory.json`

The API snapshot loader requires these three files. `.dockerignore` has explicit allow rules for them, so a local Docker context containing these files includes them; a clean clone cannot include them until they are tracked. `uci_taiwan_eval.json` under `models/` and `uci_taiwan_knn_eval.json` under `models/` are tracked and are the files read by the two backend evaluation routes. The same-named `frontend/public/data/` files are not read by the current frontend API flow. Other untracked Phase 6/10 dashboard JSONs are not required by the current snapshot endpoint.

**Unresolved under the no-stage rule:** research/evidence files, `frontend/package-lock.json`, and the three dashboard files cannot be made part of a clean Git or Docker checkout without a later authorized stage/commit. Docker’s local build was not run; the available `docker` command is a Windows stub with no CLI output, despite returning success. No Docker build is claimed.

### Dependency versions

`requirements-phase11.lock.txt` pins these material versions from the recorded research environment: NumPy 2.4.6, pandas 3.0.6, scikit-learn 1.9.1, XGBoost 3.2.0, SHAP 0.51.0, SciPy 1.17.1, matplotlib 3.11.2, openpyxl 3.1.5, xlrd 2.0.2, and their captured dependencies. The recorded experiment Python was 3.11.9. The dependency lock was installed in WSL with `pip install --no-deps -r requirements-phase11.lock.txt`; the lock enumerates the captured transitive packages explicitly. Linux testing used Python 3.14.4 because that is the Python installed in this WSL distribution, so it is not an exact recreation of GitHub Actions’ Python 3.11 runtime.

## Priority 2 — Backend Linux integration

The full existing route-level batch suite ran in WSL Ubuntu against the current worktree and real tracked model artifacts. It covered CSV/XLSX uploads, validation, worksheet mapping, seven-sheet behavior, predictions, CSV/XLSX exports, formula injection, malformed/oversized input, row errors, duplicate references, and health/scoring safety contracts.

Exact command:

```text
wsl.exe -d Ubuntu -- bash -lc "cd '/mnt/f/NUV ACD/All SEM/7th Sem/ML&DS/New folder (3)/CreditAI' && PYTHONPATH=. /tmp/creditai-phase11-ci/bin/python -m pytest tests/test_batch_workflow.py -v --tb=short"
```

**Result: 22 passed in 18.26 seconds.** The Linux environment was WSL Ubuntu 26.04, CPython 3.14.4, pytest 9.1.1, scikit-learn 1.9.1, XGBoost 3.2.0, FastAPI 0.143.0, HTTPX 0.28.1. The environment was installed from the exact lock in `/tmp`; no environment files were added to the repository.

Visible warnings were retained: scikit-learn artifact 1.9.0 versus runtime 1.9.1 (`InconsistentVersionWarning`), Pydantic config/field deprecations, Starlette’s HTTPX deprecation, and SHAP colormap deprecations. Nothing was suppressed.

This verifies the batch HTTP routes on Linux locally. It does not mean GitHub Actions ran. The repository workflow uses Python 3.11 and runs the broader `tests/` suite; no GitHub Actions run was triggered because no push or dispatch was authorized.

## Priority 3 — Frontend clean verification

Windows `npm ci` continued to fail on the locked Rolldown binary (`EPERM`), and a Windows temp-copy npm invocation ended with npm’s `Exit handler never called!`. The successful verification used a clean Linux temp copy of frontend source, package files, tests, and public files at `/tmp/creditai-frontend-clean`. The repository’s frontend and `node_modules` were not used as the install destination.

Environment: Node 24.13.1 from the `node-linux-x64` registry package; npm 9.2.0 from Ubuntu. Commands ran sequentially, with `set -e`:

```text
npm ci
PASS — 30 packages added; 0 vulnerabilities reported

npm test
PASS — 28 passed, 0 failed

npm run lint
PASS exit code 0 — 12,270 warnings, 0 errors

npx tsc -b
PASS exit code 0

npm run build
PASS — TypeScript project build completed; Vite 8.3.4 produced the production bundle
```

Oxlint scanned 577 files, including installed dependencies, and emitted the 12,270 warnings. It reported zero errors and returned exit code 0. This is a successful command result with noisy warnings; no lint rule or TypeScript check was weakened. GitHub CI uses Node 24 and should repeat these commands after the lockfile is included in a clean commit.

## Priority 4 — Shipped calibration provenance

Observed artifact:

- Path: `models/calibration_model.joblib` (tracked; unchanged in worktree)
- Git blob: `c8be94a9ab193a8d4f9a952d7853cd2ea1e9a342`, identical at `HEAD`, `8d4da35`, `c34f786`, and initial import `63607ee`
- SHA-256 of file: `6b94f41d3521c37e22d41b91e505006f1c737d022c214f803a5b9a057f185cdc`
- Loaded class: `src.calibration.calibrate.PlattCalibrator`
- Slope: `0.47414481616618126`; intercept: `-1.2645029152597382`
- Loading emitted an unsuppressed warning that its embedded LogisticRegression was serialized with scikit-learn 1.9.0 and loaded with 1.9.1.

The serving registry points XGBoost to this separate calibration artifact. `scripts/generate_evaluation_artifacts.py` loads it when present and only fits/writes a new one if the file is absent; therefore that script does not establish the current artifact’s original fitting provenance. The Git object has been unchanged since the initial upload, and no recorded source commit documents its training run. The previous `reports/phase_9_brier_discrepancy_review.md` reports the shipped Brier of 0.14412179, versus a current-code fresh validation fit with slope 0.85795861/intercept -1.09014010 and test Brier 0.13546446. Those reproduction values are documented prior evidence and were not independently recomputed in this blocker-resolution pass.

**Conclusion:** the exact original data/split/script/environment that produced the shipped coefficients remains unknown. The artifact is preserved and no replacement or refit was performed.

## Unresolved issues and recommendations

1. The requested clean Git checkout cannot contain untracked changes while staging/committing are prohibited. After separate approval, include the research code/tests/reports, `requirements-phase11.lock.txt`, `frontend/package-lock.json`, and the three required dashboard JSON files. Do not include the ignored raw dataset.
2. On a clean checkout, run the UCI fetch script and confirm the expected SHA before reproducing the experiment. The actual ZIP download branch still needs a successful end-to-end check on a machine without the local workbook.
3. Build the Docker image only after those files are committed; then verify `/v1/dashboard/snapshot` and both model evaluation endpoints in the image. Docker was not available for build verification here.
4. Run the repository workflow or the full backend suite on GitHub Actions’ Python 3.11 runner. The WSL batch suite passed, but it used Python 3.14.4 and does not certify a real GitHub run.
5. Keep calibration provenance unresolved in documentation unless original training evidence is found. Preserve the current artifact and sklearn version warnings.
6. Keep Taiwan models research/demo only and `/v1/score` at `not_validated`. No Indian borrower or production validation is claimed.

No Stage 5 work was started. No source-control staging, commit, push, merge, or deployment occurred.
