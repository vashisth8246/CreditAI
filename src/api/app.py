"""FastAPI adapter. Install the API dependencies listed in requirements.txt."""
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr
from starlette.exceptions import HTTPException as StarletteHTTPException

from .contract import ContractError, not_validated_response, validate_request
from .batch_service import (
    BatchError,
    MAX_UPLOAD_BYTES,
    build_csv,
    build_xlsx,
    inspect_workbook,
    predict_workbook,
)

# Import inference modules
from ..inference import (
    get_available_models,
    get_model_info,
    get_feature_schema,
    validate_input,
    predict,
    ArtifactNotFoundError,
    InvalidInputError,
    ModelLoadError,
)
from ..inference.schemas import PredictionRequest


class Transaction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transaction_id: StrictStr
    date: StrictStr
    transaction_type: StrictStr
    amount: StrictFloat | StrictInt
    category: StrictStr | None = None
    counterparty: StrictStr | None = None
    balance_after_transaction: StrictFloat | StrictInt | None = None


class ScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: StrictStr
    observation_start: StrictStr
    prediction_date: StrictStr
    transactions: list[Transaction] = Field(..., min_length=1)
    request_id: StrictStr | None = None


app = FastAPI(title="CreditAI Score API", version="1.0.0")

# Vite development uses a same-origin proxy. Cross-origin deployments must
# explicitly list their frontend origins instead of allowing all loopback ports.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(ContractError)
async def contract_error_handler(_: Request, exc: ContractError):
    return JSONResponse(status_code=422, content={"error": {"code": exc.code, "message": exc.message, "field": exc.field}})


@app.exception_handler(RequestValidationError)
async def request_error_handler(_: Request, exc: RequestValidationError):
    # Deliberately omit input values so logs/responses do not echo transaction data.
    errors = [{"field": ".".join(str(x) for x in e["loc"]), "code": e["type"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"error": {"code": "invalid_request", "message": "Request validation failed.", "details": errors}})


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException):
    detail_msg = exc.detail if hasattr(exc, "detail") and isinstance(exc.detail, str) else "Invalid HTTP request or malformed body."
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": "invalid_request", "message": detail_msg}})


@app.get("/health")
async def health():
    return {"status": "ok", "scoring": "not_validated"}


@app.get("/v1/status")
async def system_status():
    """System status separating connectivity, models, research inference, and production scoring."""
    models = get_available_models()
    return {
        "backend_connectivity": "connected",
        "models_registered": len(models),
        "research_inference_ready": any(m.get("inference_ready", False) for m in models),
        "indian_production_scoring": "not_validated",
    }


@app.post("/v1/score")
async def score(request: ScoreRequest):
    payload = request.model_dump(exclude_none=True)
    validate_request(payload)
    # No synthetic pipeline is loaded or invoked here.
    return not_validated_response(request.request_id)


# ============================================================================
# Phase 7 & 8: Research Inference & Evaluation Endpoints
# These endpoints provide research inference and reproducible evaluation
# for verified model artifacts.
# Indian deployment readiness: NOT VALIDATED.
# ============================================================================


@app.get("/v1/models")
async def list_models():
    """List all available models with basic metadata."""
    try:
        models = get_available_models()
        return {"models": models, "count": len(models)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")


@app.get("/v1/models/{model_id}")
async def get_model_endpoint(model_id: str):
    """Get detailed model information."""
    try:
        model_info = get_model_info(model_id)
        return model_info
    except ArtifactNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get model info: {str(e)}")


@app.get("/v1/models/{model_id}/schema")
async def get_model_schema_endpoint(model_id: str):
    """Get feature schema for a model."""
    try:
        schema = get_feature_schema(model_id)
        return schema
    except ArtifactNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get feature schema: {str(e)}")


@app.get("/v1/models/{model_id}/evaluation")
async def get_model_evaluation_endpoint(model_id: str):
    """Get reproducible evaluation artifacts (ROC/PR curves, confusion matrix, deciles)."""
    import json
    from pathlib import Path
    if model_id not in ["uci_taiwan_xgb", "uci_taiwan_knn"]:
        raise HTTPException(status_code=404, detail=f"Evaluation artifacts not found for '{model_id}'")
    eval_path = Path("models/uci_taiwan_knn_eval.json" if model_id == "uci_taiwan_knn" else "models/uci_taiwan_eval.json")
    if not eval_path.exists():
        raise HTTPException(status_code=404, detail="Evaluation artifact not found on disk")
    try:
        with open(eval_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load evaluation artifact: {str(e)}")


@app.post("/v1/predict")
async def predict_endpoint(request: PredictionRequest):
    """Run prediction for a single borrower.

    This endpoint provides research inference for verified models only.
    Indian deployment readiness: NOT VALIDATED.
    """
    try:
        result = predict(request.model_id, request.features)
        return result
    except ArtifactNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidInputError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ModelLoadError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


# ---------------------------------------------------------------------------
# Batch research inference (Taiwan UCI benchmark)
# ---------------------------------------------------------------------------
# The service layer lives in batch_service.py. These endpoints only handle HTTP
# concerns: upload limits, form parsing and file responses.

class BatchExportRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    results: list[dict] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


async def _read_upload(file: UploadFile) -> tuple[bytes, str]:
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded file exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.",
        )
    filename = file.filename or "upload.csv"
    return content, filename


def _parse_mapping(raw: str | None) -> dict | None:
    if raw is None or raw.strip() == "":
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="The column mapping is not valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=422, detail="The column mapping must be a JSON object.")
    return parsed


@app.post("/v1/research/taiwan/batch/inspect")
async def batch_inspect_endpoint(
    file: UploadFile = File(...),
    sheet: str | None = Form(None),
    mapping: str | None = Form(None),
):
    """Inspect a CSV/Excel workbook and validate one worksheet.

    Returns every worksheet's metadata plus a detailed preview, header report,
    column mapping and row validation for the selected sheet. Sheets are never
    combined automatically.
    """
    content, filename = await _read_upload(file)
    try:
        return inspect_workbook(content, filename, selected_sheet=sheet, mapping=_parse_mapping(mapping))
    except BatchError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@app.post("/v1/research/taiwan/batch/analyze")
async def batch_analyze_endpoint(
    file: UploadFile = File(...),
    sheet: str = Form(...),
    mapping: str = Form(...),
):
    """Re-validate a worksheet after an explicit column-mapping change."""
    content, filename = await _read_upload(file)
    try:
        return inspect_workbook(content, filename, selected_sheet=sheet, mapping=_parse_mapping(mapping))
    except BatchError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@app.post("/v1/research/taiwan/batch-predict")
async def batch_predict_endpoint(
    file: UploadFile = File(...),
    sheets: str | None = Form(None),
):
    """Score one or more worksheets with the Taiwan research model.

    ``sheets`` is a JSON array of ``{"name": "Sheet1", "mapping": {"0": "LIMIT_BAL"}}``.
    When omitted, the first non-empty worksheet is scored using automatic header
    matching (kept for backwards compatibility).
    """
    content, filename = await _read_upload(file)
    selections = None
    if sheets is not None and sheets.strip() != "":
        try:
            parsed = json.loads(sheets)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail="The sheet selection is not valid JSON.") from exc
        if not isinstance(parsed, list):
            raise HTTPException(status_code=422, detail="The sheet selection must be a JSON array.")
        selections = parsed
    try:
        return predict_workbook(content, filename, selections or [])
    except BatchError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@app.post("/v1/research/taiwan/batch/export/xlsx")
async def batch_export_xlsx_endpoint(payload: BatchExportRequest):
    """Return a formula-injection-safe predictions workbook with a summary sheet."""
    if len(payload.results) > 20_000:
        raise HTTPException(status_code=400, detail="Too many result rows to export.")
    content = build_xlsx(payload.model_dump())
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="creditai_batch_predictions.xlsx"'},
    )


@app.post("/v1/research/taiwan/batch/export/csv")
async def batch_export_csv_endpoint(payload: BatchExportRequest):
    """Return a formula-injection-safe predictions CSV."""
    if len(payload.results) > 20_000:
        raise HTTPException(status_code=400, detail="Too many result rows to export.")
    content = build_csv(payload.model_dump())
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="creditai_batch_predictions.csv"'},
    )
