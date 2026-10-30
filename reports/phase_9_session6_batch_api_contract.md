# Phase 9 — Session 6: Batch API Contract

**Date:** 2026-10-22
**Base URL:** `http://127.0.0.1:8000`
**Implementation:** `src/api/app.py` (HTTP layer) and `src/api/batch_service.py` (parsing, validation, prediction, export)
**Status:** research-only Taiwan benchmark inference. Not an Indian production score.

---

## 1. Scope and model

All batch endpoints operate on the registered research model `uci_taiwan_xgb` (dataset `DS003`, Taiwan credit-card default, next-month target). The model is loaded from `models/creditai_model.joblib`; calibration is loaded from `models/calibration_model.joblib`.

The batch API never falls back to a different model, never calls `/v1/score`, and never emits a synthetic or example prediction. A row is either scored by the model or returned with `status: "error"` and an `error_message`.

---

## 2. Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/research/taiwan/batch/inspect` | Parse a workbook, list worksheets, inspect one sheet, validate rows |
| `POST` | `/v1/research/taiwan/batch/analyze` | Re-validate one sheet after an explicit mapping change |
| `POST` | `/v1/research/taiwan/batch-predict` | Score one or more selected worksheets |
| `POST` | `/v1/research/taiwan/batch/export/xlsx` | Build a two-sheet Excel export from supplied results |
| `POST` | `/v1/research/taiwan/batch/export/csv` | Build a CSV export from supplied results |

The UI downloads predictions CSV locally from the same response, but the backend CSV endpoint exists and is contract-tested.

---

## 3. Upload endpoints

### 3.1 `POST /v1/research/taiwan/batch/inspect`

`multipart/form-data`:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `file` | file | yes | `.csv`, `.xlsx` or `.xls` upload |
| `sheet` | text | no | Worksheet name to inspect; defaults to the first non-empty sheet |
| `mapping` | JSON string | no | Explicit `{column_index: target}` object; omit for automatic mapping |

### 3.2 `POST /v1/research/taiwan/batch/analyze`

Same multipart shape, but `sheet` and `mapping` are required. This endpoint exists so the UI can re-run validation after a user changes the mapping, without re-uploading logic differences.

`mapping` must be a JSON **object**, for example:

```json
{
  "0": "LIMIT_BAL",
  "1": "SEX",
  "2": "EDUCATION",
  "23": "borrower_reference",
  "24": "ignore"
}
```

- Keys are zero-based column indices as strings.
- Values are one of the 23 required feature names, `borrower_reference`, `ignore`, `metadata`, `none`, or an empty string.
- A target may be assigned only once. Duplicate assignments are rejected rather than resolved by guessing.
- `borrower_reference` is metadata; it is never sent to the model.
- Invalid JSON → `422` “The column mapping is not valid JSON.”
- Non-object JSON → `422` “The column mapping must be a JSON object.”

### 3.3 `POST /v1/research/taiwan/batch-predict`

`multipart/form-data`:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `file` | file | yes | Same workbook bytes |
| `sheets` | JSON string | no | Array of `{"name": "...", "mapping": {...}}` |

Example:

```json
[
  {
    "name": "Portfolio A",
    "mapping": {"0": "LIMIT_BAL", "1": "SEX", "2": "EDUCATION"}
  },
  {
    "name": "Portfolio B",
    "mapping": {"0": "LIMIT_BAL", "1": "SEX", "2": "EDUCATION"}
  }
]
```

- When `sheets` is omitted or empty, the first non-empty worksheet is scored with automatic header matching. This is retained for backward compatibility; the UI always sends an explicit selection.
- Invalid JSON → `422` “The sheet selection is not valid JSON.”
- Non-array JSON → `422` “The sheet selection must be a JSON array.”
- Unknown or blank sheet name → `400` with a precise message.
- Incomplete mapping → `400` / `422` with the missing fields; rows are not imputed.

---

## 4. Limits

| Limit | Value | Enforcement |
|---|---:|---|
| Upload size | 10 MiB (`10 * 1024 * 1024`) | `413` before parsing |
| Rows per worksheet | 5,000 | `400` after parsing |
| Worksheets per workbook | 20 | `400` |
| Columns per worksheet | 200 | `400` |
| Cell characters returned | 400 | Truncated in responses |
| Validation errors returned | 500 | `truncated_errors: true` when reached |
| Warnings returned | 200 | Capped |
| Export result rows | 20,000 | `400` “Too many result rows to export.” |

`inspect` echoes the active limits:

```json
"limits": {
  "max_bytes": 10485760,
  "max_rows_per_sheet": 5000,
  "max_sheets": 20,
  "max_columns": 200
}
```

---

## 5. Accepted files and parsing rules

| Input | Behaviour |
|---|---|
| `.csv` | UTF-8 with optional BOM; comma delimiter; quoted fields supported |
| `.xlsx` | `openpyxl`; all worksheets enumerated |
| `.xls` | `xlrd` code path exists but is **not exercised** by the session-6 tests |
| CSV bytes named `.xlsx` | Detected as delimited text and parsed as CSV; response reports `file_format: "csv"` |
| Empty file | `400` “The uploaded file is empty.” |
| Corrupt/non-zip `.xlsx` | `400` explicit corruption message |
| Unsupported extension | `415` “Unsupported file type. Upload a .csv, .xlsx or .xls file.” |

Header matching normalises BOM, surrounding whitespace, case and separators. A normalised match is accepted only when it is unique. Duplicate or ambiguous source columns are reported; they are never silently merged.

Header row detection tolerates a small preamble: the parser scans for the first row that looks like a header and reports `header_row` (1-based). Blank rows are skipped and do not shift `source_row`.

---

## 6. Response: inspect

Top-level fields:

| Field | Type | Meaning |
|---|---|---|
| `file_name` | string | Uploaded filename |
| `file_format` | `"csv"` \| `"xlsx"` \| `"xls"` | Detected format, which may differ from the extension |
| `file_size_bytes` | integer | Size of received bytes |
| `sheet_count` | integer | Number of worksheets |
| `sheets` | array | Compact summary of every worksheet |
| `selected_sheet` | string | Sheet actually analysed |
| `analysis` | object | Full preview/validation for the selected sheet |
| `limits` | object | Active limits (section 4) |
| `multi_sheet_compatible` | boolean | True when every non-blank sheet is usable |
| `model_id` | string | Always `uci_taiwan_xgb` |

### 6.1 `sheets[]` summary

```json
{
  "name": "Portfolio A",
  "blank": false,
  "row_count": 3,
  "column_count": 25,
  "header_row": 1,
  "headers": ["LIMIT_BAL", "SEX", "..."],
  "duplicate_headers": [],
  "missing_fields": [],
  "auto_mapping": {"0": "LIMIT_BAL", "1": "SEX"},
  "status": "ready",
  "mapping_errors": [],
  "blank_rows_ignored": 0
}
```

`status` is `ready`, `needs_mapping`, `blank`, or `empty`.

### 6.2 `analysis`

| Field | Type | Meaning |
|---|---|---|
| `name` | string | Sheet name |
| `blank` | boolean | Sheet has no data |
| `header_row` | integer \| null | 1-based source row used as header |
| `row_count` | integer | Data rows after blank-row removal |
| `column_count` | integer | Source columns |
| `blank_rows_ignored` | integer | Rows skipped as blank |
| `headers` | string[] | Source header labels (truncated to 200 chars) |
| `rows` | array[] | Preview rows, at most 5,000, values typed/truncated |
| `row_numbers` | integer[] | Original 1-based source rows for the preview |
| `duplicate_headers` | object[] | Duplicate/ambiguous header report with indices |
| `ambiguous_columns` | array | Columns whose automatic match was not unique |
| `mapping` | object | Effective `{index: target}` mapping |
| `auto_mapping` | object | Mapping that automatic matching would choose |
| `missing_fields` | string[] | Required features not mapped |
| `mapping_errors` | string[] | Mapping-specific problems |
| `extra_columns` | object[] | Source columns outside the model contract, e.g. `notes` |
| `identifier_columns` | object[] | Recognised reference/metadata columns |
| `validation` | object | Row validation summary (section 6.3) |
| `status` | string | `ready`, `needs_mapping`, `empty`, `blank` |
| `usable` | boolean | True only when rows > 0, no missing fields, no mapping errors |
| `required_fields` | string[] | The 23 model features |
| `formula_detection` | `"xlsx"` \| `"unavailable"` | Formula detection capability |

### 6.3 `analysis.validation`

```json
{
  "total_rows": 6,
  "valid_rows": 4,
  "invalid_rows": 2,
  "warning_rows": 0,
  "errors": [
    {
      "source_row": 5,
      "column": "EDUCATION",
      "source_column": "EDUCATION",
      "message": "EDUCATION: value is not one of the allowed category codes."
    }
  ],
  "warnings": [],
  "status": "ready",
  "usable": true,
  "missing_fields": [],
  "mapping_errors": [],
  "truncated_errors": false
}
```

`errors` and `warnings` are capped as described in section 4. `truncated_errors` is true when the cap was reached.

---

## 7. Response: batch prediction

Top-level fields:

| Field | Type | Meaning |
|---|---|---|
| `model_id` | string | `uci_taiwan_xgb` |
| `file_name` | string | Uploaded filename |
| `file_format` | string | Detected format |
| `generated_at` | ISO-8601 UTC | Server timestamp |
| `thresholds` | object | `{classification: 0.5, low_upper: 0.25, medium_upper: 0.5}` |
| `calibrated` | boolean | True when every scored row used the calibrator |
| `calibration_method` | string | `"Platt scaling (sigmoid)"` |
| `sheets` | array | Per-sheet denominators |
| `results` | array | One entry per submitted data row, in submission order |
| `calibration_artifact` | string | `models/calibration_model.joblib` |

### 7.1 `sheets[]`

```json
{
  "name": "Portfolio B",
  "total_rows": 2,
  "scored": 1,
  "failed": 1,
  "blank_rows_ignored": 0
}
```

### 7.2 `results[]` — success

```json
{
  "result_index": 1,
  "sheet_name": "Portfolio A",
  "source_row": 2,
  "row_index": 1,
  "borrower_reference": "XL-A-001",
  "status": "success",
  "prediction": {
    "model_id": "uci_taiwan_xgb",
    "probability": 0.08206632971007599,
    "predicted_class": "Lower predicted default risk",
    "risk_category": "Low",
    "calibrated": true,
    "threshold": 0.5,
    "calibration_method": "Platt scaling (sigmoid)"
  }
}
```

- `result_index` is the 1-based position in the returned array.
- `row_index` is the 1-based data-row position within the sheet (excluding header and blank rows).
- `source_row` is the original spreadsheet row number (1-based), so row 2 is the first data row when the header is row 1.
- `borrower_reference` is null when no reference column was mapped.

### 7.3 `results[]` — failure

```json
{
  "result_index": 5,
  "sheet_name": "Portfolio B",
  "source_row": 3,
  "row_index": 2,
  "borrower_reference": "XL-B-002",
  "status": "error",
  "error_message": "EDUCATION: value is not one of the allowed category codes."
}
```

Failure rows have **no** `prediction` object. They are excluded from probability statistics and counted in `failed` / `invalid_rows`.

### 7.4 Ordering guarantee

Results preserve, in this order:

1. the order of the `sheets` array supplied by the client;
2. the order of rows within each worksheet;
3. the original `source_row`;
4. the `borrower_reference` value.

The server does not sort or deduplicate results.

---

## 8. Export endpoints

### 8.1 `POST /v1/research/taiwan/batch/export/xlsx`

JSON body:

```json
{
  "results": [ ...same result objects... ],
  "summary": { "total": 5, "succeeded": 4, "failed": 1 },
  "metadata": { "model_id": "uci_taiwan_xgb", "file_name": "portfolio.xlsx" }
}
```

Response: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, filename `creditai_batch_predictions.xlsx`, two sheets:

- `Predictions` — result rows with columns: `Result #`, `Sheet`, `Source row`, `Sheet row`, `Borrower reference`, `Status`, `Estimated default probability`, `Risk category`, `Predicted class`, `Calibrated`, `Model ID`, `Validation / error message`.
- `Summary` — totals, denominators, model and calibration metadata.

### 8.2 `POST /v1/research/taiwan/batch/export/csv`

Same body. Response: `text/csv; charset=utf-8`, filename `creditai_batch_predictions.csv`, UTF-8 BOM, same logical columns.

### 8.3 Injection protection

Any exported text cell beginning with `=`, `+`, `-`, `@` is prefixed with a single apostrophe. Example:

```text
"5","CSV","6","5","'=cmd|calc","Scored","0.082066","Low",...
```

Numeric cells remain numeric; the protection is applied to text only.

---

## 9. Error envelope and status codes

All handled errors use:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "Human-readable message."
  }
}
```

Request-model validation adds `details`:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "Request validation failed.",
    "details": [{"field": "body.schema_version", "code": "missing"}]
  }
}
```

| Status | Used for |
|---|---|
| `200` | Successful inspect/predict/export; also header-only direct predict with empty `results` |
| `400` | Empty file, corrupt workbook, invalid mapping completeness, row/sheet/column/export limit, unknown sheet |
| `413` | Upload exceeds 10 MiB |
| `415` | Unsupported extension |
| `422` | Invalid JSON in `mapping`/`sheets`, contract violation, invalid categorical value |
| `500` | Unexpected server/model failure (no stack trace or row values returned) |

The global handler deliberately avoids echoing request bodies, so error responses do not leak borrower values.

---

## 10. Adjacent endpoints (not part of batch)

### `GET /health`

```json
{"status": "ok", "scoring": "not_validated"}
```

### `POST /v1/predict`

Single Taiwan research prediction. Accepts `{model_id, features}` and returns probability, risk category, calibration flag, threshold, limitations and top feature contributions. Invalid categorical codes return `422`.

### `POST /v1/score`

Indian production-score contract. It validates the request and then returns a `not_validated` response without loading or invoking any model:

```json
{
  "score_status": "not_validated",
  "score_type": "none",
  "default_probability": null,
  "validated_risk_estimate": false,
  "model_version": null,
  "provenance": {"source": "no_validated_model", "synthetic_demo": false},
  "message": "No validated CreditAI model is available; no risk score was produced."
}
```

No batch endpoint can change this state.

---

## 11. Compatibility notes

1. **Display-string difference:** batch metadata uses `"Platt scaling (sigmoid)"`; single prediction returns `"Platt sigmoid"`. Both refer to the same calibrator, but clients should not compare the strings for equality.
2. **`source_row` vs `row_index`:** clients should display `source_row` for traceability and use `row_index` only for sheet-local ordering.
3. **Header-only input:** `inspect` sets `status: "empty"` and `usable: false`; `batch-predict` still returns `200` with an empty `results` array. Clients must check `usable` before calling predict.
4. **`.xls`:** accepted by the extension check but not verified in this session. Do not advertise it as tested.
5. **`analysis.rows`** is a preview capped at the row limit; it is not the full dataset. Predictions are generated server-side from the file, not from the preview.

---

## 12. Contract test map

| Contract area | Test |
|---|---|
| Upload/limit errors | `test_empty_corrupt_unsupported_and_oversized_uploads`, `test_row_limit_is_enforced_after_parsing` |
| Header normalisation | `test_inspect_valid_csv_with_bom_and_reference`, `test_analyze_explicit_mapping_accepts_spaces_and_case` |
| Mapping uniqueness | `test_analyze_duplicate_target_is_rejected_without_guessing`, `test_explicit_mapping_resolves_duplicate_headers` |
| Order/reference preservation | `test_predict_preserves_sheet_order_rows_and_references`, `test_blank_rows_are_ignored_but_source_rows_are_preserved` |
| No imputation / no fabrication | `test_predict_requires_complete_mapping_and_never_imputes`, `test_formula_cells_are_rejected_not_trusted` |
| Export safety | `test_csv_export_is_ordered_and_formula_injection_safe`, `test_xlsx_export_has_summary_formatting_and_injection_protection`, `test_export_rejects_unbounded_payloads` |
| Gate unchanged | `test_health_and_score_contract_remain_unchanged`, live `/v1/score` check |
| Research model identity | `test_batch_inspect_is_research_only_model` |

Live evidence: `logs/verify_live_session6.out.log` (38/38 checks). Backend suite: `logs/pytest_session6.out.log` (138 passed).
