# CreditAI Phase 5 — Implementation Plan

**Date:** October 12, 2026
**Phase:** Data Readiness & Validation Infrastructure
**Status:** Engineering and research-readiness phase (NOT model-training phase)

---

## Executive Summary

This document outlines the implementation plan for Phase 5 of CreditAI, which builds the infrastructure needed to evaluate an authorized Indian borrower-level repayment dataset when one becomes available. This is an engineering and research-readiness phase—no model training will occur.

The project has already completed:
- **Phase 1:** UCI credit card benchmark and synthetic financial-behavior track
- **Phase 2:** API scaffolding and LendingClub benchmarking with independent audit
- **Phase 3:** Indian data feasibility research
- **Phase 4:** Partnership-readiness documentation and minimum data specification

Phase 5 builds upon this foundation to create validation infrastructure that will be ready to inspect and qualify real data when a lender partnership is secured.

---

## What Already Exists (Reusable Components)

### 1. API Contract and Validation
**Location:** `src/api/contract.py`, `src/api/app.py`

**Reusable components:**
- Date parsing and validation patterns (`_parse_strict_date`, `DATE_REGEX`)
- Contract error handling class (`ContractError`)
- Request validation patterns (required fields, type checking, forbidden fields)
- Safe response generation (`not_validated_response`)
- API endpoint returning `score_status: "not_validated"` and `default_probability: null`

**Status:** Fully functional and tested. Will NOT be modified.

### 2. Financial Feature Engineering
**Location:** `src/features/financial_features.py`

**Reusable components:**
- Feature computation patterns (ratios, volatility, growth, cashflow metrics)
- Time-bounded transaction filtering
- Pseudonymization patterns (no direct identifiers)

**Status:** Fully functional. Will be extended for new feature types if needed.

### 3. Testing Infrastructure
**Location:** `tests/`, `pytest` configuration

**Reusable components:**
- Test patterns for validation logic
- Synthetic fixture patterns
- Regression test patterns (e.g., `test_phase23_benchmark.py`)

**Status:** Functional. Will be extended with new data-validation tests.

### 4. Report Generation Patterns
**Location:** `reports/` directory

**Reusable components:**
- Markdown report templates
- CSV report patterns (e.g., `phase_2_3_1_feature_reconciliation.csv`)
- Evidence table patterns

**Status:** Functional. Will be extended with Phase 5 reports.

### 5. Dependencies
**Location:** `requirements.txt`

**Existing dependencies sufficient for Phase 5:**
- `pandas>=2.0.0` - Data manipulation
- `numpy>=1.24.0` - Numerical operations
- `scikit-learn>=1.4.0` - Metric computation
- `pytest>=7.0.0` - Testing
- `fastapi>=0.115.0`, `pydantic>=2.7.0` - Schema validation

**Status:** No new dependencies required.

---

## What Needs Implementation

### 1. Data-Intake Contract Module
**New module:** `src/data_intake/contract.py`

**Purpose:** Validate a proposed research dataset before processing.

**Required functionality:**
- Dataset manifest validation (unique dataset identifier, source organization, provenance reference)
- Permission/authorization status metadata
- Schema version validation
- Prediction timestamp and observation-window definitions
- Feature definitions and feature availability timestamps
- Borrower/application pseudonymous identifiers
- Loan origination details where applicable
- Repayment event timestamps and amounts
- Outcome definition, horizon, maturity, and censoring rules
- Missing-value conventions
- Data dictionary and permitted-use notes

**Validation behavior:** Fail closed if required metadata is absent, contradictory, or invalid.

**Guardrails:**
- Do not treat a metadata flag as proof of legal permission
- Require documented human review of authorization before real-data processing
- Never place names, phone numbers, government identifiers, bank account numbers, or raw borrower records into routine logs

### 2. Data-Quality Validation Module
**New module:** `src/data_quality/validator.py`

**Purpose:** Reusable data-quality validation checks.

**Required checks:**
- Missing required columns
- Unexpected columns
- Invalid data types
- Duplicate pseudonymous IDs or duplicate event IDs
- Impossible dates and invalid chronological ordering
- Features recorded after the prediction timestamp
- Invalid negative or non-finite monetary values (where disallowed by field definition)
- Inconsistent currencies and units
- Missing repayment events or ambiguous outcomes
- Conflicting loan status and repayment records
- Immature observation windows
- Right-censoring and active-loan handling
- Target imbalance
- Excessive missingness
- Train/validation/test overlap at the borrower level
- Duplicate or repeated applications where relevant
- Potential sensitive information in column names or schemas

**Severity levels:**
- **ERROR:** Dataset must not proceed
- **WARNING:** Requires human review
- **INFORMATION:** Descriptive diagnostic

**Output:** Structured report with aggregate counts and diagnostic summaries (not raw records).

### 3. Point-in-Time and Target Audit Infrastructure
**New module:** `src/temporal_audit/audit.py`

**Purpose:** Explicit definitions and validation of temporal structure.

**Required functionality:**
- Observation window definition
- Prediction timestamp definition
- Outcome window definition
- Target event definition
- Label maturity date
- Censoring and competing outcomes
- Treatment of prepayment, settlement, restructuring, and ambiguous status

**Validation rules:**
- A feature must not be included if it was not available by the prediction timestamp
- A target must not use information from before the prediction timestamp unless the documented target definition explicitly requires historical events
- Do not hard-code a default horizon without justification
- Make target construction configurable and reject unsupported definitions
- Do not assume that a loan marked "Fully Paid" is equivalent to every possible default target definition

**Tests:** Future-feature leakage, outcome-window leakage, immature labels, censored records, contradictory labels, missing timestamps.

### 4. Reproducible Evaluation Framework (No Model Training)
**New module:** `src/evaluation/metrics.py` and `src/evaluation/splitting.py`

**Purpose:** Reusable evaluation configuration and validation code for future authorized datasets.

**Required functionality:**
- Chronological train, validation, and test windows
- Grouped splitting by borrower when necessary
- Reproducible split definitions and random seeds where applicable
- Check that no test period is used for model selection or threshold selection
- Baseline specification
- Metric computation interfaces for:
  - ROC-AUC
  - Average precision/PR-AUC
  - Brier score
  - Log loss
  - KS statistic
  - Gini coefficient
- Confusion matrices only at a documented threshold
- Confidence intervals or uncertainty estimates where feasible
- Calibration diagnostics
- Subgroup diagnostics when sample sizes and lawful use permit
- Model and dataset version metadata

**Guardrails:**
- Do not report undefined ranking metrics as zero
- Represent them as unavailable and explain why
- Do not describe a high ROC-AUC as sufficient proof of a useful lending policy
- This phase may implement metric utilities and tests using clearly synthetic fixtures
- Must not fit or promote credit-risk models

### 5. Dataset Qualification Gate
**New module:** `src/qualification/gate.py`

**Purpose:** Return one of three statuses for a dataset.

**Qualification criteria:**
- Provenance and source identity
- Documented authorization and permitted use
- Suitable borrower-level records
- Point-in-time feature availability
- A meaningful, documented repayment outcome
- A defensible prediction horizon and mature outcomes
- An explicit treatment of censoring and missing labels
- Leakage controls
- Sufficient sample quality and subgroup coverage for the intended analysis
- An approved secure processing environment and retention/deletion plan

**Return values:**
- `BLOCKED`: Critical requirements are absent or failed
- `REVIEW_REQUIRED`: Material questions remain unresolved
- `QUALIFIED_FOR_RESEARCH`: Documented checks passed and the data is approved for the specified research purpose

**Guardrail:** `QUALIFIED_FOR_RESEARCH` must not mean production-ready or legally certified.

### 6. Privacy-Safe Intake Workflow Documentation
**New report:** `reports/phase_5_secure_data_intake.md`

**Required documentation:**
- Partner authorization and agreement review
- Secure transfer approved by the data owner
- Restricted access and least privilege
- Data minimization and pseudonymization
- No raw financial records in Git or ordinary logs
- Local secrets and environment files excluded from version control
- File integrity verification
- Access logging
- Retention and deletion
- Incident reporting and escalation

**Guardrail:** Do not implement a real external transfer integration or connect to a lender account. Document the required controls instead.

### 7. Synthetic-Only Unit Tests
**New test file:** `tests/test_phase5_data_validation.py`

**Required test coverage:**
- Valid schema and manifest
- Missing required columns
- Duplicate events
- Future-dated features
- Immature labels
- Censored records
- Contradictory labels
- Train/test borrower overlap
- Unavailable metrics for one-class outcomes
- Unauthorized or unresolved dataset status
- Safe error messages that do not expose record contents
- API regression: scoring remains unvalidated and probability remains null

**Guardrail:** Never store actual borrower data in test fixtures.

### 8. Phase 5 Reports
**New reports to create:**
- `reports/phase_5_implementation_plan.md` (this document)
- `reports/phase_5_data_quality_specification.md`
- `reports/phase_5_target_and_temporal_validation.md`
- `reports/phase_5_dataset_qualification_checklist.md`
- `reports/phase_5_secure_data_intake.md`
- `reports/phase_5_test_report.md`
- `reports/phase_5_operator_guide.md`

**Update policy:** Update existing documentation only where needed, without deleting prior content.

---

## Module Structure

The following new modules will be created under `src/`:

```
src/
├── data_intake/
│   ├── __init__.py
│   └── contract.py          # Dataset manifest and metadata validation
├── data_quality/
│   ├── __init__.py
│   └── validator.py         # Data-quality checks (ERROR/WARNING/INFO)
├── temporal_audit/
│   ├── __init__.py
│   └── audit.py             # Point-in-time and target validation
├── evaluation/
│   ├── __init__.py
│   ├── metrics.py           # Metric computation utilities
│   └── splitting.py         # Chronological and grouped splitting
└── qualification/
    ├── __init__.py
    └── gate.py              # Dataset qualification gate (BLOCKED/REVIEW/QUALIFIED)
```

---

## Implementation Order

1. **Data-intake contract module** - Foundation for all subsequent validation
2. **Data-quality validation module** - Build on contract to check actual data
3. **Point-in-time and target audit infrastructure** - Temporal validation
4. **Evaluation framework** - Metric and splitting utilities (no training)
5. **Dataset qualification gate** - Orchestrate all checks into a single decision
6. **Synthetic-only tests** - Test all modules with synthetic fixtures
7. **Phase 5 reports** - Document specifications, checklists, and workflows
8. **Test execution and verification** - Ensure all tests pass and API contract unchanged

---

## Non-Negotiable Guardrails

Throughout implementation, the following guardrails MUST be respected:

1. **Do not train another credit-risk model in this phase.**
2. **Do not claim that synthetic data establishes Indian credit-risk performance.**
3. **Do not use LendingClub as evidence of Indian model accuracy.**
4. **Do not download or ingest unauthorized personal or borrower data.**
5. **Do not print raw personal or financial records in logs or reports.**
6. **Keep `/v1/score` returning `score_status: "not_validated"` and `default_probability: null`.**
7. **Do not overwrite existing Phase 2 or Phase 3 benchmark artifacts or Phase 4 partnership documents.**
8. **Do not invent fields, targets, dates, labels, data permissions, or dataset provenance.**
9. **Any synthetic fixtures must be explicitly identified as synthetic test fixtures.**
10. **Report actual commands, test results, limitations, and created files.**

---

## Verification Plan

After implementation, the following will be verified:

1. **Previous tests still pass** - No regression in existing functionality
2. **New data-validation tests pass** - All Phase 5 validation logic works correctly
3. **No existing benchmark outputs were overwritten** - Historical artifacts preserved
4. **The API contract is unchanged** - `/v1/score` still returns null probability
5. **The scoring endpoint still returns a null probability** - No model wiring
6. **No models were trained** - Verification that no training code was executed
7. **No real personal data was accessed** - Only synthetic fixtures used

---

## Next Steps After Phase 5

Once Phase 5 is complete and a lender partnership is secured:

1. Receive authorized dataset under Data Use Agreement
2. Run the data-intake contract validation
3. Execute data-quality checks
4. Perform point-in-time and target audit
5. Apply dataset qualification gate
6. If `QUALIFIED_FOR_RESEARCH`, proceed to model development (future phase)
7. If `BLOCKED` or `REVIEW_REQUIRED`, address issues with the lender

Phase 5 makes CreditAI ready to inspect and qualify real data—it does not pretend that we already possess it.

---

*End of Phase 5 Implementation Plan*
