# CreditAI Phase 4 — Existing Evidence Review

**Date:** 2026-10-12
**Scope:** Audit all existing project artifacts to establish a baseline for lender partnership outreach. Separate verified findings from assumptions and identify gaps.

---

## 1. Verified Project Artifacts

### 1.1 Phase 2.3.1 Independent Audit (Verified)

**File:** `reports/phase_2_3_1_independent_audit.md`

**Verified findings:**
- LendingClub CSV total rows: 2,260,701 (corrected from 2,260,694 in Phase 2.3.2)
- Closed-loan cohort: 1,348,099 (1,078,739 good + 269,360 bad)
- Excluded active/censored loans: 912,602 (40.4% of originations)
- Chronological splits: Train (2007-2013, 230,706), Validation (2014-2015, 598,649), Test (2016-2018, 518,744)
- 63 retained features (all documented as point-in-time: Application, Origination, or Application-Bureau)
- 47 prohibited columns (40 leakage/metadata + 7 PII)
- Test metrics (HistGradientBoosting): ROC-AUC 0.7056, PR-AUC 0.3947, Brier 0.1636, KS 0.2976, Gini 0.4112
- Thresholds selected on validation only (LR 0.16, HGB 0.17)
- No calibration fitted
- `/v1/score` remains `not_validated` with `default_probability: null`

**Verification method:** Independent re-run of identical pipeline, chunked CSV counting, status frequency verification.

**Limitations documented:**
- Historical closed-loan outcome, NOT fixed-horizon default model
- Survivorship/censoring bias from excluding active loans
- Unequal follow-up across cohorts (11 years for 2007 loans, <1 year for 2018 loans)
- U.S. LendingClub data only — no Indian borrowers
- No claim of Indian credit-risk accuracy

### 1.2 Phase 3 Indian Data Feasibility (Verified)

**File:** `reports/phase_3_indian_data_feasibility.md`

**Verified findings:**
- No qualifying Indian borrower-level labeled dataset exists publicly
- Workspace contains no Indian borrower-level dataset with both features and outcomes
- CreditMitra_transactions.csv (25 rows) has no provenance, authorization, or outcomes
- RBI/NPCI/FACE data is aggregate-only, not borrower-level
- Synthetic data is for pipeline testing only

**Verified external sources:**
- SRC001 Indifi: 300,000+ MSME loans documented in NBER w34148 (proves lenders share data via DUA)
- SRC002 Unnamed MFI: 2,036,108 borrowers documented in SMJ (proves MFIs share data)
- SRC003 RBI CRILC: Corporate-only, defaulters-only, no features
- SRC005 Account Aggregator: Features only, not labels
- SRC006 Credit Bureaus: Access requires lender membership
- SRC010 P2P Platforms: Aggregate NPA verified, borrower-level access unconfirmed

**Final decision:** CONDITIONAL GO — proceed only after signed DUA with identified lender.

### 1.3 Phase 3 Dataset Inventory (Verified)

**File:** `reports/phase_3_dataset_inventory.csv`

**Verified counts:**
- DS001 LendingClub CSV: 2,260,701 rows, 151 columns (corrected in Phase 2.3.2)
- DS007 CreditMitra: 25 rows, 2 columns (no provenance)
- DS008-DS013 Synthetic: 800-177,608 rows (synthetic only)
- DS014-DS017 Indian aggregates: 110-142 rows (macro only)

### 1.4 Test Suite (Verified)

**Status:** 53 tests passed, 0 failures (as of Phase 2.3.2)

**Key regression tests:**
- `test_prohibited_column_count_reconciliation` — pins 47 prohibited columns
- `test_feature_decisions_full_reconciliation` — 151 columns, one decision each
- `test_confusion_matrix_totals_match_split_sizes` — CM sums equal split sizes
- `test_raw_row_count_reconciliation` — pins 2,260,701 total rows
- `test_api_non_regression_contract` — confirms `/v1/score` remains unvalidated

### 1.5 API Contract (Verified)

**File:** `src/api/app.py` and contract tests

**Verified state:**
- `/v1/score` endpoint exists
- Returns `score_status: "not_validated"`
- Returns `default_probability: null`
- Returns `validated_risk_estimate: false`
- No model wired into production API

---

## 2. Findings Reported But Not Independently Rechecked

The following were reported in earlier phases but not re-verified in Phase 2.3.1 or Phase 3:

### 2.1 Phase 1 UCI Benchmark (Not rechecked)
- UCI Default of Credit Card Clients metrics
- Phase 1.1 synthetic data metrics
- Financial feature engineering pipeline on synthetic data

**Status:** These are historical pipeline validation artifacts. They were not re-audited in Phase 2.3.1 or Phase 3. They are not evidence of Indian borrower performance.

### 2.2 Phase 2.2 Dataset Qualification (Not rechecked)
- Initial LendingClub data qualification
- Feature leakage audit methodology

**Status:** The Phase 2.2 feature leakage audit CSV was used as a reference in Phase 2.3.1, but the Phase 2.2 report itself was not independently re-verified. Phase 2.3.1 confirmed the 151-column reconciliation against the Phase 2.2 audit CSV.

### 2.3 External Source Claims (Partially verified)
- Indifi NBER paper: Verified (paper exists, describes dataset)
- SMJ MFI paper: Verified (paper exists, describes dataset)
- RBI CRILC dataful.in: Verified (schema inspected)
- Kaggle synthetic: Verified (page explicitly states synthetic)
- Home Credit: Verified (well-known Kaggle dataset)
- FACE reports: Aggregate statistics verified
- P2P platform aggregate NPA: Verified (public factsheets)

**Not verified:** Whether these organizations will share data with CreditAI specifically. Evidence of past research sharing does not establish future willingness to share with this project.

---

## 3. Business Assumptions

The following are assumptions stated in project documentation but not empirically verified:

### 3.1 Market Assumptions
- "CreditAI is built for NBFCs" — No NBFC partnership exists
- "Intended production pipeline includes Account Aggregator integration" — No AA integration exists
- "Helps evaluate borrowers with limited traditional credit histories" — No Indian thin-file validation exists

### 3.2 Technical Assumptions
- "SHAP explainability provides risk drivers" — Implemented but not validated with real Indian data
- "Probability calibration aligns predictions with observed rates" — Implemented on UCI/synthetic, not validated on Indian data
- "Champion-challenger model governance framework" — Not implemented

### 3.3 Commercial Assumptions
- README mentions "Phase 2 (Next Steps)" including NBFC data integration — Not executed
- No revenue model, pricing, or commercial terms documented
- No client relationships or pilot agreements exist

---

## 4. Missing Evidence

### 4.1 Indian Borrower Validation
- No Indian borrower-level labeled dataset
- No Indian borrower performance metrics
- No validation on Indian thin-file or MSME segments
- No comparison with CIBIL or incumbent NBFC systems

### 4.2 Regulatory Compliance
- No Digital Personal Data Protection Act 2023 compliance assessment
- No RBI lending regulation review
- No fair lending or demographic fairness audit on real data
- No model governance framework for production use

### 4.3 Commercial Readiness
- No signed data-use agreements
- No lender partnerships
- No pilot agreements
- No pricing or commercial terms
- No customer references or case studies

### 4.4 Operational Infrastructure
- No Account Aggregator FIU registration
- No Credit Information Company membership
- No secure data transfer infrastructure
- No production deployment infrastructure
- No monitoring or incident response procedures

---

## 5. Claims That Must Not Appear in External Communications

The following claims are NOT supported by evidence and must not be used in lender outreach:

### 5.1 Performance Claims
- **DO NOT claim:** "CreditAI achieves X% accuracy on Indian borrowers"
- **DO NOT claim:** "CreditAI outperforms CIBIL"
- **DO NOT claim:** "CreditAI is validated for Indian NBFC lending"
- **DO NOT claim:** "CreditAI reduces default rates by Y%"

**Correct statement:** "CreditAI has demonstrated discrimination (ROC-AUC 0.7056) on a historical U.S. LendingClub benchmark under strict leakage controls. This validates the technical pipeline but does not establish Indian borrower performance."

### 5.2 Commercial Claims
- **DO NOT claim:** "CreditAI has clients"
- **DO NOT claim:** "CreditAI generates revenue"
- **DO NOT claim:** "CreditAI is production-ready"
- **DO NOT claim:** "CreditAI has regulatory approval"

**Correct statement:** "CreditAI is a research-stage prototype. No commercial deployment, client relationships, or regulatory approvals exist."

### 5.3 Data Claims
- **DO NOT claim:** "CreditAI has access to Indian borrower data"
- **DO NOT claim:** "CreditAI uses Account Aggregator data"
- **DO NOT claim:** "CreditAI integrates with CIBIL"

**Correct statement:** "CreditAI has no access to Indian borrower repayment data. A data partnership with an Indian lender is required for any Indian validation."

### 5.4 Market Claims
- **DO NOT claim:** "CreditAI serves X million Indian borrowers"
- **DO NOT claim:** "CreditAI addresses a ₹Y crore market opportunity"
- **DO NOT claim:** "Z% of Indian borrowers lack credit histories" (unless sourced from verified public statistics)

**Correct statement:** "CreditAI is designed for Indian NBFC underwriting, but market sizing and borrower segment analysis require primary research."

---

## 6. Evidence Strength Summary

| Evidence Area | Strength | Notes |
|---|---|---|
| Historical U.S. benchmark methodology | **High** | Independently verified, reproducible, leakage-safe |
| Indian data feasibility analysis | **High** | Comprehensive research, verified external sources |
| Technical pipeline implementation | **High** | 53 passing tests, reproducible training/evaluation |
| API contract safety | **High** | `/v1/score` confirmed unvalidated, regression tests in place |
| Indian borrower performance | **None** | No Indian data, no validation |
| Commercial readiness | **None** | No partnerships, no DUAs, no clients |
| Regulatory compliance | **None** | No compliance assessment performed |
| Market validation | **Low** | Assumptions stated, no primary research |

---

## 7. Conclusion for Partnership Outreach

**What we can credibly offer a lender:**
- A rigorously audited ML pipeline with proven leakage-safe methodology
- Experience with large-scale credit datasets (2.26M LendingClub loans)
- Independent verification of all metrics and feature decisions
- A clear understanding of point-in-time feature availability and leakage risks
- A commitment to data governance and privacy (to be formalized in DUA)

**What we cannot credibly claim:**
- Indian borrower performance
- Superiority to incumbent systems
- Commercial track record
- Regulatory approval
- Existing client relationships

**Outreach positioning:** "We have built and independently audited a leakage-safe credit-risk ML pipeline on historical U.S. data. We are seeking a research partnership with an Indian lender to validate whether similar methodologies can support useful decision-making on Indian borrower data, under a governed data-use agreement."

---

*End of Phase 4 existing evidence review.*
