# CreditAI final localhost acceptance

## Runtime

- Branch: visitor-money-health. Starting commit: 8687a84abca73075a8db97d29f583acdb999561a. The isolated checkout was clean before verification.
- Backend: FastAPI src.api.app:app, Uvicorn listener PID 19976 on 127.0.0.1:8000. Python launcher PID 25404. Working directory is the isolated checkout.
- Frontend: Vite PID 24304 on 127.0.0.1:5173, launched from the isolated frontend directory. Vite proxies /v1 and /health to http://127.0.0.1:8000.
- Frontend http://127.0.0.1:5173/ and visitor experience http://127.0.0.1:5173/money-health. Backend health http://127.0.0.1:8000/health.
- Existing project virtual environment: Python 3.11.9, FastAPI 0.143.0, Uvicorn 0.54.0, scikit-learn 1.9.1, SHAP 0.51.0, XGBoost 3.2.0 and openpyxl 3.1.5. Existing frontend: Node 24.13.1, npm 11.8.0 and Vite 8.3.4. No environment reinstall was needed.

## Automated and live checks

- Frontend: 62 passed, 0 failed, 0 skipped. Test, TypeScript, lint and production build exit codes were all 0. Vite retains the lazy PDF bundle size advisory.
- Full backend: 184 passed, 0 failed, 11 skipped, 0 deselected and 0 blocked. Exit 0. The previous Windows Application Control import failure did not reproduce in this run.
- Comparison backend run excluding the two previously blocked modules: 168 passed, 0 failed, 10 skipped. Exit 0. Focused API, Batch Evaluation and Agentic Commerce: 80 passed, 0 failed, 3 skipped. Exit 0.
- Frontend root and /money-health returned 200 HTML and /src/main.tsx returned 200 JavaScript. Direct and proxied /health, /v1/status, /v1/models and /v1/build returned 200 with matching payloads. Health reported ok and scoring not_validated. Status reported backend connected, two registered models and research inference ready. Dashboard snapshot returned 200 through both origins.
- The proxy carried a successful 200 Taiwan borrower prediction with calibration, six SHAP contributions and explicit limitations on Indian applicability. Synthetic CSV and two-sheet XLSX inspection returned 200. Batch scoring, analysis, and exports were covered by the backend suite. Live Agentic Commerce comparison returned 200, research_simulation and three options. AC-1/2/3 and audit behavior were also covered by the suites.
- The browser rehearsal sent a valid synthetic POST /v1/score through Vite. HTTP 200 returned not_validated, none, null probability, false validation and null model version.
- Calibration SHA-256 matched 6b94f41d3521c37e22d41b91e505006f1c737d022c214f803a5b9a057f185cdc.

## Browser and privacy

Headless Edge opened all 13 research sidebar sections and the Money Health route with a hard refresh. The navigation and reload check reported no uncaught JavaScript exceptions or HTTP responses with status 400 or higher. The visitor harness covered all four sample and personal profiles, calculations, cleared forms, a lower-income scenario, added EMI, PDF downloads and the return to CreditAI. Initial layout overflow checks covered 320, 375, 390, 430, 1366, 1440 and 1920 pixels. Populated personal dashboards and passports were checked at the four mobile widths.

The browser created all three challenge types across four profiles, verified example plans started with no actual entries, and checked consent, persistence across refresh, multiple challenges, actual entries, withdrawal, milestones, editing, deletion, JSON export and restore, independent browser contexts and Clear All Data. Invalid JSON and schema rejection were covered by unit tests. Data stays in the tab until consented browser-local saving. Independent browser contexts did not share state, and URL queries stayed empty. Backups are local files and there is no cross-device synchronization.

## Downloaded PDFs

| Report | Pages | Key value checked |
| --- | ---: | --- |
| Student Money Health | 3 | ₹1,200.29 balance and four-month purchase projection |
| Working Professional Money Health | 3 | ₹14,000 baseline and ₹8,000 with additional EMI |
| Freelancer Money Health | 3 | ₹15,000 baseline |
| Other Money Health | 3 | −₹3.25 balance with zero funds |
| Savings Goal Passport | 1 | ₹550.50 actual contribution and ₹449.50 remaining |
| Spending Reduction Passport | 1 | ₹120.25 actual against ₹700 limit |
| Emergency Buffer Passport | 1 | ₹450.75 contribution, ₹50.25 withdrawal, ₹400.50 balance and 0.40 months coverage |

Downloaded reports were parsed for labels, amounts, provenance and actual vector chart operators and rendered with Poppler for visual review. The financial reports include 5W1H, field registers, formula substitutions and What-If comparisons. Passport reports show actual timeline entries, calculated progress, milestones and page numbers. Local links are labeled Local rehearsal link. All four example financial PDFs also passed text extraction, and the print fallback generated four pages.

The Emergency Buffer report initially placed its final link on an otherwise nearly empty page. Passport report spacing was tightened and the link heading kept with its content. The browser harness now waits for the new document after hard reload instead of allowing an old DOM to satisfy readiness.

## Readiness and scope

The local frontend and backend are ready for user acceptance. Both processes were left running. This rehearsal used desktop Edge with emulated viewports. Physical phone interactions and device-specific file saving remain unverified. The suite has 11 backend skips and emits compatibility warnings for estimators serialized under scikit-learn 1.9.0. The live Taiwan research inference and SHAP response worked under the installed 1.9.1 runtime. Azure readiness has not been certified by this localhost rehearsal.
