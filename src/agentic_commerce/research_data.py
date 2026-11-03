"""Read-only access to the verified Taiwan research workbook, when installed.

The raw dataset is intentionally not committed. This module never downloads or
falls back to example rows, and it never returns the dataset target.
"""

from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

from .schemas import ResearchDataStatus, TaiwanResearchRecord

DATASET_NAME = "UCI Taiwan Default of Credit Card Clients"
EXPECTED_SHA256 = "21b3cf4e30878150ae8db9386780e23febb613921747dec9e59dccb32f6104d3"
EXPECTED_ROWS = 30_000
TARGET_COLUMN = "default payment next month"
RECORD_COLUMNS = (
    "ID", "LIMIT_BAL", "SEX", "EDUCATION", "MARRIAGE", "AGE", "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6",
    "BILL_AMT1", "BILL_AMT2", "BILL_AMT3", "BILL_AMT4", "BILL_AMT5", "BILL_AMT6",
    "PAY_AMT1", "PAY_AMT2", "PAY_AMT3", "PAY_AMT4", "PAY_AMT5", "PAY_AMT6",
)


def dataset_candidates() -> list[Path]:
    root = Path(__file__).resolve().parents[2]
    override = os.getenv("CREDITAI_TAIWAN_DATASET_PATH", "").strip()
    candidates = [Path(override)] if override else []
    candidates.extend([
        root / "Data" / "credit_default" / "default of credit card clients.xls",
        root / "data" / "credit_default" / "default of credit card clients.xls",
    ])
    return candidates


@lru_cache(maxsize=1)
def _verified_frame() -> pd.DataFrame:
    path = next((candidate for candidate in dataset_candidates() if candidate.is_file()), None)
    if path is None:
        raise FileNotFoundError(
            "Research dataset unavailable. Install the UCI workbook locally and verify it with "
            "scripts/fetch_phase11_dataset.py; raw research data is not included in Git or the release."
        )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError(f"UCI research dataset SHA-256 mismatch: expected {EXPECTED_SHA256}, got {digest}.")
    frame = pd.read_excel(path, header=1)
    frame.columns = [str(column).strip() for column in frame.columns]
    required = set(RECORD_COLUMNS) | {TARGET_COLUMN}
    if len(frame) != EXPECTED_ROWS or not required.issubset(frame.columns):
        raise ValueError("Verified UCI workbook does not match the recorded research dataset structure.")
    if frame["ID"].duplicated().any():
        raise ValueError("Verified UCI workbook contains duplicate research record IDs.")
    return frame


def dataset_status() -> ResearchDataStatus:
    try:
        frame = _verified_frame()
    except FileNotFoundError as exc:
        return ResearchDataStatus(status="unavailable", sha256=EXPECTED_SHA256, message=str(exc))
    except (OSError, ValueError, ImportError) as exc:
        return ResearchDataStatus(
            status="unavailable",
            sha256=EXPECTED_SHA256,
            message=f"Research dataset could not be verified or read: {exc}",
        )
    return ResearchDataStatus(
        status="available",
        sha256=EXPECTED_SHA256,
        row_count=len(frame),
        message="Verified UCI Taiwan research data is available; the target column is withheld from records.",
    )


def _record_from_frame(frame: pd.DataFrame, source_row: int) -> TaiwanResearchRecord:
    if not 1 <= source_row <= len(frame):
        raise IndexError("Research record number is outside the verified dataset.")
    row = frame.iloc[source_row - 1]
    record_id = int(row["ID"])
    feature_columns = [
        "LIMIT_BAL", "SEX", "EDUCATION", "MARRIAGE", "AGE",
        "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6",
        *[f"BILL_AMT{month}" for month in range(1, 7)],
        *[f"PAY_AMT{month}" for month in range(1, 7)],
    ]
    repayment_columns = ["PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]
    statement_columns = [f"BILL_AMT{month}" for month in range(1, 7)]
    payment_columns = [f"PAY_AMT{month}" for month in range(1, 7)]
    return TaiwanResearchRecord(
        reference=f"UCI-TW-{record_id:05d}",
        source_row=source_row,
        features={column: int(row[column]) for column in feature_columns},
        credit_limit_twd=int(row["LIMIT_BAL"]),
        age_years=int(row["AGE"]),
        repayment_status_codes=[int(row[column]) for column in repayment_columns],
        statement_balances_twd=[int(row[column]) for column in statement_columns],
        payments_twd=[int(row[column]) for column in payment_columns],
    )


def list_research_records(offset: int = 0, limit: int = 25) -> tuple[int, list[TaiwanResearchRecord]]:
    frame = _verified_frame()
    start = max(offset, 0)
    stop = min(start + min(max(limit, 1), 100), len(frame))
    return len(frame), [_record_from_frame(frame, row_number) for row_number in range(start + 1, stop + 1)]


def get_research_record(reference: str) -> TaiwanResearchRecord:
    if not reference.startswith("UCI-TW-"):
        raise ValueError("Research record reference is invalid.")
    try:
        record_id = int(reference.removeprefix("UCI-TW-"))
    except ValueError as exc:
        raise ValueError("Research record reference is invalid.") from exc
    frame = _verified_frame()
    matches = frame.index[frame["ID"].astype(int) == record_id]
    if len(matches) != 1:
        raise LookupError("Research record was not found in the verified UCI dataset.")
    return _record_from_frame(frame, int(matches[0]) + 1)
