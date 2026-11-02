"""Static workflow contract; this state machine is not executed in AC-1."""

from .schemas import CommerceWorkflowState, WorkflowStage


WORKFLOW_STAGES = (
    WorkflowStage(order=1, name="Purchase Intent", state=CommerceWorkflowState.PURCHASE_INTENT_RECEIVED),
    WorkflowStage(order=2, name="Affordability / Risk Research", state=CommerceWorkflowState.AFFORDABILITY_RESEARCH),
    WorkflowStage(order=3, name="Financing Options", state=CommerceWorkflowState.OFFER_DISCOVERY),
    WorkflowStage(order=4, name="Comparison", state=CommerceWorkflowState.OFFER_COMPARISON),
    WorkflowStage(order=5, name="Recommendation", state=CommerceWorkflowState.RECOMMENDATION_READY),
    WorkflowStage(order=6, name="User Confirmation", state=CommerceWorkflowState.AWAITING_HUMAN_CONFIRMATION),
    WorkflowStage(order=7, name="Simulated Transaction", state=CommerceWorkflowState.SIMULATION_CONFIRMED),
    WorkflowStage(order=8, name="Audit Trail", state=CommerceWorkflowState.SIMULATED_TRANSACTION_COMPLETE),
)

# A simulator may be called only after AWAITING_HUMAN_CONFIRMATION receives an
# explicit confirm_simulation decision. Rejection and failure are terminal.
ALLOWED_STATE_TRANSITIONS = {
    CommerceWorkflowState.PURCHASE_INTENT_RECEIVED: (CommerceWorkflowState.AFFORDABILITY_RESEARCH, CommerceWorkflowState.FAILED),
    CommerceWorkflowState.AFFORDABILITY_RESEARCH: (CommerceWorkflowState.RISK_RESEARCH, CommerceWorkflowState.FAILED),
    CommerceWorkflowState.RISK_RESEARCH: (CommerceWorkflowState.OFFER_DISCOVERY, CommerceWorkflowState.FAILED),
    CommerceWorkflowState.OFFER_DISCOVERY: (CommerceWorkflowState.OFFER_COMPARISON, CommerceWorkflowState.FAILED),
    CommerceWorkflowState.OFFER_COMPARISON: (CommerceWorkflowState.RECOMMENDATION_READY, CommerceWorkflowState.FAILED),
    CommerceWorkflowState.RECOMMENDATION_READY: (CommerceWorkflowState.AWAITING_HUMAN_CONFIRMATION, CommerceWorkflowState.FAILED),
    CommerceWorkflowState.AWAITING_HUMAN_CONFIRMATION: (
        CommerceWorkflowState.SIMULATION_CONFIRMED,
        CommerceWorkflowState.SIMULATION_REJECTED,
    ),
    CommerceWorkflowState.SIMULATION_CONFIRMED: (CommerceWorkflowState.SIMULATED_TRANSACTION_COMPLETE,),
    CommerceWorkflowState.SIMULATION_REJECTED: (),
    CommerceWorkflowState.SIMULATED_TRANSACTION_COMPLETE: (),
    CommerceWorkflowState.FAILED: (),
}
