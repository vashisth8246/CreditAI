# CreditAI Minimum Data Specification

**Version:** 1.0
**Date:** October 12, 2026
**Purpose:** Define the minimum fields required for a credible first experiment on Indian borrower credit-risk modeling

---

## Overview

This specification defines the minimum data fields required to conduct a meaningful feasibility study on whether application-time financial features can support credit-risk decision-making. The specification is designed to be flexible—lenders may provide additional fields, but the core fields below are necessary for a basic analysis.

**Important:** The target definition must be agreed with the lender based on their business context and data availability. We do not arbitrarily choose a default horizon or event type.

---

## Core Identifiers

### Pseudonymous Borrower/Application ID

| Field | Type | Required | Point-in-Time | Purpose | Leakage Risk | If Unavailable |
|---|---|---|---|---|---|---|
| `borrower_id` | String | Required | Yes | Unique identifier for each borrower/application (pseudonymized, not PAN/mobile/name) | None if pseudonymized | Analysis not possible - each record must be uniquely identifiable |

**Notes:**
- Use a pseudonymous ID (e.g., hash of actual ID) rather than direct identifiers
- Do not include PAN, mobile number, name, or other direct identifiers in the modeling view
- A separate re-identification key may be maintained by the lender for internal reference

---

## Temporal Fields

### Application and Decision Timestamps

| Field | Type | Required | Point-in-Time | Purpose | Leakage Risk | If Unavailable |
|---|---|---|---|---|---|---|
| `application_date` | Date | Required | Yes | Date when loan application was submitted | None if before decision | Chronological splitting not possible |
| `decision_date` | Date | Required | Yes | Date when underwriting decision was made | None | Cannot establish feature observation window |
| `disbursement_date` | Date | Optional | Yes | Date when loan was disbursed | None if after decision | May be needed for outcome observation window |

**Notes:**
- All features must be observable as of the `decision_date` or earlier
- `disbursement_date` may be needed to define the observation window for outcomes

---

## Application-Time Income and Repayment Capacity

### Income Features

| Field | Type | Required | Point-in-Time | Purpose | Leakage Risk | If Unavailable |
|---|---|---|---|---|---|---|
| `annual_income` | Numeric | Optional | Yes | Self-reported or verified annual income | None if verified at application | Exclude from feature set |
| `monthly_income` | Numeric | Optional | Yes | Monthly income (if annual not available) | None if verified at application | Exclude from feature set |
| `income_verification_status` | Categorical | Optional | Yes | Whether income was verified (e.g., "verified", "self-reported", "not provided") | None | Exclude from feature set |
| `employment_type` | Categorical | Optional | Yes | Employment status (salaried, self-employed, etc.) | None | Exclude from feature set |
| `employment_years` | Numeric | Optional | Yes | Years in current employment | None | Exclude from feature set |
| `industry` | Categorical | Optional | Yes | Industry sector for self-employed | None | Exclude from feature set |

**Notes:**
- Income features are useful for repayment capacity assessment
- Verification status helps assess data quality
- If unavailable, the model will rely on other features (e.g., bureau data, cash flow)

---

## Existing Debt and Credit History

### Bureau Features

| Field | Type | Required | Point-in-Time | Purpose | Leakage Risk | If Unavailable |
|---|---|---|---|---|---|---|
| `credit_score` | Numeric | Optional | Yes | Credit bureau score (e.g., CIBIL score) | None if pulled at application | Exclude from feature set |
| `num_open_accounts` | Numeric | Optional | Yes | Number of open credit accounts | None if from bureau snapshot | Exclude from feature set |
| `num_delinquent_accounts` | Numeric | Optional | Yes | Number of accounts with delinquency | None if from bureau snapshot | Exclude from feature set |
| `total_outstanding_debt` | Numeric | Optional | Yes | Total outstanding debt across all accounts | None if from bureau snapshot | Exclude from feature set |
| `credit_utilization` | Numeric | Optional | Yes | Credit utilization ratio | None if from bureau snapshot | Exclude from feature set |
| `num_inquiries_last_6m` | Numeric | Optional | Yes | Number of credit inquiries in last 6 months | None if from bureau snapshot | Exclude from feature set |
| `worst_delinquency_days` | Numeric | Optional | Yes | Worst delinquency in days past due | None if from bureau snapshot | Exclude from feature set |

**Notes:**
- Bureau features are strong predictors but require lender membership or partnership
- All bureau features must be from a snapshot pulled at or before the decision date
- Post-origination bureau updates (e.g., `last_credit_pull_d`) must be excluded

---

## Historical Cash Flow Summaries

### Bank Statement Aggregates

| Field | Type | Required | Point-in-Time | Purpose | Leakage Risk | If Unavailable |
|---|---|---|---|---|---|---|
| `avg_monthly_credits_6m` | Numeric | Optional | Yes | Average monthly credits over last 6 months | None if from pre-decision statements | Exclude from feature set |
| `avg_monthly_debits_6m` | Numeric | Optional | Yes | Average monthly debits over last 6 months | None if from pre-decision statements | Exclude from feature set |
| `net_cashflow_6m` | Numeric | Optional | Yes | Net cash flow (credits - debits) over last 6 months | None if from pre-decision statements | Exclude from feature set |
| `cashflow_volatility_6m` | Numeric | Optional | Yes | Standard deviation of monthly cash flow over last 6 months | None if from pre-decision statements | Exclude from feature set |
| `num_negative_months_6m` | Numeric | Optional | Yes | Number of months with negative cash flow in last 6 months | None if from pre-decision statements | Exclude from feature set |
| `avg_balance_6m` | Numeric | Optional | Yes | Average ending balance over last 6 months | None if from pre-decision statements | Exclude from feature set |

**Notes:**
- Cash-flow features are particularly relevant for MSME and thin-file borrowers
- All cash-flow aggregates must be computed from statements dated before the decision date
- Account Aggregator access can provide these features, but AA does not provide outcome labels

---

## Loan Origination Terms

### Loan Characteristics

| Field | Type | Required | Point-in-Time | Purpose | Leakage Risk | If Unavailable |
|---|---|---|---|---|---|---|
| `loan_amount` | Numeric | Required | Yes | Loan principal amount | None | Analysis not possible |
| `loan_tenure_months` | Numeric | Required | Yes | Loan tenure in months | None | Analysis not possible |
| `interest_rate` | Numeric | Optional | Yes | Interest rate (annualized) | None if set at origination | Exclude from feature set |
| `emi_amount` | Numeric | Optional | Yes | Equated monthly installment | None if computed at origination | Exclude from feature set |
| `product_type` | Categorical | Optional | Yes | Loan product type (e.g., personal loan, working capital) | None | Exclude from feature set |
| `purpose` | Categorical | Optional | Yes | Stated loan purpose | None | Exclude from feature set |

**Notes:**
- `loan_amount` and `loan_tenure_months` are required for outcome normalization (e.g., default per unit exposure)
- Interest rate and EMI are useful for repayment capacity assessment

---

## Repayment Events and Outcomes

### Dated Repayment History

| Field | Type | Required | Point-in-Time | Purpose | Leakage Risk | If Unavailable |
|---|---|---|---|---|---|---|
| `repayment_schedule` | Array of {date, amount_due} | Required | No | Scheduled repayment dates and amounts | N/A (future schedule) | Cannot define expected payments |
| `actual_repayments` | Array of {date, amount_paid} | Required | No | Actual repayment dates and amounts | N/A (post-origination) | Cannot compute outcomes |
| `current_balance` | Numeric | Required | No | Current outstanding balance | N/A (post-origination) | Cannot define exposure |
| `days_past_due` | Numeric | Required | No | Current days past due | N/A (post-origination) | Cannot define default |

**Notes:**
- These fields are NOT point-in-time—they are post-origination outcomes
- They must be excluded from the feature set used for prediction
- They are essential for defining the target variable

---

## Outcome Definition

### Target Variable

| Field | Type | Required | Point-in-Time | Purpose | Leakage Risk | If Unavailable |
|---|---|---|---|---|---|---|
| `default_flag` | Binary | Required | No | Whether loan reached default (1 = default, 0 = non-default) | N/A (outcome) | Analysis not possible |
| `default_date` | Date | Optional | No | Date when default occurred | N/A (outcome) | Cannot analyze time-to-default |
| `write_off_flag` | Binary | Optional | No | Whether loan was written off | N/A (outcome) | Cannot analyze write-off |
| `closure_status` | Categorical | Required | No | Loan closure status (e.g., "fully_paid", "charged_off", "active", "restructured") | N/A (outcome) | Cannot define cohort |

**Notes:**
- The target definition must be agreed with the lender
- Common definitions: 90+ DPD, 180+ DPD, write-off, or lender-specific criteria
- The observation window must be specified (e.g., 12 months, 24 months, or full tenure)
- Active loans must be flagged as censored

---

## Censoring and Special Cases

### Handling Incomplete Outcomes

| Field | Type | Required | Point-in-Time | Purpose | Leakage Risk | If Unavailable |
|---|---|---|---|---|---|---|
| `censoring_flag` | Binary | Required | No | Whether outcome is censored (e.g., loan still active, prepaid early) | N/A (outcome) | Cannot handle survivorship bias |
| `prepayment_flag` | Binary | Optional | No | Whether loan was prepaid early | N/A (outcome) | May bias analysis if not flagged |
| `restructuring_flag` | Binary | Optional | No | Whether loan was restructured | N/A (outcome) | May bias analysis if not flagged |
| `observation_end_date` | Date | Required | No | Date when observation of the loan ended | N/A (outcome) | Cannot define observation window |

**Notes:**
- Censoring is critical for unbiased analysis
- Loans that are still active, prepaid early, or restructured must be flagged
- The observation window for each loan must be clearly defined

---

## Feature and Outcome Definitions

### Metadata

| Field | Type | Required | Purpose |
|---|---|---|---|
| `field_name` | String | Required | Name of the field |
| `field_description` | String | Required | Clear description of what the field represents |
| `data_type` | String | Required | Data type (numeric, categorical, date, array) |
| `observation_timestamp` | Date | Required | When this field is known (for features) or observed (for outcomes) |
| `source_system` | String | Required | System where the field originates (e.g., "loan_origination_system", "bureau_api", "bank_statement_parser") |
| `missing_value_handling` | String | Required | How missing values should be handled (e.g., "impute_median", "treat_as_category", "exclude") |

**Notes:**
- A data dictionary with these metadata fields is essential for reproducibility
- Timestamps are critical for leakage prevention

---

## Source Provenance and Permissions

### Data Lineage

| Field | Type | Required | Purpose |
|---|---|---|---|
| `data_source_id` | String | Required | Identifier for the data source (e.g., "lender_production_db", "bureau_api") |
| `extraction_date` | Date | Required | When the data was extracted |
| `extraction_method` | String | Required | How the data was extracted (e.g., "sql_query", "api_call", "file_export") |
| `permission_basis` | String | Required | Legal basis for sharing (e.g., "data_use_agreement", "consent", "legitimate_interest") |
| `retention_period` | String | Required | How long the data may be retained |
| `deletion_date` | Date | Required | Date by which the data must be deleted |

**Notes:**
- Provenance tracking is essential for governance and compliance
- Permission basis must be documented in the Data Use Agreement

---

## What We Do Not Request

The following fields are NOT requested and should not be included:

- **Direct identifiers:** PAN, mobile number, Aadhaar number, passport number, voter ID
- **Raw identity documents:** Scanned copies of PAN card, Aadhaar card, passport
- **Passwords or credentials:** Bank account passwords, API keys, authentication tokens
- **Unrestricted account access:** Full transaction histories without time bounds
- **Post-origination leakage fields:** Fields that encode repayment performance (e.g., `total_pymnt`, `recoveries`, `last_fico_range_high`)
- **Sensitive personal information:** Medical records, biometric data, caste/religion (unless legally required and consented)

---

## Account Aggregator Note

Account Aggregator (AA) framework provides consented access to borrower financial data (bank statements, transactions, balances). However:

1. **AA provides features only, not labels.** The repayment outcomes must come from the lender's own loan performance data.
2. **AA data must be time-bounded.** Only data available before the decision date should be used for features.
3. **Consent is required per pull.** Each data pull requires explicit borrower consent via the AA consent artefact.
4. **AA is data-blind.** The AA itself cannot see the content; only the FIU (lender) receives decrypted data.

For a research collaboration, the lender would need to provide both:
- AA-consented feature data (if using AA for feature acquisition)
- Lender's own loan performance data (for outcomes)

---

## Target Definition Process

We do not arbitrarily choose a target definition. The process is:

1. **Review lender's business context:** Understand the product, typical loan tenures, and default definitions used in practice.
2. **Assess data availability:** Determine which events are actually observable in the historical data (e.g., is 90+ DPD tracked? Is write-off recorded?).
3. **Define observation window:** Agree on the time horizon for outcome observation (e.g., 12 months, 24 months, or full tenure).
4. **Specify censoring rules:** Define how to handle active loans, prepayments, and restructurings.
5. **Document the definition:** Clearly specify the target in the data dictionary with examples.

The target definition must be observable in the data and aligned with the lender's business use.

---

## Summary Checklist

For a credible first experiment, the lender should provide:

**Required:**
- Pseudonymous borrower/application ID
- Application date and decision date
- Loan amount and tenure
- Repayment schedule and actual repayments
- Default flag (or equivalent outcome)
- Closure status
- Censoring flag
- Observation end date
- Data dictionary with field descriptions and timestamps

**Optional but valuable:**
- Income and employment features
- Bureau features (credit score, delinquency history)
- Cash-flow aggregates from bank statements
- Interest rate and EMI
- Default date and write-off flag
- Prepayment and restructuring flags

**Not requested:**
- Direct identifiers (PAN, mobile, name)
- Raw identity documents
- Passwords or credentials
- Post-origination leakage fields
- Sensitive personal information beyond what is legally required

---

*This specification is a starting point for discussion. The exact fields will be refined based on the lender's data availability and business context.*
