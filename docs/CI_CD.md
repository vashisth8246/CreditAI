# CreditAI CI/CD guide

## Architecture

GitHub Actions uses two workflows. **CreditAI CI** runs mandatory backend and frontend checks on pushes to `main` and pull requests targeting `main`. Successful checks feed a package job that creates one commit-addressed ZIP containing the Python application, tracked model artifacts, the already-tested frontend build under `frontend/dist/`, and `build-manifest.json`. The ZIP path matches FastAPI's static-file mount. Dataset files, local logs, caches, tests, and untracked artifacts are excluded. **CreditAI CD** runs separately after a successful CI workflow for a push to `main` and downloads the ZIP from that exact CI run.

The CD deployment job runs only after successful CI from a push to `main`, uses the GitHub `production` environment, and reads `DEPLOYMENT_PROVIDER`. The `azure-container-apps` adapter builds an image from the exact immutable release ZIP (including the frontend build already tested in CI), pushes it to Azure Container Registry, updates an existing Azure Container App, routes traffic to its latest revision in multiple-revision mode, and returns its public URL. In single-revision mode Azure routes the active revision automatically. GitHub authenticates through OIDC; no Azure client secret is stored. The adapter sets `CREDITAI_BUILD_SHA` to the full commit SHA. The app exposes it through `/v1/build` and shows the short form in the dashboard header; the CD job verifies it against the expected release SHA alongside `/health` and `/v1/status`. Azure resources are not created by these workflows. With the provider variable unset, CD reports that deployment is pending. Unknown providers and missing settings/resources fail the deploy job. See [CreditAI CD README](CD_README.md) for the separate Actions view and Azure setup.

## Workflow jobs and triggers

CI workflow: `.github/workflows/ci.yml` (`CreditAI CI`). Triggers are pushes to `main` and pull requests targeting `main`. A concurrency group cancels superseded runs for the same branch or pull request. Workflow permissions default to `contents: read`.

| Job | Runs | Required work |
|---|---|---|
| Backend Tests | Every trigger | Python 3.11, install `requirements.txt`, verify the `src.data` and FastAPI imports, run `python -m pytest tests/ -v --tb=short` |
| Frontend Tests, Lint, TypeScript, and Build | Every trigger | Node 24, `npm ci`, `npm test`, `npm run lint`, `npx tsc -b`, `npm run build`; upload `frontend/dist` for 7 days |
| Package Immutable Release | After both checks pass | Download the tested frontend output and package it with tracked Python/model inputs from a clean tracked worktree; retain for 30 days |

CD workflow: `.github/workflows/cd.yml` (`CreditAI CD`). It starts on completion of `CreditAI CI` for `main`, then explicitly requires the original CI event to be a successful push to `main`.

| CD job | Runs | Required work |
|---|---|---|
| Deployment Pending Provider Selection | Successful CI for a `main` push when no provider is configured | Writes the pending status; does not call a deploy adapter |
| Deploy and Verify | Successful CI for a `main` push when `vars.DEPLOYMENT_PROVIDER` is set | Requires the production environment, downloads the immutable release from the triggering CI run, authenticates to Azure with OIDC, deploys the registered adapter, then verifies live API health and safety status |

Pull requests cannot deploy. CD starts only after the CI workflow succeeds, which means backend tests, frontend tests/build, and release packaging all passed. A deployment or verification error makes the deploy job fail. No automatic rollback is configured.

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
| `AZURE_RESOURCE_GROUP` | Yes for Azure deployment | Not set | Repository variable naming the existing Azure resource group |
| `AZURE_CONTAINER_APP` | Yes for Azure deployment | Not set | Repository variable naming the existing public Container App |
| `AZURE_CONTAINER_REGISTRY` | Yes for Azure deployment | Not set | Repository variable naming the existing Container Registry resource |
| `AZURE_CLIENT_ID` | Yes for Azure OIDC | Not set | GitHub `production` environment secret for the federated Entra identity |
| `AZURE_TENANT_ID` | Yes for Azure OIDC | Not set | GitHub `production` environment secret |
| `AZURE_SUBSCRIPTION_ID` | Yes for Azure OIDC | Not set | GitHub `production` environment secret |
| `CREDITAI_BUILD_SHA` | Set by Azure deployment | Not set locally | Full commit SHA for live release identity; never a model validation claim |

There are no backend application secrets required by the current code.

The backend requires Python dependencies from `requirements.txt` and the tracked model bundle under `models/` for research inference. The release packager includes only model files tracked by Git. Health and status routes report connectivity and model availability; `/health` explicitly reports `scoring: not_validated`. No database, persistent filesystem, or background worker is used. FastAPI/Starlette may spool multipart upload bytes to request-scoped temporary storage before the endpoint reads them; the endpoint enforces a 10 MiB limit and returns parsed data without persisting the upload. Hosting must provide writable temporary space plus memory for bounded parsing. No file is required to survive the request, and ephemeral disk is not used as durable storage.

`scikit-learn` is pinned to 1.9.1, matching the current environment and newest KNN artifacts inspected in this workspace. The older tracked XGBoost/calibration bundle records 1.9.0 and emits `InconsistentVersionWarning` under 1.9.1; model loading and inference tests pass, but the warning is retained. The artifacts have mixed provenance, so do not silently suppress the warning or overwrite/retrain artifacts as part of CI setup. Before relying on the legacy bundle in production, reproduce training under the pinned runtime and review a governed artifact update.

## Frontend build and environment

The Vite production build is `frontend/dist`. Set optional `VITE_API_BASE_URL` at build time in the frontend environment for an independently hosted API. Leave it empty for same-origin routing. Production JavaScript never falls back to localhost; only the Vite development proxy uses loopback URLs. `.env.example` files are templates and contain no secrets. These variables are public build configuration, not secret storage.

The frontend is a single-page app. The selected host must serve `index.html` for application routes and route `/health` and `/v1/*` to the backend when using same-origin configuration. A separate frontend/API host needs the correct `VITE_API_BASE_URL` and matching backend `CORS_ORIGINS`.

## Enabling Azure Container Apps deployment

The repo includes an Azure Container Apps adapter, but automatic deployment stays disabled until the owner configures the Azure target and GitHub environment. The adapter updates an existing app; it does not provision Azure resources.

1. Create or select an Azure Container Registry and an externally reachable Azure Container App in the same resource group. Configure the app ingress target port as `10000` and enable its system-assigned identity. Grant that identity `AcrPull` on the registry. The adapter checks ingress and stops before pushing if the app is not externally reachable on the expected port.
2. Create a Microsoft Entra federated identity credential for GitHub Actions using issuer `https://token.actions.githubusercontent.com`, audience `api://AzureADTokenExchange`, and subject `repo:vashisth8246/CreditAI:environment:production`. Grant this identity only the Azure permissions needed to read the named resources, push images to the selected registry, and update the selected Container App (including managed identity and traffic settings).
3. In GitHub, create the `production` environment and configure branch restrictions and any required reviewers. Add the environment secrets `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_SUBSCRIPTION_ID` for the federated identity.
4. Add repository variables `DEPLOYMENT_PROVIDER=azure-container-apps`, `AZURE_RESOURCE_GROUP`, `AZURE_CONTAINER_APP`, and `AZURE_CONTAINER_REGISTRY` with the names of the existing resources.
5. A push to `main` runs tests, builds the frontend, packages the immutable release, then logs in with OIDC and deploys only after those jobs pass. PRs never deploy. The adapter tags the image with the full commit SHA and deploys the artifact's prebuilt frontend and backend source.
6. Confirm the run's deploy job and live `/health`, `/v1/status`, `/v1/build`, and app URL before announcing deployment. A failed health, safety, or expected-SHA check fails the job. Rollback is not automated; define and test a rollback procedure before relying on this pipeline.

Azure login uses the GitHub OIDC token (`id-token: write`) and does not use a client secret. GitHub environment approvals are configured in GitHub settings, not by this repository workflow. Never print tokens or put credentials in workflow YAML, `.env.example`, build metadata, or frontend variables.

## Deployment verification and failure handling

The adapter owns provider submission and must return a real result. `scripts/deploy_release.py` first validates the ZIP CRC, exact manifest file list, full source SHA, clean-worktree marker, required app files, safe extraction paths, and the `not_validated` manifest marker. It then calls the configured adapter and checks `/health`, `/v1/status`, and `/v1/build` with bounded retries. Verification requires HTTP success, `status: ok`, `not_validated` scoring values, and the expected commit SHA. A failed adapter or failed health/safety/release-identity check fails the Actions job; inspect both the deploy step and provider logs.

No rollback behavior is implemented. Before production use, define a provider-specific rollback mechanism, retain prior immutable releases, document health-gate behavior, and test rollback in a non-production environment. Never claim rollback occurred unless provider evidence confirms it.

## ML safety boundary

`/v1/score` remains `not_validated`. Taiwan benchmark artifacts are research models based on 2005 Taiwan credit-card data; they do not validate Indian borrowers. Synthetic data is only for software testing/demonstration. A build, package, health check, or deployment does not validate or promote a model. The existing model registry checks and batch provenance/limitations remain in force.

## Dataset notes

The CI checkout does not fetch or package datasets. UCI identifies the Default of Credit Card Clients dataset as CC BY 4.0; preserve attribution if redistributing it ([official dataset page](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients)). The local LendingClub CSV is archived from Figshare/Kaggle mirrors, is 1.68 GB, and has no bundled license establishing redistribution or commercial rights for this exact copy. Keep it out of GitHub Actions artifacts and provide it locally for benchmark tests. The tests use the actual files when present and report explicit skips when absent. No placeholder data is used.

## Known limits

Azure is selected as the intended host, and a reviewed Container Apps adapter is registered. The target Azure resources, federated identity, GitHub environment secrets/variables, first deployment, and rollback are still unconfigured/unverified. Until the required settings exist, `DEPLOYMENT_PROVIDER` must remain unset; the separate CD workflow reports deployment pending and no cloud deployment occurs.
