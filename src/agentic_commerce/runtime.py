"""In-process, research-only AC-3 session and explicit simulation gate."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from uuid import NAMESPACE_URL, uuid5

from .comparison import compare_purchase
from .research_data import get_research_record
from .schemas import (
    AC3CreateSessionRequest,
    AC3SimulationConfirmation,
    AuditEvent,
    CommerceProvenance,
    CommerceSessionResponse,
    CommerceWorkflowState,
    ResearchModelOutput,
    SimulatedTransactionRecord,
)
from src.inference.predictor import ArtifactNotFoundError, InvalidInputError, ModelLoadError, predict

_sessions: dict[str, CommerceSessionResponse] = {}
_sessions_lock = RLock()


def _event(session_id: str, event_type: CommerceWorkflowState, actor: str, summary: str,
           provenance: dict[str, str]) -> AuditEvent:
    # Stable event identity keeps repeated calculations reproducible. The
    # event timestamp remains the actual time the user action occurred.
    return AuditEvent(
        event_id=str(uuid5(NAMESPACE_URL, f"creditai:ac3:{session_id}:{event_type.value}")),
        session_id=session_id,
        event_type=event_type,
        actor=actor,
        summary=summary,
        timestamp=datetime.now(timezone.utc),
        provenance=provenance,
    )


def create_session(request: AC3CreateSessionRequest) -> CommerceSessionResponse:
    session_id = request.intent.session_id
    research_record = None
    if request.research_record_reference:
        if request.research_profile is not None:
            raise ValueError("Choose either a verified dataset record or a manual research profile, not both.")
        research_record = get_research_record(request.research_record_reference)

    research_features = research_record.features if research_record else request.research_profile
    research_output = None
    if research_features is not None:
        try:
            prediction = predict("uci_taiwan_xgb", research_features, include_explanations=True)
        except InvalidInputError as exc:
            raise ValueError(str(exc)) from exc
        except (ArtifactNotFoundError, FileNotFoundError, ModelLoadError, OSError) as exc:
            raise RuntimeError(f"Taiwan research model artifact is unavailable: {exc}") from exc
        research_output = ResearchModelOutput(
            model_id=prediction.model_id,
            geography="Taiwan",
            probability=prediction.probability,
            predicted_class=prediction.predicted_class,
            calibrated=prediction.calibrated,
            limitations=prediction.limitations,
            feature_contributions=prediction.feature_contributions,
        )
        if research_record:
            research_record = research_record.model_copy(update={"model_inference_performed": True})

    comparison = compare_purchase(request)
    provenance = CommerceProvenance(
        research_record=("uci_taiwan_research_dataset" if research_record else "unavailable_or_not_selected"),
        research_profile_source=(
            "verified_dataset_record" if research_record
            else request.research_profile_source if research_features is not None
            else "not_provided"
        ),
        model_inference=("uci_taiwan_research_model" if research_output else "not_used"),
    )
    provenance_map = provenance.model_dump()
    events = [
        _event(session_id, CommerceWorkflowState.PURCHASE_INTENT_RECEIVED, "human",
               "User-entered purchase context received.", provenance_map),
    ]
    if research_record:
        events.append(_event(session_id, CommerceWorkflowState.AFFORDABILITY_RESEARCH, "tool",
                             "Verified Taiwan research row supplied the raw profile for a separate research-only model estimate; financing comparisons do not use it.",
                             {"research_record": "uci_taiwan_research_dataset", "model_inference": "uci_taiwan_research_model", "ground_truth_target": "excluded"}))
    elif research_output:
        events.append(_event(session_id, CommerceWorkflowState.AFFORDABILITY_RESEARCH, "tool",
                             "User-entered raw profile supplied to the Taiwan research model; output is separate from financing calculations.",
                             {"research_profile": provenance.research_profile_source, "model_inference": "uci_taiwan_research_model", "ground_truth_target": "not_provided"}))
    events.extend([
        _event(session_id, CommerceWorkflowState.OFFER_DISCOVERY, "tool",
               f"Generated {len(comparison.options)} simulated rate scenarios from user-supplied parameters.",
               {"financing_rates": "simulated_parameter"}),
        _event(session_id, CommerceWorkflowState.OFFER_COMPARISON, "tool",
               "Compared estimated payments and total interest using deterministic calculations.",
               {"payment_estimates": "deterministic_calculation"}),
        _event(session_id, CommerceWorkflowState.RECOMMENDATION_READY, "tool",
               "Produced a research-preferred scenario from the supplied assumptions.",
               {"preferred_option": "deterministic_comparison"}),
    ])
    response = CommerceSessionResponse(
        session_id=session_id,
        status="awaiting_confirmation",
        comparison=comparison,
        research_record=research_record,
        research_output=research_output,
        provenance=provenance,
        audit_events=events,
        transaction=None,
    )
    with _sessions_lock:
        if session_id in _sessions:
            raise ValueError("This session ID already exists. Start a new session before confirming.")
        _sessions[session_id] = response
    return response


def get_session(session_id: str) -> CommerceSessionResponse | None:
    with _sessions_lock:
        return _sessions.get(session_id)


def confirm_simulation(session_id: str, confirmation: AC3SimulationConfirmation) -> CommerceSessionResponse | None:
    with _sessions_lock:
        current = _sessions.get(session_id)
        if current is None:
            return None
        if current.transaction is not None:
            if current.transaction.selected_option.option_id != confirmation.option_id:
                raise ValueError("This session was already confirmed with a different option.")
            return current.model_copy(update={"idempotent_replay": True})
        if confirmation.option_id not in {item.option_id for item in current.comparison.options}:
            raise LookupError("Selected financing scenario does not belong to this session.")

        selected = next(item for item in current.comparison.options if item.option_id == confirmation.option_id)
        confirmed_event = _event(
            session_id, CommerceWorkflowState.SIMULATION_CONFIRMED, "human",
            "User explicitly confirmed the selected simulated financing option.",
            {"confirmation": "explicit_user_action", "financing_option": "simulated_parameter"},
        )
        completed_event = _event(
            session_id, CommerceWorkflowState.SIMULATED_TRANSACTION_COMPLETE, "tool",
            "Research transaction simulation completed; no external transaction was executed.",
            {"simulation": "local_research_simulation", "real_transaction": "not_executed"},
        )
        transaction = SimulatedTransactionRecord(
            simulation_id=str(uuid5(
                NAMESPACE_URL,
                f"creditai:ac3:simulation:{session_id}:{selected.option_id}",
            )),
            session_id=session_id,
            research_record_reference=current.research_record.reference if current.research_record else None,
            selected_option=selected,
            purchase_price=current.comparison.purchase_price,
            down_payment=current.comparison.down_payment,
            financed_amount=current.comparison.financed_amount,
            monthly_payment=selected.estimated_monthly_payment,
            tenure_months=selected.tenure_months,
            total_estimated_repayment=selected.estimated_total_payment,
            timestamp=completed_event.timestamp,
            audit_reference=completed_event.event_id,
        )
        updated = current.model_copy(update={
            "status": "simulation_completed",
            "audit_events": [*current.audit_events, confirmed_event, completed_event],
            "transaction": transaction,
        })
        _sessions[session_id] = updated
        return updated
