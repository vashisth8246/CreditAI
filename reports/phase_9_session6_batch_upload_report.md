# Phase 9 — Session 6: Batch Upload Root-Cause and Fix Report

**Date:** 2026-10-22
**Project:** `F:\NUV ACD\All SEM\7th Sem\ML&DS\New folder (3)\CreditAI`
**Commit:** `549acea Add batch evaluation feature`
**Scope:** Fix the broken batch upload/UI, verify CSV and XLSX end to end, document actual evidence.

---

## 1. Executive summary

The batch workflow is now working end to end in the live application:

- CSV upload → inspect → preview/mapping/validation → prediction → charts → export **works**.
- Multi-sheet XLSX upload → per-sheet selection → per-sheet validation → combined prediction preserving sheet and source row → charts → export **works**.
- Missing required columns, unsupported file types, corrupt workbooks, formula-injection references and invalid categorical values are handled with explicit, actionable messages.

The immediate blocker in this session was a **broken frontend module**, not an HTTP or file-format problem. `frontend/src/batch.ts` ended in the middle of a function call, so the module could not be parsed and the Batch Evaluation page could not render. The previously reported server-side CSV problems (exact-header matching and masked errors) were already fixed in the preceding session by `src/api/batch_service.py`; those fixes were re-verified here.

---

## 2. Root causes

### 2.1 Current blocker — truncated TypeScript/JavaScript module (fixed)

**Symptom observed:** opening `http://127.0.0.1:5173/` and clicking **Batch evaluation** left the application on the previous page; the batch UI never rendered.

**Root cause:** the final statement of `buildAnalysisReport` in `frontend/src/batch.ts` was:

```ts
lines.push(
  '',
  '## Limitations',
  ...
  '- The production `/v1/score` endpoint remains disabled ...',
]          // <-- opened with ( but closed with ]
```

Node/TypeScript reported:

```text
SyntaxError [ERR_INVALID_TYPESCRIPT_SYNTAX]: Expression expected
    at .../frontend/src/batch.ts:615
```

Because `BatchEvaluation.tsx` imports this module, the whole route failed to load. An earlier copy of the file also contained trailing NUL padding, consistent with an interrupted write; the surviving text still ended mid-call. This was not an HTTP, CORS, proxy or multipart failure.

**Fix applied:** changed the closing `]` to `)` and preserved the file's UTF-8 en dash. No logic was altered.

**Evidence after the fix:**

```text
npm run build   -> ✓ built in 1.32s (25 modules transformed)
npm test        -> 26 tests, 26 pass, 0 fail
```

The browser then rendered Step 1 and completed the full workflow (section 4).

### 2.2 Earlier upload failures — retained fixes, re-verified

The preceding session documented and fixed these in `src/api/batch_service.py`:

1. **Exact-only header matching.** Headers such as `LIMIT BAL`, `pay_0`, `EDUCATION ` were rejected as missing. The new service normalises BOM, whitespace, case and separators, but only accepts the match when it is unique.
2. **Structured 422 detail masked by the global exception handler.** Missing-column responses became a generic "Invalid HTTP request or malformed body". They now return a precise message; an inspection response also exposes `missing_fields`, `duplicate_headers` and `extra_columns`.
3. **CSV bytes with an `.xlsx` extension** caused an opaque pandas error. The reader now falls back between CSV and Excel parsing and reports corruption explicitly.

These were re-verified through the live API and browser in this session.

---

## 3. Implementation surface used by the upload path

| Layer | File | Role |
|---|---|---|
| Parsing / validation | `src/api/batch_service.py` (untracked, inherited) | CSV/XLSX read, sheet inspection, header normalisation, row validation, prediction, CSV/XLSX export |
| HTTP | `src/api/app.py` | `/inspect`, `/analyze`, `/batch-predict`, `/export/xlsx`, `/export/csv` |
| Frontend API | `frontend/src/api.ts` | Multipart upload, JSON sheets payload, export blob |
| Frontend helpers | `frontend/src/batch.ts` | Mapping, statistics, filters, histogram, CSV/report builders |
| Frontend UI | `frontend/src/BatchEvaluation.tsx` | Three-step workflow |
| Charts | `frontend/src/BatchCharts.tsx` | SVG charts derived only from returned results |

---

## 4. Live upload evidence

Server: `http://127.0.0.1:8000` (system Python 3.11, uvicorn).
Frontend: `http://127.0.0.1:5173` (Vite, proxying `/v1` and `/health` to port 8000).

### 4.1 CSV (`portfolio_quirky.csv`)

Fixture properties: UTF-8 BOM, headers with leading/trailing spaces and mixed case, one extra `notes` column, one `borrower_reference` column, one invalid `EDUCATION=9`, one blank model row with a reference, one formula-like reference `=cmd|calc`.

UI Step 1 reported:

```text
FILE portfolio_quirky.csv · SIZE 819 B · DETECTED FORMAT CSV · WORKSHEETS 1
CSV | 6 rows | 25 columns | Ready | Schema complete
```

UI Step 2 reported:

```text
TOTAL ROWS 6 | VALID ROWS 4 | INVALID ROWS 2
REQUIRED FEATURES FOUND 23/23 | MISSING REQUIRED 0 | EXTRA COLUMNS 1 | DUPLICATE HEADERS 0
```

UI Step 3 returned:

```text
Prediction complete — 4 of 6 row(s) scored, 2 failed.
model uci_taiwan_xgb · Platt scaling (sigmoid)

APP-001  CSV  row 2  Scored   8.21%  Low
APP-002  CSV  row 3  Scored  24.82%  Low
APP-003  CSV  row 4  Scored  41.13%  Medium
APP-004  CSV  row 5  Failed   —      EDUCATION: value is not one of the allowed category codes.
=cmd|calc CSV row 6  Scored   8.21%  Low
BLANK-ROW CSV row 7  Failed   —      LIMIT_BAL: missing required value.
```

Mean PD 20.59%, median 16.51%, denominators explicitly stated as 4 scored rows.

### 4.2 XLSX multi-sheet (`portfolio_multisheet.xlsx`)

Workbook: `Portfolio A` (3 valid rows), `Portfolio B` (2 rows, spaced headers, 1 invalid), `Blank sheet`, `Incomplete` (4 columns).

UI Step 1 listed all four sheets and marked:

```text
Portfolio A | 3 | 25 | Ready | Schema complete
Portfolio B | 2 | 25 | Ready | Schema complete
Blank sheet | — | — | Blank sheet | 23 required feature(s) missing
Incomplete  | 1 | 4  | Needs mapping | 20 required feature(s) missing
2 worksheet(s) selected
```

After selecting **Portfolio A** and **Portfolio B**, Step 2 exposed separate sheet tabs and per-sheet validation. Step 3 returned 4 scored / 1 failed across both sheets, preserving order, sheet name and original row:

```text
XL-A-001  Portfolio A  row 2  8.21%   Low
XL-A-002  Portfolio A  row 3  24.82%  Low
XL-A-003  Portfolio A  row 4  41.13%  Medium
XL-B-001  Portfolio B  row 2  8.21%   Low
XL-B-002  Portfolio B  row 3  Failed  EDUCATION: value is not one of the allowed category codes.
```

The **Risk distribution by worksheet** chart showed `Portfolio A n=3 scored/3 rows, mean 24.7%` and `Portfolio B n=1 scored/2 rows, mean 8.2%`.

### 4.3 Failure modes seen in the UI

| Input | UI result |
|---|---|
| `missing_column.csv` | `Needs mapping`, `1 required feature(s) missing`, Continue disabled, `Before continuing: CSV: 1 required feature(s) not mapped.`; template download available |
| `unsupported.txt` | `Unsupported file type. Upload a .csv, .xlsx or .xls file.` |
| `corrupted.xlsx` | `Could not open the Excel workbook. It may be corrupted, password-protected, or not a real .xlsx file. Details: File is not a zip file` |
| header-only CSV | Inspect marks validation `empty`, `usable: false`; prediction returns zero results, so the UI cannot advance (no fabricated rows) |

---

## 5. Changed files (this session)

| File | Change |
|---|---|
| `frontend/src/batch.ts` | Fixed the truncated `lines.push(...]` closing token → `)`. This was the blocking parse error. |
| `frontend/tests/batch.test.ts` | Restored and extended to 26 tests (mapping, histogram, median, filters, sorting, CSV/XLSX payloads, analysis report, injection protection). |
| `frontend/public/testdata/*` | Added synthetic verification fixtures: quirky CSV, exact CSV, missing-column CSV, header-only CSV, multi-sheet XLSX, corrupted XLSX, unsupported TXT. No borrower data. |

No model artifact, historical report, or backend behaviour was replaced. The uncommitted batch implementation inherited from the prior session was preserved.

---

## 6. Known limitations

- `.xls` has a code path (`xlrd`) but was **not** exercised in this session; only `.csv` and `.xlsx` are claimed as tested.
- The browser automation injected `File` objects into the real file input because the accessibility snapshot could not expose the hidden input ref; the real React `change` handler and the real HTTP upload path were executed. This is not an OS file-picker test, but every byte sent to the backend came from the fixture file.
- Header-only workbooks are blocked at Step 1 (`usable: false`); a direct `batch-predict` call returns `200` with an empty result list rather than `400`. The UI prevents this call.
