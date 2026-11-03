# CreditAI Agentic Commerce AC-2 Implementation Report

## AC-1 repository review

AC-1 remains a separate research/demo foundation. Its typed purchase, financing, recommendation, confirmation, simulation, and audit contracts are defined in `src/agentic_commerce/schemas.py`; validation rejects unknown input fields and the purchase-intent contract contains no borrower name, address, account number, or borrower ID. `src/agentic_commerce/tools.py` is a protocol only. `src/agentic_commerce/workflow.py` is a static future state graph. `src/api/agentic_commerce.py` exposes read-only status and workflow metadata. `frontend/src/agenticCommerce.ts` previously rendered a planned-stage foundation and an honest empty audit page. Existing contract and frontend tests cover those boundaries.

| Journey capability | Implementation | AC-1 state |
|---|---|---|
| Purchase-intent typed contract | `schemas.py` | Complete contract; no submission endpoint |
| Affordability / risk research | Typed result schemas and protocol only | Placeholder; no calculation or validated risk output |
| Financing options / costs | Typed schemas and protocol only | Placeholder; no offer discovery or calculation |
| Comparison / recommendation | Typed schemas and protocol only | Placeholder; no ranking or recommendation |
| Human confirmation | Contract and state transition guard | Contract only; no UI or execution endpoint |
| Simulated transaction | Contract and gated state | Not implemented |
| Audit event | Typed contract | Not implemented; no persistent event store |
| Status / planned journey | Read-only endpoints and UI | Complete for AC-1 foundation metadata |

## AC-2 scope and design

AC-2 adds a deterministic commerce-intelligence layer: one endpoint accepts the existing `PurchaseIntent` shape plus two or three distinct illustrative annual-rate assumptions, calculates reducing-balance payment estimates, compares total interest, and returns a research-preferred scenario with reasons. The assumptions are clearly described as examples, not lender pricing. The UI uses the existing CreditAI navigation and green panel styles, lets the presenter edit purchase and rate inputs, and renders calculated alternatives, a comparison bar, a research recommendation, and the human-confirmation boundary.

The API is `POST /v1/agentic-commerce/compare`. Monthly payments use the standard reducing-balance EMI formula, with a zero-interest branch and currency rounding. Aggregate total repayment cannot fall below principal because monthly rounding can otherwise undershoot principal by cents. The recommendation selects the option with the lowest estimated total interest; it does not rank borrower risk or infer eligibility. Payment-to-income and remaining-income values are descriptive only.

AC-2 does not add an agent runtime, persistent audit storage, a confirmation action, transaction simulation, real lender data, a credit decision, or model scoring. The result’s event summary is generated from the actual request and explicitly says that nothing was persisted. The UI marks affordability/risk research as “Not assessed”; confirmation, simulation, and audit remain future stages.

## Files changed

- `src/agentic_commerce/schemas.py`
- `src/agentic_commerce/comparison.py` (new)
- `src/api/agentic_commerce.py`
- `src/api/app.py`
- `tests/test_agentic_commerce.py`
- `frontend/src/agenticCommerce.ts`
- `frontend/src/App.css`
- `frontend/tests/agenticCommerce.test.ts`
- `reports/ac2_implementation_report.md` (this report)

## Safety and boundaries

- `/v1/score` remains `not_validated`, `score_type="none"`, `default_probability=null`, `validated_risk_estimate=false`, and `model_version=null`.
- Taiwan artifacts and predictions remain research/demo-only; AC-2 does not call the model registry or inference routes.
- No model or calibration artifacts were modified. The required SHA-256 for `models/calibration_model.joblib` remains `6b94f41d3521c37e22d41b91e505006f1c737d022c214f803a5b9a057f185cdc` (recheck after final verification).
- Existing scikit-learn warnings remain visible.
- No Azure action or release packaging was performed.

## Verification

| Check | Result |
|---|---|
| AC-2 backend unit / contract tests | 22 passed; 2 HTTP tests skipped on Windows |
| Full backend suite | 174 passed, 11 skipped, 57 warnings in 30.58 seconds (`python -m pytest tests/ -q -rs`, with normal local socket access) |
| Frontend tests | 40 passed, 0 failed, 0 skipped |
| Frontend lint | Passed after removing an impure render-time identifier |
| TypeScript (`node node_modules/typescript/bin/tsc -b`) | Passed |
| Frontend production build | Passed (Vite 8.3.4) |
| Live AC-2 API | Passed local POST to `/v1/agentic-commerce/compare` on port 8002; returned three deterministic scenarios and research-only flags |
| Browser runtime | AC-2 workspace opened, submitted defaults through the live API, and rendered the three calculated options and recommendation; stage statuses were corrected after observing that risk research must remain “Not assessed” |
| `/v1/score` direct contract | Passed in AC-1/AC-2 contract test |
| Calibration SHA | Rechecked after implementation: `6b94f41d3521c37e22d41b91e505006f1c737d022c214f803a5b9a057f185cdc` |
| `git diff --check` | Passed |

The first sandboxed Windows test attempt stalled at the existing `TestClient` `/health` call. Re-running with normal local socket access completed the entire suite. Three route-over-HTTP tests are skipped on Windows (two AC status/compare tests and one existing API integration test); one LendingClub raw-dataset integration test and seven Taiwan raw-dataset integration tests are skipped because those datasets are intentionally absent. The new compare handler and contract tests passed directly, and an actual local Uvicorn POST succeeded on port 8002. GitHub Linux CI should exercise the platform-skipped route tests; no GitHub run has yet verified AC-2.

## Remaining limitations

- Rate values are illustrative assumptions, not sourced lender offers or market quotes.
- Payment-to-income and remaining-income values do not establish affordability or eligibility.
- No validated risk information is connected to this feature.
- Human confirmation, simulated transaction, and durable audit remain for a later phase.
- Browser review was performed at the available in-app browser viewport; fixed 1366×768, 1440×900, and 1920×1080 viewport checks were not available.
- Azure deployment and packaging are intentionally deferred.

## Recommended AC-3

**Objective:** add an explicit human confirmation and rejection flow for a selected research scenario, with append-only audit events, while stopping before any real transaction. Inputs should be the AC-2 comparison identifier and a user-selected option; outputs should be an explicit confirmation/rejection state and minimized audit events. No real payment, purchase, lender integration, or credit approval should be possible.
