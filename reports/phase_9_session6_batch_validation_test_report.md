# Phase 9 — Session 6: Batch Validation and Test Report

**Date:** 2026-10-22
**Project:** `F:\NUV ACD\All SEM\7th Sem\ML&DS\New folder (3)\CreditAI`
**Commit under test:** `549acea727b19fedc37697a5d8bce1a9b9b69d05` (`Add batch evaluation feature`) plus uncommitted batch work
**Scope:** Automated and live verification of the CSV/XLSX batch workflow, row validation, prediction, exports and the research-only API gate.

---

## 1. Result summary

| Suite | Command | Result |
|---|---|---|
| Backend, full | `.\.venv\Scripts\python.exe -m pytest -q` | **138 passed**, 0 failed, 55 warnings, **147.19 s** |
| Backend, batch only | `.\.venv\Scripts\python.exe -m pytest tests/test_batch_workflow.py -q` | **20 passed**, 0 failed |
| Frontend, all test files | `npm test` (in `frontend/`) | **26 passed**, 0 failed (21 batch + 5 dashboard) |
| Frontend build | `npm run build` | **success**, 25 modules, 664 ms |
| Frontend lint | `npm run lint` (oxlint) | **no findings** |
| Live API contract | `python C:\Users\Admin\AppData\Local\Temp\opencode\verify_live.py` | **38 / 38 checks passed** |
| Live browser flow | Manual browser session against `http://127.0.0.1:5173` | CSV and multi-sheet XLSX completed end to end; exports inspected |

No test was skipped or marked expected-failure. The only failures encountered during the session were the pre-existing parse error in `frontend/src/batch.ts` (fixed) and deliberate 4xx responses used as negative tests.

Evidence logs:

- `logs/pytest_session6.out.log`
- `logs/fetest_session6.out.log`
- `logs/build_session6.out.log`
- `logs/lint_session6.out.log`
- `logs/verify_live_session6.out.log`

---

## 2. Environment

| Component | Version / value |
|---|---|
| OS | Windows (win32) |
| Python (backend) | 3.11.9, virtual environment `.venv` |
| Node.js | v24.13.1 |
| npm | 11.8.0 |
| scikit-learn | 1.9.1 (model artifacts pickled with 1.9.0; load with `InconsistentVersionWarning`) |
| Backend | `uvicorn src.api.app:app --host 127.0.0.1 --port 8000` |
| Frontend | Vite dev server, `http://127.0.0.1:5173`, proxy to port 8000 |
| Model | `uci_taiwan_xgb`, Taiwan UCI credit-card benchmark |

The backend was started from `.venv\Scripts\python.exe`; on Windows the venv launcher re-executes the base interpreter, so both the launcher and the base process appear in the process list. The live verification script was run with the system Python 3.11.9 because the venv does not include the `requests` package. The script only performs HTTP calls; it does not import project modules.

---

## 3. Backend test inventory

`pytest --collect-only -q` reports 138 tests:

| File | Tests | Area |
|---|---:|---|
| `tests/test_api_contract.py` | 9 | Score API contract, validation, not-validated gate |
| `tests/test_api_integration.py` | 11 | API integration and error envelopes |
| `tests/test_batch_workflow.py` | 20 | Batch parsing, mapping, prediction, exports |
| `tests/test_financial_pipeline.py` | 5 | Financial feature pipeline |
| `tests/test_inference.py` | 13 | Model registry, schema, single prediction |
| `tests/test_phase12_signal.py` | 3 | Signal validation |
| `tests/test_phase22_audit.py` | 4 | Phase 2.2 audit artifacts |
| `tests/test_phase23_benchmark.py` | 14 | Benchmark metrics |
| `tests/test_phase5_data_validation.py` | 45 | Data intake and validation |
| `tests/test_phase8_features.py` | 7 | Phase 8 features and evaluation endpoint |
| `tests/test_pipeline.py` | 7 | End-to-end pipeline |
| **Total** | **138** | |

---

## 4. Batch test coverage (`tests/test_batch_workflow.py`)

| Test | Behaviour proved |
|---|---|
| `test_inspect_valid_csv_with_bom_and_reference` | UTF-8 BOM, case/space-insensitive headers, `borrower_reference` treated as metadata, 23/23 required fields found |
| `test_inspect_multisheet_summary_blank_and_duplicate_detection` | Every worksheet listed; blank sheet flagged; duplicate/ambiguous headers reported without guessing |
| `test_inspect_missing_schema_is_precise_and_never_fabricated` | Missing required fields returned as `missing_fields`, not a generic 422; `usable: false` |
| `test_analyze_explicit_mapping_accepts_spaces_and_case` | Explicit mapping resolves spaced/mixed-case headers |
| `test_analyze_duplicate_target_is_rejected_without_guessing` | Two source columns mapped to one required target is rejected |
| `test_explicit_mapping_resolves_duplicate_headers` | A user can resolve an ambiguous header by index |
| `test_predict_preserves_sheet_order_rows_and_references` | Result order, sheet name, source row, result index and reference preserved |
| `test_predict_requires_complete_mapping_and_never_imputes` | Incomplete mapping aborts; no default value is invented |
| `test_predict_rejects_blank_and_unknown_sheets` | Blank/unknown sheet selection rejected |
| `test_formula_cells_are_rejected_not_trusted` | Excel formula cells are validation errors, never evaluated |
| `test_blank_rows_are_ignored_but_source_rows_are_preserved` | Blank rows skipped; original row numbers retained |
| `test_empty_corrupt_unsupported_and_oversized_uploads` | `400` empty, `400` corrupt workbook, `415` unsupported type, `413` oversized |
| `test_row_limit_is_enforced_after_parsing` | 5,001-row sheet rejected with the documented limit |
| `test_csv_renamed_as_xlsx_uses_safe_fallback` | Delimited text with an `.xlsx` name is detected and parsed as CSV |
| `test_excel_numbers_stored_as_text_are_warned` | Text-formatted numeric cells validate with a warning, not silent coercion |
| `test_csv_export_is_ordered_and_formula_injection_safe` | Export order preserved; `=cmd|calc` neutralised |
| `test_xlsx_export_has_summary_formatting_and_injection_protection` | `Predictions` + `Summary` sheets, formatting, injection protection |
| `test_export_rejects_unbounded_payloads` | Export payload above 20,000 rows rejected |
| `test_health_and_score_contract_remain_unchanged` | `/health` and `/v1/score` semantics unchanged |
| `test_batch_inspect_is_research_only_model` | Batch endpoints report `uci_taiwan_xgb`, not a production Indian model |

---

## 5. Frontend test coverage (`frontend/tests/batch.test.ts`)

The batch test file contains 21 tests; the full `npm test` run also executes 5 dashboard tests from `tests/analytics.test.ts`, for 26 total.

| Group | Tests |
|---|---|
| CSV parsing | header/row parsing, trailing blank line, quoted delimiters |
| Mapping | 23-field missing-field detection, case/space tolerance, move/clear mapping, missing/duplicate issues |
| Injection | `sanitizeCell` neutralises `=`, `+`, `-`, `@`; CSV export escapes quotes and sanitises references |
| Statistics | success/failure counts, mean over scored rows only, sheet denominators, risk counts, empty-result statistics, median, histogram covers each finite probability exactly once |
| Formatting | probability and byte formatting keep unavailable values readable |
| Results table | combined status/risk/search filter; stable non-mutating sort |
| Exports | result CSV keeps order/sheet/source row/reference/failures; validation CSV exports real issues; XLSX payload includes real results, denominators and metadata; Markdown report includes evidence, denominators, limitations and validation errors |
| Template | all required headers plus one synthetic row |

Run output tail:

```text
ℹ tests 26
ℹ suites 1
ℹ pass 26
ℹ fail 0
ℹ duration_ms 900.2948
```

---

## 6. Live API verification (38 checks)

The live script exercised the running server, not an in-process test client. Full output: `logs/verify_live_session6.out.log`.

### 6.1 Health and single prediction

| Check | Observed |
|---|---|
| `/health` | `{"status":"ok","scoring":"not_validated"}` |
| Single prediction, low preset | `200`, probability `0.08206633`, `Low`, calibrated `true` |
| Single prediction, severe preset | `200`, higher probability, calibrated `true` |
| Invalid category (`EDUCATION=9`) | `422`, `Field 'EDUCATION' must be one of [1, 2, 3, 4, 5, 6], got 9.` |
| `/v1/score` with a valid transaction payload | `200`, `score_status: not_validated`, `default_probability: null`, `validated_risk_estimate: false` |

### 6.2 CSV: BOM, spaces, mixed case, extra column, invalid rows

| Check | Observed |
|---|---|
| Inspect status | `200` |
| Detected format | `csv` |
| Required fields | `23/23`, `missing_fields: []` |
| Extra column | `notes` reported at index 23 |
| Reference mapping | `borrower_reference` recognised as metadata |
| Validation | `6` rows, `4` valid, `2` invalid |
| Invalid reasons | `EDUCATION` category code; blank `LIMIT_BAL` row |
| Prediction | `200`, 4 scored rows, 2 row-level failures |
| Probabilities | `0.0821, 0.2482, 0.4113, 0.0821` — distinct, not placeholders |
| Order/references | `APP-001 … APP-004` preserved |
| Fabricated values on failures | none (`prediction` absent, `error_message` present) |
| Calibration metadata | `calibrated: true`, `Platt scaling (sigmoid)` |

### 6.3 Multi-sheet XLSX

| Check | Observed |
|---|---|
| Inspect status | `200` |
| Sheets | `Portfolio A`, `Portfolio B`, `Blank sheet`, `Incomplete` |
| Blank sheet | `blank: true` |
| Incomplete sheet | required features missing |
| Selected-sheet inspect | `200`; spaced headers in `Portfolio B` auto-mapped |
| Preview | limited and typed |
| Prediction | `200`; both sheets scored |
| Sheet names preserved | `Portfolio A ×3`, `Portfolio B ×2` |
| Sheet summaries | A: 3/3 scored; B: 1/2 scored, 1 failed |

### 6.4 Exports

| Check | Observed |
|---|---|
| XLSX export | `200`, 6,988 bytes |
| XLSX sheets | `Predictions`, `Summary` |
| XLSX columns | result number, sheet, source row, sheet row, reference, status, probability, risk, class, calibration flag, model, error |
| XLSX row count | 5, equal to backend `results` |
| CSV export | `200` |
| Formula injection | reference exported as `'=cmd|calc` (leading apostrophe) |
| Numeric preservation | probabilities remain numeric decimal strings, not text-mangled |

### 6.5 Failure modes

| Input | Status | Message / behaviour |
|---|---|---|
| Missing required column | `200` inspect, `usable: false`, `needs_mapping` | precise `missing_fields`; no prediction path |
| Header-only CSV | `200` inspect, `status: empty`, `usable: false` | direct predict returns `200` with `results: []` (no fabricated rows) |
| Corrupted `.xlsx` | `400` | “Could not open the Excel workbook … File is not a zip file” |
| Unsupported `.txt` | `415` | “Unsupported file type. Upload a .csv, .xlsx or .xls file.” |
| Empty file | `400` | “The uploaded file is empty.” |
| File > 10 MB | `413` | size-limit message |
| Sheet > 5,000 rows | `400` | maximum-rows message |
| Duplicate target mapping | `422` / validation error | rejected without guessing |
| Formula cell | row-level error | formula text reported, never evaluated |

---

## 7. UI-level validation checks

Performed in the browser against the live Vite app:

| Scenario | UI behaviour |
|---|---|
| Valid CSV | Step 1 “Ready / Schema complete”; Step 2 `6 total / 4 valid / 2 invalid`; Step 3 `4 of 6 scored` |
| Multi-sheet XLSX | All four sheets listed with independent status; selection of A and B enabled Continue |
| Missing required column | `Needs mapping`, Continue disabled, explicit “1 required feature(s) not mapped” |
| Unsupported file | Immediate unsupported-type message; no request sent |
| Corrupted workbook | Explicit “could not open / may be corrupted” message |
| Header-only file | Marked unusable at Step 1; UI cannot advance to prediction |
| Invalid category row | Row shown as `Failed` with the backend message; not counted in statistics |
| Zero scored rows | Empty-state message; probability statistics unavailable rather than zero |
| Formula reference | Displayed as text; export neutralised |

The batch page also renders after a production build and after the dev server restart; see `reports/figures/phase_9_session6_batch_step1.png`.

---

## 8. Defects found and fixed in this session

| Defect | Impact | Fix | Regression evidence |
|---|---|---|---|
| `frontend/src/batch.ts` ended with `]` instead of `)` in `buildAnalysisReport` | Module parse error; Batch Evaluation route failed to render | One-token syntax fix; no logic change | Build, lint, 26 frontend tests, browser flow |
| Frontend tests had been reduced to 6 | Low coverage of export/injection/statistics | Restored and extended to 21 batch tests | `npm test` 26/26 |

Earlier backend fixes were re-verified, not re-implemented:

- header normalisation (BOM, spaces, case, separators) with uniqueness requirement;
- structured 422 detail instead of a generic malformed-body message;
- CSV/XLSX fallback for mislabelled files.

---

## 9. Limitations and untested paths

1. **`.xls` is not claimed as tested.** The reader has an `xlrd` branch, but only `.csv` and `.xlsx` were exercised end to end. The UI copy lists `.xls`; this should be narrowed or a real `.xls` fixture added before claiming support.
2. **Header-only direct prediction** returns `200` with an empty result list rather than `400`. The UI prevents this call because `usable: false`. This is a documented API asymmetry.
3. **Browser upload automation** injected a `File` into the real hidden input with `DataTransfer` and dispatched the real React `change` event. The real handler and real multipart request ran, but this is not an OS file-picker test.
4. **Large-file performance** was not benchmarked near the 10 MB / 5,000-row limits; only limit enforcement was tested.
5. **Excel formula detection** is only available for `.xlsx`; the service explicitly reports `formula_detection: "unavailable"` for CSV and `.xls`.

---

## 10. Reproduction

```powershell
# from the project root
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest tests/test_batch_workflow.py -q

cd frontend
npm test
npm run build
npm run lint
```

Live checks require the backend on port 8000:

```powershell
python C:\Users\Admin\AppData\Local\Temp\opencode\verify_live.py
```

Fixtures: `frontend/public/testdata/` and `C:\Users\Admin\AppData\Local\Temp\opencode\creditai_fixtures\`. All fixtures are synthetic; no real borrower data is present.

---

## 11. Verdict

The batch validation surface is covered at three levels — service/API unit tests, live HTTP contract checks, and browser workflow checks — with no failing test and no fabricated result on any failure path. The untested `.xls` branch and the header-only API asymmetry are the only material gaps, and both are disclosed rather than hidden.
