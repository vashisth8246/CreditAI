# CreditAI final UI and release audit

The versioned candidate passed the main browser journeys and clean archive checks on Windows and Linux Python 3.11. The Azure gate is **BLOCKED** because the target configuration could not be inspected. The audit distinguishes observed passes from checks that still lack evidence.

## Source and changes

Branch `visitor-money-health`. Base `54f1229f4a3ab2a3f49cf7e44f9a3d502f2c43db`. Packaged source `11cb674e290f2eec22d22e8d5a4eabe11d344af3`. The later documentation commit records the audit and does not alter the packaged application.

| File | Change |
|---|---|
| `frontend/src/release-polish.css`, `frontend/src/main.tsx` | Shared emerald, navy and border tokens, nav focus, chart contrast, 180 ms reduced-motion-aware transitions, and a Batch header that wraps on narrow screens |
| `frontend/src/PredictionWorkspace.tsx` | Actual research threshold marker and SHAP magnitude bars on a common scale, with exact values retained |
| `frontend/src/ConfidenceGuardian.tsx` | Measured coverage/error points, domain expansion for observed data, point tooltips and exclusion of unavailable errors |
| `frontend/src/BatchCharts.tsx` | Risk bars share the scored-row denominator, histogram zeros have zero height, keyboard labels identify the bin and count |
| `frontend/src/MoneyHealthDashboard.tsx` | Immediate exact text values and short signed-bar transitions from the deterministic engine |
| `frontend/src/agenticCommerce.ts` | Current simulated workflow stage exposed to assistive technology |
| `frontend/src/moneyHealthPdf.ts` | Replaced the missing separator glyph in financial explanations and comparisons |
| This report | Browser, packaging and deployment-gate evidence |

The existing evaluation views retain their saved ROC, calibration and Guardian data. Missing PR coordinates and unavailable evidence remain disclosed. Approved forms, consent and financial calculations retain their existing behavior.

## Feature verification matrix

PASS refers to the named check. Comprehensive error injection, screen-reader testing and all-width checks across every state remain NOT TESTED.

| Section | Status | Evidence |
|---|---|---|
| Executive Overview | PASS | Snapshot, headline and chart render; sidebar and direct route |
| Borrower Prediction | PASS | Three 23-field samples, editable age, real estimates 8.2%, 17.6%, 37.8%, reset, metadata, calibration, research warning and SHAP |
| Batch Evaluation | PASS | CSV and multi-sheet XLSX, invalid EDUCATION row, sheet selection, scoring and both export formats; every displayed row reconciled against both exports |
| Data Discovery | PASS | Search, empty search, reset and detail dialog |
| Portfolio Intelligence | PASS | Chart, segment change and no-match filter |
| Model Lab | PASS | Model and validation split controls |
| Model Performance Lab | PASS | Evaluation loaded and charts rendered; no new curve data inferred |
| Risk Explorer | PASS | Historical evidence-gap state rendered |
| Explainability | PASS | Historical evidence-gap state rendered; local SHAP verified through Borrower Prediction |
| Monitoring | PASS | Historical signals and awaiting-deployment state |
| Architecture & Audit | PASS | Safety-lock state and architecture flow |
| Agentic Commerce | PASS | Purchase context, research profile, comparison, explicit confirmation, simulated execution; live duplicate confirmation retained the transaction and audit length |
| Commerce Audit Trail | PASS | Seven actual simulated events |
| Confidence Guardian | PASS | Individual assessment and held-out evaluation |
| DecisionProof | PASS | Scenario and plan, benchmark, manual review, audit download and replay, HTTP validation, refresh |
| My Money Health | PASS | Four sample and four personal profiles, charts and clear behavior |
| What-If | PASS | Ready-made and custom modes, live edits, Apply, Reset, recommendations and draft; all four profile balances verified |
| Money Challenge | PASS | Three types, confirmation, actual test entries, edit/delete and milestones |
| Money Passport | PASS | Consent, save, refresh, backup restore and separate browser context |
| Financial reports | PASS | Eight direct financial PDFs, print fallback, Passport PDFs and custom scenario value reconciliation |
| Live Azure configuration | BLOCKED | Authenticated Azure CLI unavailable; public health and build requests timed out |

## Accessibility, arithmetic and integrity

Edge checked 320, 375, 390, 768, 1024, 1366, 1440 and 1920px on the overview, prediction, batch, performance, DecisionProof, Commerce and Money Health landing states. The final run reported no document-wide overflow, uncaught JavaScript errors or HTTP failures. Focused workflows additionally checked keyboard access, report replay and live status feedback. Emulated reduced motion set the new chart entrance animation to none. Full assistive-technology and physical-device certification remain NOT TESTED.

The professional custom case combined ₹40,000 income and ₹1,000 extra EMI, producing ₹3,000 versus a ₹14,000 baseline. Student, Freelancer and zero-income cases also matched the engine. The tests cover integer-paise totals, goals, added EMI and scenario isolation. Archive inference and Batch both returned a calibrated PD of 0.08206632971007599 for the same synthetic 23-field profile. Both clean environments returned the full documented `/v1/score` tuple.

Calibration SHA-256 `6b94f41d3521c37e22d41b91e505006f1c737d022c214f803a5b9a057f185cdc`. Model files were preserved. The local model loads with scikit-learn compatibility warnings for calibration objects serialized with 1.9.0 and read with 1.9.1. Predictions and calibration checks succeeded in both environments.

## Security and privacy

Reviewed request validation, export formula neutralization, workbook handling, archive exclusion and consent. Batch limits include 10 MiB, 5,000 rows, 20 sheets and 200 columns. The parser handles CSV/XLSX and flags formulas in XLSX. Legacy XLS has a documented formula-detection limitation. Compressed workbook resource-exhaustion behavior was not stress-tested. The narrow source scan found no matching private-key or token signatures. Archive inventory checks excluded local secrets, datasets, test fixtures and logs. The isolated Passport browser context started empty. This is a scoped review, with no penetration testing or production security certification.

## Tests and performance

Windows 11 10.0.26200, Intel i3-10110U (4 logical processors), approximately 16 GiB, Python 3.11.9, Node 24.13.1, Edge headless, Vite 8.3.4. Backend pytest **201 passed, 0 failed, 11 skipped**. Three skips were Windows HTTP harness limitations, one required raw LendingClub data, and seven required the Taiwan workbook at its pipeline fixture path. Live HTTP covered key skipped harness paths. Frontend **73 passed, 0 failed, 0 skipped**. TypeScript, configured Oxlint, Vite production build and Git whitespace checks passed.

| Measurement | Local observation |
|---|---:|
| Overview ready from fresh Edge tab | 621 ms |
| Borrower form ready | 498 ms |
| Batch / Performance / DecisionProof / Commerce / Money Health ready | 33 / 137 / 393 / 98 / 183 ms |
| Single comparison update observed through Edge automation | 78 ms |
| Financial PDF download | 1,355 ms |
| Edge tab JS heap after route audit | 4.64 MB |
| Windows extracted archive startup / inference / one-row batch | 6,010 / 181 / 38 ms |
| Linux container startup including extraction / inference / one-row batch | 4,381 / 115 / 27 ms |
| Linux container memory after smoke test | 206.4 MiB |

These are single local observations including automation overhead, with no load or long-duration test. The main JS is 464.21 kB minified, 134.19 kB gzip, up from 463.94 kB minified in the prior build. Deferred PDF engine and fonts remain 1,325.61 kB and 830.02 kB minified and trigger the existing warning. Their lazy-loading boundary remains in place.

## Candidate and clean extraction

- ZIP `release/creditai-11cb674e290f2eec22d22e8d5a4eabe11d344af3.zip`, 14,084,624 bytes, SHA-256 `55ebbbb7d06533a095548884f3cf13493cbd48c048ca4591bf7a04d7a07e589d`.
- Sidecar `release/creditai-11cb674e290f2eec22d22e8d5a4eabe11d344af3.manifest.json`, SHA-256 `f20034bfcc7aeccfa68d66ea2646eb246881d7da588ab94632510a45dc4f0c4b`.
- CRC and manifest inventory passed for 95 archive entries. The registered artifacts and production frontend were present. Windows used the project interpreter from a separate extraction directory. Docker mounted only the ZIP, extracted it inside the container and ran Python 3.11.18 with the packaged requirements and system `libgomp1`.
- Both boots passed `/health`, `/v1/status`, source SHA from `/v1/build`, static assets, direct and repeated `/money-health`, dashboard, DecisionProof, Guardian inference, Batch, Commerce replay and score safety. The initial Docker dependency download timed out and a longer-timeout retry succeeded.
- Historical rollback SHA-256 `ed8f4d22ee478d6f1d43f6a1ec8ba7c4257041ce70d8e2337a023b6ba389900d`. Historical manifest SHA-256 `e4c0bd79a5aa3e5aa1aba47e789b1c739a989ee0ae4ed7e21dc602881c7dbd53`. The existing predeployment audit remains untracked.

## Azure and GitHub

The tested startup is `python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000` with `CREDITAI_BUILD_SHA` set to the exact packaged source. CI uses Python 3.11. The raw workbook is provisioned separately for verified dataset-dependent flows. The repository's cloud workflow is gated to main and its configured provider, so this branch delivery is separate from deployment.

Azure remains blocked pending authenticated read access for the actual App Service OS, Python stack, startup command, build settings, environment configuration, plan limits, health check, current deployment ID, and rollback procedure. Public health and build requests to the supplied hostname timed out. Local Docker validates Linux runtime behavior, while App Service capacity and configuration require separate verification. If a deployment is later authorized, use the exact audited artifact and retain the historical ZIP and manifest for the rollback audit.

The source and audit are published together on `origin/visitor-money-health`. Compare `git rev-parse HEAD` with `git ls-remote origin refs/heads/visitor-money-health`; the audit-only tip is distinct from the packaged source SHA.

[Edge layout captures](../frontend/build/release-polish-evidence/) · [Borrower outputs](../frontend/build/original-borrower-restored/) · [Custom scenario evidence](../frontend/build/release-custom-timed/) · [Clean Linux log](../logs/release-final-linux.log) · [Clean Windows log](../logs/release-final-windows.log)

**CREDITAI FINAL RELEASE BLOCKED — ISSUES REMAIN**
