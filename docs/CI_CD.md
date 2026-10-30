# CreditAI CI/CD guide

## Architecture

GitHub Actions runs mandatory backend and frontend checks on pushes to `main` and pull requests targeting `main`. Successful checks feed a package job that creates one commit-addressed ZIP containing the Python application, tracked model artifacts, the already-tested frontend build, and `build-manifest.json`. Dataset files, local logs, caches, and untracked artifacts are excluded. The same ZIP is the only input to the later deploy job.

The deploy job is provider-neutral. It runs only for a successful push to `main`, uses the GitHub `production` environment, and reads the single repository variable `DEPLOYMENT_PROVIDER`. The configured provider ID must exist in the reviewed `PROVIDER_ADAPTERS` allowlist in `src/cicd/deployment.py`. Each registered module must declare the matching `PROVIDER_ID` and implement `deploy(release_dir, version)`, returning `provider`, `deployment_id`, and `base_url`. It must raise on provider failure. CreditAI then checks `/health` and `/v1/status`, including that production scoring remains `not_validated`. The adapter registry is currently empty, so no provider can deploy. With the variable unset, Actions reports that CI passed and deployment is pending provider configuration. An unknown ID, missing registered module, incomplete adapter, missing required credentials, or failed provider response must fail the deploy job.

## Workflow jobs and triggers

Workflow: `.github/workflows/ci.yml` (`CreditAI CI and CD`). Triggers are pushes to `main` and pull requests targeting `main`. A concurrency group cancels superseded runs for the same branch or pull request. Workflow permissions default to `contents: read`.

| Job | Runs | Required work |
|---|---|---|
| Backend Tests | Every trigger | Python 3.11, install `requirements.txt`, verify the `src.data` and FastAPI imports, run `python -m pytest tests/ -v --tb=short` |
| Frontend Tests, Lint, TypeScript, and Build | Every trigger | Node 24, `npm ci`, `npm test`, `npm run lint`, `npx tsc -b`, `npm run build`; upload `frontend/dist` for 7 days |
| Package Immutable Release | After both checks pass | Download the tested frontend output and package it with tracked Python/model inputs from a clean tracked worktree; retain for 30 days |
| Deployment Pending Provider Selection | Successful `main` push when no provider is configured | Writes the explicit pending status to the run summary; does not call a deploy adapter |
| Deploy and Verify | Successful `main` push when `vars.DEPLOYMENT_PROVIDER` is set | Requires the production environment, downloads the same release ZIP, calls the configured adapter, then verifies live API health and safety status |

Pull requests cannot deploy. Deployment cannot start unless backend tests, frontend tests/build, and release packaging all pass. A deployment or verification error makes the deploy job fail. No automatic rollback is configured.

## Inspecting CI failures and running locally

Open the repository's **Actions** tab, select the failed run, and expand the failed job and step. The logs contain commands and test output; do not add credentials or borrower data to diagnostic output.

From the repository root, use Python 3.11 and run:

```sh
python -m pip install -r requirements.txt
python -c "import src.data.generate, src.data.preprocessing, src.data.validation; from src.api.app import app; print(app.title)"
python -m pytest tests/ -v --tb=short
```

From `frontend/`, use Node 24 and run:

```sh
npm ci
npm test
npm run lint
npx tsc -b
npm run build
```

An absent LendingClub raw CSV or UCI Taiwan workbook causes only the explicitly documented dataset-backed tests to be skipped. The pytest summary identifies each skip and its reason. These skips are not counted as passes; all deterministic tests still run.

## Backend startup and configuration

Run from the repository root so the existing model registry's relative `models/...` paths resolve:

```sh
python -m uvicorn src.api.app:app --host 0.0.0.0 --port "${PORT:-8000}"
```

On Windows PowerShell, use `$env:PORT` or `8000` as the port value. The `.env.example` files are templates; the application does not automatically load them. Set the values in the shell or hosting environment. The Vite development proxy is same-origin, so local development does not need CORS exceptions. For a split frontend/API deployment, set only the actual HTTPS frontend origin(s). Keep credentials out of these files and use provider environment settings or GitHub Secrets for credentials.

| Variable | Required | Development value | Production value |
|---|---|---|---|
| `PORT` | No; defaults to `8000` in the documented startup command | `8000` | Use the port assigned by the host |
| `CORS_ORIGINS` | No for same-origin requests | Empty | Comma-separated exact HTTPS frontend origin(s), only for cross-origin hosting |
| `VITE_API_BASE_URL` | No for same-origin routing | Empty (Vite proxies API paths) | Optional GitHub repository variable consumed by the build; empty with same-origin routing or the API's HTTPS base URL when separately hosted |
| `DEPLOYMENT_PROVIDER` | No; an empty value safely skips deployment | Not set | Repository variable containing a provider ID registered to a reviewed adapter |
| `CREDITAI_DEPLOYMENT_TOKEN` | Only if the selected adapter requires it | Not set | GitHub production environment secret; never exposed to frontend |

There are no backend application secrets required by the current code.

The backend requires Python dependencies from `requirements.txt` and the tracked model bundle under `models/` for research inference. The release packager includes only model files tracked by Git. Health and status routes report connectivity and model availability; `/health` explicitly reports `scoring: not_validated`. No database, persistent filesystem, or background worker is used. FastAPI/Starlette may spool multipart upload bytes to request-scoped temporary storage before the endpoint reads them; the endpoint enforces a 10 MiB limit and returns parsed data without persisting the upload. Hosting must provide writable temporary space plus memory for bounded parsing. No file is required to survive the request, and ephemeral disk is not used as durable storage.

`scikit-learn` is pinned to 1.9.1, matching the current environment and newest KNN artifacts inspected in this workspace. The older tracked XGBoost/calibration bundle records 1.9.0 and emits `InconsistentVersionWarning` under 1.9.1; model loading and inference tests pass, but the warning is retained. The artifacts have mixed provenance, so do not silently suppress the warning or overwrite/retrain artifacts as part of CI setup. Before relying on the legacy bundle in production, reproduce training under the pinned runtime and review a governed artifact update.

## Frontend build and environment

The Vite production build is `frontend/dist`. Set optional `VITE_API_BASE_URL` at build time in the frontend environment for an independently hosted API. Leave it empty for same-origin routing. Production JavaScript never falls back to localhost; only the Vite development proxy uses loopback URLs. `.env.example` files are templates and contain no secrets. These variables are public build configuration, not secret storage.

The frontend is a single-page app. The selected host must serve `index.html` for application routes and route `/health` and `/v1/*` to the backend when using same-origin configuration. A separate frontend/API host needs the correct `VITE_API_BASE_URL` and matching backend `CORS_ORIGINS`.

## Connecting a provider later

After selecting a provider:

1. Implement and review an adapter module with a matching `PROVIDER_ID` and `deploy(release_dir, version)`. It must validate its required credentials/configuration, deploy the supplied release, return the real provider deployment ID and API base URL, and raise on errors. Do not return success before the provider confirms the release.
2. Add provider-specific runtime instructions (ASGI command, environment, frontend/static hosting, routing, health path, and artifact needs) to the adapter and this guide.
3. In GitHub repository settings, create a `production` environment. Configure required reviewers and deployment branch restrictions there before enabling automatic deployment.
4. Register the reviewed adapter in `PROVIDER_ADAPTERS` using the provider ID it declares. Add repository variable `DEPLOYMENT_PROVIDER` with exactly that ID. Store provider credentials as production environment secrets. The adapter may read `CREDITAI_DEPLOYMENT_TOKEN`; provider-specific secret names should be added to the workflow only when the provider is selected.
5. Review least-privilege permissions, secret scope, environment approval rules, adapter source, and provider's rollback procedure. Then enable the workflow on successful pushes to `main` by setting `DEPLOYMENT_PROVIDER`.
6. Confirm run logs identify the commit SHA and release artifact; confirm the live `/health` and `/v1/status` response before announcing deployment.

GitHub Secrets and environment secrets must never be printed. Do not put credentials in workflow YAML, `.env.example`, build metadata, or frontend variables. Environment approvals are configured in GitHub settings, not by this repository workflow.

## Deployment verification and failure handling

The adapter owns provider submission and must return a real result. `scripts/deploy_release.py` first validates the ZIP CRC, exact manifest file list, full source SHA, clean-worktree marker, required app files, safe extraction paths, and the `not_validated` manifest marker. It then calls the configured adapter and checks `/health` plus `/v1/status` with bounded retries. Verification requires HTTP success, `status: ok`, and `not_validated` scoring values. The manifest's version is the source commit SHA. A failed adapter or failed health/safety check fails the Actions job; inspect both the deploy step and provider logs.

No rollback behavior is implemented. Before production use, define a provider-specific rollback mechanism, retain prior immutable releases, document health-gate behavior, and test rollback in a non-production environment. Never claim rollback occurred unless provider evidence confirms it.

## ML safety boundary

`/v1/score` remains `not_validated`. Taiwan benchmark artifacts are research models based on 2005 Taiwan credit-card data; they do not validate Indian borrowers. Synthetic data is only for software testing/demonstration. A build, package, health check, or deployment does not validate or promote a model. The existing model registry checks and batch provenance/limitations remain in force.

## Dataset notes

The CI checkout does not fetch or package datasets. UCI identifies the Default of Credit Card Clients dataset as CC BY 4.0; preserve attribution if redistributing it ([official dataset page](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients)). The local LendingClub CSV is archived from Figshare/Kaggle mirrors, is 1.68 GB, and has no bundled license establishing redistribution or commercial rights for this exact copy. Keep it out of GitHub Actions artifacts and provide it locally for benchmark tests. The tests use the actual files when present and report explicit skips when absent. No placeholder data is used.

## Known limits

The hosting provider is not selected. Accordingly, there is no provider adapter, infrastructure definition, real deployment, provider secret, live URL, or tested rollback. The generic workflow, release contract, environment gate, and API verification are ready for that provider-specific follow-up.
