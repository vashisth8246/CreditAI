# DATASET EXPLORATION & TECHNICAL FEASIBILITY REPORT
**Project:** CreditAI — ML + NLP-Powered Credit Risk Decisioning API for NBFCs  
**Author:** Senior Data Scientist & ML Systems Engineer  
**Stage:** Stage 1 — Technical Prototype  
**Date:** October 2026  
**Status:** Complete & Validated  

---

## 1. Executive Summary

This report establishes the data foundation and architectural feasibility for **CreditAI Stage 1**, an end-to-end technical prototype designed to demonstrate how automated transaction parsing, financial feature engineering, machine learning risk scoring, and explainable AI (SHAP) can power a credit-decisioning API for Non-Banking Financial Companies (NBFCs).

### Core Findings & Architectural Decisions
1. **Total Data Inventory Discovered:** A recursive forensic scan across the project discovered **28 total files** comprising **107,908,602 bytes (~102.9 MB)**, including 3 ZIP archives, 14 Excel files (`.xlsx`/`.xls`), 3 CSV/delimited data files, 2 documentation/codebook files, 2 index files, 1 Lisp knowledge-base file, 2 attribute name files, and 1 numeric data file.
2. **Primary Supervised ML Dataset Identified:** **UCI Default of Credit Card Clients (`default of credit card clients.xls`)** is unequivocally selected as the **Primary ML Training Dataset**. It provides 30,000 real individual borrower accounts, exactly zero missing values, 23 financial and behavioral features (6 months of delinquency status, statement balances, and actual payment amounts), and a clean, unambiguous binary target: `default payment next month` (22.12% default rate / 3.52:1 imbalance ratio).
3. **Secondary Validation Dataset:** **Statlog German Credit (`german.data`)** provides 1,000 individual loans with 20 features and a binary creditworthiness label (700 Good, 300 Bad). It serves as a benchmark for cost-sensitive classification (5:1 penalty for false negatives) and multi-dataset pipeline validation.
4. **NLP / Transaction Feature Engineering Prototype:** **`CreditMitra_transactions.csv`** contains 25 realistic UPI bank statement narration strings. It contains **zero default or repayment labels** and cannot train a credit risk classifier. It is classified strictly as an **NLP/Transaction Parsing & Feature Engineering Dataset** to demonstrate automated entity extraction (merchant identification, debit vs. credit, banking rail, and discretionary spending tags).
5. **Contextual Market Data (Non-Borrower Level):**
   - **NPCI UPI Monthly Statistics (11 files, 2016-17 to 2026-27):** 126 monthly aggregate observations tracking macro-level UPI growth in India (volume, transaction value, and participating banks). Contains zero borrower-level data.
   - **RBI DBIE Banking Data (3 files):** Macroeconomic aggregate credit deployment across industrial sectors. One file (`_Bank Credit of SCBs...xlsx`, 96.4 MB) was found to be corrupted during download due to an RBI server-side API error (`getBlobChunk` failure). These files represent macro/market context and cannot be joined with individual borrower records.
6. **Datasets Excluded:** **UCI Credit Approval (`crx.data` / `credit.lisp`)** is **strictly rejected** because it predicts historical human credit approval (`+`/`-`), not default risk, and all its features are obfuscated characters (`A1` to `A15`), destroying model explainability.

---

## 2. Complete Project Data Inventory (Phase 1)

All files within `F:\NUV ACD\All SEM\7th Sem\ML&DS\New folder (3)\CreditAI\Data\` were inventoried, categorized, and inspected for loadability.

| # | Relative File Path | File Name | Size (Bytes) | Category | Loading Library / Method | Native Load Status | Detailed Description / Role |
|---|---|---|---|---|---|---|---|
| 1 | `credit_default/Dataset #2 — UCI Default of Credit Card Clients/default+of+credit+card+clients.zip` | `default+of+credit+card+clients.zip` | 5,539,494 | Archive | `zipfile` | Verified | Raw ZIP archive containing the UCI credit card XLS file. |
| 2 | `credit_default/Dataset #2 — UCI Default of Credit Card Clients/default+of+credit+card+clients/default of credit card clients.xls` | `default of credit card clients.xls` | 5,539,328 | Dataset (Primary) | Excel COM / `win32com.client` | Requires COM / `xlrd` | 30,000 borrower records, 25 columns. Primary default prediction dataset. |
| 3 | `credit_default/Dataset #3 — German Credit/statlog+german+credit+data.zip` | `statlog+german+credit+data.zip` | 29,607 | Archive | `zipfile` | Verified | Raw ZIP archive containing German Credit files. |
| 4 | `credit_default/Dataset #3 — German Credit/statlog+german+credit+data/Index` | `Index` | 150 | Metadata | `open(encoding='latin1')` | Success | Index manifest of German credit package. |
| 5 | `credit_default/Dataset #3 — German Credit/statlog+german+credit+data/german.data` | `german.data` | 79,793 | Dataset (Secondary) | `pd.read_csv(sep=r'\s+')` | Success | 1,000 rows, 21 columns (categorical + numerical). Creditworthiness benchmark. |
| 6 | `credit_default/Dataset #3 — German Credit/statlog+german+credit+data/german.data-numeric` | `german.data-numeric` | 102,000 | Dataset (Variant) | `pd.read_csv(sep=r'\s+')` | Success | 1,000 rows, 25 integer columns. Pre-encoded numerical version of German credit. |
| 7 | `credit_default/Dataset #3 — German Credit/statlog+german+credit+data/german.doc` | `german.doc` | 4,679 | Documentation | `open(encoding='latin1')` | Success | Codebook and cost matrix definition (Prof. Hofmann, Hamburg). |
| 8 | `credit_default/Dataset #5 — UCI Credit Approval/credit+approval.zip` | `credit+approval.zip` | 13,901 | Archive | `zipfile` | Verified | Raw ZIP archive containing Quinlan credit approval files. |
| 9 | `credit_default/Dataset #5 — UCI Credit Approval/credit+approval/Index` | `Index` | 182 | Metadata | `open(encoding='latin1')` | Success | Index manifest of credit screening package. |
| 10 | `credit_default/Dataset #5 — UCI Credit Approval/credit+approval/credit.lisp` | `credit.lisp` | 12,314 | Metadata / Code | `open(encoding='latin1')` | Success | 125 instances in Common LISP format for Inductive Logic Programming (1992). |
| 11 | `credit_default/Dataset #5 — UCI Credit Approval/credit+approval/credit.names` | `credit.names` | 522 | Documentation | `open(encoding='latin1')` | Success | Description of Japanese Credit Screening domain theory. |
| 12 | `credit_default/Dataset #5 — UCI Credit Approval/credit+approval/crx.data` | `crx.data` | 32,218 | Dataset (Irrelevant) | `pd.read_csv(na_values='?')` | Success | 690 rows, 16 columns. Obfuscated credit approval dataset (Quinlan, 1987). |
| 13 | `credit_default/Dataset #5 — UCI Credit Approval/credit+approval/crx.names` | `crx.names` | 1,486 | Documentation | `open(encoding='latin1')` | Success | Documentation of attributes A1–A16 and class distribution (+/-). |
| 14 | `india_banking/RBI DBIE/Financial Sector/Bank Credit of SCBs — .../ _Bank Credit of SCBs...xlsx` | `_Bank Credit of SCBs...xlsx` | 96,469,123 | Dataset (Corrupted) | Truncated Zip / COM | Fails (BadZipFile) | 96.4 MB file corrupted during RBI portal download (`getBlobChunk` API failure). |
| 15 | `india_banking/RBI DBIE/Financial Sector/Industry-Wise Deployment.../Industry-Wise Deployment...xlsx` | `Industry-Wise Deployment...xlsx` | 21,609 | Macro Context | Excel COM / `openpyxl` | Requires COM / `openpyxl` | 3 sheets: 1990–2023 aggregate sectoral bank credit deployment in India. |
| 16 | `india_banking/RBI DBIE/Financial Sector/Sectoral Statistics/Deployment of Bank Credit by Major Sectors.xlsx` | `Deployment of Bank Credit by Major Sectors.xlsx` | 100,753 | Macro Context | Excel COM / `openpyxl` | Requires COM / `openpyxl` | 2 sheets: Monthly aggregate credit deployment across food/non-food sectors. |
| 17 | `india_upi/NPCI/2016-17/Product-Statistics-UPI-...-2016-17-Monthly.xlsx` | `...-2016-17-Monthly.xlsx` | 17,870 | Macro Context | Excel COM / `openpyxl` | Requires COM / `openpyxl` | 12 monthly rows: UPI volume, value, banks (FY 2016-17). |
| 18 | `india_upi/NPCI/2017-18/Product-Statistics-UPI-...-2017-18-Monthly.xlsx` | `...-2017-18-Monthly.xlsx` | 17,922 | Macro Context | Excel COM / `openpyxl` | Requires COM / `openpyxl` | 12 monthly rows: UPI volume, value, banks (FY 2017-18). |
| 19 | `india_upi/NPCI/2018-19/Product-Statistics-UPI-...-2018-19-Monthly.xlsx` | `...-2018-19-Monthly.xlsx` | 17,972 | Macro Context | Excel COM / `openpyxl` | Requires COM / `openpyxl` | 12 monthly rows: UPI volume, value, banks (FY 2018-19). |
| 20 | `india_upi/NPCI/2019-20/Product-Statistics-UPI-...-2019-20-Monthly.xlsx` | `...-2019-20-Monthly.xlsx` | 17,998 | Macro Context | Excel COM / `openpyxl` | Requires COM / `openpyxl` | 12 monthly rows: UPI volume, value, banks (FY 2019-20). |
| 21 | `india_upi/NPCI/2020-21/Product-Statistics-UPI-...-2020-21-Monthly.xlsx` | `...-2020-21-Monthly.xlsx` | 18,002 | Macro Context | Excel COM / `openpyxl` | Requires COM / `openpyxl` | 12 monthly rows: UPI volume, value, banks (FY 2020-21). |
| 22 | `india_upi/NPCI/2021-22/Product-Statistics-UPI-...-2021-22-Monthly.xlsx` | `...-2021-22-Monthly.xlsx` | 18,003 | Macro Context | Excel COM / `openpyxl` | Requires COM / `openpyxl` | 12 monthly rows: UPI volume, value, banks (FY 2021-22). |
| 23 | `india_upi/NPCI/2022-23/Product-Statistics-UPI-...-2022-23-Monthly.xlsx` | `...-2022-23-Monthly.xlsx` | 18,012 | Macro Context | Excel COM / `openpyxl` | Requires COM / `openpyxl` | 12 monthly rows: UPI volume, value, banks (FY 2022-23). |
| 24 | `india_upi/NPCI/2023-24/Product-Statistics-UPI-...-2023-24-Monthly.xlsx` | `...-2023-24-Monthly.xlsx` | 18,022 | Macro Context | Excel COM / `openpyxl` | Requires COM / `openpyxl` | 12 monthly rows: UPI volume, value, banks (FY 2023-24). |
| 25 | `india_upi/NPCI/2024-25/Product-Statistics-UPI-...-2024-25-Monthly.xlsx` | `...-2024-25-Monthly.xlsx` | 18,071 | Macro Context | Excel COM / `openpyxl` | Requires COM / `openpyxl` | 12 monthly rows: UPI volume, value, banks (FY 2024-25). |
| 26 | `india_upi/NPCI/2025-26/Product-Statistics-UPI-...-2025-26-Monthly.xlsx` | `...-2025-26-Monthly.xlsx` | 18,173 | Macro Context | Excel COM / `openpyxl` | Requires COM / `openpyxl` | 12 monthly rows: UPI volume, value, banks (FY 2025-26). |
| 27 | `india_upi/NPCI/2026-27/Product-Statistics-UPI-...-2026-27-Monthly.xlsx` | `...-2026-27-Monthly.xlsx` | 17,001 | Macro Context | Excel COM / `openpyxl` | Requires COM / `openpyxl` | 6 monthly rows (Apr–Sep 2026): UPI volume, value, banks (FY 2026-27). |
| 28 | `transactions/CreditMitra_transactions.csv` | `CreditMitra_transactions.csv` | 3,052 | NLP / Features | `pd.read_csv()` | Success | 25 rows, 2 columns. Real UPI statement narrations for NLP extraction. |

### Loading Environment & Technical Observations (Rule 6 Compliance)
- **Standard Pandas Excel Engines:** When executing standard `pd.read_excel()` in Python 3.11, the environment raises:
  - For `.xlsx`: `ImportError: 'Import openpyxl' failed. Use pip or conda to install the openpyxl package.`
  - For `.xls`: `ImportError: 'Import xlrd' failed. Install xlrd >= 2.0.1 for xls Excel support Use pip or conda to install the xlrd package.`
- **Inspection Protocol:** In accordance with **Rule 1** (*Do not download anything new*) and **Rule 2** (*Do not modify existing datasets*), all Excel files were successfully inspected using Windows native Excel COM automation via `win32com.client.Dispatch("Excel.Application")`, which runs natively on this host without installing external third-party Python wheels.
- **Corrupted File Diagnostic (RBI 96.4 MB):** Python's `zipfile` module threw `zipfile.BadZipFile: File is not a zip file`. Binary inspection of the final 2,048 bytes revealed that the file abruptly ends with the following raw server JSON response:
  ```json
  {"error":{"error_code":"WSR 00101","message":"An internal error occured while calling 'getBlobChunk' API. (Error: ERR_WIS_30270)"}}
  ```
  This proves the file was partially downloaded from the RBI DBIE portal and truncated by a server-side exception.

---

## 3. Dataset-by-Dataset In-Depth Analysis (Phase 2)

### 3.1 UCI Default of Credit Card Clients (`default of credit card clients.xls`)
- **Origin & Realism:** Real-world credit card data from a major cash and credit card issuer in Taiwan (Yeh & Lien, 2009). Real, individual borrower-level records.
- **Shape:** 30,000 rows × 25 columns.
- **Identification:** Column `ID` (integers 1 to 30,000, 0 duplicates, 0 nulls). Must be dropped prior to ML training.
- **Features Structure:**
  - **Demographics (4 features):**
    - `SEX`: Categorical (1 = Male: 11,888 [39.6%]; 2 = Female: 18,112 [60.4%]).
    - `EDUCATION`: Categorical (1 = Graduate School: 10,585; 2 = University: 14,030; 3 = High School: 4,917; 4 = Others: 123; 5/6/0 = Undocumented/Unknown: 345).
    - `MARRIAGE`: Categorical (1 = Married: 13,659; 2 = Single: 15,964; 3 = Others: 323; 0 = Undocumented: 54).
    - `AGE`: Numerical continuous (range: 21 to 79 years; mean: 35.49; median: 34.00; std: 9.22).
  - **Credit Facility (1 feature):**
    - `LIMIT_BAL`: Credit limit in New Taiwan Dollars (range: NT\$ 10,000 to NT\$ 1,000,000; mean: NT\$ 167,484; median: NT\$ 140,000).
  - **Repayment Status History (6 features):**
    - `PAY_0` (Sept 2005), `PAY_2` (Aug 2005), `PAY_3` (Jul 2005), `PAY_4` (Jun 2005), `PAY_5` (May 2005), `PAY_6` (Apr 2005).
    - Scale: `-2` = No consumption/inactive; `-1` = Paid in full; `0` = Revolving credit / paid minimum due; `1` = 1 month payment delay; `2` = 2 months delay; up to `8` = 8+ months delay.
  - **Billed Statement Amounts (6 features):**
    - `BILL_AMT1` to `BILL_AMT6`: Statement balance for September to April 2005.
    - Median values: NT\$ 17,071 to NT\$ 22,381. Features exhibit negative minimums (e.g., `BILL_AMT1` min: NT\$ -165,580), which reflect legitimate credit balances / overpayments.
  - **Previous Payment Amounts (6 features):**
    - `PAY_AMT1` to `PAY_AMT6`: Amount paid by the borrower in September to April 2005.
    - Range: NT\$ 0 to NT\$ 1,684,259; median: NT\$ 1,500 to NT\$ 2,100; right-skewed with heavy tails.
- **Target Variable:** `default payment next month`
  - Values: `0` = Repaid / Non-default (23,364 rows, 77.88%); `1` = Default (6,636 rows, 22.12%).
  - Imbalance Ratio: 3.52:1 (Non-default : Default).
- **Missing Values:** Exactly 0 missing values (100% complete across all 30,000 rows).
- **Leakage Assessment:** Zero data leakage. The repayment and billing histories cover April–September 2005, whereas the target strictly measures default in October 2005.
- **Fair Lending / PII:** Contains demographic indicators `SEX`, `AGE`, and `MARRIAGE`. In a production NBFC deployment, `SEX` and `MARRIAGE` are protected attributes and must be excluded or audited for demographic parity; for this Stage 1 technical prototype, they can be evaluated to demonstrate bias detection and feature ablation.

---

### 3.2 Statlog German Credit (`german.data` & `german.data-numeric`)
- **Origin & Realism:** Real bank credit assessment data collected by Prof. Hans Hofmann at the University of Hamburg (1994).
- **Shape:**
  - `german.data`: 1,000 rows × 21 columns (20 features + 1 target).
  - `german.data-numeric`: 1,000 rows × 25 columns (pre-encoded integer matrix created by Strathclyde University).
- **Identification:** None. No ID column exists.
- **Features Structure (`german.data`):**
  - **7 Numerical Features:** `duration_month` (4–72 months; median 18), `credit_amount` (250–18,424 DM; median 2,319.5 DM), `installment_rate` (1–4% of disposable income), `residence_since` (1–4 years), `age_years` (19–75 years; median 33), `existing_credits` (1–4), `maintenance_people` (1–2).
  - **13 Categorical Features:** `status_checking` (4 categories), `credit_history` (5 categories), `purpose` (10 categories), `savings_account` (5 categories), `employment_since` (5 categories), `personal_status_sex` (4 categories), `other_debtors` (3 categories), `property` (4 categories), `other_installment_plans` (3 categories), `housing` (3 categories), `job` (4 categories), `telephone` (2 categories), `foreign_worker` (2 categories).
- **Target Variable:** Attribute 21 (`target_creditworthiness`).
  - Values: `1` = Good Credit (700 rows, 70.0%); `2` = Bad Credit (300 rows, 30.0%).
  - Imbalance Ratio: 2.33:1.
- **Asymmetric Cost Matrix:** Documented in `german.doc`:
  $$\text{Cost} = \begin{pmatrix} C(\text{Good} \mid \text{Good}) = 0 & C(\text{Bad} \mid \text{Good}) = 1 \\ C(\text{Good} \mid \text{Bad}) = 5 & C(\text{Bad} \mid \text{Bad}) = 0 \end{pmatrix}$$
  Classifying a defaulting/bad borrower as good incurs 5× the economic loss of turning away a good borrower.
- **Missing Values:** 0 missing values.
- **Duplicates:** 0 duplicate rows.
- **Leakage Assessment:** Zero leakage. All attributes represent applicant state at the time of credit evaluation.

---

### 3.3 UCI Credit Approval (`crx.data`, `crx.names`, `credit.lisp`)
- **Origin:** Donated by J. Ross Quinlan (1987) from a confidential credit card approval study.
- **Shape:** 690 rows × 16 columns (15 features + 1 class attribute).
- **Features Structure:**
  - Continuous numerical: `A2` (age surrogate), `A3`, `A8`, `A11`, `A14`, `A15`.
  - Nominal categorical: `A1` (b, a), `A4` (u, y, l), `A5` (g, p, gg), `A6` (14 categories), `A7` (9 categories), `A9` (t, f), `A10` (t, f), `A12` (f, t), `A13` (g, p, s).
- **Target Variable:** `A16` (Class):
  - Values: `+` = Approved (307 rows, 44.49%); `-` = Rejected (383 rows, 55.51%).
- **Missing Values:** 67 total missing values across 37 rows (5.36% of instances), encoded as `?`:
  - `A1`: 12 (1.74%), `A2`: 12 (1.74%), `A4`: 6 (0.87%), `A5`: 6 (0.87%), `A6`: 9 (1.30%), `A7`: 9 (1.30%), `A14`: 13 (1.88%).
- **CRITICAL DEFECT FOR CREDIT RISK:**
  1. **Wrong Objective:** Predicts credit application *approval* (underwriter acceptance), NOT loan repayment or default. An approved borrower may default, and a rejected applicant's repayment capacity was never observed.
  2. **Zero Explainability:** Every feature name and categorical token is masked (`A1..A15`, `u`, `g`, `p`, etc.). SHAP output will output "Feature A6 = w contributes +0.4 to score", which is unusable for credit risk explanation to underwriters or regulators.

---

### 3.4 CreditMitra Transaction Data (`CreditMitra_transactions.csv`)
- **Origin:** Real/semi-anonymized transaction narration extract from an Indian retail bank statement.
- **Shape:** 25 rows × 2 columns (`Category`, `Narration`).
- **Data Types:** Both columns are text strings.
- **Missing Values & Duplicates:** 0 missing values, 0 duplicate rows.
- **Analysis of Fields:**
  - `Category`: Near-constant / uninformative (`UPI` across all 25 rows).
  - `Narration`: High-density raw banking narration strings conforming to standard Indian bank format:
    $$\text{UPI} / \{\text{DR} \mid \text{CR}\} / \{\text{RRN}\} / \{\text{Counterparty/Merchant}\} / \{\text{Bank}\} / **\{\text{Masked VPA}\} / \{\text{Purpose}\} // \{\text{UTR/Hash}\} / \{\text{Timestamp}\}$$
- **Discovered Transaction Metadata:**
  - **Transaction Type:** 22 Debits (`DR`), 3 Credits (`CR` — rows 6, 7, 19).
  - **Merchants / Counterparties:** E-commerce (`FLIPKART`), Travel (`IRCTC WEB`, `IRCTC CF`, `GOIBIBO`), Food (`SWIGGY`), Catering (`K K CATER`), Telco recharge (`MYJIO`, `JIO RECHA`), Investments (`ICCLGROWW`, `ICCL MU`), Peer-to-Peer individuals (`YASH NIGAM`, `DAULAT RA`, `TIPUCH AND`, `RASEEL A P`, `MAHEND RA`, `APOORV A S`).
  - **Banks Identified:** `HDFC`, `YESB`, `AIRP`, `UTIB` (Axis), `NSPB`, `SBIN`, `UCBA`.
  - **Temporal Span:** November 5, 2025 22:28:03 to November 15, 2025 17:20:27 (10 days).
  - **Defects & Limitations:**
    - No transaction amount column.
    - No customer/borrower identifier column.
    - **Zero default / repayment labels.**

---

### 3.5 NPCI UPI Monthly Product Statistics (11 Files, FY 2016-17 to FY 2026-27)
- **Origin:** National Payments Corporation of India (NPCI) official monthly product statistics.
- **Shape:** 11 individual annual files containing 12 monthly rows each (except FY 2026-27 which contains 6 months through September 2026), 4 columns per file. Total dataset: 126 monthly aggregate observations.
- **Variables:**
  1. `Month`: Monthly timestamp (e.g., `March-2017`, `September-2026`).
  2. `No. of Banks live on UPI`: Ecosystem capacity indicator (grew from 21 banks in 2016 to 756 banks in September 2026).
  3. `Volume (In Mn.)`: Total aggregate monthly transactions (grew from 6.37 Million in March 2017 to 24,068.38 Million in September 2026).
  4. `Value (In Cr.)`: Total aggregate monthly transaction value in INR Crores (grew from ₹2,425.14 Cr in March 2017 to ₹29,37,396.67 Cr in September 2026).
- **Entity Level:** Macroeconomic / National aggregate time series.
- **Missing Values:** 0 missing values.
- **Borrower Relevance:** Completely aggregate. Contains zero borrower, account, or credit-risk indicators.

---

### 3.6 RBI DBIE Banking Data (3 Files)
- **Origin:** Reserve Bank of India — Database on Indian Economy (DBIE).
- **Files & Contents:**
  1. `Industry-Wise Deployment of Gross Bank Credit.xlsx`: 3 sheets (`Data from 1997-2007`, `Old Format`, `New Format (2019 Onwards)`). Captures gross bank credit deployed across major manufacturing, infrastructure, and mining sectors (e.g., Coal, Iron & Steel, Engineering, Food Processing) in INR Crores.
  2. `Deployment of Bank Credit by Major Sectors.xlsx`: 2 sheets (`Old Format`, `New Format`). Monthly aggregate credit outstanding across major broad sectors: Priority Sector, Agriculture, Industry, Services, and Personal Loans in INR Crores.
  3. `_Bank Credit of SCBs...xlsx`: 96.4 MB file. Intended to provide district-wise and bank-group-wise credit deployment across India. Truncated and unreadable due to server-side `getBlobChunk` failure.
- **Entity Level:** Sectoral / Geographic aggregate banking statistics.
- **Borrower Relevance:** Zero individual borrower records, repayment histories, or default flags.

---

## 4. Deep-Dive Comparative Evaluation of Credit Datasets (Phase 3)

The following matrix formally evaluates the three candidate tabular credit datasets against the strict requirements of supervised credit risk modeling.

| Evaluation Criterion | UCI Default of Credit Card Clients | Statlog German Credit | UCI Credit Approval (`crx.data`) |
|---|---|---|---|
| **Underlying Problem** | Credit Card Default Prediction | Consumer Loan Creditworthiness | Credit Card Application Screening |
| **Prediction Target** | `default payment next month` | `target_creditworthiness` | `target_approval` (`A16`) |
| **Target Semantics** | `1` = Default, `0` = Full Repayment | `2` = Bad Risk, `1` = Good Risk | `+` = Approved, `-` = Rejected |
| **Target Nature** | **True Credit Default** | **Creditworthiness / Bad Loan** | **Underwriter Decision (Policy)** |
| **Observation Count** | 30,000 borrowers | 1,000 borrowers | 690 applicants |
| **Usable Features** | 23 numerical & categorical | 20 numerical & categorical | 15 completely masked features |
| **Missing Data** | 0 (0.0%) | 0 (0.0%) | 67 values across 37 rows (5.4%) |
| **Target Distribution** | 23,364 / 6,636 (22.12% default) | 700 / 300 (30.0% bad) | 307 / 383 (44.49% approved) |
| **Imbalance Ratio** | 3.52 : 1 | 2.33 : 1 | 1.25 : 1 |
| **Delinquency History** | 6 months (`PAY_0` to `PAY_6`) | Past payment delay category (`A30–A34`) | None |
| **Financial Exposure** | 6 months bills + 6 months payments | Credit amount + Installment rate | Masked numerical scales (`A3`, `A8`, etc.) |
| **Explainability (SHAP)** | **High** (Real financial features) | **High** (Interpretable attributes) | **Zero** (Masked tokens `A1`..`A15`) |
| **Feasibility for Credit Risk ML**| **Optimal (Primary Choice)** | **Strong (Secondary Benchmark)** | **Unusable (Rejection Mandated)** |

### Critical Analytical Distinctions
- **Approval vs. Default (Rule 8):** In lending operations, optimizing for *approval* trains the model to mimic the historical prejudices, conservative biases, and manual heuristics of human loan officers. Optimizing for *default* trains the model on ground-truth financial repayment failure, which is the foundational mathematical definition of Probability of Default ($PD$) in NBFC risk engines.
- **Feature Richness:** UCI Default contains longitudinal monthly time-series data per customer (balance migration, repayment velocity, payment-to-bill ratios), allowing modern feature engineering pipelines to compute utilization volatility and delinquency drift.

---

## 5. Transaction & NLP Dataset Analysis (Phase 4)

### Data Reality & Classification
`CreditMitra_transactions.csv` is an illustrative sample of 25 UPI banking narration strings.
- **Classification:** **Feature Engineering / NLP Dataset — NOT a supervised default-label dataset.**
- **Can it train a default model?** **ABSOLUTELY NOT.** There are no borrower IDs, no account balances, no repayment outcomes, and no default labels.

### Usability for Stage 1 Prototype
Despite its small size, this dataset provides the exact text patterns required to build and unit-test the **Stage 1 NLP Narration Parsing Subsystem**:

```
Raw Narration
  "UPI/DR/101895374870/FLIPKAR T /HDFC/**.PAYU@HDFCBANK/U PI TRAN//HDFD625E7E1E4A94657.../05/11/2025 22:28:03"
    │
    ▼ (Regex & Rule-Based NER Engine)
Parsed Transaction Attributes:
  ├── Payment Rail: UPI
  ├── Flow Direction: DEBIT (DR)
  ├── Reference ID (RRN): 101895374870
  ├── Counterparty / Merchant: FLIPKART
  ├── Sponsor / Processing Bank: HDFC Bank
  ├── Counterparty VPA: **.PAYU@HDFCBANK
  ├── Merchant Category: E-Commerce / Shopping
  ├── Discretionary vs. Non-Discretionary: Discretionary
  └── Transaction Timestamp: 2025-11-05 22:28:03
```

---

## 6. NPCI UPI Macro Data Analysis (Phase 5)

- **Structure:** 11 Excel spreadsheets covering April 2016 to September 2026.
- **Total Records:** 126 monthly aggregate observations.
- **Growth Dynamics:** Captures the exponential adoption curve of digital payments in India:
  - Monthly Volume: expanded from 6.37 Million (Mar 2017) to 24,068.38 Million (Sep 2026).
  - Monthly Value: grew from ₹2,425.14 Crores to ₹29,37,396.67 Crores (~$350B+ per month).
- **Technical Classification:** **Context / Market Data — NOT borrower-level credit-risk training data.**
- **Integration Boundary:** Must NOT be fed into the supervised tabular model. It can be used as an informative analytical backdrop in API documentation, executive dashboards, or market size benchmarking for the CreditAI pitch deck.

---

## 7. RBI DBIE Banking Data Analysis (Phase 6)

- **Available Tables:**
  1. *Deployment of Bank Credit by Major Sectors (Monthly, 2007–2024)*
  2. *Industry-Wise Deployment of Gross Bank Credit (Annual/Periodic, 1990–2023)*
  3. *Bank Credit of SCBs — Bank Group, Population Group, Occupation, District Wise (Corrupted / Incomplete)*
- **Data Granularity:** Aggregate macroeconomic industry-level and sector-level credit balances.
- **Technical Classification:** **Macro / Market Context Data — NOT borrower-level training data.**
- **Use Case in Stage 1:** Provides benchmark default or credit growth baselines across sectors (e.g., Agriculture vs. Services vs. NBFCs). Not suitable as feature inputs for individual borrower scoring in Stage 1.

---

## 8. Dataset Role Classification (Phase 7)

Every single file in the CreditAI project is classified into exactly one mutually exclusive role:

| Dataset / File Group | Assigned Category Role | Justification |
|---|---|---|
| `default of credit card clients.xls` | **A. PRIMARY ML TRAINING DATA** | 30,000 real borrower records, 0 missing values, longitudinal delinquency tracking, clean binary default target ($PD$). |
| `german.data` & `german.data-numeric` | **B. SECONDARY ML / VALIDATION DATA** | 1,000 records, 20 features, binary creditworthiness label with documented 5:1 asymmetric cost matrix for model cross-validation. |
| `CreditMitra_transactions.csv` | **C. NLP / TRANSACTION FEATURE DATA** | 25 rich UPI statement narrations to prove parsing, NER merchant extraction, and behavioral categorization algorithms. |
| `NPCI/2016-17` to `2026-27` (11 files) | **D. MACRO / MARKET CONTEXT DATA** | 126 monthly aggregate records of Indian digital payment adoption. Market context only. |
| `RBI DBIE/Financial Sector` (2 valid files)| **D. MACRO / MARKET CONTEXT DATA** | Macroeconomic sectoral credit deployment. Market context and industry benchmarking. |
| `german.doc`, `Index`, `credit.names`, `crx.names` | **E. DOCUMENTATION / METADATA** | Textual documentation, attribute definitions, and cost matrices. |
| `crx.data` (UCI Credit Approval) | **F. NOT USEFUL FOR STAGE 1** | Predicts application approval, not default; all 15 features are masked/obfuscated symbols (`A1..A15`). |
| `credit.lisp` | **F. NOT USEFUL FOR STAGE 1** | 1992 Japanese credit screening domain theory in Lisp syntax for symbolic AI; not tabular ML data. |
| `_Bank Credit of SCBs...xlsx` (96.4 MB) | **F. NOT USEFUL FOR STAGE 1** | Truncated and unreadable file resulting from RBI DBIE server crash (`getBlobChunk` failure). |
| 3 `.zip` archives | **E. DOCUMENTATION / METADATA** | Redundant byte-for-byte compressed source archives of unpacked project files. |

---

## 9. Cross-Dataset Compatibility Analysis (Phase 8)

A critical error in early-stage ML architectures is attempting to join heterogeneous public datasets into a single tabular training matrix. The following matrix evaluates cross-dataset joinability:

| Dataset Pair | Same Entity? | Same Target? | Same Currency / Time? | Realistic Join Key? | Decision |
|---|---|---|---|---|---|
| **UCI Default** + **German Credit** | No (Taiwan vs. Germany) | No (Default vs. Bad credit) | No (NT\$ 2005 vs. DM 1994) | None | **STRICTLY SEPARATE** |
| **UCI Default** + **CreditMitra** | No (Borrower vs. UPI txn) | No (Default vs. No label) | No (Taiwan 2005 vs. India 2025) | None | **STRICTLY SEPARATE** |
| **UCI Default** + **NPCI UPI** | No (Micro vs. Macro) | No (Default vs. Macro volume) | No (Taiwan vs. India) | None | **STRICTLY SEPARATE** |
| **UCI Default** + **RBI DBIE** | No (Micro vs. Sectoral) | No (Default vs. Gross credit) | No (Taiwan vs. India) | None | **STRICTLY SEPARATE** |
| **German Credit** + **UCI Approval** | No (Germany vs. Quinlan) | No (Creditworthiness vs. Approval) | No (DM 1994 vs. Masked 1987) | None | **STRICTLY SEPARATE** |

### Architectural Conclusion
**All datasets must remain strictly decoupled in separate pipeline modules.**
- The tabular ML risk engine trains on **UCI Default**.
- The secondary benchmark engine trains on **German Credit**.
- The NLP transaction engine parses **CreditMitra**.
- Market context metrics are served as static analytical background.

---

## 10. Data Quality Scoring (Phase 12)

Each dataset is scored from 1 (poor) to 10 (exceptional) across eight technical dimensions:

| Dimension | UCI Default Credit Card | Statlog German Credit | UCI Credit Approval (`crx.data`) | CreditMitra Transactions | NPCI UPI Statistics | RBI DBIE Sectoral |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **1. Availability** | 10 | 10 | 10 | 10 | 10 | 8 |
| **2. Completeness** | 10 (0% null) | 10 (0% null) | 8 (5.4% null) | 10 (0% null) | 10 (0% null) | 7 |
| **3. Target Quality** | 10 (True default) | 8 (Credit rating) | 2 (Approval policy) | 0 (No target) | 0 (No target) | 0 (No target) |
| **4. Feature Quality** | 9 (Time-series) | 8 (Mixed types) | 1 (Masked symbols) | 7 (Rich narrations) | 7 (Macro stats) | 6 (Macro stats) |
| **5. ML Usefulness** | 10 (30k rows) | 8 (1k rows) | 2 (Misleading) | 2 (Unlabeled) | 2 (Time-series) | 2 (Time-series) |
| **6. Relevance to CreditAI** | 9 | 8 | 1 | 9 (UPI in India) | 6 (Indian market) | 5 (Indian banking) |
| **7. Documentation** | 9 | 9 | 7 | 4 (Self-evident) | 9 | 6 |
| **8. Integration Simplicity** | 8 (Needs COM/xlrd) | 10 (Plain text) | 8 (Plain text) | 10 (Standard CSV) | 8 (Needs openpyxl) | 7 (Complex sheets)|
| **Overall Score (/10)** | **9.1** | **8.6** | **2.9** | **6.1** | **6.5** | **5.1** |
| **Stage 1 Decision** | **PRIMARY USE** | **SECONDARY USE** | **STRICT SKIP** | **NLP ENGINE ONLY** | **CONTEXT ONLY** | **CONTEXT ONLY** |

---

## 11. Target & Label Integrity Analysis

### UCI Default of Credit Card Clients
- **Label Name:** `default payment next month`
- **Definition:** Indicates whether the client defaulted on the subsequent monthly credit card payment ($Y=1$) or remained current ($Y=0$).
- **Integrity:** Highly robust. Collected from billing ledger settlement records. It is a genuine indicator of credit default.

### Statlog German Credit
- **Label Name:** Attribute 21
- **Definition:** Assessed creditworthiness by bank credit analysts ($1 = \text{Good}, 2 = \text{Bad}$).
- **Integrity:** Strong proxy for default risk, but incorporates credit officer evaluation rather than pure automated ledger default.

### CreditMitra & NPCI / RBI
- **Label Name:** None.
- **Integrity:** Zero credit risk labels exist. They must never be coerced into predicting default without ground-truth labels.

---

## 12. Data Leakage & Feature Engineering Risks

1. **Identifier Leakage:** In UCI Default, `ID` is a sequential index ($1 \dots 30000$). If included in model training, tree models may split on ID, causing severe overfitting. **Requirement:** Drop `ID` immediately.
2. **Temporal Precedence:** In UCI Default, features represent monthly statements from April to September 2005; the target measures default in October 2005. Features are strictly antecedent to the target. Zero temporal leakage.
3. **Negative Statement Balances:** `BILL_AMT1` to `BILL_AMT6` contain negative values (e.g., `-165580`). In banking, negative balances indicate customer credit balances (overpayments or refunds). These must **not** be clipped to zero, as they represent liquidity and low risk.
4. **Undocumented Categorical Levels:** In UCI Default:
   - `EDUCATION` contains levels `0`, `4`, `5`, and `6` in addition to `1, 2, 3`.
   - `MARRIAGE` contains level `0` in addition to `1, 2, 3`.
   - `PAY_0` to `PAY_6` contain levels `-2` and `0` in addition to `-1` and positive integers.
   - **Mitigation:** Map undocumented levels into an explicit `Unknown / Other` bucket during preprocessing to prevent pipeline inference failures.

---

## 13. Recommended Stage 1 Data Stack (Phase 9)

To achieve an 80% practical API/ML pipeline and 20% supporting context without unnecessary complexity, we recommend the following streamlined stack:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CREDITAI STAGE 1 DATA STACK                     │
└────────────────────────────────────────────────────────────────────────┘
                                    │
    ┌───────────────────────────────┼───────────────────────────────┐
    ▼                               ▼                               ▼
[PRIMARY ML ENGINE]         [NLP PARSER ENGINE]            [BENCHMARK ENGINE]
UCI Default Credit Card     CreditMitra Transactions       Statlog German Credit
(30,000 Borrowers)          (25 Indian UPI Narrations)     (1,000 Borrowers)
  • Default Risk Scoring      • Narration Tokenization       • Secondary Validation
  • Probability of Default    • Merchant / Entity NER        • Cost-Sensitive Matrix
  • Demo Score (0-1000)       • Direction (DR/CR)            • Model Generalizability
  • SHAP Explanations         • Discretionary Tagging        
```

---

## 14. Proposed Machine Learning Experiment Design (Phase 10)

This experiment plan is designed strictly for the primary dataset (`UCI Default of Credit Card Clients`).

### 14.1 Feature Engineering Plan
From the 23 raw features, engineer domain-specific credit risk signals:
1. **Credit Utilization Ratios ($CUR$):**
   $$CUR_t = \frac{\max(0, BILL\_AMT_t)}{LIMIT\_BAL} \quad \text{for } t \in \{1 \dots 6\}$$
2. **Payment-to-Bill Ratios ($PBR$):**
   $$PBR_t = \frac{PAY\_AMT_t}{\max(1, BILL\_AMT_t)} \quad \text{for } t \in \{1 \dots 5\}$$
3. **Delinquency Trend & Velocity:**
   $$\Delta \text{Delinquency} = PAY\_0 - PAY\_2, \quad \text{MaxDelinquency} = \max(PAY\_0 \dots PAY\_6)$$
4. **Balance Growth Rate:**
   $$\text{Balance Trend} = \frac{BILL\_AMT1 - BILL\_AMT6}{LIMIT\_BAL + 1}$$
5. **Revolving Credit Indicator:** Count of months where $PAY_t == 0$.

### 14.2 Train / Validation / Test Splitting Strategy
- **Split Ratio:** 70% Train (21,000), 15% Validation (4,500), 15% Test (4,500).
- **Stratification:** Stratified by target (`default payment next month`) to preserve the 22.12% default rate across all splits.
- **Random State:** Fixed seed (`42`) for full reproducibility.

### 14.3 Model Progression & Hyperparameters
1. **Baseline Model:** Logistic Regression with Standard Scaler and Weight Balancing (`class_weight='balanced'`). Establishes a linear benchmark.
2. **Comparison Model:** Random Forest Classifier (300 estimators, max depth 10, min samples leaf 20). Captures non-linear feature interactions.
3. **Primary Production Candidate:** XGBoost Classifier (`scale_pos_weight=3.52`, `max_depth=5`, `learning_rate=0.05`, `subsample=0.8`, `colsample_bytree=0.8`, `eval_metric='aucpr'`). Tree-based gradient boosting is the industry standard for tabular credit risk.

### 14.4 Model Explainability (SHAP)
- Use `shap.TreeExplainer` on the XGBoost model.
- Generate local waterfall plots for individual credit decisions in the FastAPI response payload:
  - Top 3 risk-increasing drivers (e.g., $PAY\_0 \ge 2$, Utilization $> 85\%$).
  - Top 3 risk-reducing drivers (e.g., High $PBR$, Clean repayment history).

### 14.5 Target Calibration & Credit Score Mapping (0–1000)
- Calibrate model probabilities using Isotonic Regression or Platt Scaling to ensure predicted probabilities match empirical default frequencies.
- Map Probability of Default ($PD$) to a standardized 0–1000 CreditAI Score using the standard FICO odds doubling methodology:
  $$\text{Score} = \text{Offset} - \text{Factor} \times \ln\left(\frac{PD}{1 - PD}\right)$$
  - Calibrated so $PD = 0.5 \implies \text{Score} = 500$; $PD \to 0 \implies \text{Score} \to 1000$; $PD \to 1 \implies \text{Score} \to 0$.

### 14.6 Comprehensive Credit Risk Evaluation Metrics
Rather than relying on misleading raw accuracy, the evaluation will measure:
- **ROC-AUC & PR-AUC:** Discrimination capability under class imbalance.
- **Kolmogorov-Smirnov (KS) Statistic:** Separation between cumulative good and bad distributions (target $KS > 40\%$).
- **Gini Coefficient:** $2 \times \text{ROC-AUC} - 1$.
- **Brier Score:** Mean squared calibration error of predicted probabilities.
- **Risk Decile Table:** Bad rate monotonic progression across score deciles (Decile 1 should capture $> 50\%$ of all defaults).

---

## 15. Proposed NLP & Transaction Parsing Pipeline (Phase 11)

This future experiment utilizes `CreditMitra_transactions.csv` to demonstrate financial feature extraction from unstructured UPI passbooks:

```
Raw Narration String: "UPI/DR/101895374870/FLIPKAR T /HDFC/**.PAYU@HDFCBANK/U PI TRAN//HDFD625E7E1E4A94657.../05/11/2025 22:28:03"
    │
    ▼ [Regex Tokenizer & Normalizer]
Tokens: ['UPI', 'DR', '101895374870', 'FLIPKAR T', 'HDFC', '**.PAYU@HDFCBANK', '05/11/2025 22:28:03']
    │
    ▼ [Entity Extractor & Keyword Categorizer]
Attributes:
  • Flow: DEBIT
  • Merchant: FLIPKART
  • Category: E-Commerce
  • Spend Type: Discretionary
    │
    ▼ [Aggregated Behavioral Feature Vector (Future Stage 2)]
Borrower Profile:
  • Discretionary Spend Ratio: % of debits on shopping/food/travel
  • UPI Transaction Velocity: Transactions per week
  • Recurring Payment Detection: Mutual fund / SIP debits (ICCLGROWW)
  • Salary Credit Detection: Recurring large CR transactions on 1st–5th of month
```

> **Mandatory Disclaimer (Rule 9):** Transaction features do not constitute a credit default score without historical loan repayment/default ground-truth labels. In Stage 1, this pipeline proves technical capability; in Stage 2, these engineered features will be joined with real lender repayment outcomes.

---

## 16. Final Decision Tables (Phase 13)

### Comprehensive Inventory & Dataset Decision Table

| Dataset | Rows | Columns | Target Variable | Target Semantics | Entity Level | Role Classification | Stage 1 Decision | Technical Rationale |
|---|---|---|---|---|---|---|---|---|
| **UCI Default Credit Card** | 30,000 | 25 | `default payment next month` | Binary (0=repaid, 1=default) | Individual Borrower | PRIMARY ML DATA | **USE (Primary)** | Optimal scale, real default ground-truth, 0 nulls, longitudinal features. |
| **Statlog German Credit** | 1,000 | 21 | `target_creditworthiness` | Binary (1=good, 2=bad) | Individual Borrower | SECONDARY ML DATA | **USE (Secondary)** | Benchmark model, asymmetric 5:1 loss validation, multi-dataset pipeline test. |
| **CreditMitra Transactions** | 25 | 2 | None | Unlabeled text | Transaction Narration | NLP / FEATURE ENG | **USE (NLP Only)** | Realistic Indian UPI narrations for parsing & feature extraction logic. |
| **NPCI UPI Statistics** | 126 | 4 | None | Macro aggregate stats | National Aggregate | MACRO CONTEXT | **CONTEXT ONLY** | Indian digital payment context. Not borrower-level data. |
| **RBI Sectoral Deployment** | 112 | 167 | None | Macro credit totals | Sectoral Aggregate | MACRO CONTEXT | **CONTEXT ONLY** | Sectoral credit deployment baseline. Not borrower-level data. |
| **RBI Industry Deployment**| 145 | 19 | None | Macro industry credit | Industrial Aggregate | MACRO CONTEXT | **CONTEXT ONLY** | Industry credit trends. Not borrower-level data. |
| **UCI Credit Approval** | 690 | 16 | `A16` (Approval) | Binary (+/- approval) | Individual Applicant | NOT USEFUL | **SKIP** | Predicts application approval, not default; all features masked. |
| **Credit LISP (`credit.lisp`)**| 125 | N/A | None | Symbolic predicates | Individual (Symbolic) | NOT USEFUL | **SKIP** | Non-tabular 1992 Lisp research codebook. |
| **RBI SCBs District-Wise** | Corrupt | Corrupt | None | Truncated file | District Aggregate | NOT USEFUL | **SKIP** | File download corrupted by RBI DBIE server error (`getBlobChunk`). |

### Summary Action Table

| Dataset | Stage 1 Decision | Implementation Purpose |
|---|---|---|
| **UCI Default of Credit Card Clients** | **USE** | Main ML risk engine, PD calculation, 0–1000 scoring, SHAP explainability. |
| **Statlog German Credit** | **USE** | Secondary benchmark model, cost-sensitive evaluation pipeline. |
| **CreditMitra Transactions** | **USE** | NLP narration parser, merchant entity extraction, behavioral feature prototype. |
| **NPCI UPI Statistics (11 Files)** | **CONTEXT ONLY** | Contextual background, market size metrics in dashboard/API documentation. |
| **RBI DBIE Credit Deployment (2 Files)** | **CONTEXT ONLY** | Sectoral credit growth context. |
| **UCI Credit Approval (`crx.data`)** | **SKIP** | Excluded: approval target ≠ default; masked features destroy explainability. |
| **UCI Credit Screening (`credit.lisp`)** | **SKIP** | Excluded: non-tabular symbolic Lisp codebook. |
| **RBI SCBs District-Wise (96.4 MB)** | **SKIP** | Excluded: corrupted archive file from RBI portal. |

---

## 17. Risks and Limitations

1. **Geographic & Currency Mismatch in Stage 1:** UCI Default reflects Taiwan borrowers (2005, NTD) and German Credit reflects German borrowers (1994, DM). While mathematically robust for technical prototyping of the ML pipeline, they do not model contemporary Indian borrower behavior or Indian credit bureau dynamics (CIBIL/Experian).
2. **Missing Transaction Target:** CreditMitra transaction data lacks credit default labels. Stage 1 cannot train a combined transaction-to-default model.
3. **Protected Attributes:** Demographics (`SEX`, `MARRIAGE`, `AGE`) exist in the UCI dataset. In production, lenders must adhere to fair lending standards (RBI fair practice codes).
4. **Transition to Stage 2:** Production deployment will require onboarding real NBFC partner data (Account Aggregator AA consent flows, bank statement PDFs, and verified 90+ DPD loan repayment outcomes).

---

## 18. Executive Conclusions & Exact Next Steps

### IF I WERE BUILDING CREDITAI STAGE 1 WITH THESE EXACT FILES, I WOULD USE:
1. **`UCI Default of Credit Card Clients` (`default of credit card clients.xls`)** as the **Primary ML Training Dataset** to build the core credit risk scoring engine, estimate Probability of Default ($PD$), compute the 0–1000 CreditAI demo score, and output real-time SHAP feature explanations.
2. **`CreditMitra_transactions.csv`** as the **NLP & Transaction Parsing Prototype** to build the text parsing pipeline that extracts merchant names, debit/credit flags, and expense categories from UPI passbook narrations.
3. **`Statlog German Credit` (`german.data`)** as the **Secondary Validation Dataset** to demonstrate that our ML training and evaluation harness generalizes across multiple credit portfolios and handles asymmetric default costs.
4. **`NPCI UPI Product Statistics` & `RBI DBIE Sectoral Files`** as **Contextual Reference Data** to enrich dashboard analytics and prototype documentation.
5. **Strictly Ignore:** `crx.data`, `credit.lisp`, and `_Bank Credit of SCBs...xlsx`.

---

### NEXT STEP AFTER THIS REPORT:
Upon your review and explicit approval of this report:
1. Initialize the Stage 1 repository structure (`src/data/`, `src/features/`, `src/models/`, `src/api/`).
2. Implement the data loader and feature engineering pipeline for `default of credit card clients.xls` (utilization ratios, payment ratios, delinquency progression).
3. Execute the 3-model progression experiment (Logistic Regression $\to$ Random Forest $\to$ XGBoost) and log ROC-AUC, PR-AUC, KS, Gini, and calibration metrics.
4. Integrate `shap.TreeExplainer` and the 0–1000 score transformation function.
5. Implement the regex/NLP parser for `CreditMitra_transactions.csv`.
6. Package the scoring and parsing engines into a clean FastAPI REST API endpoint (`POST /v1/score` and `POST /v1/parse-transactions`).
