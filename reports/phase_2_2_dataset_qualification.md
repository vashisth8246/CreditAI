# CreditAI Phase 2.2 — Real Dataset Qualification and LendingClub Label Audit Report

## Executive Summary & Qualification Decisions

Phase 2.2 presents a leakage-aware dataset qualification audit evaluating the local LendingClub dataset (`Data/archive/accepted_2007_to_2018Q4.csv`) and existing UCI benchmarks (UCI Taiwan Credit Card Default, Statlog German Credit, UCI Credit Approval).

The objective of this phase is to establish whether any locally available dataset is suitable for a clearly defined historical credit-risk benchmark. **This phase is strictly an audit, not a model-training phase.** No new models were trained, API scoring remains disabled (`/v1/score` returns `not_validated` with `default_probability: null`), and no financial accounts were integrated.

### Explicit Qualification Decisions

1. **Suitability for Historical Offline Benchmarking**: `QUALIFIED WITH LIMITATIONS`
   - *Evidence*: The LendingClub dataset contains 2,260,701 loans with explicit origination dates (2007–2018Q4) and point-in-time underwriting features. However, offline benchmarking is **qualified only with strict limitations**: 40.37% of records (active `Current` loans and unseasoned delinquent loans) must be excluded to prevent severe outcome censoring bias, and 43 post-origination repayment/recovery fields plus 7 PII/identifier columns must be stripped to prevent target leakage.
2. **Suitability for Indian Borrower Validation**: `NOT QUALIFIED — MORE EVIDENCE REQUIRED`
   - *Evidence*: LendingClub reflects U.S. peer-to-peer consumer loans (USD currency, FICO credit scores, U.S. macro/regulatory environment). None of the local datasets contain Indian borrower features, Account Aggregator consent flows, UPI narrations with repayment outcomes, or Indian credit bureau (CIBIL/CMR) scores.
3. **Suitability for Commercial Deployment**: `NOT QUALIFIED — MORE EVIDENCE REQUIRED`
   - *Evidence*: The local LendingClub dataset copy lacks bundled license documentation establishing commercial distribution rights or data-subject consent for live scoring. API endpoint `/v1/score` remains unvalidated.

---

## 1. Local Data Inventory & Metadata Audit

| Dataset / File Path | Rows & Columns | File Size | Date Coverage | Source Documentation & License Status |
|---|---|---|---|---|
| `Data/archive/accepted_2007_to_2018Q4.csv` | 2,260,701 rows<br>151 columns | 1.56 GB (1,675,133,810 bytes) | Issue dates: 2007–2018Q4 (139 unique issue months) | Public Kaggle/figshare mirror of LendingClub data. **Unresolved local license**: No terms bundled with local CSV. Restrict to offline research. |
| `Data/archive/accepted_2007_to_2018Q4.xlsx` | 1,048,576 rows<br>151 columns | 630 MB (630,182,798 bytes) | Truncated by Excel row limit | **Do not use**: Incomplete truncated copy of CSV (46.4% of rows omitted). |
| `Data/credit_default/Dataset #2.../default of credit card clients.xls` | 30,000 rows<br>25 columns | 5.28 MB | April–Sept 2005 (Taiwan) | UCI Machine Learning Repository (**CC BY 4.0**). Validated offline Taiwan benchmark. |
| `Data/credit_default/Dataset #3.../german.data` | 1,000 rows<br>21 columns | 77.9 KB | 1994 (Germany, undated rows) | UCI Machine Learning Repository (**CC BY 4.0**). Good/Bad credit risk proxy class. |
| `Data/credit_default/Dataset #5.../crx.data` | 690 rows<br>16 columns | 31.4 KB | 1987 (Undated) | UCI Machine Learning Repository (**CC BY 4.0**). Screening approval decision, not default. |

> [!CAUTION]
> **Data Integrity Warning**: The Excel workbook `accepted_2007_to_2018Q4.xlsx` contains exactly 1,048,576 rows (Excel's maximum capacity). It truncates over 1.21 million loan records present in the CSV. All audits and future pipeline steps must use the CSV file with chunked processing.

---

## 2. LendingClub Provenance & Permission Audit

### Provenance Audit
- **Source**: The dataset originates from LendingClub's public peer-to-peer loan disclosures (2007–2018), mirrored on Kaggle and figshare.
- **Local File Inspection**: The local CSV file contains no header comments, license notice, or data-use agreement.
- **Sensitive & Identifying Fields**:
  - `id` & `member_id`: Direct loan/borrower keys.
  - `url`: Direct link containing loan ID.
  - `desc`: Borrower self-written application text (contains unstructured personal disclosures).
  - `emp_title`: Employer job title (unstructured high-cardinality free text with privacy risk).
  - `title`: Loan title string.
  - `zip_code`: 3-digit partial ZIP code.
- **Permission Assessment**: Marked as **UNRESOLVED PROVENANCE / UNVERIFIED COMMERCIAL LICENSE**. Public availability on Kaggle/figshare does not constitute a license for commercial re-identification or live API integration. All direct identifiers and free-text fields are flagged for mandatory exclusion.

---

## 3. LendingClub Candidate Outcome Label Audit

An audit of all 2,260,701 rows in `accepted_2007_to_2018Q4.csv` identified 10 distinct `loan_status` values (including nulls):

| `loan_status` Value | Row Count | Percentage | Proposed Target Classification | Inclusion Status | Technical Rationale |
|---|---:|---:|---|---|---|
| `Fully Paid` | 1,076,751 | 47.63% | **Good / Non-Default** | **Included** | Loan fully repaid principal & interest to maturity. |
| `Current` | 878,317 | 38.85% | **Ambiguous / Active** | **Excluded** | Active ongoing loan; outcome not yet observed (unseasoned). |
| `Charged Off` | 268,559 | 11.88% | **Bad / Default** | **Included** | Verified default written off by lender. |
| `Late (31-120 days)` | 21,467 | 0.95% | **Ambiguous / Delinquent** | **Excluded** | In-flight severe delinquency; final default/cure unobserved. |
| `In Grace Period` | 8,436 | 0.37% | **Ambiguous / Delinquent** | **Excluded** | 1-15 days late; active unseasoned status. |
| `Late (16-30 days)` | 4,349 | 0.19% | **Ambiguous / Delinquent** | **Excluded** | 16-30 days late; active unseasoned status. |
| `Does not meet credit policy... Fully Paid` | 1,988 | 0.09% | **Good / Non-Default** | **Included** | Legacy pre-2010 loan fully repaid under older criteria. |
| `Does not meet credit policy... Charged Off` | 761 | 0.03% | **Bad / Default** | **Included** | Legacy pre-2010 loan charged off under older criteria. |
| `Default` | 40 | 0.00% | **Bad / Default** | **Included** | Declared loan default. |
| `nan` (Missing) | 33 | 0.00% | **Ambiguous / Missing** | **Excluded** | Corrupted summary footer rows. |
| **Total** | **2,260,701** | **100.00%** | — | — | — |

### Target Definition & Maturity Analysis
1. **Bad Candidate Cohort (Default Target = 1)**: `Charged Off` + `Default` + `Does not meet credit policy... Charged Off` = **269,360 loans** (11.92% of total dataset).
2. **Good Candidate Cohort (Default Target = 0)**: `Fully Paid` + `Does not meet credit policy... Fully Paid` = **1,078,739 loans** (47.72% of total dataset).
3. **Ambiguous / Unseasoned Cohort (Excluded)**: `Current` + `Late` statuses + `In Grace Period` + `nan` = **912,602 loans** (40.37% of total dataset).
4. **Closed-Loan Default Rate**: Restricting the dataset to mature closed loans yields **1,348,099 loans** with an observed charge-off rate of **19.98%**.
5. **Fixed-Horizon Limitation**: `Fully Paid` status alone does not guarantee a fixed 12-month or 36-month default horizon without combining `issue_d` and `term` (36 vs 60 months). Loans issued in 2017–2018 with 60-month terms that remain `Current` cannot be evaluated without right-censoring adjustments.

---

## 4. Column-Level Feature Leakage Audit

All **151 columns** in `accepted_2007_to_2018Q4.csv` were audited and classified into three operational buckets:

- **Included Candidate Predictors**: **101 columns** (available at application/origination time: credit bureau metrics, income, DTI, FICO score ranges, loan terms).
- **Excluded Post-Origination / Leakage Fields**: **43 columns** (generated post-origination: payment totals, recoveries, updated FICO scores, hardship flags, debt settlement details).
- **Excluded PII / Identifiers / Metadata**: **7 columns** (`id`, `member_id`, `emp_title`, `url`, `desc`, `title`, `zip_code`).

### Summary Table of Excluded Post-Origination & Leakage Fields (43 Columns)

| Column Category | Specific Columns Excluded | Reason for Exclusion & Leakage Risk |
|---|---|---|
| **Repayment Totals** | `total_pymnt`, `total_pymnt_inv`, `total_rec_prncp`, `total_rec_int`, `total_rec_late_fee`, `last_pymnt_amnt` | Direct mathematical function of post-origination loan performance. |
| **Collections & Recoveries** | `recoveries`, `collection_recovery_fee`, `collections_12_mths_ex_med`, `tot_coll_amt` | Generated strictly post-default/charge-off. Direct target leakage. |
| **Post-Origination Balances** | `out_prncp`, `out_prncp_inv` | Reflects ongoing principal repayment state after loan origination. |
| **Updated Bureau Scores & Dates** | `last_fico_range_high`, `last_fico_range_low`, `last_pymnt_d`, `next_pymnt_d`, `last_credit_pull_d` | Post-origination credit score updates and tracking timestamps. |
| **Hardship Program (15 cols)** | `hardship_flag`, `hardship_type`, `hardship_reason`, `hardship_status`, `deferral_term`, `hardship_amount`, `hardship_start_date`, `hardship_end_date`, `payment_plan_start_date`, `hardship_length`, `hardship_dpd`, `hardship_loan_status`, `orig_projected_additional_accrued_interest`, `hardship_payoff_balance_amount`, `hardship_last_payment_amount` | Post-origination loan modification and financial distress indicators. |
| **Debt Settlement (7 cols)** | `debt_settlement_flag`, `debt_settlement_flag_date`, `settlement_status`, `settlement_date`, `settlement_amount`, `settlement_percentage`, `settlement_term` | Post-default debt restructuring and charge-off settlement terms. |

> [!IMPORTANT]
> Complete column-level details for all 151 fields are exported in [reports/phase_2_2_feature_leakage_audit.csv](file:///f:/NUV%20ACD/All%20SEM/7th%20Sem/ML&DS/New%20folder%20%283%29/CreditAI/reports/phase_2_2_feature_leakage_audit.csv).

---

## 5. Cross-Dataset Benchmark Suitability Comparison

| Dimension | LendingClub (U.S.) | UCI Taiwan Credit Card | Statlog German Credit | UCI Credit Approval |
|---|---|---|---|---|
| **Local File Path** | `Data/archive/accepted_2007_to_2018Q4.csv` | `Data/credit_default/.../default of credit card clients.xls` | `Data/credit_default/.../german.data` | `Data/credit_default/.../crx.data` |
| **Sample Size** | 2,260,701 loans | 30,000 accounts | 1,000 accounts | 690 applications |
| **Target Variable** | `loan_status` (Charge-off vs Paid) | `default payment next month` | `class` (Good vs Bad Risk) | `A16` (`+` vs `-` Approval) |
| **Target Nature** | Observed loan charge-off | Observed 1-month credit card default | Subjective credit risk class | Underwriting approval decision |
| **Geographic Relevance** | U.S. P2P loans | Taiwan credit cards | Germany bank loans | Confidential financial institution |
| **Time Horizon** | 2007–2018Q4 (12 years) | April–Sept 2005 (6 months) | 1994 (Undated) | 1987 (Undated) |
| **Indian Borrower Relevance** | **None** (USD / U.S. FICO) | **None** (TWD / Taiwan cards) | **None** (EUR / German banks) | **None** (Anonymized 1987 screening) |
| **License & Terms** | Unresolved local terms | UCI Repository (**CC BY 4.0**) | UCI Repository (**CC BY 4.0**) | UCI Repository (**CC BY 4.0**) |
| **Benchmark Status** | **Qualified with Limitations** | **Qualified Baseline** | **Legacy Benchmark** | **Not Qualified for Default** |

---

## 6. Audit Script & Test Suite Execution

### Audit Command
```bash
python scripts/phase_2_2_audit.py
```
- **Execution Time**: ~28 seconds (chunked streaming).
- **Outputs**:
  - `reports/phase_2_2_lendingclub_label_audit.csv` (10 status rows)
  - `reports/phase_2_2_feature_leakage_audit.csv` (151 audited column rows)

### Pytest Command
```bash
python -m pytest
```
- **Total Tests**: **39 Passed, 0 Failed** in 25.89s.
  - `tests/test_phase22_audit.py`: 4 Passed
  - `tests/test_api_integration.py`: 11 Passed
  - `tests/test_api_contract.py`: 9 Passed
  - `tests/test_financial_pipeline.py`: 5 Passed
  - `tests/test_phase12_signal.py`: 3 Passed
  - `tests/test_pipeline.py`: 7 Passed
- **Unresolved Failures**: **0**

---

## 7. Mandatory Disclaimers & Next Steps

1. **Scoring API Contract Preserved**: `/v1/score` continues to return `score_status: "not_validated"` and `default_probability: null`.
2. **No Model Training**: Phase 2.2 performed zero model training, hyperparameter tuning, or pipeline fitting.
3. **India Data Requirement**: Before any pilot for Indian borrowers, CreditAI must establish a formal data partnership with an Indian financial institution/NBFC to acquire consent-backed borrower features, bureau scores (CIBIL/CMR), and observed repayment histories.
