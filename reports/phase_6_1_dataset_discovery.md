# CreditAI Phase 6.1 — Dataset Discovery

**As of:** 2026-10-13  
**Scope:** local project data and three specified public candidates. This is an inventory, not a grant of data rights.

## Findings

The workspace contains one large borrower-level historical repayment dataset suitable for a bounded offline research benchmark: LendingClub (United States). The UCI Taiwan credit-card dataset also has a genuine next-month default outcome and a temporal feature/label definition, but is small, old, product-specific, and not Indian. The local German data has a creditworthiness class rather than a clean observed default event. No authorized Indian borrower-level historical repayment data is present.

Aggregate Indian UPI/RBI files have no borrower rows or repayment target. Synthetic records are useful for software demonstrations and tests only. The local CreditMitra narration sample has no documented consent or authorization and no outcome; it is not used by the dashboard or modeling pipeline. One local RBI workbook is unreadable. A truncated LendingClub XLSX is not counted as independent observations.

| ID | Dataset | Local state / size | Rows × columns | Outcome and time | Phase 6.1 decision |
|---|---|---:|---:|---|---|
| DS001 | LendingClub accepted loans | Present, 2,260,701 rows | 2,260,701 × 151 | Terminal `loan_status`; issue dates 2007–2018Q4. Closed-cohort outcome, variable horizon. | `QUALIFIED_FOR_RESEARCH` with limitations for historical U.S. benchmarking only |
| DS002 | LendingClub Excel export | Present, truncated at Excel row limit | 1,048,575 × 151 | Same source as DS001; overlapping copy, not independent. | `BLOCKED` for modeling; preserve as redundant/truncated source |
| DS003 | UCI Taiwan credit-card default | Present | 30,000 × 25 | Default payment next month; six preceding monthly billing/payment periods in 2005. | `QUALIFIED_FOR_RESEARCH` for separate Taiwan benchmark only |
| DS004–005 | UCI German credit | Present, two encodings | 1,000 × 21 and 1,000 × 25 | Good/bad creditworthiness proxy; no row-level dates. DS005 duplicates the encoded representation of DS004. | `REVIEW_REQUIRED`; not direct default prediction |
| DS006 | UCI Credit Approval | Present | 690 × 16 | Accept/reject decision, not repayment/default. 67 missing cells reported by prior inventory. | `BLOCKED` for default modeling; preprocessing only |
| DS007 | CreditMitra transaction narration sample | Present | 25 × 2 | No outcome or borrower/loan key; authorization and consent absent from workspace. | `BLOCKED`; do not use pending provenance/authorization |
| DS008–013 | Project synthetic data/features | Present | 800 synthetic outcomes; transaction/features as detailed in CSV | Generated labels/features, not observed repayment. | `BLOCKED` as real evidence; demo and tests only |
| DS014–016 | NPCI UPI and RBI credit statistics | Present | Aggregates; see CSV | No borrower-level labels. UPI monthly history spans FY2016–17 to FY2026–27 through Sep 2026; RBI files are aggregate series. | `BLOCKED` for borrower scoring; macro context only |
| DS017 | RBI district credit workbook | Present but corrupt | Unreadable | Unknown. | `BLOCKED` until authorized readable copy is obtained |
| EXT001 | Kaggle City Bank vehicle-finance competition | Not downloaded; competition access | Unknown until accepted rules/files inspected | Competition documentation describes default at first EMI due date; not 90-day default or general PD. | `BLOCKED` pending access, terms and schema review |
| EXT002 | OpenML Credit-Risk-Dataset, ID 43454 | Remote metadata only; not downloaded | 32,581 × 12 features per OpenML metadata | `loan_status` described as 0 non-default / 1 default; no verified per-row chronology. | `REVIEW_REQUIRED`; community provenance and target generation need review |
| EXT003 | PLOS ONE SHG microfinance study (2026) | Article and supporting data links; files not acquired | Article reports 400 members; supplementary schemas not inspected | Cross-sectional survey constructs, not point-in-time future loan default. | `REVIEW_REQUIRED` for separate survey research, not general PD training |

The machine-readable inventory at [`phase_6_1_dataset_inventory.csv`](phase_6_1_dataset_inventory.csv) records path, source, format, byte size, counts, target, prevalence when established, coverage, missingness, duplicates, provenance, usage caveats, privacy/leakage risks, proposed use, and qualification decision. “Not measured” and “not verified” are intentionally retained where evidence is absent. Counts and missingness from older local inventory reports are labeled as such, rather than presented as freshly recomputed.

## Candidate source checks

- Kaggle competition [City Bank Loan Default Prediction](https://www.kaggle.com/competitions/city-bank-loan-default-prediction/data): files are gated by Kaggle login and competition rules/acceptance. No download or access bypass was attempted. First-EMI target semantics must be rechecked against the accepted data documentation and actual schema before use.
- [OpenML entry 43454](https://www.openml.org/search?id=43454&type=data): public metadata indicates 32,581 rows, 12 features, CC0, and `loan_status`; quality metadata reports 4,011 missing cells and 3,943 rows with missing attributes, without a verified denominator for these summary counts. Community provenance and target construction remain uncertain. No raw file was downloaded.
- [PLOS ONE SHG study](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0341674): article reports a cross-sectional sample of 400 women in West Bengal and links supporting files. The article is CC BY; supplementary data terms, schema, and participant-data protections must be reviewed on retrieval. The described constructs do not establish a time-indexed borrower default target.
- [UCI Taiwan default dataset](https://archive.ics.uci.edu/dataset/350/default): local dataset and project documentation identify CC BY 4.0 and next-month default label. The product, geography, vintage, sensitive attributes, and license attribution requirements constrain reuse.

These source references are discovery evidence, not legal advice. Commercial use needs a separate rights and privacy review. No private data, gated data, or account integration was acquired.

## Limits and acquisition recommendation

There is no qualified Indian borrower-level dataset with authorized point-in-time application/transaction features and actual subsequent repayment outcomes. Existing LendingClub evidence can demonstrate an offline research pipeline but cannot validate Indian borrowers or a lender's deployment. Taiwan UCI supports an independent historical benchmark, not geographic transfer. Aggregate RBI/NPCI statistics cannot be converted into borrower labels.

Recommended acquisition order:

1. Seek a lender or regulated-finance partner willing to provide a governed, consent-compatible, pseudonymized historical loan cohort with origination-time features, repayment schedules, dated payment events, servicing outcomes, and stable pseudonymous borrower/loan keys. Agree purpose, retention, access, security, deletion, and permitted research/commercial use before receipt.
2. Define a lender-approved outcome (for example, a specific days-past-due threshold within a stated horizon), observation window, cure/restructure treatment, censoring rules, and maturity requirement before data transfer.
3. Request a data dictionary, provenance, access terms, consent/authority basis, cohort dates, lineage, and a small schema-only sample first. Keep direct identifiers out of the modeling environment and audit duplicate/related borrowers before splitting.
4. Optionally request Kaggle access for the first-EMI competition as a separately licensed, limited research benchmark; do not conflate it with standard PD. Review OpenML only after its upstream provenance is resolved. Use the PLOS files for contextual SHG research only after human-participant data review.
5. Keep U.S. LendingClub and Taiwan UCI as distinct external benchmarks. Never pool them with Indian data absent a defensible domain design and separate evaluation.

## Reproducible aggregate artifacts

[`scripts/phase_6_1_build_artifacts.py`](../scripts/phase_6_1_build_artifacts.py) streams DS001 in 100,000-row chunks and exports only aggregate, non-identifying summaries to the frontend. The generated summary contains counts, segment rates with denominators, histogram bins, correlations, and copied benchmark metrics/split metadata. It does not export borrower rows, IDs, or scores. The full source is not loaded into the browser.

See also [`phase_6_1_qualification_decision.md`](phase_6_1_qualification_decision.md), [`phase_6_1_feature_inventory.csv`](phase_6_1_feature_inventory.csv), and [`phase_6_1_data_visualization_spec.md`](phase_6_1_data_visualization_spec.md).
