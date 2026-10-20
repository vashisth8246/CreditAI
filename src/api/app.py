"""FastAPI adapter. Install the API dependencies listed in requirements.txt."""
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr
from starlette.exceptions import HTTPException as StarletteHTTPException

from .contract import ContractError, not_validated_response, validate_request

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

# Keep local Vite development usable on any loopback port; deployments can add
# explicit web origins through CORS_ORIGINS without opening the API globally.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
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
    if model_id != "uci_taiwan_xgb":
        raise HTTPException(status_code=404, detail=f"Evaluation artifacts not found for '{model_id}'")
    eval_path = Path("models/uci_taiwan_eval.json")
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
# Batch prediction endpoint for Taiwan research model
# ---------------------------------------------------------------------------
# duplicate import removed
import pandas as pd
from typing import List

@app.post("/v1/research/taiwan/batch-predict")
async def batch_predict_endpoint(file: UploadFile = File(...)):
    """Accept an Excel or CSV file, validate rows, and return per‑row predictions.

    The file must contain the 23 raw UCI Taiwan fields. An optional column
    `borrower_reference` can be included for identification but is never used as a
    model feature.
    """
    # -------------------------------------------------------------------
    # 1. Load file into a DataFrame (support .xlsx and .csv)
    # -------------------------------------------------------------------
    filename = file.filename
    ext = filename.split('.')[-1].lower()
    if ext not in {"csv", "xlsx"}:
        raise HTTPException(status_code=415, detail="Unsupported file type. Use .csv or .xlsx.")
    try:
        max_upload_bytes = 10 * 1024 * 1024  # 10 MB
        content = await file.read()
        if len(content) > max_upload_bytes:
            raise HTTPException(status_code=413, detail="Uploaded file exceeds the 10 MB limit.")
        if ext == "csv":
            df = pd.read_csv(pd.io.common.BytesIO(content))
        else:
            df = pd.read_excel(pd.io.common.BytesIO(content))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse uploaded file: {e}")

    # -------------------------------------------------------------------
    # 2. Basic sanity checks (empty, size, row count)
    # -------------------------------------------------------------------
    if df.empty:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    max_rows = 5000
    if len(df) > max_rows:
        raise HTTPException(status_code=400, detail=f"File contains {len(df)} rows; maximum allowed is {max_rows}.")

    # -------------------------------------------------------------------
    # 3. Validate required columns against the feature schema
    # -------------------------------------------------------------------
    model_id = "uci_taiwan_xgb"
    schema = get_feature_schema(model_id)
    raw_features = schema.get("raw_features", {})
    required_cols = [name for name, meta in raw_features.items() if meta.get("required", False)]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise HTTPException(status_code=422, detail={"missing_columns": missing})

    # Optional reference column – keep for output but drop from model input
    reference_col = None
    if "borrower_reference" in df.columns:
        reference_col = "borrower_reference"

    # -------------------------------------------------------------------
    # 4. Process each row individually, preserving order and row number
    # -------------------------------------------------------------------
    results: List[dict] = []
    for idx, row in df.iterrows():
        row_number = idx + 2  # +2 because pandas is 0‑based and header is line 1
        raw_dict = row.to_dict()
        # Remove reference column before validation / prediction
        borrower_ref = None
        if reference_col:
            borrower_ref = raw_dict.pop(reference_col, None)
        # Cast to native Python types (pandas may use numpy scalars)
        raw_dict = {k: (v.item() if hasattr(v, "item") else v) for k, v in raw_dict.items()}
        try:
            # Validate using the same routine as single‑borrower
            validate_input(raw_dict, schema)
            pred = predict(model_id, raw_dict)
            result_entry = {
                "row_index": row_number,
                "borrower_reference": borrower_ref,
                "status": "success",
                "prediction": {
                    "model_id": pred.model_id,
                    "probability": pred.probability,
                    "predicted_class": pred.predicted_class,
                    "risk_category": pred.risk_category,
                    "calibrated": pred.calibrated,
                    "threshold": pred.threshold,
                },
            }
        except Exception as e:
            # Capture validation / prediction failures without exposing internals
            result_entry = {
                "row_index": row_number,
                "borrower_reference": borrower_ref,
                "status": "error",
                "error_message": str(e),
            }
        results.append(result_entry)

    return {"model_id": model_id, "results": results}
