# DecisionProof research report

DecisionProof asks which synthetic evidence checks are sufficient to make a simulated affordability outcome invariant. Confidence Guardian separately flags input quality and unusualness relative to a Taiwan training reference. XGBoost estimates default probability within its research scope. The Guardian evaluation did not establish a statistically conclusive predictive benefit.

The approach relates to decision-dependent information value and the reject option. DecisionProof contributes a reproducible CreditAI demonstration of exact finite-state separation with declared verification effort. No claim of algorithmic novelty or superiority to banking practice is made. [Howard, Information Value Theory](https://ieeexplore.ieee.org/document/4082064/) · [Chow, On Optimum Recognition Error and Reject Tradeoff](https://research.ibm.com/publications/on-optimum-recognition-error-and-reject-tradeoff)

## Method and architecture

The bounded FastAPI route accepts a catalog ID, residual floor, payment-to-income cap in basis points, and verification cost profile. Each synthetic evidence item records its field, possible values, source, and quality state. Verification actions specify which fields they reveal, effort and permission. There are no uploads or real borrower data. The nine cases cover consistent evidence, missing income, conflicting income, missing EMI, variable earnings, outdated evidence, irrelevant expense conflict, multiple consequential gaps, and unavailable verification.

Enumerate every listed income, expenses and payment combination. Residual equals income minus expenses minus payment. The default policy requires positive income, a residual of at least ₹20,000 and a payment-to-income ratio of at most 40%. Compare the ratio by integer cross multiplication. A field is consequential if changing it alone can reverse the outcome. For each permitted action subset, group states by revealed values. An action set resolves the decision exactly when every group has one outcome. Select minimum summed effort, then minimum action count, then deterministic action order. The downloadable Markdown embeds the inputs and results as JSON with a SHA-256 replay ID. Timing measurements are outside that ID.

This is exact over the declared alternatives and fixed action sets. Cartesian expansion can include infeasible combinations when fields are correlated. Verification is assumed to reveal the listed field exactly, with known additive effort. Unknown alternatives, noisy verification, adaptive plans, actual monetary costs and outcomes after manual review remain outside the evaluation.

## Synthetic evaluation

Nine authored cases crossed with three effort profiles give 27 deterministic runs. At the default policy there are two stable and seven reversible cases in each profile. The no-permitted-action case stays unresolved and requests manual review. A conflicting expense in the irrelevant case does not change the outcome. The conflicting-income case has residuals of ₹10,000 and ₹35,000 and requires the four-unit income check at base cost. An independent opposite-outcome-pair oracle checks minimum cost and feasibility across all 27 runs.

| Strategy | Resolved per profile (of 9) | Base total effort | Income costly | Combined costly |
|---|---:|---:|---:|---:|
| No verification | 2 | 0 | 0 | 0 |
| Verify all | 8 | 120 | 184 | 216 |
| Fixed sequence | 8 | 32 | 80 | 32 |
| Cheapest first | 8 | 50 | 60 | 50 |
| Manual review on any uncertainty | 1 | 0 | 0 | 0 |
| DecisionProof | 8 | 27 | 35 | 28 |

Zero effort for manual review excludes downstream human work. The comparisons support lower modeled verification effort at equal resolution on these cases. Authored cases and repeated cost profiles are a fixed test set. Sampling confidence intervals would misrepresent the uncertainty of those comparisons. Retrieve case-level comparisons from `POST /v1/research/decisionproof/analyze` and aggregate action counts, effort, reversals and runtime from `GET /v1/research/decisionproof/evaluation`.

At base cost, DecisionProof requested 7 actions with zero individually removable actions. Verify-all requested 32 (31 individually removable), fixed sequence 9 (1), and cheapest-first 17 (9). These counts test removal one action at a time. A local base-profile run took 8.857 ms for nine cases. The search grows exponentially with the number of actions, so the API uses a bounded catalog. The planner has no fitted parameters. The tests establish behavior on authored fixtures rather than an independent estimate of scenario detection in the wild.

## Taiwan held-out sensitivity replay

The evaluator checks the workbook hash and reconstructs the Guardian split. The held-out set contained 4,500 rows and 4,490 passed the raw request schema. The frozen model and calibrator produced baseline error 21.18%, Brier score 0.14581, log loss 0.45595, and 441 Guardian review flags. Perturbations retain original labels and all 4,490 valid rows in the denominator, including values clipped at the permitted boundaries. The 95% Wilson intervals describe row-level reversal proportions under each replay, conditional on treating rows as independent. They do not measure a paired predictive benefit, a document correction, or transportability to another population.

| Perturbation | Reversals at 0.5 | Reversal rate (95% interval) | Mean absolute PD change | Guardian review |
|---|---:|---:|---:|---:|
| PAY_0 one code lower | 42 | 0.94% (0.69–1.26%) | 0.02317 | 439 |
| PAY_0 one code higher | 37 | 0.82% (0.60–1.13%) | 0.02759 | 461 |
| Credit limit −10% | 24 | 0.53% (0.36–0.79%) | 0.00940 | 469 |
| Credit limit +10% | 18 | 0.40% (0.25–0.63%) | 0.00709 | 466 |

Run `python -m scripts.evaluate_decisionproof_taiwan WORKBOOK --output reports/decisionproof_taiwan_results.json` with the original workbook. The aggregate JSON includes full precision, changed-input counts and dataset identity. The replay establishes sensitivity in this research model. It supplies no evidence of real verification efficacy, causality, Indian lending performance or production readiness.

Historical repayment labels primarily describe people who received credit. Outcomes for rejected applicants are generally unobserved and cannot be counted as defaults or successful repayments. The synthetic verification baselines have no meaningful mapping to the historical Taiwan rows, so the Taiwan comparisons use frozen original-input inference as their reference.

## Demonstration and verification

Open `/#decisionproof`, analyze conflicting income, inspect the two residuals, show the verification plan, then download the research report. Select the unavailable-verification case and confirm the manual-review outcome. Contrast that workflow with a Guardian input check, a Taiwan research prediction, and the Money Health visitor calculator.

Production-build Edge rehearsal checked keyboard reachability, benchmark, the ₹10,000 and ₹35,000 residuals, four-unit verification plan, downloaded report ID and strategy replay, responsive widths of 1440, 768 and 390, reload, and the manual-review case. It ran a Borrower Prediction with Guardian output and opened the Guardian lab, Batch Evaluation, Commerce, Money Health and Money Passport. These last navigation checks are smoke coverage. Live HTTP checked unknown scenario, malformed and oversized inputs and the public scoring safety tuple. Local screenshots and the downloaded example are under `frontend/build/decisionproof-evidence/`.

Calibration SHA-256 `6b94f41d3521c37e22d41b91e505006f1c737d022c214f803a5b9a057f185cdc`. Existing rollback ZIP SHA-256 `ed8f4d22ee478d6f1d43f6a1ec8ba7c4257041ce70d8e2337a023b6ba389900d`.

Backend regression finished with 196 passed, 0 failed and 11 skipped. Three skips cover Windows HTTP test harness limitations, seven require the Taiwan workbook in the pipeline's fixture path, and one requires raw LendingClub data. The standalone Taiwan replay used the original workbook explicitly. Frontend finished with 68 passed, 0 failed and 0 skipped. TypeScript, lint, production build and Git whitespace checks passed.
