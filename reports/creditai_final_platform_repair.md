# CreditAI final platform repair

Branch `visitor-money-health`. Starting commit `6681baf63f16c2a60838fc3fa308a7beec04d928`. The existing predeployment audit was untracked when work began and remains separate.

## DecisionProof diagnosis and recovery

Before editing, `GET /v1/research/decisionproof/scenarios` on localhost ports 5173, 8000 and 8768 returned HTTP 404 and `{"error":{"code":"invalid_request","message":"Not Found"}}`. The same request on 8769 returned HTTP 200 with the synthetic catalog. The old process logs `final-api.log` and `guardian-final-api.log` recorded the route-level 404. Vite's default `/v1` proxy targeted 8000. The running FastAPI processes on 8000 and 8768 predated route registration, while the process on 8769 served the registered router ahead of the static-file mount. This reproduced the failure locally and isolated it to the backend version serving the request.

The two stale listeners were replaced with FastAPI from this checkout. Ports 5173, 8000, 8768 and 8769 then returned 200 for the catalog. DecisionProof uses the shared API client with the configured `VITE_API_BASE_URL` or same-origin routing and the existing Vite proxy. The page presents a real Retry and expandable HTTP diagnostics when the catalog fails. The server's response remains the source of scenarios, evidence, verification options and analysis. The local failure does not establish the status of any Azure release.

In development, start FastAPI from this checkout on port 8000 with `python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload` using the project Python environment. Run Vite from the same checkout. For another local API listener, set `CREDITAI_API_PROXY_TARGET` before starting Vite. For a same-origin production rehearsal, build the frontend and start FastAPI from this checkout. Confirm the catalog returns nine cases before a demo.

The prominent Load Example button applies the selected synthetic catalog case, resets its policy to ₹20,000 residual and 40% payment-to-income at base cost, and runs the backend. Policy edits clear stale findings and report access until the next analysis. Edge rehearsed all nine presets, the conflicting-income residuals of ₹10,000 and ₹35,000, the four-unit income check, the strategy comparison, benchmark, refresh, and a forced catalog 404 followed by a successful Retry. The downloaded report matched the live API replay ID `c7960097be6ef990c86d6f39d7244031d8df8ccd6d755cbbd9ab483b8673c801`.

## Flexible borrower history

Each record groups a reporting period, repayment status, bill and payment in one editor. Users can add, edit, remove, load a six-month history example and clear the history independently of borrower profile fields. Destructive changes involving entered values ask for confirmation. The editor shows entered and complete counts, missing periods, field errors and the selected research window. Valid repayment codes range from −2 to 9. Negative bill balances and zero payments are accepted within the existing schema.

| Entered months | Compatibility behavior |
|---|---|
| 2 or 3 | Store in the current form and explain missing history. Submission produces no inference request. |
| 6 | Require six valid consecutive months. Send the original 18 monthly features plus the five profile features through the existing Guardian endpoint. |
| 12 | Show all 12. Select only the latest six consecutive complete months. Older rows remain visible for context. |
| Gap, duplicate period, or invalid selected value | Identify the issue and gate the request. No dates or monetary values are imputed. |

The positional mapping is newest to oldest into the September–April 2005 reference slots `PAY_0, PAY_2, PAY_3, PAY_4, PAY_5, PAY_6`, with matching numbered bill and payment slots. Later calendar periods use a research-only positional window. They carry no current-borrower validation. Six and twelve records with the same selected window returned the same displayed 8.2% research PD. Edge captured the 23-field payload, Guardian output and SHAP contributions. The insufficient-history UI provides a local readiness finding with no probability.

## UI, responsiveness and performance

Hash routing now synchronizes sidebar navigation, direct links, refresh and browser history. Monthly rows use responsive cards, larger inputs, visible remove and clear controls, field error associations, and predictable focus after adding or confirming. Scoped entry and results animations respect reduced motion. At 320px, the root's previous 320px CSS minimum overflowed the 305px content area in Edge with a vertical scrollbar. The narrow breakpoint now allows the root to shrink.

Edge checked both repaired pages at 320, 375, 390, 430, 768, 1366, 1440 and 1920 pixels without page-wide horizontal overflow. A wide evidence table scrolls within its own region. The two repaired workspaces now load on demand. The main production JavaScript chunk decreased from 508.42 kB to 456.59 kB minified. The on-demand PDF engine and fonts still exceed Vite's 500 kB warning threshold. Single local HTTP samples returned 200 in 16 ms for the dashboard HTML, 10 ms for Money Health HTML, 13 ms for the catalog, 11 ms for analysis and 40 ms for the benchmark. These timings characterize this local run only.

Edge keyboard events activated Add Month, moved focus to the date, opened removal confirmation and canceled it. Tab moved from the DecisionProof scenario selector to Load Example, and browser Back returned to the prediction route. Emulated reduced motion disabled the new entry and scenario animations.

## Regression evidence

- Backend suite, 201 passed, 0 failed, 11 skipped. Three skips concern the Windows HTTP harness, seven concern the Taiwan workbook fixture path, and one concerns missing raw LendingClub data. Live HTTP and Edge exercised key routes outside that harness.
- Frontend suite, 72 passed, 0 failed, 0 skipped. Lint, TypeScript, production build and Git whitespace checks passed.
- DecisionProof catalog, analysis and evaluation returned HTTP 200 on 8000 directly, 5173 through Vite, and 8769 with the built frontend. The catalog contained nine cases, the conflict analysis contained two states, and the benchmark contained three cost profiles. Live and unit checks covered the public score contract and DecisionProof error status handling.
- Browser research audit checked overview rendering, dataset search and details, portfolio filters, model and split selection, Guardian lab charts, scoped Risk Explorer and Explainability states, Monitoring and Architecture. All 14 sidebar destinations were visited. The research audit reported no uncaught JavaScript or HTTP errors. The separately forced 404 was deliberate.
- Agentic Commerce ran from the synthetic exhibition example through research comparison, explicit confirmation, simulated execution and seven actual audit events.
- Batch scored CSV and two-sheet XLSX. The displayed PDs were 8.21% for `A-OK` and 14.13% for `B-OK`. The corresponding complements were 91.79% and 85.87%, with Low risk for both. `A-BAD` retained its EDUCATION validation error and no PD. Both prediction export formats matched the displayed sheet, row, reference, status and available values. The validation downloads retained row 3, the EDUCATION error and the correct sheet identity, CSV or Alpha. The original 23-column batch schema was used.
- Money Health covered the four samples and all four personal profiles, charts, Clear All, scenario changes and freelancer lower-income analysis. The browser downloaded eight valid financial PDFs with 3–4 pages and generated a four-page print fallback. Money Challenge exercised savings, spending reduction and emergency goals. Money Passport covered consent, actual entries, edit/delete, milestones, refresh, JSON backup restore, browser-context isolation and Passport PDFs.
- The production-style server returned 200 for `/`, `/money-health` and all entry assets. Edge loaded the lazy workspace assets while completing the same-origin workflows.

Public `/v1/score` returned `score_status: "not_validated"`, `score_type: "none"`, `default_probability: null`, `validated_risk_estimate: false`, and `model_version: null`. Calibration SHA-256 `6b94f41d3521c37e22d41b91e505006f1c737d022c214f803a5b9a057f185cdc`. Rollback ZIP SHA-256 `ed8f4d22ee478d6f1d43f6a1ec8ba7c4257041ce70d8e2337a023b6ba389900d`. Rollback manifest SHA-256 `e4c0bd79a5aa3e5aa1aba47e789b1c739a989ee0ae4ed7e21dc602881c7dbd53`.

## Local screenshots and exports

The linked evidence was captured in Edge from the running app. Generated files are stored locally in the worktree's ignored browser output folder.

| Area | Evidence |
|---|---|
| History | [Two months](../frontend/build/platform-repair-final/history-2.png) · [Six months](../frontend/build/platform-repair-final/history-6.png) · [Twelve months](../frontend/build/platform-repair-final/history-12.png) · [Mobile history](../frontend/build/platform-repair-final/mobile-history.png) |
| Inference | [Research prediction and SHAP](../frontend/build/platform-repair-final/prediction.png) · [Confidence Guardian](../frontend/build/platform-repair-final/guardian.png) |
| DecisionProof | [Loaded example](../frontend/build/platform-repair-final/decisionproof-example.png) · [Analysis](../frontend/build/platform-repair-final/decisionproof-analysis.png) · [Benchmark](../frontend/build/platform-repair-final/decisionproof-benchmark.png) · [Downloaded report](../frontend/build/platform-repair-final/decisionproof-conflicting-income.md) |
| Dashboard | [Desktop](../frontend/build/platform-repair-final/desktop-dashboard.png) · [Mobile](../frontend/build/platform-repair-final/mobile-dashboard.png) |
| Commerce and batch | [Commerce completion](../frontend/build/repair-batch-1793800297361/commerce-completion.png) · [Audit trail](../frontend/build/repair-batch-1793800297361/commerce-audit.png) · [XLSX results](../frontend/build/repair-batch-1793800297361/gate.xlsx-results.png) |
| Visitor exports | [Print fallback](../frontend/build/final-verification-1793800512346/print-fallback.pdf) · [Working professional financial PDF](../frontend/build/final-verification-1793800512346/personal-Working.pdf) · [Emergency Passport](../frontend/build/final-verification-1793800512346/emergency-passport.pdf) |

## Files and release state

- `frontend/src/App.tsx`, `frontend/src/App.css` — hash routing, deferred workspaces and narrow viewport behavior.
- `frontend/src/PredictionWorkspace.tsx`, `frontend/src/MonthlyHistoryEditor.tsx`, `frontend/src/monthlyHistory.ts`, `frontend/src/monthlyHistory.css` — editor, validation, form state, research compatibility and presentation.
- `frontend/src/DecisionProof.tsx`, `frontend/src/decisionProof.css`, `frontend/src/api.ts` — shared routing, failure recovery, examples and research output.
- `frontend/tests/monthlyHistory.test.ts`, `tests/test_decisionproof_api.py` — exact input mapping, readiness, route registration and endpoint contract tests.
- `reports/creditai_final_platform_repair.md` — implementation and verification evidence.

The repair commit is the `visitor-money-health` commit that adds this report. Verify the local commit with `git log -1 -- reports/creditai_final_platform_repair.md` and compare it with `git ls-remote origin refs/heads/visitor-money-health`. The local build is suitable for the exhibition rehearsal and a separate release audit. Deployment remains a separate gate. Browser findings apply to the interactions and viewport checks documented above, with no heap profiling or independent production environment certification.
