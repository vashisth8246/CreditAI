# Confidence Guardian research report

## Question and scope

Can a transparent evidence gate identify cases that merit review, and does deferring those cases reduce observed error among retained cases? This evaluates a historical Taiwan model on a reconstructed held-out partition. It does not evaluate Indian borrowers or create a lending recommendation. Input validity, population similarity, predictive performance, calibration and geographic applicability are separate claims.

## Baseline and verified data

The active model is uci_taiwan_xgb, loaded from the unchanged creditai_model.joblib with the existing Platt sigmoid calibration artifact. The API takes 23 inputs: LIMIT_BAL, SEX, EDUCATION, MARRIAGE, AGE, PAY_0 and PAY_2–PAY_6, BILL_AMT1–6, and PAY_AMT1–6. The serving pipeline creates 27 engineered inputs covering utilization, payment-to-bill ratios, delinquency, trends and payments, aligns the 50 features to the model bundle, applies calibration and returns genuine local SHAP contributions. The classification threshold stays at 0.50.

The workbook in the original checkout was read in place and matched SHA-256 21b3cf4e30878150ae8db9386780e23febb613921747dec9e59dccb32f6104d3. It contains 30,000 unique IDs. The dataset is the UCI Taiwan Default of Credit Card Clients study, credit history from April to September 2005 and next-month default. No raw rows were added to Git. Dataset source: https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients

The documented stratified seed-42 split reconstructs 21,000 training, 4,500 validation and 4,500 test rows with disjoint indices and 996 test defaults. The existing offline pipeline reproduces saved test ROC-AUC 0.780653 and calibrated Brier 0.144122. The recovered model metadata does not include original row identifiers. Matching split design, test counts and saved metrics supports reconstruction but is not independent proof of original training membership. The Guardian experiment uses the serving feature-engineering function on raw feature values. This differs from the archived vectorized engineering/preprocessing path, so the baseline for the comparison below is measured separately. The ungated offline replay can score records outside current API bounds; the schema-only row gives the deployable research baseline.

## Rules and architecture

- The additive POST /v1/research/reliability-assessment returns assessment and optional prediction. GET /v1/research/reliability-evaluation returns the measured aggregate artifact or an honest unavailable state. Existing prediction, batch, commerce and production safety routes are unchanged.
- Validation uses the deployed model schema. It reports all missing values, malformed or non-finite numbers, unsupported categorical/repayment codes, out-of-range numbers, and unknown fields. Form strings are parsed as whole numbers; the values are never clamped or imputed. Existing inference bounds are contract limits, not universal definitions of plausible people or records.
- A zero credit limit or largest statement exceeding twice a positive limit prompts a source-record check. The latter is a review heuristic, because a statement can legitimately exceed the limit. Negative statements are valid informational findings and zero payments are accepted. None of these observations by itself establishes a default, fraud, or data error.
- The training reference uses nested symmetric empirical intervals for credit limit, age, bill statements and payments, and observed frequencies with add-one smoothing for education and repayment statuses. Education uses the training-side consolidation for the reference lookup only. Gender and marital status are omitted from distribution scoring; gender codes and age groups are retained in aggregate subgroup reporting. The sum of the three strongest marginal signals is compared with a cutoff selected on validation. This exposes the contributing fields and avoids treating categorical codes as continuous distances. It does not model joint dependencies, detect drift across periods, or prove model reliability.
- Gate thresholds were specified at 95%, 90%, 80% and 70% nominal validation distribution coverage. Ties are retained, and the combined quality gate and distribution shift can change actual coverage. The UI uses the preselected 90% point (cutoff 8). The comparator ranks absolute distance from the same fixed probability threshold and selects its own cutoff on validation. No held-out labels enter reference fitting or cutoff selection.
- The versioned artifact stores aggregate reference summaries, dataset and model hashes, split fingerprints, calibration bins, subgroup counts and the test results. The runtime checks the model and calibration hashes before accepting the reference. No individual labels or profiles are served by the artifact.
- Eligible for research review means no rule crossed the selected threshold. A warning prompts manual review. Invalid input produces no prediction. Valid but unusual or reference-unavailable cases can still show the labeled research prediction and evidence limitations. The UI never supplies an approval, rejection, or lending recommendation. KNN has no evaluated Guardian distribution; its valid prediction remains labeled accordingly.

## Held-out results

All rows below use the unchanged calibrated research model. Error is at 0.50, and counts are out of 4,500. Metrics apply to each retained subset.

| Gate | Retained / abstained | Coverage | Error | ROC-AUC | Avg. precision | Brier | Log loss |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Ungated replay | 4500 / 0 | 100.00% | 21.16% | 0.7661 | 0.5492 | 0.1458 | 0.4560 |
| Schema only | 4490 / 10 | 99.78% | 21.18% | 0.7671 | 0.5511 | 0.1458 | 0.4560 |
| Schema + warnings | 4478 / 22 | 99.51% | 21.19% | 0.7680 | 0.5525 | 0.1458 | 0.4557 |
| Quality + distribution, nominal 95% | 4278 / 222 | 95.07% | 20.85% | 0.7659 | 0.5452 | 0.1440 | 0.4515 |
| Quality + distribution, nominal 90% | 4049 / 451 | 89.98% | 20.89% | 0.7663 | 0.5430 | 0.1439 | 0.4514 |
| Quality + distribution, nominal 80% | 3621 / 879 | 80.47% | 21.15% | 0.7670 | 0.5554 | 0.1453 | 0.4549 |
| Quality + distribution, nominal 70% | 3098 / 1402 | 68.84% | 21.11% | 0.7586 | 0.5404 | 0.1464 | 0.4581 |
| Probability margin, nominal 90% | 4029 / 471 | 89.53% | 16.93% | 0.6965 | 0.3356 | 0.1316 | 0.4242 |

At the chosen operating point, conditional error fell by about 0.26 percentage points versus the ungated replay, with a paired test-row bootstrap 95% interval of −0.67 to +0.15 points. **Predictive benefit was not established at the chosen point.** The 95% nominal point had a small exploratory decrease; multiple cutoffs were examined and there is no external replication. The probability margin comparator reduced conditional error more at similar coverage but retained a different subset and reduced discrimination. For the same retained rows the model outputs are identical with or without the Guardian. The gate does not improve a given prediction.

The quality scan counted 296 valid negative-statement observations, 12 statement-to-limit warnings, eight invalid-code records and two out-of-range records. At the selected point, 1,567/1,766 gender-code-1 rows and 2,482/2,734 gender-code-2 rows were retained; age under 30 retained 1,307/1,414 and age 30+ retained 2,742/3,086. These are descriptive sample counts, not fairness certification. The artifact provides calibration bin counts, mean predicted versus observed rates, alternative threshold metrics and uncertainty intervals.

## Demonstration and reproduction

Run the low-risk research sample for an eligible case. Expand Guardian research demonstrations for a valid unusual profile, missing age, unsupported PAY_0, a large statement relative to the limit, or an unsupported demonstration model. Select the existing KNN research model and run a valid sample to show unavailable distribution evidence. Model Performance Lab displays the measured coverage/error curve and retained counts. No confidence percentage is assigned.

Reproduce with Python 3.11 from the isolated checkout: python scripts/evaluate_confidence_guardian.py <path-to-verified-UCI-workbook> --output <temporary-artifact.json>. The input digest is enforced before loading. Do not overwrite credit model artifacts. The frozen reference can be served without the raw workbook.

Future research requires an independently audited holdout, temporal and external validation, an evaluation of abstention costs and subgroup uncertainty, and a separately designed applicability study before any Indian lending use.


## Verification and files

The full backend suite ran in the trusted Windows virtual environment: 191 passed, 0 failed, 11 skipped. The 11 existing skips comprise transport-specific tests and raw datasets absent from the isolated checkout's standard locations. The Guardian evaluation separately used the explicitly verified workbook path. Frontend: 68 passed, 0 failed, 0 skipped. TypeScript, lint, production build and Git whitespace checks passed.

Connected Edge verified a typical sample with SHAP, an unusual valid sample, a cross-field warning, missing age, invalid repayment code, unavailable demonstration model, KNN with unavailable distribution evidence, the evaluated Model Performance Lab, and its 390 px layout. Batch and Commerce routes opened. The full Money Health and Passport browser suite passed on the same updated backend, including eight viewport widths, all presets, downloads and saved Passport flows. That suite also checked the live /v1/score safety tuple.

Changes: src/inference/guardian.py and guardian_reference.json; src/api/app.py; scripts/evaluate_confidence_guardian.py; tests/test_confidence_guardian.py; frontend/src/api.ts, PredictionWorkspace.tsx, ModelPerformanceLab.tsx, ConfidenceGuardian.tsx and confidenceGuardian.css; this report. Browser screenshots are in frontend/build/guardian-evidence.

Calibration SHA-256 remained 6b94f41d3521c37e22d41b91e505006f1c737d022c214f803a5b9a057f185cdc. The prior rollback ZIP remained ed8f4d22ee478d6f1d43f6a1ec8ba7c4257041ce70d8e2337a023b6ba389900d. The evaluated demo runs locally at http://127.0.0.1:8768/#prediction. It is ready to demonstrate input checks and the limitations of selective prediction.
