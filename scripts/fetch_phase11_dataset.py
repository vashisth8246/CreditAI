"""Fetch or verify the licensed UCI Taiwan research workbook without tracking it.

The raw dataset remains in the root Data/ directory, which is gitignored.
The download is accepted only when its extracted workbook matches the SHA-256
recorded by the Phase 11 experiment.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import sys
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "Data" / "credit_default" / "default of credit card clients.xls"
ARCHIVE_URL = (
    "https://archive.ics.uci.edu/static/public/350/"
    "default%2Bof%2Bcredit%2Bcard%2Bclients.zip"
)
EXPECTED_SHA256 = "21b3cf4e30878150ae8db9386780e23febb613921747dec9e59dccb32f6104d3"
EXPECTED_MEMBER = "default of credit card clients.xls"
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024
MAX_DATASET_BYTES = 10 * 1024 * 1024


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_file(path: Path = DATA_PATH) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"UCI workbook not found: {path}")
    actual = sha256(path.read_bytes())
    if actual != EXPECTED_SHA256:
        raise ValueError(
            f"Dataset SHA-256 mismatch for {path}: expected {EXPECTED_SHA256}, got {actual}. "
            "The file was not modified."
        )
    print(f"Verified UCI Taiwan dataset: {path}")
    print(f"SHA-256: {actual}")


def download_file(url: str = ARCHIVE_URL) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "CreditAI-Phase11-research/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError(f"UCI dataset download returned HTTP {response.status}.")
        content = response.read(MAX_ARCHIVE_BYTES + 1)
    if len(content) > MAX_ARCHIVE_BYTES:
        raise ValueError(f"UCI archive exceeds the {MAX_ARCHIVE_BYTES}-byte safety limit.")
    return content


def fetch_verified_dataset() -> None:
    if DATA_PATH.exists():
        verify_file(DATA_PATH)
        return

    archive_bytes = download_file()
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        matches = [
            item for item in archive.infolist()
            if PurePosixPath(item.filename.replace("\\", "/")).name.casefold()
            == EXPECTED_MEMBER.casefold()
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Expected one '{EXPECTED_MEMBER}' entry in the UCI archive; found {len(matches)}."
            )
        member = matches[0]
        if member.file_size > MAX_DATASET_BYTES:
            raise ValueError(f"Dataset entry exceeds the {MAX_DATASET_BYTES}-byte safety limit.")
        dataset_bytes = archive.read(member)  # also validates the ZIP member CRC

    actual = sha256(dataset_bytes)
    if actual != EXPECTED_SHA256:
        raise ValueError(
            f"Downloaded dataset SHA-256 mismatch: expected {EXPECTED_SHA256}, got {actual}. "
            "Nothing was written."
        )

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = DATA_PATH.with_suffix(DATA_PATH.suffix + ".phase11-download.tmp")
    try:
        temporary.write_bytes(dataset_bytes)
        temporary.replace(DATA_PATH)
    finally:
        temporary.unlink(missing_ok=True)
    verify_file(DATA_PATH)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify the local ignored dataset without downloading it.",
    )
    args = parser.parse_args()
    try:
        if args.verify_only:
            verify_file(DATA_PATH)
        else:
            fetch_verified_dataset()
    except Exception as exc:
        print(f"Dataset preparation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
