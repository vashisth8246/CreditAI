from datetime import datetime
import math

import pytest

from src.api.contract import ContractError, not_validated_response, validate_request


def valid_payload():
    return {
        "schema_version": "1.0",
        "observation_start": "2025-01-01",
        "prediction_date": "2025-02-01",
        "transactions": [{"transaction_id": "t-1", "date": "2025-01-10", "transaction_type": "credit", "amount": 1000}],
    }


def test_request_accepts_explicit_window_and_transaction():
    assert validate_request(valid_payload())["schema_version"] == "1.0"


def test_missing_observation_window_is_rejected():
    payload = valid_payload()
    del payload["observation_start"]
    with pytest.raises(ContractError, match="Required request fields"):
        validate_request(payload)


def test_post_cutoff_transaction_is_rejected():
    payload = valid_payload()
    payload["transactions"][0]["date"] = "2025-02-01"
    with pytest.raises(ContractError, match="observation window"):
        validate_request(payload)


def test_unvalidated_response_cannot_look_like_a_probability():
    response = not_validated_response("opaque-123")
    assert response["score_status"] == "not_validated"
    assert response["default_probability"] is None
    assert response["validated_risk_estimate"] is False
    assert response["model_version"] is None
    assert response["provenance"] == {"source": "no_validated_model", "synthetic_demo": False}
    assert response["request_id"] == "opaque-123"


def test_duplicate_transaction_ids_are_rejected():
    payload = valid_payload()
    payload["transactions"].append(dict(payload["transactions"][0]))
    with pytest.raises(ContractError, match="unique"):
        validate_request(payload)


def test_strict_date_format_enforced():
    payload = valid_payload()
    payload["observation_start"] = "2025-1-1"
    with pytest.raises(ContractError, match="exact YYYY-MM-DD format"):
        validate_request(payload)

    payload2 = valid_payload()
    payload2["transactions"][0]["date"] = "2025/01/10"
    with pytest.raises(ContractError, match="exact YYYY-MM-DD format"):
        validate_request(payload2)


def test_empty_transactions_rejected():
    payload = valid_payload()
    payload["transactions"] = []
    with pytest.raises(ContractError, match="must contain at least one transaction"):
        validate_request(payload)


def test_unknown_fields_rejected():
    payload = valid_payload()
    payload["extra_top_level"] = "forbidden"
    with pytest.raises(ContractError, match="Unknown request field"):
        validate_request(payload)

    payload2 = valid_payload()
    payload2["transactions"][0]["extra_tx_field"] = "forbidden"
    with pytest.raises(ContractError, match="Unknown transaction field"):
        validate_request(payload2)


def test_invalid_amounts_rejected():
    for bad_amount in [0, -100, float("nan"), float("inf"), True, False]:
        payload = valid_payload()
        payload["transactions"][0]["amount"] = bad_amount
        with pytest.raises(ContractError, match="amount"):
            validate_request(payload)

