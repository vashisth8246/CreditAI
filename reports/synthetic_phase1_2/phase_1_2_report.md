# CreditAI Phase 1.2 — Synthetic signal validation

## Decision

**Recommendation: retain the risk pipeline as an engineering prototype and prioritize consented or properly licensed historical repayment data.** The simulator creates a weak, unstable but detectable relationship by construction. It does not establish real borrower or Indian lending performance. Do not build production approval/pricing decisions on these results.

## Data and target audit

Phase 1.1's 120 historical test borrowers were quarantined from Phase 1.2 development, cross-validation, associations, and model selection. The remaining 680 borrowers were used for exploratory development. A separately generated seed-20261010 cohort of 240 borrowers / 53271 transactions served as the fresh simulation holdout. Dates and labels follow `reports/data_generation_assumptions.md`: 2024 history, 2025-01-01 prediction, and a probabilistic day 1–90 default event. The label shares pre-loan ingredients such as income CV, outflow shortfall, and EMI ratio with feature columns, plus hidden profile adjustments. This is an artificial target mechanism with substantial Bernoulli noise, not independent repayment evidence.

## Cross-validation protocol and results

Reproducible stratified 5-fold outer CV (seed 20261009) evaluates every development borrower as an outer test record once. Within each outer-training portion, a stratified 80/20 inner fit/validation split trains LR/RF/XGBoost/constant-prior dummy; feature scaling is inside the LR pipeline. Validation ROC-AUC chooses the model; Platt calibration and the experimental maximum-F1 threshold use validation predictions only. Outer-fold test outcomes are used only for metrics. Transaction feature aggregates are deterministic row-wise calculations over the fixed pre-loan window, with no global learned preprocessing.

Average outer-fold default prevalence: **0.178**. A constant-prevalence ranking has ROC-AUC 0.500 and PR-AUC equal to default prevalence. Candidate raw ROC-AUC / PR-AUC / Brier are means ± fold SD:

```csv
model,folds,roc_auc_mean,roc_auc_sd,pr_auc_mean,pr_auc_sd,brier_mean,brier_sd,default_prevalence_mean
Logistic Regression,5,0.5728239221364222,0.031496044050285,0.2618294540894919,0.0338042299770666,0.2392545852502957,0.0047303272724571,0.1779411764705882
Prevalence Dummy,5,0.5,0.0,0.1779411764705882,0.0032883352610291,0.146285195806424,0.0021207134024557,0.1779411764705882
Random Forest,5,0.5670511583011584,0.0499829500334626,0.2359783396784154,0.0358897408439337,0.2035018875721873,0.0055077784690537,0.1779411764705882
XGBoost,5,0.5102227316602317,0.0336808559438718,0.2042200265993729,0.0067398625460499,0.1560612589120865,0.0046405552411102,0.1779411764705882
```

Model selection varied by fold: {'Logistic Regression': 3, 'Random Forest': 2}. Calibrated rows in the CV summary are conditional on a model being selected in that fold (so their fold counts are less than five); they should not be compared as an unconditional estimator. Full per-fold metrics, including calibrated selected candidates, are in `cross_validation_fold_metrics.csv`.

## Feature associations and risk bands

Point-biserial correlations and paired-bootstrap percentile 95% intervals use only the 680 nonhistorical-test development records (1000 resamples, seed 20261009). These are unadjusted exploratory associations across 40 correlated features; intervals are not multiplicity-adjusted and do not imply causation.

```csv
feature,point_biserial_r,bootstrap_95ci_low,bootstrap_95ci_high,n
negative_cashflow_months,0.1072876279239979,0.0385418381197854,0.1741219459438415,680
cashflow_volatility,0.1023567909375489,0.0255158685625744,0.1786748464590234,680
income_stability_index,-0.0875115137126344,-0.1613874988274305,-0.0087301362776846,680
income_cv,0.0843755701242243,0.0034594839826393,0.160169645513168,680
emi_to_income_ratio,0.0783962499540294,-0.0035531621205365,0.1509900308996744,680
emi_count,0.0759089158564128,0.0010854578477337,0.1481979498230858,680
essential_expense_ratio,0.0642311989689882,-0.0137665763354329,0.1429430231853302,680
emi_share_of_expenses,0.0626445537582297,-0.0125959159220066,0.1353388666034257,680
```

Predefined `income_cv` quartiles are cut using feature values without labels. Default rates rise modestly from the lower to upper band but the Wilson intervals overlap substantially:

```csv
risk_band,borrowers,default_rate,wilson_95ci_low,wilson_95ci_high
"(0.0168, 0.133]",170,0.1529411764705882,0.1065589539622371,0.2146616524426531
"(0.133, 0.2]",170,0.1647058823529411,0.1164821346381154,0.2277479427361004
"(0.2, 0.597]",170,0.188235294117647,0.1366094006208714,0.2536396186919961
"(0.597, 1.963]",170,0.2058823529411764,0.151924485190557,0.2728387405762991
```

The leading associations are small (absolute r near 0.08–0.11). Some features are constant in this simulator and have undefined correlation. This supports weak constructed signal plus random outcome noise, not a strong broad predictive signal.

## Fresh-seed holdout

Final model selection, Platt fit, and threshold selection used only the development fit/validation split; the new cohort was scored once. Validation selected **Random Forest**, threshold **0.1366** by validation F1. Fresh holdout prevalence was **0.150**. The train-prevalence dummy Brier was **0.1283**.

```csv
model,prediction,fresh_holdout_prevalence,roc_auc,pr_auc,brier_score,precision,recall,f1,threshold
Prevalence Dummy,raw,0.15,0.5,0.15,0.1283013894896193,0.0,0.0,0.0,0.5
Logistic Regression,raw,0.15,0.5061274509803921,0.167704883524435,0.2495724647612016,0.1530612244897959,0.4166666666666667,0.2238805970149253,0.5
Random Forest,raw,0.15,0.5561002178649238,0.1753876583488075,0.2057104409719152,0.1111111111111111,0.1944444444444444,0.1414141414141414,0.5
XGBoost,raw,0.15,0.5905501089324618,0.1858674386225373,0.131699651479721,0.0,0.0,0.0,0.5
Random Forest,calibrated,0.15,0.5561002178649238,0.1753876583488075,0.1283343647683888,0.1596244131455399,0.9444444444444444,0.2730923694779116,0.1365866235651121
```

The holdout's raw XGBoost AUC is higher than the validation-selected Random Forest, but this does not justify switching models after seeing holdout results. The calibrated Random Forest Brier should be compared with the prevalence baseline; any small difference is not calibration evidence on its own. At the validation-selected threshold, many observations are flagged; the objective uses F1 without a lender-approved false-negative/false-positive cost and is illustrative only.

## Validation/test ranking reversal

Historical Phase 1.1 validation/test ROC-AUCs were LR 0.488/0.666 and RF 0.468/0.640. Phase 1.2 did not use the old test borrowers. A 120-person test set had only about 21 defaults and 99 nondefaults, giving 2,079 positive-negative pairs underlying AUC. Rank estimates can move materially with a small number of pair orderings, and the 5-fold CV now shows fold SD around 0.031 for LR and 0.050 for RF. Different training subsets, noisy Bernoulli outcomes, and chance ordering are plausible reasons for reversal. It cannot be resolved by choosing whichever old test score is larger. The fresh cohort also shows performance depends on simulator draw and still represents only the same generator.

## Preservation, tests, and limits

Historical Phase 1.1 reports and its test metrics were left intact. Phase 1.2 outputs are confined to `reports/synthetic_phase1_2/`; no model artifacts are written. The existing UCI benchmark bundle and recovered metadata were not used for selection or overwritten.

Run `python scripts/validate_synthetic_signal.py` to reproduce the new analyses and `python -m pytest tests/ -q` for tests. The test suite verifies historical-test quarantine, outer-fold disjointness/coverage, deterministic generator behavior and nested event labels, bootstrap association output, validation-only threshold inputs, feature cutoff, and UCI artifact preservation. Phase 1.2 results remain synthetic and are not evidence for a real data pilot. The next meaningful validation needs a real, governed dataset with verified financial-source labels and lender-observed repayment outcomes.
