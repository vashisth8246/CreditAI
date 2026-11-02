"""Unit checks for the Azure Container Apps release adapter."""

import json
from pathlib import Path

import pytest

from src.cicd.azure_container_apps import deploy
from src.cicd.deployment import DeploymentError, PROVIDER_ADAPTERS, verify_live_deployment


def test_azure_provider_is_registered():
    assert PROVIDER_ADAPTERS["azure-container-apps"] == "src.cicd.azure_container_apps"


def _release(tmp_path: Path, sha: str) -> Path:
    root = tmp_path / "release"
    (root / "src" / "api").mkdir(parents=True)
    (root / "models").mkdir()
    (root / "frontend").mkdir()
    (root / "src" / "api" / "app.py").write_text("app = None", encoding="utf-8")
    (root / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (root / "frontend" / "index.html").write_text("<html></html>", encoding="utf-8")
    (root / "build-manifest.json").write_text(json.dumps({
        "commit_sha": sha,
        "scoring_status": "not_validated",
    }), encoding="utf-8")
    return root


def test_azure_adapter_fails_clearly_without_resource_configuration(tmp_path, monkeypatch):
    for key in ("AZURE_RESOURCE_GROUP", "AZURE_CONTAINER_APP", "AZURE_CONTAINER_REGISTRY"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(DeploymentError, match="AZURE_RESOURCE_GROUP"):
        deploy(_release(tmp_path, "a" * 40), "a" * 40)


@pytest.mark.parametrize(("revision_mode", "routes_latest"), [("Multiple", True), ("Single", False)])
def test_azure_adapter_builds_the_tested_release_and_routes_latest_revision(tmp_path, monkeypatch, revision_mode, routes_latest):
    sha = "a" * 40
    release = _release(tmp_path, sha)
    monkeypatch.setenv("AZURE_RESOURCE_GROUP", "creditai-rg")
    monkeypatch.setenv("AZURE_CONTAINER_APP", "creditai-app")
    monkeypatch.setenv("AZURE_CONTAINER_REGISTRY", "creditairegistry")
    commands = []

    def fake_run(command, *, cwd=None):
        commands.append((command, cwd))
        if command[:3] == ["az", "acr", "show"]:
            return "creditairegistry.azurecr.io"
        if command[:3] == ["az", "containerapp", "show"]:
            return json.dumps({
                "properties": {
                    "latestRevisionName": "creditai-app--abc123",
                    "configuration": {
                        "ingress": {
                            "external": True,
                            "fqdn": "creditai.example.azurecontainerapps.io",
                            "targetPort": 10000,
                        },
                        "activeRevisionsMode": revision_mode,
                    },
                },
            })
        if command[:3] == ["docker", "build", "--pull"]:
            dockerfile = Path(cwd, "Dockerfile").read_text(encoding="utf-8")
            assert "COPY frontend/ ./frontend/dist/" in dockerfile
            assert any(value.endswith(f"creditai:{sha}") for value in command)
        return ""

    monkeypatch.setattr("src.cicd.azure_container_apps._run", fake_run)
    result = deploy(release, sha)

    assert result == {
        "provider": "azure-container-apps",
        "deployment_id": "creditai-app--abc123",
        "base_url": "https://creditai.example.azurecontainerapps.io",
    }
    assert any("latest=100" in command for command, _ in commands) is routes_latest
    assert any("--identity" in command and "system" in command for command, _ in commands)


def test_azure_adapter_rejects_release_for_another_commit(tmp_path, monkeypatch):
    root = _release(tmp_path, "b" * 40)
    with pytest.raises(DeploymentError, match="does not match"):
        deploy(root, "a" * 40)


def test_azure_adapter_rejects_wrong_ingress_port_before_push(tmp_path, monkeypatch):
    sha = "c" * 40
    release = _release(tmp_path, sha)
    for name, value in {
        "AZURE_RESOURCE_GROUP": "creditai-rg",
        "AZURE_CONTAINER_APP": "creditai-app",
        "AZURE_CONTAINER_REGISTRY": "creditairegistry",
    }.items():
        monkeypatch.setenv(name, value)

    def fake_run(command, *, cwd=None):
        if command[:3] == ["az", "containerapp", "show"]:
            return json.dumps({
                "properties": {
                    "configuration": {"ingress": {
                        "external": True,
                        "fqdn": "creditai.example.azurecontainerapps.io",
                        "targetPort": 80,
                    }},
                },
            })
        pytest.fail(f"Deployment should stop before running: {command}")

    monkeypatch.setattr("src.cicd.azure_container_apps._run", fake_run)
    with pytest.raises(DeploymentError, match="target port must be 10000"):
        deploy(release, sha)


def test_live_verification_requires_the_expected_build_sha(monkeypatch):
    sha = "d" * 40
    payloads = {
        "/health": {"status": "ok", "scoring": "not_validated"},
        "/v1/status": {"indian_production_scoring": "not_validated"},
        "/v1/build": {"commit_sha": sha},
    }
    requested = []

    class Response:
        def __init__(self, body):
            self.body = json.dumps(body).encode()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return self.body

    def fake_urlopen(url, timeout):
        requested.append(url)
        return Response(payloads[url.removeprefix("https://creditai.example")])

    monkeypatch.setattr("src.cicd.deployment.urlopen", fake_urlopen)
    result = verify_live_deployment("https://creditai.example", expected_version=sha)
    assert result["build"]["commit_sha"] == sha
    assert len(requested) == 3

    payloads["/v1/build"] = {"commit_sha": "e" * 40}
    with pytest.raises(DeploymentError, match="does not report the deployed release commit SHA"):
        verify_live_deployment("https://creditai.example", expected_version=sha)
