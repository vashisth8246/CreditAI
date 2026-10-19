# CreditAI Go/No-Go Gates for Indian Model Development

**Version:** 1.0
**Date:** October 12, 2026
**Purpose:** Define clear decision gates before proceeding to Indian borrower model training

---

## Overview

Indian borrower model training must not proceed until all gates are passed. These gates ensure that:
- The partnership is with a legitimate organization
- Data access is lawful and authorized
- The data is suitable for meaningful analysis
- The methodology is leakage-safe and reproducible

Interest from a partner is not equivalent to permission to access data. A signed agreement is not sufficient if the actual dataset lacks suitable labels or timestamps.

---

## Gate 1: Credible Organization and Authorized Contact Route

### Criteria
- [ ] Organization is a verified Indian NBFC, fintech lender, or P2P platform
- [ ] Organization has a legitimate official website and physical presence
- [ ] Contact route is verified (email from official domain, LinkedIn profile with organization affiliation, or published contact information)
- [ ] No evidence of fraudulent or misleading claims about the organization

### Evidence Required
- Official website URL
- Company registration number (e.g., CIN for Indian companies)
- RBI registration or license number (if applicable)
- Verified contact email or phone number from official source

### Go Condition
All criteria met. Organization is legitimate and contact route is authentic.

### No-Go Condition
Organization cannot be verified, or contact route appears suspicious/unofficial.

---

## Gate 2: Potential Partner Expresses Interest

### Criteria
- [ ] Partner responds to outreach (email, call, or meeting)
- [ ] Partner confirms interest in discussing research collaboration
- [ ] Partner identifies relevant internal team (risk, data science, innovation, or compliance)
- [ ] Partner agrees to introductory call or meeting

### Evidence Required
- Email response or call notes
- Meeting confirmation
- Names and roles of relevant team members

### Go Condition
Partner expresses interest and agrees to discuss collaboration.

### No-Go Condition
Partner declines interest, does not respond after multiple follow-ups, or indicates this is not a priority.

---

## Gate 3: Data Access, Permitted Purposes, and Agreement Documented

### Criteria
- [ ] Partner confirms data availability for the proposed research
- [ ] Partner identifies lawful basis for data sharing (consent, legitimate interest, contractual necessity)
- [ ] Partner's legal/compliance team agrees to review Data Use Agreement
- [ ] Data Use Agreement is drafted and shared with partner

### Evidence Required
- Written confirmation of data availability
- Legal basis documentation
- Draft Data Use Agreement
- Legal team contact information

### Go Condition
Partner confirms data can be shared for research purposes and agrees to DUA review.

### No-Go Condition
Partner indicates data cannot be shared, legal basis is unclear, or legal team declines to review DUA.

---

## Gate 4: Signed Data Use Agreement and Sample Received

### Criteria
- [ ] Data Use Agreement is signed by both parties
- [ ] DUA covers: pseudonymization, purpose limitation, retention, security, deletion, publication rights
- [ ] Data dictionary is provided and reviewed
- [ ] Sample extract (e.g., 1,000 rows) is received via secure channel
- [ ] Sample extract is pseudonymized (no direct identifiers in modeling view)

### Evidence Required
- Signed DUA document
- Data dictionary with field definitions, timestamps, and provenance
- Secure transfer confirmation
- Sample data file

### Go Condition
DUA is signed, data dictionary is reviewed, and sample extract is received securely.

### No-Go Condition
DUA cannot be agreed, data dictionary is insufficient, or sample extract is not provided.

---

## Gate 5: Data Quality, Target Definition, and Point-in-Time Availability Pass Review

### Criteria
- [ ] Data quality assessment shows sufficient completeness (missingness < 50% for key features)
- [ ] Target definition is agreed and observable in the data (e.g., 90+ DPD, write-off)
- [ ] Observation window is specified and sufficient (≥12 months for recent loans)
- [ ] Point-in-time feature availability is verified (all features observable as of decision date)
- [ ] No post-origination leakage fields are present in the feature set
- [ ] Censoring is properly flagged (active loans, prepayments, restructurings)
- [ ] Sample size is sufficient for meaningful analysis (minimum to be agreed based on product)

### Evidence Required
- Data quality report (missingness, distributions, prevalence)
- Target definition document with examples
- Feature timing audit (timestamp verification for each feature)
- Leakage assessment (confirmation that no post-origination fields are included)
- Sample size calculation

### Go Condition
Data quality is sufficient, target is observable, point-in-time availability is verified, and no leakage is present.

### No-Go Condition
Data quality is poor, target cannot be observed, point-in-time availability cannot be verified, or leakage is present.

---

## Gate 6: Leakage-Safe Research Dataset and Reproducible Validation Protocol Approved

### Criteria
- [ ] Full dataset (not just sample) is received via secure channel
- [ ] Dataset is pseudonymized and matches the agreed specification
- [ ] Feature engineering pipeline is documented and reproducible
- [ ] Chronological split is defined (train/validation/test by origination date)
- [ ] Baseline models are defined (e.g., prevalence baseline, scorecard)
- [ ] Evaluation metrics are specified (ROC-AUC, PR-AUC, Brier, calibration, stability)
- [ ] Validation protocol is approved by partner's risk/data science team

### Evidence Required
- Full dataset file
- Feature engineering code with documentation
- Split definition with date ranges
- Baseline model specifications
- Evaluation metrics specification
- Approval from partner's team

### Go Condition
Full dataset is received, pipeline is reproducible, and validation protocol is approved.

### No-Go Condition
Full dataset does not match specification, pipeline is not reproducible, or validation protocol is not approved.

---

## Gate 7: Initial Analysis Shows Meaningful Signal

### Criteria
- [ ] Baseline models run successfully
- [ ] ML models show meaningful discrimination over baseline (e.g., ROC-AUC improvement > 0.02)
- [ ] Calibration is reasonable (not severely overconfident or underconfident)
- [ ] No severe data quality issues emerge in full dataset
- [ ] No unexpected biases or anomalies are detected

### Evidence Required
- Baseline model results
- ML model results
- Calibration assessment
- Data quality check on full dataset
- Bias/fairness assessment (where data permits)

### Go Condition
Initial analysis shows meaningful signal without severe issues.

### No-Go Condition
No meaningful signal over baseline, severe calibration issues, or unexpected biases/anomalies.

---

## Gate 8: Partner Approves Publication of Research Findings

### Criteria
- [ ] Research report is drafted with clear limitations
- [ ] Partner reviews research report
- [ ] Partner approves publication (or agrees to confidential sharing)
- [ ] Attribution and confidentiality terms are agreed

### Evidence Required
- Draft research report
- Partner review comments
- Publication approval (or confidentiality agreement)

### Go Condition
Partner approves research findings for publication or confidential sharing.

### No-Go Condition
Partner does not approve findings and no agreement on confidential sharing is reached.

---

## Summary of Gates

| Gate | Description | Decision Point |
|---|---|---|
| 1 | Credible organization and authorized contact route | Before initial outreach |
| 2 | Partner expresses interest | After initial outreach |
| 3 | Data access, permitted purposes, and agreement documented | Before DUA drafting |
| 4 | Signed DUA and sample received | Before full data request |
| 5 | Data quality, target definition, and point-in-time availability | Before full dataset analysis |
| 6 | Leakage-safe dataset and reproducible validation protocol | Before model training |
| 7 | Initial analysis shows meaningful signal | Before proceeding to extended analysis |
| 8 | Partner approves publication of findings | Before public disclosure |

---

## Critical Principles

### Interest ≠ Permission
A partner expressing interest does not mean data access is permitted. A signed Data Use Agreement is required before any data is accessed.

### Signed Agreement ≠ Data Suitability
A signed DUA does not guarantee the data is suitable for analysis. The data must pass quality, timing, and leakage review (Gate 5) before model training.

### No Shortcuts
All gates must be passed in sequence. Skipping gates (e.g., proceeding to model training before data quality review) is prohibited.

### Transparency Over Speed
If any gate fails, the failure must be documented clearly. Do not force a positive result by bypassing gates.

---

## Gate Failure Actions

### If Gate 1 Fails
- Document why organization could not be verified
- Remove from partner shortlist
- Investigate alternative organizations

### If Gate 2 Fails
- Document partner's response (or lack thereof)
- Follow up once more if appropriate
- Move to next partner in shortlist

### If Gate 3 Fails
- Document legal or compliance blockers
- Discuss whether blockers can be addressed
- If not, move to next partner

### If Gate 4 Fails
- Document DUA negotiation issues
- Discuss whether terms can be adjusted
- If not, move to next partner

### If Gate 5 Fails
- Document data quality or timing issues
- Discuss whether data improvements are possible
- If not, terminate collaboration gracefully

### If Gate 6 Fails
- Document dataset or pipeline issues
- Discuss whether issues can be resolved
- If not, terminate collaboration gracefully

### If Gate 7 Fails
- Document that no meaningful signal was found
- Report this as a valid negative result
- Discuss whether different approaches or data could work

### If Gate 8 Fails
- Discuss publication restrictions
- Agree on confidential sharing if publication is not possible
- Document findings for internal use only

---

## Gate Tracking

All gate decisions must be documented in the partnership tracker with:
- Gate number
- Date reviewed
- Decision (GO/NO-GO)
- Evidence reviewed
- Rationale for decision
- Next action (if GO) or termination reason (if NO-GO)

---

## Final Decision

Indian borrower model training may proceed ONLY after:

1. **All 8 gates are passed** in sequence
2. **All evidence is documented** in the partnership tracker
3. **Partner approval is obtained** for the validation protocol
4. **API remains in `not_validated` state** until model is validated on Indian data

**No exceptions.**

---

*These gates are designed to ensure rigorous, lawful, and transparent research. Bypassing gates compromises project integrity and may violate legal or regulatory requirements.*
