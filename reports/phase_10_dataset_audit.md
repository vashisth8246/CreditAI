# Phase 10 Unified Dataset Audit Report
**Project:** CreditAI  
**Phase:** 10 — Unified Dataset Audit, KNN Model Development, Feature Engineering, Evaluation and Lender Research  
**Audit Scope:** DS001–DS017, EXT001–EXT003  
**Status:** Completed  
**Verification Date:** 2026-10-27  

---

## 1. Executive Summary

A complete empirical audit was executed across all twenty registered datasets in the CreditAI repository. Every physical file was inspected directly on disk to measure existence, byte size, readability, column names, data types, missingness, duplicate records, identifier leakage, and supervised target suitability.

### Summary of Dataset Status
- **Qualified for Research (2):**
  - `DS001`: LendingClub accepted loans (1,348,099 closed-loan cohort with strict leakage exclusion).
  - `DS003`: Default of Credit Card Clients (Taiwan) (30,000 clean borrower records with next-month default target; CC BY 4.0).
- **Review Required (4):**
  - `DS004`: Statlog German Credit (1,000 records; academic non-commercial research use; German context 1994).
  - `DS005`: Statlog German Credit numeric variant (1,000 records; same restrictions).
  - `EXT002`: OpenML Credit-Risk-Dataset ID 43454 (32,581 records; remote candidate metadata; not downloaded).
  - `EXT003`: Indian SHG Microfinance Survey (PLOS ONE 2026; survey-based constructs; not downloaded).
- **Blocked from Supervised Default Research (14):**
  - `DS002`: LendingClub Excel-limited copy (truncated at 1,048,575 rows due to Excel ceiling; silently omits >1.2M rows).
  - `DS006`: UCI Credit Approval (target is application approval/rejection, not default; features permanently obfuscated).
  - `DS007`: CreditMitra UPI narrations (25 rows; no target; unverified borrower consent/license).
  - `DS008`–`DS013`: Synthetic outcomes, transactions, and features (simulated test artifacts; strictly prohibited from claiming real credit risk performance).
  - `DS014`: NPCI Monthly UPI statistics (macroeconomic aggregates across 11 annual workbooks; no borrower records).
  - `DS015`: RBI Industry-Wise Gross Bank Credit (macro industry aggregates; no borrower records).
  - `DS016`: RBI Deployment by Major Sectors (sector-level aggregates; no borrower records).
  - `DS017`: RBI District-Wise SCB Credit (corrupted workbook; unreadable ZIP archive structure).
  - `EXT001`: City Bank Vehicle Loan Default (remote competition data; redistribution prohibited; not downloaded).

---

## 2. Dataset Audit Table

| ID | Name | Format | Status on Disk | Rows | Cols | Target | Prevalence | Decision | Key Restrictions / Reason |
|:---|:---|:---|:---|:---:|:---:|:---|:---:|:---|:---|
| **DS001** | LendingClub accepted loans | CSV | Present (1.68 GB) | 2,260,701 | 151 | `loan_status` | 19.98% (closed) | **QUALIFIED_FOR_RESEARCH** | Historical U.S. offline benchmark; 47 post-origination fields prohibited; unseasoned loans excluded; no Indian claim. |
| **DS002** | LendingClub Excel copy | XLSX | Present (601 MB) | 1,048,575 | 151 | `loan_status` | Truncated | **BLOCKED** | Silently truncated at Excel 1M row ceiling (missing 1,212,126 rows). Defective and redundant. |
| **DS003** | Taiwan Credit Card Default | XLS | Present (5.28 MB) | 30,000 | 25 | `default payment next month` | 22.12% | **QUALIFIED_FOR_RESEARCH** | CC BY 4.0 license; 6-month repayment history; 0 missing values; Taiwan 2005 context; primary benchmark. |
| **DS004** | Statlog German Credit | DAT | Present (80 KB) | 1,000 | 21 | Attribute 21 | 30.00% | **REVIEW_REQUIRED** | Non-commercial research license; small sample (1k); German banking framework 1994. |
| **DS005** | Statlog German Credit Numeric | DAT | Present (100 KB) | 1,000 | 25 | Attribute 25 | 30.00% | **REVIEW_REQUIRED** | Numeric encoding of DS004; same licensing and sample size restrictions. |
| **DS006** | UCI Credit Approval | DATA | Present (30 KB) | 690 | 16 | Col 15 (`+`/`-`) | 44.49% | **BLOCKED** | Target is underwriting approval, NOT default; features permanently anonymized. |
| **DS007** | CreditMitra UPI | CSV | Present (2.6 KB) | 25 | 2 | None | N/A | **BLOCKED** | Only 25 text narrations; no credit target, no loan amounts, unverified consent. |
| **DS008** | Synthetic outcomes v1 | CSV | Present (28 KB) | 800 | 6 | `default_30d/60d/90d` | ~20% | **BLOCKED** | Synthetic simulation data; strictly for pipeline testing. |
| **DS009** | Synthetic transactions v1 | CSV | Present (13.8 MB) | 177,446 | 8 | None | N/A | **BLOCKED** | Synthetic transactions; strictly for testing. |
| **DS010** | Synthetic features v1 | CSV | Present (460 KB) | 800 | 43 | None | N/A | **BLOCKED** | Synthetic features; strictly for testing. |
| **DS011** | Synthetic outcomes v1.1 | CSV | Present (28 KB) | 800 | 7 | `default_30d/60d/90d` | ~20% | **BLOCKED** | Synthetic simulation data v1.1. |
| **DS012** | Synthetic transactions v1.1 | CSV | Present (13.9 MB) | 177,608 | 8 | None | N/A | **BLOCKED** | Synthetic transactions v1.1. |
| **DS013** | Synthetic features v1.1 | CSV | Present (450 KB) | 800 | 41 | None | N/A | **BLOCKED** | Synthetic features v1.1. |
| **DS014** | NPCI UPI Monthly Stats | XLSX | Present (11 files) | 126 | 4 | None | N/A | **BLOCKED** | Macroeconomic monthly volume/value aggregates; no borrower records. |
| **DS015** | RBI Industry Deployment | XLSX | Present (20 KB) | 142 | 20 | None | N/A | **BLOCKED** | Industry-level gross bank credit flows; no borrower outcomes. |
| **DS016** | RBI Major Sectors | XLSX | Present (100 KB) | 110 | 100 | None | N/A | **BLOCKED** | Macro sector banking aggregates; no borrower records. |
| **DS017** | RBI District-Wise SCB Credit | XLSX | Corrupted (92 MB) | 0 | 0 | None | N/A | **BLOCKED** | File is corrupted ('File is not a zip file'); completely unreadable. |
| **EXT001** | City Bank Vehicle Default | Remote | Not downloaded | 0 | 0 | `default` | Unknown | **BLOCKED** | External competition data; redistribution prohibited; not local. |
| **EXT002** | OpenML Credit Risk (43454) | Remote | Remote metadata | 32,581 | 12 | `loan_status` | 21.82% | **REVIEW_REQUIRED** | Remote OpenML dataset; not downloaded into local repository. |
| **EXT003** | Indian SHG Survey | Remote | Remote metadata | 400 | N/A | Survey construct | N/A | **REVIEW_REQUIRED** | Survey data on self-help groups, not loan-level transactional ledger; not downloaded. |

---

## 3. Methodological Guidance & Leakage Isolation

1. **DS001 Leakage Isolation:**
   - 47 columns must be permanently prohibited (7 PII fields + 40 post-origination fields including `recoveries`, `total_pymnt`, `last_pymnt_d`, `last_fico_range_high`).
   - Active/censored loans (`Current`, `Late`, `In Grace Period`) must be strictly excluded from closed-loan training/test splits.
2. **DS003 Leakage Isolation:**
   - `ID` column must be dropped prior to modeling to prevent memorization.
   - All repayment history predictors (`PAY_0`..`PAY_6`, `BILL_AMT1`..`BILL_AMT6`, `PAY_AMT1`..`PAY_AMT6`) temporally precede the October 2005 default target.
3. **No Synthetic Misrepresentation:**
   - Synthetic datasets (DS008–DS013) must remain strictly labeled as synthetic in all reports and code. They must never be used to claim empirical borrower risk accuracy.
