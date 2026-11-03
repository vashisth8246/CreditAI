# My Money Health implementation

The CreditAI frontend opens the visitor experience at `/money-health`. The FastAPI static deployment serves the same application entry at that path. Visitors can return to the research dashboard through Explore Full CreditAI.

- `frontend/src/MoneyHealthPage.tsx` renders forms, charts, scenarios and print report content.
- `frontend/src/moneyHealthPdf.ts` composes the direct-download A4 report with pdfmake, bundled fonts and vector charts.
- `frontend/src/moneyHealth.ts` holds the input schema, examples, exact paise calculations and presentation data.
- `frontend/src/moneyHealth.css` defines responsive and A4 layouts.
- `frontend/tests/moneyHealth.test.ts` and `frontend/tests/moneyHealth.browser.mjs` exercise calculations and the connected app.
- `frontend/src/App.tsx`, `frontend/package.json` and `src/api/app.py` integrate navigation, tests and production routing.

## Inputs and calculations

The field definitions document labels, help, required status, example values and aggregation rules. Student fields cover allowance, work income and personal spending. Professional fields cover take-home pay, additional income, housing, household and transport. Freelancer fields cover typical and lower-month income plus personal spending and business costs that have yet to be deducted. The other profile covers support, other funds and essential and discretionary spending. Each profile accepts accessible savings, current debt payments and a monthly savings goal.

INR strings accept up to ten whole digits and two fractional digits. Sums and differences use integer paise. The engine adds funds and sums distinct expense categories. Outflow adds debt to expenses and balance subtracts outflow from funds. Expense and debt ratios divide by positive funds. Coverage divides accessible savings by positive outflow. Ratios display to two decimal places. Monthly savings feasibility compares the goal with balance. Purchase timelines divide the amount still needed by an explicit positive contribution and round up. Blank optional amounts remain unavailable in the register and contribute zero to sums.

| Example | Funds | Expenses | Debt | Balance |
| --- | ---: | ---: | ---: | ---: |
| Student | ₹5,000 | ₹3,800 | ₹0 | ₹1,200 |
| Professional | ₹50,000 | ₹28,000 | ₹8,000 | ₹14,000 |
| Freelancer | ₹40,000 | ₹25,000 | ₹0 | ₹15,000 |
| Other | ₹3,000 | ₹2,200 | ₹0 | ₹800 |

Examples require an explicit action. Edited examples retain example provenance. Switching profiles, clearing, refreshing or selecting personal mode resets input state. Financial values stay in React state and the rendered report. No visitor amounts are sent to a server or used by the research model.

## Exhibition walkthrough

Select a profile and enter amounts or calculate an example. Open an input or calculation explanation to see its meaning. View signed cash flow, entered spending categories and funds allocation. Replace amounts in the planner and compare the new balance and metrics with baseline. Professionals can add monthly debt; freelancers can use their lower-income estimate. Students and visitors in the other profile can enter a purchase target and explicitly allocate savings. The scenario and purchase charts use the same values as the comparison and timeline.

Select **Download PDF** to generate an A4 file in the browser. **Print or save detailed PDF** opens the device's print dialog as a fallback. The A4 report includes a branded introduction, profile and timestamp, provenance, 5W1H, input register, substituted calculations, summary, charts, scenario changes, planning observations, assumptions and a link to the current CreditAI origin.

## Verification

- Frontend automated tests: 55 passed, 0 failed, 0 skipped, including ten engine cases. TypeScript, lint and production build passed. Vite reports a size warning for the lazily loaded PDF library and font bundles.
- The connected FastAPI production build ran in headless Edge. The rehearsal checked direct navigation, refresh, blank starting inputs, Calculate Sample and all four sample profiles, all four personal profiles, Clear All, and return navigation. Populated personal dashboards fit at 320, 375, 390 and 430 pixels. The welcome view also fit at 1366, 1440 and 1920 pixels.
- Personal balances were ₹1,200.29 for Student with no EMI, ₹14,000 for Professional with ₹8,000 EMI, ₹15,000 for Freelancer and −₹3.25 for Other with zero funds. A ₹6,000 additional EMI changed the Professional scenario to ₹8,000. The Freelancer lower-income scenario produced ₹3,000. A Student purchase target of ₹1,500 with ₹500 allocated and ₹250 per month projected four months.
- The browser checked that financial inputs left local storage, session storage and the URL query empty. A second isolated browser context started without inputs while the first retained its results.
- Eight direct downloads covered personal and sample reports for every profile. Each had three numbered A4 pages. Poppler rendered all 24 pages for visual inspection. The pypdf check extracted provenance, formulas, INR values, scenario and chart labels and verified 21–33 vector rectangles per report. The Student purchase report included its goal chart and timeline. The report link is derived from the serving origin and labeled Local rehearsal link on localhost.
- The print control invoked the browser print function. Chromium rendered a valid four-page fallback PDF. Physical iOS and Android file saving was outside this browser rehearsal.
- Browser navigation opened Borrower Prediction, Batch Evaluation and Agentic Commerce. The focused backend run exercised their related API contracts, batch workflow and commerce cases with 80 passed, 0 failed and 3 skipped. The browser also called the real HTTP POST /v1/score and verified 200, not_validated, none, null probability, false validation and null model version.
- Full backend collection stopped with two import errors in test_phase12_signal.py and test_phase23_benchmark.py. With those modules excluded, the broader suite recorded 165 passed, 3 failed and 10 skipped. Windows Application Control blocked scikit-learn's _bitset extension. A separate SHAP import confirmed the same underlying error, which explains the two missing-contribution failures. The third failure imported the blocked extension directly through the training pipeline.
- Calibration SHA-256 matched 6b94f41d3521c37e22d41b91e505006f1c737d022c214f803a5b9a057f185cdc. Model and inference files were unchanged.

The browser harness is frontend/tests/moneyHealth.browser.mjs. Its evidence is written under frontend/build. Run frontend/tests/inspect_money_health_pdf.py with pypdf against the generated directory to repeat the text, page-number and vector checks.
