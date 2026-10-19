# CreditAI Phase 6.1 — Qualification Decisions

Qualification describes fitness for the stated research purpose, not commercial permission. It uses exactly `QUALIFIED_FOR_RESEARCH`, `REVIEW_REQUIRED`, or `BLOCKED` per inventory entry.

| Candidate / ID | Status | Permitted Phase 6.1 use | Gate / rationale |
|---|---|---|---|
| LendingClub accepted loans / DS001 | `QUALIFIED_FOR_RESEARCH` | Existing U.S. historical closed-loan benchmark and aggregate portfolio research. | Existing leakage-safe point-in-time feature audit and chronological split. Terminal outcome is variable horizon; 912,602 unresolved/current records are censored/excluded. Local redistribution license remains unverified. Never claim Indian validation or deploy. |
| LendingClub XLSX / DS002 | `BLOCKED` | Inventory only. | Truncated overlapping copy of DS001 at spreadsheet row capacity; not a separate cohort. |
| UCI Taiwan Default of Credit Card Clients / DS003 | `QUALIFIED_FOR_RESEARCH` | Separate Taiwan credit-card next-month default benchmark or preprocessing research. | Real label and preceding six-month features are documented; 30,000 rows. Old, product/geography-specific; sensitive attributes exist. Keep separate from LendingClub and Indian populations. CC BY 4.0 attribution; confirm terms before downstream commercial use. |
| German UCI representations / DS004 and DS005 | `REVIEW_REQUIRED` | Schema, preprocessing, and label-semantics research. | “Good/bad credit” is not a dated observed default event; no time split; DS005 is an alternate encoding of DS004, not independent borrowers. |
| UCI Credit Approval / DS006 | `BLOCKED` | Preprocessing demonstration only. | Acceptance outcome is not repayment. Feature semantics are masked, missing values exist. |
| CreditMitra narrations / DS007 | `BLOCKED` | None until written provenance, authority/consent, and use restrictions are established. | Sensitive transaction narrations; no label, amounts, or borrower key. Keep out of dashboard processing and modeling. |
| Synthetic datasets / DS008–013 | `BLOCKED` | Clearly marked software/demo fixtures and tests only. | Generated outcomes are not actual borrower events. Never display as evidence of predictive performance. |
| NPCI/RBI aggregate statistics / DS014–016 | `BLOCKED` | Aggregate macro/product context, if attribution and reuse terms are checked. | No borrower rows, features, repayment labels, or individual-level prediction design. Verify source reuse terms. |
| Corrupt RBI workbook / DS017 | `BLOCKED` | None until a readable, authorized file is obtained. | Schema, contents, coverage, and integrity cannot be verified. |
| Kaggle City Bank competition / EXT001 | `BLOCKED` | None until account access and rules are accepted and reviewed. | Not locally present; gated by login/rules. Documentation indicates first-EMI default, a distinct target. Need actual files, schema, licensing and leakage review. |
| OpenML 43454 / EXT002 | `REVIEW_REQUIRED` | Metadata review only; potential separate benchmark after upstream review. | CC0 metadata and binary `loan_status` are visible, but community origin, target construction, feature timing, duplicate risks, and row-level chronology are not verified. |
| PLOS SHG study / EXT003 | `REVIEW_REQUIRED` | Literature and separate survey-method research after supplemental data/privacy review. | Cross-sectional human-participant sample, 400 participants per article. No verified prospective loan-level default label or time split. Article CC BY does not by itself resolve every data/privacy obligation. |

## Qualification gate for an Indian repayment dataset

No current dataset passes this gate. Require all of the following before labeling a source `QUALIFIED_FOR_RESEARCH` for Indian repayment prediction:

- Verifiable source, lawful authority/consent or other valid basis, explicit permitted purpose, retention/deletion terms, and access controls.
- Loan-level cohort with actual dated repayment outcomes and lender-agreed default/cure/restructure definitions; features timestamped at decision time.
- Sufficient observation and outcome windows, explicit censoring/maturity treatment, and chronology that supports a later-period holdout.
- A data dictionary, lineage, quality/missingness/duplicate review, borrower grouping strategy, and sensitive-attribute handling.
- Leakage review and reproducible baseline/model comparison on an untouched time-based test set.

This table does not authorize collection or commercial use. No production Account Aggregator integration or regulatory-compliance claim is part of Phase 6.1.
