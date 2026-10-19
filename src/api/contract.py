"""Framework-independent request validation and safe scoring response."""
from __future__ import annotations

from datetime import date, datetime, timezone
import re
from math import isfinite
from typing import Any

DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ContractError(ValueError):
    def __init__(self, code: str, message: str, field: str | None = None):
        super().__init__(message)
        self.code, self.message, self.field = code, message, field


def _parse_strict_date(val: Any, field_name: str | None = None) -> date:
    if not isinstance(val, str) or not DATE_REGEX.match(val):
        raise ContractError("invalid_date", "Dates must use exact YYYY-MM-DD format.", field_name)
    try:
        return datetime.strptime(val, "%Y-%m-%d").date()
    except ValueError:
        raise ContractError("invalid_date", "Dates must use exact YYYY-MM-DD format.", field_name)


ALLOWED_REQUEST_FIELDS = {"schema_version", "observation_start", "prediction_date", "transactions", "request_id"}
ALLOWED_TX_FIELDS = {"transaction_id", "date", "transaction_type", "amount", "category", "counterparty", "balance_after_transaction"}


def validate_request(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ContractError("invalid_request", "Request body must be an object.")

    extra_request_fields = sorted(set(data.keys()) - ALLOWED_REQUEST_FIELDS)
    if extra_request_fields:
        raise ContractError("unknown_field", "Unknown request field is forbidden.", extra_request_fields[0])

    required = {"schema_version", "observation_start", "prediction_date", "transactions"}
    missing = sorted(required - data.keys())
    if missing:
        raise ContractError("missing_field", "Required request fields are missing.", missing[0])

    if not isinstance(data["schema_version"], str) or data["schema_version"] != "1.0":
        raise ContractError("unsupported_schema_version", "schema_version must be '1.0'.", "schema_version")

    if data.get("request_id") is not None and not isinstance(data["request_id"], str):
        raise ContractError("invalid_type", "request_id must be a string or null.", "request_id")

    start = _parse_strict_date(data["observation_start"], "observation_start")
    cutoff = _parse_strict_date(data["prediction_date"], "prediction_date")

    if start >= cutoff:
        raise ContractError("invalid_observation_window", "observation_start must precede prediction_date.")

    txs = data["transactions"]
    if not isinstance(txs, list):
        raise ContractError("invalid_type", "transactions must be an array.", "transactions")

    if len(txs) == 0:
        raise ContractError("empty_transactions", "transactions array must contain at least one transaction.", "transactions")

    seen: set[str] = set()
    allowed_types = {"credit", "debit"}

    for index, tx in enumerate(txs):
        field = f"transactions[{index}]"
        if not isinstance(tx, dict):
            raise ContractError("invalid_type", "Each transaction must be an object.", field)

        extra_tx_fields = sorted(set(tx.keys()) - ALLOWED_TX_FIELDS)
        if extra_tx_fields:
            raise ContractError("unknown_field", "Unknown transaction field is forbidden.", f"{field}.{extra_tx_fields[0]}")

        for key in ("transaction_id", "date", "transaction_type", "amount"):
            if key not in tx:
                raise ContractError("missing_field", "A required transaction field is missing.", f"{field}.{key}")

        txid = tx["transaction_id"]
        if not isinstance(txid, str) or not txid.strip() or txid in seen:
            raise ContractError("invalid_transaction_id", "Transaction IDs must be non-empty and unique.", f"{field}.transaction_id")
        seen.add(txid)

        txdate = _parse_strict_date(tx["date"], f"{field}.date")
        if txdate < start or txdate >= cutoff:
            raise ContractError("transaction_outside_window", "Transactions must fall within the observation window, before prediction_date.", f"{field}.date")

        if not isinstance(tx["transaction_type"], str) or tx["transaction_type"] not in allowed_types:
            raise ContractError("invalid_transaction_type", "transaction_type must be 'credit' or 'debit'.", f"{field}.transaction_type")

        amount = tx["amount"]
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not isfinite(amount) or amount <= 0:
            raise ContractError("invalid_amount", "amount must be a finite number greater than zero.", f"{field}.amount")

        for optional in ("category", "counterparty"):
            if optional in tx and tx[optional] is not None and not isinstance(tx[optional], str):
                raise ContractError("invalid_type", f"{optional} must be a string or null.", f"{field}.{optional}")

        if "balance_after_transaction" in tx and tx["balance_after_transaction"] is not None:
            bal = tx["balance_after_transaction"]
            if isinstance(bal, bool) or not isinstance(bal, (int, float)) or not isfinite(bal):
                raise ContractError("invalid_balance", "balance_after_transaction must be finite or null.", f"{field}.balance_after_transaction")

    return data


def not_validated_response(request_id: str | None = None) -> dict[str, Any]:
    """Never synthesize a PD; no validated CreditAI model is currently registered."""
    return {
        "score_status": "not_validated",
        "score_type": "none",
        "default_probability": None,
        "validated_risk_estimate": False,
        "model_version": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provenance": {"source": "no_validated_model", "synthetic_demo": False},
        "request_id": request_id,
        "message": "No validated CreditAI model is available; no risk score was produced.",
    }

