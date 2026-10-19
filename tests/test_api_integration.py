"""HTTP integration tests for CreditAI FastAPI adapter endpoints (/health and /v1/score)."""
import json
from fastapi.testclient import TestClient
import pytest

from src.api.app import app


client = TestClient(app)


def valid_payload():
    return {
        "schema_version": "1.0",
        "observation_start": "2025-01-01",
        "prediction_date": "2025-02-01",
        "request_id": "integration-req-001",
        "transactions": [
            {
                "transaction_id": "txn-101",
                "date": "2025-01-15",
                "transaction_type": "credit",
                "amount": 50000.0,
                "category": "salary",
                "counterparty": "Employer Corp",
                "balance_after_transaction": 75000.0,
            }
        ],
    }


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok", "scoring": "not_validated"}


def test_valid_score_endpoint_returns_not_validated():
    response = client.post("/v1/score", json=valid_payload())
    assert response.status_code == 200
    data = response.json()
    assert data["score_status"] == "not_validated"
    assert data["score_type"] == "none"
    assert data["default_probability"] is None
    assert data["validated_risk_estimate"] is False
    assert data["model_version"] is None
    assert data["request_id"] == "integration-req-001"
    assert data["provenance"] == {"source": "no_validated_model", "synthetic_demo": False}


def test_unsupported_schema_version_rejected():
    payload = valid_payload()
    payload["schema_version"] = "2.0"
    response = client.post("/v1/score", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] in ("unsupported_schema_version", "invalid_request")


def test_missing_fields_rejected():
    for req_field in ["schema_version", "observation_start", "prediction_date", "transactions"]:
        payload = valid_payload()
        del payload[req_field]
        response = client.post("/v1/score", json=payload)
        assert response.status_code == 422
        data = response.json()
        assert "error" in data


def test_duplicate_transaction_ids_rejected():
    payload = valid_payload()
    payload["transactions"].append(
        {
            "transaction_id": "txn-101",  # Duplicate ID
            "date": "2025-01-20",
            "transaction_type": "debit",
            "amount": 100.0,
        }
    )
    response = client.post("/v1/score", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "invalid_transaction_id"


def test_invalid_transaction_date_formats_and_windows():
    # Invalid date format
    payload1 = valid_payload()
    payload1["transactions"][0]["date"] = "2025/01/15"
    res1 = client.post("/v1/score", json=payload1)
    assert res1.status_code == 422

    # Date on or after prediction_date cutoff
    payload2 = valid_payload()
    payload2["transactions"][0]["date"] = "2025-02-01"
    res2 = client.post("/v1/score", json=payload2)
    assert res2.status_code == 422

    # Date before observation_start
    payload3 = valid_payload()
    payload3["transactions"][0]["date"] = "2024-12-31"
    res3 = client.post("/v1/score", json=payload3)
    assert res3.status_code == 422


def test_zero_negative_nonfinite_invalid_amounts():
    bad_amounts = [0, -500.0, True, False, "5000"]
    for amt in bad_amounts:
        payload = valid_payload()
        payload["transactions"][0]["amount"] = amt
        res = client.post("/v1/score", json=payload)
        assert res.status_code == 422


def test_unknown_top_level_and_transaction_fields_rejected():
    # Unknown top-level field
    payload1 = valid_payload()
    payload1["unexpected_field"] = "secret_value_123"
    res1 = client.post("/v1/score", json=payload1)
    assert res1.status_code == 422
    assert "secret_value_123" not in res1.text

    # Unknown transaction field
    payload2 = valid_payload()
    payload2["transactions"][0]["secret_tx_prop"] = "sensitive_data"
    res2 = client.post("/v1/score", json=payload2)
    assert res2.status_code == 422
    assert "sensitive_data" not in res2.text


def test_empty_transactions_rejected():
    payload = valid_payload()
    payload["transactions"] = []
    res = client.post("/v1/score", json=payload)
    assert res.status_code == 422
    data = res.json()
    assert "error" in data


def test_error_responses_do_not_echo_submitted_transaction_values():
    sensitive_id = "SECRET_TXN_ID_9999"
    sensitive_counterparty = "CONFIDENTIAL_VENDOR_XYZ"
    payload = valid_payload()
    payload["transactions"][0]["transaction_id"] = sensitive_id
    payload["transactions"][0]["counterparty"] = sensitive_counterparty
    payload["transactions"][0]["amount"] = -99999.0  # Cause validation failure

    res = client.post("/v1/score", json=payload)
    assert res.status_code == 422
    assert sensitive_id not in res.text
    assert sensitive_counterparty not in res.text


def test_malformed_json_handling():
    res = client.post("/v1/score", content="{malformed_json: true,", headers={"Content-Type": "application/json"})
    assert res.status_code in (400, 422)
    assert "error" in res.json()
