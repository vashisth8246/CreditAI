# Agentic Commerce AC-1 Safety Boundaries

## Non-negotiable limits

- Research/demo only. No real purchase, payment, lending, lender integration, or automated loan decision.
- No agent/tool execution, offer generation, recommendation, transaction, or audit persistence is active in AC-1.
- All workflow stages are marked planned. The pages do not fabricate completed runs, offers, or audit events.
- Future risk output must be called **Research risk information**, never a credit approval decision.
- Taiwan models remain research/demo-only and are not validated for Indian borrowers. No production lending readiness is claimed.
- `POST /v1/score` remains safety-locked: `score_status="not_validated"`, `default_probability=null`, and `validated_risk_estimate=false`.
- No model/calibration artifact is retrained, replaced, or modified by AC-1.

## Human-confirmation invariant

Any future simulated transaction must follow:

```text
Recommendation
    ↓
AWAITING_HUMAN_CONFIRMATION (wait; no timeout auto-accept)
    ├── explicit reject → SIMULATION_REJECTED
    └── explicit confirm_simulation → SIMULATION_CONFIRMED → simulated transaction
```

The state map has no recommendation-to-confirmed transition. Only an explicit human confirmation contract can move the future state from waiting to a simulation branch. A real transaction is outside the approved AC scope.

## Data minimization and audit

Purchase intent excludes unnecessary personal identifiers. Future audit records should contain opaque session IDs, event/tool identifiers, a bounded summary, actor, and timestamp; raw financial inputs and credentials should not be copied into event summaries. AC-1 has no event store, and the audit page truthfully reports that no simulated commerce sessions have been recorded.
