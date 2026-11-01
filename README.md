# CreditAI — ML + NLP-Powered Credit Risk Decisioning Engine

## Stage 1: Core ML Engine (Phase 1)

---

## What is CreditAI?

CreditAI is a machine-learning-powered credit risk decisioning prototype
built for Non-Banking Financial Companies (NBFCs).

The system takes raw borrower financial data as input and outputs a
**Probability of Default (PD)** with explainable risk drivers using SHAP.

The intended production pipeline is:

```
Raw Borrower Data
      |
      v
Transaction / Narration NLP
      |
      v
Feature Engineering
      |
      v
Credit Risk ML Model
      |
      v
Probability of Default (0 to 1)
      |
      v
Demo Credit Score (0-1000)
      |
      v
SHAP Explainability
      |
      v
FastAPI Decisioning API
```

---

## Stage 1 Objective

Stage 1 validates the technical ML pipeline using a publicly available
credit card default dataset. It demonstrates:

- Clean data loading, validation, and preprocessing
- Credit-specific behavioral feature engineering
- Three model training and benchmarking
- Comprehensive credit risk evaluation metrics
- Probability calibration
- SHAP feature explainability
- Reproducible model serialization

---

## Dataset

**UCI Default of Credit Card Clients**

- Source: Yeh & Lien, 2009 (Taiwan credit card issuer)
- Rows: 30,000 borrowers
- Columns: 25 (23 features + ID + Target)
- Target: `default payment next month` (0 = Repaid, 1 = Default)
- Default Rate: 22.12% (3.52:1 class imbalance)

### Feature Groups

| Group | Columns |
|---|---|
| Credit Limit | LIMIT_BAL |
| Demographics | Gender (`SEX` model input), EDUCATION, MARRIAGE, AGE |
| Repayment Status (6 months) | PAY_0, PAY_2, PAY_3, PAY_4, PAY_5, PAY_6 |
| Bill Amounts (6 months) | BILL_AMT1 to BILL_AMT6 |
| Payment Amounts (6 months) | PAY_AMT1 to PAY_AMT6 |

---

## Feature Engineering

The following behavioral credit risk signals are engineered from raw features:

| Feature | Formula | Signal |
|---|---|---|
| `UTIL_1..6` | BILL_AMT / LIMIT_BAL | Monthly credit utilization |
| `AVG_UTILIZATION` | Mean of UTIL_1..6 | Average utilization burden |
| `MAX_UTILIZATION` | Max of UTIL_1..6 | Peak utilization stress |
| `PAY_TO_BILL_1..6` | PAY_AMT / max(BILL_AMT, 1) | Monthly repayment effort |
| `AVG_PAY_TO_BILL` | Mean of PAY_TO_BILL_1..6 | Average repayment ratio |
| `MAX_DELINQUENCY` | Max of PAY_0..PAY_6 | Worst delinquency month |
| `AVG_DELINQUENCY` | Mean of PAY_0..PAY_6 | Average delinquency level |
| `DELINQUENT_MONTHS_COUNT` | Count months where PAY > 0 | Delinquency frequency |
| `RECENT_DELINQUENCY_FLAG` | PAY_0 > 0 | Recent month late payment |
| `DELINQUENCY_TREND_SHORT` | PAY_0 - PAY_2 | 1-month trend |
| `DELINQUENCY_TREND_LONG` | PAY_0 - PAY_6 | 6-month trend |
| `BILL_CHANGE_1_2` | BILL_AMT1 - BILL_AMT2 | Recent balance change |
| `BILL_GROWTH_OVER_LIMIT` | (BILL_AMT1 - BILL_AMT6) / LIMIT_BAL | Balance growth rate |
| `PAYMENT_MONTHS_COUNT` | Months with PAY_AMT > 0 | Payment frequency |
| `TOTAL_PAY_TO_TOTAL_BILL` | Sum(PAY_AMT) / Sum(BILL_AMT) | Repayment coverage |
| `PAYMENT_AMOUNT_STD` | Std of PAY_AMT1..6 | Payment volatility |
| `TIMELY_PAYMENT_COUNT` | Months where PAY <= 0 | On-time payment count |

**Total: 50 features** (23 raw + 27 engineered)

---

## ML Models

| Model | Role | Key Settings |
|---|---|---|
| Logistic Regression | Linear baseline | class_weight=balanced, StandardScaler |
| Random Forest | Non-linear benchmark | 200 trees, max_depth=10, balanced |
| **XGBoost** | **Primary model** | 300 trees, scale_pos_weight~3.52, lr=0.05 |

**Train/Validation/Test Split:** 70% / 15% / 15% (stratified, seed=42)

---

## Evaluation Metrics

Because the dataset is **class-imbalanced (22% defaults)**, accuracy alone
is NOT used. All models are evaluated with:

| Metric | Why It Matters |
|---|---|
| ROC-AUC | Discrimination ability across all thresholds |
| PR-AUC | Precision-Recall tradeoff (important for imbalanced data) |
| KS Statistic | Max separation between good and bad CDF distributions |
| Gini Coefficient | 2 * ROC-AUC - 1 (standard banking metric) |
| Brier Score | Probability calibration quality |
| Precision / Recall / F1 | Classification performance at threshold |
| Risk Decile Table | Monotonic bad-rate lift from highest to lowest risk |

---

## Probability Calibration

Raw predicted probabilities from tree models can be overconfident.
Calibration (Platt Scaling / sigmoid) is applied on the validation set
to align predicted probabilities with observed default rates.

---

## Explainability

SHAP (SHapley Additive exPlanations) is used with `TreeExplainer`
for the XGBoost model. Each prediction outputs:

- Top 3 risk-**increasing** feature contributions
- Top 3 risk-**decreasing** feature contributions

---

## IMPORTANT LIMITATION

> **This Stage 1 prototype does NOT prove that CreditAI performs better
> than CIBIL, traditional underwriting, or real Indian NBFC credit-risk systems.**

The UCI dataset is from Taiwan (2005) and is used purely to **validate
the technical ML pipeline**. Real-world validation requires:

- Actual lender / NBFC data
- Consented borrower financial data
- Real repayment history and default labels
- Regulatory compliance and data governance
- Demographic fairness and stability testing
- Proper backtesting and champion-challenger methodology

---

## Project Structure

```
CreditAI/
|
|-- data/
|   `-- credit_default/
|       `-- default of credit card clients.xls
|
|-- src/
|   |-- __init__.py
|   |-- config.py              # Paths, constants, feature groups
|   |-- data_loader.py         # Excel loading and diagnostics
|   |-- preprocessing.py       # Validation, cleaning, ID removal
|   |-- feature_engineering.py # 27 behavioral credit features
|   |-- train.py               # Full training + evaluation pipeline
|   |-- evaluate.py            # Credit metrics (AUC, KS, Deciles)
|   |-- calibration.py         # Platt scaling calibration
|   `-- predict.py             # Single-borrower inference
|
|-- models/
|   |-- creditai_model.joblib
|   |-- feature_names.json
|   `-- model_metadata.json
|
|-- reports/
|   `-- figures/
|       |-- target_distribution.png
|       |-- roc_curves.png
|       |-- pr_curves.png
|       |-- calibration_curve.png
|       |-- risk_deciles.png
|       `-- feature_importance_shap.png
|
|-- tests/
|   `-- test_pipeline.py
|
|-- requirements.txt
|-- README.md
`-- .gitignore
```

---

## How to Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Train all models and evaluate

```bash
python -m src.train
```

### 3. Run unit tests

```bash
python -m pytest tests/ -v
```

### 4. Run prediction on a sample borrower

```bash
python -m src.predict
```

---

## Phase 2 (Next Steps)

- Integrate CreditMitra UPI narration NLP parser
- Engineer transaction-level behavioral features
- Connect to real NBFC lender data via Account Aggregator APIs
- Deploy as FastAPI REST endpoint (`POST /v1/score`)
- Add CIBIL/bureau score integration
- Add demographic fairness audit (AIF360)
- Build champion-challenger model governance framework

## Phase 1B: Synthetic financial-behavior risk engine

This track supplements the retained UCI benchmark with a clearly labeled synthetic dataset for transaction feature development. It simulates 12 months for 800 heterogeneous profiles (seed 42), plus probabilistic synthetic 30/60/90-day outcomes. These records are generated solely to exercise software; they are not actual borrowers, and metrics are not lending evidence.

Architecture: transaction validation and pre-cutoff filtering → borrower financial features → stratified 70/15/15 train/validation/test split → Logistic Regression, Random Forest, and XGBoost comparison → validation ROC-AUC model selection → validation-fitted Platt sigmoid → test evaluation and SHAP for a selected tree model.

Feature definitions are implemented in `src/features/financial_features.py` and explained individually in `reports/financial_feature_dictionary.md`. Ratios divide by the relevant total income or expense (floor denominator 1); monthly volatility uses population standard deviation; income/spending consistency is `1/(1+CV)`; growth is the linear monthly trend divided by mean monthly income; cashflow is credits minus debits; a cash-flow gap is a negative net-flow month; buffer is mean observed closing balance divided by mean monthly expense; counterparty diversity is unique counterparties / transactions. Data are cut off strictly before the prediction date, and outcome/loan columns are explicitly rejected by the model feature selector.

### Reproduce the synthetic track

```bash
python scripts/generate_synthetic_data.py
python scripts/build_features.py
python scripts/train_models.py
python scripts/evaluate_model.py
python -m pytest tests/ -v
```

The Phase 1.1 scripts write transactions/outcomes/features to `data/synthetic_phase1_1/`, model artifacts to `models/synthetic_phase1_1/`, and comparison, split prevalence, deciles, calibration curve, SHAP (only if a tree model is selected), and report to `reports/synthetic_phase1_1/`. `predict_risk(transaction_dataframe, as_of_date=...)` returns calibrated PD and actual selected-model SHAP factors when applicable; it does not produce an unsupported confidence value.

The original Phase 1B outputs are retained as historical artifacts. Phase 1.1 audit reruns use isolated `data/synthetic_phase1_1/`, `models/synthetic_phase1_1/`, and `reports/synthetic_phase1_1/` locations. See `reports/phase_1_1_audit.md` for the corrected evaluation. Synthetic labels and transactions do not establish production performance, fairness, Indian thin-file validity, regulatory compliance, or superiority to incumbent systems. Real consented data, actual repayment labels, lender validation, governance and monitoring remain future requirements. Account Aggregator integration and pricing/approval decisions are out of scope.
