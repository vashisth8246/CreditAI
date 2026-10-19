# CreditAI Phase 1.1 — Synthetic risk pipeline audit

## Scope and inspected implementation

Inspected `scripts/generate_synthetic_data.py`, `scripts/build_features.py`, `scripts/train_models.py`, `scripts/evaluate_model.py`; `src/data/generate.py`, `validation.py`, `preprocessing.py`; `src/features/financial_features.py`; `src/models/train.py`, `evaluate.py`, `predict.py`; `src/calibration/calibrate.py`; `src/explainability/shap_explainer.py`; `tests/`; and the existing UCI model bundle, feature names, metadata, README, and prior reports.

The audited run has 800 distinct borrowers, 177,608 transactions, and 40 nonduplicated borrower features. Transactions cover 2024-01-01 through 2024-12-31. Features are cut off strictly before loan/prediction date 2025-01-01. Inference uses the same 12-month window relative to its cutoff. The synthetic outcome window is days 1–90 after loan date. One sampled default event day produces nested 30/60/90-day indicators; non-defaults have no outcome date. The event is generated probabilistically from pre-loan synthetic history. The target is therefore an artificial function of related inputs, not independent observed repayment behavior.

The data generator and model trainer were traced to `src/data/generate.py` and `src/models/train.py`. Model training uses a fixed seed (42), borrower-level rows, stratified 70/15/15 splits, and saved borrower IDs per split. Outcomes join one-to-one by borrower ID; only the features table is passed to the feature selector. Calibration fits on validation predictions. Model selection and the experimental threshold use validation only. Test metrics are produced after these choices are frozen. XGBoost 3.2.0 imported and trained in this run.

## Confirmed code defects and changes

1. **Generic transfers counted as income.** `TRANSFER_IN` was treated as income without evidence that it was external earnings. Income now uses an explicit allow-list of labeled income categories; generic transfers are excluded. Synthetic irregular income is labeled `OTHER_INCOME`. Real data still needs sender/account relationship verification.
2. **Inactive months omitted.** Monthly aggregates previously contained only transaction months. They now reindex to the calendar window, including zero-record months. This is a zero-*observed-flow* convention and can confuse inactivity with zero income; account coverage is unavailable.
3. **Duplicate signals.** Removed `cashflow_gap_count` (duplicate of negative months), `debt_payment_ratio` (previously duplicate of EMI/income), and `income_consistency` (duplicate of income stability). `emi_share_of_expenses` is now a distinct denominator. The model has 40 unique features.
4. **Misleading balance/debt names.** `low_balance_days` became `low_balance_transaction_dates`, explicitly counting only dates with low transaction-time balance observations. Mean/volatility/min/max balance fields now say they are transaction-observation based. EMI ratios are labeled EMI proxies; they do not represent all debt obligations.
5. **Income growth window.** The slope is now calculated over the complete calendar timeline rather than only active transaction months.
6. **Label horizon consistency.** Default labels now use one event day in days 1–90, so 30-day default implies 60- and 90-day default. The label formula and its behavior overlap are documented. No coefficients were adjusted to improve metrics.
7. **Evaluation lacked a prevalence comparator and threshold protocol.** Added a prevalence-only dummy, split default rates, model comparison across validation and test, and a threshold selected by validation F1 only. The threshold is explicitly experimental.
8. **Calibration could invert ranking.** The unconstrained sigmoid could fit a negative slope on a weak validation ranker. Platt scaling now constrains the slope to be nonnegative; it cannot reverse risk ordering. Validation fit metrics remain in-sample. In this run, the baseline is selected, so calibrated predictions remain effectively constant.
9. **Artifact collision risk.** Phase 1.1 outputs are isolated in `data/synthetic_phase1_1/`, `models/synthetic_phase1_1/`, and `reports/synthetic_phase1_1/`.

## Synthetic label audit and leakage

The default probability is the logistic transform of the documented synthetic rule in `reports/data_generation_assumptions.md`: credit CV, debit shortfall relative to identified income, EMI/income, and explicit profile adjustments. A Bernoulli draw samples default presence; if present, an event day is sampled uniformly from 1 to 90. The financial terms overlap with engineered features by design. This is **construct overlap**, not future-data leakage, but it means the experiment tests recovery of a hand-authored formula and cannot validate real default risk. Hidden profile adjustments and simplified amount/category rules add further synthetic artifacts.

No future transaction or outcome field enters the features. Feature selection rejects 30/60/90-day labels, loan amount/date, and outcome date. Every generated borrower appears once; splits are saved in `reports/synthetic_phase1_1/borrower_splits.csv` and tested for disjoint borrower membership. All transaction dates precede the prediction date. The run is reproducible under the recorded seed and generator code; changing the generator changes the synthetic cohort and means old/new scores are not a controlled paired comparison.

## Evaluation findings

Split default prevalence: train **0.1768**, validation **0.1833**, test **0.1750**. The baseline PR-AUC equals prevalence (0.183 validation, 0.175 test); model PR-AUC should be read against those values.

Validation ROC-AUC: prevalence dummy **0.500**, Logistic Regression **0.488**, Random Forest **0.468**, XGBoost **0.440**. Accordingly, validation selected the prevalence dummy. This is an explicit no-skill result; none of the trained risk models beat the baseline on validation ROC-AUC. Held-out test ROC-AUCs for the uncalibrated candidates were LR **0.666**, RF **0.640**, XGBoost **0.570**. These test results do not change selection: choosing LR/RF after seeing them would be test-set tuning. The validation/test rank reversal indicates high instability in this small synthetic sample.

For the selected dummy on test, ROC-AUC is **0.500**, PR-AUC **0.175**, raw Brier **0.144378**, calibrated Brier **0.144444**, and prevalence-baseline Brier **0.144378**. Calibration did not improve held-out Brier versus the baseline; the tiny difference is not meaningful evidence of calibration quality. The calibrated test probabilities are essentially constant at **0.18333** (min and max approximately equal), so no scores reach 0.50. The held-out calibration plot has one point near prevalence because constant probabilities cannot form informative bins; it does not establish good calibration.

The validation-F1 threshold is **0.183333**. It labels every constant calibrated score positive, yielding test recall **1.00**, precision **0.175**, and F1 **0.298**; this is an unhelpful classifier and not a lending threshold. At the conventional 0.50 cutoff, calibrated recall is **0.00** because all predictions are below 0.50. Ranking metrics remain the threshold-independent comparisons. See `reports/synthetic_phase1_1/model_comparison.csv`, `split_prevalence.csv`, `risk_deciles.csv`, and `calibration_curve.png` for the full metrics, confusion matrices, and decile table.

SHAP was not run for the selected model because it is a constant prevalence dummy and has no borrower-specific contribution model. No fabricated local factors are returned. The prior UCI benchmark retains its separate tree model and its existing explainability artifacts.

Previous Phase 1 metrics (validation ROC-AUC 0.590, test ROC-AUC 0.540, calibrated Brier 0.144) came from the earlier synthetic definition and are not directly comparable to this corrected rerun. No claim of metric improvement is made.

## Potential risks requiring more evidence

- Category/sender labels cannot reliably distinguish income from internal transfers without account/counterparty identity and source metadata.
- Empty observed months may mean missing data rather than no financial activity.
- Transaction-time balances are frequency-weighted; daily balances are unavailable.
- EMI records are not a complete debt registry; transfer pairing, source coverage, seasonality, censored outcomes, and repayment event mechanics are simplified or absent.
- 120 validation/test borrowers give noisy rank and calibration estimates. No uncertainty intervals or real-population representativeness are established.

## Tests and preservation

Full suite result: **12 passed**. Coverage includes transaction validation, post-outcome exclusion, cutoff, absent calendar months, transfer/income category behavior, nonduplicate features, label horizon nesting, reproducibility, disjoint borrower splits, calibration monotonicity/validation metadata, threshold-selection metadata, scoring and bundle reload, and hashes of the existing UCI bundle/feature names/metadata before and after the synthetic train test.

The existing UCI `creditai_model.joblib`, feature names, and metadata files were not modified by the Phase 1.1 run; the test verified unchanged hashes during synthetic training. The metadata file already contained a recovery note from the prior session: its benchmark identity and feature list were reconstructed from the untouched UCI bundle because original metric fields were not recoverable then. This audit did not reconstruct or invent those missing historic metrics.

## Remaining limitations before any real-data pilot

This pipeline is an auditable software experiment, not a production risk model. A real pilot needs consented and governed transaction records, validated income/transfer/debt classification, outcome dates and lender-defined default labels, sufficient longitudinal borrower cohorts, temporal and external validation, calibration and threshold policy approved for a defined use, fairness and stability evaluation, and operational/model-risk review. No regulatory compliance, Indian thin-file validity, or incumbent-system comparison has been established.
