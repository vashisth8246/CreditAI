# CreditAI Phase 5 — Dataset Qualification Checklist

**Date:** October 12, 2026
**Purpose:** Define criteria for dataset qualification for research use

---

## Overview

This document defines the dataset qualification gate that determines whether a dataset is BLOCKED, REVIEW_REQUIRED, or QUALIFIED_FOR_RESEARCH.

**IMPORTANT:** QUALIFIED_FOR_RESEARCH does NOT mean production-ready or legally certified. It means the dataset passes documented checks for the specified research purpose.

---

## Qualification Status Values

### BLOCKED
Critical requirements are absent or failed. Dataset must not proceed to processing.

### REVIEW_REQUIRED
Material questions remain unresolved. Dataset requires human review before proceeding.

### QUALIFIED_FOR_RESEARCH
Documented checks passed and the data is approved for the specified research purpose.

---

## Qualification Criteria

A real dataset cannot proceed to Indian model training unless the review establishes the following:

### 1. Provenance and Source Identity

**Required:**
- [ ] Dataset has a unique identifier (`dataset_id`)
- [ ] Source organization is documented (`source_organization`)
- [ ] Provenance reference is documented (`provenance_reference`)
- [ ] Schema version is specified (`schema_version`)

**Evidence:**
- Dataset manifest includes all required provenance fields
- Source can be traced to an identifiable organization or system

**Failure:** BLOCKED if any required field is missing or invalid.

---

### 2. Documented Authorization and Permitted Use

**Required:**
- [ ] Permission status is documented (`permission_status`)
- [ ] Permission status is not "pending_review" or "rejected"
- [ ] Data Use Agreement (DUA) is signed and in place
- [ ] Legal/compliance review is complete
- [ ] Purpose limitation is clearly defined

**Evidence:**
- Manifest specifies `permission_status` as "authorized_documented" or "authorized_pending_legal_signoff"
- Signed DUA is available for review
- Legal counsel has reviewed the DUA

**Failure:** BLOCKED if permission status is "rejected" or "revoked". REVIEW_REQUIRED if permission status is "pending_review" or "under_review".

**Guardrail:** The metadata flag is NOT proof of legal permission. Human review of the actual authorization and agreement is required.

---

### 3. Suitable Borrower-Level Records

**Required:**
- [ ] Pseudonymous borrower/application ID is present (`borrower_id_field`)
- [ ] Records are at the borrower or application level (not aggregate)
- [ ] Direct identifiers (PAN, mobile, name) are excluded from modeling view
- [ ] Sample size is sufficient for meaningful analysis

**Evidence:**
- Manifest specifies `borrower_id_field`
- Data dictionary confirms pseudonymization
- Re-identification key is stored separately by the lender

**Failure:** BLOCKED if no borrower ID or if direct identifiers are present.

---

### 4. Point-in-Time Feature Availability

**Required:**
- [ ] Prediction timestamp is defined (`prediction_timestamp_definition.field_name`)
- [ ] Observation window is defined (`observation_window_definition`)
- [ ] All features have documented observation timestamps
- [ ] No features have observation timestamps after prediction timestamp

**Evidence:**
- Manifest specifies prediction timestamp field
- Field definitions include `observation_timestamp` for each feature
- Temporal audit confirms no future feature leakage

**Failure:** BLOCKED if prediction timestamp is missing or if future feature leakage is detected.

---

### 5. Meaningful, Documented Repayment Outcome

**Required:**
- [ ] Target field is specified (`outcome_definition.target_field`)
- [ ] Target event is specified (`outcome_definition.target_event`)
- [ ] Target definition is observable in the data
- [ ] Target prevalence is neither 0% nor 100%

**Evidence:**
- Manifest specifies target field and event
- Data quality check confirms target field exists
- Target balance check confirms both classes are present

**Failure:** BLOCKED if target field is missing or if prevalence is 0% or 100%.

---

### 6. Defensible Prediction Horizon and Mature Outcomes

**Required:**
- [ ] Target horizon is specified (`outcome_definition.horizon_months`)
- [ ] Horizon is a positive integer
- [ ] Observation windows are sufficient for the horizon
- [ ] Label maturity dates are documented

**Evidence:**
- Manifest specifies horizon in months
- Temporal audit confirms sufficient observation windows
- Immature label count is documented

**Failure:** BLOCKED if horizon is missing or invalid. REVIEW_REQUIRED if excessive immature labels are present.

---

### 7. Explicit Treatment of Censoring and Missing Labels

**Required:**
- [ ] Censoring field is specified (`outcome_definition.censoring_field`)
- [ ] Censoring rules are documented
- [ ] Treatment of censored records is specified (exclude, survival analysis, separate analysis)
- [ ] Missing label handling is documented

**Evidence:**
- Manifest specifies censoring field
- Censoring counts are documented in temporal audit
- Censoring treatment is documented in data dictionary

**Failure:** REVIEW_REQUIRED if censoring field is missing or if censoring treatment is not documented.

---

### 8. Leakage Controls

**Required:**
- [ ] No post-origination leakage fields are included
- [ ] No future feature leakage is detected
- [ ] No outcome-window leakage is detected
- [ ] Temporal audit passes with no ERROR-level issues

**Evidence:**
- Field definitions exclude post-origination fields
- Temporal audit confirms no leakage
- Leakage audit report is available

**Failure:** BLOCKED if any leakage is detected.

---

### 9. Sufficient Sample Quality and Subgroup Coverage

**Required:**
- [ ] Data quality checks pass with no ERROR-level issues
- [ ] Missingness is within acceptable thresholds
- [ ] Invalid data types are within acceptable thresholds
- [ ] Subgroup sizes (if analyzed) are sufficient for meaningful inference

**Evidence:**
- Data quality report shows no ERROR-level issues
- Missingness report shows acceptable levels
- Subgroup analysis (if performed) documents sample sizes

**Failure:** BLOCKED if data quality has ERROR-level issues. REVIEW_REQUIRED if WARNING-level issues exist.

---

### 10. Approved Secure Processing Environment and Retention/Deletion Plan

**Required:**
- [ ] Secure storage environment is prepared
- [ ] Access controls and logging are configured
- [ ] Retention period is agreed and documented
- [ ] Deletion process is documented
- [ ] Incident response plan is documented

**Evidence:**
- Security environment documentation is available
- Access control matrix is defined
- Retention and deletion schedule is in DUA
- Incident response procedures are documented

**Failure:** REVIEW_REQUIRED if secure environment or retention plan is not documented.

---

## Qualification Decision Logic

### BLOCKED
Return BLOCKED if ANY of the following are true:

1. Manifest validation fails (missing required fields, invalid values)
2. Permission status is "rejected" or "revoked"
3. Direct identifiers are present in the modeling view
4. Prediction timestamp is missing or invalid
5. Future feature leakage is detected
6. Target field is missing or invalid
7. Target prevalence is 0% or 100%
8. Any leakage is detected
9. Data quality has ERROR-level issues

### REVIEW_REQUIRED
Return REVIEW_REQUIRED if ANY of the following are true:

1. Permission status is "pending_review" or "under_review"
2. Censoring field is missing or censoring treatment is not documented
3. Excessive immature labels are present
4. Data quality has WARNING-level issues
5. Secure environment or retention plan is not documented
6. Any WARNING-level temporal audit issues

### QUALIFIED_FOR_RESEARCH
Return QUALIFIED_FOR_RESEARCH if ALL of the following are true:

1. Manifest validation passes
2. Permission status is "authorized_documented" or "authorized_pending_legal_signoff"
3. All 10 qualification criteria are met
4. No ERROR-level issues in any validation
5. No WARNING-level issues that require human review
6. Human review of authorization and agreement is complete

---

## What QUALIFIED_FOR_RESEARCH Does NOT Mean

QUALIFIED_FOR_RESEARCH does NOT mean:

- Production-ready models
- Legally certified for deployment
- Regulatory approval obtained
- Commercial deployment readiness
- Generalization beyond the studied product and time period
- Superiority to existing underwriting systems
- Fairness or stability validated

QUALIFIED_FOR_RESEARCH means:

- The dataset passes documented checks for the specified research purpose
- The data is suitable for the agreed research analysis
- The research can proceed under the agreed governance controls

---

## Human Review Requirements

The following always require human review, regardless of automated checks:

1. **Legal permission:** Signed DUA and legal counsel review
2. **Provenance verification:** Confirmation that data source is legitimate
3. **Pseudonymization verification:** Confirmation that direct identifiers are excluded
4. **Censoring treatment:** Confirmation that censoring handling is appropriate
5. **Subgroup analysis:** Confirmation that subgroup sizes support inference
6. **Security environment:** Confirmation that security controls are in place

Automated checks are necessary but not sufficient. Human judgment is required for material decisions.

---

## Re-Qualification

A dataset may require re-qualification if:

1. The manifest is updated (new fields, changed definitions)
2. The research purpose changes
3. Additional data is added
4. Retention period expires
5. Security controls are modified
6. Legal or regulatory requirements change

Re-qualification requires running the full qualification pipeline again.

---

## Summary

The dataset qualification gate provides:

1. **Explicit criteria:** 10 required criteria for qualification
2. **Clear status values:** BLOCKED, REVIEW_REQUIRED, QUALIFIED_FOR_RESEARCH
3. **Automated checks:** Manifest validation, data quality, temporal audit
4. **Human review requirements:** Legal, security, and judgment-based decisions
5. **Guardrails:** QUALIFIED_FOR_RESEARCH is not production certification
6. **Re-qualification process:** Mechanism for updating qualification

This gate ensures that only datasets meeting documented requirements proceed to model development.

---

*End of Phase 5 Dataset Qualification Checklist*
