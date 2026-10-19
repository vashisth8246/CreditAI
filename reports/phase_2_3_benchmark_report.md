# CreditAI Phase 2.3 — Leakage-Safe LendingClub Benchmark Report

## Executive Summary

Phase 2.3 establishes a reproducible, leakage-safe historical credit-risk benchmark using the U.S. LendingClub accepted loans dataset (`Data/archive/accepted_2007_to_2018Q4.csv`).

This experiment evaluates model performance strictly on mature closed consumer loans under point-in-time feature availability constraints and a rigorous chronological train/validation/test split design (Train: 2007–2013, Validation: 2014–2015, Test: 2016–2018).

All 43 post-origination repayment, collection, recovery, settlement, and hardship fields, as well as 7 direct PII/identifier columns, were strictly excluded from the feature set. Preprocessing transformations (imputation, ordinal encoding, scaling) were fitted **strictly on training data**. Model decision thresholds were selected **strictly on validation data** and evaluated on an untouched test set.

### Benchmark Performance Highlights (Untouched Test Set: 518,744 Closed Loans)

| Model Name | ROC-AUC | PR-AUC | Prevalence Baseline | Brier Score | Log Loss | KS Statistic | Gini | Selected Thresh | Precision | Recall | F1 Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Prevalence Baseline** | *N/A* | 0.2242 | 0.2242 | 0.1785 | 0.5479 | *N/A* | *N/A* | 0.50 | 0.0000 | 0.0000 | 0.0000 |
| **Logistic Regression** | 0.7005 | 0.3886 | 0.2242 | 0.1662 | 0.5153 | 0.2929 | 0.4010 | 0.16 | 0.3739 | 0.5383 | 0.4413 |
| **HistGradientBoosting** | **0.7056** | **0.3947** | 0.2242 | **0.1636** | **0.5035** | **0.2976** | **0.4112** | **0.17** | **0.3650** | **0.5799** | **0.4480** |

> Note: For the Prevalence Baseline, ROC-AUC, KS, and Gini are mathematically undefined because constant probability predictions produce an unranked score distribution.

### Explicit Qualification Decisions

1. **Suitability for Historical U.S. Offline Benchmarking**: `QUALIFIED WITH LIMITATIONS`
   - *Evidence*: Under strict leakage removal and chronological splitting, gradient boosted decision trees achieve a valid ROC-AUC of **0.7056** and PR-AUC of **0.3947** (relative to a 0.2242 default prevalence baseline) on 518,744 test loans, demonstrating genuine credit risk discrimination signal in historical U.S. peer-to-peer data.
2. **Suitability for Indian Borrower Validation**: `NOT QUALIFIED — MORE EVIDENCE REQUIRED`
   - *Evidence*: The dataset reflects U.S. peer-to-peer consumer loans (USD currency, FICO credit scores, U.S. regulatory environment). It contains no Indian borrower attributes, Account Aggregator consent flows, UPI narration features, or Indian bureau (CIBIL/CMR) metrics.
3. **Suitability for Commercial Deployment**: `NOT QUALIFIED — MORE EVIDENCE REQUIRED`
   - *Evidence*: API endpoint `/v1/score` remains in its safe skeleton state (`score_status: "not_validated"`, `default_probability: null`). No commercial deployment or live scoring is authorized.

---

## 1. Target Definition & Cohort Filtering

### Target Mapping
- **Good Cohort (Target = 0)**: `Fully Paid` (1,076,751) + `Does not meet credit policy... Fully Paid` (1,988) = **1,078,739 loans**.
- **Bad Cohort (Target = 1)**: `Charged Off` (268,559) + `Default` (40) + `Does not meet credit policy... Charged Off` (761) = **269,360 loans**.
- **Excluded Unseasoned Cohort**: `Current` (878,317) + `Late (31-120 days)` (21,467) + `In Grace Period` (8,436) + `Late (16-30 days)` (4,349) + `nan` (33) = **912,602 loans** (40.37% of raw dataset).
- **Total Closed Benchmark Cohort**: **1,348,099 loans** (Overall closed default rate = **19.98%**).

### Seasoning & Outcome Horizon Limitation (Maturity Caveat)

The binary target is a **historical closed-loan outcome**, not a fixed-horizon default flag. `loan_status` values of `Fully Paid`, `Charged Off`, `Default` (and their pre-2010 credit-policy variants) represent terminal states observed at the dataset cutoff (2018Q4). The contractual `term` is either 36 or 60 months.

- **We do NOT assume that every closed loan issued in 2016–2018 reached full contractual maturity.** A 60-month loan issued in 2018 that is `Fully Paid` was prepaid early; a 60-month loan issued in 2017 that is `Charged Off` defaulted before its 2022 maturity. Both are valid observed terminal outcomes.
- **Active/unseasoned loans are excluded.** Loans still `Current`, `In Grace Period`, `Late (16–30)`, or `Late (31–120)` at the 2018Q4 cutoff have no observed terminal outcome and are excluded (912,602 loans, 40.37% of the raw dataset).
- **No fixed-horizon target can be established.** The dataset provides only the final status, not time-to-default or monthly performance snapshots. Therefore the target is "did this loan reach a terminal bad state (charge-off/default) at any point before the cutoff," not "did it default within 12/36 months of origination." This is a defensible historical outcome label but must not be interpreted as a fixed-horizon default probability.
- **Term distribution is reported** (see split summary above). The 36-month share ranges from 76.0% (Train) to 77.5% (Test); the 60-month share is 24.0% (Train) to 22.5% (Test). All cohorts contain both terms, so neither term is dropped.

> [!IMPORTANT]
> The metrics below measure discrimination among **closed historical U.S. loans**. They are not calibrated 12-month or 36-month default probabilities and are not validated for any Indian borrower population.

---

## 2. Conservative Feature Set & Leakage Prevention

### Prohibited Column Leakage Guard (47 Columns Excluded)

> **Reconciliation note (Phase 2.3.1):** An earlier draft of this section stated "50 Columns Excluded (43 leakage + 7 PII)". The actual `PROHIBITED_COLUMNS` set contains exactly **47** columns: **40** post-origination/leakage/metadata fields (18 repayment/recovery + 7 debt-settlement + 15 hardship) and **7** PII/identifier fields. This was a documentation-only discrepancy; the code and `phase_2_3_feature_decisions.csv` always used the correct 47-column prohibited set. A full 151-column reconciliation is in [reports/phase_2_3_1_feature_reconciliation.csv](file:///f:/NUV%20ACD/All%20SEM/7th%20Sem/ML&DS/New%20folder%20%283%29/CreditAI/reports/phase_2_3_1_feature_reconciliation.csv).

- **Post-Origination Repayment/Recovery Fields (18 cols)**: `pymnt_plan`, `out_prncp`, `out_prncp_inv`, `total_pymnt`, `total_pymnt_inv`, `total_rec_prncp`, `total_rec_int`, `total_rec_late_fee`, `recoveries`, `collection_recovery_fee`, `last_pymnt_d`, `last_pymnt_amnt`, `next_pymnt_d`, `last_credit_pull_d`, `last_fico_range_high`, `last_fico_range_low`, `collections_12_mths_ex_med`, `policy_code`.
- **Debt Settlement Fields (7 cols)**: `debt_settlement_flag`, `debt_settlement_flag_date`, `settlement_status`, `settlement_date`, `settlement_amount`, `settlement_percentage`, `settlement_term`.
- **Hardship Program Fields (15 cols)**: `hardship_flag`, `hardship_type`, `hardship_reason`, `hardship_status`, `deferral_term`, `hardship_amount`, `hardship_start_date`, `hardship_end_date`, `payment_plan_start_date`, `hardship_length`, `hardship_dpd`, `hardship_loan_status`, `orig_projected_additional_accrued_interest`, `hardship_payoff_balance_amount`, `hardship_last_payment_amount`.
- **PII & Identifiers (7 cols)**: `id`, `member_id`, `url`, `desc`, `emp_title`, `title`, `zip_code`.

### Selected Point-in-Time Features (63 Features)
After filtering features with >50% missingness in the 2007–2013 Train split, **63 point-in-time features** (52 numerical, 11 categorical) were retained, including loan amount, interest rate, term, grade, sub-grade, annual income, DTI, FICO score ranges (`fico_range_low`, `fico_range_high`), open accounts, revolving utilization, and historical bureau trade line metrics.

> Complete machine-readable inclusion decisions are exported in [reports/phase_2_3_feature_decisions.csv](file:///f:/NUV%20ACD/All%20SEM/7th%20Sem/ML&DS/New%20folder%20%283%29/CreditAI/reports/phase_2_3_feature_decisions.csv).

---

## 3. Chronological Evaluation Design & Split Summary

The closed loan dataset was split strictly by loan origination date (`issue_d` year):

| Split Name | Issue Date Range | Total Closed Loans | Good Loans (0) | Bad Loans (1) | Default Prevalence | Term 36m | Term 60m |
|---|---|---:|---:|---:|---:|---:|---:|
| **Train** | 2007-01-01 to 2013-12-31 | 230,706 | 194,607 | 36,099 | 15.65% | 175,426 | 55,280 |
| **Validation** | 2014-01-01 to 2015-12-31 | 598,649 | 481,683 | 116,966 | 19.54% | 445,596 | 153,053 |
| **Test** | 2016-01-01 to 2018-12-31 | 518,744 | 402,449 | 116,295 | 22.42% | 402,184 | 116,560 |
| **Total** | **2007 to 2018Q4** | **1,348,099** | **1,078,739** | **269,360** | **19.98%** | **1,023,206** | **324,893** |

### Issue-Year Distribution per Split

| Year | Train | Validation | Test |
|---:|---:|---:|---:|
| 2007 | 603 | — | — |
| 2008 | 2,393 | — | — |
| 2009 | 5,281 | — | — |
| 2010 | 12,537 | — | — |
| 2011 | 21,721 | — | — |
| 2012 | 53,367 | — | — |
| 2013 | 134,804 | — | — |
| 2014 | — | 223,103 | — |
| 2015 | — | 375,546 | — |
| 2016 | — | — | 293,105 |
| 2017 | — | — | 169,321 |
| 2018 | — | — | 56,318 |

> Exported in [reports/phase_2_3_split_summary.csv](file:///f:/NUV%20ACD/All%20SEM/7th%20Sem/ML&DS/New%20folder%20%283%29/CreditAI/reports/phase_2_3_split_summary.csv).

---

## 4. Comprehensive Benchmark Results Matrix

Decision thresholds were selected on the Validation set to maximize F1 score (Logistic Regression: `0.16`, HistGradientBoosting: `0.17`).

| Model Name | Split | ROC-AUC | PR-AUC | Prev. Base | Brier | Log Loss | KS | Gini | Thresh | Precision | Recall | F1 | TN | FP | FN | TP |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Prevalence Baseline** | Train | *N/A* | 0.1565 | 0.1565 | 0.1320 | 0.4338 | *N/A* | *N/A* | 0.50 | 0.0000 | 0.0000 | 0.0000 | 194,607 | 0 | 36,099 | 0 |
| **Prevalence Baseline** | Validation | *N/A* | 0.1954 | 0.1954 | 0.1587 | 0.4993 | *N/A* | *N/A* | 0.50 | 0.0000 | 0.0000 | 0.0000 | 481,683 | 0 | 116,966 | 0 |
| **Prevalence Baseline** | Test | *N/A* | 0.2242 | 0.2242 | 0.1785 | 0.5479 | *N/A* | *N/A* | 0.50 | 0.0000 | 0.0000 | 0.0000 | 402,449 | 0 | 116,295 | 0 |
| **Logistic Regression** | Train | 0.6937 | 0.2885 | 0.1565 | 0.1235 | 0.4023 | 0.2803 | 0.3874 | 0.16 | 0.2509 | 0.6253 | 0.3581 | 127,216 | 67,391 | 13,527 | 22,572 |
| **Logistic Regression** | Validation | 0.7195 | 0.3818 | 0.1954 | 0.1451 | 0.4564 | 0.3204 | 0.4390 | 0.16 | 0.3419 | 0.5912 | 0.4332 | 348,579 | 133,104 | 47,821 | 69,145 |
| **Logistic Regression** | Test | 0.7005 | 0.3886 | 0.2242 | 0.1662 | 0.5153 | 0.2929 | 0.4010 | 0.16 | 0.3739 | 0.5383 | 0.4413 | 297,629 | 104,820 | 53,688 | 62,607 |
| **HistGradientBoosting**| Train | 0.7332 | 0.3457 | 0.1565 | 0.1191 | 0.3873 | 0.3423 | 0.4664 | 0.17 | 0.2777 | 0.6562 | 0.3902 | 132,986 | 61,621 | 12,410 | 23,689 |
| **HistGradientBoosting**| Validation | 0.7244 | 0.3837 | 0.1954 | 0.1430 | 0.4485 | 0.3287 | 0.4488 | 0.17 | 0.3317 | 0.6383 | 0.4365 | 331,248 | 150,435 | 42,311 | 74,655 |
| **HistGradientBoosting**| Test | **0.7056** | **0.3947** | 0.2242 | **0.1636** | **0.5035** | **0.2976** | **0.4112** | **0.17** | **0.3650** | **0.5799** | **0.4480** | 285,104 | 117,345 | 48,853 | 67,442 |

> Exported in [reports/phase_2_3_metrics.csv](file:///f:/NUV%20ACD/All%20SEM/7th%20Sem/ML&DS/New%20folder%20%283%29/CreditAI/reports/phase_2_3_metrics.csv).

---

## 5. Execution Environment & Reproducibility

### Execution Commands
```bash
# 1. Run leakage-safe benchmark experiment
python scripts/phase_2_3_benchmark.py

# 2. Run full repository test suite
python -m pytest
```

### Environment & Package Versions
- **Python**: `3.11.9`
- **scikit-learn**: `1.4.0` / runtime active
- **pandas**: `2.2.3`
- **numpy**: `1.26.4`
- **FastAPI**: `0.143.0`
- **pytest**: `9.1.1`
- **Random Seed**: `42`

### Full Test Suite Pass Verification
- **Total Test Cases**: **49 Passed, 0 Failed**.
  - `tests/test_phase23_benchmark.py`: 10 Passed (label mapping, chronological separation, feature leakage, preprocessing isolation, empty cohorts, missing columns, reproducibility, report schemas, API non-regression, term parsing)
  - `tests/test_phase22_audit.py`: 4 Passed
  - `tests/test_api_integration.py`: 11 Passed
  - `tests/test_api_contract.py`: 9 Passed
  - `tests/test_financial_pipeline.py`: 5 Passed
  - `tests/test_phase12_signal.py`: 3 Passed
  - `tests/test_pipeline.py`: 7 Passed
- **Unresolved Failures**: **0**

---

## 6. Safety & Operational Disclaimers

> [!WARNING]
> **OFFLINE U.S. BENCHMARK ONLY — NOT VALIDATED FOR INDIAN BORROWERS**
> - The performance metrics reported above reflect historical U.S. peer-to-peer consumer loans from 2007–2018Q4.
> - They do **not** demonstrate credit prediction accuracy for Indian retail borrowers, UPI transactional data, or Account Aggregator flows.
> - The API endpoint `/v1/score` remains in its safe unvalidated contract state (`scoring: "not_validated"`, `default_probability: null`).
> - No model trained in this phase has been wired into the live API.
