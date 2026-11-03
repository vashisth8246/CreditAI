# AC-3 implementation report

**Branch:** `ac3-commerce-execution`

**Base:** AC-2 commit `2006f6198ac179b88fb65e2aa28ef7ec183c679c`
**Status:** implemented locally; not committed or pushed. The clean dataset-backed exhibition scenario and full multi-resolution visual review remain incomplete.

## AC-1 / AC-2 review

| Capability | Existing implementation and finding | Classification / action |
|---|---|---|
| AC-1 purchase intent | Typed contracts in `src/agentic_commerce/schemas.py`; test requests use deterministic fixture values. | Contract and test fixture; no runtime borrower is supplied. |
| AC-1 status and journey | `/v1/agentic-commerce/status` and `/workflow` return a foundation status and static stage definitions. | Capability/status scaffold; no real tools execute. |
| AC-1 risk and affordability | Risk status is `not_validated`; no validated borrower inference is connected. | Research boundary; no model result fabricated. |
| AC-1 financing / transaction | Demo tool interfaces and simulation contracts exist, but do not connect to a lender, payment processor, or order system. | Explicit simulation interface; no real transaction. |
| AC-1 audit | Earlier workflow structures are contracts, not persistent runtime transaction history. | Partial; AC-3 adds process-local events. |
| AC-2 financing | `src/agentic_commerce/comparison.py` calculates reducing-balance payments with `Decimal`, evaluates only submitted rates, and selects by total interest then payment. | Deterministic calculation over user-entered simulated parameters. |
| AC-2 prior prefill | The AC-2 page had prefilled synthetic laptop/purchase/income assumptions. They were removed on this branch. All purchase, income, obligation, and rate fields now start empty and are labeled `USER INPUT`; rates are explicitly simulated. | Unacceptable as unlabeled runtime defaults; corrected. No test fixtures are presented as customer data. |
| AC-2 lender sourcing | No lender-rate source or real lender offer data was found. | Rates remain simulated assumptions; no lender names or live offers are shown. |
| AC-1/AC-2 tests | `tests/test_agentic_commerce.py` covers the earlier contracts, comparison, explicit human gate, and `/v1/score` safety. | Existing deterministic test fixtures only. |

No AC-1/AC-2 runtime fake borrower, customer identity, portfolio, or transaction history was retained in the AC page. AC-2's product and financial fields must come from the operator; the simulated rate parameters are not market offers.

## Data inventory and provenance

| Data source | Location / evidence | Rows and fields | Current use and limitation |
|---|---|---|---|
| UCI Taiwan Default of Credit Card Clients raw workbook | Expected at `Data/credit_default/default of credit card clients.xls` or `data/credit_default/default of credit card clients.xls`; optional override `CREDITAI_TAIWAN_DATASET_PATH`. No verified workbook exists in this AC-3 worktree. | Existing Phase 11 metadata records 30,000 rows, 25 columns, and target `default payment next month`; expected SHA-256 `21b3cf4e30878150ae8db9386780e23febb613921747dec9e59dccb32f6104d3`. | AC-3 reader requires a local workbook and verifies SHA, shape, fields, and unique IDs. Guarded acquisition was attempted from the existing official UCI archive, but the extracted workbook digest was `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933`, not the recorded digest. The fetch script rejected it and wrote nothing. Runtime correctly reports `unavailable`; no real record was used. The expected checksum was not changed. |
| Taiwan aggregate research artifacts | Tracked `models/uci_taiwan_eval.json`, `models/uci_taiwan_knn_eval.json`, `reports/phase11/*`, and `models/knn_model_metadata.json`. | Aggregate metrics, methodology metadata, and saved evaluation evidence; not borrower rows. | Legitimate research evidence, but not a source for purchase price, income, or a selected borrower. AC-3 does not convert these metrics into an individual risk estimate. |
| Frontend historical snapshots | Tracked `frontend/public/data/phase_9_dataset_inventory.json`, `phase_9_feature_inventory.json`, and `phase_9_lendingclub_summary.json`. | Historical aggregate/inventory payloads, not applicant-level observations. | Existing dashboard content only; not used as AC-3 borrower records. |
| LendingClub raw data | Not present in this worktree; full tests report the expected `Data/archive/accepted_2007_to_2018Q4.csv` is unavailable. | No raw rows available here. | Not used by AC-3. |
| AC-3 fields | Frontend form and submitted request. | Product label/category, INR price/down payment, tenure, monthly income context, obligations, and rate scenarios. | User-entered. These are not dataset-backed or model outputs. |
| Payment and comparison fields | `src/agentic_commerce/comparison.py`. | Financed principal, EMI, total repayment/interest, payment-to-income ratio, remaining income, preferred option. | Deterministically calculated from user inputs and simulated rates; not an approval or validated affordability decision. |
| Research record projection | `src/agentic_commerce/research_data.py`. | UCI reference, source row, credit limit in TWD, age, repayment status codes, statement balances, and payments. | Intended only for a verified Taiwan research workbook; known target column is never projected and no inference is performed. Unavailable until the raw workbook is installed and verified. |
| Audit / simulation IDs | `src/agentic_commerce/runtime.py`. | Stable UUIDv5 IDs derived from session and event/option. Event time is the actual action time. | No random borrower, offer, recommendation, or event identifier generation. Session ID uses a timestamp and monotonic page-local counter. |

### Field/value provenance shown by the AC-3 screen

| Field / value | Source | Provenance category | Real / calculated / simulated |
|---|---|---|---|
| Purchase label and category | Form submitter | USER INPUT | User supplied |
| Purchase price and down payment (INR) | Form submitter | USER INPUT | User supplied |
| Tenure, monthly income context, existing obligations | Form submitter | USER INPUT | User supplied; not sourced from a borrower record |
| Annual rate scenarios | Form submitter | SIMULATED PARAMETER | Hypothetical assumptions; not lender pricing |
| Taiwan borrower research fields | Optional checksum-verified workbook | DATASET-BACKED when available | Real historical UCI observations; unavailable in this checkout; target withheld |
| EMI, principal, total repayment, interest, ratios | Comparison service | DETERMINISTICALLY CALCULATED | Calculated from submitted values |
| Research-preferred scenario | Comparison service | DETERMINISTICALLY CALCULATED | Lowest total interest, then monthly payment; not credit approval |
| Confirmation and simulation record | Explicit user API/UI action | SIMULATED | Local research simulation; no external order/payment/lending action |
| Taiwan metrics | Tracked evaluation JSON/report artifacts | LEGITIMATE RESEARCH ARTIFACT | Aggregate research evidence only; not an individual score |

The Taiwan dataset is not Indian borrower data. No production lending validation is claimed. `/v1/score` remains `not_validated` with a null probability and no validated risk estimate.

## AC-3 implementation

- Added schemas for data availability, target-excluded Taiwan research records, session state, explicit confirmation, simulated transaction records, provenance, and audit events.
- Added an optional reader that searches only the documented locations or explicit path override, verifies the expected SHA-256 and dataset structure, and does not download or substitute data. Dataset absence is surfaced as unavailable.
- Added session creation, retrieval, and confirmation endpoints under `/v1/agentic-commerce`. A session remains `awaiting_confirmation` with no transaction until the request explicitly contains `decision: confirm_simulation` and a valid selected option.
- Repeated confirmation of the same option is idempotent. A different option after confirmation returns conflict; invalid options and missing sessions fail. Session/audit storage is process-local and is lost when the backend restarts.
- The simulated record includes the computed terms and a direct audit reference. It states that no external transaction was executed.
- Added AC-3 source/provenance messaging, blank user inputs, optional verified research-record selection, review/confirmation flow, completion state, and an audit-history page that reads actual session records. No automatic confirmation occurs.
- Stable event and simulation IDs are derived from session/event/option identity; no model, calibration, or prediction calculation was changed.

## Verification

### Backend

Command: `python -m pytest tests/ -v --tb=short` (run with local loopback access).
Result: **182 passed, 11 skipped, 0 failed** in 26.15 seconds; 57 warnings. Existing sklearn version warnings and Pydantic deprecations were left visible.

Skip reasons captured with `python -m pytest tests/ -q -rs --tb=no`:

- 3 Windows TestClient/HTTP-loopback cases are skipped by their existing platform guards; live HTTP verification was performed separately.
- 1 LendingClub raw integration test is skipped because the raw CSV is absent.
- 7 UCI Taiwan pipeline tests are skipped because the raw workbook is absent.

Focused command: `python -m pytest tests/test_agentic_commerce.py tests/test_agentic_commerce_ac3.py -q --tb=short`.
Result: **30 passed, 2 skipped, 0 failed**. The two are the AC-1 Windows HTTP cases.

Actual local HTTP check against the AC-3 Uvicorn server:

- `GET /v1/agentic-commerce/research-data` → 200, `status=unavailable` (no raw workbook).
- `POST /v1/agentic-commerce/sessions` with a test-only request fixture → `awaiting_confirmation`, two simulated options, four audit events, no transaction.
- `POST /sessions/{id}/confirm` → `simulation_completed`, six total events, `real_transaction_executed=false`.
- Repeating the same confirmation → `idempotent_replay=true`.
- Confirming an unknown session → HTTP 404.

These HTTP values were a test fixture, not a borrower or an exhibition dataset record. A full dataset-backed scenario was not possible because the verified UCI workbook is absent.

### Frontend

The main worktree's ignored `frontend/node_modules` was copied from AC-2 after confirming both worktrees have the same `package-lock.json` SHA-256. `npm ci --no-audit --no-fund` in that directory failed twice with Windows `EPERM` unlinking `@rolldown/binding-win32-x64-msvc/rolldown-binding.win32-x64-msvc.node`. One partial attempt removed React and caused a transient import failure; the ignored dependency tree was restored from AC-2. To verify the lockfile independently, a fresh temporary copy of the frontend source (excluding `node_modules` and `dist`) was created inside the worktree: clean `npm ci` succeeded there, then the test, lint, TypeScript, and build commands below all passed. The temporary copy was removed. The lockfile itself was not changed. The remaining local issue is reinstalling over the existing native binding in the main Windows worktree.

Using those installed dependencies:

- `npm test`: **41 passed, 0 failed, 0 skipped**.
- `npm run lint`: **passed**.
- `node node_modules/typescript/bin/tsc -b`: **passed**.
- `npm run build`: **passed**, Vite produced production assets under ignored `frontend/dist`.

### Runtime, UI, and safety

- Browser loaded the AC-3 worktree at `http://127.0.0.1:5179/`. An Executive Overview screenshot rendered, and the Agentic Commerce accessibility tree confirmed the source-unavailable notice, empty form fields, user-input labels, research-only warning, and no sample borrower. Important limitation: Vite's existing proxy points to port 8000, so that page was not confirmed against the temporary AC-3 backend on port 8011; the AC-3 API round trip was separately verified directly over HTTP. The Browser tool reported concurrent user input before a subsequent screenshot/navigation action, so the AC-3 page was not visually inspected by screenshot.
- Visual review at 1366×768, 1440×900, and 1920×1080 was **not completed**. No visual PASS is claimed.
- `tests/test_agentic_commerce.py::test_score_endpoint_remains_safety_locked_with_valid_dummy_request` passed in the full suite. Scoring code was not changed.
- SHA-256 of `models/calibration_model.joblib` is `6b94f41d3521c37e22d41b91e505006f1c737d022c214f803a5b9a057f185cdc`, matching the required value and the AC-2 baseline. It was not modified.
- SHA-256 of the separate `models/calibration_knn_model.joblib` is `6d917f0d918a21a289fb0efc73ff510862cc22e5fc29bd890c6929558c4cdebc`, matching its AC-2 baseline. It was not modified.
- No model was retrained or replaced; no Taiwan or synthetic model was promoted; scikit-learn warnings were not suppressed.
- `git diff --check` passed before this report was added; it is rerun in final checks below.

## Remaining limitations and next steps

1. Resolve the UCI source/version discrepancy and obtain a workbook whose bytes match the recorded SHA-256 (or have the research owner approve and independently validate a new source/version before changing metadata). The guarded fetch rejected the current archive and wrote no file. Do not bypass hash verification or add raw data to Git.
2. Re-run the application against the AC-3 backend and complete the borrower-record context flow only after that verification. Commerce assumptions must still be entered by a human.
3. Complete visual inspection of Agentic Commerce and Audit at 1366×768, 1440×900, and 1920×1080, including the empty, comparison, confirmation, completion, and audit states.
4. If a local reinstall is needed in the primary Windows worktree, resolve the native binding `EPERM`; clean install and all frontend checks passed from a fresh temporary source copy.
5. The session/audit store is in memory; sessions disappear on backend restart. Persistent audit storage remains future work if cross-restart history is required.
6. Do not claim Indian borrower validation, production readiness, a real lender offer, or a real transaction. Keep `/v1/score` `not_validated`.

**Source control:** no files staged; no commit, push, merge, release packaging, or deployment performed. Commit/push are withheld pending clean dependency installation, dataset-backed runtime, and required visual review.

## Final AC workflow repair and verification — 3 Nov 2026

This section supersedes earlier statements above that the dataset was unavailable, the runtime was not connected to the AC-3 backend, and browser acceptance was incomplete. Those earlier statements remain as historical context for the first AC-3 pass.

### Root cause and changes

The existing browser runtime was pointed at the Vite proxy's fixed `127.0.0.1:8000` target. That listener served a stale API: `/health` and the schema route responded, while AC routes such as `/v1/agentic-commerce/research-data` returned 404. AC-1 therefore did not reach the current AC-3 session routes. The purchase form also submitted directly into the session path, skipping a structured research-profile step.

The proxy now reads `CREDITAI_API_PROXY_TARGET`, defaulting to `http://127.0.0.1:8000`. The verified runtime used this branch's API on port 8011 and the frontend on port 5180, with the proxy pointed to 8011. No existing process on port 8000 or 5173 was stopped or modified.

The Agentic Commerce page now has a continuous purchase-intent → research-profile → comparison/recommendation → explicit confirmation → simulation/audit flow. The frontend loads the existing `uci_taiwan_xgb` feature schema from the connected API and renders its exact 23 required raw fields. Manual fields start empty; the client checks required values, integer values, categorical values and numeric ranges. The backend validates the same profile through the existing prediction service and returns a Taiwan research-only estimate with its limitations. The research output is shown separately and is not used by the financing calculation or recommendation.

When a verified record is selected, the server fetches the same row by its reference and runs research inference from its 23 raw features. Target values are never included. Dataset-backed fields are read-only in that mode so displayed values cannot diverge from the record used by the server. The session and audit response distinguish dataset input, model output, simulated rates and calculated payments. A retry control lets the operator recheck dataset availability after a transient backend start-up failure.

### Files in this AC branch change set

- `frontend/src/agenticCommerce.ts` — connected steps, schema-driven profile, provenance, dataset selection, output, confirmation and audit state.
- `frontend/src/App.css` — research-profile grid, select controls, buttons and output presentation.
- `frontend/vite.config.ts` — configurable local API proxy target.
- `frontend/tests/agenticCommerce.test.ts` — empty AC-1 start and current-schema input validation regression coverage.
- `src/agentic_commerce/schemas.py` — complete raw feature projection, optional input profile and typed research output/provenance.
- `src/agentic_commerce/research_data.py` — exposes all 23 target-free raw features for verified rows.
- `src/agentic_commerce/runtime.py` — performs server-side research inference and records the research event without using it in financing calculations.
- `src/api/agentic_commerce.py` — clear validation/model artifact error mapping.
- `src/api/app.py` and the rest of the AC-3 route implementation were already present in this branch's uncommitted AC work before this final repair; they remain part of the intended AC branch change set and were preserved.
- `tests/test_agentic_commerce_ac3.py` — full-schema projection and separation of research inference from the comparison.
- `reports/ac3_implementation_report.md` — this final verification addendum.

No unrelated Batch Evaluation logic was edited. No model or calibration artifact was modified, no model was retrained, and no scikit-learn warning was suppressed.

### Dataset provenance

The raw workbook exists in the original repository at `F:\NUV ACD\All SEM\7th Sem\ML&DS\New folder (3)\CreditAI\Data\credit_default\default of credit card clients.xls`. The `Data` and `data` paths resolve to the same Windows file. Its computed SHA-256 is exactly `21b3cf4e30878150ae8db9386780e23febb613921747dec9e59dccb32f6104d3`, matching Phase 11 metadata. It contains 30,000 rows; the verified record response contains the 23 expected raw features and omits `default payment next month`.

The raw workbook remains outside this branch and is not committed. The verified runtime received it through `CREDITAI_TAIWAN_DATASET_PATH`; on a clean checkout, manual research input remains available without it, while dataset mode remains unavailable until the same SHA-verified workbook is provisioned locally.

### Test results

- `python -m pytest tests/ -v --tb=short` — **183 passed, 11 skipped, 0 failed; 57 warnings; 25.84 seconds**. The three Windows TestClient tests are intentionally skipped due to the existing Windows HTTP limitation. One raw LendingClub row reconciliation test is skipped because `Data/archive/accepted_2007_to_2018Q4.csv` is not present. Seven UCI pipeline integration tests are skipped because the raw workbook is not in the branch's normal `Data`/`data` location. Other HTTP integration tests passed when run with local access enabled. Warnings, including scikit-learn artifact-version warnings, were left visible.
- `python -m pytest tests/test_agentic_commerce.py tests/test_agentic_commerce_ac3.py -v --tb=short` — **31 passed, 2 skipped, 0 failed**.
- `npm test` — **43 passed, 0 skipped, 0 failed**.
- `npm run lint` — **passed**.
- `node node_modules/typescript/bin/tsc -b` — **passed**.
- `npm run build` — **passed**.
- Actual `POST /v1/score` through the connected local frontend proxy — `score_status=not_validated`, `score_type=none`, `default_probability=null`, `validated_risk_estimate=false`, and `model_version=null`.
- Calibration SHA-256 — `6b94f41d3521c37e22d41b91e505006f1c737d022c214f803a5b9a057f185cdc`; unchanged.

### Browser acceptance

An isolated headless Chrome session loaded the actual Vite frontend at `http://127.0.0.1:5180/`, connected through the configured proxy to this branch's API at `http://127.0.0.1:8011/`.

- Manual flow: entered a clearly test-only purchase fixture; AC-1 advanced to AC-2; the model-schema form rendered 23 empty fields; all 23 test values were then entered; the session returned a research output and three calculated simulated options; a selected option required explicit confirmation; the simulation completed with `real_transaction_executed=false`; the audit page displayed seven factual events.
- Verified-dataset flow: selected `UCI-TW-00001` (source row 1); the form displayed 23 `DATASET` fields and withheld the historical target; the API response showed `model_inference_performed=true`, 23 feature keys, no target key, and the research model output; explicit confirmation completed a simulation with `real_transaction_executed=false` and seven audit events.
- Empty/manual, dataset-filled, result/completion and audit screens were rendered and visually inspected. The empty form was visually checked at 1440×900, 1366×768 and 1920×1080. It contained 23 blank fields and had no horizontal document overflow at any size. The existing design remains usable at normal desktop sizes.
- Test values were used only for browser acceptance; they are not borrower evidence or research findings.

### Current limitations and source control

- The raw Taiwan dataset is not tracked and must be provisioned by path for dataset mode on a new checkout. Manual mode does not require it.
- Taiwan model outputs remain research-only and not validated for Indian borrowers. `/v1/score` remains locked as `not_validated`; no production lending readiness or real lender offer is claimed.
- Sessions and audit events remain process-local/in-memory and are lost when the API restarts.
- No package or release ZIP was built; no deployment occurred.
- No merge or Azure action occurred.
- The AC change set remains on `ac3-commerce-execution`; no files were staged while this report section was written. Commit/push, if performed under the task's explicit AC-3 instruction, must include only this reviewed branch change set and must not merge or deploy.
