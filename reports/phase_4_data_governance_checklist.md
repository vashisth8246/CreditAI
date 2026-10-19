# CreditAI Data Governance Checklist

**Version:** 1.0
**Date:** October 12, 2026
**Purpose:** Review items for data governance, privacy, and compliance in lender research partnerships

---

## Disclaimer

This checklist is for planning purposes only and does not constitute legal advice. A qualified legal professional should review all data-sharing agreements, privacy policies, and compliance requirements before any data is accessed or used.

---

## 1. Data Ownership and Authority to Share

### Legal Authority
- [ ] Does the lender have legal ownership or lawful authority to share the proposed data?
- [ ] Is the data subject to any third-party restrictions (e.g., bureau data licenses, co-lending partner agreements)?
- [ ] Has the lender's legal team confirmed authority to share for research purposes?

### Board or Management Approval
- [ ] Has the lender's management or board approved data sharing for research collaboration?
- [ ] Is there a documented approval process for data-sharing decisions?

### Regulatory Restrictions
- [ ] Are there any regulatory restrictions on sharing the data (RBI, SEBI, IRDAI, etc.)?
- [ ] Does the data fall under any restricted categories (e.g., sensitive personal data, financial confidentiality)?

---

## 2. Permitted Research and Model-Development Purposes

### Purpose Limitation
- [ ] Is the permitted purpose clearly defined in the Data Use Agreement (DUA)?
- [ ] Is the purpose limited to credit-risk model development research only?
- [ ] Are there any restrictions on using the data for other purposes (e.g., marketing, product development)?

### Scope of Research
- [ ] Is the scope of research clearly defined (e.g., specific product, time period, analysis type)?
- [ ] Are there any prohibited analyses or outcomes (e.g., competitive benchmarking, publication of rankings)?

### Publication Rights
- [ ] Does the lender have review rights over any publications or disclosures?
- [ ] Are there restrictions on publishing model performance comparisons?
- [ ] Is attribution to the lender required or prohibited?

---

## 3. Consent or Other Lawful Basis

### Consent Requirements
- [ ] Was borrower consent obtained for the original data collection?
- [ ] Does the consent cover research use or model development?
- [ ] Is re-consent required for the proposed research use?

### Alternative Lawful Bases
- [ ] If consent is not available, is there an alternative lawful basis (e.g., legitimate interest, contractual necessity)?
- [ ] Has the legal basis been documented and approved by counsel?

### Data Minimization
- [ ] Is the data minimized to only what is necessary for the research?
- [ ] Are unnecessary fields excluded from the extract?

---

## 4. Restrictions on Reuse and Onward Sharing

### No Onward Sharing
- [ ] Does the DUA explicitly prohibit onward sharing to third parties?
- [ ] Are there any exceptions (e.g., subprocessors with approval)?

### No Redistribution
- [ ] Is redistribution of the data prohibited?
- [ ] Are there restrictions on sharing derived features or model artifacts?

### Time-Limited Use
- [ ] Is the data use limited to a specific time period?
- [ ] Is there a clear end date for the research collaboration?

---

## 5. Personal and Sensitive Information Minimization

### Direct Identifiers
- [ ] Are direct identifiers (PAN, mobile, name, Aadhaar) excluded from the modeling view?
- [ ] Is a pseudonymous ID used instead?
- [ ] Is the re-identification key stored separately by the lender?

### Sensitive Categories
- [ ] Are sensitive categories (health, biometrics, caste, religion, political opinion) excluded unless legally required?
- [ ] Is there a documented justification for any sensitive categories included?

### Special Category Data
- [ ] Does the data include any special category data under DPDP Act 2023?
- [ ] Is enhanced consent or legal basis documented for special category data?

---

## 6. Pseudonymization and Re-Identification Risk

### Pseudonymization Method
- [ ] Is the pseudonymization method documented (e.g., hashing, tokenization)?
- [ ] Is the pseudonymization reversible only by the lender?
- [ ] Is the re-identification key stored securely by the lender?

### Re-Identification Risk Assessment
- [ ] Has a re-identification risk assessment been performed?
- [ ] Are there any quasi-identifiers that could enable re-identification?
- [ ] Are k-anonymity or l-diversity considerations documented?

### Key Separation
- [ ] Is the re-identification key stored separately from the pseudonymized data?
- [ ] Is access to the re-identification key restricted to authorized lender personnel only?

---

## 7. Secure Transfer and Storage

### Transfer Method
- [ ] Is the data transferred via a secure channel (e.g., SFTP, encrypted file transfer)?
- [ ] Is encryption in transit (TLS 1.2+) used?
- [ ] Is the transfer method documented in the DUA?

### Storage Security
- [ ] Is the data stored in encrypted form at rest (AES-256 or equivalent)?
- [ ] Is the storage environment access-controlled (role-based permissions)?
- [ ] Is the storage environment compliant with relevant security standards (e.g., ISO 27001)?

### Access Logging
- [ ] Is all data access logged (who, when, what, why)?
- [ ] Are access logs reviewed regularly?
- [ ] Is there an alert mechanism for unauthorized access attempts?

---

## 8. Access Logging and Role-Based Permissions

### Role-Based Access Control
- [ ] Are roles defined for personnel accessing the data (e.g., data scientist, analyst, administrator)?
- [ ] Is access granted on a need-to-know basis?
- [ ] Is role assignment documented and approved?

### Access Logging
- [ ] Is all access to data logged (read, write, delete)?
- [ ] Are logs retained for an appropriate period (e.g., 12 months)?
- [ ] Are logs protected against tampering?

### Privileged Access
- [ ] Is privileged access (admin, root) restricted and monitored?
- [ ] Is there a process for revoking access when personnel leave the project?

---

## 9. Retention and Deletion

### Retention Period
- [ ] Is the data retention period clearly defined in the DUA?
- [ ] Is the retention period aligned with the research timeline?
- [ ] Is there a documented end date for data retention?

### Deletion Process
- [ ] Is the deletion process documented (e.g., secure erase, cryptographic deletion)?
- [ ] Is deletion confirmed by both parties?
- [ ] Is a deletion certificate provided to the lender?

### Artifact Retention
- [ ] Are model artifacts and derived features subject to the same retention period?
- [ ] Is there a process for anonymizing artifacts before retention?

---

## 10. Incident Response

### Incident Response Plan
- [ ] Is there a documented incident response plan for data breaches?
- [ ] Are roles and responsibilities defined for incident response?
- [ ] Is there a timeline for notifying the lender in case of a breach?

### Notification Requirements
- [ ] Are notification timelines defined (e.g., within 24 hours, 72 hours)?
- [ ] Are notification requirements aligned with DPDP Act 2023?

### Remediation
- [ ] Is there a process for remediation after an incident?
- [ ] Are post-incident reviews documented?

---

## 11. Model-Development and Evaluation Permissions

### Model Training Permissions
- [ ] Is model training on the data explicitly permitted in the DUA?
- [ ] Are there any restrictions on model types or techniques?

### Model Evaluation Permissions
- [ ] Is model evaluation (metrics, benchmarks) permitted?
- [ ] Are there restrictions on publishing evaluation results?

### Model Artifact Permissions
- [ ] Are model artifacts (weights, parameters) subject to the same restrictions as the data?
- [ ] Can model artifacts be shared with the lender?
- [ ] Can model artifacts be used for other purposes?

---

## 12. Use of Derived Features and Model Artifacts

### Derived Features
- [ ] Are derived features (e.g., engineered features, aggregations) considered part of the data?
- [ ] Are derived features subject to the same retention and deletion requirements?

### Model Artifacts
- [ ] Who owns model artifacts trained on the data?
- [ ] Can model artifacts be used for commercial purposes?
- [ ] Are there restrictions on deploying model artifacts in production?

### Publication of Results
- [ ] Can research results be published?
- [ ] Are there restrictions on disclosing specific metrics or comparisons?
- [ ] Is lender attribution required or prohibited?

---

## 13. Publication and Disclosure Restrictions

### Pre-Publication Review
- [ ] Does the lender have pre-publication review rights?
- [ ] What is the review timeline (e.g., 14 days, 30 days)?
- [ ] What happens if the lender objects to publication?

### Confidential Information
- [ ] Is confidential information clearly defined in the DUA?
- [ ] Are there restrictions on disclosing confidential information in publications?

### Attribution
- [ ] Is the lender to be attributed in publications?
- [ ] Is the lender to remain anonymous?

---

## 14. Applicable Indian Privacy Requirements

### Digital Personal Data Protection Act 2023
- [ ] Has the data been classified under DPDP Act categories (personal data, sensitive personal data)?
- [ ] Is consent documented where required?
- [ ] Are data principal rights (access, correction, erasure) addressed?

### Consent Requirements
- [ ] Is consent free, specific, informed, and unambiguous?
- [ ] Can consent be withdrawn?
- [ ] Is the withdrawal process documented?

### Data Fiduciary Obligations
- [ ] Are data fiduciary obligations documented (purpose limitation, storage limitation, accountability)?
- [ ] Is there a Data Protection Officer designated?

---

## 15. Applicable Financial-Sector Requirements

### RBI Regulations
- [ ] Are RBI NBFC regulations applicable to the data sharing?
- [ ] Are RBI fair practice codes followed?
- [ ] Are there any RBI circulars relevant to the data sharing?

### Co-Lending Considerations
- [ ] If the lender uses co-lending, do co-lending partner agreements restrict data sharing?
- [ ] Is co-lending partner consent required?

### Credit Bureau Regulations
- [ ] If bureau data is included, are CIC Regulations applicable?
- [ ] Is bureau data sharing permitted for research purposes?
- [ ] Is borrower consent for bureau pull documented?

---

## 16. Applicable Lending Requirements

### Fair Lending Practices
- [ ] Are fair lending practices documented?
- [ ] Is there a process for assessing model fairness?
- [ ] Are demographic biases assessed where data permits?

### Model Governance
- [ ] Is there a model governance framework in place?
- [ ] Are model validation and approval processes defined?
- [ ] Is there a champion-challenger process?

### Regulatory Reporting
- [ ] Are there any regulatory reporting requirements related to the models?
- [ ] Is model documentation sufficient for regulatory review?

---

## 17. Items Requiring Professional Legal/Compliance Review

The following items MUST be reviewed by qualified legal/compliance professionals:

- [ ] Data Use Agreement (DUA) terms and conditions
- [ ] Lawful basis for data sharing under DPDP Act 2023
- [ ] RBI regulatory compliance for NBFC data sharing
- [ ] Credit bureau data sharing permissions under CIC Regulations
- [ ] Cross-border data transfer restrictions (if applicable)
- [ ] Liability and indemnification provisions
- [ ] Intellectual property rights (data, models, artifacts)
- [ ] Dispute resolution mechanisms
- [ ] Governing law and jurisdiction

---

## 18. Best Practices (Not Legal Requirements)

The following are recommended best practices but may not be legally required:

### Data Quality
- [ ] Is data quality assessed before sharing (missingness, outliers, consistency)?
- [ ] Are data quality issues documented?

### Documentation
- [ ] Is a comprehensive data dictionary provided?
- [ ] Are field definitions, timestamps, and provenance documented?
- [ ] Are data lineage and transformation steps documented?

### Reproducibility
- [ ] Is the analysis code version-controlled?
- [ ] Are random seeds and hyperparameters documented?
- [ ] Is the analysis environment documented (software versions, dependencies)?

### Transparency
- [ ] Are model limitations clearly documented?
- [ ] Are assumptions and constraints disclosed?
- [ ] Are uncertainties communicated?

---

## 19. Pre-Data-Access Checklist

Before any data is accessed, confirm:

- [ ] Signed Data Use Agreement is in place
- [ ] Legal/compliance review is complete
- [ ] Data dictionary is reviewed and approved
- [ ] Secure storage environment is prepared
- [ ] Access controls and logging are configured
- [ ] Incident response plan is documented
- [ ] Retention and deletion schedule is agreed
- [ ] Publication and disclosure restrictions are understood

---

## 20. Post-Data-Access Checklist

After data access ends:

- [ ] All copies of the data are securely deleted
- [ ] Deletion is confirmed by both parties
- [ ] Deletion certificate is provided to the lender
- [ ] Access logs are archived for the retention period
- [ ] Model artifacts are handled per DUA terms
- [ ] Research results are reviewed with the lender
- [ ] Publication rights are exercised per DUA terms

---

*This checklist is a living document and should be updated based on specific partnership requirements and evolving regulations.*
