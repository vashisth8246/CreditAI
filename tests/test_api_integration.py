"""HTTP integration tests for CreditAI FastAPI adapter endpoints (/health and /v1/score)."""
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.app import app, _load_dashboard_snapshot, dashboard_snapshot


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


def test_dashboard_snapshot_loader_reads_only_expected_historical_artifacts(tmp_path):
    data_dir = tmp_path / "frontend" / "public" / "data"
    data_dir.mkdir(parents=True)
    expected = {
        "phase_9_lendingclub_summary.json": {"generated_at": "2026-10-13", "dataset": {"records": 10}},
        "phase_9_dataset_inventory.json": [{"dataset_id": "DS001"}],
        "phase_9_feature_inventory.json": [{"feature": "loan_amount"}],
    }
    for name, payload in expected.items():
        (data_dir / name).write_text(json.dumps(payload), encoding="utf-8")

    loaded = _load_dashboard_snapshot(tmp_path)
    assert loaded["summary"]["generated_at"] == "2026-10-13"
    assert loaded["summary"]["dataset"]["records"] == 10
    assert loaded["inventory"][0]["dataset_id"] == "DS001"
    assert loaded["features"][0]["feature"] == "loan_amount"


def test_dashboard_snapshot_handler_marks_payload_historical_and_uncached(monkeypatch):
    monkeypatch.setattr(
        "src.api.app._load_dashboard_snapshot",
        lambda _root: {"summary": {"generated_at": "2026-10-13"}, "inventory": [], "features": []},
    )
    iterator = dashboard_snapshot().__await__()
    with pytest.raises(StopIteration) as completion:
        next(iterator)
    response = completion.value.value
    payload = json.loads(response.body)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert payload["source"] == "historical_research_snapshot"
    assert payload["source_snapshot_date"] == "2026-10-13"
    assert payload["retrieved_at"]


def test_dashboard_frontend_backend_snapshot_contract_and_assets():
    """Check the route contract, exact source files and real loaded dataset identity."""
    repository = Path(__file__).resolve().parents[1]
    api_source = (repository / "frontend" / "src" / "api.ts").read_text(encoding="utf-8")
    backend_source = (repository / "src" / "api" / "app.py").read_text(encoding="utf-8")
    required_files = (
        "phase_9_lendingclub_summary.json",
        "phase_9_dataset_inventory.json",
        "phase_9_feature_inventory.json",
    )

    assert "request<T>('/v1/dashboard/snapshot'" in api_source
    assert '@app.get("/v1/dashboard/snapshot")' in backend_source
    for filename in required_files:
        artifact = repository / "frontend" / "public" / "data" / filename
        assert artifact.is_file(), f"Required dashboard artifact is missing: {artifact}"
        assert json.loads(artifact.read_text(encoding="utf-8")), f"Dashboard artifact is empty: {artifact}"

    route = next(route for route in app.routes if route.path == "/v1/dashboard/snapshot")
    assert route.endpoint is dashboard_snapshot
    payload = _load_dashboard_snapshot(repository)
    assert payload["summary"]["dataset"]["id"] == "DS001"
    assert payload["summary"]["dataset"]["name"] == "LendingClub accepted loans"
    assert payload["inventory"]
    assert payload["features"]
    datetime.strptime(payload["summary"]["generated_at"], "%Y-%m-%d")


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows TestClient stalls on localhost requests; verify the live HTTP route separately.",
)
def test_dashboard_snapshot_http_returns_committed_artifacts_with_provenance():
    response = client.get("/v1/dashboard/snapshot")
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "historical_research_snapshot"
    assert payload["source_snapshot_date"] == payload["summary"]["generated_at"]
    assert payload["summary"]["dataset"]["id"] == "DS001"
    assert payload["inventory"]
    assert payload["features"]
    assert response.headers["cache-control"] == "no-store"
    datetime.fromisoformat(payload["retrieved_at"].replace("Z", "+00:00"))


def test_dashboard_loader_does_not_substitute_phase6_or_taiwan_assets(tmp_path):
    """Missing Phase 9 evidence must fail explicitly instead of using unrelated JSON."""
    data_dir = tmp_path / "frontend" / "public" / "data"
    data_dir.mkdir(parents=True)
    unrelated = {
        "phase_6_1_lendingclub_summary.json": {"generated_at": "unrelated"},
        "phase_6_1_dataset_inventory.json": [{"dataset_id": "unrelated"}],
        "uci_taiwan_eval.json": {"metadata": {"dataset_id": "DS003"}},
    }
    for filename, payload in unrelated.items():
        (data_dir / filename).write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="Historical dashboard artifacts are unavailable"):
        _load_dashboard_snapshot(tmp_path)


def test_dashboard_endpoint_reports_missing_artifacts_as_explicit_service_error(monkeypatch):
    def missing(_root):
        raise ValueError("Historical dashboard artifacts are unavailable on this server.")

    monkeypatch.setattr("src.api.app._load_dashboard_snapshot", missing)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as error:
        next(dashboard_snapshot().__await__())
    assert error.value.status_code == 503
    assert "Historical dashboard artifacts are unavailable" in error.value.detail


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
