# Agentic Commerce AC-1 Architecture

## Scope

AC-1 establishes a separate Agentic Commerce foundation. It does not replace Borrower Prediction or Batch Evaluation and does not run an autonomous agent. The `src/agentic_commerce/` package contains data contracts, a typed future-tool protocol, and a static workflow state map. `src/api/agentic_commerce.py` exposes read-only foundation metadata under `/v1/agentic-commerce/`. The frontend adds separate Agentic Commerce and Commerce Audit Trail navigation entries.

## Approved future workflow

1. Purchase Intent
2. Affordability / Risk Research
3. Financing Options
4. Comparison
5. Recommendation
6. Human Confirmation
7. Simulated Transaction
8. Audit Trail

All eight displayed stages are `planned` and inactive in AC-1. The state contract includes purchase intent, affordability research, risk research, offer discovery/comparison, recommendation, waiting for confirmation, confirmed/rejected simulation, completion, and failure.

## Tool architecture

`AgenticCommerceToolContracts` defines typed asynchronous contracts for affordability, research risk information, demo option discovery, cost calculation, comparison, recommendations, human confirmation, simulated transactions, and audit writes. AC-1 registers no implementation or orchestration runtime for those methods.

## Component boundaries

```text
CreditAI
├── Credit Risk Research
│   ├── Borrower Prediction (existing)
│   └── Batch Evaluation (existing)
└── Agentic Commerce (AC-1 foundation)
    ├── Typed contracts and inactive tool interface
    ├── Read-only status and workflow endpoints
    ├── Foundation page
    └── Empty audit-trail page; no event store
```

Borrower Prediction and Batch Evaluation keep their current routes, inputs, calculations, and behavior. Agentic Commerce does not route through `/v1/score` or alter research model artifacts.

See [API contract](AC1_API_CONTRACT.md), [safety boundaries](AC1_SAFETY_BOUNDARIES.md), and [implementation report](AC1_IMPLEMENTATION_REPORT.md).
