"""AC-1 status and workflow-contract endpoints; no commerce tools execute."""

from fastapi import APIRouter

from src.agentic_commerce.schemas import AgenticCommerceStatus, WorkflowStage
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
