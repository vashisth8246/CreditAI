"""Validation for transaction-level input data."""
from __future__ import annotations
import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ["borrower_id", "transaction_id", "date", "transaction_type", "amount", "category", "counterparty", "balance_after_transaction"]
ALLOWED_TYPES = {"CREDIT", "DEBIT"}

def validate_transactions(transactions: pd.DataFrame, *, strict: bool = True) -> dict:
    """Return a quality report; strict mode raises on structural/critical errors."""
    missing = [c for c in REQUIRED_COLUMNS if c not in transactions.columns]
    errors = []
    if missing:
        errors.append(f"Missing required columns: {missing}")
    if errors and strict:
        raise ValueError("; ".join(errors))
    if errors:
        return {"valid": False, "errors": errors}
    dates = pd.to_datetime(transactions["date"], errors="coerce")
    invalid_types = ~transactions["transaction_type"].isin(ALLOWED_TYPES)
    numeric_amount=pd.to_numeric(transactions["amount"],errors="coerce")
    numeric_balance=pd.to_numeric(transactions["balance_after_transaction"],errors="coerce")
    invalid_amount=numeric_amount.isna() | ~np.isfinite(numeric_amount)
    invalid_balance=numeric_balance.isna() | ~np.isfinite(numeric_balance)
    negative = numeric_amount < 0
    duplicate_ids = transactions["transaction_id"].duplicated(keep=False)
    missing_ids = transactions["borrower_id"].isna() | transactions["transaction_id"].isna()
    impossible_balance = numeric_balance < 0
    missing_categories = transactions["category"].isna()
    report = {"valid": not (invalid_types.any() or negative.any() or invalid_amount.any() or invalid_balance.any() or missing_ids.any() or dates.isna().any() or duplicate_ids.any() or impossible_balance.any() or missing_categories.any()),
              "rows": int(len(transactions)), "missing_borrower_or_transaction_id": int(missing_ids.sum()),
              "duplicate_transaction_ids": int(duplicate_ids.sum()), "invalid_dates": int(dates.isna().sum()),
              "negative_amounts": int(negative.sum()), "invalid_amounts": int(invalid_amount.sum()), "invalid_transaction_types": int(invalid_types.sum()),
              "impossible_negative_balances": int(impossible_balance.sum()),
              "missing_categories": int(missing_categories.sum()),
              "duplicate_records": int(transactions.duplicated().sum()),
              "extreme_amounts_over_99_9_percentile": int((numeric_amount > numeric_amount.quantile(.999)).sum())}
    if strict and not report["valid"]:
        raise ValueError(f"Invalid transaction data: {report}")
    return report
