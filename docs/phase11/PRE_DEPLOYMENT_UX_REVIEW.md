# Phase 11 Pre-Deployment UX Review

## Runtime review follow-up — 1 Nov 2026

The earlier entries below are retained as the historical record of the Windows dependency and runtime failures at that time. A later clean GitHub Actions run (`41297858536`, user-observed) passed backend tests, frontend tests, lint, TypeScript, production build, and immutable release packaging; its deployment jobs were skipped. This follow-up records a separate local runtime review and checks run against the current working tree. The current working-tree display fixes have not yet been included in that GitHub run, so they still require CI verification after an authorized push.

### Runtime and display findings

- Started the FastAPI backend at `127.0.0.1:8000` and Vite at `127.0.0.1:5173`. The frontend loaded backend-backed dashboard data. `/health`, `/v1/status`, dashboard snapshot, model list, Taiwan model detail/schema/evaluation endpoints returned HTTP 200. `/health` continued to report scoring as `not_validated`; `/v1/status` continued to mark production Indian lending as not validated.
- Manually reviewed all 11 navigation pages at 100% browser zoom on a 1440×900 desktop viewport, then checked narrow mobile layout at 390×844. Page content stayed within the viewport after the chart containers gained internal horizontal scrolling. The persistent horizontal navigation scroll is intentional. Batch Evaluation measured a 1px subpixel width excess on mobile; no material page-wide overflow was observed.
- End-to-end batch UI exercise used temporary synthetic-only inputs: CSV inspection identified two valid borrower rows and one invalid age row, retained duplicate-reference warnings, provenance and the rejected-row reason, and scored/exported the valid rows. CSV, XLSX, and validation-error CSV downloads were checked. A synthetic seven-sheet workbook was classified by sheet; selected valid sheets scored all four rows with worksheet/row provenance intact. No raw or restricted dataset was used.
- The real `/v1/score` contract check returned `not_validated` with `default_probability: null`. The demo workflow remained explicitly simulated. Taiwan model views retained research/demo warnings; LendingClub views remained historical. No validation claim was added.
- Small presentation fixes made during review: removed duplicated manual numbering in Risk Explorer's ordered list; separated the real-score result labels from values; added a separator between dataset status and source badge; constrained Data Discovery and Portfolio Intelligence chart wrappers to scroll internally on narrow screens. These are presentation-only changes.
- The browser console showed a Vite HMR WebSocket connection failure (`[vite] failed to connect to websocket`) during the local session. HTTP app rendering and backend-proxy requests worked; live-reload connectivity was not established in that session.

### Verification against current working tree

| Check | Command / method | Actual result |
|---|---|---|
| Frontend tests | `npm test` (from `frontend`) | **PASS** — 36 passed, 0 failed, 0 skipped. |
| Frontend lint | `npm run lint` (from `frontend`) | **PASS** — exit code 0. |
| TypeScript project build | `node node_modules/typescript/bin/tsc -b` (from `frontend`) | **PASS** — exit code 0. |
| Production frontend build | `npm run build` (from `frontend`) | **PASS** — TypeScript and Vite production build completed. |
| Backend API contract tests | `pytest tests/test_api_contract.py -v --tb=short` | **PASS** — 9 passed. |
| Full backend suite | `pytest tests/ -v --tb=short` | **UNVERIFIED locally** — Windows TestClient stalled at `tests/test_api_integration.py::test_health_endpoint`; interrupted. An additional run excluding that integration file stalled at `tests/test_batch_workflow.py::test_inspect_valid_csv_with_bom_and_reference`. Do not treat either interrupted run as a pass. |
| Backend/UI runtime | Live requests and synthetic CSV/XLSX workflow described above | **PASS for the exercised local flows**; this does not replace a complete backend test-suite pass. |
| Desktop and mobile visual review | 11 pages at 100% zoom; 1440×900 and 390×844 | **PASS with noted 1px Batch Evaluation mobile measurement and Vite HMR warning.** |
| Whitespace validation | `git diff --check` | **PASS** — exit code 0; Git reported only line-ending conversion notices. |

### Safety and remaining verification

The calibration artifact `models/calibration_model.joblib` was not edited; its previously recorded SHA-256 remains `6b94f41d3521c37e22d41b91e505006f1c737d022c214f803a5b9a057f185cdc`. No models were retrained, replaced, or promoted. Taiwan data/models remain research/demo only. `/v1/score` remains `not_validated` with a null probability. No deployment occurred.

The local frontend checks and reviewed UI paths pass, but the full Windows backend suite remains blocked by TestClient stalls, and the current display-only edits have not yet been covered by a new clean GitHub Actions run. The prior successful run is evidence for its own tested commit only. The current local source changes need to be reviewed, pushed to `phase11-final-verification`, and verified by a new Actions run before claiming clean-CI verification of these changes. Deployment remains out of scope.

**Historical review status at the time of the original entry: PARTIAL.** The UX and evidence changes below were implemented in the working tree, but complete frontend/backend checks and page-by-page runtime acceptance had not yet been completed because the Windows dependency installation and local test environment did not complete. No deployment or model promotion was performed.

## Changes made

- Prediction results now show estimated PD, its arithmetic non-default complement, the model's research classification and threshold comparison, calculation steps, a five-part context summary, submitted fields, calibration context and signed model attribution. The screen retains the Taiwan dataset's native NT$ context; it does not relabel those values as Indian rupees. If a local attribution is absent, the five-part explanation says so instead of implying that drivers exist.
- Positive-class attribution direction was checked against `src/inference/explanations.py` and `src/inference/predictor.py`: positive contribution sign is risk-increasing and negative sign is risk-decreasing. XGBoost contribution magnitudes are described as model-output units, not percentage points. The UI states attribution is not causation. KNN attribution remains labeled as neighbor attribution.
- Batch prediction now returns local contribution data and submitted features per successful row; the interface provides expandable row explanations and model/data limitations. CSV and XLSX exports include classification, comparison, driver summaries, dataset context and limitations. Existing columns remain in place. Summary cards identify scored/correction counts, mean/median PD, risk mix/distribution, and lowest/highest PD examples.
- Data Discovery uses evidence/readiness language (Research Ready, Available — Restricted Use, Evidence Gap, Synthetic / Demo, Needs Review, Source Unavailable). Dataset detail panels explain recorded findings, why evidence cannot advance, and the next evidence needed. Unavailable local source status takes precedence over research qualification.
- Portfolio segment and metric tables now use horizontal scrolling, visible dividers, padding, row shading/hover, sticky headers where supported, and numeric alignment. The metric table retains the saved values and headers for ROC-AUC, PR-AUC, prevalence, Brier, log loss, KS, Gini, precision, recall and F1.
- Model Performance Lab renders saved ROC points and saved calibration bins only when usable coordinate evidence exists. It includes a no-skill diagonal, axes and model/test context. The Taiwan threshold sweep is intentionally withheld: `scripts/generate_evaluation_artifacts.py` computes that sweep from locked-test labels (`y_test_arr`), and validation-split probabilities/labels are not present for a valid threshold sensitivity plot.
- Risk Explorer separates the unchanged real `/v1/score` safety check from an explicitly simulated future workflow. Its synthetic Indian-product example uses `Intl.NumberFormat('en-IN', INR)`; it neither calls the real score endpoint nor creates a score. Required India-specific evidence and governance prerequisites are listed.
- Monitoring and Architecture & Audit use future-state/evidence-gate labels. `/v1/score` remains `not_validated` with a null probability; Taiwan models remain research/demo only.
- The typography stylesheet retains Inter and its rendering settings without changing root/component font sizes. The original 14px root and compact component hierarchy remain in `frontend/src/index.css` and existing component CSS.

## Evidence and source currency

Taiwan monetary features and presets are labeled with Taiwan/native dataset context (NT$); they are not converted. LendingClub views retain their existing U.S.-dollar labels. INR formatting is used only for the synthetic Indian-product example. No exchange-rate conversion was introduced.

ROC and calibration coordinates come from the saved Taiwan evaluation artifacts served through the model evaluation endpoint. The curves are held-out test evidence, not India validation. The performance view does not plot the test-derived threshold sweep. LendingClub aggregate metrics do not become a fabricated LendingClub curve.

The source audit verified that `/v1/score` still returns `score_status: not_validated` and `default_probability: null`; no production scoring, model replacement, calibration replacement, retraining, or Indian borrower performance claim was introduced. The current SHA-256 of `models/calibration_model.joblib` is `6b94f41d3521c37e22d41b91e505006f1c737d022c214f803a5b9a057f185cdc`, matching the previously recorded value. No model or calibration artifact is included in this UX change.

## Verification record

| Check | Command | Actual result |
|---|---|---|
| Dependency-free frontend helper tests | `node --experimental-strip-types --test tests/assessment.test.ts tests/batch.test.ts` (from `frontend`) | **PASS** — 30 passed, 0 failed, 0 skipped. Covers assessment/complement/threshold language, 5W scope, attribution mapping, INR formatting, readiness/evidence helpers, batch CSV details and PD example selection. |
| Full frontend test command | `npm test` (from `frontend`) | **BLOCKED/FAILED** — 28 test cases passed, but the analytics test module could not resolve `react` after installation was interrupted. |
| Frontend dependency restore | `npm ci` (from `frontend`) | **FAILED** — Windows `EPERM` while trying to unlink `frontend/node_modules/@rolldown/binding-win32-x64-msvc/rolldown-binding.win32-x64-msvc.node`. A clean short-path attempt with `npm ci --offline` also failed because `vite@8.3.4` was not cached (`ENOTCACHED`). |
| Backend syntax check | `python -m py_compile src/api/batch_service.py tests/test_batch_workflow.py` | **PASS** — both changed Python files compile. |
| Backend tests | `pytest tests/ -v --tb=short`; focused attempt `pytest tests/test_batch_workflow.py -k export -q` | **UNVERIFIED** — full run reached `tests/test_api_integration.py::test_health_endpoint` and stalled in Windows TestClient; interrupted. Focused export run produced no test output before it was interrupted. No backend test pass is claimed. |
| Frontend lint | `npm run lint` | **BLOCKED** — command failed because `frontend/node_modules/oxlint/bin/oxlint` is missing after the failed dependency restore. |
| TypeScript project build | `npx --no-install tsc -b` | **BLOCKED** — command produced no output and was stopped after 15 seconds while the package was unavailable. `npm exec --offline -- tsc -b` confirmed `ENOTCACHED` for `tsc`. |
| Production frontend build | `npm run build` | **BLOCKED** — command failed because `frontend/node_modules/typescript/bin/tsc` is missing. |
| Whitespace/error check | `git diff --check` | **PASS** — no whitespace errors. Git emitted only line-ending conversion warnings. |
| Runtime and visual acceptance | Fresh backend/frontend processes and 11-page 100% zoom review | **NOT VERIFIED** — no fresh, working dependency install was available for this session. Therefore no console/API or visual-layout pass is claimed. |

## Follow-up source audit and launch attempt

On 1 Nov 2026, the requested helper tests were rerun: **30 passed, 0 failed, 0 skipped**. `git diff --check` passed again. Source inspection reconfirmed the score contract, positive-class SHAP direction, saved ROC/calibration provenance, and the test-derived threshold-sweep limitation. The calibration artifact SHA-256 still matches the recorded value above.

The intended UX implementation was committed locally on `phase11-final-verification` as `a3976f96b2624e62871fab56e0a2fe2f564acd0a`. No GitHub Actions result exists for this commit because `gh auth status` reports the configured GitHub token as invalid. Per the explicit authorization, only intended UX source, tests, and this review document were committed; pre-existing untracked files remain excluded. No push occurred.

The requested post-commit fresh launch was attempted. `npm run dev -- --host 127.0.0.1 --port 5173` failed because `frontend/node_modules/vite/bin/vite.js` is missing after the interrupted dependency restore. The backend process did not produce a health response; Windows loopback access returned a socket-permission error, and the attempted process was stopped. Earlier foreground Uvicorn startup emitted the existing Pydantic `schema_extra` warning and stalled before serving. The current frontend source could not be launched or rebuilt. The existing `frontend/dist` is not verified as containing this implementation and was not represented as current.

## Final completeness matrix

| Requirement | Implementation | CI | Runtime |
|---|---|---|---|
| Prediction assessment | PASS | PARTIAL | PARTIAL |
| Prediction math | PASS | PARTIAL | PARTIAL |
| 5W explanation | PASS | PARTIAL | PARTIAL |
| Attribution | PASS | PARTIAL | PARTIAL |
| Batch explanation | PASS | PARTIAL | PARTIAL |
| Batch exports | PASS | PARTIAL | PARTIAL |
| INR synthetic demo | PASS | PARTIAL | PARTIAL |
| Source currency preservation | PASS | PARTIAL | PARTIAL |
| Data Discovery statuses | PASS | PARTIAL | PARTIAL |
| Portfolio table | PASS | PARTIAL | PARTIAL |
| Model metrics table | PASS | PARTIAL | PARTIAL |
| ROC | PASS | PARTIAL | PARTIAL |
| Calibration | PASS | PARTIAL | PARTIAL |
| Threshold evidence decision | PASS | PARTIAL | PARTIAL |
| Simulated API | PASS | PARTIAL | PARTIAL |
| Monitoring | PASS | PARTIAL | PARTIAL |
| Architecture/Audit | PASS | PARTIAL | PARTIAL |
| Typography | PASS | PARTIAL | PARTIAL |

## Page-by-page acceptance

The requested 11 navigation pages were not manually reviewed in a fresh runtime. Component/source updates span prediction, batch, discovery, portfolio, model performance, risk exploration, explainability, monitoring and architecture. Executive overview and remaining dashboard page appearance still need visual acceptance at normal zoom. This source inspection is not a substitute for that review.

## Completeness checklist

- [x] Borrower Prediction detailed assessment (implementation present; runtime pending)
- [x] Prediction math and threshold comparison (helper tests pass)
- [x] Prediction 5W context (helper tests pass)
- [x] SHAP sign interpretation and attribution presentation (source audited; runtime pending)
- [x] Input value summary with readable feature names
- [x] Batch per-row explanation and portfolio summary
- [x] Batch CSV/XLSX export fields; frontend CSV behavior covered by helper test; backend integration pending
- [x] INR formatting for synthetic Indian-product display; Taiwan/LendingClub source currency retained
- [x] Data Discovery readiness statuses and evidence details
- [x] Portfolio segment table presentation
- [x] Model metric table presentation with existing values
- [x] ROC evidence decision and coordinate-based plot implementation
- [x] Calibration evidence decision and coordinate-based plot implementation
- [x] Threshold plot withheld because only test-derived sweep is saved
- [x] Risk Explorer simulated API is separate from real score contract
- [x] Monitoring future-state language
- [x] Architecture & Audit evidence roadmap
- [x] Plain-language metric descriptions/glossary added
- [x] Inter font family/rendering retained; prior root font sizing retained
- [ ] Complete frontend suite, lint, TypeScript check and production build
- [ ] Full backend tests and batch export integration tests
- [ ] Fresh runtime review of all 11 pages at 100% zoom; console/API inspection
- [x] Review documentation added; `git diff --check` passes

## Remaining blockers and next steps

1. Release the Windows lock on the native Rolldown binary or use a clean Linux/CI checkout with network access, then run `npm ci`, `npm test`, `npm run lint`, `npx tsc -b` and `npm run build` sequentially.
2. Run the backend suite and focused batch export tests in Linux/CI where the HTTP client does not stall; confirm API response serialization of row explanations and exports.
3. Restore local dependencies and loopback access, or use an authorized clean CI/runtime environment. Start fresh backend/frontend services and visually review all 11 pages at 100% zoom, then check browser console and API requests.
4. Resolve any failures discovered by those checks before treating this UX work as complete. CI and visual runtime acceptance remain required before a PASS classification.
