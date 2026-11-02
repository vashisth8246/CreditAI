"""Provider adapter contract and post-deployment health verification.

A configured adapter module must expose ``deploy(release_dir, version)`` and
    return a mapping containing provider, deployment_id, and base_url. The adapter
    is responsible for validating required configuration/credentials, authenticating
    with its provider, and raising on failure.
"""

from __future__ import annotations

import importlib
import json
import os
import time
from collections.abc import Mapping
from urllib.error import URLError
from urllib.request import urlopen
from pathlib import Path
from typing import Any


class DeploymentError(RuntimeError):
    """Raised when deployment or live verification fails."""


# Register a provider only after its adapter has been implemented, reviewed,
# and tested. An empty registry deliberately means no provider is deployable.
PROVIDER_ADAPTERS: dict[str, str] = {
    "azure-container-apps": "src.cicd.azure_container_apps",
}


def load_configured_adapter():
    provider = os.getenv("DEPLOYMENT_PROVIDER", "").strip().lower()
    if not provider:
        raise DeploymentError("DEPLOYMENT_PROVIDER is not configured.")
    module_name = PROVIDER_ADAPTERS.get(provider)
    if not module_name:
        raise DeploymentError(
            f"Unsupported deployment provider '{provider}'; no reviewed adapter is registered."
        )
    try:
        adapter = importlib.import_module(module_name)
    except ImportError as exc:
        raise DeploymentError(f"Unable to import deployment adapter '{module_name}'.") from exc
    if getattr(adapter, "PROVIDER_ID", None) != provider:
        raise DeploymentError(
            f"Deployment adapter '{module_name}' must declare PROVIDER_ID='{provider}'."
        )
    deploy = getattr(adapter, "deploy", None)
    if not callable(deploy):
        raise DeploymentError(f"Deployment adapter '{module_name}' must define deploy(release_dir, version).")
    return provider, deploy


def deploy_with_configured_adapter(release_dir: Path, version: str) -> dict[str, Any]:
    provider, deploy = load_configured_adapter()
    result = deploy(release_dir, version)
    if not isinstance(result, Mapping):
        raise DeploymentError("Deployment adapter must return a mapping with provider, deployment_id, and base_url.")
    required = ("provider", "deployment_id", "base_url")
    if any(not str(result.get(key, "")).strip() for key in required):
        raise DeploymentError("Deployment adapter returned an incomplete deployment result.")
    if str(result["provider"]).strip().lower() != provider:
        raise DeploymentError(
            f"Deployment adapter reported provider '{result['provider']}', expected configured provider '{provider}'."
        )
    return {key: str(result[key]) for key in required}


def verify_live_deployment(
    base_url: str,
    *,
    expected_version: str | None = None,
    attempts: int = 12,
    delay_seconds: float = 5,
) -> dict[str, Any]:
    """Check health and status without asserting that research models are valid."""
    base = base_url.rstrip("/")
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urlopen(f"{base}/health", timeout=5) as response:
                health = json.load(response)
            with urlopen(f"{base}/v1/status", timeout=5) as response:
                status = json.load(response)
            build = None
            if expected_version is not None:
                with urlopen(f"{base}/v1/build", timeout=5) as response:
                    build = json.load(response)
            if health.get("status") != "ok":
                raise DeploymentError("Live /health response did not report status=ok.")
            if health.get("scoring") != "not_validated" or status.get("indian_production_scoring") != "not_validated":
                raise DeploymentError("Live API violated the not_validated production scoring contract.")
            if expected_version is not None and build.get("commit_sha") != expected_version:
                raise DeploymentError("Live /v1/build does not report the deployed release commit SHA.")
            result = {"health": health, "status": status}
            if build is not None:
                result["build"] = build
            return result
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(delay_seconds)
    raise DeploymentError(f"Live API verification failed after {attempts} attempts: {last_error}")
