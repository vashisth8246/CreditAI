"""AC-1 contract, safety and endpoint tests; no commerce tool execution."""

import asyncio
import sys
from decimal import Decimal

import httpx
import pytest
from pydantic import ValidationError

from src.agentic_commerce.schemas import (
    AgenticCommerceStatus,
    CommerceComparisonRequest,
    CommerceWorkflowState,
    HumanConfirmation,
    PurchaseIntent,
    Recommendation,
)
from src.agentic_commerce.workflow import ALLOWED_STATE_TRANSITIONS, WORKFLOW_STAGES
from src.agentic_commerce.comparison import compare_purchase, monthly_payment
from src.api.agentic_commerce import agentic_commerce_status, agentic_commerce_workflow, compare_financing_scenarios
from src.api.app import ScoreRequest, app, score


def valid_intent_payload() -> dict:
    return {
        "session_id": "session-demo-001",
        "product_name": "Synthetic laptop example",
        "product_category": "electronics",
        "product_price": "50000.00",
        "down_payment": "10000.00",
        "requested_tenure_months": 12,
        "monthly_income": "80000.00",
        "existing_monthly_obligations": "12000.00",
        "currency": "INR",
    }


@pytest.mark.skipif(sys.platform == "win32", reason="Windows TestClient/ASGI HTTP requests stall in this workspace; GitHub Linux CI exercises these routes.")
def test_status_and_workflow_endpoints_are_truthful_foundation_only():
    async def request_endpoints():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://creditai.test") as client:
            status_response = await client.get("/v1/agentic-commerce/status")
            workflow_response = await client.get("/v1/agentic-commerce/workflow")
        return status_response, workflow_response

    status_response, workflow_response = asyncio.run(request_endpoints())
    assert status_response.status_code == 200
    assert status_response.json() == AgenticCommerceStatus().model_dump(mode="json")
    assert status_response.json()["status"] == "foundation_ready"
    assert status_response.json()["workflow_execution_enabled"] is False
    assert status_response.json()["real_transactions_enabled"] is False
    assert status_response.json()["real_lending_enabled"] is False
    assert status_response.json()["human_confirmation_required"] is True
    assert workflow_response.status_code == 200
    stages = workflow_response.json()
    assert len(stages) == 8
    assert [stage["order"] for stage in stages] == list(range(1, 9))
    assert {stage["status"] for stage in stages} == {"planned"}


def test_status_and_workflow_routes_are_registered_and_return_foundation_contracts():
    paths = app.openapi()["paths"]
    assert "/v1/agentic-commerce/status" in paths
    assert "/v1/agentic-commerce/workflow" in paths
    assert agentic_commerce_status().model_dump()["status"] == "foundation_ready"
    stages = agentic_commerce_workflow()
    assert len(stages) == 8
    assert all(stage.status == "planned" for stage in stages)


def test_purchase_intent_accepts_valid_decimal_financial_values():
    intent = PurchaseIntent.model_validate(valid_intent_payload())
    assert intent.product_price == Decimal("50000.00")
    assert intent.currency == "INR"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("product_price", "-1.00"),
        ("product_price", "0.00"),
        ("down_payment", "-0.01"),
        ("requested_tenure_months", 0),
        ("monthly_income", "-1.00"),
        ("existing_monthly_obligations", "-1.00"),
    ],
)
def test_purchase_intent_rejects_invalid_amounts_and_tenure(field, value):
    payload = valid_intent_payload()
    payload[field] = value
    with pytest.raises(ValidationError):
        PurchaseIntent.model_validate(payload)


def test_purchase_intent_rejects_down_payment_above_product_price():
    payload = valid_intent_payload()
    payload["down_payment"] = "50000.01"
    with pytest.raises(ValidationError, match="down_payment must not exceed product_price"):
        PurchaseIntent.model_validate(payload)


def test_contracts_forbid_unnecessary_pii_and_unsafe_decisions():
    payload = valid_intent_payload()
    payload["borrower_name"] = "not-collected"
    with pytest.raises(ValidationError):
        PurchaseIntent.model_validate(payload)
    with pytest.raises(ValidationError):
        Recommendation(explanation="demo only", requires_human_confirmation=False)
    with pytest.raises(ValidationError):
        AgenticCommerceStatus(real_transactions_enabled=True)


def test_human_confirmation_is_explicit_and_state_graph_gates_simulation():
    confirmation = HumanConfirmation(
        session_id="session-demo-001",
        option_id="demo-option-1",
        decision="confirm_simulation",
        timestamp="2026-11-02T10:00:00Z",
    )
    assert confirmation.decision == "confirm_simulation"
    assert CommerceWorkflowState.SIMULATION_CONFIRMED in ALLOWED_STATE_TRANSITIONS[
        CommerceWorkflowState.AWAITING_HUMAN_CONFIRMATION
    ]
    assert CommerceWorkflowState.AWAITING_HUMAN_CONFIRMATION in ALLOWED_STATE_TRANSITIONS[
        CommerceWorkflowState.RECOMMENDATION_READY
    ]
    assert CommerceWorkflowState.SIMULATION_CONFIRMED not in ALLOWED_STATE_TRANSITIONS[
        CommerceWorkflowState.RECOMMENDATION_READY
    ]
    assert len(WORKFLOW_STAGES) == 8


def test_score_endpoint_remains_safety_locked_with_valid_dummy_request():
    payload = {
        "schema_version": "1.0",
        "observation_start": "2025-01-01",
        "prediction_date": "2025-02-01",
        "request_id": "ac1-safety-check",
        "transactions": [
            {
                "transaction_id": "synthetic-income-1",
                "date": "2025-01-15",
                "transaction_type": "credit",
                "amount": 50000.0,
                "category": "synthetic_salary",
            }
        ],
    }

    request = ScoreRequest.model_validate(payload)
    coroutine = score(request).__await__()
    with pytest.raises(StopIteration) as completion:
        next(coroutine)
    response = completion.value.value
    assert response["score_status"] == "not_validated"
    assert response["default_probability"] is None
    assert response["validated_risk_estimate"] is False


def comparison_payload() -> dict:
    return {
        "intent": valid_intent_payload(),
        "annual_rate_scenarios_percent": ["12", "0", "8"],
    }


def test_monthly_payment_handles_zero_rate_and_reducing_balance():
    assert monthly_payment(Decimal("1200"), Decimal("0"), 12) == Decimal("100.00")
    assert monthly_payment(Decimal("1200"), Decimal("12"), 12) == Decimal("106.62")
    assert monthly_payment(Decimal("0"), Decimal("12"), 12) == Decimal("0.00")


def test_comparison_is_deterministic_and_selects_lowest_total_interest():
    request = CommerceComparisonRequest.model_validate(comparison_payload())
    first = compare_purchase(request)
    second = compare_purchase(request)
    assert first == second
    assert first.status == "research_simulation"
    assert len(first.options) == 3
    assert [option.annual_rate_percent for option in first.options] == [Decimal("0"), Decimal("8"), Decimal("12")]
    assert first.preferred_option_id == "scenario-1"
    assert first.options[0].estimated_monthly_payment == Decimal("3333.33")
    assert first.options[0].payment_to_income_ratio == Decimal("0.041667")
    assert first.options[0].estimated_remaining_income_after_obligations == Decimal("64666.67")
    assert first.human_confirmation_required is True
    assert first.real_lending_enabled is False
    assert first.real_transactions_enabled is False
    assert "not an affordability assessment" in first.recommendation_explanation
    assert "not a lender offer" in first.options[0].research_notes
    assert "no transaction or audit event was persisted" in first.event_summary
    assert all(option.estimated_total_interest >= 0 for option in first.options)


@pytest.mark.parametrize("rates", [[], ["5"], ["5", "5"], ["-1", "5"], ["5", "101"], ["NaN", "5"], ["Infinity", "5"]])
def test_comparison_rejects_incomplete_or_invalid_rate_scenarios(rates):
    payload = comparison_payload()
    payload["annual_rate_scenarios_percent"] = rates
    with pytest.raises(ValidationError):
        CommerceComparisonRequest.model_validate(payload)


def test_comparison_endpoint_is_registered_and_has_typed_contract():
    assert "/v1/agentic-commerce/compare" in app.openapi()["paths"]
    response = compare_financing_scenarios(CommerceComparisonRequest.model_validate(comparison_payload()))
    assert response.model_dump(mode="json")["phase"] == "AC-2"


@pytest.mark.skipif(sys.platform == "win32", reason="HTTP loopback/ASGI request tests are exercised by GitHub Linux CI in this workspace.")
def test_comparison_http_endpoint_validates_and_returns_research_simulation():
    async def request_endpoint():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://creditai.test") as client:
            valid = await client.post("/v1/agentic-commerce/compare", json=comparison_payload())
            invalid_payload = comparison_payload()
            invalid_payload["intent"]["down_payment"] = "60000"
            invalid = await client.post("/v1/agentic-commerce/compare", json=invalid_payload)
        return valid, invalid

    valid, invalid = asyncio.run(request_endpoint())
    assert valid.status_code == 200
    assert valid.json()["status"] == "research_simulation"
    assert valid.json()["human_confirmation_required"] is True
    assert invalid.status_code == 422
