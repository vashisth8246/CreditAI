# CreditAI Phase 3 — Indian Repayment Data Feasibility

**Scope:** Identify and qualify realistic, lawful sources of Indian borrower-level financial features linked to subsequent repayment outcomes. Prioritize evidence of data availability over building another model.

**Status:** Complete. No existing Phase 2.3 benchmark artifacts were modified. `/v1/score` remains `not_validated`.

---

## 1. Executive Summary

**No qualifying Indian borrower-level labeled dataset is publicly available.** After inventorying all local data and researching external sources, the conclusion is:

- The workspace contains **no Indian borrower-level dataset** with both point-in-time application features and subsequent repayment/default outcomes.
- The only real Indian borrower-level labeled datasets that exist are **proprietary lender datasets** accessed through **research partnerships** (e.g., Indifi's 300,000+ MSME loan applications, an unnamed Indian MFI's 2,036,108-borrower dataset). These prove that Indian lenders possess suitable labeled data and are willing to share it with researchers under data-use agreements — but they are **not downloadable**.
- Public Indian credit data (RBI CRILC wilful defaulters, RBI/NPCI aggregates, FACE reports) is either **corporate-only**, **aggregate-only**, or **defaulters-only** — none can train a retail NBFC default model.
- The **Account Aggregator (AA) framework** is the lawful, scalable route for consented borrower financial *features*, but it does **not** provide *outcome labels*. Labels must come from the lender's own loan performance data.
- The most feasible path for a small startup is a **lender/NBFC data partnership** combined with **AA-consented feature access**.

**Smallest realistic first milestone:** Secure a written data-use agreement with one Indian NBFC or fintech lender (or P2P platform) for a pseudonymized extract of their closed personal-loan book with application-time features and subsequent repayment outcomes. Until that agreement is signed and the extract is received, no Indian-borrower model development should begin.

---

## 2. Local Dataset Inventory

Full inventory in [phase_3_dataset_inventory.csv](file:///f:/NUV%20ACD/All%20SEM/7th%20Sem/ML%26DS/New%20folder%20(3)/CreditAI/reports/phase_3_dataset_inventory.csv). Counts below verified by direct file inspection.

### 2.1 Indian borrower-level features with repayment outcomes

**None.** No local dataset combines Indian borrower features with actual repayment/default labels.

### 2.2 Indian financial transaction data without outcomes

| Dataset | Rows | Cols | Features | Target | Limitation |
|---|---:|---:|---|---|---|
| `transactions/CreditMitra_transactions.csv` | 25 | 2 | UPI narration strings | None | No amounts, no borrower ID, no outcomes, no local consent/license. NLP parsing demo only. |

### 2.3 Indian aggregate economic/banking data

| Dataset | Rows | Cols | Content | Borrower level? |
|---|---:|---:|---|---|
| `india_upi/NPCI/` (11 files) | 126 | 4 | Monthly UPI volume/value/banks FY2016-17–FY2026-27 | No |
| `india_banking/RBI DBIE/.../Industry-Wise Deployment...` | ~142 | 11–20 | Industry-wise bank credit deployment | No |
| `india_banking/RBI DBIE/.../Deployment by Major Sectors` | ~110 | 94–168 | Monthly sectoral bank credit | No |
| `india_banking/RBI DBIE/.../SCBs District Wise` | — | — | Corrupted (BadZipFile) | No |

### 2.4 International borrower-level benchmark datasets

| Dataset | Rows | Cols | Target | Indian? |
|---|---:|---:|---|---|
| `archive/accepted_2007_to_2018Q4.csv` | 2,260,701 | 151 | loan_status (US LendingClub) | No |
| `credit_default/default of credit card clients.xls` | 30,000 | 25 | default next month (Taiwan) | No |
| `credit_default/.../german.data` | 1,000 | 21 | creditworthiness class (Germany) | No |
| `credit_default/.../german.data-numeric` | 1,000 | 25 | Same as german.data | No |
| `credit_default/.../crx.data` | 690 | 16 | approval decision (Japan) | No |

### 2.5 Synthetic data

| Dataset | Rows | Cols | Target |
|---|---:|---:|---|
| `synthetic/outcomes.csv` | 800 | 6 | Synthetic 30/60/90-day default flags |
| `synthetic/transactions.csv` | 177,446 | 8 | None (features) |
| `processed/borrower_features.csv` | 800 | 43 | None (features) |
| `synthetic_phase1_1/outcomes.csv` | 800 | 7 | Synthetic default flags + outcome dates |
| `synthetic_phase1_1/transactions.csv` | 177,608 | 8 | None (features) |
| `synthetic_phase1_1/borrower_features.csv` | 800 | 41 | None (features) |

---

## 3. External Source Research

Full evidence table in [phase_3_source_evidence.csv](file:///f:/NUV%20ACD/All%20SEM/7th%20Sem/ML%26DS/New%20folder%20(3)/CreditAI/reports/phase_3_source_evidence.csv).

### 3.1 Verified sources (evidence of actual data existence confirmed)

#### SRC001 — Indifi fintech lender dataset (RESEARCH PARTNERSHIP)

- **Identity:** Indifi Technologies Pvt. Ltd., Indian fintech lender for unsecured MSME loans.
- **Evidence:** NBER Working Paper w34148, "FinTech Lending and Cashless Payments" (Gopal et al.), describes "comprehensive loan application-level data from Indifi... more than 300,000 applications from 2015 to 2022."
- **Features:** Complete applicant screening information, 6-month payment-transaction history, merged credit-bureau scores. All point-in-time at application.
- **Labels:** Loan financing outcomes and loan performance as of 2022.
- **Access:** Proprietary. Requires data-use agreement with Indifi. Not downloadable.
- **Legal:** Indifi's internal data policy + researcher DUA. Indian privacy law applies. Pseudonymization required.
- **Relevance:** HIGH. Indian MSME unsecured lending. Payment-history features align with AA-based cashflow underwriting.
- **Verdict:** The single strongest lead. Proves an Indian lender has suitable labeled data and has shared it with researchers.

#### SRC002 — Indian MFI dataset (RESEARCH PARTNERSHIP)

- **Identity:** Unnamed Indian microfinance institution. Referenced in SMJ article (doi:10.1002/smj.3558) on demonetization and MFI defaults.
- **Evidence:** 2,036,108 borrowers with active loans at Nov 8 2016; full repayment records Jul 2016–Feb 2017; borrower demographics and loan characteristics.
- **Features:** Borrower demographics, loan characteristics (at origination).
- **Labels:** Full ledger repayment records.
- **Access:** Proprietary. Requires identifying and partnering with the (unnamed) MFI.
- **Relevance:** MEDIUM-HIGH. Indian MFI group-lending context. Larger sample but crisis-period window.
- **Verdict:** Proves Indian MFIs share borrower-level repayment data. Specific partner must be identified.

#### SRC003 — RBI CRILC wilful defaulters (PUBLIC, CORPORATE-ONLY)

- **Identity:** RBI CRILC data released via RTI (App. no RBIND/R/E/22/02061). Hosted on dataful.in.
- **Evidence:** 3,057 rows × 6 columns (data_as_on, bank_name, borrower_name, value, units, notes). Snapshot as of Dec 31 2021.
- **Features:** Bank name, borrower name, amount owed (₹ crore). No application features.
- **Labels:** Wilful defaulter classification (dues ≥ ₹25 lakh). **Defaulters only — no non-defaulter comparison group.**
- **Access:** Publicly downloadable from dataful.in.
- **Relevance:** LOW. Corporate large-borrower only. No retail NBFC relevance. No features. Cannot train a model.
- **Verdict:** Supplementary aggregate/corporate context only. Not a training dataset.

#### SRC004 — RBI/NPCI aggregate data (PUBLIC, AGGREGATE-ONLY)

- **Identity:** RBI DBIE sectoral/industry credit deployment; NPCI monthly UPI statistics.
- **Evidence:** Local copies inspected. 126 NPCI monthly rows + RBI sectoral series.
- **Features:** Aggregate credit volumes, UPI volume/value.
- **Labels:** None at borrower level. Aggregate GNPA ratios derivable from RBI FSR but not loan-level.
- **Relevance:** LOW. Macro context only.
- **Verdict:** Already in workspace. Cannot support borrower-level ML.

#### SRC007 — Kaggle "Credit Risk with Home Loans" (SYNTHETIC)

- **Identity:** Kaggle dataset by Gauri Verma, 5,000 records.
- **Evidence:** Kaggle page explicitly states "5,000 synthetic records simulating credit risk profiles." CC0 license.
- **Verdict:** Synthetic. Not evidence of real Indian repayment data. Already have internal synthetic data.

#### SRC008 — Home Credit Default Risk (INTERNATIONAL)

- **Identity:** Kaggle competition dataset from Home Credit (international consumer finance).
- **Verdict:** International benchmark. Not Indian. Useful for methodology only (already have LendingClub/UCI).

#### SRC009 — FACE fintech personal loan reports (AGGREGATE)

- **Identity:** FACE reports drawn from CRIF High Mark records covering 110+ digital NBFCs.
- **Evidence:** Aggregate NPA/delinquency rates, sanction volumes. E.g., fintech small-ticket personal loan 90–170 DPD = 6.4% as of Mar 2026.
- **Verdict:** Useful for calibration targets and prevalence benchmarks. Not borrower-level training data.

### 3.2 Leads requiring confirmation

#### SRC005 — Account Aggregator (AA) framework (INFRASTRUCTURE, NOT LABELED DATA)

- **Identity:** RBI Master Direction on NBFC-Account Aggregators, 2016. Licensed AAs (CAMSFinServ, NESL, FinVu, Cookiejar, OneMoney).
- **Status:** Verified operational framework. But AA provides **features only**, not labels.
- **Relevance:** HIGH as lawful feature-acquisition infrastructure. Must be combined with a lender partnership for outcomes.
- **Verdict:** Essential infrastructure, not a labeled source.

#### SRC006 — Credit Information Companies (CIBIL, Equifax, Experian, CRIF High Mark)

- **Identity:** Four RBI-licensed CICs.
- **Status:** Verified existence and API access. Access requires **lender membership** — not available to a standalone startup.
- **Relevance:** HIGH for features. Historical DPD could serve as label proxy for existing borrowers only.
- **Verdict:** Gold-standard feature source. Access gated behind lender relationship.

#### SRC010 — Indian P2P lending platforms (Faircent, LenDenClub, IndiaP2P)

- **Identity:** RBI-registered P2P NBFCs. Publicly report aggregate NPA in monthly factsheets.
- **Status:** Aggregate NPA verified (e.g., LenDenClub NPA 3.69% as of Oct 2025). **Borrower-level access not confirmed.**
- **Relevance:** MEDIUM-HIGH. P2P personal loans are close to NBFC personal loan underwriting.
- **Verdict:** Promising partnership target. Borrower-level labeled data likely exists internally but access requires partnership.

---

## 4. Source Ranking

Ranked by feasibility for a small startup, relevance to Indian NBFC underwriting, legal/data-governance clarity, and ML usefulness.

| Rank | Source | Type | ML Usefulness | Legal Clarity | Startup Feasibility | NBFC Relevance |
|---:|---|---|---|---|---|---|
| 1 | Indifi research partnership | Lender DUA | High (300k+ loans, features+outcomes) | Medium (DUA required) | Medium (proven willingness) | High (Indian MSME) |
| 2 | Indian MFI partnership | Lender DUA | High (2M borrowers, repayment records) | Medium (DUA required) | Medium (partner unnamed) | Medium (group lending) |
| 3 | P2P platform partnership | Lender DUA | High (retail personal loans) | Medium (DUA required) | Medium (access unconfirmed) | High (personal loans) |
| 4 | Account Aggregator | Infrastructure | Features only | High (RBI-regulated, consent-based) | High (integrate as FIU) | High (lawful features) |
| 5 | Credit bureaus (CICs) | Licensed API | Features + historical DPD | High (CIC Act) | Low (needs lender membership) | High (bureau features) |
| 6 | RBI CRILC wilful defaulters | Public | Very Low (corporate, no negatives) | High (public) | High (downloadable) | Low (corporate) |
| 7 | RBI/NPCI aggregates | Public | None (aggregate) | High (public) | High (local) | Low (macro) |
| 8 | FACE reports | Public aggregate | None (aggregate stats) | High (public) | High (downloadable) | Medium (prevalence benchmarks) |
| 9 | Kaggle synthetic | Synthetic | None (not real) | High (CC0) | High (downloadable) | None |
| 10 | Home Credit (international) | Public benchmark | Medium (methodology) | Medium (Kaggle license) | High (downloadable) | Low (not Indian) |

---

## 5. Key Gaps

1. **No public Indian retail borrower-level labeled dataset exists.** All real Indian labeled data is proprietary to lenders.
2. **AA solves features, not labels.** The consent-based framework is the lawful route for borrower financial data, but subsequent repayment outcomes must come from the lender.
3. **Bureau access is lender-gated.** A startup cannot pull CIBIL/Experian data without being (or partnering with) a regulated lender.
4. **CreditMitra has no provenance.** The 25-row narration file has no license, consent, or authorization record. It cannot be used beyond NLP parsing demos and only after provenance is confirmed.
5. **Corporate defaulter lists are not retail training data.** RBI CRILC wilful defaulters cover ₹25 lakh+ corporate borrowers and have no non-defaulter group.

---

## 6. Recommended Acquisition Path

### Phase 3.1 — Data partnership (prerequisite for any Indian model)

1. **Identify 3–5 target lenders:** Indian fintech/NBFC personal-loan lenders (e.g., Indifi, MoneyView, EarlySalary, KreditBee, CASHe) and P2P platforms (Faircent, LenDenClub). Indifi is the highest-probability lead given their documented research data sharing.
2. **Initiate research partnership:** Approach the lender's data science / risk team with a concrete research proposal. Reference the Indifi NBER paper as precedent for lender-researcher data sharing.
3. **Negotiate a Data Use Agreement (DUA) covering:**
   - Purpose limitation (credit risk model development only)
   - Pseudonymization (no direct identifiers in modeling dataset; separate re-identification key with lender)
   - Data minimization (only application-time features + repayment outcomes)
   - Retention and deletion schedule
   - Access controls and audit logging
   - Publication review rights for the lender
   - Compliance with Digital Personal Data Protection Act, 2023 and RBI lending regulations
4. **Specify the extract before ingestion:**
   - Product: one closed personal-loan or MSME-loan product
   - Observation window: origination dates with ≥12 months of mature follow-up
   - Target: lender-defined default (e.g., 90+ DPD or write-off)
   - Features: all fields available at application time (form fields, bureau pull, bank statement aggregates)
   - Censoring: flag loans that are still active, prepaid, or restructured
5. **Receive a secure offline extract** — not in this repository. Store in controlled access storage.

### Phase 3.2 — AA integration (in parallel, for feature acquisition)

1. Register as (or partner with) a Financial Information User (FIU).
2. Integrate with one licensed Account Aggregator (e.g., FinVu, NESL).
3. Build consent management for borrower-initiated data pulls.
4. Use AA data as the feature stream at scoring time; use lender DUA data for training labels.

### Phase 3.3 — Bureau data (optional, via lender partner)

1. If the lender partner has CIC membership, request that bureau features be included in the DUA extract (pulled at application time, per-borrower consent).
2. This avoids the startup needing its own CIC membership.

---

## 7. Smallest Realistic First Milestone

**Milestone:** Signed Data Use Agreement with one Indian lender for a pseudonymized closed-loan extract.

**Exact evidence required before model development begins:**

1. A **signed written DUA** with an identified Indian NBFC/fintech lender or P2P platform.
2. A **data dictionary** from the lender specifying:
   - Product type and origination date range
   - Default definition (e.g., 90+ DPD) and observation/outcome window
   - List of application-time fields (with timestamps proving point-in-time availability)
   - Censoring/closure status per loan
3. A **sample extract** (e.g., 1,000 rows) received via secure transfer, with:
   - No direct identifiers (PAN, mobile, name) in the modeling view
   - At least 5% positive (default) class or a documented oversampling approach
   - ≥12 months of outcome maturity for the most recent loans
4. **Legal sign-off** from the lender's compliance team confirming lawful basis for sharing.

**Do not proceed to model development until all four items are in hand.** Synthetic and international benchmarks should continue to be used only for pipeline methodology, never as evidence of Indian borrower performance.

---

## 8. What Does NOT Qualify as Evidence

The following were explicitly excluded as proof that suitable labeled Indian data exists:

- **Provider marketing claims** (e.g., "we have alternative data for underwriting") without a documented schema, sample, or access method.
- **Dataset titles alone** (e.g., a Kaggle dataset named "Indian Credit Risk") without inspecting provenance and confirming it is real (not synthetic) and Indian.
- **Aggregate dashboards** (RBI FSR, FACE reports, NPCI statistics) — these report portfolio-level default rates, not borrower-level labeled records.
- **Synthetic labels** (Kaggle "Credit Risk with Home Loans," internal synthetic data) — generated outcomes are not observed defaults.
- **Approval decisions** (UCI Credit Approval) — underwriter decisions are not repayment outcomes.
- **Corporate-only lists** (RBI CRILC wilful defaulters) — no retail borrowers, no non-defaulter group.

---

## 9. Deliverables

- [phase_3_dataset_inventory.csv](file:///f:/NUV%20ACD/All%20SEM/7th%20Sem/ML%26DS/New%20folder%20(3)/CreditAI/reports/phase_3_dataset_inventory.csv) — 17 local datasets with path, format, rows/cols, provenance, license, features, targets, dates, limitations, category.
- [phase_3_source_evidence.csv](file:///f:/NUV%20ACD/All%20SEM/7th%20Sem/ML%26DS/New%20folder%20(3)/CreditAI/reports/phase_3_source_evidence.csv) — 10 external sources with exact identity, availability, lawful access, features, labels, license, effort, verification status, ranking.
- [phase_3_indian_data_feasibility.md](file:///f:/NUV%20ACD/All%20SEM/7th%20Sem/ML%26DS/New%20folder%20(3)/CreditAI/reports/phase_3_indian_data_feasibility.md) — this report.

---

## 10. Reproducibility Notes

- All local row/column counts were verified by direct file reading (Python pandas/openpyxl/xlrd), not inferred from filenames.
- The LendingClub CSV row count (2,260,701 data rows) was confirmed by independent chunked count, status frequency sum, and full load in Phase 2.3.2; the XLSX copy is truncated at Excel's 1,048,576-row limit.
- External source claims were verified against primary sources: NBER working paper, SMJ journal article, RBI RTI response, dataful.in schema, Kaggle dataset pages, RBI Master Direction.
- No raw borrower data was read into this report. Only aggregate counts and schema-level descriptions are included.
- No Phase 2.3 benchmark artifacts or `/v1/score` endpoint were modified.

---

## 11. Conclusion

**Indian borrower-level labeled data is not publicly available.** It exists inside Indian lenders (Indifi, MFIs, P2P platforms) and has been shared with academic researchers under data-use agreements. The lawful path for a startup is:

1. **Lender DUA** for labeled training data (features + outcomes).
2. **Account Aggregator** for lawful, consented feature acquisition at scoring time.
3. **CIC data** via the lender partner (if available).

The smallest realistic first milestone is a **signed DUA with one Indian lender** plus a documented data dictionary and sample extract. Until that is secured, no Indian-borrower model development should begin, and `/v1/score` must remain `not_validated`.

---

## 12. Final Decision: CONDITIONAL GO

**Decision:** CONDITIONAL GO for obtaining Indian validation data.

**Evidence-based reasoning:**

- **GO condition met:** Evidence exists that Indian lenders possess suitable labeled data and are willing to share it with researchers under data-use agreements (Indifi: 300,000+ MSME loans documented in NBER w34148; unnamed MFI: 2,036,108 borrowers documented in SMJ). This proves the data exists and can be lawfully accessed via partnership.
- **GO condition met:** The Account Aggregator framework provides a regulated, consent-based infrastructure for lawful feature acquisition at scoring time.
- **GO condition met:** P2P platforms (Faircent, LenDenClub, IndiaP2P) publicly report aggregate NPA, confirming they track loan-level outcomes and are potential partnership targets.
- **BLOCKER:** No public Indian retail borrower-level labeled dataset exists. All real labeled data is proprietary and requires a signed Data Use Agreement with a lender.
- **BLOCKER:** Bureau data access requires lender membership or partnership; a standalone startup cannot pull CIBIL/Experian directly.
- **BLOCKER:** The workspace contains no Indian borrower-level dataset with both features and outcomes (CreditMitra has no provenance/authorization; aggregate data is macro-only).

**Conditional requirement:** Proceed only after securing a signed Data Use Agreement with an identified Indian NBFC/fintech lender or P2P platform, including a documented data dictionary and sample extract. Until that agreement is in hand, Indian borrower model development must not begin.

**Recommended next action:** Initiate partnership outreach to Indifi (highest-probability lead given documented research sharing) and 2–3 additional Indian fintech/NBFC personal-loan lenders or P2P platforms with a concrete research proposal and DUA template.
