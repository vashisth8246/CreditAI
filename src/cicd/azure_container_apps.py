"""Deploy a tested CreditAI release ZIP to an existing Azure Container App.

The GitHub runner authenticates with Azure using OIDC. Azure Container Registry
pull access must be granted to the Container App's system-assigned identity.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .deployment import DeploymentError


PROVIDER_ID = "azure-container-apps"
_REQUIRED_PATHS = ("requirements.txt", "src/api/app.py", "frontend/dist/index.html", "models")


def _setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise DeploymentError(f"Azure deployment requires the GitHub environment variable {name}.")
    return value


def _run(command: list[str], *, cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise DeploymentError(f"Required deployment tool is unavailable: {command[0]}.") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        if len(detail) > 1200:
            detail = detail[-1200:]
        raise DeploymentError(f"Azure deployment command failed ({command[0]}): {detail}") from exc
    return result.stdout.strip()


def _dockerfile() -> str:
    return """FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app MPLCONFIGDIR=/tmp/matplotlib PORT=10000
WORKDIR /app
RUN apt-get update \\
    && apt-get install -y --no-install-recommends libgomp1 \\
    && rm -rf /var/lib/apt/lists/* \\
    && useradd --system --create-home --home-dir /home/creditai creditai \\
    && mkdir -p /tmp/matplotlib \\
    && chown creditai:creditai /tmp/matplotlib
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY models/ ./models/
COPY frontend/dist/ ./frontend/dist/
USER creditai
EXPOSE 10000
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \\
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:10000/health', timeout=4)" || exit 1
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "10000", "--workers", "1"]
"""


def deploy(release_dir: Path, version: str) -> dict[str, str]:
    """Build and publish the immutable release image, then update the live app."""
    if not re.fullmatch(r"[0-9a-f]{40}", version):
        raise DeploymentError("Azure deployment version must be the full lowercase Git commit SHA.")

    missing = [name for name in _REQUIRED_PATHS if not (release_dir / name).exists()]
    if missing:
        raise DeploymentError(f"Validated release is missing Azure image inputs: {', '.join(missing)}.")

    manifest_path = release_dir / "build-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeploymentError("Azure deployment requires the validated release build manifest.") from exc
    if manifest.get("commit_sha") != version or manifest.get("scoring_status") != "not_validated":
        raise DeploymentError("Azure image source does not match the validated release manifest and scoring status.")

    resource_group = _setting("AZURE_RESOURCE_GROUP")
    app_name = _setting("AZURE_CONTAINER_APP")
    registry_name = _setting("AZURE_CONTAINER_REGISTRY")

    current_details = _run(["az", "containerapp", "show", "--name", app_name,
                            "--resource-group", resource_group, "--output", "json"])
    try:
        current_app = json.loads(current_details)
        app_configuration = current_app["properties"]["configuration"]
        current_ingress = app_configuration["ingress"]
        fqdn = current_ingress.get("fqdn", "").strip()
        target_port = current_ingress.get("targetPort")
        revision_mode = str(app_configuration.get("activeRevisionsMode", "single")).strip().lower()
    except (json.JSONDecodeError, KeyError, AttributeError, TypeError) as exc:
        raise DeploymentError("Azure Container App must already exist with configured ingress.") from exc
    if current_ingress.get("external") is not True or not fqdn:
        raise DeploymentError("Azure Container App must have public external ingress before deployment.")
    if target_port != 10000:
        raise DeploymentError("Azure Container App ingress target port must be 10000 before deployment.")
    if revision_mode not in {"single", "multiple"}:
        raise DeploymentError("Azure Container App revision mode must be single or multiple.")

    login_server = _run([
        "az", "acr", "show", "--name", registry_name,
        "--resource-group", resource_group, "--query", "loginServer", "--output", "tsv",
    ])
    if not login_server or "/" in login_server:
        raise DeploymentError("Azure Container Registry returned an invalid login server.")
    image = f"{login_server}/creditai:{version}"

    with tempfile.TemporaryDirectory(prefix="creditai-azure-image-") as temp_dir:
        context = Path(temp_dir)
        shutil.copy2(release_dir / "requirements.txt", context / "requirements.txt")
        shutil.copytree(release_dir / "src", context / "src")
        shutil.copytree(release_dir / "models", context / "models")
        shutil.copytree(release_dir / "frontend" / "dist", context / "frontend" / "dist")
        (context / "Dockerfile").write_text(_dockerfile(), encoding="utf-8")

        _run(["az", "acr", "login", "--name", registry_name])
        _run(["docker", "build", "--pull", "--tag", image, str(context)], cwd=context)
        _run(["docker", "push", image])

    # Configure pulls through the app's managed identity; never enable ACR admin
    # credentials or pass registry passwords through GitHub Actions.
    _run(["az", "containerapp", "identity", "assign", "--name", app_name,
          "--resource-group", resource_group, "--system-assigned"])
    _run(["az", "containerapp", "registry", "set", "--name", app_name,
          "--resource-group", resource_group, "--server", login_server, "--identity", "system"])
    _run(["az", "containerapp", "update", "--name", app_name,
          "--resource-group", resource_group, "--image", image,
          "--set-env-vars", "PORT=10000", f"CREDITAI_BUILD_SHA={version}"])
    if revision_mode == "multiple":
        _run(["az", "containerapp", "ingress", "traffic", "set", "--name", app_name,
              "--resource-group", resource_group, "--revision-weight", "latest=100"])

    details = _run(["az", "containerapp", "show", "--name", app_name,
                    "--resource-group", resource_group, "--output", "json"])
    try:
        app = json.loads(details)
        revision = app["properties"].get("latestRevisionName", "").strip()
    except (json.JSONDecodeError, KeyError, AttributeError, TypeError) as exc:
        raise DeploymentError("Azure Container App did not return valid revision details.") from exc
    if not revision:
        raise DeploymentError("Azure Container App did not report a deployment revision.")
    return {"provider": PROVIDER_ID, "deployment_id": revision, "base_url": f"https://{fqdn}"}
