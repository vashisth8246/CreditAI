# Phase 9 — Session 6: Frontend Report

**Date:** 2026-10-22
**Application:** `http://127.0.0.1:5173` (Vite dev server, backend proxy to `http://127.0.0.1:8000`)
**Route:** **Batch evaluation** (sidebar item 3)
**Scope:** Three-step CSV/XLSX batch workflow, charts, result table, exports and failure handling.

---

## 1. Summary

The Batch Evaluation page now renders and completes the full workflow against the live backend:

- **Step 1** — upload, format detection, worksheet inventory and selection.
- **Step 2** — per-sheet tabs, compact paginated preview, explicit column mapping, validation summary, template and error downloads.
- **Step 3** — live prediction, KPI cards with explicit denominators, five charts, sortable/searchable/filterable results, and four exports.

All displayed predictions, counts and chart values come from the backend response. There are no example, fallback or randomly generated rows. Failed rows remain visible with their error message and are excluded from probability statistics.

A screenshot of the restored page is at `reports/figures/phase_9_session6_batch_step1.png`.

---

## 2. Files

| File | Responsibility |
|---|---|
| `frontend/src/BatchEvaluation.tsx` | Three-step state machine, upload/sheet selection, mapping editor, preview, run, KPI cards, results table, export actions |
| `frontend/src/BatchCharts.tsx` | SVG/CSS charts derived only from `BatchSummary` |
| `frontend/src/batch.ts` | CSV parsing, mapping helpers, statistics, histogram, filters, sort, export builders, Markdown report |
| `frontend/src/api.ts` | Multipart upload, batch endpoints, export blob, base-URL fallback |
| `frontend/src/App.css` | Batch layout, table, chart and responsive styling |
| `frontend/tests/batch.test.ts` | 21 unit tests for the helpers |
| `frontend/public/testdata/` | Synthetic CSV/XLSX fixtures |

---

## 3. Step 1 — Upload and select data

### Capabilities

- Drag-and-drop zone plus **Choose file** button; the file input is `aria-label="Upload a CSV or Excel workbook"`.
- Accepts one workbook at a time; format is detected from content, not only the extension.
- Shows file name, size, detected format and worksheet count.
- Lists every worksheet in a table with: name, row count, column count, status badge and missing-required count.
- Each worksheet has an **Include worksheet** checkbox. At least one usable sheet is required to continue.
- “2 worksheet(s) selected” counter and a **Continue to Step 2** button.
- **Download CSV template** produces all 23 Taiwan features plus `borrower_reference` and one synthetic example row.
- **Replace file** and **Choose another file** reset the flow cleanly.

### Status semantics

| Badge | Meaning |
|---|---|
| `Ready` / `Schema complete` | All required fields auto-mapped |
| `Needs mapping` | One or more required features missing; mapping must be completed in Step 2 |
| `Blank sheet` | No data rows |
| `Empty` | Header-only or no usable rows |

### Observed — CSV

```text
FILE portfolio_quirky.csv · SIZE 819 B · DETECTED FORMAT CSV · WORKSHEETS 1
CSV | 6 rows | 25 columns | Ready | Schema complete
```

The file had a UTF-8 BOM, headers with leading/trailing spaces and mixed case, an extra `notes` column, a `borrower_reference` column, one invalid `EDUCATION=9`, one blank model row and a formula-like reference `=cmd|calc`.

### Observed — multi-sheet XLSX

```text
Portfolio A | 3 | 25 | Ready        | Schema complete
Portfolio B | 2 | 25 | Ready        | Schema complete
Blank sheet | — | —  | Blank sheet  | 23 required feature(s) missing
Incomplete  | 1 | 4  | Needs mapping| 20 required feature(s) missing
2 worksheet(s) selected
```

---

## 4. Step 2 — Preview, map and validate

### Per-sheet tabs

Selected worksheets appear as tabs (`role="tablist"`, `aria-label="Selected worksheets"`). Each tab shows the sheet name and its validation status. Switching tabs re-renders the statistics, mapping and preview for that sheet; the client does not merge sheets.

### Validation summary

A compact stat grid shows:

- total rows, valid rows, invalid rows, warning rows
- required features found (`23/23`)
- missing required count and names
- extra columns, duplicate headers

Observed for the quirky CSV:

```text
TOTAL ROWS 6 | VALID ROWS 4 | INVALID ROWS 2
REQUIRED FEATURES FOUND 23/23 | MISSING REQUIRED 0 | EXTRA COLUMNS 1 | DUPLICATE HEADERS 0
```

### Column mapping

- The mapping panel is collapsible (`Show mapping` / `Hide mapping`).
- One row per source column; a `<select>` chooses the target feature, `Ignore`, or `borrower_reference`.
- Already-assigned targets are marked, and attempts to assign a duplicate are surfaced by `mappingIssues`.
- Changing a mapping calls `/batch/analyze` with the current sheet and explicit mapping; the backend re-validates rather than the browser guessing.
- Missing fields are listed explicitly; **Continue to Step 3** stays disabled until the mapping is complete and the sheet is usable.

### Preview

- First **15 rows per page**, horizontal scroll confined to the table.
- Column search (`Search preview columns`), column visibility toggles with **Show all columns**, and previous/next pagination.
- Original source row numbers are shown as the first column, so a preview row can be traced back to the workbook.
- Values are the backend's typed/truncated preview values; the UI does not re-interpret blanks.

### Validation details and downloads

- Errors show source row, column, source column and message (first 100 displayed).
- Warnings show the same shape (first 50 displayed).
- **Download validation errors CSV** is enabled only when there are issues and exports the real issues with formula neutralisation.
- **Download CSV template** remains available.

### Guard conditions

- No sheet selected → “No worksheet selected” with a return-to-Step-1 action.
- Blank sheet → “This worksheet is blank” and no mapping controls.
- Missing fields → `Before continuing: CSV: 1 required feature(s) not mapped.`
- `usable: false` → Continue disabled.

---

## 5. Step 3 — Predict and analyse

### Run panel

- Lists each selected sheet with rows, valid count and invalid count.
- Shows **Total rows to submit**.
- States: “Rows with validation errors will be returned individually as failed rows; nothing is imputed.”
- While running: a status region announces “Scoring N row(s) across M worksheet(s)…”. Predictions appear only after the backend responds.
- On transport/HTTP failure: an alert with the backend message and a **Retry** button. No local fallback.

### KPI cards

| Card | Value shown | Denominator |
|---|---|---|
| Total rows submitted | backend `results.length` | all submitted rows |
| Successfully scored | `summary.succeeded` | — |
| Failed / rejected | `summary.failed` | — |
| Mean estimated PD | `summary.meanProbability` | explicitly “Denominator: N scored rows” |
| Median estimated PD | `summary.medianProbability` | explicitly “Denominator: N scored rows” |
| Risk mix | `L n · M n · H n` | “denominator N”; thresholds `<25%`, `25% to <50%`, `≥50%` |

If `succeeded === 0`, the UI shows **“No rows could be scored”** and states that probability statistics are unavailable rather than zero. Charts are not rendered in that state.

### Charts

All five charts derive from the same `BatchSummary` and show sample sizes:

1. **Risk distribution** — Low / Medium / High bars with counts and percentage of scored rows.
2. **Probability histogram** — mutually exclusive probability bands; 100% included in the final band.
3. **Cumulative probability** — cumulative share of scored borrowers at or below each PD threshold.
4. **Prediction status** — every submitted row counted once as scored or failed; denominator is total submitted.
5. **Risk distribution by worksheet** — one stacked Low/Medium/High bar per sheet, with `n = scored / total` and mean PD. Hidden when fewer than two sheets have scored rows, because a single-sheet comparison would be misleading.

### Observed — CSV result

```text
Prediction complete — 4 of 6 row(s) scored, 2 failed.
model uci_taiwan_xgb · Platt scaling (sigmoid)

APP-001  CSV  row 2  Scored   8.21%   Low
APP-002  CSV  row 3  Scored  24.82%   Low
APP-003  CSV  row 4  Scored  41.13%   Medium
APP-004  CSV  row 5  Failed   —       EDUCATION: value is not one of the allowed category codes.
=cmd|calc CSV row 6  Scored   8.21%   Low
BLANK-ROW CSV row 7  Failed   —       LIMIT_BAL: missing required value.
```

Mean PD `20.59%`, median `16.51%`, both over 4 scored rows.

### Observed — multi-sheet XLSX result

```text
XL-A-001  Portfolio A  row 2  8.21%   Low
XL-A-002  Portfolio A  row 3  24.82%  Low
XL-A-003  Portfolio A  row 4  41.13%  Medium
XL-B-001  Portfolio B  row 2  8.21%   Low
XL-B-002  Portfolio B  row 3  Failed  EDUCATION: value is not one of the allowed category codes.
```

Chart evidence:

```text
Portfolio A  n = 3 scored / 3 rows  mean 24.7%
Portfolio B  n = 1 scored / 2 rows  mean 8.2%
```

### Results table

- Columns: `#`, borrower reference, worksheet, source row, status, estimated PD, risk, detail.
- Status filters with live counts: All, Scored, Failed, Low, Medium, High.
- Free-text search across reference, sheet, row, status and error.
- Sortable by result index, reference, sheet, source row and probability; sorting does not mutate the source array.
- Pagination: **25 rows per page**, with page count and matching-row count.
- Error rows show the backend message; successful rows show predicted class and threshold in the detail column.
- Risk pills and row classes are derived from `risk_category`.

### Exports

| Button | Source | Format |
|---|---|---|
| Download predictions CSV | Browser, from the same result object | UTF-8 BOM CSV |
| Download predictions Excel | Backend `/batch/export/xlsx` | `.xlsx` with `Predictions` + `Summary` |
| Download validation errors | Browser, from per-sheet validation issues | UTF-8 BOM CSV |
| Download analysis report (.md) | Browser, from results + sheets + validation | Markdown |

Export controls state: “Exports use the actual backend results and preserve order, worksheet names and source rows. Text cells are neutralised against spreadsheet formula injection.”

Downloaded and inspected during verification:

- predictions CSV: 4 scored + 2 failed rows, sheet/source row/reference preserved; formula reference exported as `'=cmd|calc`.
- predictions XLSX: `Predictions` and `Summary` sheets; 5 result rows; reference and error columns present.
- validation errors CSV: real row/column messages.
- Markdown report: denominators, calibration note, validation errors and limitations.

---

## 6. Failure-mode UX

| Input | UI behaviour |
|---|---|
| Missing required column | `Needs mapping`; Continue disabled; explicit missing count/names; template available |
| Unsupported `.txt` | “Unsupported file type. Upload a .csv, .xlsx or .xls file.” No prediction request |
| Corrupted `.xlsx` | “Could not open the Excel workbook. It may be corrupted, password-protected, or not a real .xlsx file. Details: File is not a zip file” |
| Header-only CSV | Step 1 marks `empty`, `usable: false`; cannot advance; no fabricated rows |
| Invalid category | Row-level `Failed` with the backend message; excluded from statistics |
| Backend offline | Alert with “The batch research API is unreachable. Check that the FastAPI backend is running on port 8000.” Retry available |
| API 4xx | `batchDetail` extracts the `error.message`; displayed verbatim, no generic “network error” |
| Zero scored rows | Empty state; statistics unavailable; no division-by-zero values |

---

## 7. Accessibility and interaction details

- The three-step progress control is a `navigation` landmark labelled “Batch evaluation progress”; the active step uses `aria-current="step"`.
- Sheet selection checkboxes have `aria-label="Include worksheet <name>"`.
- Preview and result search inputs have explicit `aria-label`s.
- Table sort headers expose `aria-sort`.
- Filter buttons use `aria-pressed`.
- Running and success banners use `role="status"`; errors use `role="alert"`.
- Charts have `role="img"` / `aria-labelledby` and text equivalents for counts.
- The research-only warning is permanent and visible above the workflow: the Taiwan benchmark is not validated for Indian borrowers or production underwriting.

---

## 8. Build, lint and tests

```text
npm run build  → ✓ 25 modules transformed, built in 664ms
npm run lint   → oxlint, no findings
npm test       → 26 tests, 26 pass, 0 fail (900ms)
```

The build output was:

```text
dist/index.html                   0.45 kB │ gzip:   0.29 kB
dist/assets/index-CFUlQD37.css   49.68 kB │ gzip:  11.21 kB
dist/assets/index-CuVOo2an.js   368.70 kB │ gzip: 105.52 kB
```

The batch page was also loaded after the dev-server restart to confirm the route still renders (screenshot evidence above).

---

## 9. Verification method and limitation

The browser session used the real application at `http://127.0.0.1:5173`. Because the hidden file input is not exposed by the accessibility snapshot as a usable ref, the fixture was supplied by constructing a real `File`/`DataTransfer` and dispatching the native `change` event on the input element. This means:

- the real React `onChange` handler ran;
- the real `FormData` was built and sent over HTTP to the live backend;
- the rendered result came from the real response.

It is **not** an operating-system file-picker test. Keyboard-only file selection and OS drag-and-drop were not automated, although the drop handler, the keyboard handler and the visible “Choose file” button all feed the same `handleFile` path.

No React runtime error appeared during the successful flows. The only console errors observed earlier were the deliberate `400` (header-only/corrupt) and `415` (unsupported type) responses from negative tests; these were expected and were rendered as UI messages.

---

## 10. Known UI limitations

1. `.xls` is listed in the upload copy but was not exercised; only `.csv` and `.xlsx` are verified.
2. The preview shows at most 15 rows per page and the returned preview itself is capped server-side; it is a sample, not the full sheet.
3. The results table paginates client-side at 25 rows; very large result sets are fully held in memory (bounded by the 5,000-row-per-sheet server limit).
4. The Markdown report is generated in the browser; it is a convenience artifact, not a signed audit record.
5. No dark-mode-specific or print stylesheet verification was performed for the batch page.
6. The chart components are CSS/SVG, not a charting library; they are intentionally dependency-free but have no zoom/tooltip interaction beyond native `title` text.
