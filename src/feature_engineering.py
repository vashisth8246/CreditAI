"""
CreditAI: Feature Engineering Module
Transforms raw credit ledger data into predictive behavioral risk features.
Computes credit utilization, payment ratios, delinquency progression,
balance trends, payment consistency, and timely repayment indicators.

All features are strictly derived from historical data (April - September 2005).
Zero target leakage is guaranteed.
"""

import pandas as pd
import numpy as np


def engineer_credit_features(df: pd.DataFrame, verbose: bool = False) -> pd.DataFrame:
    """
    Constructs domain-specific behavioral credit risk features from preprocessed data.
    
    Feature Groups Added:
    ---------------------
    A. Monthly Credit Utilization Ratios (UTIL_1 to UTIL_6, AVG_UTIL, MAX_UTIL)
    B. Payment-to-Bill Ratios (PAY_TO_BILL_1 to PAY_TO_BILL_6, AVG_PAY_TO_BILL)
    C. Delinquency Dynamics (MAX_DELINQ, AVG_DELINQ, DELINQ_MONTHS_COUNT, RECENT_DELINQ_FLAG, DELINQ_TREND_SHORT, DELINQ_TREND_LONG)
    D. Balance Trajectory (BILL_CHANGE_1_2, BILL_GROWTH_OVER_LIMIT)
    E. Payment Consistency (PAYMENT_MONTHS_COUNT, TOTAL_PAY_TO_TOTAL_BILL, PAYMENT_AMOUNT_STD)
    F. Timely Repayment Count (TIMELY_PAYMENT_COUNT)
    
    Parameters:
    -----------
    df : pd.DataFrame
        Cleaned feature matrix from preprocessing (without ID, without Target).
    verbose : bool, default=False
        Whether to print feature engineering progress.
        
    Returns:
    --------
    pd.DataFrame
        Enriched feature matrix containing original features plus all engineered signals.
    """
    X = df.copy()

    # Define feature lists
    bill_cols = [f"BILL_AMT{i}" for i in range(1, 7)]
    pay_amt_cols = [f"PAY_AMT{i}" for i in range(1, 7)]
    pay_status_cols = ["PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]

    # -------------------------------------------------------------------------
    # A. Credit Utilization Features
    # Formula: max(0, BILL_AMT_t) / max(1, LIMIT_BAL)
    # Rationale: Higher revolving credit utilization is strongly correlated with default.
    # We clip negative bills to zero because negative balances indicate credit/refunds.
    # -------------------------------------------------------------------------
    limit_safe = np.maximum(X["LIMIT_BAL"].values, 1.0)
    util_cols = []
    for i in range(1, 7):
        col_name = f"UTIL_{i}"
        bill_positive = np.maximum(X[f"BILL_AMT{i}"].values, 0.0)
        X[col_name] = bill_positive / limit_safe
        util_cols.append(col_name)

    # Aggregated utilization across 6 months
    X["AVG_UTILIZATION"] = X[util_cols].mean(axis=1)
    X["MAX_UTILIZATION"] = X[util_cols].max(axis=1)

    # -------------------------------------------------------------------------
    # B. Payment-to-Bill Ratios
    # Formula: PAY_AMT_t / max(1, BILL_AMT_t)
    # Rationale: Measures what fraction of the billed balance was actually paid.
    # If the bill is zero or negative (no payment needed) and pay is zero, ratio = 1.0.
    # We clip the ratio to [0.0, 5.0] to prevent extreme ratio spikes from distorting linear models.
    # -------------------------------------------------------------------------
    pay_ratio_cols = []
    for i in range(1, 7):
        col_name = f"PAY_TO_BILL_{i}"
        bill_val = X[f"BILL_AMT{i}"].values
        pay_val = X[f"PAY_AMT{i}"].values

        # Where bill is zero or negative: if pay >= 0, borrower owes nothing, ratio is 1.0
        # Where bill > 0: ratio is pay / bill
        ratio = np.where(
            bill_val <= 0.0,
            np.where(pay_val > 0.0, 2.0, 1.0),
            pay_val / np.maximum(bill_val, 1.0),
        )
        X[col_name] = np.clip(ratio, 0.0, 5.0)
        pay_ratio_cols.append(col_name)

    X["AVG_PAY_TO_BILL"] = X[pay_ratio_cols].mean(axis=1)

    # -------------------------------------------------------------------------
    # C. Delinquency Dynamic Features
    # Uses: PAY_0, PAY_2, PAY_3, PAY_4, PAY_5, PAY_6
    # Note: Values > 0 denote months of payment delay (1 = 1 month delay, etc.)
    # -------------------------------------------------------------------------
    # Maximum and Average delinquency across the 6-month observation window
    X["MAX_DELINQUENCY"] = X[pay_status_cols].max(axis=1)
    X["AVG_DELINQUENCY"] = X[pay_status_cols].mean(axis=1)

    # Count of delinquent months (months where status > 0)
    X["DELINQUENT_MONTHS_COUNT"] = (X[pay_status_cols] > 0).sum(axis=1)

    # Recent delinquency indicator (September 2005 status > 0)
    # Rationale: Most recent month is the single most predictive temporal signal.
    X["RECENT_DELINQUENCY_FLAG"] = (X["PAY_0"] > 0).astype(int)

    # Delinquency trends (velocity)
    # Short-term: change between September and August (PAY_0 - PAY_2)
    # Long-term: change over the full 6 months (PAY_0 - PAY_6)
    X["DELINQUENCY_TREND_SHORT"] = X["PAY_0"] - X["PAY_2"]
    X["DELINQUENCY_TREND_LONG"] = X["PAY_0"] - X["PAY_6"]

    # -------------------------------------------------------------------------
    # D. Balance Trajectory Features
    # Rationale: Rapidly expanding balances relative to credit limit signal credit distress.
    # -------------------------------------------------------------------------
    # Absolute bill change between most recent month (Sept) and prior month (Aug)
    X["BILL_CHANGE_1_2"] = X["BILL_AMT1"] - X["BILL_AMT2"]

    # Overall 6-month bill growth normalized by credit limit
    X["BILL_GROWTH_OVER_LIMIT"] = (X["BILL_AMT1"] - X["BILL_AMT6"]) / limit_safe

    # -------------------------------------------------------------------------
    # E. Payment Consistency Features
    # Rationale: Responsible borrowers pay consistently each month.
    # -------------------------------------------------------------------------
    # Number of months (out of 6) where a non-zero payment was recorded
    X["PAYMENT_MONTHS_COUNT"] = (X[pay_amt_cols] > 0).sum(axis=1)

    # Total 6-month payments divided by total positive billed amounts
    total_payments = X[pay_amt_cols].sum(axis=1)
    total_bills = np.maximum(X[bill_cols].clip(lower=0).sum(axis=1), 1.0)
    X["TOTAL_PAY_TO_TOTAL_BILL"] = np.clip(total_payments / total_bills, 0.0, 5.0)

    # Standard deviation of payment amounts (volatility in repayment amount)
    X["PAYMENT_AMOUNT_STD"] = X[pay_amt_cols].std(axis=1)

    # -------------------------------------------------------------------------
    # F. Timely Repayment Count
    # Rationale: Counts months where the client was either current, paid in full,
    # or had zero revolving balance (status <= 0).
    # -------------------------------------------------------------------------
    X["TIMELY_PAYMENT_COUNT"] = (X[pay_status_cols] <= 0).sum(axis=1)

    if verbose:
        n_orig = len(df.columns)
        n_new = len(X.columns) - n_orig
        print(f"[Feature Engineering] Added {n_new} engineered features (total features: {len(X.columns)}).")

    return X


if __name__ == "__main__":
    from src.data_loader import load_uci_credit_card_data
    from src.preprocessing import preprocess_data

    raw = load_uci_credit_card_data(verbose=False)
    X_pre, y = preprocess_data(raw, is_training=True, verbose=False)
    X_feat = engineer_credit_features(X_pre, verbose=True)
    print("\nFeature Matrix Shape:", X_feat.shape)
    print("\nEngineered Feature Summary:")
    print(X_feat.describe().T[["mean", "std", "min", "max"]].tail(18))
