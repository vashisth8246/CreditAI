# Phase 2.3.1 — Independent Audit of the Leakage-Safe LendingClub Benchmark

**Audit date:** 2026-10-11
**Scope:** Reconcile feature counts, audit point-in-time feature availability, verify cohort selection and outcome bias, and independently reproduce the reported metrics of Phase 2.3.
**Method:** Re-read the source LendingClub CSV, the Phase 2.2 leakage audit, the Phase 2.3 feature decisions, and the metrics CSV; re-execute the preprocessing, models, and metric computation in an independent verification script; cross-check every number against the saved artifacts.
**No new model was trained for deployment.** The verification run used the identical seed, feature set, and preprocessing pipeline as Phase 2.3 purely to reproduce and confirm its numbers.

---

## 1. Executive Summary

| Area | Finding | Status |
|---|---|---|
| Feature-count discrepancy | Report claimed "50 excluded (43 leakage + 7 PII)"; actual `PROHIBITED_COLUMNS` = **47** (40 leakage/metadata + 7 PII). Code/CSV were always correct; only the report header was wrong. | **Documentation defect, corrected** |
| Feature decisions reconciliation | All 151 source columns have exactly one Phase 2.3 decision: 63 Included, 88 Excluded. Reconciles to source schema. | **Verified** |
| Point-in-time availability | All 63 retained features are documented Application / Application-Bureau / Origination fields. No unresolved timing fields found. Conservative set = 63. | **Verified** |
| Cohort selection | Closed-loan cohort = 1,348,099 (1,078,739 good + 269,360 bad). 912,602 active/censored loans excluded. Splits match reported counts exactly. | **Verified** |
| Outcome horizon | Confirmed **historical closed-loan outcome**, not a fixed-horizon default model. Selection/censoring bias from excluding active loans is **not eliminated**. | **Verified (with caveats)** |
| Metrics | All 9 model×split rows reproduced exactly: ROC-AUC, PR-AUC, Brier, log loss, KS, Gini, precision, recall, F1, confusion matrices. Confusion matrices sum to split sizes. | **Verified** |
| Threshold / calibration isolation | Thresholds (LR 0.16, HGB 0.17) selected on validation only. No calibration fitted anywhere (test set untouched). | **Verified** |
| Baseline ranking metrics | Prevalence baseline ROC-AUC, KS, Gini reported as `NaN` (undefined). | **Verified** |
| `/v1/score` contract | Remains `not_validated`, `default_probability: null`. | **Verified** |

---

## 2. Feature-Count Reconciliation

### 2.1 The discrepancy

The Phase 2.3 report section header read **"Prohibited Column Leakage Guard (50 Columns Excluded)"** and described the set as "43 leakage-related fields + 7 identifier/PII fields." However, the explicitly listed categories sum to only **47** columns:

| Category | Count |
|---|---:|
| Post-Origination Repayment/Recovery | 18 |
| Debt Settlement | 7 |
| Hardship Program | 15 |
| PII & Identifiers | 7 |
| **Total listed** | **47** |

The actual `PROHIBITED_COLUMNS` set in [scripts/phase_2_3_benchmark.py](file:///f:/NUV%20ACD/All%20SEM/7th%20Sem/ML&DS/New%20folder%20%283%29/CreditAI/scripts/phase_2_3_benchmark.py) contains exactly **47** entries, verified by `len(PROHIBITED_COLUMNS) == 47`. The set is identical to the 47 `Exclude` rows in [phase_2_2_feature_leakage_audit.csv](computer://f:/NUV%20ACD/All%20SEM/7th%20Sem/ML&DS/New%20folder%20%283%29/CreditAI/reports/phase_2_2_feature_leakage_audit.csv) (set equality confirmed).

**Root cause:** The "50 / 43 leakage" figure was carried over from the Phase 2.2 report narrative, which overstated the leakage count by 3 (the Phase 2.2 summary table listed 39 fields but the text said 43; neither matched the actual 40 leakage/metadata columns). The Phase 2.3 code never used 50 — it always used the correct 47. This is a **documentation-only defect**; no prohibited column was ever included, and no safe column was ever wrongly prohibited.

**Correction applied:** The report header is now "47 Columns Excluded" with a reconciliation note. A regression test (`test_prohibited_column_count_reconciliation`) pins `len(PROHIBITED_COLUMNS) == 47` and the 7-PII / 40-leakage split.

### 2.2 Full 151-column reconciliation

Every source column has exactly one final Phase 2.3 decision. The counts reconcile to the actual 151-column source schema:

| Audit action | Phase 2.3 Included | Phase 2.3 Excluded | Total |
|---|---:|---:|---:|
| Include | 63 | 40 | 103 |
| Exclude | 0 | 47 | 47 |
| Target Label | 0 | 1 | 1 |
| **Total** | **63** | **88** | **151** |

- **63 Included** = audit-Include columns that passed the train-set (>50% missingness) filter.
- **88 Excluded** = 47 prohibited (audit-Exclude) + 1 target (`loan_status`) + 40 audit-Include columns dropped because they were >50% missing in the 2007–2013 train split (joint-app fields, recency fields sparse in early cohorts, etc.).
- **No column has more than one decision; no source column is missing a decision.**

The complete per-column table (column, category, audit action, phase-2.3 decision, leakage risk, availability time, audit reason, phase-2.3 reason, reconciliation note) is in [reports/phase_2_3_1_feature_reconciliation.csv](computer://f:/NUV%20ACD/All%20SEM/7th%20Sem/ML&DS/New%20folder%20%283%29/CreditAI/reports/phase_2_3_1_feature_reconciliation.csv).

---

## 3. Point-in-Time Feature Availability Audit

### 3.1 Method

For every one of the 63 retained features, I checked:
1. The actual source column name.
2. Its documented meaning (from the Phase 2.2 audit `meaning` field).
3. Evidence of availability at origination (availability_time: Application / Application-Bureau / Origination).
4. Leakage risk (from the audit `leakage_risk` field).
5. Whether the timing is defensible or unresolved.

### 3.2 Findings

All 63 retained features fall into three timing categories, all defensible as point-in-time:

| Timing category | Count | Examples | Evidence of origination availability |
|---|---:|---|---|
| **Application** | 9 | `loan_amnt`, `emp_length`, `home_ownership`, `annual_inc`, `verification_status`, `purpose`, `addr_state`, `application_type`, `dti` | Self-reported at application / underwriting-verified at application |
| **Origination** | 9 | `funded_amnt`, `funded_amnt_inv`, `term`, `int_rate`, `installment`, `grade`, `sub_grade`, `initial_list_status`, `disbursement_method` | Set at loan origination (listing/underwriting decision) |
| **Application-Bureau** | 45 | `fico_range_low/high`, `delinq_2yrs`, `inq_last_6mths`, `open_acc`, `pub_rec`, `revol_bal`, `revol_util`, `total_acc`, `tot_cur_bal`, all `num_*`/`mo_sin_*`/`mths_since_*`/`total_*`/`bc_*`/`pct_*`/`percent_*` bureau fields | Credit-bureau snapshot pulled at application; the same fields' post-origination counterparts (`last_fico_range_high`, `last_credit_pull_d`, `collections_12_mths_ex_med`) are in the prohibited set |

### 3.3 Fields specifically investigated for timing ambiguity

| Column | Concern | Resolution |
|---|---|---|
| `fico_range_low`, `fico_range_high` | Could be current FICO, not application FICO | LendingClub documents these as the FICO score at the time the listing was created. The post-origination FICO (`last_fico_range_high/low`) is separately excluded. **Safe.** |
| `chargeoff_within_12_mths` | Similar name to excluded `collections_12_mths_ex_med` | `chargeoff_within_12_mths` is the application-time bureau count of charge-offs in the prior 12 months. `collections_12_mths_ex_med` is a rolling current snapshot updated post-origination. Distinct fields; the rolling one is excluded. **Safe.** |
| `funded_amnt`, `funded_amnt_inv` | Reflect investor funding, potentially post-listing | The loan is not originated until funded; at origination these are known constants. They do not encode repayment performance. **Safe.** |
| `revol_util`, `revol_bal` | Credit balances change over time | These are the application-time bureau snapshot; not updated in this dataset. **Safe.** |
| `dti` | Could be current DTI | Calculated at application from applicant-supplied income and bureau debts. **Safe.** |

### 3.4 Unresolved features and conservative-set impact

**No unresolved timing fields were found among the 63 retained features.** All have documented Application / Application-Bureau / Origination availability, and their post-origination counterparts (where they exist) are in the prohibited set.

Therefore the **conservative set = the full 63 retained features**. Excluding any of them would reduce model information without removing a demonstrated leakage risk. The excluded 88 columns (47 prohibited + 40 missingness + 1 target) remain excluded.

> Impact of excluding unresolved features: **none**, because none were identified.

---

## 4. Cohort Selection and Outcome Bias

### 4.1 Verified against the raw CSV

Re-reading `Data/archive/accepted_2007_to_2018Q4.csv` independently:

| `loan_status` (raw) | Count |
|---|---:|
| Fully Paid | 1,076,751 |
| Current | 878,317 |
| Charged Off | 268,559 |
| Late (31-120 days) | 21,467 |
| In Grace Period | 8,436 |
| Late (16-30 days) | 4,349 |
| Does not meet credit policy. Status:Fully Paid | 1,988 |
| Does not meet credit policy. Status:Charged Off | 761 |
| Default | 40 |
| (missing) | 33 |
| **Total raw** | **2,260,701** |

> **Reconciliation note (Phase 2.3.2):** An earlier draft of this section stated "Total raw: 2,260,694". The actual total row count is **2,260,701** (verified by independent chunked count, status frequency sum, and full load). This was a documentation-only typo of 7 rows; the cohort counts, split sizes, and all metrics remain correct. A regression test (`test_raw_row_count_reconciliation`) pins the correct total.

Target mapping (verified):
- **Good (0):** `Fully Paid` + `Does not meet the credit policy. Status:Fully Paid` = **1,078,739**
- **Bad (1):** `Charged Off` + `Default` + `Does not meet the credit policy. Status:Charged Off` = **269,360**
- **Excluded:** all other statuses + missing = **912,602**
- **Closed cohort:** 1,078,739 + 269,360 = **1,348,099** ✓ (matches report and split summary)

Issue-date parsing: `issue_d` is `Mon-YYYY` (e.g., `Jan-2015`); year extracted via regex `(\d{4})`. Term: `36 months` / `60 months` parsed to integers {36, 60}. No other term values appear.

### 4.2 Splits (verified exactly)

| Split | Issue years | n | Bad | Prevalence | 36-mo | 60-mo |
|---|---|---:|---:|---:|---:|---:|
| Train | 2007–2013 | 230,706 | 36,099 | 15.65% | 175,426 | 55,280 |
| Validation | 2014–2015 | 598,649 | 116,966 | 19.54% | 445,596 | 153,053 |
| Test | 2016–2018 | 518,744 | 116,295 | 22.42% | 402,184 | 116,560 |
| **Total** | | **1,348,099** | **269,360** | **19.98%** | **1,023,206** | **324,893** |

### 4.3 Selection bias from retaining only terminal-status loans

The closed-loan cohort excludes **912,602 loans (40.4% of all originations)** that had not reached a terminal status by the 2018Q4 dataset cutoff. This creates two distinct biases that **are not eliminated** by the exclusion:

1. **Survivorship / right-censoring bias.** A loan issued in 2018 that is still `Current` at cutoff is excluded, even though it might default in 2019–2023. Conversely, a 2018 loan that charged off early is included. The 2016–2018 test cohort is therefore enriched for **early defaults and early payoffs** and depleted for slow payers and late defaulters. The 22.42% test prevalence cannot be interpreted as the true default rate of 2016–2018 originations.

2. **Unequal follow-up across cohorts.** Follow-up time ranges from ~11 years (2007 originations) to <1 year (2018 Q4 originations). Because only terminal-status loans are kept, later cohorts systematically contain loans that resolved quickly. The rising prevalence across Train (15.65%) → Validation (19.54%) → Test (22.42%) partly reflects this censoring asymmetry, not necessarily a true increase in credit risk. A 60-month loan issued in 2017 has at most ~2 years of observed performance; if it `Charged Off` it is in the cohort, if it `Current` it is excluded — there is no way to observe its true 60-month outcome.

### 4.4 Confirmed nature of the benchmark

**This is a historical closed-loan outcome experiment, NOT a fixed-horizon default model.** The binary target is "did the loan reach a terminal bad state (Charged Off / Default) at any observed point before the dataset cutoff," not "did the loan default within N months of origination." No time-to-default or monthly performance series is available in the dataset, so a fixed-horizon target cannot be constructed. The reported metrics measure discrimination among loans that already terminated, not calibrated default probabilities over a fixed window.

Excluding active loans **does not eliminate censoring or selection bias** — it trades left-truncation/active-loan noise for a different form of survivorship bias. This must be disclosed whenever the benchmark results are interpreted.

---

## 5. Independent Metric Verification

### 5.1 Method

Saved predictions are not persisted by Phase 2.3 (only the aggregated metrics CSV). To verify independently, I re-ran the **identical** pipeline (same seed `42`, same 63 features, same train-only preprocessing, same model hyperparameters) and recomputed every metric from scratch, then compared against [phase_2_3_metrics.csv](computer://f:/NUV%20ACD/All%20SEM/7th%20Sem/ML&DS/New%20folder%20%283%29/CreditAI/reports/phase_2_3_metrics.csv).

### 5.2 Test-set results (computed == saved, to 4 decimals)

| Model | ROC-AUC | PR-AUC | Prev. | Brier | LogLoss | KS | Gini | P | R | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Prevalence Baseline | NaN | 0.2242 | 0.2242 | 0.1785 | 0.5479 | NaN | NaN | 0.0000 | 0.0000 | 0.0000 |
| Logistic Regression | 0.7005 | 0.3886 | 0.2242 | 0.1662 | 0.5153 | 0.2929 | 0.4010 | 0.3739 | 0.5383 | 0.4413 |
| HistGradientBoosting | 0.7056 | 0.3947 | 0.2242 | 0.1636 | 0.5035 | 0.2976 | 0.4112 | 0.3650 | 0.5799 | 0.4480 |

Every row reproduced exactly. Train and validation rows also reproduced exactly (see [phase_2_3_1_metric_verification.csv](computer://f:/NUV%20ACD/All%20SEM/7th%20Sem/ML&DS/New%20folder%20%283%29/CreditAI/reports/phase_2_3_1_metric_verification.csv)).

### 5.3 Verification checks (all passed)

| Check | Result |
|---|---|
| Confusion matrix (TN+FP+FN+TP) == split size, all 9 rows | ✓ (e.g., Test HGB: 285,104+117,345+48,853+67,442 = 518,744) |
| Bad count from confusion matrix (FN+TP) == split bad count | ✓ (Test: 48,853+67,442 = 116,295) |
| LR threshold selected on validation only | ✓ 0.16 (max F1 on val grid 0.10–0.90) |
| HGB threshold selected on validation only | ✓ 0.17 (max F1 on val grid 0.10–0.90) |
| No calibration fitted on any split | ✓ No calibrator in code; `calibrated` field absent |
| Baseline ranking metrics (ROC-AUC, KS, Gini) = NaN | ✓ Undefined for a constant predictor |
| PR-AUC definition | ✓ `average_precision_score(y, p)`; PR baseline = positive-class prevalence |
| Feature selection used only train missingness | ✓ `train_df[...].isna().mean() < 0.50` |
| Imputation/encoding/scaling fit on train only | ✓ Verified: imputer median equals train median; encoder categories from train only; scaler mean from train only |
| Random seed fixed | ✓ `RANDOM_SEED = 42`; models reproduce identically |

### 5.4 Threshold-free vs threshold-dependent metrics

- **Threshold-free (ranked):** ROC-AUC, PR-AUC, Brier score, log loss, KS, Gini. These evaluate the probability scores directly and do not depend on the selected threshold.
- **Threshold-dependent:** Precision, recall, F1, confusion matrix. These use the validation-selected threshold (LR 0.16, HGB 0.17) applied frozen to the test set.
- The constant baseline has no ranking ability, so ROC-AUC, KS, and Gini are correctly reported as `NaN`, not 0 or 0.5.

---

## 6. Project Integrity

- **No prior artifacts overwritten.** Phase 1 / Phase 2.1 / Phase 2.2 / UCI benchmark reports remain intact. The only Phase 2.3 report change is the corrected "47 Columns Excluded" header and an added reconciliation note.
- **`/v1/score` unchanged.** Confirmed via test `test_api_non_regression_contract`: `score_status == "not_validated"`, `default_probability is None`, `validated_risk_estimate is False`. No model wiring was added.
- **No raw borrower data or identifiers printed.** All cohort reporting uses aggregates only.
- **New regression tests added** (in [tests/test_phase23_benchmark.py](file:///f:/NUV%20ACD/All%20SEM/7th%20Sem/ML&DS/New%20folder%20%283%29/CreditAI/tests/test_phase23_benchmark.py)):
  - `test_prohibited_column_count_reconciliation` — pins `len(PROHIBITED_COLUMNS) == 47`.
  - `test_feature_decisions_full_reconciliation` — 151 columns, one decision each, 63+88=151, prohibited ⊆ excluded.
  - `test_confusion_matrix_totals_match_split_sizes` — CM sums equal split sizes.

---

## 7. Distinction: Verified Findings vs. Claims Not Independently Reproducible

| Item | Status |
|---|---|
| Feature counts (47 prohibited, 63 included, 88 excluded, 151 total) | **Verified** against code and CSVs |
| Cohort counts and split sizes | **Verified** by re-reading the raw CSV |
| All reported metrics (ROC-AUC, PR-AUC, Brier, log loss, KS, Gini, P/R/F1, CM) | **Verified** by independent re-run |
| Thresholds selected on validation only | **Verified** by code inspection + re-run |
| Preprocessing fit on train only | **Verified** by direct assertion of imputer/encoder/scaler statistics |
| Absence of post-origination leakage in the 63 features | **Verified** by field-level timing audit |
| Closed-loan outcome (not fixed-horizon) | **Verified** by dataset structure (no time-to-default) |
| True long-term default rate of 2016–2018 originations | **Not reproducible** — censored by the 2018Q4 cutoff; not claimed |
| Calibration quality | **Not applicable** — no calibration was performed; not claimed |
| Indian borrower credit-risk accuracy | **Not reproducible / not claimed** — no Indian data in this dataset |
| Commercial deployment readiness | **Not claimed** — model not wired to API |

---

## 8. Final Decisions

### 8.1 Historical U.S. benchmarking suitability — **QUALIFIED WITH LIMITATIONS**

The Phase 2.3 benchmark is a **valid historical closed-loan discrimination experiment** on U.S. LendingClub data:
- Genuine out-of-sample discrimination (HGB test ROC-AUC 0.7056, PR-AUC 0.3947 vs 0.2242 baseline) under strict leakage removal and chronological splitting.
- All metrics independently reproduced; no test-set leakage in preprocessing, feature selection, or thresholding.
- Limitations: (a) the target is a closed-loan outcome, not a fixed-horizon default; (b) the 2016–2018 test cohort is subject to survivorship/censoring bias from excluding 912K active loans; (c) prevalence trends across splits partly reflect unequal follow-up, not pure risk. These are documented and do not invalidate the benchmark as a historical U.S. discrimination benchmark.

### 8.2 Indian borrower validation readiness — **NOT READY**

No Indian data, features, or outcomes exist in the LendingClub dataset. No Account-Aggregator cash-flow features, UPI narration outcomes, CIBIL/CMR fields, or Indian macro factors are present. The benchmark says **nothing** about Indian borrower credit risk. Validation on an Indian cohort is a separate, future phase requiring its own data, leakage audit, and target definition.

### 8.3 Commercial deployment readiness — **NOT READY**

- `/v1/score` remains `not_validated` with `default_probability: null`.
- No model is wired into the production API.
- Calibration, fairness, stability, and regulatory review have not been performed.
- The closed-loan outcome target is not a deployable default-probability estimate for any fixed horizon.
- No claim of Indian credit-risk accuracy is made or should be inferred.

---

*End of Phase 2.3.1 independent audit.*
