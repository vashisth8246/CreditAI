# Phase 11 Reproduction Guide

This guide describes the checked-in commands and labels unavailable verification explicitly. Run all commands from the repository root unless a `cd frontend` is shown. Phase 11 research is limited to the historical UCI Taiwan dataset; `/v1/score` remains `not_validated`.

## Environment

The recorded research environment is CPython 3.11.9 with the exact package snapshot in `requirements-phase11.lock.txt`; Node 24 is the frontend/CI target. The current Windows machine reported Python 3.11.9 and Node 24.13.1. A clean `npm ci` could not be completed in this environment due a Windows `EPERM` error in the existing `node_modules`, then registry DNS failure in a clean temporary copy. These versions and lock files should be used on a network-enabled clean machine.

## Clean checkout prerequisites

Several required Phase 11 files, research evidence files, and these documents are currently untracked. The three historical dashboard inputs under `frontend/public/data/` are also untracked. A temporary archive of current `HEAD` contained `frontend/package-lock.json` and both tracked Taiwan evaluation JSONs, but omitted modified tracked Stage 2–3 application code/tests, the Phase 11 lock, research runner/fetcher/module/tests, Docker files, and dashboard summary JSON. The raw Taiwan workbook was absent as intended. Thus current Git `HEAD` is **not** a complete clean-checkout reproduction point. Preserve the files and include the reviewed sources, reports, required Docker files, and dashboard JSON assets in a later authorized Git change. Never add `Data/`, raw Taiwan or LendingClub datasets, secrets, logs, virtual environments, caches, or `node_modules/`.

## Backend and research dependencies

```bash
python --version
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-phase11.lock.txt
```

The research lock installation above has **not** been verified as a single clean `pip install` in this pass. The prior recorded Linux test environment used the pinned list with `pip install --no-deps`; use the full install in a clean network-enabled environment and retain all dependency warnings.

## Dataset acquisition and verification

```bash
python scripts/fetch_phase11_dataset.py
python scripts/fetch_phase11_dataset.py --verify-only
```

The script downloads the official UCI archive, finds the expected workbook, checks archive/member limits and ZIP CRC, verifies SHA-256 `21b3cf4e30878150ae8db9386780e23febb613921747dec9e59dccb32f6104d3`, then writes into ignored `Data/credit_default/`. The experiment runner independently verifies the same hash before it loads data or trains. The local workbook passed verification in this pass. A fresh download could not be completed because this environment could not resolve the UCI host; that branch is **UNVERIFIED** until it succeeds on a network-enabled machine.

## Research experiment

```bash
python scripts/run_phase11_experiment.py --output-dir .phase11-reproduction
```

The command above writes to a separate directory and leaves the saved research evidence unchanged. The default output remains `reports/phase11/`; use `--output-dir` for a fresh evidence location. In this pass the full runner completed with the isolated output option. Its dataset and split hashes matched the saved run, the selective-review JSON matched, the SHAP stability CSV was byte-identical, and metric CSV values agreed within `1e-12`; JSON floating-point values differed by at most `1.5e-14`. This verifies reproduction from the current dirty worktree and already-present local dataset, not from a clean Git checkout or fresh dataset download.

## Backend tests and startup

```bash
python -m pytest tests/ -v --tb=short
python -m pytest tests/test_batch_workflow.py -v --tb=short
python -m pytest tests/test_phase11_research.py -v --tb=short
python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

The focused research tests passed here (6 passed). The seven-sheet synthetic acceptance test passed here (1 passed). The complete suite stalled at `tests/test_api_integration.py::test_health_endpoint` under Windows `TestClient` and was interrupted; run all three commands on Linux/CI with working loopback sockets. A prior blocker-resolution report records 22 batch HTTP tests passed in WSL, but that is not a fresh result from this pass. Keep the UCI dataset/model warnings visible.

After startup, verify in a Linux-capable environment:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/v1/status
curl -fsS http://127.0.0.1:8000/v1/dashboard/snapshot
```

The health and status responses must continue to state `not_validated`. The snapshot is historical; its source date is distinct from request retrieval time. Model evaluation routes are `/v1/models/uci_taiwan_xgb/evaluation` and `/v1/models/uci_taiwan_knn/evaluation`.

## Frontend checks

The lockfile lives in `frontend/` and is tracked. Run sequentially:

```bash
cd frontend
npm ci
npm test
npm run lint
npx tsc -b
npm run build
```

Lint is configured to cover project-owned `src`, `tests`, and `vite.config.ts`, avoiding dependency scanning. The changed lint scope was not executable here because the clean install failed and Oxlint was unavailable in the temporary copy. Re-run all five commands after a successful install; do not weaken TypeScript or other lint rules to force a pass.

## Batch evaluation

The seven-sheet synthetic acceptance test can be run with:

```bash
python -m pytest tests/test_batch_workflow.py -k synthetic_seven_sheet_workbook_inspects_and_scores_eligible_sheets -v --tb=short
```

Use a Linux runner for the complete upload/inspect/predict/export HTTP workflow. The generated acceptance workbook is synthetic and has no real borrower records. The UI/API supports CSV, XLSX, and `.xls` where its dependencies allow; preserve row/sheet provenance, duplicate warnings, rejected-row reasons, export formulas, and formula-injection handling. The phrase “non-default complement” means only mathematical `1 - PD`, not observed repayment.

## Docker and CI

Expected Docker commands (not verified in this environment because the Docker executable was inaccessible):

```bash
docker build -t creditai-phase11 .
docker run --rm -p 10000:10000 -e PORT=10000 creditai-phase11
```

Verify `/health`, `/v1/status`, `/v1/dashboard/snapshot`, both evaluation routes, and a batch upload in the running container. Docker must receive the tracked model artifacts and the three dashboard JSON assets.

GitHub Actions workflow: `.github/workflows/ci.yml`. It runs Python 3.11 and Node 24 checks on push and pull request to `main`, and packaging after backend/frontend jobs. No GitHub Actions run was launched or claimed. After required files are authorized and committed, use a pull request to `main` to validate CI; only a successful real Actions run establishes CI status.
