"""Invoke the configured deployment adapter and verify its live API."""

from __future__ import annotations

import json
import os
import sys
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.cicd.deployment import DeploymentError, deploy_with_configured_adapter, verify_live_deployment


def extract_verified_release(archive: Path, release_dir: Path, expected_sha: str) -> None:
    try:
        with zipfile.ZipFile(archive) as bundle:
            if bundle.testzip() is not None:
                raise DeploymentError("Release ZIP failed its CRC check.")
            names = [info.filename for info in bundle.infolist() if not info.is_dir()]
            if len(names) != len(set(names)):
                raise DeploymentError("Release ZIP contains duplicate file paths.")
            if "build-manifest.json" not in names:
                raise DeploymentError("Release ZIP is missing build-manifest.json.")
            manifest = json.loads(bundle.read("build-manifest.json"))
            if manifest.get("commit_sha") != expected_sha or manifest.get("worktree_clean") is not True:
                raise DeploymentError("Release manifest does not match the clean checked-out commit.")
            if manifest.get("scoring_status") != "not_validated":
                raise DeploymentError("Release manifest violates the production scoring safety status.")
            listed = set(manifest.get("contents", []))
            if listed != set(names) - {"build-manifest.json"}:
                raise DeploymentError("Release manifest contents do not match the ZIP contents.")
            required = {"requirements.txt", "src/api/app.py", "frontend/dist/index.html"}
            if not required.issubset(listed):
                raise DeploymentError("Release ZIP is missing required application files.")

            release_root = release_dir.resolve()
            for info in bundle.infolist():
                if info.is_dir():
                    continue
                relative = PurePosixPath(info.filename)
                if relative.is_absolute() or ".." in relative.parts:
                    raise DeploymentError("Release ZIP contains an unsafe file path.")
                destination = (release_root / Path(*relative.parts)).resolve()
                if not destination.is_relative_to(release_root):
                    raise DeploymentError("Release ZIP contains an unsafe file path.")
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(bundle.read(info))
    except (zipfile.BadZipFile, json.JSONDecodeError, OSError) as exc:
        raise DeploymentError(f"Unable to validate or extract release ZIP: {exc}") from exc


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/deploy_release.py <release-zip>", file=sys.stderr)
        return 2
    archive = Path(sys.argv[1]).resolve()
    version = os.getenv("GITHUB_SHA", "unknown")
    try:
        release_dir = archive.parent / f"release-unpacked-{version[:12]}"
        if release_dir.exists():
            raise DeploymentError("Release extraction directory already exists; use a clean deployment runner.")
        release_dir.mkdir(parents=True)
        extract_verified_release(archive, release_dir, version)
        result = deploy_with_configured_adapter(release_dir, version)
        verification = verify_live_deployment(result["base_url"], expected_version=version)
    except DeploymentError as exc:
        print(f"Deployment or verification failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"deployment": result, "verification": verification}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
