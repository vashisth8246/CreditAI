# CreditAI Phase 6.1 — Frontend Implementation

## Delivered

The previous React + TypeScript + Vite frontend is now an eight-view research workbench: executive overview, data discovery/readiness, portfolio intelligence, model lab, risk explorer, explainability, monitoring, and architecture/audit. It keeps a compact persistent navigation rail, responsive layout, interactive filters/selection, status badges, and data-source labels. Charts are purpose-built responsive SVG/CSS components; no chart dependency or remote font is required.

The dashboard consumes only three generated local JSON artifacts under `frontend/public/data/`: inventory, feature metadata, and sanitized LendingClub aggregates/metrics. `scripts/phase_6_1_build_artifacts.py` streams the large CSV in chunks, never exports row-level records, IDs, or predictions, and reuses saved benchmark CSVs. The frontend does not parse raw source data. Other datasets show verified metadata or a limited-profile state.

The dashboard does not invent individual historical predictions, score distributions, ROC/PR curves, calibration curves, or local explanations. Risk Explorer has an explicit synthetic contract-example action against the existing local scoring API and safe nullable-probability display; API behavior was not modified. Explainability and Monitoring identify evidence that is not available. No production Account Aggregator connection exists.

## Running locally

From the `frontend` directory:

```powershell
npm install
npm run dev
```

In this Windows workspace, the repository path includes `ML&DS`, and npm's generated command shims can misparse that path under the current shell. If npm scripts fail with an incorrectly split path, use the installed package entrypoints directly:

```powershell
node .\node_modules\vite\bin\vite.js --host 127.0.0.1
node .\node_modules\oxlint\bin\oxlint src
node .\node_modules\typescript\bin\tsc -b
node .\node_modules\vite\bin\vite.js build
node --experimental-strip-types --test tests/analytics.test.ts
```

The API example requires the existing FastAPI app to be running separately according to the root operator guide. Its expected response remains `score_status: not_validated` and `default_probability: null`; network/API failure is rendered without substituting a local risk estimate.

## Refreshing safe aggregate artifacts

With the repository Python environment and dependencies installed, run:

```powershell
python scripts/phase_6_1_build_artifacts.py
```

This reads project reports and streams the existing LendingClub source. It writes only inventory CSV/JSON and aggregate dashboard JSON. It does not alter old benchmark reports, source datasets, fitted models, or the scoring contract. The CSV's license, consent, and commercial redistribution status remain subject to existing source terms; do not publish raw data.

## Data-source labels and safety

- `HISTORICAL RESEARCH DATA`: aggregate evidence derived from the U.S. LendingClub benchmark.
- `SYNTHETIC DEMO`: generated records used only in software examples/tests.
- `LIVE API — NOT VALIDATED`: the current API contract, with null validated probability.
- `DATA UNAVAILABLE`: evidence is absent, mixed, or not verified.

Metric captions preserve dataset, target, cohort and split. A research benchmark score is not an Indian borrower prediction, calibrated production PD, or lending recommendation. The dashboard is for research demonstration only.
