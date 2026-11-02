# Agentic Commerce AC-1 API and Data Contracts

## Active read-only endpoints

### `GET /v1/agentic-commerce/status`

Returns module `agentic_commerce`, phase `AC-1`, status `foundation_ready`, mode `research_demo`, with workflow execution, real transactions, real lending, and audit storage disabled. It states that human confirmation is required.

### `GET /v1/agentic-commerce/workflow`

Returns eight ordered workflow stages. Each stage is marked `planned`; this is descriptive metadata, not an executed workflow.

No purchase-intent submission, offer-discovery, recommendation, confirmation, transaction, or audit-write endpoint is exposed in AC-1.

## Typed contracts (inactive)

`src/agentic_commerce/schemas.py` defines:

- `PurchaseIntent`: opaque session identifier, product/category, price, down payment, tenure, monthly income/obligations, and ISO currency code. It has no name, address, account number, or borrower ID.
- `AffordabilityResult`: principal, income/obligations, estimated payment, optional ratio, explicit research-only indicator, and explanation.
- `ResearchRiskResult`: `not_validated` status and research-only wording.
- `FinancingOption`: simulated-demo provider type, principal, tenure, annual rate percentage, estimated EMI, interest/repayment totals, currency, and `demo_only=true`.
- `Recommendation`: optional option ID, ranked options, research-only explanation, and `requires_human_confirmation=true`.
- `HumanConfirmation`: session/option, explicit `confirm_simulation` or `reject_simulation`, and timestamp.
- `SimulatedTransaction`: simulated-only status and selected demo option.
- `AuditEvent`: opaque session/event IDs, typed state, actor/tool, bounded summary, and timestamp.

Monetary values use `Decimal`, unknown fields are rejected, and purchase intent validates positive product price, nonnegative down payment/income/obligations, down payment no greater than price, and positive tenure. The schemas do not imply a calculation, offer, recommendation, or transaction exists.

The typed future-tool interface is in `src/agentic_commerce/tools.py`. No tool is registered or callable in AC-1.
