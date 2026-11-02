"""End-to-end tests for the batch research inference workflow.

These tests exercise the real FastAPI adapter, the real workbook parser and the
real Taiwan model artifact. They deliberately use representative workbooks
rather than mocking the service layer, because the batch feature's main risks
are parsing, mapping, row accounting and export fidelity.
"""
from __future__ import annotations

import io
import json

import openpyxl
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.batch_service import (
    MAX_ROWS,
    MAX_UPLOAD_BYTES,
    build_export_rows,
    build_csv,
    build_xlsx,
    inspect_workbook,
    predict_workbook,
)

client = TestClient(app)

COLS = [
    "LIMIT_BAL", "SEX", "EDUCATION", "MARRIAGE", "AGE",
    "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6",
    "BILL_AMT1", "BILL_AMT2", "BILL_AMT3", "BILL_AMT4", "BILL_AMT5", "BILL_AMT6",
    "PAY_AMT1", "PAY_AMT2", "PAY_AMT3", "PAY_AMT4", "PAY_AMT5", "PAY_AMT6",
]
LOW = [200000, 2, 1, 2, 34, 0, 0, 0, 0, 0, 0, 15000, 14000, 13000, 12000, 11000, 10000, 5000, 4500, 4000, 3500, 3000, 2500]
MEDIUM = [80000, 2, 2, 2, 31, 1, 0, 0, 0, 0, 0, 40000, 39000, 38000, 37000, 36000, 35000, 1500, 1400, 1300, 1200, 1100, 1000]
DELINQUENT = [20000, 1, 3, 2, 39, 2, 2, 1, 0, 0, 0, 19000, 18000, 17000, 16000, 15000, 14000, 300, 300, 300, 300, 300, 300]
MALFORMED = list(LOW)
MALFORMED[2] = 99  # EDUCATION is not in {1..6}


def workbook_bytes(sheets: dict[str, list[list[object]]]) -> bytes:
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    for name, rows in sheets.items():
        worksheet = workbook.create_sheet(name)
        for row in rows:
            worksheet.append(row)
    stream = io.BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def csv_bytes(rows: list[list[object]], bom: bool = False) -> bytes:
    text = "\r\n".join(",".join(str(value) for value in row) for row in rows) + "\r\n"
    return (("\ufeff" if bom else "") + text).encode("utf-8")


def inspect(content: bytes, filename: str, sheet: str | None = None, mapping: dict | None = None):
    data = {}
    if sheet is not None:
        data["sheet"] = sheet
    if mapping is not None:
        data["mapping"] = json.dumps(mapping)
    response = client.post(
        "/v1/research/taiwan/batch/inspect",
        files={"file": (filename, content, "application/octet-stream")},
        data=data,
    )
    return response


def analyze(content: bytes, filename: str, sheet: str, mapping: dict):
    return client.post(
        "/v1/research/taiwan/batch/analyze",
        files={"file": (filename, content, "application/octet-stream")},
        data={"sheet": sheet, "mapping": json.dumps(mapping)},
    )


def predict(content: bytes, filename: str, sheets: list[dict] | None = None):
    data = {"sheets": json.dumps(sheets)} if sheets is not None else {}
    return client.post(
        "/v1/research/taiwan/batch-predict",
        files={"file": (filename, content, "application/octet-stream")},
        data=data,
    )


def full_mapping(headers: list[str], overrides: dict[int, str] | None = None) -> dict[str, str]:
    """Map every unique header exactly once; duplicate headers must be explicit."""
    mapping: dict[str, str] = {}
    seen: set[str] = set()
    for index, header in enumerate(headers):
        key = str(header).strip().upper().replace(" ", "_")
        if key in seen:
            continue
        seen.add(key)
        mapping[str(index)] = key
    if overrides:
        for index, target in overrides.items():
            mapping[str(index)] = target
    return mapping


# ---------------------------------------------------------------------------
# Inspection and validation
# ---------------------------------------------------------------------------

def test_inspect_valid_csv_with_bom_and_reference():
    content = csv_bytes([
        ["borrower_reference", *COLS, "customer_id", "notes"],
        ["csv-low", *LOW, "C-1", "metadata"],
        ["csv-bad", *MALFORMED, "C-2", "metadata"],
    ], bom=True)

    response = inspect(content, "valid.csv")

    assert response.status_code == 200
    data = response.json()
    assert data["file_format"] == "csv"
    assert data["sheet_count"] == 1
    assert data["multi_sheet_compatible"] is True
    analysis = data["analysis"]
    assert analysis["status"] == "ready_with_errors"
    assert analysis["validation"]["valid_rows"] == 1
    assert analysis["validation"]["invalid_rows"] == 1
    # CSV text is not an Excel "number stored as text" warning; warning noise is
    # suppressed for delimited text while values are still validated.
    assert analysis["validation"]["warning_rows"] == 0
    assert analysis["mapping"]["0"] == "borrower_reference"
    assert analysis["row_numbers"] == [2, 3]
    # Unmapped identifiers stay metadata and are never sent to the model.
    assert analysis["identifier_columns"][0]["name"] == "customer_id"
    assert {item["name"] for item in analysis["extra_columns"]} == {"customer_id", "notes"}


def test_inspect_multisheet_summary_blank_and_duplicate_detection():
    duplicate_headers = list(COLS)
    duplicate_headers[5] = "PAY_0"
    duplicate_headers[6] = "PAY_0"
    content = workbook_bytes({
        "Portfolio": [[*COLS, "borrower_reference"], [*LOW, "p-low"], [*MEDIUM, "p-medium"]],
        "Incomplete": [["LIMIT_BAL", "SEX", "EDUCATION"], [200000, 2, 1]],
        "Blank": [],
        "Duplicates": [[*duplicate_headers, "borrower_reference"], [*LOW, "dup"]],
    })

    response = inspect(content, "multi.xlsx")
    assert response.status_code == 200
    data = response.json()

    assert data["file_format"] == "xlsx"
    assert data["sheet_count"] == 4
    assert data["multi_sheet_compatible"] is False
    by_name = {sheet["name"]: sheet for sheet in data["sheets"]}
    assert by_name["Portfolio"]["status"] == "ready"
    assert by_name["Incomplete"]["status"] == "needs_mapping"
    assert by_name["Blank"]["status"] == "blank"
    assert by_name["Duplicates"]["missing_fields"] == ["PAY_0", "PAY_2"]
    assert len(by_name["Duplicates"]["duplicate_headers"]) == 1
    duplicate = by_name["Duplicates"]["duplicate_headers"][0]
    assert duplicate["kind"] == "exact"
    assert duplicate["count"] == 2
    # The first non-blank worksheet is selected by default and analysed.
    assert data["selected_sheet"] == "Portfolio"
    assert data["analysis"]["validation"]["valid_rows"] == 2


def test_inspect_missing_schema_is_precise_and_never_fabricated():
    content = workbook_bytes({
        "Incomplete": [["LIMIT_BAL", "SEX", "EDUCATION", "MARRIAGE", "AGE", "borrower_reference"], [200000, 2, 1, 2, 34, "x"]],
    })
    response = inspect(content, "incomplete.xlsx")
    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["status"] == "needs_mapping"
    assert analysis["usable"] is False
    assert analysis["validation"]["valid_rows"] == 0
    assert analysis["validation"]["invalid_rows"] == 0
    assert len(analysis["missing_fields"]) == 18
    assert "PAY_2" in analysis["missing_fields"]


def test_analyze_explicit_mapping_accepts_spaces_and_case():
    spaced = [column.replace("_", " ") for column in COLS]
    content = workbook_bytes({
        "Spaces": [[*spaced, "BORROWER REFERENCE"], [*LOW, "spaced-low"]],
    })
    first = inspect(content, "spaces.xlsx", sheet="Spaces")
    assert first.status_code == 200
    analysis = first.json()["analysis"]
    assert analysis["status"] == "ready"
    assert analysis["mapping"]["0"] == "LIMIT_BAL"

    response = analyze(content, "spaces.xlsx", "Spaces", analysis["mapping"])
    assert response.status_code == 200
    assert response.json()["analysis"]["status"] == "ready"


def test_analyze_duplicate_target_is_rejected_without_guessing():
    content = workbook_bytes({"Sheet1": [[*COLS], [*LOW]]})
    first = inspect(content, "dup-target.xlsx", sheet="Sheet1")
    mapping = first.json()["analysis"]["mapping"]
    mapping["3"] = "EDUCATION"  # MARRIAGE already maps to EDUCATION

    response = analyze(content, "dup-target.xlsx", "Sheet1", mapping)

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["usable"] is False
    assert analysis["status"] == "needs_mapping"
    assert analysis["mapping_errors"]
    assert "more than one column" in analysis["mapping_errors"][0]


def test_explicit_mapping_resolves_duplicate_headers():
    duplicate_headers = list(COLS)
    duplicate_headers[5] = "PAY_0"
    duplicate_headers[6] = "PAY_0"
    content = workbook_bytes({
        "Duplicates": [[*duplicate_headers, "borrower_reference"], [*LOW, "dup-explicit"]],
    })
    first = inspect(content, "dup.xlsx", sheet="Duplicates")
    assert first.status_code == 200
    analysis = first.json()["analysis"]
    mapping = analysis["mapping"]
    mapping["5"] = "PAY_0"
    mapping["6"] = "PAY_2"

    response = analyze(content, "dup.xlsx", "Duplicates", mapping)

    assert response.status_code == 200
    resolved = response.json()["analysis"]
    assert resolved["usable"] is True
    assert resolved["status"] == "ready"
    assert resolved["validation"]["valid_rows"] == 1
    assert resolved["mapping"]["5"] == "PAY_0"
    assert resolved["mapping"]["6"] == "PAY_2"


# ---------------------------------------------------------------------------
# Prediction accounting
# ---------------------------------------------------------------------------

def test_predict_preserves_sheet_order_rows_and_references():
    content = workbook_bytes({
        "First": [[*COLS, "borrower_reference"], [*LOW, "first-low"], [*MALFORMED, "first-bad"], [*DELINQUENT, "first-delinquent"]],
        "Second": [[*COLS, "borrower_reference"], [*MEDIUM, "second-medium"], [*LOW, "second-low"]],
    })
    inspected = inspect(content, "ordered.xlsx", sheet="First").json()
    first_mapping = inspected["analysis"]["mapping"]
    second_mapping = inspect(content, "ordered.xlsx", sheet="Second").json()["analysis"]["mapping"]

    response = predict(content, "ordered.xlsx", [
        {"name": "Second", "mapping": second_mapping},
        {"name": "First", "mapping": first_mapping},
    ])

    assert response.status_code == 200
    data = response.json()
    assert [sheet["name"] for sheet in data["sheets"]] == ["Second", "First"]
    assert data["sheets"][0]["scored"] == 2
    assert data["sheets"][1]["scored"] == 2
    assert data["sheets"][1]["failed"] == 1
    observed = [(row["sheet_name"], row["source_row"], row["borrower_reference"], row["status"]) for row in data["results"]]
    assert observed == [
        ("Second", 2, "second-medium", "success"),
        ("Second", 3, "second-low", "success"),
        ("First", 2, "first-low", "success"),
        ("First", 3, "first-bad", "error"),
        ("First", 4, "first-delinquent", "success"),
    ]
    assert [row["result_index"] for row in data["results"]] == [1, 2, 3, 4, 5]
    assert data["calibrated"] is True
    assert data["results"][3]["error_message"].startswith("EDUCATION:")
    assert all("probability" in row["prediction"] for row in data["results"] if row["status"] == "success")


def test_predict_requires_complete_mapping_and_never_imputes():
    content = workbook_bytes({
        "Incomplete": [["LIMIT_BAL", "SEX", "EDUCATION", "MARRIAGE", "AGE"], [200000, 2, 1, 2, 34]],
    })
    mapping = {"0": "LIMIT_BAL", "1": "SEX", "2": "EDUCATION", "3": "MARRIAGE", "4": "AGE"}

    response = predict(content, "incomplete.xlsx", [{"name": "Incomplete", "mapping": mapping}])

    assert response.status_code == 422
    message = response.json()["error"]["message"]
    assert "missing required model features" in message
    assert "PAY_0" in message


def test_predict_rejects_blank_and_unknown_sheets():
    content = workbook_bytes({"Data": [[*COLS], [*LOW]], "Blank": []})
    mapping = inspect(content, "blank.xlsx", sheet="Data").json()["analysis"]["mapping"]

    blank = predict(content, "blank.xlsx", [{"name": "Blank", "mapping": mapping}])
    assert blank.status_code == 422
    assert "blank" in blank.json()["error"]["message"].lower()

    unknown = predict(content, "blank.xlsx", [{"name": "Nope", "mapping": mapping}])
    assert unknown.status_code == 422
    assert "not found" in unknown.json()["error"]["message"]


def test_formula_cells_are_rejected_not_trusted():
    content = workbook_bytes({
        "Formulas": [[*COLS, "borrower_reference"], [*LOW, "ok"], ["=100000+100000", *LOW[1:], "formula"]],
    })
    inspected = inspect(content, "formulas.xlsx", sheet="Formulas")
    assert inspected.status_code == 200
    analysis = inspected.json()["analysis"]
    assert analysis["formula_detection"] == "xlsx"
    assert analysis["validation"]["valid_rows"] == 1
    assert analysis["validation"]["invalid_rows"] == 1
    assert "formula" in analysis["validation"]["errors"][0]["message"].lower()

    mapping = analysis["mapping"]
    response = predict(content, "formulas.xlsx", [{"name": "Formulas", "mapping": mapping}])
    assert response.status_code == 200
    result = response.json()["results"][1]
    assert result["status"] == "error"
    assert "formula" in result["error_message"].lower()


def test_blank_rows_are_ignored_but_source_rows_are_preserved():
    content = workbook_bytes({
        "Gaps": [[*COLS], [*LOW], [None] * len(COLS), [*MEDIUM]],
    })
    response = inspect(content, "gaps.xlsx", sheet="Gaps")
    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["row_count"] == 2
    assert analysis["blank_rows_ignored"] == 1
    assert analysis["row_numbers"] == [2, 4]


# ---------------------------------------------------------------------------
# Reading failures and limits
# ---------------------------------------------------------------------------

def test_empty_corrupt_unsupported_and_oversized_uploads():
    empty = client.post(
        "/v1/research/taiwan/batch/inspect",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert empty.status_code == 400
    assert "empty" in empty.json()["error"]["message"].lower()

    corrupt = client.post(
        "/v1/research/taiwan/batch/inspect",
        files={"file": ("broken.xlsx", b"not a workbook at all", "application/octet-stream")},
    )
    assert corrupt.status_code == 400
    assert "corrupt" in corrupt.json()["error"]["message"].lower()

    unsupported = client.post(
        "/v1/research/taiwan/batch/inspect",
        files={"file": ("data.txt", b"LIMIT_BAL\n1\n", "text/plain")},
    )
    assert unsupported.status_code == 415

    oversized = client.post(
        "/v1/research/taiwan/batch/inspect",
        files={"file": ("large.csv", b"a" * (MAX_UPLOAD_BYTES + 1), "text/csv")},
    )
    assert oversized.status_code == 413


def test_row_limit_is_enforced_after_parsing():
    rows = [COLS] + [[*LOW] for _ in range(MAX_ROWS + 1)]
    content = workbook_bytes({"Too many": rows})
    response = inspect(content, "too-many.xlsx", sheet="Too many")
    assert response.status_code == 400
    assert "maximum" in response.json()["error"]["message"].lower()


def test_csv_renamed_as_xlsx_uses_safe_fallback():
    content = csv_bytes([["borrower_reference", *COLS], ["renamed", *LOW]])
    response = inspect(content, "actually-a-csv.xlsx")
    assert response.status_code == 200
    data = response.json()
    assert data["file_format"] == "csv"
    assert data["analysis"]["validation"]["valid_rows"] == 1


def test_excel_numbers_stored_as_text_are_warned():
    text_row = [str(value) for value in LOW]
    text_row[0] = "200000"
    content = workbook_bytes({
        "Text numbers": [[*COLS], text_row],
    })
    response = inspect(content, "text.xlsx", sheet="Text numbers")
    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["validation"]["valid_rows"] == 1
    assert analysis["validation"]["warning_rows"] == 1
    assert "stored as text" in analysis["validation"]["warnings"][0]["message"]


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

def _prediction_payload():
    return {
        "model_id": "uci_taiwan_xgb",
        "file_name": "export.xlsx",
        "file_format": "xlsx",
        "generated_at": "2026-10-21T00:00:00+00:00",
        "calibration_method": "Platt scaling (sigmoid)",
        "sheets": [{"name": "Portfolio", "total_rows": 2, "scored": 1, "failed": 1}],
        "results": [
            {
                "result_index": 1,
                "sheet_name": "Portfolio",
                "source_row": 2,
                "row_index": 1,
                "borrower_reference": "=cmd|calc",
                "status": "success",
                "prediction": {
                    "model_id": "uci_taiwan_xgb",
                    "probability": 0.123456,
                    "risk_category": "Low",
                    "predicted_class": "Lower predicted default risk",
                    "calibrated": True,
                    "threshold": 0.5,
                    "dataset_name": "Default of Credit Card Clients",
                    "geography": "Taiwan",
                    "calibration_method": "Platt scaling (sigmoid)",
                    "feature_contributions": [
                        {"feature": "PAY_0", "contribution": 0.31, "direction": "increases_risk"},
                        {"feature": "PAY_AMT1", "contribution": 0.08, "direction": "decreases_risk"},
                    ],
                },
                "submitted_features": {"PAY_0": 2, "PAY_AMT1": 500},
            },
            {
                "result_index": 2,
                "sheet_name": "Portfolio",
                "source_row": 3,
                "row_index": 2,
                "borrower_reference": "failed-row",
                "status": "error",
                "error_message": "EDUCATION: value is not one of the allowed category codes.",
            },
        ],
    }


def test_csv_export_is_ordered_and_formula_injection_safe():
    response = client.post(
        "/v1/research/taiwan/batch/export/csv",
        json={**_prediction_payload(), "summary": {"total": 2, "succeeded": 1, "failed": 1}},
    )
    assert response.status_code == 200
    text = response.text
    assert response.headers["content-disposition"].startswith("attachment")
    assert text.startswith('"Result #","Sheet","Source row","Sheet row","Borrower reference"')
    assert "'=cmd|calc" in text
    assert '"1","Portfolio","2","1","\'=cmd|calc"' in text
    assert '"2","Portfolio","3","2","failed-row"' in text
    assert text.index("=cmd|calc") < text.index("failed-row")
    assert '"Research classification"' in text
    assert '"Threshold comparison"' in text
    assert '"PAY 0 (0.3100 model-output units)"' in text
    assert '"PAY AMT1 (0.0800 model-output units)"' in text
    assert '"Default of Credit Card Clients (Taiwan); Platt scaling (sigmoid)"' in text
    assert '"Research only; not validated for Indian borrowers or lending"' in text


def test_xlsx_export_has_summary_formatting_and_injection_protection():
    payload = _prediction_payload()
    payload["summary"] = {
        "total": 2,
        "succeeded": 1,
        "failed": 1,
        "meanProbability": 0.123456,
        "medianProbability": 0.123456,
        "lowRisk": 1,
        "mediumRisk": 0,
        "highRisk": 0,
        "histogram": [{"label": "10% to <20%", "count": 1}],
    }
    response = client.post("/v1/research/taiwan/batch/export/xlsx", json=payload)
    assert response.status_code == 200
    assert response.content[:2] == b"PK"

    workbook = openpyxl.load_workbook(io.BytesIO(response.content))
    assert workbook.sheetnames == ["Predictions", "Summary"]
    predictions = workbook["Predictions"]
    assert predictions["A2"].value == 1
    assert predictions["B2"].value == "Portfolio"
    assert predictions["E2"].value == "'=cmd|calc"
    assert predictions["G2"].value == 0.123456
    assert predictions["G2"].number_format == "0.00%"
    assert predictions["N1"].value == "Research classification"
    assert predictions["O2"].value == "0.1235 < 0.5000"
    assert "PAY 0" in predictions["P2"].value
    assert "PAY AMT1" in predictions["Q2"].value
    assert "Taiwan" in predictions["R2"].value
    assert "not validated for Indian borrowers" in predictions["S2"].value
    assert predictions["F3"].value == "Failed"
    summary = workbook["Summary"]
    labels = [row[0].value for row in summary.iter_rows(min_row=1, max_row=summary.max_row)]
    assert "Total rows submitted" in labels
    assert "High risk (>=50%)" in labels


def test_exports_compute_non_default_complement_only_for_valid_probabilities():
    results = [
        {"result_index": 1, "row_index": 1, "status": "success", "prediction": {"probability": 0.123456}},
        {"result_index": 2, "row_index": 2, "status": "success", "prediction": {"probability": 1.2}},
        {"result_index": 3, "row_index": 3, "status": "error"},
    ]
    rows = build_export_rows(results)
    assert rows[0][7] == pytest.approx(0.876544)
    assert rows[1][7] is None
    assert rows[2][7] is None

    csv_text = build_csv({"results": results})
    assert '"Estimated non-default complement (1 - PD)"' in csv_text
    assert '"0.876544"' in csv_text

    workbook = openpyxl.load_workbook(io.BytesIO(build_xlsx({"results": results})))
    worksheet = workbook["Predictions"]
    assert worksheet["H1"].value == "Estimated non-default complement (1 - PD)"
    assert worksheet["H2"].value == pytest.approx(0.876544)
    assert worksheet["H2"].number_format == "0.00%"
    assert worksheet["H3"].value is None


def test_synthetic_seven_sheet_workbook_inspects_and_scores_eligible_sheets():
    """Exercise independent sheet validation and row provenance with synthetic rows."""
    reordered = list(reversed(COLS))
    missing_value = list(LOW)
    missing_value[4] = None  # AGE is required; do not impute it.
    fixture = workbook_bytes({
        "Portfolio_A": [[*COLS, "borrower_reference"], [*LOW, "synthetic-a"], [*MEDIUM, "synthetic-a"]],
        "Portfolio_B": [[*reordered, "borrower_reference"], [*reversed(LOW), "synthetic-b"]],
        "Portfolio_C": [[*COLS, "borrower_reference"], [*missing_value, "synthetic-c"]],
        "Portfolio_D": [[*COLS, "borrower_reference", "notes"], [*LOW, "synthetic-d", "synthetic metadata"]],
        "Invalid_Sheet": [["LIMIT_BAL", "AGE", "borrower_reference"], [200000, 34, "synthetic-invalid"]],
        "Summary": [["Metric", "Value"], ["Borrowers", 4]],
        "Empty_Sheet": [],
    })

    inspected = inspect_workbook(fixture, "synthetic-seven-sheet.xlsx")
    by_name = {sheet["name"]: sheet for sheet in inspected["sheets"]}
    assert inspected["sheet_count"] == 7
    assert by_name["Portfolio_A"]["status"] == "ready"
    assert by_name["Portfolio_B"]["status"] == "ready"
    assert by_name["Portfolio_C"]["status"] == "ready"
    assert by_name["Portfolio_D"]["status"] == "ready"
    assert by_name["Invalid_Sheet"]["status"] == "needs_mapping"
    assert by_name["Summary"]["status"] == "needs_mapping"
    assert by_name["Empty_Sheet"]["status"] == "blank"

    c_analysis = inspect_workbook(fixture, "synthetic-seven-sheet.xlsx", selected_sheet="Portfolio_C")["analysis"]
    assert c_analysis["validation"]["invalid_rows"] == 1
    assert c_analysis["validation"]["valid_rows"] == 0
    a_analysis = inspect_workbook(fixture, "synthetic-seven-sheet.xlsx", selected_sheet="Portfolio_A")["analysis"]
    assert a_analysis["validation"]["warning_rows"] == 2
    assert all("retained separately" in item["message"] for item in a_analysis["validation"]["warnings"])

    selections = [{"name": name, "mapping": None} for name in ("Portfolio_A", "Portfolio_B", "Portfolio_C", "Portfolio_D")]
    predicted = predict_workbook(fixture, "synthetic-seven-sheet.xlsx", selections)
    assert len(predicted["results"]) == 5
    assert [row["status"] for row in predicted["results"]] == ["success", "success", "success", "error", "success"]
    assert [row["borrower_reference"] for row in predicted["results"]] == [
        "synthetic-a", "synthetic-a", "synthetic-b", "synthetic-c", "synthetic-d",
    ]
    assert [row["sheet_name"] for row in predicted["results"]] == [
        "Portfolio_A", "Portfolio_A", "Portfolio_B", "Portfolio_C", "Portfolio_D",
    ]
    assert [row["source_row"] for row in predicted["results"]] == [2, 3, 2, 2, 2]


def test_export_rejects_unbounded_payloads():
    response = client.post(
        "/v1/research/taiwan/batch/export/csv",
        json={"results": [{} for _ in range(20_001)]},
    )
    assert response.status_code == 400
    assert "too many" in response.json()["error"]["message"].lower()


# ---------------------------------------------------------------------------
# Safety contract preserved
# ---------------------------------------------------------------------------

def test_health_and_score_contract_remain_unchanged():
    assert client.get("/health").json() == {"status": "ok", "scoring": "not_validated"}
    # The production score endpoint must stay disabled even while batch research
    # inference is available.
    response = client.post("/v1/score", json={
        "schema_version": "1.0",
        "observation_start": "2025-01-01",
        "prediction_date": "2025-02-01",
        "transactions": [{
            "transaction_id": "t1",
            "date": "2025-01-01",
            "transaction_type": "credit",
            "amount": 1,
        }],
    })
    assert response.status_code == 200
    assert response.json()["score_status"] == "not_validated"


def test_batch_inspect_is_research_only_model():
    content = workbook_bytes({"Data": [[*COLS], [*LOW]]})
    response = inspect(content, "research.xlsx")
    assert response.status_code == 200
    assert response.json()["model_id"] == "uci_taiwan_xgb"
