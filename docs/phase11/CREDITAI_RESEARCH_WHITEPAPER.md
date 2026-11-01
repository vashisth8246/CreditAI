# CreditAI: Reliability-Aware Credit Risk Research

**Phase 11 research paper — Taiwan UCI benchmark, research/demo only**
**Evidence snapshot:** saved experiment artifacts in `reports/phase11/`; no experiment outputs were regenerated for this paper.

## Abstract

This paper documents a reproducible software and modeling study using the UCI Default of Credit Card Clients dataset. Logistic Regression, Random Forest, and XGBoost were trained on a stratified 70/15/15 train/validation/test split. Platt sigmoid and isotonic calibration were fitted from validation predictions only, then assessed on the held-out test split. The saved evidence shows Random Forest with the highest ROC-AUC (0.7816), XGBoost with the highest average precision (0.5588), and Platt-calibrated Random Forest with the lowest Brier score (0.1349), log loss (0.4288), and equal-width 10-bin ECE (0.0083). A validation-selected review margin and bounded SHAP perturbation analysis are also reported. The Taiwan dataset does not establish performance for Indian borrowers, current lending, or real lending decisions. CreditAI's `/v1/score` remains `not_validated`.

## Problem statement and objective

Credit default research often reports ranking metrics without examining probability quality, referral coverage, explanation sensitivity, data provenance, or the boundary between a research model and a lending decision. Phase 11 records those dimensions for one historical dataset and provides repeatable software paths for CSV and Excel portfolio evaluation. It is a methods and engineering exercise, not a credit policy or production model validation.

## Dataset, provenance, and limitations

The experiment uses the UCI Default of Credit Card Clients workbook: 30,000 records, 23 predictors, an identifier, and the target `default payment next month`. The saved metadata records 23,364 non-default and 6,636 default observations, no missing values, and SHA-256 `21b3cf4e30878150ae8db9386780e23febb613921747dec9e59dccb32f6104d3`. The file remains local under the ignored `Data/` directory. `scripts/fetch_phase11_dataset.py` selects the expected workbook from the official UCI archive and verifies its hash before writing it.

The data describe Taiwanese credit-card clients and historical payment behavior from 2005. They do not represent Indian applicants, other products, current economic conditions, or an institution's present portfolio. The source dataset has demographic fields and historical credit behavior; this study does not establish fairness, legal acceptability, causal effects, or operational utility. See the [UCI dataset record](https://doi.org/10.24432/C55S3H) and the original [Yeh and Lien study](https://doi.org/10.1016/j.eswa.2007.12.020).

## Experimental design and feature preparation

The runner uses seed 42 and a stratified split of 21,000 training, 4,500 validation, and 4,500 locked-test rows. It loads through `src/data_loader.py`, applies `src/preprocessing.py`, then `src/feature_engineering.py`. The target is the workbook's `default payment next month`; the identifier is excluded. The saved metadata contains SHA-256 hashes of the row-position arrays for each split. The split hashes are recorded in `reports/phase11/run_metadata.json`.

The runner fits each model on training rows and produces validation and test probabilities. Calibration maps are fitted only on validation probabilities and labels. Saved locked-test metrics are calculated after calibration. No model or hyperparameter search is implemented in this runner. The existing artifacts show all three model families and all calibration methods on the same held-out split. Because multiple candidates are evaluated on the locked test set, that set is best described as a common final comparison set; repeated human inspection can still inform future choices. The saved metadata says the split was used only for final metrics, but the repository cannot establish that no later decision-maker ever consulted these results when making a choice.

## Models

- **Logistic Regression:** `StandardScaler` plus `LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)`.
- **Random Forest:** 200 trees, maximum depth 10, minimum leaf size 20, balanced class weights, seed 42, all available CPU workers.
- **XGBoost:** 300 estimators, depth 5, learning rate 0.05, row and column subsampling 0.8, training-derived `scale_pos_weight`, seed 42, log-loss evaluation.

The values above describe the actual Phase 11 runner and saved metadata, not a claim that these configurations are optimal.

## Calibration and metrics

Raw probabilities are compared with a sigmoid (Platt-style logistic regression on clipped probability logits) and isotonic regression. Both calibrators are fitted on the validation split only. Calibration performance is evaluated on the locked test split. The study reports ROC-AUC, average precision, Brier score, log loss, and ECE. ECE uses ten equal-width intervals on `[0, 1]`; empty bins are omitted and each non-empty bin's absolute difference between mean predicted probability and observed default rate is weighted by its fraction of all rows. Log-loss inputs are clipped to `[1e-15, 1 - 1e-15]` for numerical stability.

### Saved locked-test comparison

| Model | Method | ROC-AUC | Average precision | Brier | Log loss | ECE (10 equal-width bins) |
|---|---|---:|---:|---:|---:|---:|
| Logistic Regression | Raw | 0.7550 | 0.4903 | 0.1934 | 0.5804 | 0.2175 |
| Logistic Regression | Platt | 0.7550 | 0.4903 | 0.1436 | 0.4518 | 0.0124 |
| Logistic Regression | Isotonic | 0.7514 | 0.4733 | 0.1440 | 0.4553 | 0.0133 |
| Random Forest | Raw | 0.7816 | 0.5568 | 0.1756 | 0.5339 | 0.1917 |
| Random Forest | Platt | 0.7816 | 0.5568 | **0.1349** | **0.4288** | **0.0083** |
| Random Forest | Isotonic | 0.7803 | 0.5371 | 0.1351 | 0.4504 | 0.0123 |
| XGBoost | Raw | 0.7807 | 0.5588 | 0.1709 | 0.5205 | 0.1696 |
| XGBoost | Platt | 0.7807 | 0.5588 | 0.1355 | 0.4305 | 0.0145 |
| XGBoost | Isotonic | 0.7800 | 0.5394 | 0.1359 | 0.4451 | 0.0111 |

These values were read from `reports/phase11/probability_metrics.csv` and `.json`; an independent row-by-row comparison in this completion pass found all nine rows and numeric fields equal within `1e-12`. Results are mixed by metric: no single model wins every column. The displayed values are research results on this split and are not expected performance on another population.

## Selective-review experiment

The saved procedure uses the XGBoost model with Platt calibration fitted on validation data. For candidate margin `m`, it accepts an observation when `abs(PD - 0.5) >= m` and refers it otherwise. Candidate margins are evaluated on validation; among candidates with at least 80% coverage, the implementation chooses the lowest accepted-case 0.5-threshold error rate, breaking ties by higher coverage and then smaller margin. It selected `m = 0.20`.

On validation, coverage was 0.8122 (3,655 of 4,500 accepted); accepted-case error was 0.1382. On the locked test, coverage was 0.8024 (3,611 accepted, 889 referred), and accepted-case error was 0.1310 (473 errors). This is a confidence-based referral screen, not a measurement of epistemic uncertainty, a guarantee of safer decisions, or an authorization to lend.

## SHAP perturbation analysis

The saved runner uses `shap.TreeExplainer` on the fitted XGBoost model and 100 fixed rows from the test split. For each of 12 selected features, it replaces that one feature with values drawn from observed training rows, leaving the other columns fixed. It compares absolute-SHAP feature rankings with Spearman rank correlation and top-10 Jaccard overlap. Across the 1,200 row-feature perturbations, the saved per-feature mean top-10 Jaccard values range from 0.8298 to 0.9858; mean absolute-SHAP rank correlations range from 0.9512 to 0.9969.

These replacements preserve the empirical marginal values of the changed feature but can create implausible cross-feature combinations. Rank stability under this perturbation is not causal evidence, a fairness test, or proof that explanations are stable under realistic population shifts. The SHAP method is described in [Lundberg and Lee (2017)](https://proceedings.neurips.cc/paper/7062-a-unified-approach-to-interpreting-model-predictions/).

## Batch evaluation system and application architecture

The application has a React, TypeScript, and Vite frontend in `frontend/` and a FastAPI service in `src/api/app.py`. The API loads tracked model files from `models/` and exposes research inference and evaluation routes separately from `/v1/score`. The frontend uses same-origin `/health` and `/v1/...` paths in production. The API dashboard snapshot marks its bundled Phase 9 LendingClub summary as historical and provides a retrieval timestamp separately from the source snapshot date.

The batch evaluator accepts CSV and Excel workbooks, examines worksheets independently, validates the Taiwan research feature contract, and reports row and sheet provenance. The synthetic seven-sheet acceptance fixture covers valid and reordered portfolio sheets, missing values, extra metadata, an invalid feature sheet, a summary sheet, an empty sheet, duplicate references, and row-level outcomes. Duplicate references remain separate rows and receive warnings. CSV and XLSX export code includes formula-injection protection. A reported `1 - PD` field is only the mathematical complement; it is not an observed or guaranteed repayment probability.

In this final pass, the seven-sheet test passed on Windows. The full HTTP suite did not complete in this Windows environment: it stalled at the first FastAPI `TestClient` health request and was interrupted. A previous blocker-resolution report records 22 batch HTTP tests passing on a local WSL Linux environment, but WSL was inaccessible in this pass and that result is historical rather than a fresh verification.

## Reproducibility record

The saved run metadata records CPython 3.11.9, NumPy 2.4.6, pandas 3.0.6, scikit-learn 1.9.1, XGBoost 3.2.0, SHAP 0.51.0, seed 42, dataset hash, split sizes, and split hashes. The dependency snapshot is `requirements-phase11.lock.txt`. The runner now accepts `--output-dir`; this pass reproduced the study in `.phase11-reproduction-verification/` without overwriting `reports/phase11/`. Dataset and split hashes matched; selective-review results matched exactly; the SHAP stability CSV was byte-identical; metric CSV values matched within `1e-12`, with JSON float differences no greater than `1.5e-14`. This was a current-worktree reproduction using the local workbook. It does not establish a clean Git checkout reproduction.

This worktree contains required research code, reports, and three dashboard JSON assets that are untracked. A clean checkout at current `HEAD` therefore does not contain the complete Phase 11 implementation/assets. The raw workbook is ignored and should be acquired using the verifier. The download branch was attempted in an isolated temporary path but DNS resolution for the UCI host failed, so clean-machine acquisition is **unverified**. The local workbook hash did pass.

## Calibration artifact provenance limitation

The shipped `models/calibration_model.joblib` was not modified. Its SHA-256 is `6b94f41d3521c37e22d41b91e505006f1c737d022c214f803a5b9a057f185cdc`; it loads as `src.calibration.calibrate.PlattCalibrator` with slope `0.47414481616618126` and intercept `-1.2645029152597382`. Loading emits an unsuppressed scikit-learn warning because the artifact was serialized with 1.9.0 and current runtime is 1.9.1. The original training data, split, and script are unknown. Earlier repository review documented a discrepancy between this artifact's reported Brier result and a fresh fit under current code; the original provenance remains unresolved. No artifact was replaced.

## Threats to validity and safety boundary

The study has one historical Taiwanese dataset, one fixed random split, no external validation population, no uncertainty intervals, and no demonstrated stability across time or institutions. Feature engineering and the target reflect the source collection. The test split was used for a multi-model and multi-calibrator report, so repeated inspection must not be treated as an untouched confirmatory trial. Selective review and SHAP findings have the limitations stated above. No Indian borrower validation, regulatory review, production monitoring, or lending authorization is established.

The API continues to report `/v1/score` as `not_validated`. Taiwan models remain research/demo models. No claim of production readiness, regulatory approval, or Indian lending performance is made.

## Future Indian validation plan

Any future India-focused study requires an authorized, representative dataset with a documented lawful basis, product and population scope, target and observation horizon, clear treatment of censoring, and temporal separation. Before fitting, define missingness handling, leakage prevention, candidate baselines, subgroup and calibration analyses, decision costs, governance, retention, and access controls. Use a temporal holdout and an independent evaluation protocol. Review fairness and legal obligations with qualified local stakeholders. Do not use this Taiwan experiment as a substitute for those steps.

## Conclusion

The saved Phase 11 results show that calibration improved probability metrics in this particular Taiwan test split, with Random Forest leading on several calibration measures and XGBoost having the highest average precision. The batch and research code provide useful research and demonstration workflows. Clean-checkout reproduction, current full backend HTTP verification, clean frontend dependency verification, Docker runtime verification, and a real GitHub Actions run remain unresolved. Phase 11 is therefore **PARTIAL**, with explicit research and engineering limitations.

## References

1. UCI Machine Learning Repository, “Default of Credit Card Clients,” [dataset record](https://doi.org/10.24432/C55S3H).
2. Yeh, I.-C., and Lien, C.-H. (2009), “The comparisons of data mining techniques for the predictive accuracy of probability of default of credit card clients,” *Expert Systems with Applications*, 36(2), 2473–2480. [doi:10.1016/j.eswa.2007.12.020](https://doi.org/10.1016/j.eswa.2007.12.020).
3. Niculescu-Mizil, A., and Caruana, R. (2005), “Predicting Good Probabilities With Supervised Learning,” *Proceedings of ICML 2005*. [doi:10.1145/1102351.1102430](https://doi.org/10.1145/1102351.1102430).
4. Lundberg, S. M., and Lee, S.-I. (2017), “A Unified Approach to Interpreting Model Predictions,” *Advances in Neural Information Processing Systems 30*. [paper](https://proceedings.neurips.cc/paper/7062-a-unified-approach-to-interpreting-model-predictions/).
