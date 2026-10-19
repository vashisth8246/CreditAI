# CreditAI Research Workbench

The Phase 6.2 frontend is an evidence-driven research dashboard with enhanced UI/UX. It displays a historical U.S. LendingClub benchmark, dataset readiness, portfolio summaries, evaluation metrics, API safety state, and implementation/audit gates. It does not present the synthetic pipeline as Indian borrower validation or provide production credit decisions.

## Phase 6.2 Enhancements

- **Keyboard Navigation:** Press 1-8 to navigate between views (overview, discovery, portfolio, lab, explorer, explainability, monitoring, architecture)
- **Retry Loading:** Error states now include a retry button with attempt counter
- **Dataset Detail Modal:** Click "View details" in the Data Discovery table to see full dataset metadata
- **Navigation Shortcuts:** Hover over navigation items to see keyboard shortcuts
- **Improved Error States:** Context-specific error messages with actionable next steps
- **Source Filtering:** Filter datasets by source type (All, Historical, Synthetic, External) in Data Discovery

## Run

```powershell
npm install
npm run dev
```

The current Windows workspace path contains `ML&DS`, which can be split by npm's generated command shims in this shell. If `npm run` fails due to that path, invoke the installed tools directly:

```powershell
node .\node_modules\vite\bin\vite.js --host 127.0.0.1
node .\node_modules\oxlint\bin\oxlint src
node .\node_modules\typescript\bin\tsc -b
node .\node_modules\vite\bin\vite.js build
node --experimental-strip-types --test tests/analytics.test.ts
```

For the API example, start the existing FastAPI app as described in the root project guide. `/v1/score` remains `not_validated` and returns `default_probability: null`. The dashboard displays API failures without substituting an estimated score.

## Data and artifacts

The frontend loads sanitized local JSON from `public/data/`. These files are generated from the existing data inventory, saved Phase 2.3 metrics/split summaries, and a chunked aggregate pass over the LendingClub CSV. They contain aggregate counts/rates, a histogram and correlation summaries; no raw borrower rows, IDs, or individual predictions are exported. Refresh from the repository root using the configured Python environment:

```powershell
python scripts/phase_6_1_build_artifacts.py
```

Dataset rows marked `REVIEW_REQUIRED` or `BLOCKED` do not enter model evaluation. Synthetic data is for software demonstration and testing only. Review `reports/phase_6_1_dataset_discovery.md` and `reports/phase_6_1_frontend_implementation.md` for provenance, labels, limitations, and detailed use.

## Evidence boundary

Historical metrics are explicitly tied to the U.S. LendingClub closed-loan chronological benchmark. Its terminal outcome has a variable horizon and is not a fixed-horizon probability of default. It does not validate Indian borrowers. The application contains no production Account Aggregator integration and makes no regulatory-compliance claim.
