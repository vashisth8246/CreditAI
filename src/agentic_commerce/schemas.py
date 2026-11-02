"""Typed, non-PII contracts for the future Agentic Commerce workflow.

These schemas describe inputs and outputs only. AC-1 registers no tools and
does not execute affordability, lender discovery, recommendations, or trades.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CommerceWorkflowState(str, Enum):
    PURCHASE_INTENT_RECEIVED = "PURCHASE_INTENT_RECEIVED"
    AFFORDABILITY_RESEARCH = "AFFORDABILITY_RESEARCH"
    RISK_RESEARCH = "RISK_RESEARCH"
    OFFER_DISCOVERY = "OFFER_DISCOVERY"
    OFFER_COMPARISON = "OFFER_COMPARISON"
    RECOMMENDATION_READY = "RECOMMENDATION_READY"
    AWAITING_HUMAN_CONFIRMATION = "AWAITING_HUMAN_CONFIRMATION"
    SIMULATION_CONFIRMED = "SIMULATION_CONFIRMED"
    SIMULATION_REJECTED = "SIMULATION_REJECTED"
    SIMULATED_TRANSACTION_COMPLETE = "SIMULATED_TRANSACTION_COMPLETE"
    FAILED = "FAILED"


class PurchaseIntent(ContractModel):
    """Minimum transaction context; excludes names and borrower identifiers."""

    session_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._:-]+$")
    product_name: str = Field(min_length=1, max_length=160)
    product_category: str = Field(min_length=1, max_length=80)
    product_price: Decimal = Field(gt=Decimal("0"), max_digits=14, decimal_places=2)
    down_payment: Decimal = Field(ge=Decimal("0"), max_digits=14, decimal_places=2)
    requested_tenure_months: int = Field(gt=0, le=600)
    monthly_income: Decimal = Field(ge=Decimal("0"), max_digits=14, decimal_places=2)
    existing_monthly_obligations: Decimal = Field(ge=Decimal("0"), max_digits=14, decimal_places=2)
    currency: str = Field(pattern=r"^[A-Z]{3}$")

    @model_validator(mode="after")
    def down_payment_must_not_exceed_price(self) -> PurchaseIntent:
        if self.down_payment > self.product_price:
            raise ValueError("down_payment must not exceed product_price")
        return self


class AffordabilityResult(ContractModel):
    finance_amount: Decimal = Field(ge=Decimal("0"), max_digits=14, decimal_places=2)
    monthly_income: Decimal = Field(ge=Decimal("0"), max_digits=14, decimal_places=2)
    existing_monthly_obligations: Decimal = Field(ge=Decimal("0"), max_digits=14, decimal_places=2)
    estimated_monthly_payment: Decimal = Field(ge=Decimal("0"), max_digits=14, decimal_places=2)
    obligation_ratio: Decimal | None = Field(default=None, ge=Decimal("0"), max_digits=8, decimal_places=6)
    affordability_indicator: Literal["not_assessed", "research_estimate"] = "not_assessed"
    research_only: Literal[True] = True
    explanation: str = Field(min_length=1, max_length=500)


class ResearchRiskResult(ContractModel):
    risk_status: Literal["not_validated"] = "not_validated"
    risk_information: str = "Research risk information is not connected in AC-1."
    research_only: Literal[True] = True


class FinancingOption(ContractModel):
    option_id: str = Field(min_length=1, max_length=80)
    provider_name: str = Field(min_length=1, max_length=120)
    provider_type: Literal["simulated_demo"] = "simulated_demo"
    principal: Decimal = Field(gt=Decimal("0"), max_digits=14, decimal_places=2)
    tenure_months: int = Field(gt=0, le=600)
    annual_rate_percent: Decimal = Field(ge=Decimal("0"), le=Decimal("100"), max_digits=6, decimal_places=3)
    estimated_emi: Decimal = Field(ge=Decimal("0"), max_digits=14, decimal_places=2)
    total_interest: Decimal = Field(ge=Decimal("0"), max_digits=14, decimal_places=2)
    total_repayment: Decimal = Field(ge=Decimal("0"), max_digits=14, decimal_places=2)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    demo_only: Literal[True] = True


class FinancingCostResult(ContractModel):
    option_id: str = Field(min_length=1, max_length=80)
    estimated_emi: Decimal = Field(ge=Decimal("0"), max_digits=14, decimal_places=2)
    total_interest: Decimal = Field(ge=Decimal("0"), max_digits=14, decimal_places=2)
    total_repayment: Decimal = Field(ge=Decimal("0"), max_digits=14, decimal_places=2)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    research_only: Literal[True] = True


class FinancingOptionRank(ContractModel):
    option_id: str = Field(min_length=1, max_length=80)
    rank: int = Field(gt=0)
    explanation: str = Field(min_length=1, max_length=300)


class Recommendation(ContractModel):
    recommended_option_id: str | None = Field(default=None, max_length=80)
    ranking: list[FinancingOptionRank] = Field(default_factory=list, max_length=50)
    explanation: str = Field(min_length=1, max_length=1000)
    research_only: Literal[True] = True
    requires_human_confirmation: Literal[True] = True


class HumanConfirmation(ContractModel):
    session_id: str = Field(min_length=1, max_length=80)
    option_id: str = Field(min_length=1, max_length=80)
    decision: Literal["confirm_simulation", "reject_simulation"]
    timestamp: datetime


class SimulationConfirmation(ContractModel):
    """Narrow gate contract accepted by a future simulator after a human action."""

    session_id: str = Field(min_length=1, max_length=80)
    option_id: str = Field(min_length=1, max_length=80)
    decision: Literal["confirm_simulation"]
    actor: Literal["human"]
    timestamp: datetime


class SimulatedTransaction(ContractModel):
    transaction_id: str = Field(min_length=1, max_length=80)
    session_id: str = Field(min_length=1, max_length=80)
    selected_option: FinancingOption
    status: Literal["simulated_complete", "rejected"]
    simulated: Literal[True] = True
    timestamp: datetime


class AuditEvent(ContractModel):
    event_id: str = Field(min_length=1, max_length=80)
    session_id: str = Field(min_length=1, max_length=80)
    event_type: CommerceWorkflowState
    actor: Literal["system", "human", "tool"]
    tool: str | None = Field(default=None, max_length=100)
    summary: str = Field(min_length=1, max_length=500)
    timestamp: datetime


class WorkflowStage(ContractModel):
    order: int = Field(ge=1, le=8)
    name: str
    state: CommerceWorkflowState
    status: Literal["planned"] = "planned"


class AgenticCommerceStatus(ContractModel):
    module: Literal["agentic_commerce"] = "agentic_commerce"
    phase: Literal["AC-1"] = "AC-1"
    status: Literal["foundation_ready"] = "foundation_ready"
    mode: Literal["research_demo"] = "research_demo"
    workflow_execution_enabled: Literal[False] = False
    real_transactions_enabled: Literal[False] = False
    real_lending_enabled: Literal[False] = False
    human_confirmation_required: Literal[True] = True
    audit_store_enabled: Literal[False] = False
