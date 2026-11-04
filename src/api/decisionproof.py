"""Synthetic DecisionProof research endpoints. Only catalog IDs and bounded policy controls are accepted."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from ..decisionproof import AnalysisRequest, SCENARIOS, analyze, benchmark

router = APIRouter(prefix="/v1/research/decisionproof", tags=["DecisionProof"])


@router.get("/scenarios")
def scenarios():
    return {"synthetic": True, "scenarios": [scenario.model_dump() for scenario in SCENARIOS.values()]}


@router.get("/evaluation")
def evaluation():
    return benchmark()


@router.post("/analyze", openapi_extra={"requestBody": {"required": True, "content": {
    "application/json": {"schema": AnalysisRequest.model_json_schema()},
}}})
async def analysis(request: Request):
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > 4096:
            raise HTTPException(413, "Synthetic policy request exceeds 4 KiB.")
        body.extend(chunk)
    try:
        controls = AnalysisRequest.model_validate_json(body)
    except ValidationError:
        raise HTTPException(422, "Use a catalog scenario and bounded integer policy inputs.") from None
    if controls.scenario_id not in SCENARIOS:
        raise HTTPException(404, "Unknown synthetic scenario.")
    return analyze(controls)
