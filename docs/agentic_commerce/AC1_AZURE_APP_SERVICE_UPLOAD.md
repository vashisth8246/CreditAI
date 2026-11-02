# AC-1 Azure App Service ZIP Deployment Handoff

This handoff targets the existing App Service named `creditai-research-demo` in resource group `creditai-demo-rg`, using the owner-provided Linux Python 3.11/F1 details. Those Azure resource details were not independently verified. AC-1 does not create or resize resources.

## Package layout

After the AC-1 commit is pushed, run the verified frontend build and `python scripts/package_release.py` from a clean tracked checkout of that exact commit. The ZIP must have root entries:

```text
requirements.txt
src/...
models/...
frontend/dist/index.html
frontend/dist/assets/...
build-manifest.json
```

The package manifest records the source commit SHA and `scoring_status: not_validated`. Do not upload a repository-source ZIP or a package where the compiled frontend is placed directly at `frontend/`.

## Upload through the Azure portal/Kudu ZIP UI

1. In the Azure portal, open the existing `creditai-research-demo` App Service in `creditai-demo-rg`.
2. Open **Development Tools → Advanced Tools → Go** to open its Kudu site.
3. In Kudu, open **Tools → Zip Push Deploy** and upload the exact `release/creditai-<full-commit-sha>.zip` package. Do not deploy a different or rebuilt ZIP.
4. In the App Service **Configuration → General settings**, retain/set the user-provided startup command exactly as `python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000`. Save/restart if it was changed.
5. In **Configuration → Application settings**, ensure `SCM_DO_BUILD_DURING_DEPLOYMENT=1` so Linux Python App Service builds the virtual environment and installs `requirements.txt`. Do not set `WEBSITE_RUN_FROM_PACKAGE=1` for this Python application; Python App Service ZIP deployment uses build automation instead.
6. Review Kudu deployment status/log output and wait for the App Service restart. If build automation reports dependency or runtime failure, stop and inspect its log rather than changing the package or model behavior.

## Post-upload checks

Open the existing public URL and verify `/`, `/health`, `/v1/status`, `/v1/models`, `/v1/agentic-commerce/status`, `/v1/agentic-commerce/workflow`, and `/docs`. Use a synthetic/dummy request to `/v1/score` and confirm `not_validated`, null probability, and `validated_risk_estimate=false`. Also verify Borrower Prediction and a synthetic CSV/XLSX Batch Evaluation round trip. A successful upload alone is not a successful health or feature verification.

Microsoft documentation: [Deploy files to Azure App Service with ZIP deployment](https://learn.microsoft.com/en-us/azure/app-service/deploy-zip) and [Configure a Linux Python App Service startup command](https://learn.microsoft.com/en-us/azure/developer/python/configure-python-web-app-on-app-service).
