# CreditAI CI/CD implementation report

**Date:** 2026-10-30
**Branch:** `main`
**Commit at audit:** `8ca9881`
**Provider:** Not selected
**Deployment performed:** No

## 1. Initial repository audit

The repository already had `.github/workflows/ci.yml`, a Python 3.11 backend job and Node 24 frontend job. The workflow ran pytest and frontend tests/lint/type-check/build, but had no concurrency control, artifact handoff, release packaging, deployment gate, or post-deployment verification. `reports/ci_implementation_report.md` described an earlier CI-only implementation; it was preserved and was not treated as current test evidence.

The branch was `main`, at `8ca9881` (`Fix GitHub Actions CI import errors`), following `bfaad93` (`Add GitHub Actions CI workflow`). Initially there were no staged changes. Existing unstaged user edits included `frontend/src/batch.ts`, `models/uci_taiwan_eval.json`, `src/api/app.py`, `src/inference/model_registry.py`, and `src/inference/predictor.py`. Existing untracked user files included the `Data/` datasets, local KNN model artifacts and metadata, experiment reports, frontend public research JSON, logs/fixtures, scripts, `src/models/knn.py`, `check_batch.py`, and root `package-lock.json`. These were preserved and not staged.

The four `src/data/` package files were already tracked and importable. The root ignore entry was `/Data//`, which did not ignore the root dataset directory. It is now `/Data/`, confirmed to ignore `Data/archive/...` while leaving `src/data/generate.py` tracked. The UCI Taiwan workbook and LendingClub CSV were present locally. Both were absent from Git tracking as intended.

The frontend lockfile is `frontend/package-lock.json`; the separate root `package-lock.json` is user-owned untracked content and is not used by CI. The frontend test failures described in the assignment were already addressed in the current `frontend/src/batch.ts` working-tree edit: all 26 tests pass, including the em dash/en dash and probability histogram report assertions.

## 2. CI implementation

Updated `.github/workflows/ci.yml` to run on pushes to `main` and pull requests targeting `main`, with concurrency cancellation and read-only default token permissions.

Jobs and commands:

| Job | Commands and artifact behavior |
|---|---|
| Backend Tests | Python 3.11; install `requirements.txt`; import `src.data.generate`, `src.data.preprocessing`, `src.data.validation`, and `src.api.app`; run `python -m pytest tests/ -v --tb=short` |
| Frontend Tests, Lint, TypeScript, and Build | Node 24; `npm ci`; `npm test`; `npm run lint`; `npx tsc -b`; `npm run build`; upload `frontend/dist/` for 7 days |
| Package Immutable Release | Runs only after both required jobs pass; requires a clean tracked checkout, verifies registered model file paths, packages tracked Python/model files, requirements, and the tested frontend build; uploads a commit-SHA-named ZIP for 30 days |
| Deployment Pending Provider Selection | On a successful push to `main` when no provider variable exists, writes an explicit pending message; does not attempt or claim a deployment |
| Deploy and Verify | Only on a successful push to `main` with `DEPLOYMENT_PROVIDER`; uses the `production` GitHub environment; downloads that run's exact release ZIP; validates and runs the allowlisted provider adapter, then checks live health/status |

The packager excludes datasets, untracked artifacts, logs, caches, and local files. Release contents are listed in `build-manifest.json` together with source commit SHA, version, build time, and `scoring_status: not_validated`.

Actual local results:

- Backend: **138 passed, 0 failed, 0 skipped**, 55 warnings, 71.13 seconds. Command: `.venv\Scripts\python.exe -m pytest tests/ -v --tb=short` (run with local socket access for Starlette's test client).
- Frontend dependency install: `npm ci` completed on retry with network access; 27 packages installed, audit reported 0 vulnerabilities. The first restricted attempt exited with an npm internal error.
- Frontend: `npm test` â€” **26 passed, 0 failed, 0 skipped**.
- Lint: `npm run lint` â€” passed with no diagnostics.
- `npx tsc -b` â€” failed because npm resolved the path incorrectly in this Windows workspace path containing `&`. The direct installed TypeScript 6.0.2 compiler invocation passed, and `npm run build` also ran `tsc -b` successfully.
- Production build: `npm run build` â€” passed; Vite transformed 25 modules and emitted the production bundle.
- The local full-suite result includes both available external datasets; no dataset-backed tests were skipped.

The 55 warnings include existing Pydantic and SHAP deprecations, scikit-learn artifact-version warnings, and one logistic regression convergence warning. They were not suppressed. The scikit-learn dependency is pinned to 1.9.1 to match the current environment and newest KNN artifacts. Older tracked XGBoost/calibration artifacts record 1.9.0 and load successfully in the suite but emit `InconsistentVersionWarning`; do not promote those artifacts to production without a reproducible, reviewed update.

## 3. Dataset-dependent tests

Local data availability and outcomes:

| Dataset | Local status | CI policy | License/redistribution assessment |
|---|---|---|---|
| UCI Default of Credit Card Clients, `Data/credit_default/.../default of credit card clients.xls` | Present (5,539,328 bytes) | Seven `tests/test_pipeline.py` cases run when present; otherwise the class is explicitly skipped with a path-specific pytest reason | UCI lists CC BY 4.0; attribution is required. The file is not fetched or included in CI |
| LendingClub accepted loans, `Data/archive/accepted_2007_to_2018Q4.csv` | Present (1,675,133,810 bytes; 2,260,701 rows) | The raw row-count reconciliation runs when present; otherwise one test is skipped with an explicit pytest reason | Existing audit records say commercial/redistribution rights are not established for this copy. The large file stays out of Git and workflow artifacts |

There were **zero skipped dataset tests** in the local run. In a clean GitHub checkout, these eight cases skip individually if the ignored local datasets are not supplied. All other tests still execute. No download scripts or fabricated datasets were added. The package job includes neither dataset.

## 4. Frontend deployment readiness

`frontend/src/api.ts` now uses same-origin requests in production when `VITE_API_BASE_URL` is empty. Loopback fallback URLs are enabled only in Vite development mode. A configured API URL is used directly and does not fall back to localhost. `frontend/.env.example` documents the optional public build-time API base URL. The production bundle was searched for `localhost` and `127.0.0.1`; neither was found.

The application is a Vite single-page app. A future host must provide SPA fallback to `index.html`. For same-origin operation, it must route `/health` and `/v1/*` to FastAPI. A split frontend/API topology needs `VITE_API_BASE_URL` and matching exact origins in `CORS_ORIGINS`. The Vite development proxy remains local-only.

## 5. Backend deployment readiness

ASGI startup command from the repository root:

```sh
python -m uvicorn src.api.app:app --host 0.0.0.0 --port "${PORT:-8000}"
```

The repository root is required because the current model registry uses relative `models/...` paths. `.env.example` documents optional `CORS_ORIGINS` and `PORT`; no backend application secret is currently required. CORS now accepts only explicit configured origins. Same-origin Vite development does not need a broad loopback CORS exception.

`requirements.txt` provides the ASGI runtime and pins scikit-learn 1.9.1. Tracked model artifacts under `models/` are required for research inference and included in the package. `/health` and `/v1/status` were verified against a locally started server: health returned `{"status":"ok","scoring":"not_validated"}` and status returned `indian_production_scoring: not_validated` with two registered research models. Uploads are capped at 10 MiB; multipart parser temporary spooling is request-scoped. No database, persistent storage, or background jobs are used.

## 6. CD implementation

The provider-neutral release and deployment components are `scripts/package_release.py`, `src/cicd/deployment.py`, and `scripts/deploy_release.py`. There is one provider selector: repository variable `DEPLOYMENT_PROVIDER`. The reviewed `PROVIDER_ADAPTERS` allowlist in `src/cicd/deployment.py` is currently empty. A provider must be explicitly registered in code, its module must declare the same `PROVIDER_ID`, and it must implement `deploy(release_dir, version)` with a complete result or raise on failure. Unknown providers, missing modules/interfaces, incomplete results, and mismatched provider IDs fail. No built-in adapter fabricates a deployment. Before invoking an adapter, the deployment script checks ZIP integrity, manifest/source SHA consistency, clean-worktree provenance, required files, safe paths, and the `not_validated` safety marker. It then checks `/health` and `/v1/status` and fails if live scoring no longer says `not_validated`.

Deployment requires every mandatory CI/package job to pass, a push to `main`, repository variable `DEPLOYMENT_PROVIDER`, and the GitHub `production` environment. Without a configured provider, the workflow reports: â€œNo deployment provider configured. CI completed successfully; deployment is pending provider configuration.â€ It does not run the deploy script. The immutable release ZIP is retained 30 days and is not rebuilt between tests and deployment.

No provider was configured and no deployment occurred. An unset provider is rejected by the adapter interface; an unknown provider ID is rejected as unregistered. The GitHub workflow safely skips `deploy` when the variable is empty and reports deployment pending. The deploy job uses the `production` environment, but actual environment reviewer/branch settings cannot be inspected here. Automatic rollback is not implemented.

## 7. Security

GitHub workflow token permissions are read-only by default; the deploy job adds only artifact read access. No secret values are in YAML or `.env.example`. `CREDITAI_DEPLOYMENT_TOKEN`, if needed by a future adapter, belongs in the GitHub production environment secret store. Frontend variables are public and must never carry secrets. Existing API validation errors avoid echoing submitted transaction values, and no borrower payload logging was added.

The root `Data/` ignore rule prevents the local datasets from entering Git status or release packaging. The packager selects only Git-tracked model files and excludes logs, raw data, and untracked local artifacts. No commit, push, staging, or deployment occurred. The deployment adapter is trusted code and must not print credentials.

## 8. ML safety

`/v1/score` remains `not_validated`, returns no probability, and was covered by passing contract/integration tests. `/health`, `/v1/status`, and the build manifest retain that status. Taiwan research models remain labeled for their dataset/geography and do not validate Indian borrowers. Synthetic data remains a software demonstration/testing source only. Deployment success cannot promote a model. Existing registry checks and batch provenance/limitations remain active.

## 9. Verification evidence

- `git branch --show-current`, `git log -6 --oneline --decorate`, and `git status --short` â€” branch and initial user work recorded above.
- `git ls-files src/data/...` â€” all four required package files tracked.
- `git check-ignore -v Data/archive/accepted_2007_to_2018Q4.csv` â€” root dataset is ignored by `.gitignore:33:/Data/`; the tracked `src/data` module is not ignored.
- Backend import smoke test in workflow configuration; full local pytest: **138 passed**.
- Frontend: **26 passed, 0 failed, 0 skipped**; lint passed; `npx tsc -b` failed due Windows path parsing, direct TypeScript compilation passed; Vite production build passed.
- Local Uvicorn startup and HTTP checks: `/health` and `/v1/status` both returned HTTP 200 and preserved `not_validated`.
- Existing ignored local release ZIPs were inspected with CRC checks. They include `requirements.txt`, backend source, and the built frontend; archive scans found no `.env`, logs, caches, raw `Data/`, or known secret-pattern matches. One manifest uses only abbreviated SHA `8ca9881`; the other full SHA matches `HEAD`. Both were created before the clean-worktree guard and contain dirty source while claiming a commit SHA, so both are **rejected as release artifacts**. The extracted app starts and returns HTTP 200 for `/health` and `/v1/status`, but the ZIP's modified registry/API requires four absent KNN model/evaluation files. Its model-path verification fails.
- `scripts/package_release.py` now refuses dirty tracked worktrees, checks `GITHUB_SHA == HEAD`, includes only tracked runtime sources/dependencies/models, and checks model/metadata file references from the model registry and API. It correctly refuses to create a ZIP from this uncommitted workspace. A trustworthy release ZIP must be produced by the clean GitHub checkout after reviewed changes are committed; none was generated in this audit.
- With `DEPLOYMENT_PROVIDER` unset, the adapter loader fails with a clear configuration message; an unregistered provider is rejected before deploy. The adapter registry is empty. Python compilation of the deployment/package helpers passed.
- Workflow logic checks confirmed main push/PR triggers, mandatory job dependencies, main-only deploy condition, explicit pending status, matching artifact names/paths, and the shared provider variable.
- Production bundle loopback scan: no `localhost` or `127.0.0.1` occurrences.
- `git diff --check` â€” passed; no whitespace errors.
- No standalone YAML/actionlint validator is installed. External YAML/GitHub Actions validation is pending; the workflow has not run on GitHub. The `production` environment is declared, but its GitHub-side protection rules were not inspectable.
- Provider-specific deployment, environment approvals, and live provider health were not testable because no provider is selected.

## 10. Files changed

Added for the CI/CD implementation:

- `.env.example`
- `docs/CI_CD.md`
- `reports/ci_cd_implementation_report.md`
- `scripts/package_release.py`
- `scripts/deploy_release.py`
- `src/cicd/__init__.py`
- `src/cicd/deployment.py`

Modified by this implementation:

- `.github/workflows/ci.yml`
- `.gitignore`
- `frontend/.env.example`
- `requirements.txt`
- `frontend/src/api.ts`
- `src/api/app.py` (CORS allowlist is explicit)
- `tests/test_pipeline.py` (explicit skip when the UCI source file is absent)
- `tests/test_phase23_benchmark.py` (explicit skip when the LendingClub source file is absent)

Updated in this final audit:

- `.github/workflows/ci.yml` (one provider variable; adapter validation before deployment; build-time API URL variable)
- `docs/CI_CD.md` and this report (consistent provider contract and current audit evidence)
- `scripts/package_release.py` (clean-tree/SHA checks and required model-path validation)
- `scripts/deploy_release.py` (manifest validation and safe extraction before adapter invocation)
- `src/cicd/deployment.py` (empty reviewed-provider registry and strict adapter/provider checks)

Important pre-existing user work preserved and not otherwise edited here:

- `frontend/src/batch.ts`, `models/uci_taiwan_eval.json`, `src/inference/model_registry.py`, `src/inference/predictor.py`
- User-added KNN artifacts, KNN training/model code, datasets, logs, generated reports, frontend research JSON, `check_batch.py`, and root `package-lock.json`
- Existing `reports/ci_implementation_report.md`

No files were staged. `git diff --cached` remained empty. The `frontend/dist/` and `release/` outputs are local ignored build artifacts.

## 11. Remaining provider-specific tasks

Select the host, implement and register a reviewed adapter keyed by one `DEPLOYMENT_PROVIDER` ID, install/pin its dependency, validate required secrets in that adapter, configure GitHub `production` reviewers/branch rules and API/frontend routing, then verify deployment and test rollback. No provider adapter is currently registered.

## 12. Exact next steps for the user

1. Review this report, `.github/workflows/ci.yml`, and `docs/CI_CD.md` alongside your existing unstaged and untracked project work.
2. Decide which existing user files you want included with the CI/CD implementation; this task did not stage or commit anything.
3. Stage only the reviewed CI/CD files and any desired application changes, then commit and push using your normal workflow.
4. Run a YAML/GitHub Actions validator and the workflow on GitHub after the reviewed changes are committed. The CI package job requires a clean tracked checkout and will verify model paths before upload.
5. Select a hosting provider before adding deployment variables, secrets, an adapter, or approvals.

## 13. Final pre-push readiness audit (2026-10-30)

### KNN artifacts and clean-checkout requirements

The four KNN paths referenced by the current registry/API are all **untracked and not ignored** (`git ls-files` returns no entries and `git check-ignore` returns no match):

| Path | Role | Required behavior |
|---|---|---|
| `models/creditai_knn_model.joblib` | Runtime model bundle; contains the fitted pipeline and a serialized `KNNNeighborExplainer` | Required for KNN inference. Unpickling also requires `src/models/knn.py`, which defines that class. |
| `models/calibration_knn_model.joblib` | Separate Platt calibration object | Optional to the predictor, which falls back to raw probability when absent/invalid; required for the current calibrated KNN result. |
| `models/knn_model_metadata.json` | Registry/readiness metadata | Not loaded for startup or prediction; registry/model validation reports its presence. |
| `models/uci_taiwan_knn_eval.json` | Evaluation response payload | Required only by `/v1/models/uci_taiwan_knn/evaluation`; not needed to start the API or score a request. |

Startup and `/health` do not load these artifacts. KNN prediction loads the model bundle and the shared tracked `models/feature_names.json`. The calibration file is optional for raw inference. The KNN evaluation endpoint reads its JSON file directly. The model bundle's custom explainer makes `src/models/knn.py` a real runtime dependency even though the API does not import it directly. `scripts/train_knn_model.py` creates these artifacts but is a training/reproduction tool, not an API runtime dependency. `frontend/public/data/uci_taiwan_knn_eval.json` has no matching source reference in `frontend/src` and is not required by the current frontend code.

For a release that includes the current KNN code and advertised features, the following exact additions must be committed: `models/creditai_knn_model.joblib`, `models/calibration_knn_model.joblib`, `models/knn_model_metadata.json`, `models/uci_taiwan_knn_eval.json`, and `src/models/knn.py`. The modified tracked application files that carry the corresponding feature/configuration changes are `src/api/app.py`, `src/inference/model_registry.py`, and `src/inference/predictor.py`; commit their reviewed working-tree versions. `requirements.txt` and `models/feature_names.json` are already tracked. `models/uci_taiwan_eval.json` is a separate modified tracked comparison artifact; include its reviewed change only if that updated evaluation is intended. Do not add `Data/`, LendingClub CSVs, logs, secrets, caches, or generated frontend research files. No file was staged by this audit.

`registered_model_paths()` now additionally requires `src/models/knn.py` whenever the registry contains a K-Nearest Neighbors entry, because the joblib object must import the serialized class during deserialization. Python compilation passed. Running the packager on this workspace exits before generating a ZIP because tracked source is dirty. No ZIP was created or used. Once the exact reviewed changes are committed and pushed, the GitHub package job runs from that clean commit, checks out the tested frontend build artifact, verifies every registered runtime/model/API path exists among tracked release inputs, and writes the source SHA into the manifest. The deploy job downloads that exact ZIP artifact from the same workflow run. A clean-checkout ZIP and its contents have not yet been verified because no commit/push is authorized.

### Workflow validation and release safety

Manual inspection and static assertions confirm the workflow declares push to `main` and pull request to `main`; pull requests cannot satisfy the deploy condition. Deployment is conditioned on a successful push to `refs/heads/main`, needs backend, frontend, and package jobs, and targets the `production` environment. The no-provider branch writes a pending message and skips deploy. The deployment loader rejects an unknown provider, and the adapter registry is empty, so a configured provider cannot succeed until a real adapter is implemented and registered. Artifact upload/download names are both `creditai-release-${{ github.sha }}`; upload uses `release/creditai-${{ github.sha }}.zip`, and the deploy step receives the matching SHA-derived path. Deployment health/status checks return failure on non-healthy responses and require `/v1/status` to retain `not_validated`.

No real YAML/GitHub Actions validator was available or run. `actionlint`, `yamllint`, `yq`, Ruby, and Go were not installed. Docker is present as a Windows command shim but could not be invoked as a CLI in this environment; GitHub CLI is installed but not authenticated and has no usable remote validation. Therefore syntax validation by an external validator and a real GitHub Actions run remain pending. GitHub production-environment protection settings were not inspectable. Do not treat manual checks as a validator result or as a successful GitHub run.

### TypeScript command

In this Windows workspace, `npx tsc -b` failed with `Cannot find module 'F:\\NUV ACD\\All SEM\\7th Sem\\typescript\\bin\\tsc'`. The npm-generated command path is being split at the unquoted `&` in the parent directory (`ML&DS`), causing resolution to drop the remaining path components. Direct invocation through `node node_modules/typescript/bin/tsc -b` and `npm run build` passed in the prior recorded frontend run; the package build script invokes Node with the local compiler path. GitHub's Linux runner checks out under a path without `&`, so the same `npx tsc -b` is expected to resolve there, but this expectation is unverified until the workflow runs. The CI type-check has not been weakened or removed.

### Verification summary and blockers

Previously recorded actual local checks remain: backend `pytest tests/ -v --tb=short` â€” **138 passed, 0 failed, 0 skipped** (55 warnings); frontend `npm test` â€” **26 passed, 0 failed, 0 skipped**; `npm run lint` passed; `npx tsc -b` failed as above; direct TypeScript compiler invocation passed; `npm run build` passed. No scikit-learn warning was suppressed. `/v1/score` remains `not_validated`; Taiwan models remain research-only, and deployment health checks do not assert model validation. No synthetic or Taiwan model was promoted. No unrelated batch evaluation feature was modified in this final audit.

The remaining pre-push blockers are: review and commit the required KNN source/artifacts above; resolve all other intended dirty/untracked application changes without including restricted data or local files; run a real YAML/Actions validator; push the reviewed commit and confirm the actual GitHub workflow; and, before any deployment, implement/register the selected provider adapter and configure the production environment protections. The checkout is currently dirty, so no valid release ZIP can be made here. Neither previously rejected ZIP is valid for release.
