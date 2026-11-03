# Phase 10 Feature Engineering and Leakage Prevention Documentation
**Project:** CreditAI  
**Target:** Next-month default prediction (DS003, Taiwan)  
**Schema Definition:** 23 Raw Inputs -> 50 Total Features (27 Domain-Engineered)  

---

## 1. Domain Feature Inventory

| Group | Feature Names | Formulation | Domain Rationale | Source Fields |
|:---|:---|:---|:---|:---|
| **A. Credit Utilization** | `UTIL_1` to `UTIL_6` | `max(0, BILL_AMT_t) / max(1, LIMIT_BAL)` | High revolving utilization is strongly predictive of credit strain. Negative bills clipped to 0 (credits). | `BILL_AMT1..6`, `LIMIT_BAL` |
| | `AVG_UTILIZATION` | Mean of `UTIL_1..6` | Average sustained leverage across 6-month trajectory. | `UTIL_1..6` |
| | `MAX_UTILIZATION` | Max of `UTIL_1..6` | Peak credit limit absorption during observation window. | `UTIL_1..6` |
| **B. Payment-to-Bill Ratios** | `PAY_TO_BILL_1` to `PAY_TO_BILL_6` | `PAY_AMT_t / max(1, BILL_AMT_t)` | Ratio of payments made to outstanding balance billed. Clipped to [0.0, 5.0]. | `PAY_AMT1..6`, `BILL_AMT1..6` |
| | `AVG_PAY_TO_BILL` | Mean of `PAY_TO_BILL_1..6` | Consistent full-payer vs revolving minimum-payer indicator. | `PAY_TO_BILL_1..6` |
| **C. Delinquency Dynamics** | `MAX_DELINQUENCY` | `max(PAY_0, PAY_2..6)` | Worst payment delay experienced in past 6 months. | `PAY_0`, `PAY_2..6` |
| | `AVG_DELINQUENCY` | `mean(PAY_0, PAY_2..6)` | Average delinquency severity over time. | `PAY_0`, `PAY_2..6` |
| | `DELINQUENT_MONTHS_COUNT` | `sum(PAY_t > 0)` | Number of delinquent billing cycles out of 6. | `PAY_0`, `PAY_2..6` |
| | `RECENT_DELINQUENCY_FLAG` | `int(PAY_0 > 0)` | Recency indicator: whether payment was delayed in the most recent cycle. | `PAY_0` |
| | `DELINQUENCY_TREND_SHORT` | `PAY_0 - PAY_2` | Delinquency acceleration in immediate past 2 months. | `PAY_0`, `PAY_2` |
| | `DELINQUENCY_TREND_LONG` | `PAY_0 - PAY_6` | Net 6-month repayment trajectory trend. | `PAY_0`, `PAY_6` |
| **D. Balance Trajectory** | `BILL_CHANGE_1_2` | `BILL_AMT1 - BILL_AMT2` | Immediate balance expansion / contraction. | `BILL_AMT1`, `BILL_AMT2` |
| | `BILL_GROWTH_OVER_LIMIT` | `(BILL_AMT1 - BILL_AMT6) / LIMIT_BAL` | Total balance expansion scaled by available line. | `BILL_AMT1`, `BILL_AMT6`, `LIMIT_BAL` |
| **E. Payment Consistency** | `PAYMENT_MONTHS_COUNT` | `sum(PAY_AMT_t > 0)` | Active repayment months out of 6 cycles. | `PAY_AMT1..6` |
| | `TOTAL_PAY_TO_TOTAL_BILL` | `sum(PAY_AMT) / max(1, sum(BILL_AMT))` | Aggregate 6-month debt service efficiency ratio. | `PAY_AMT1..6`, `BILL_AMT1..6` |
| | `PAYMENT_AMOUNT_STD` | `std(PAY_AMT1..6)` | Payment installment stability vs erratic lump sums. | `PAY_AMT1..6` |
| **F. Timely Repayments** | `TIMELY_PAYMENT_COUNT` | `sum(PAY_t <= 0)` | Count of fully paid / current months. | `PAY_0`, `PAY_2..6` |

---

## 2. Leakage Prevention Protocol

1. **Temporal Isolation:** All feature signals are strictly computed from historical statements (April to September 2005). The outcome variable (`default payment next month`, October 2005) is never accessible during feature engineering.
2. **Identifier Stripping:** Borrower `ID` is permanently purged prior to preprocessing and training to prevent rote memorization.
3. **Pipeline Encapsulation:** Imputation medians and scaling parameters (mean and standard deviation) are strictly calculated on the 70% training split via `scikit-learn` `Pipeline(StandardScaler())`. Validation and test splits are transformed using frozen train statistics only.
