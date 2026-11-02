from pathlib import Path

from scripts.package_release import frontend_release_files


def test_frontend_release_files_excludes_public_batch_test_fixtures(tmp_path: Path):
    dist = tmp_path / "dist"
    production_files = (
        "index.html",
        "assets/app.js",
        "data/phase_9_lendingclub_summary.json",
    )
    test_fixtures = (
        "batch_test_sample.csv",
        "batch_test_sample.xlsx",
        "testdata/header_only.csv",
        "testdata/portfolio_multisheet.xlsx",
        "testdata/unsupported.txt",
    )
    for relative in production_files + test_fixtures:
        path = dist / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")

    packaged = frontend_release_files(dist)
    names = {archive_name for _, archive_name in packaged}

    assert names == {f"frontend/dist/{name}" for name in production_files}
