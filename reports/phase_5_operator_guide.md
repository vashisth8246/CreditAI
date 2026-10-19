# CreditAI Phase 5 — Operator Guide

**Date:** October 12, 2026
**Purpose:** Plain-language guide for operators using the Phase 5 validation infrastructure

---

## Overview

This guide explains, in plain language, how to use the CreditAI Phase 5 validation infrastructure to inspect and qualify a research dataset from a lender partner.

---

## What Files a Future Partner Needs to Provide

### 1. Dataset File
The actual borrower-level data file, typically in one of these formats:
- CSV (comma-separated values)
- Parquet (columnar storage)
- JSON (JavaScript Object Notation)

**What it contains:**
- One row per borrower or loan application
- Columns for features (e.g., income, credit score, loan amount)
- Columns for outcomes (e.g., default flag, repayment history)
- Pseudonymous borrower IDs (no direct identifiers like PAN or mobile)

### 2. Data Dictionary
A document describing each field in the dataset.

**What it should contain:**
- Field name
- Description of what the field represents
- Data type (numeric, categorical, date, boolean)
- When the field is known (observation timestamp)
- Where the field comes from (source system)
- How missing values should be handled

### 3. Dataset Manifest
A structured metadata file (JSON format) describing the dataset.

**What it should contain:**
- Dataset ID and version
- Source organization and provenance reference
- Permission status (e.g., "authorized_documented")
- Prediction timestamp definition
- Observation window definition
- Outcome definition (target field, event, horizon)
- Field definitions with observation timestamps

The manifest is the primary input to the validation pipeline.

---

## What Metadata Must Accompany the Data

### Required Metadata Fields

| Field | Description | Example |
|---|---|---|
| `dataset_id` | Unique identifier for the dataset | "lender_abc_personal_loans_2024" |
| `dataset_version` | Version of the dataset | "1.0" |
| `schema_version` | Version of the schema | "1.0" |
| `source_organization` | Name of the data source organization | "ABC Lending Ltd." |
| `provenance_reference` | Reference to where the data came from | "Production database extract #12345" |
| `permission_status` | Status of authorization | "authorized_documented" |
| `prediction_timestamp_definition` | When the prediction is made | `{"field_name": "decision_date"}` |
| `observation_window_definition` | When features are observed | `{"start_field": "application_date", "end_field": "decision_date"}` |
| `outcome_definition` | How the target is defined | `{"target_field": "default_flag", "target_event": "90_plus_dpd", "horizon_months": 12}` |
| `field_definitions` | List of all fields with metadata | Array of field definition objects |
| `borrower_id_field` | Field containing pseudonymous borrower ID | "borrower_pseudo_id" |

### Optional but Recommended Metadata

| Field | Description | Example |
|---|---|---|
| `extraction_date` | When the data was extracted | "2024-01-15" |
| `retention_date` | When the data must be deleted | "2025-01-15" |
| `censoring_field` | Field flagging censored records | "censoring_flag" |
| `prepayment_field` | Field flagging prepaid records | "prepayment_flag" |
| `restructuring_field` | Field flagging restructured records | "restructuring_flag" |

---

## How the Validation Process Works

### Step 1: Create the Dataset Manifest
Create a JSON file with the metadata described above. This file tells the validation pipeline what to expect.

### Step 2: Load the Dataset
Load the dataset file (CSV, Parquet, etc.) into a list of dictionaries or a pandas DataFrame.

### Step 3: Run the Qualification Pipeline
Call the `qualify_dataset()` function with the dataset and manifest:

```python
from src.qualification.gate import qualify_dataset

result = qualify_dataset(df_rows, manifest)
print(result.status)  # BLOCKED, REVIEW_REQUIRED, or QUALIFIED_FOR_RESEARCH
print(result.message)
```

### Step 4: Review the Results
The qualification result includes:
- **Status:** BLOCKED, REVIEW_REQUIRED, or QUALIFIED_FOR_RESEARCH
- **Message:** Plain-language explanation of the result
- **Issues:** List of all validation issues with severity levels
- **Details:** Aggregate counts and diagnostic summaries

### Step 5: Address Issues (if any)
- **BLOCKED:** Critical errors must be fixed before proceeding
- **REVIEW_REQUIRED:** Material questions require human review
- **QUALIFIED_FOR_RESEARCH:** All checks passed, research can proceed

---

## Where Aggregate Reports Are Written

The validation pipeline does not automatically write reports to disk. Instead, it returns structured result objects that can be written to files by the operator.

### Example: Writing Reports

```python
import json

# Qualify the dataset
result = qualify_dataset(df_rows, manifest)

# Write the qualification result to a file
with open("qualification_result.json", "w") as f:
    json.dump({
        "status": result.status,
        "message": result.message,
        "manifest_valid": result.manifest_valid,
        "data_quality_passed": result.data_quality_passed,
        "temporal_audit_passed": result.temporal_audit_passed,
        "permission_status": result.permission_status,
        "issues": result.issues,
        "details": result.details,
    }, f, indent=2)
```

### Report Locations (Recommended)

Create a dedicated directory for each dataset validation:

```
reports/
└── dataset_validations/
    └── lender_abc_personal_loans_2024/
        ├── qualification_result.json
        ├── data_quality_report.json
        ├── temporal_audit_report.json
        └── summary.md
```

---

## What a BLOCKED Result Means

A BLOCKED result means critical requirements are not met. The dataset must not proceed to processing.

### Common Reasons for BLOCKED

1. **Missing required metadata:** The manifest is missing required fields
2. **Invalid permission status:** Permission is "rejected" or "revoked"
3. **Direct identifiers present:** PAN, mobile, or names are in the modeling view
4. **Missing prediction timestamp:** No field specified for when prediction is made
5. **Future feature leakage:** Features have observation timestamps after prediction
6. **Missing target field:** No target field specified or not found in data
7. **Invalid target prevalence:** Target is 0% or 100% (no variation)
8. **Leakage detected:** Post-origination or outcome-window leakage
9. **Data quality errors:** Critical data quality issues (missing required columns, invalid types)

### What to Do

1. Review the issues list in the qualification result
2. Fix the issues (update manifest, request missing data, exclude problematic fields)
3. Re-run the qualification pipeline
4. Do not proceed to model development until the result is not BLOCKED

---

## What a QUALIFIED_FOR_RESEARCH Result Means

A QUALIFIED_FOR_RESEARCH result means all documented checks passed for the specified research purpose.

### What It Does NOT Mean

QUALIFIED_FOR_RESEARCH does NOT mean:
- The dataset is production-ready
- The dataset is legally certified for deployment
- Regulatory approval has been obtained
- Models trained on this data can be deployed commercially
- The data is superior to other sources
- Fairness or stability has been validated

### What It Does Mean

QUALIFIED_FOR_RESEARCH means:
- The dataset passes all documented validation checks
- The data is suitable for the agreed research analysis
- The research can proceed under the agreed governance controls
- The manifest is complete and valid
- No critical errors or leakage were detected
- Human review of authorization is complete

### What Happens Next

After QUALIFIED_FOR_RESEARCH:
1. Proceed to model development (if approved by the lender)
2. Follow the agreed research scope
3. Adhere to data retention and deletion schedules
4. Respect publication and disclosure restrictions
5. Maintain security controls throughout the research

---

## What Still Requires Human Review

Even with automated validation, the following always require human review:

### 1. Legal Permission
- Signed Data Use Agreement must be reviewed by legal counsel
- Lawful basis for data sharing must be confirmed
- Compliance with DPDP Act 2023 and RBI regulations must be verified

### 2. Provenance Verification
- Confirm that the data source is legitimate
- Verify that the data actually comes from the stated organization
- Check that the provenance reference is accurate

### 3. Pseudonymization Verification
- Confirm that direct identifiers are excluded from the modeling view
- Verify that the re-identification key is stored separately by the lender
- Check that no sensitive information is inadvertently included

### 4. Censoring Treatment
- Confirm that the chosen censoring treatment is appropriate
- Verify that censoring rules are documented and followed
- Check that censoring does not introduce unacceptable bias

### 5. Subgroup Analysis
- If performing subgroup analysis, confirm that sample sizes support inference
- Verify that subgroup definitions are appropriate
- Check that subgroup results are not over-interpreted

### 6. Security Environment
- Confirm that security controls are in place and operational
- Verify that access logging is enabled
- Check that retention and deletion procedures are documented

Automated checks are necessary but not sufficient. Human judgment is required for material decisions.

---

## Example Workflow

### Step 1: Receive Data from Partner
Partner provides:
- Dataset file: `lender_abc_loans.csv`
- Data dictionary: `lender_abc_data_dictionary.pdf`
- Signed DUA: `data_use_agreement.pdf`

### Step 2: Create Manifest
Create `lender_abc_manifest.json` with metadata.

### Step 3: Load Dataset
```python
import pandas as pd

df = pd.read_csv("lender_abc_loans.csv")
df_rows = df.to_dict("records")
```

### Step 4: Load Manifest
```python
import json

with open("lender_abc_manifest.json", "r") as f:
    manifest = json.load(f)
```

### Step 5: Run Qualification
```python
from src.qualification.gate import qualify_dataset

result = qualify_dataset(df_rows, manifest)
```

### Step 6: Review Result
```python
print(f"Status: {result.status}")
print(f"Message: {result.message}")
print(f"Issues: {len(result.issues)}")
```

### Step 7: Write Report
```python
with open("qualification_result.json", "w") as f:
    json.dump(result.__dict__, f, indent=2)
```

### Step 8: Proceed or Address Issues
- If BLOCKED: Fix issues and re-run
- If REVIEW_REQUIRED: Review with legal/compliance teams
- If QUALIFIED_FOR_RESEARCH: Proceed to research (with human confirmation)

---

## Troubleshooting

### Issue: "Missing required field" error
**Cause:** Manifest is missing a required field.
**Solution:** Add the missing field to the manifest.

### Issue: "Future feature leakage" error
**Cause:** A feature has an observation timestamp after the prediction timestamp.
**Solution:** Exclude the feature or correct the observation timestamp in the manifest.

### Issue: "Target prevalence is 0%" error
**Cause:** All records have the same target value (no variation).
**Solution:** Check the target field and confirm it contains both classes.

### Issue: "Permission status not ready" warning
**Cause:** Permission status is "pending_review" or "under_review".
**Solution:** Complete human review of the authorization and agreement.

### Issue: "Immature labels" warning
**Cause:** Some records have observation windows shorter than the target horizon.
**Solution:** Exclude immature records or adjust the target horizon.

---

## Summary

The operator guide provides:

1. **File requirements:** What files the partner must provide
2. **Metadata requirements:** What metadata must accompany the data
3. **Validation process:** Step-by-step workflow
4. **Report locations:** Where to write validation reports
5. **Result interpretation:** What BLOCKED and QUALIFIED_FOR_RESEARCH mean
6. **Human review requirements:** What always requires human judgment
7. **Example workflow:** Concrete example of using the validation pipeline
8. **Troubleshooting:** Common issues and solutions

This guide enables operators to use the Phase 5 validation infrastructure effectively, even without deep technical knowledge of the implementation.

---

*End of Phase 5 Operator Guide*
