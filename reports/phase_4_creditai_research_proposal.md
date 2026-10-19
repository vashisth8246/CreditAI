# CreditAI Research Partnership Proposal

**Date:** October 12, 2026
**Prepared for:** Indian NBFCs, Fintech Lenders, and P2P Platforms
**Contact:** [To be completed by project owner]

---

## Executive Summary

CreditAI is a research-stage machine learning project focused on developing leakage-safe credit-risk decision-support methodologies. We have built and independently audited a rigorous ML pipeline on historical U.S. LendingClub data, demonstrating discrimination (ROC-AUC 0.7056) under strict leakage controls and chronological evaluation.

We are seeking a research partnership with an Indian lender to validate whether similar methodologies can support useful decision-making on Indian borrower data. Our goal is not to replace existing underwriting systems, but to conduct a controlled feasibility study on whether application-time financial features can provide incremental signal for credit-risk assessment.

This proposal outlines a small, governed pilot using an authorized historical dataset, subject to the lender's approval. All work would be conducted under a formal Data Use Agreement with pseudonymization, purpose limitation, and data minimization.

---

## The Problem

Many credit applicants in India have limited traditional credit histories—thin files, new-to-credit profiles, or informal income documentation that conventional scoring models struggle to evaluate. Lenders must balance access to credit with risk management, often relying on conservative underwriting that may exclude creditworthy borrowers.

Alternative data sources—bank transaction histories, GST records, cash-flow patterns, and behavioral indicators—offer potential signals for repayment capacity. However, it is unclear whether these features, when used in a leakage-safe manner, actually improve risk decisions beyond existing methods.

The question is not whether ML can be applied to credit data, but whether a rigorously validated, point-in-time feature set can provide reliable, actionable signal for Indian borrowers under real-world constraints.

---

## Proposed Research

CreditAI proposes to conduct a controlled feasibility study in collaboration with a lender partner. The research would:

1. **Assess data completeness and quality:** Evaluate whether the lender's historical loan book contains sufficient point-in-time features and matured outcomes to support meaningful analysis.

2. **Define an observable repayment outcome:** Work with the lender to specify a target definition (e.g., 90+ DPD, write-off) that aligns with business use and is observable in the data.

3. **Build a leakage-safe point-in-time dataset:** Construct a feature set using only information available at the time of loan application, excluding post-origination leakage fields.

4. **Establish a chronological holdout:** Split data by origination date to simulate real-world deployment and prevent temporal leakage.

5. **Compare simple baselines with candidate ML models:** Evaluate whether ML models (e.g., logistic regression, gradient boosting) provide meaningful discrimination over rule-based or scorecard baselines.

6. **Assess discrimination, calibration, stability, and subgroup performance:** Where data permits, evaluate model performance across segments and assess calibration quality.

We do not promise a specific accuracy target before observing the data. The goal is to determine whether a useful signal exists, not to force a positive result.

---

## Existing Technical Work

CreditAI has developed and independently audited a leakage-safe credit-risk benchmark on historical U.S. LendingClub data:

**Dataset:** 2.26 million loan applications from LendingClub (2007–2018), a U.S. peer-to-peer lending platform.

**Methodology:**
- Strict exclusion of 47 post-origination leakage fields (payment history, recovery data, hardship flags, PII)
- Retention of 63 point-in-time features (application form fields, bureau snapshot at application, origination terms)
- Chronological train/validation/test split (2007–2013, 2014–2015, 2016–2018)
- Closed-loan cohort only (1.35M loans with terminal outcomes; 912K active loans excluded)

**Results (Test set, HistGradientBoosting):**
- ROC-AUC: 0.7056
- PR-AUC: 0.3947 (vs. 0.2242 prevalence baseline)
- Brier Score: 0.1636
- KS Statistic: 0.2976
- Gini Coefficient: 0.4112

**Independent verification:** All metrics were independently reproduced in Phase 2.3.1 audit. Feature counts, cohort sizes, and preprocessing isolation (train-only imputation/encoding/scaling) were verified.

**Limitations:**
- This is historical U.S. data, not Indian data. It says nothing about Indian borrower performance.
- The target is a closed-loan outcome (did the loan reach a terminal bad state), not a fixed-horizon default.
- The cohort excludes active loans, introducing survivorship bias.
- No calibration, fairness, or regulatory review was performed.

This work validates the technical pipeline and leakage-safe methodology, but it does not establish Indian borrower accuracy or commercial readiness.

---

## Proposed Pilot

We propose a small, controlled feasibility pilot using an authorized historical dataset from the lender partner.

### Scope

- **Product:** One closed personal-loan or MSME-loan product (to be selected by the lender)
- **Observation window:** Origination dates with ≥12 months of mature follow-up (to be defined by the lender)
- **Sample size:** Sufficient to support meaningful analysis (exact size to be agreed with the lender)
- **Features:** All fields available at application time (form fields, bureau pull, bank statement aggregates, where available)
- **Target:** Lender-defined default (e.g., 90+ DPD, write-off) with clear observation window

### Pilot Objectives

1. **Data quality assessment:** Evaluate missingness, feature distributions, and outcome prevalence
2. **Target definition:** Specify a clear, observable default event with appropriate censoring flags
3. **Feature engineering:** Construct point-in-time features from raw application data
4. **Baseline comparison:** Compare ML models against simple rule-based or scorecard baselines
5. **Leakage audit:** Ensure no post-origination information contaminates the feature set
6. **Evaluation:** Assess discrimination (ROC-AUC, PR-AUC), calibration (Brier, reliability diagrams), and stability across time

### Deliverables

- Data quality report (missingness, distributions, prevalence)
- Feature documentation (data dictionary, timing evidence, leakage assessment)
- Model evaluation report (metrics, baseline comparisons, limitation analysis)
- Reproducible code (under appropriate access controls)
- Clear explanation of limitations and conditions for generalization

### What We Do Not Promise

- A specific accuracy target or improvement over existing methods
- Production-ready models or deployment recommendations
- Regulatory approval or compliance certification
- Generalization beyond the studied product and time period

---

## What the Partner Contributes

The lender partner would provide:

1. **Data dictionary:** A documented schema of available fields, including definitions, timestamps, and provenance
2. **Authorized sample extract:** A pseudonymized historical loan book extract for the selected product, delivered through a secure channel
3. **Target/outcome definition:** Clear specification of default events, observation windows, and censoring indicators
4. **Business context:** Product characteristics, underwriting policies, and relevant constraints
5. **Data governance sign-off:** Confirmation from the lender's compliance team that sharing is lawful under applicable regulations

All data would be pseudonymized—no direct identifiers (PAN, mobile, name) in the modeling view. A separate re-identification key would remain with the lender.

---

## What CreditAI Contributes

CreditAI would provide:

1. **Data-quality analysis:** Assessment of missingness, distributions, outliers, and data integrity
2. **Reproducible experiments:** Code for feature engineering, model training, and evaluation with version control
3. **Model evaluation:** Comprehensive metrics (discrimination, calibration, stability) with baseline comparisons
4. **Leakage audit:** Rigorous review of feature timing to prevent post-origination contamination
5. **Documented research report:** Clear findings, limitations, and conditions for interpretation
6. **Code and artifact handover:** All analysis code and model artifacts under agreed access controls

We commit to transparency about limitations. If the data does not support meaningful analysis, we will report that clearly rather than force a positive result.

---

## Privacy and Governance

All work would be conducted under a formal Data Use Agreement (DUA) with the following provisions:

### Data Minimization
- Only application-time features and repayment outcomes necessary for the research
- No unnecessary personal identifiers, raw identity documents, or unrestricted account credentials
- Pseudonymization of all borrower records in the modeling view

### Purpose Limitation
- Data used solely for the agreed credit-risk model development research
- No reuse for other purposes without explicit lender approval
- No onward sharing or redistribution to third parties

### Access Controls
- Role-based permissions for all personnel accessing the data
- Audit logging of all data access and operations
- Secure storage with encryption at rest and in transit

### Retention and Deletion
- Agreed retention period for research artifacts (e.g., 12 months after report delivery)
- Secure deletion procedures for all copies of the data after retention period
- Confirmation of deletion provided to the lender

### Security Review
- Vulnerability assessment of storage and processing infrastructure
- Secure data transfer mechanisms (e.g., SFTP, encrypted file transfer)
- Incident response procedures for data breaches

### Legal Compliance
- Compliance with Digital Personal Data Protection Act, 2023
- Adherence to RBI lending regulations and fair practice codes
- Respect for borrower consent and privacy rights

### Publication and Disclosure
- No publication of raw data or identifiable information
- Lender review rights for any public disclosures or publications
- Anonymized reporting only, with lender approval

---

## Commercial Pathway

This proposal is for a research collaboration, not a commercial engagement. However, if the pilot demonstrates meaningful results, potential future pathways could include:

1. **Extended validation:** Larger-scale studies across multiple products or time periods
2. **Paid pilot:** A structured paid engagement for model development and validation
3. **Production integration:** Support for integrating validated models into the lender's underwriting workflow (subject to separate agreement)

No commercial commitment is implied or expected at this stage. The research collaboration is a prerequisite for any future commercial discussion.

---

## Explicit Limitations

CreditAI is a research-stage prototype with the following limitations:

1. **No validated Indian model:** We have not trained or validated any model on Indian borrower data. The LendingClub benchmark is U.S. data only.

2. **No production deployment:** The `/v1/score` API endpoint remains in `not_validated` state with `default_probability: null`. No model is wired into production.

3. **No regulatory approval:** No regulatory review, fairness audit, or compliance certification has been performed.

4. **No commercial track record:** We have no clients, revenue, or commercial deployments.

5. **No claim of superiority:** We do not claim that our methods outperform CIBIL, traditional underwriting, or existing NBFC systems.

6. **No market validation:** We have not validated our approach with Indian lenders or borrowers.

Any claims to the contrary would be inaccurate. We are transparent about these limitations and will not overstate our capabilities.

---

## Next Steps

If this proposal is of interest, we suggest the following process:

1. **Introductory call:** Discuss research objectives, data availability, and governance requirements
2. **Data Use Agreement:** Negotiate and sign a formal DUA covering data access, purpose, retention, and security
3. **Data dictionary review:** Review the lender's available fields and agree on the extract specification
4. **Secure data transfer:** Receive the pseudonymized extract through an approved secure channel
5. **Feasibility assessment:** Conduct initial data quality review and confirm suitability for analysis
6. **Research execution:** Perform the agreed analysis with regular progress updates
7. **Findings review:** Present results to the lender's risk, data, and compliance teams
8. **Report delivery:** Provide final research report with clear limitations and recommendations

We are flexible on timeline and scope based on the lender's preferences and constraints.

---

## Contact

**Project Owner:** [Name]
**Email:** [Email]
**Phone:** [Phone]
**Website:** [Website]

---

*This proposal is for discussion purposes only and does not constitute a binding agreement. All work would be governed by a formal Data Use Agreement.*
