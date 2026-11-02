from scripts.package_release import frontend_release_files


def test_frontend_release_files_exclude_unreferenced_public_test_fixtures(tmp_path):
    dist = tmp_path / "dist"
    for relative in (
        "index.html",
        "assets/app.js",
        "batch_test_sample.csv",
        "batch_test_sample.xlsx",
        "testdata/corrupted.xlsx",
        "testdata/header_only.csv",
    ):
        path = dist / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")

    included = {path.relative_to(dist).as_posix() for path in frontend_release_files(dist)}

    assert included == {"index.html", "assets/app.js"}
