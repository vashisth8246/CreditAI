# Financial feature dictionary (Phase 1.1)

**Window:** for the synthetic run, transaction dates from 2024-01-01 through 2024-12-31, with prediction/loan date 2025-01-01; the cutoff is exclusive. The API accepts `observation_start` and `as_of_date`. Monthly arrays are reindexed to every calendar month in that interval; absent transaction months have zero recorded income, expense, and net flow. This does not prove that the account was observed or active in an empty month.

**Input/limitations common to all:** Requires borrower/date/type/amount/category, closing-balance observation, counterparty. Cash flow uses all recorded credits less debits; unpaired transfers between accounts can inflate observed flow. Income is only explicitly identified categories (`SALARY`, `BUSINESS_INCOME`, `OTHER_INCOME`, `PENSION`, `BENEFITS`, `RENTAL_INCOME`, `REMITTANCE_INCOME`). `TRANSFER_IN` is excluded by default to avoid treating own-account transfers as new income. Income categories still require provider/sender verification in real data. Ratio denominators use `max(denominator,1)` in the dataset currency; this prevents division by zero but makes zero-income ratio values large. No winsorization is applied; extreme records are reported by validation and need review.

| Feature | Definition / formula | Why it may matter (hypothesis) | Required fields / limitation |
|---|---|---|---|
| total_income | Sum credits in the explicit income category allow-list | Observed income scale | amount, type, category; category/sender may be misclassified |
| avg_monthly_income | total_income / number of calendar months in requested window | Typical monthly identified income | date, amount, category |
| income_std | Population SD of monthly identified income, including zero-transaction months | Income variability | date, amount, category |
| income_cv | income_std / max(avg_monthly_income, 1) | Relative income variability | monthly income; unstable for near-zero income |
| income_months | Count of calendar months with identified income > 0 | Persistence of identified inflow | date, amount, category |
| income_stability_index | 1 / (1 + income_cv) | Bounded inverse variability proxy | monthly income; defined as 1 for all-zero income under current finite-denominator rule |
| income_growth | OLS slope of monthly identified income against calendar-month index / max(avg_monthly_income,1) | Trend in identified income | date, amount, category; short synthetic window makes trend noisy |
| total_expense | Sum of all debit amounts | Observed outflow burden | amount, type; includes transfers/debt if recorded as debits |
| avg_monthly_expense | Mean monthly debits across all calendar months | Typical observed outflow | date, amount, type |
| expense_std | Population SD of monthly debits including zero-transaction months | Spending variability | date, amount, type |
| expense_ratio | total_expense / max(total_income,1) | Outflow relative to identified income | amount, type, category; may exceed one |
| essential_expense_ratio | Debits labeled rent/food/utilities/transport/EMI/health/education divided by max(total_income,1) | Required-outflow proxy | amount, type, category; depends on merchant categorization |
| discretionary_expense_ratio | Shopping and entertainment debits / max(total_income,1) | Flexible-outflow proxy | amount, type, category; categories are coarse |
| total_cashflow | Sum all credits less all debits | Net recorded account flow | amount, type; transfers may distort if only one side is present |
| avg_monthly_cashflow | Mean monthly net flow including zero-activity months | Typical observed monthly surplus/shortfall | date, amount, type |
| cashflow_std | Population SD of monthly net flow | Net-flow variability | date, amount, type |
| cashflow_volatility | cashflow_std / max(abs(avg_monthly_income),1) | Relative cash-flow variability | date, amount, type, category |
| negative_cashflow_months | Count of calendar months with net flow < 0 | Shortfall frequency | date, amount, type; zero-activity months are zero, not negative |
| cashflow_surplus_ratio | Sum of positive monthly net flows / max(total_income,1) | Positive-flow scale relative to income | date, amount, type, category |
| mean_observed_transaction_balance | Arithmetic mean of balances recorded after transactions | Observed liquidity proxy | balance_after_transaction; weighted toward dates with many transactions, not time-weighted |
| minimum_observed_transaction_balance | Minimum recorded post-transaction balance | Lowest observed transaction-time liquidity | balance_after_transaction; may miss between-transaction lows |
| maximum_observed_transaction_balance | Maximum recorded post-transaction balance | Highest observed transaction-time liquidity | balance_after_transaction |
| observed_transaction_balance_volatility | Population SD of post-transaction balances | Transaction-time liquidity variability | balance_after_transaction; transaction-frequency weighted |
| low_balance_transaction_dates | Count distinct dates with any recorded transaction balance <= the borrower's 10th percentile of transaction balance observations | Low-balance-date proxy | date, balance_after_transaction; does **not** count all low-balance calendar days |
| transaction_count | Number of valid transaction rows | Data activity/context | transaction_id |
| credit_transaction_count | Number of CREDIT rows | Recorded inflow frequency | transaction_type |
| debit_transaction_count | Number of DEBIT rows | Recorded outflow frequency | transaction_type |
| avg_transaction_amount | Mean absolute transaction amount | Typical recorded transaction size | amount |
| median_transaction_amount | Median absolute transaction amount | Robust typical transaction size | amount |
| transaction_frequency | transaction_count / inclusive calendar days from first to last observed transaction | Observed transaction intensity | date, transaction_id; does not measure account coverage |
| unique_counterparties | Distinct non-missing counterparties | Breadth of recorded parties | counterparty; identity resolution required |
| counterparty_diversity | unique_counterparties / transaction_count | Relative breadth of recorded parties | counterparty, transaction_id |
| top_counterparty_share | Maximum counterparty transaction count / all transaction count | Count concentration proxy | counterparty; amount concentration is not measured |
| emi_count | Number of debits categorized EMI | Frequency of identified EMI debits | category, type; not all debt obligations |
| emi_amount | Sum identified EMI debit amounts | Identified EMI outflow amount | amount, category, type; not all debt service |
| emi_to_income_ratio | emi_amount / max(total_income,1) | Identified EMI burden against identified income | amount, category, type; not a complete debt-to-income measure |
| emi_share_of_expenses | emi_amount / max(total_expense,1) | EMI share of all recorded debit outflow | amount, category, type; differs from income burden |
| spending_consistency | 1 / (1 + expense_std / max(avg_monthly_expense,1)) | Bounded inverse monthly expense variability | date, amount, type; zero-expense case follows denominator floor |
| financial_buffer_ratio | mean_observed_transaction_balance / max(avg_monthly_expense,1) | Observed balance relative to monthly outflow proxy | balance, date, amount, type; transaction-weighted balance |
| income_expense_gap | avg_monthly_income - avg_monthly_expense | Typical monthly identified inflow less recorded debit outflow | date, amount, type, category |

Exact duplicate features `negative_cashflow_months`/`cashflow_gap_count`, `emi_to_income_ratio`/`debt_payment_ratio`, and `income_consistency`/`income_stability_index` were removed. `emi_share_of_expenses` is a distinct ratio. Transaction-transfer classification remains a limitation because the base schema does not guarantee an own-account/external-party flag.
