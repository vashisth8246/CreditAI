# Borrower Prediction original UI restoration

## Historical source

Selected `6681baf63f16c2a60838fc3fa308a7beec04d928`, the parent of the first flexible-history change, `08780eb`. Its Borrower Prediction component is identical to the one in the Guardian introduction, `cdf3011`. It contains the compact form and the Guardian integration together. The selection is based on Git history and the archived local browser capture.

The restored form has the original demographics and capacity group, six repayment dropdowns, six monthly bill fields and six monthly payment fields. It uses the historical NT$ labels and helper descriptions. The two local adaptations are a port-neutral connectivity label and the existing secondary button style for a visible Reset control.

## Files

- Restored and adapted `frontend/src/PredictionWorkspace.tsx`.
- Removed the unused `MonthlyHistoryEditor.tsx`, `HistoryInsights.tsx`, `monthlyHistory.ts`, `monthlyHistory.css`, and `historyAnalytics.ts` files under `frontend/src`, with their two dedicated tests.
- Added this report. The original stylesheet, shared API, backend and model files required no edits.

## Browser and model checks

Edge at 375, 390, 768, 1366 and 1440px showed the original group hierarchy and no page-wide horizontal overflow. Each preset filled all 23 fields. The Low Risk example was edited before submission to verify that the request reflected the form. Captured Guardian request payloads matched the form fields, including `PAY_0` and `PAY_2` through `PAY_6`, and all 12 monetary history fields. The model returned the research classification, probability, Guardian assessment and SHAP output for all three presets. Reset cleared the inputs and displayed prediction. The example labels name synthetic presets.

| Example | Displayed research PD |
|---|---:|
| Low Risk Borrower, age edited to 35 | 8.2% |
| Moderate Risk Borrower | 17.6% |
| High Risk Delinquent | 37.8% |

[Historical form and Guardian](../frontend/build/guardian-evidence/typical.png) · [Restored 375px](../frontend/build/original-borrower-restored/form-375.png) · [390px](../frontend/build/original-borrower-restored/form-390.png) · [768px](../frontend/build/original-borrower-restored/form-768.png) · [1366px](../frontend/build/original-borrower-restored/form-1366.png) · [1440px](../frontend/build/original-borrower-restored/form-1440.png) · [Live prediction](../frontend/build/original-borrower-restored/High-Risk-Delinquent.png)

## Regression and release

The frontend suite passed 68 tests with zero failures and skips. The focused backend suite passed 88 tests with zero failures and two skips for Windows HTTP harness limitations. TypeScript, lint, production build, and Git whitespace checks passed. Vite reports the existing size warning for the deferred PDF assets.

The production-style browser run visited all 14 research destinations. DecisionProof completed analysis, planning, benchmark, download and report replay. Batch Evaluation scored CSV and multi-sheet XLSX and downloaded exports, preserving the partial-row error and source-sheet labels. Commerce completed the simulated journey and emitted seven audit events. Money Health passed all four sample and personal workflows, What-If, eight direct financial PDFs, print fallback, Money Challenge and Money Passport. The research panels also passed the focused chart and filter checks through Vite.

Live `/v1/score` returned the documented `not_validated` status, `none` score type, null probability and model version, and false validation flag. Calibration SHA-256 matched `6b94f41d3521c37e22d41b91e505006f1c737d022c214f803a5b9a057f185cdc`. Rollback ZIP SHA-256 matched `ed8f4d22ee478d6f1d43f6a1ec8ba7c4257041ce70d8e2337a023b6ba389900d`. The manifest and existing untracked predeployment audit were preserved.

The restoration commit is the commit introducing this report. Use `git log -1 -- reports/borrower_prediction_original_ui_restoration.md` and compare it with `git ls-remote origin refs/heads/visitor-money-health`. Browser captures are local worktree artifacts. The local verification covers the restored historical Taiwan research workflow.

**CREDITAI ORIGINAL BORROWER PREDICTION RESTORED — VERIFIED**
