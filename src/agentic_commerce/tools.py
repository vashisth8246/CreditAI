"""Typed interfaces for future tools. No AC-1 tool is registered or active."""

from __future__ import annotations

from typing import Protocol, Sequence

from .schemas import (
    AffordabilityResult,
    AuditEvent,
    FinancingCostResult,
    FinancingOption,
    FinancingOptionRank,
    HumanConfirmation,
    PurchaseIntent,
    Recommendation,
    ResearchRiskResult,
    SimulationConfirmation,
    SimulatedTransaction,
)


class AgenticCommerceToolContracts(Protocol):
    async def calculate_affordability(self, intent: PurchaseIntent) -> AffordabilityResult: ...

    async def get_research_risk(self, intent: PurchaseIntent) -> ResearchRiskResult: ...

    async def discover_demo_financing_options(self, intent: PurchaseIntent) -> Sequence[FinancingOption]: ...

    async def calculate_financing_cost(self, option: FinancingOption) -> FinancingCostResult: ...

    async def compare_financing_options(self, options: Sequence[FinancingOption]) -> Sequence[FinancingOptionRank]: ...

    async def generate_recommendation(self, options: Sequence[FinancingOption]) -> Recommendation: ...

    async def request_human_confirmation(self, recommendation: Recommendation) -> HumanConfirmation: ...

    async def simulate_transaction(
        self, confirmation: SimulationConfirmation, option: FinancingOption
    ) -> SimulatedTransaction: ...

    async def write_audit_event(self, event: AuditEvent) -> AuditEvent: ...
