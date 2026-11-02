# CreditAI Continuous Deployment

CreditAI has a dedicated **CreditAI CD** workflow in the GitHub Actions tab. It runs after **CreditAI CI** completes successfully for a push to `main`. Pull requests and failed CI runs cannot deploy.

The CD workflow downloads the immutable release ZIP produced by that exact CI run, validates its commit identity, deploys it to the configured Azure Container App, and checks `/health`, `/v1/status`, and `/v1/build`. A live build identity confirms which source release is running; it does not validate the credit model. Production scoring remains `not_validated`, and Taiwan artifacts remain research/demo only.

## Azure setup required

The workflow expects an existing Azure Container Registry and public Azure Container App. Configure these GitHub repository variables:

- `DEPLOYMENT_PROVIDER=azure-container-apps`
- `AZURE_RESOURCE_GROUP`
- `AZURE_CONTAINER_APP`
- `AZURE_CONTAINER_REGISTRY`

Configure these secrets in the GitHub `production` environment:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

The Entra identity must have a GitHub OIDC federated credential for `repo:vashisth8246/CreditAI:environment:production`, permission to push to the registry and update the existing Container App, and the app's managed identity must have `AcrPull`. The app must allow external ingress on port `10000`; the registry and app are expected in the configured resource group. The `production` environment's branch and reviewer rules should restrict deployment to `main` and apply any required approval.

If `DEPLOYMENT_PROVIDER` is unset, CD reports that provider selection is pending and does not deploy. An unknown provider or incomplete Azure configuration fails the deployment job. The workflow does not create Azure resources or GitHub credentials.
