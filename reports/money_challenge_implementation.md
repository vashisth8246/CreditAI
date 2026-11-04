# Money Challenge and Money Passport

The existing public Money Health route now opens Money Passport from the Start My Money Challenge or Continue My Money Challenge button. Passport creation works with or without a Money Health result. A visitor reviews and explicitly confirms the plan. The optional retained profile and monthly balance come from that result only when explicitly selected. Example context is marked EXAMPLE-BASED PLAN and adds no recorded entries.

## Implementation files

- `frontend/src/MoneyPassport.tsx` owns plan review, active challenges, entry editing, export/import and consent controls.
- `frontend/src/moneyChallenge.ts` defines the schema, validation, calendar schedules, calculations and storage envelope.
- `frontend/src/moneyPassportStorage.ts` handles browser initialization and storage failures.
- `frontend/src/moneyPassportPdf.ts` builds the local progress report with the existing PDF stack and runtime CreditAI link.
- `frontend/src/MoneyHealthPage.tsx` and `frontend/src/moneyHealth.css` integrate the entry point and responsive styling.
- `frontend/tests/moneyChallenge.test.ts`, `frontend/tests/moneyHealth.browser.mjs` and `frontend/tests/inspect_money_passport_pdf.py` verify the engine, connected browser and downloaded report.

## Data and privacy

A version 1 passport stores an ID, type, title, creation and optional end date, monetary plan, optional profile and snapshot, and a list of dated self-reported entries. An entry has a unique ID, amount in integer paise, type and optional note. Browser-local storage holds a versioned consent envelope only after Save Money Passport. Edits to a saved passport also save. Unsaved passports are held in this tab. Up to 20 independent passports can be opened with a selector. The UI checks for a changed saved collection before updating it, so a stale tab can export and reload rather than overwrite newer records.

An export is plain JSON. Import checks the version, file size, dates, integer amount bounds, unique entry IDs, entry count, categories, compatible types and historical withdrawal balance. Import opens a separate in-memory record and rejects an already open ID. Saving an import requires consent. Delete and Clear All Data require confirmation and offer a chance to export first. The feature has no account or backend storage and puts no amounts into requests, URLs or third-party tools. Anyone with access to the same browser profile can access its saved passports. Browser clearing or changing devices can remove access, and backups carry the underlying data.

## Calculations

Savings balance equals explicitly allocated starting funds plus contributions minus withdrawals. The amount remaining is the positive target gap. Emergency buffer uses the same balance, and divides it by reported monthly essential spending for coverage when the denominator is positive. A coverage target multiplies the selected number of months by essential monthly spending.

Spending reduction subtracts the reduction target from the comparable baseline to get a spending limit. It sums in-period entries and compares actual spending with both baseline and limit. This comparison does not establish a deposit. Spending milestones require the inclusive tracking period to have ended and a recorded entry to exist.

Milestone thresholds are 25%, 50%, 75% and 100% of target, rounded up to the next paise. Achievement follows the current recorded balance or closed-period comparison, so editing or deleting an entry can change it. A dated running chart comes from actual entries. The schedule projects the remaining amount at the chosen daily, weekly or monthly cadence. It uses calendar dates with month-end clamping and rounds required contributions up to a paise. Snapshot feasibility compares the monthly equivalent of planned contributions with the retained balance, using a 30-day month. Estimates assume future contributions occur as planned.

## PDF and checks

The downloadable Money Passport PDF is generated in the browser. It separates the original plan, optional retained context, recorded timeline, calculated progress, milestones and estimated future dates. It includes numbered pages, vector bars, remaining steps, privacy and limitations, and the current CreditAI link.

- Frontend tests: 62 passed, 0 failed, 0 skipped, including seven new tests. TypeScript, production build and lint passed. The build retains the existing lazy PDF bundle size advisory.
- Focused backend: 80 passed, 0 failed, 3 skipped. These checks cover API, multi-sheet Batch Evaluation, and Agentic Commerce. Full backend certification was outside this run. The previous full-suite investigation found Windows Application Control blocking scikit-learn's _bitset import.
- Calibration SHA-256 matched 6b94f41d3521c37e22d41b91e505006f1c737d022c214f803a5b9a057f185cdc.
- The Student PDF was rendered with Poppler and checked with pypdf. It contains one numbered A4 page, five vector rectangles, the edited ₹550.5 contribution and ₹449.5 remaining, with the old ₹300.25 value absent. Its plan provenance and self-reported entry are explicit.
- Browser evidence is produced by `frontend/tests/moneyHealth.browser.mjs` under `frontend/build`. Physical mobile device file saving is not covered by the viewport rehearsal.


The connected Edge rehearsal created four challenges across all four Money Health profiles and all three challenge types. It verified review and confirmation, no initial activity, opt-in saving, refresh and Continue My Money Challenge, editing, deleting, milestones, backup download and restore, isolated browser context, Clear All Data and layout at 320, 375, 390 and 430 pixels. The existing Money Health browser cases and all eight Money Health PDF extraction checks passed. The connected live HTTP POST /v1/score returned 200 with not_validated, none, null probability, false validation and null model version. Navigation returned to the full CreditAI application and opened Borrower Prediction, Batch Evaluation and Agentic Commerce.
