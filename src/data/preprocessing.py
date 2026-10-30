"""Leakage-safe transaction windowing helpers."""
import pandas as pd
from .validation import validate_transactions

def prepare_transactions(transactions: pd.DataFrame, as_of_date=None) -> pd.DataFrame:
    """Validate and retain only transactions strictly before the prediction date."""
    validate_transactions(transactions)
    frame = transactions.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    if as_of_date is not None:
        frame = frame.loc[frame["date"] < pd.Timestamp(as_of_date)].copy()
    return frame
