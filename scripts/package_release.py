"""Package a traceable release without datasets, logs, or local artifacts."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def tracked_release_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", "src", "models", "requirements.txt"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / name for name in result.stdout.decode().split("\0") if name]


def registered_model_paths() -> set[str]:
    registry_path = ROOT / "src" / "inference" / "model_registry.py"
    module = ast.parse(registry_path.read_text(encoding="utf-8"), filename=str(registry_path))
    api_path = ROOT / "src" / "api" / "app.py"
    api_module = ast.parse(api_path.read_text(encoding="utf-8"), filename=str(api_path))
    api_model_paths = {
        node.value
        for node in ast.walk(api_module)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value.startswith("models/")
        and node.value.endswith((".joblib", ".json"))
    }
    for node in module.body:
        is_models_assign = isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "MODELS" for target in node.targets
        )
        is_models_annotated_assign = (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "MODELS"
        )
        if is_models_assign or is_models_annotated_assign:
            models = ast.literal_eval(node.value)
            registry_paths = {
                model[key]
                for model in models.values()
                for key in ("artifact_path", "calibration_path", "feature_names_path", "metadata_path")
                if key in model
            }
            # The KNN joblib bundle contains a KNNNeighborExplainer instance.
            # Python must import its defining module when it unpickles the bundle.
            if any(
                str(model.get("model_type", "")).lower().startswith("k-nearest")
                for model in models.values()
            ):
                registry_paths.add("src/models/knn.py")
            return registry_paths | api_model_paths
    raise SystemExit("Unable to verify required model paths in src/inference/model_registry.py")


def frontend_release_files(dist: Path) -> list[tuple[Path, str]]:
    """Return production frontend files, excluding public batch-test fixtures."""
    entries: list[tuple[Path, str]] = []
    for path in dist.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(dist).as_posix()
        if relative.startswith("testdata/") or relative in {
            "batch_test_sample.csv",
            "batch_test_sample.xlsx",
        }:
            continue
        entries.append((path, f"frontend/dist/{relative}"))
    return entries


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if dirty:
        raise SystemExit(
            "Release packaging requires a clean tracked worktree so the source commit SHA matches the packaged code."
        )

    head_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    branch = subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, text=True,
    ).strip()
    sha = os.getenv("GITHUB_SHA") or head_sha
    if sha != head_sha:
        raise SystemExit(f"GITHUB_SHA ({sha}) does not match checked-out commit ({head_sha}).")
    dist = ROOT / "frontend" / "dist"
    if not (dist / "index.html").is_file():
        raise SystemExit("Frontend build is missing: run npm run build in frontend first.")

    output = ROOT / "release"
    output.mkdir(exist_ok=True)
    archive_path = output / f"creditai-{sha}.zip"
    tracked_files = tracked_release_files()
    missing = [path.relative_to(ROOT).as_posix() for path in tracked_files if not path.is_file()]
    if missing:
        raise SystemExit(f"Tracked release inputs are missing: {', '.join(missing)}")
    entries = [(path, path.relative_to(ROOT).as_posix()) for path in tracked_files]
    included_paths = {name for _, name in entries}
    missing_models = sorted(registered_model_paths() - included_paths)
    if missing_models:
        raise SystemExit(f"Registered model files are not included in the release: {', '.join(missing_models)}")
    entries.extend(frontend_release_files(dist))

    calibration_path = ROOT / "models" / "calibration_model.joblib"
    if not calibration_path.is_file():
        raise SystemExit("Required shipped calibration artifact is missing from the release.")
    backend_test_result = os.getenv(
        "CREDITAI_BACKEND_TEST_RESULT",
        "PASS (GitHub Actions packaging depends on the successful backend test job)"
        if os.getenv("GITHUB_ACTIONS") == "true" else "NOT_RECORDED",
    )
    frontend_test_result = os.getenv(
        "CREDITAI_FRONTEND_TEST_RESULT",
        "PASS (GitHub Actions packaging depends on successful frontend checks)"
        if os.getenv("GITHUB_ACTIONS") == "true" else "NOT_RECORDED",
    )
    manifest = {
        "application": "CreditAI",
        "branch": branch,
        "commit_sha": sha,
        "version": sha[:12],
        "worktree_clean": True,
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "contents": [name for _, name in entries],
        "frontend_build_status": "PASS",
        "backend_test_result": backend_test_result,
        "frontend_test_result": frontend_test_result,
        "calibration_sha256": sha256(calibration_path),
        "dataset_provisioning_mode": "external_verified_workbook_required; raw_workbook_not_packaged",
        "scoring_status": "not_validated",
        "score_safety_status": {
            "score_status": "not_validated",
            "score_type": "none",
            "default_probability": None,
            "validated_risk_estimate": False,
            "model_version": None,
        },
    }
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path, arcname in entries:
            bundle.write(path, arcname)
        bundle.writestr("build-manifest.json", json.dumps(manifest, indent=2) + "\n")
    package_hash = sha256(archive_path)
    release_manifest = {
        **manifest,
        "artifact": archive_path.name,
        "package_sha256": package_hash,
    }
    sidecar_path = archive_path.with_suffix(".manifest.json")
    sidecar_path.write_text(json.dumps(release_manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "artifact": str(archive_path), "manifest": str(sidecar_path),
        "package_sha256": package_hash, "version": sha[:12], "file_count": len(entries),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
