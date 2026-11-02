"""Batch workbook parsing, validation, prediction and export helpers.

Design notes
------------
* Parsing is performed with ``header=None`` so duplicate and blank headers are
  preserved instead of silently mangled by pandas.
* Every sheet is analysed independently. Sheets are never concatenated.
* The 23 raw Taiwan fields are the model contract. Extra columns are metadata
  and are never passed to the model.
* Numbers stored as text are coerced with an explicit warning; missing values
  are never imputed.
* Formula cells in .xlsx workbooks are detected and rejected when they are
  required model inputs, because openpyxl may return a stale cached value.
"""

from __future__ import annotations

import io
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from ..inference import get_feature_schema, predict

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_ROWS = 5_000
MAX_SHEETS = 20
MAX_COLUMNS = 200
MAX_CELL_CHARS = 400
MAX_ERRORS_RETURNED = 500
MAX_WARNINGS_RETURNED = 200

MODEL_ID = "uci_taiwan_xgb"
REFERENCE_FIELD = "borrower_reference"
IDENTIFIER_HEADERS = {
    "ID", "CUSTOMER_ID", "CUSTOMERID", "BORROWER_ID", "BORROWERID", "LOAN_ID",
    "NAME", "BORROWER_NAME", "CUSTOMER_NAME", "ACCOUNT_ID", "ACCOUNT_NUMBER",
    "PAN", "EMAIL", "PHONE", "MOBILE",
}


class BatchError(Exception):
    """User-facing batch error with an HTTP status code."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (float, np.floating)) and math.isnan(float(value)):
        return True
    if isinstance(value, str):
        return value.strip() == "" or value.strip().lower() in {"nan", "none", "nat"}
    return False


def _text(value: Any, max_chars: int = MAX_CELL_CHARS) -> str:
    if value is None:
        return ""
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if math.isnan(number):
            return ""
        if number.is_integer():
            return str(int(number))
        return repr(number)
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        return str(int(value))
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value).replace("\x00", "").strip()
    if text.lower() in {"nan", "none", "nat"}:
        return ""
    return text[:max_chars]


def _normalise_header(value: Any) -> str:
    text = _text(value, 200).upper()
    text = re.sub(r"[^A-Z0-9]+", "_", text).strip("_")
    return text


def _is_formula_text(value: Any) -> bool:
    return isinstance(value, str) and value.lstrip().startswith("=")


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def _read_csv(content: bytes) -> pd.DataFrame:
    last_error: Optional[Exception] = None
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return pd.read_csv(
                io.BytesIO(content),
                header=None,
                dtype=object,
                keep_default_na=False,
                sep=None,
                engine="python",
                encoding=encoding,
            )
        except Exception as exc:  # pragma: no cover - error detail captured below
            last_error = exc
    try:
        return pd.read_csv(
            io.BytesIO(content),
            header=None,
            dtype=object,
            keep_default_na=False,
            encoding="utf-8-sig",
        )
    except Exception as exc:  # pragma: no cover
        raise BatchError(f"Could not parse the CSV file: {exc}", 400) from last_error or exc


def _read_excel(content: bytes, ext: str) -> Dict[str, pd.DataFrame]:
    engine = "xlrd" if ext == "xls" else "openpyxl"
    try:
        excel = pd.ExcelFile(io.BytesIO(content), engine=engine)
    except Exception as exc:
        raise BatchError(
            "Could not open the Excel workbook. It may be corrupted, password-protected, "
            f"or not a real .{ext} file. Details: {exc}",
            400,
        ) from exc
    names = list(excel.sheet_names)
    if not names:
        raise BatchError("The workbook does not contain any worksheets.", 400)
    if len(names) > MAX_SHEETS:
        raise BatchError(
            f"The workbook contains {len(names)} worksheets; the maximum is {MAX_SHEETS}.",
            400,
        )
    sheets: Dict[str, pd.DataFrame] = {}
    for name in names:
        try:
            sheets[name] = excel.parse(name, header=None, dtype=object)
        except Exception as exc:
            raise BatchError(f"Worksheet '{name}' could not be read: {exc}", 400) from exc
    return sheets


def _formula_cells(content: bytes, ext: str) -> set[Tuple[str, int, int]]:
    """Return (sheet, excel_row, excel_col) for formula cells in .xlsx files.

    .xls formula detection is not attempted; the limitation is disclosed in the
    validation output and reports.
    """
    if ext != "xlsx":
        return set()
    found: set[Tuple[str, int, int]] = set()
    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=False)
        for worksheet in workbook.worksheets:
            for row in worksheet.iter_rows():
                for cell in row:
                    if isinstance(cell.value, str) and cell.value.lstrip().startswith("="):
                        found.add((worksheet.title, cell.row, cell.column))
        workbook.close()
    except Exception:
        return set()
    return found


def _looks_like_delimited_text(content: bytes) -> bool:
    """Reject binary/corrupt payloads before accepting an Excel-extension fallback."""
    sample = content[:65536]
    if b"\x00" in sample:
        return False
    try:
        text = sample.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = sample.decode("cp1252")
        except UnicodeDecodeError:
            return False
    # A delimited export has at least one real cell separator. Random text or a
    # corrupt binary masquerading as .xlsx should not silently become a sheet.
    return any(separator in text for separator in (",", ";", "\t"))


def read_workbook(content: bytes, filename: str) -> Tuple[str, Dict[str, pd.DataFrame], set]:
    """Read a workbook based on its extension, with a safe cross-format fallback."""
    if len(content) > MAX_UPLOAD_BYTES:
        raise BatchError(
            f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.",
            413,
        )
    if len(content) == 0:
        raise BatchError("The uploaded file is empty.", 400)
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if ext not in {"csv", "xlsx", "xls"}:
        raise BatchError("Unsupported file type. Upload a .csv, .xlsx or .xls file.", 415)

    if ext == "csv":
        try:
            frame = _read_csv(content)
            return "csv", {"CSV": frame}, set()
        except BatchError:
            # A CSV renamed to .xlsx/.xls is the common inverse case; the
            # reverse fallback below handles CSV bytes with an Excel extension.
            pass

    try:
        return ext, _read_excel(content, ext), _formula_cells(content, ext)
    except BatchError as excel_error:
        if ext == "csv":
            raise
        # Some exports are actually delimited text with an Excel extension.
        if _looks_like_delimited_text(content):
            try:
                frame = _read_csv(content)
                return "csv", {filename.rsplit(".", 1)[0] or "Sheet1": frame}, set()
            except Exception:
                pass
        raise excel_error


# ---------------------------------------------------------------------------
# Sheet preparation and mapping
# ---------------------------------------------------------------------------

def _prepare_sheet(name: str, raw: pd.DataFrame) -> Dict[str, Any]:
    if raw is None or raw.empty or raw.shape[1] == 0:
        return {
            "name": name,
            "blank": True,
            "headers": [],
            "rows": [],
            "row_numbers": [],
            "blank_rows_ignored": 0,
            "header_row": None,
            "column_count": 0,
            "row_count": 0,
        }

    # Drop columns that are entirely empty (common trailing Excel columns).
    keep_columns: List[int] = []
    for col in raw.columns:
        column = raw[col]
        if any(not _is_blank(value) for value in column.tolist()):
            keep_columns.append(col)
    if not keep_columns:
        return {
            "name": name,
            "blank": True,
            "headers": [],
            "rows": [],
            "row_numbers": [],
            "blank_rows_ignored": 0,
            "header_row": None,
            "column_count": 0,
            "row_count": 0,
        }
    frame = raw[keep_columns]
    column_positions: List[int] = []
    for position, column in enumerate(keep_columns):
        try:
            column_positions.append(int(column) + 1)
        except Exception:
            column_positions.append(position + 1)

    if frame.shape[1] > MAX_COLUMNS:
        raise BatchError(
            f"Worksheet '{name}' has {frame.shape[1]} columns; the maximum is {MAX_COLUMNS}.",
            400,
        )

    # First non-blank row is the header row. Leading blank rows are preserved in
    # the source row numbering so users can locate the data in Excel.
    header_position: Optional[int] = None
    for position in range(len(frame)):
        row_values = frame.iloc[position].tolist()
        if any(not _is_blank(value) for value in row_values):
            header_position = position
            break
    if header_position is None:
        return {
            "name": name,
            "blank": True,
            "headers": [],
            "rows": [],
            "row_numbers": [],
            "blank_rows_ignored": 0,
            "header_row": None,
            "column_count": 0,
            "row_count": 0,
        }

    header_values = frame.iloc[header_position].tolist()
    headers: List[str] = []
    for index, value in enumerate(header_values):
        text = _text(value, 200)
        headers.append(text if text else f"Column {index + 1}")

    data_frame = frame.iloc[header_position + 1:]
    rows: List[List[Any]] = []
    row_numbers: List[int] = []
    blank_rows_ignored = 0
    for index, row in data_frame.iterrows():
        values = row.tolist()
        if all(_is_blank(value) for value in values):
            blank_rows_ignored += 1
            continue
        # Pandas index is zero-based; Excel rows are one-based.
        row_numbers.append(int(index) + 1 if isinstance(index, (int, np.integer)) else len(row_numbers) + header_position + 2)
        rows.append(values)

    if len(rows) > MAX_ROWS:
        raise BatchError(
            f"Worksheet '{name}' contains {len(rows)} data rows; the maximum is {MAX_ROWS}.",
            400,
        )

    return {
        "name": name,
        "blank": False,
        "headers": headers,
        "rows": rows,
        "row_numbers": row_numbers,
        "blank_rows_ignored": blank_rows_ignored,
        "header_row": header_position + 1,
        "column_count": len(headers),
        "row_count": len(rows),
        "column_positions": column_positions,
    }


def _duplicate_report(headers: Sequence[str]) -> Tuple[List[dict], List[int]]:
    normalised = [_normalise_header(header) for header in headers]
    exact_counts = Counter(str(header).strip() for header in headers)
    norm_counts = Counter(normalised)
    duplicates: List[dict] = []
    seen: set[str] = set()
    for index, header in enumerate(headers):
        key = _normalise_header(header)
        exact_key = str(header).strip()
        if norm_counts[key] > 1 and key not in seen:
            seen.add(key)
            duplicates.append({
                "name": _text(header, 200),
                "normalized": key,
                "count": norm_counts[key],
                "indices": [i for i, value in enumerate(normalised) if value == key],
                "kind": "exact" if exact_counts[exact_key] > 1 else "normalized",
            })
    ambiguous = sorted({i for i, key in enumerate(normalised) if norm_counts[key] > 1})
    return duplicates, ambiguous


def _auto_mapping(headers: Sequence[str], schema: Dict[str, Any]) -> Dict[int, str]:
    raw_features = schema.get("raw_features", {})
    canonical = {_normalise_header(name): name for name in raw_features}
    canonical[_normalise_header(REFERENCE_FIELD)] = REFERENCE_FIELD
    counts = Counter(_normalise_header(header) for header in headers)
    mapping: Dict[int, str] = {}
    for index, header in enumerate(headers):
        key = _normalise_header(header)
        if key in canonical and counts[key] == 1:
            mapping[index] = canonical[key]
    return mapping


def _resolve_mapping(
    headers: Sequence[str],
    supplied: Optional[Dict[str, Any]],
    schema: Dict[str, Any],
) -> Tuple[Dict[int, str], List[str]]:
    """Merge automatic and explicit mappings. Explicit intent wins."""
    auto = _auto_mapping(headers, schema)
    errors: List[str] = []
    if supplied is None:
        return auto, errors

    raw_features = schema.get("raw_features", {})
    allowed = set(raw_features.keys()) | {REFERENCE_FIELD}
    mapping: Dict[int, str] = {}
    used_targets: Dict[str, int] = {}

    # Build a name -> unique index lookup for clients that send header names.
    name_lookup: Dict[str, List[int]] = {}
    for index, header in enumerate(headers):
        name_lookup.setdefault(str(header).strip(), []).append(index)

    for key, target in supplied.items():
        key_text = str(key)
        if key_text.isdigit() and int(key_text) < len(headers):
            index = int(key_text)
        elif key_text in name_lookup and len(name_lookup[key_text]) == 1:
            index = name_lookup[key_text][0]
        else:
            errors.append(f"Unknown source column '{key_text}'.")
            continue
        target_text = "" if target is None else str(target).strip()
        if target_text in {"", "ignore", "metadata", "none"}:
            continue
        if target_text not in allowed:
            errors.append(f"Unknown model feature '{target_text}'.")
            continue
        if target_text in used_targets and used_targets[target_text] != index:
            errors.append(
                f"Feature '{target_text}' is mapped to more than one column "
                f"('{_text(headers[used_targets[target_text]], 80)}' and '{_text(headers[index], 80)}')."
            )
            continue
        used_targets[target_text] = index
        mapping[index] = target_text
    return mapping, errors


def _coerce(value: Any, field_schema: Dict[str, Any], formula: bool, field_name: str = "", warn_text: bool = True) -> Tuple[Any, Optional[str]]:
    """Coerce a raw spreadsheet cell to a model value without imputing."""
    target_label = field_name or field_schema.get("description", "value")
    if formula:
        raise ValueError(
            f"{target_label}: the cell contains a formula. Save the calculated value "
            "as a number or remove the formula; formulas are not trusted."
        )
    if _is_blank(value):
        raise ValueError(f"{target_label}: missing required value.")

    field_type = field_schema.get("type", "numeric")
    warning: Optional[str] = None
    number: float
    if isinstance(value, bool):
        raise ValueError(f"{target_label}: expected a number, not a boolean.")
    if isinstance(value, (int, float, np.integer, np.floating)):
        number = float(value)
    else:
        text = str(value).strip()
        cleaned = text.replace(",", "").replace(" ", "")
        try:
            number = float(cleaned)
            warning = "Number was stored as text and was converted." if warn_text else None
        except Exception as exc:
            raise ValueError(f"{target_label}: expected a number.") from exc

    if not math.isfinite(number):
        raise ValueError(f"{target_label}: expected a finite number.")

    if field_type == "categorical":
        if not number.is_integer():
            raise ValueError(f"{target_label}: expected a whole-number category code.")
        number = int(number)
        allowed = field_schema.get("values")
        if allowed and number not in allowed:
            raise ValueError(f"{target_label}: value is not one of the allowed category codes.")
    else:
        value_range = field_schema.get("range")
        if value_range:
            minimum, maximum = value_range
            if not (minimum <= number <= maximum):
                raise ValueError(f"{target_label}: value is outside the allowed range {minimum} to {maximum}.")

    return number, warning


def _analyse_rows(
    sheet: Dict[str, Any],
    schema: Dict[str, Any],
    mapping: Dict[int, str],
    formulas: set[Tuple[str, int, int]],
    warn_text_numbers: bool = True,
) -> Dict[str, Any]:
    raw_features = schema.get("raw_features", {})
    required = [name for name, field in raw_features.items() if field.get("required", False)]
    mapped_targets = set(mapping.values())
    missing = [name for name in required if name not in mapped_targets]
    mapping_errors = sheet.get("mapping_errors", [])

    # If the required schema is incomplete, row-level counts would be misleading.
    if missing or mapping_errors:
        return {
            "total_rows": sheet["row_count"],
            "valid_rows": 0,
            "invalid_rows": 0,
            "warning_rows": 0,
            "errors": [],
            "warnings": [],
            "status": "needs_mapping",
            "usable": False,
            "missing_fields": missing,
            "mapping_errors": mapping_errors,
        }

    errors: List[dict] = []
    warnings: List[dict] = []
    valid_rows = 0
    invalid_rows = 0
    warning_rows = 0
    sheet_name = sheet["name"]
    reference_index = next((index for index, target in mapping.items() if target == REFERENCE_FIELD), None)
    duplicate_references: set[str] = set()
    if reference_index is not None:
        reference_values = [
            _text(row[reference_index], 200).strip()
            for row in sheet["rows"]
            if reference_index < len(row) and _text(row[reference_index], 200).strip()
        ]
        duplicate_references = {value for value, count in Counter(reference_values).items() if count > 1}

    for position, row in enumerate(sheet["rows"]):
        source_row = sheet["row_numbers"][position]
        row_errors: List[dict] = []
        row_warnings: List[dict] = []
        for index, target in mapping.items():
            if target == REFERENCE_FIELD:
                reference = _text(row[index], 200).strip() if index < len(row) else ""
                if reference and reference in duplicate_references:
                    row_warnings.append({
                        "source_row": source_row,
                        "column": REFERENCE_FIELD,
                        "source_column": sheet["headers"][index],
                        "message": "Borrower reference appears on multiple rows in this worksheet; rows are retained separately.",
                    })
                continue
            field_schema = raw_features[target]
            header = sheet["headers"][index]
            source_column = sheet.get("column_positions", [])[index] if index < len(sheet.get("column_positions", [])) else index + 1
            is_formula = _is_formula_text(row[index]) or (sheet_name, source_row, source_column) in formulas
            try:
                _, warning = _coerce(row[index], field_schema, is_formula, target, warn_text=warn_text_numbers)
            except ValueError as exc:
                row_errors.append({
                    "source_row": source_row,
                    "column": target,
                    "source_column": header,
                    "message": str(exc),
                })
                continue
            if warning:
                row_warnings.append({
                    "source_row": source_row,
                    "column": target,
                    "source_column": header,
                    "message": warning,
                })
        if row_errors:
            invalid_rows += 1
            if len(errors) < MAX_ERRORS_RETURNED:
                errors.extend(row_errors[: max(1, MAX_ERRORS_RETURNED - len(errors))])
        else:
            valid_rows += 1
        if row_warnings:
            warning_rows += 1
            if len(warnings) < MAX_WARNINGS_RETURNED:
                warnings.extend(row_warnings[: max(1, MAX_WARNINGS_RETURNED - len(warnings))])

    total = sheet["row_count"]
    status = "ready" if total > 0 else "empty"
    return {
        "total_rows": total,
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows,
        "warning_rows": warning_rows,
        "errors": errors,
        "warnings": warnings,
        "status": status,
        "usable": total > 0 and valid_rows > 0,
        "missing_fields": [],
        "mapping_errors": [],
        "truncated_errors": invalid_rows > 0 and len(errors) >= MAX_ERRORS_RETURNED,
    }


def _sheet_summary(prepared: Dict[str, Any], schema: Dict[str, Any], formulas: set) -> Dict[str, Any]:
    if prepared["blank"]:
        return {
            "name": prepared["name"],
            "blank": True,
            "row_count": 0,
            "column_count": 0,
            "headers": [],
            "duplicate_headers": [],
            "missing_fields": [name for name, field in schema["raw_features"].items() if field.get("required")],
            "auto_mapping": {},
            "status": "blank",
            "note": "Worksheet is blank.",
        }
    auto_mapping, auto_errors = _resolve_mapping(prepared["headers"], None, schema)
    required = [name for name, field in schema["raw_features"].items() if field.get("required", False)]
    missing = [name for name in required if name not in set(auto_mapping.values())]
    duplicates, _ = _duplicate_report(prepared["headers"])
    return {
        "name": prepared["name"],
        "blank": False,
        "row_count": prepared["row_count"],
        "column_count": prepared["column_count"],
        "header_row": prepared["header_row"],
        "headers": [_text(header, 120) for header in prepared["headers"]],
        "duplicate_headers": duplicates,
        "missing_fields": missing,
        "auto_mapping": {str(key): value for key, value in auto_mapping.items()},
        "status": "ready" if not missing else "needs_mapping",
        "mapping_errors": auto_errors,
        "blank_rows_ignored": prepared["blank_rows_ignored"],
    }


def _analysis_payload(
    prepared: Dict[str, Any],
    schema: Dict[str, Any],
    supplied_mapping: Optional[Dict[str, Any]],
    formulas: set,
    warn_text_numbers: bool = True,
) -> Dict[str, Any]:
    mapping: Dict[int, str] = {}
    mapping_errors: List[str] = []
    if not prepared["blank"]:
        mapping, mapping_errors = _resolve_mapping(prepared["headers"], supplied_mapping, schema)
    prepared = dict(prepared)
    prepared["mapping_errors"] = mapping_errors
    duplicates, ambiguous = _duplicate_report(prepared["headers"]) if not prepared["blank"] else ([], [])
    required = [name for name, field in schema["raw_features"].items() if field.get("required", False)]
    mapped_targets = set(mapping.values())
    missing = [name for name in required if name not in mapped_targets]
    extra = [
        {"index": index, "name": _text(header, 200)}
        for index, header in enumerate(prepared["headers"])
        if index not in mapping
    ]
    identifiers = [item for item in extra if _normalise_header(item["name"]) in IDENTIFIER_HEADERS]
    validation = _analyse_rows(prepared, schema, mapping, formulas, warn_text_numbers) if not prepared["blank"] else {
        "total_rows": 0, "valid_rows": 0, "invalid_rows": 0, "warning_rows": 0,
        "errors": [], "warnings": [], "status": "blank", "usable": False,
        "missing_fields": required, "mapping_errors": [],
    }
    status = validation["status"]
    if not prepared["blank"] and missing:
        status = "needs_mapping"
    elif not prepared["blank"] and validation["usable"]:
        status = "ready_with_errors" if validation["invalid_rows"] else "ready"

    preview_rows = [
        [_text(value) for value in row]
        for row in prepared["rows"][:MAX_ROWS]
    ]
    return {
        "name": prepared["name"],
        "blank": prepared["blank"],
        "header_row": prepared["header_row"],
        "row_count": prepared["row_count"],
        "column_count": prepared["column_count"],
        "blank_rows_ignored": prepared["blank_rows_ignored"],
        "headers": [_text(header, 200) for header in prepared["headers"]],
        "rows": preview_rows,
        "row_numbers": prepared["row_numbers"],
        "duplicate_headers": duplicates,
        "ambiguous_columns": ambiguous,
        "mapping": {str(key): value for key, value in mapping.items()},
        "auto_mapping": {str(key): value for key, value in _resolve_mapping(prepared["headers"], None, schema)[0].items()},
        "missing_fields": missing,
        "mapping_errors": mapping_errors,
        "extra_columns": extra,
        "identifier_columns": identifiers,
        "validation": validation,
        "status": status,
        "usable": bool(validation.get("usable")) and not missing and not mapping_errors,
        "required_fields": required,
        "formula_detection": "xlsx" if formulas else "unavailable",
    }


# ---------------------------------------------------------------------------
# Public inspection / prediction
# ---------------------------------------------------------------------------

def inspect_workbook(
    content: bytes,
    filename: str,
    selected_sheet: Optional[str] = None,
    mapping: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    file_format, sheets, formulas = read_workbook(content, filename)
    schema = get_feature_schema(MODEL_ID)
    prepared = {name: _prepare_sheet(name, frame) for name, frame in sheets.items()}
    summaries = [_sheet_summary(prepared[name], schema, formulas) for name in sheets]

    non_blank = [name for name in sheets if not prepared[name]["blank"]]
    chosen = selected_sheet if selected_sheet in sheets else (non_blank[0] if non_blank else next(iter(sheets)))
    analysis = _analysis_payload(prepared[chosen], schema, mapping, formulas, warn_text_numbers=file_format != "csv")

    all_usable = all(
        summary["status"] == "ready" for summary in summaries if not summary.get("blank")
    )
    return {
        "file_name": filename,
        "file_format": file_format,
        "file_size_bytes": len(content),
        "sheet_count": len(sheets),
        "sheets": summaries,
        "selected_sheet": chosen,
        "analysis": analysis,
        "limits": {
            "max_bytes": MAX_UPLOAD_BYTES,
            "max_rows_per_sheet": MAX_ROWS,
            "max_sheets": MAX_SHEETS,
            "max_columns": MAX_COLUMNS,
        },
        "multi_sheet_compatible": all_usable,
        "model_id": MODEL_ID,
    }


def predict_workbook(
    content: bytes,
    filename: str,
    selections: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    file_format, sheets, formulas = read_workbook(content, filename)
    schema = get_feature_schema(MODEL_ID)
    prepared = {name: _prepare_sheet(name, frame) for name, frame in sheets.items()}
    required = [name for name, field in schema["raw_features"].items() if field.get("required", False)]

    if not selections:
        first = next((name for name in sheets if not prepared[name]["blank"]), None)
        if first is None:
            raise BatchError("The workbook does not contain any non-empty worksheet.", 400)
        selections = [{"name": first, "mapping": None}]

    results: List[dict] = []
    sheet_summaries: List[dict] = []
    for selection in selections:
        name = str(selection.get("name", ""))
        if name not in sheets:
            raise BatchError(f"Worksheet '{name}' was not found in the workbook.", 422)
        if prepared[name]["blank"]:
            raise BatchError(f"Worksheet '{name}' is blank and cannot be scored.", 422)
        mapping, mapping_errors = _resolve_mapping(
            prepared[name]["headers"], selection.get("mapping"), schema
        )
        mapped_targets = set(mapping.values())
        missing = [field for field in required if field not in mapped_targets]
        if mapping_errors:
            raise BatchError("Invalid column mapping: " + " ".join(mapping_errors), 422)
        if missing:
            raise BatchError(
                f"Worksheet '{name}' is missing required model features: {', '.join(missing)}.",
                422,
            )

        scored = 0
        failed = 0
        for position, row in enumerate(prepared[name]["rows"]):
            source_row = prepared[name]["row_numbers"][position]
            raw_features: Dict[str, Any] = {}
            borrower_reference = None
            row_error: Optional[str] = None
            # Capture the reference first so failed rows remain identifiable in
            # the results and exports, even when validation stops at an earlier
            # feature column.
            for index, target in mapping.items():
                if target == REFERENCE_FIELD:
                    borrower_reference = _text(row[index], 200) or None
                    break
            for index, target in mapping.items():
                if target == REFERENCE_FIELD:
                    continue
                field_schema = schema["raw_features"][target]
                source_column = prepared[name].get("column_positions", [])[index] if index < len(prepared[name].get("column_positions", [])) else index + 1
                is_formula = _is_formula_text(row[index]) or (name, source_row, source_column) in formulas
                try:
                    value, _ = _coerce(row[index], field_schema, is_formula, target)
                    raw_features[target] = value
                except ValueError as exc:
                    row_error = str(exc)
                    break
            if row_error is None:
                try:
                    prediction = predict(MODEL_ID, raw_features, include_explanations=True)
                    results.append({
                        "result_index": len(results) + 1,
                        "sheet_name": name,
                        "source_row": source_row,
                        "row_index": position + 1,
                        "borrower_reference": borrower_reference,
                        "status": "success",
                        "prediction": {
                            "model_id": prediction.model_id,
                            "probability": prediction.probability,
                            "predicted_class": prediction.predicted_class,
                            "risk_category": prediction.risk_category,
                            "calibrated": prediction.calibrated,
                            "threshold": prediction.threshold,
                            "calibration_method": prediction.calibration_method,
                            "dataset_id": prediction.dataset_id,
                            "dataset_name": prediction.dataset_name,
                            "geography": prediction.geography,
                            "target_meaning": prediction.target_meaning,
                            "feature_contributions": [item.model_dump() for item in (prediction.feature_contributions or [])],
                            "explanation_available": bool(prediction.feature_contributions),
                        },
                        "submitted_features": raw_features,
                    })
                    scored += 1
                except Exception as exc:
                    row_error = str(exc) or "Prediction failed."
            if row_error is not None:
                results.append({
                    "result_index": len(results) + 1,
                    "sheet_name": name,
                    "source_row": source_row,
                    "row_index": position + 1,
                    "borrower_reference": borrower_reference,
                    "status": "error",
                    "error_message": row_error,
                })
                failed += 1

        sheet_summaries.append({
            "name": name,
            "total_rows": prepared[name]["row_count"],
            "scored": scored,
            "failed": failed,
            "blank_rows_ignored": prepared[name]["blank_rows_ignored"],
        })

    calibration_model_path = "models/calibration_model.joblib"
    return {
        "model_id": MODEL_ID,
        "file_name": filename,
        "file_format": file_format,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "thresholds": {
            "classification": 0.5,
            "low_upper": 0.25,
            "medium_upper": 0.5,
        },
        "calibrated": all(
            item.get("prediction", {}).get("calibrated", False)
            for item in results if item["status"] == "success"
        ) if any(item["status"] == "success" for item in results) else False,
        "calibration_method": "Platt scaling (sigmoid)" if any(
            item.get("prediction", {}).get("calibrated", False)
            for item in results if item["status"] == "success"
        ) else None,
        "sheets": sheet_summaries,
        "results": results,
        "calibration_artifact": calibration_model_path,
    }


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def _excel_safe(value: Any) -> Any:
    if isinstance(value, str):
        text = value.replace("\x00", "")
        if text.startswith(("=", "+", "-", "@", "\t", "\r")):
            return "'" + text
        return text
    return value


def build_export_rows(results: Sequence[Dict[str, Any]]) -> List[List[Any]]:
    rows: List[List[Any]] = []
    for item in results:
        prediction = item.get("prediction") or {}
        probability = prediction.get("probability")
        non_default_complement = (
            1.0 - float(probability)
            if isinstance(probability, (int, float))
            and not isinstance(probability, bool)
            and math.isfinite(float(probability))
            and 0.0 <= float(probability) <= 1.0
            else None
        )
        threshold = prediction.get("threshold")
        classification = None
        comparison = None
        if (isinstance(probability, (int, float)) and math.isfinite(float(probability))
                and isinstance(threshold, (int, float)) and math.isfinite(float(threshold))):
            comparison = "<" if float(probability) < float(threshold) else ">="
            classification = "Lower predicted-default-risk class" if comparison == "<" else "Higher predicted-default-risk class"
        contributions = prediction.get("feature_contributions") or []
        def drivers(direction: str) -> str:
            return "; ".join(
                f"{str(item.get('feature', '')).replace('_', ' ')} ({float(item.get('contribution', 0.0)):.4f} model-output units)"
                for item in contributions if item.get("direction") == direction
            )
        explanation = (
            f"Estimated PD {float(probability) * 100:.2f}% {comparison} research threshold {float(threshold) * 100:.2f}%; "
            f"research classification: {classification}. Complement is arithmetic only, not a repayment guarantee. "
            "Research only; not a lending decision."
            if classification and comparison else None
        )
        rows.append([
            item.get("result_index"),
            item.get("sheet_name"),
            item.get("source_row"),
            item.get("row_index"),
            item.get("borrower_reference"),
            "Scored" if item.get("status") == "success" else "Failed",
            probability,
            non_default_complement,
            prediction.get("risk_category"),
            prediction.get("predicted_class"),
            prediction.get("calibrated"),
            prediction.get("model_id"),
            item.get("error_message"),
            classification,
            f"{float(probability):.4f} {comparison} {float(threshold):.4f}" if comparison else None,
            drivers("increases_risk") or ("Attribution unavailable" if item.get("status") == "success" else None),
            drivers("decreases_risk") or ("Attribution unavailable" if item.get("status") == "success" else None),
            f"{prediction.get('dataset_name', 'Default of Credit Card Clients')} ({prediction.get('geography', 'Taiwan')}); {prediction.get('calibration_method') or 'not calibrated'}" if item.get("status") == "success" else None,
            "Research only; not validated for Indian borrowers or lending" if item.get("status") == "success" else None,
            explanation,
        ])
    return rows


EXPORT_HEADERS = [
    "Result #", "Sheet", "Source row", "Sheet row", "Borrower reference",
    "Status", "Estimated default probability", "Estimated non-default complement (1 - PD)", "Risk category",
    "Predicted class", "Calibrated", "Model ID", "Validation / error message",
    "Research classification", "Threshold comparison", "Risk-increasing model drivers", "Risk-decreasing model drivers",
    "Model and dataset context", "Limitation status", "Plain-language explanation",
]


def _csv_cell(value: Any) -> str:
    safe = _excel_safe(value)
    text = "" if safe is None else str(safe)
    return '"' + text.replace('"', '""') + '"'


def build_csv(payload: Dict[str, Any]) -> str:
    """Build a formula-injection-safe predictions CSV."""
    results = payload.get("results") or []
    lines = [",".join(_csv_cell(header) for header in EXPORT_HEADERS)]
    for row in build_export_rows(results):
        cells: List[str] = []
        for index, value in enumerate(row):
            if index in {6, 7} and isinstance(value, (int, float)):
                cells.append(_csv_cell(f"{float(value):.6f}"))
            else:
                cells.append(_csv_cell(value))
        lines.append(",".join(cells))
    return "\r\n".join(lines) + "\r\n"


def build_xlsx(payload: Dict[str, Any]) -> bytes:
    """Build a formula-injection-safe predictions workbook with a summary sheet."""
    results = payload.get("results") or []
    summary = payload.get("summary") or {}
    metadata = payload.get("metadata") or {}

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Predictions"
    header_fill = PatternFill("solid", fgColor="1F4E5A")
    header_font = Font(color="FFFFFF", bold=True)
    for column, header in enumerate(EXPORT_HEADERS, start=1):
        cell = worksheet.cell(row=1, column=column, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    for row_index, row in enumerate(build_export_rows(results), start=2):
        for column, value in enumerate(row, start=1):
            safe = _excel_safe(value)
            cell = worksheet.cell(row=row_index, column=column, value=safe)
            if column in {7, 8} and isinstance(value, (int, float)):
                cell.number_format = "0.00%"
            if column == 2:
                cell.alignment = Alignment(horizontal="left")
    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions
    widths = [9, 18, 12, 10, 22, 11, 16, 25, 14, 24, 11, 20, 60, 34, 24, 48, 48, 42, 48, 70]
    for index, width in enumerate(widths, start=1):
        worksheet.column_dimensions[get_column_letter(index)].width = width

    summary_sheet = workbook.create_sheet("Summary")
    summary_rows: List[Tuple[str, Any]] = [
        ("CreditAI batch analysis", ""),
        ("Research status", "RESEARCH ONLY — Taiwan UCI benchmark; not validated for Indian underwriting"),
        ("File", metadata.get("file_name", "")),
        ("Worksheets", ", ".join(metadata.get("sheet_names", []) or [])),
        ("Generated at", metadata.get("generated_at", datetime.now(timezone.utc).isoformat())),
        ("Model ID", metadata.get("model_id", MODEL_ID)),
        ("Calibration", metadata.get("calibration_method") or "Not calibrated"),
        ("", ""),
        ("Total rows submitted", summary.get("total", 0)),
        ("Successfully scored", summary.get("succeeded", 0)),
        ("Failed / rejected", summary.get("failed", 0)),
        ("Mean estimated PD (scored rows)", summary.get("meanProbability")),
        ("Median estimated PD (scored rows)", summary.get("medianProbability")),
        ("Low risk (<25%)", summary.get("lowRisk", 0)),
        ("Medium risk (25% to <50%)", summary.get("mediumRisk", 0)),
        ("High risk (>=50%)", summary.get("highRisk", 0)),
        ("", ""),
        ("Probability band", "Borrowers"),
    ]
    for item in summary.get("histogram", []) or []:
        summary_rows.append((item.get("label", ""), item.get("count", 0)))
    summary_rows.extend([
        ("", ""),
        ("Limitation", "Predicted probabilities are model estimates, not observed defaults. Without outcome labels, actual default rates, losses, accuracy and portfolio performance cannot be computed from this batch."),
        ("Limitation", "The non-default complement (1 - PD) is a mathematical complement, not evidence or a guarantee of repayment."),
        ("Limitation", "Taiwan credit-card data (April–September 2005). Not validated for Indian borrowers or production lending decisions."),
    ])
    for row_index, (label, value) in enumerate(summary_rows, start=1):
        label_cell = summary_sheet.cell(row=row_index, column=1, value=_excel_safe(label))
        label_cell.font = Font(bold=row_index == 1 or row_index == 9)
        value_cell = _excel_safe(value)
        if isinstance(value, float) and label.startswith(("Mean", "Median")):
            cell = summary_sheet.cell(row=row_index, column=2, value=value)
            cell.number_format = "0.00%"
        else:
            summary_sheet.cell(row=row_index, column=2, value=value_cell)
    summary_sheet.column_dimensions["A"].width = 44
    summary_sheet.column_dimensions["B"].width = 90

    stream = io.BytesIO()
    workbook.save(stream)
    return stream.getvalue()
