"""AC-3 research-only record provenance, confirmation and simulation tests."""

from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from src.agentic_commerce import research_data
from src.agentic_commerce import runtime
from src.agentic_commerce.research_data import RECORD_COLUMNS, TARGET_COLUMN
from src.agentic_commerce.runtime import _event, confirm_simulation, create_session, get_session
from src.agentic_commerce.schemas import (
    AC3CreateSessionRequest,
    AC3SimulationConfirmation,
    CommerceWorkflowState,
)
from src.api.agentic_commerce import (
    commerce_session,
    confirm_commerce_simulation,
    create_commerce_session,
    research_data_status,
    research_records,
)
from src.api.app import app


def request_payload(session_id: str = "ac3-test-session-1001") -> dict:
    return {
        "intent": {
            "session_id": session_id,
            "product_name": "User-entered item",
            "product_category": "user-entered category",
            "product_price": "100000.00",
            "down_payment": "20000.00",
            "requested_tenure_months": 12,
            "monthly_income": "80000.00",
            "existing_monthly_obligations": "12000.00",
            "currency": "INR",
        },
        "annual_rate_scenarios_percent": ["8", "12"],
    }


def test_ac3_routes_are_registered_and_contracts_are_research_safe():
    paths = app.openapi()["paths"]
    assert "/v1/agentic-commerce/research-data" in paths
    assert "/v1/agentic-commerce/research-records" in paths
    assert "/v1/agentic-commerce/sessions" in paths
    assert "/v1/agentic-commerce/sessions/{session_id}" in paths
    assert "/v1/agentic-commerce/sessions/{session_id}/confirm" in paths
    with pytest.raises(ValidationError):
        AC3SimulationConfirmation.model_validate({"option_id": "scenario-1"})


def test_missing_dataset_reports_unavailable_without_fallback(monkeypatch, tmp_path):
    absent = tmp_path / "not-installed.xls"
    monkeypatch.setattr(research_data, "dataset_candidates", lambda: [absent])
    research_data._verified_frame.cache_clear()
    try:
        status = research_data_status()
        records = research_records()
        assert status.status == "unavailable"
        assert status.sha256 == research_data.EXPECTED_SHA256
        assert status.target_excluded_from_record is True
        assert "Research dataset unavailable" in status.message
        assert records.status == "unavailable"
        assert records.records == []
    finally:
        research_data._verified_frame.cache_clear()


def test_record_projection_excludes_target_and_marks_research_provenance():
    row = {column: 0 for column in RECORD_COLUMNS}
    row.update({"ID": 125, "LIMIT_BAL": 50000, "AGE": 34, "PAY_0": 1, "BILL_AMT1": 3000, "PAY_AMT1": 500})
    row[TARGET_COLUMN] = 1
    frame = pd.DataFrame([row])
    record = research_data._record_from_frame(frame, 1)
    payload = record.model_dump()
    assert record.reference == "UCI-TW-00125"
    assert record.credit_limit_twd == 50000
    assert record.age_years == 34
    assert len(record.features) == 23
    assert record.features["SEX"] == 0
    assert record.features["PAY_AMT6"] == 0
    assert record.model_inference_performed is False
    assert record.target_included is False
    assert TARGET_COLUMN not in payload
    assert "default" not in " ".join(payload).lower()


def test_manual_profile_is_inferred_by_the_research_model_and_recorded_separately(monkeypatch):
    profile = {
        "LIMIT_BAL": 200000, "SEX": 2, "EDUCATION": 2, "MARRIAGE": 1, "AGE": 35,
        "PAY_0": 0, "PAY_2": 0, "PAY_3": 0, "PAY_4": 0, "PAY_5": 0, "PAY_6": 0,
        "BILL_AMT1": 50000, "BILL_AMT2": 45000, "BILL_AMT3": 40000,
        "BILL_AMT4": 35000, "BILL_AMT5": 30000, "BILL_AMT6": 25000,
        "PAY_AMT1": 5000, "PAY_AMT2": 5000, "PAY_AMT3": 5000,
        "PAY_AMT4": 5000, "PAY_AMT5": 5000, "PAY_AMT6": 5000,
    }
    calls = []

    def fake_predict(model_id, features, include_explanations):
        calls.append((model_id, features, include_explanations))
        return SimpleNamespace(
            model_id=model_id, probability=0.25, predicted_class="Lower predicted default risk",
            calibrated=True, limitations=["Taiwan 2005 research data", "Not validated for Indian borrowers"],
        )

    monkeypatch.setattr(runtime, "predict", fake_predict)
    payload = request_payload("ac3-manual-profile-research-0001")
    payload["research_profile"] = profile
    created = create_session(AC3CreateSessionRequest.model_validate(payload))

    assert calls == [("uci_taiwan_xgb", profile, False)]
    assert created.research_output is not None
    assert created.research_output.probability == 0.25
    assert created.research_output.interpretation == "research_only_not_validated_for_indian_borrowers"
    assert created.provenance.model_inference == "uci_taiwan_research_model"
    assert created.audit_events[1].event_type == CommerceWorkflowState.AFFORDABILITY_RESEARCH
    assert "financing calculations" in created.audit_events[1].summary
    assert created.comparison.model_validation_status == "not_validated"


def test_session_requires_explicit_confirmation_then_records_simulation_and_audit():
    request = AC3CreateSessionRequest.model_validate(request_payload())
    session = create_commerce_session(request)
    assert session.status == "awaiting_confirmation"
    assert session.transaction is None
    assert session.human_confirmation_required is True
    assert session.real_lending_enabled is False
    assert session.real_transactions_enabled is False
    assert session.model_validation_status == "not_validated"
    assert session.provenance.purchase_context == "user_input"
    assert session.provenance.monthly_income == "user_input"
    assert session.provenance.financing_rates == "simulated_parameter"
    assert session.provenance.payment_estimates == "deterministic_calculation"
    assert session.provenance.preferred_option == "deterministic_comparison"
    assert session.provenance.model_inference == "not_used"
    assert session.provenance.ground_truth_target == "excluded"
    assert [event.event_type.value for event in session.audit_events] == [
        "PURCHASE_INTENT_RECEIVED", "OFFER_DISCOVERY", "OFFER_COMPARISON", "RECOMMENDATION_READY",
    ]

    selected = session.comparison.options[0]
    confirmation = AC3SimulationConfirmation(decision="confirm_simulation", option_id=selected.option_id)
    completed = confirm_commerce_simulation(session.session_id, confirmation)
    transaction = completed.transaction
    assert completed.status == "simulation_completed"
    assert transaction is not None
    assert transaction.confirmation_status == "confirmed"
    assert transaction.execution_status == "simulation_completed"
    assert transaction.simulation_status == "research_transaction_simulated"
    assert transaction.real_transaction_executed is False
    assert transaction.monthly_payment == selected.estimated_monthly_payment
    assert transaction.total_estimated_repayment == selected.estimated_total_payment
    assert transaction.total_estimated_repayment == Decimal("12") * transaction.monthly_payment
    assert transaction.audit_reference == completed.audit_events[-1].event_id
    assert completed.audit_events[-1].event_type.value == "SIMULATED_TRANSACTION_COMPLETE"
    assert "no external transaction was executed" in completed.audit_events[-1].summary


def test_duplicate_confirmation_is_idempotent_and_cannot_change_option():
    session = create_session(AC3CreateSessionRequest.model_validate(request_payload("ac3-test-session-1002")))
    option = session.comparison.options[0]
    confirmation = AC3SimulationConfirmation(decision="confirm_simulation", option_id=option.option_id)
    first = confirm_simulation(session.session_id, confirmation)
    assert first is not None and first.transaction is not None
    replay = confirm_simulation(session.session_id, confirmation)
    assert replay is not None and replay.transaction is not None
    assert replay.idempotent_replay is True
    assert replay.transaction.simulation_id == first.transaction.simulation_id
    assert len(replay.audit_events) == len(first.audit_events)

    other_option = session.comparison.options[1]
    with pytest.raises(ValueError, match="already confirmed with a different option"):
        confirm_simulation(session.session_id, AC3SimulationConfirmation(
            decision="confirm_simulation", option_id=other_option.option_id,
        ))


def test_invalid_option_and_unknown_session_do_not_create_transaction():
    session = create_session(AC3CreateSessionRequest.model_validate(request_payload("ac3-test-session-1003")))
    with pytest.raises(LookupError, match="does not belong"):
        confirm_simulation(session.session_id, AC3SimulationConfirmation(
            decision="confirm_simulation", option_id="foreign-option",
        ))
    assert get_session(session.session_id).transaction is None
    assert confirm_simulation("missing-ac3-session", AC3SimulationConfirmation(
        decision="confirm_simulation", option_id="scenario-1",
    )) is None


def test_duplicate_session_is_rejected_without_overwriting_original():
    request = AC3CreateSessionRequest.model_validate(request_payload("ac3-test-session-1004"))
    original = create_session(request)
    with pytest.raises(ValueError, match="already exists"):
        create_session(request)
    assert get_session(original.session_id) == original
    with pytest.raises(HTTPException) as missing:
        commerce_session("session-that-does-not-exist")
    assert missing.value.status_code == 404


def test_audit_event_identity_is_stable_without_random_identifiers():
    first = _event("stable-session", CommerceWorkflowState.PURCHASE_INTENT_RECEIVED,
                   "human", "User-entered purchase context received.", {"purchase_context": "user_input"})
    second = _event("stable-session", CommerceWorkflowState.PURCHASE_INTENT_RECEIVED,
                    "human", "User-entered purchase context received.", {"purchase_context": "user_input"})
    assert first.event_id == second.event_id
