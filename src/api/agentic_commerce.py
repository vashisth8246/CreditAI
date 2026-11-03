"""AC-1 status and workflow-contract endpoints; no commerce tools execute."""

from fastapi import APIRouter, HTTPException

from src.agentic_commerce.research_data import (
    EXPECTED_SHA256,
    dataset_status,
    list_research_records,
)
from src.agentic_commerce.runtime import create_session, confirm_simulation, get_session
from src.agentic_commerce.schemas import (
    AC3CreateSessionRequest,
    AC3SimulationConfirmation,
    AgenticCommerceStatus,
    CommerceSessionResponse,
    ResearchDataStatus,
    ResearchRecordListResponse,
    WorkflowStage,
)
from src.agentic_commerce.workflow import WORKFLOW_STAGES
from src.agentic_commerce.comparison import compare_purchase
from src.agentic_commerce.schemas import CommerceComparisonRequest, CommerceComparisonResponse


router = APIRouter(prefix="/v1/agentic-commerce", tags=["Agentic Commerce — AC-1 Foundation"])


@router.get("/status", response_model=AgenticCommerceStatus)
def agentic_commerce_status() -> AgenticCommerceStatus:
    return AgenticCommerceStatus()


@router.get("/workflow", response_model=list[WorkflowStage])
def agentic_commerce_workflow() -> list[WorkflowStage]:
    return list(WORKFLOW_STAGES)


def compare_financing_scenarios(request: CommerceComparisonRequest) -> CommerceComparisonResponse:
    return compare_purchase(request)


def research_data_status() -> ResearchDataStatus:
    return dataset_status()


def research_records(offset: int = 0, limit: int = 25) -> ResearchRecordListResponse:
    status = dataset_status()
    if status.status == "unavailable":
        return ResearchRecordListResponse(
            status="unavailable", sha256=EXPECTED_SHA256, message=status.message,
        )
    try:
        row_count, records = list_research_records(offset=offset, limit=limit)
    except (FileNotFoundError, ValueError, OSError) as exc:
        return ResearchRecordListResponse(status="unavailable", sha256=EXPECTED_SHA256, message=str(exc))
    return ResearchRecordListResponse(
        status="available", sha256=EXPECTED_SHA256, row_count=row_count, records=records,
        message="Verified Taiwan research records; the historical target is excluded.",
    )


def create_commerce_session(request: AC3CreateSessionRequest) -> CommerceSessionResponse:
    try:
        return create_session(request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        status_code = 409 if "already exists" in str(exc) else 422
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def commerce_session(session_id: str) -> CommerceSessionResponse:
    response = get_session(session_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Commerce session was not found in this running process.")
    return response


def confirm_commerce_simulation(session_id: str, confirmation: AC3SimulationConfirmation) -> CommerceSessionResponse:
    try:
        response = confirm_simulation(session_id, confirmation)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if response is None:
        raise HTTPException(status_code=404, detail="Commerce session was not found in this running process.")
    return response
