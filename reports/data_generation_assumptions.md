# Phase 1.1 synthetic data generation assumptions

This file documents the deterministic development generator in `src/data/generate.py` (NumPy generator seed 42 by default). Data are fictional and must not be represented as observed people or lending outcomes.

## Observation and outcome dates

- Borrower transaction observation: 2024-01-01 through 2024-12-31 (12 calendar months).
- Prediction/loan date: 2025-01-01.
- Feature cutoff: strictly earlier than 2025-01-01.
- Outcome horizon: days 1 through 90 after loan date. `default_30d`, `default_60d`, and `default_90d` are nested cumulative indicators from one sampled default event day; `outcome_date` is absent for non-defaults.
- No transaction after prediction date is generated or used as a model feature. Label formation uses only the synthetic pre-loan transaction history and an independent random draw.

## Population and transaction assumptions

800 borrowers cycle through eight hand-authored profiles: stable salary, stable business, volatile, high expense, cash gap, gig-like, healthy, and unstable. A lognormal base inflow is centered near 52,000 units with profile-specific dispersion. Borrowers receive one monthly primary inflow, 12–23 debit transactions per month, randomized dates/categories/amounts, and accumulated closing balances floored at zero. The category and amount distributions are programmer assumptions, not estimates from lender or household records. The generator's generic `OTHER_INCOME` category represents modeled gig/irregular inflows; `TRANSFER_IN` is not treated as income in feature engineering.

## Synthetic label rule

For each borrower, the generator computes a noisy-probability target from the full pre-loan year: `risk_logit = -2.25 + 1.05*min(credit_amount_CV,2) + 1.5*min(max(0,(debits-income)/income),2) + 1.1*min(EMI/income,1) + 0.48*I(profile in {cash_gap,unstable}) - 0.30*I(profile=healthy)`. Probabilities are the logistic transform and a Bernoulli draw determines whether a default event occurs by 90 days; a uniform day 1–90 is drawn conditional on such an event. Thus labels intentionally depend on constructs that overlap model features (income volatility, cash-flow shortfall, EMI burden), as a supervised synthetic pipeline should, but this is a **generator relationship**, not independently observed repayment behavior. Profile effects and simplified proxy calculations are also not represented fully in features. The model can only demonstrate end-to-end mechanics and recovery of an arbitrary synthetic rule.

The label rule is not tuned to improve benchmark metrics. Changes in this audit correct income-category consistency and event-date nesting while preserving the stated coefficients. If this generator changes, its version and metrics must be treated as a new experiment.

## Known limitations

No own-account transfer pairing, verified income source, debt registry, account coverage indicator, holidays, seasonality evidence, real repayment process, selection bias, censoring, or lender policy is modeled. Empty transaction months are assigned zero observed monthly flows by the feature pipeline; this can confound lack of activity with zero income/spending. Transaction balances are sampled at transaction points, not measured as daily time-weighted balances. These assumptions prohibit real credit-risk inference.
