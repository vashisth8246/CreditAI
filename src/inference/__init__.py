"""Inference service for verified model artifacts.

This module provides a research inference pipeline for loading verified models,
validating inputs, computing predictions, and generating explanations.

Only models with verified artifacts and documented evaluation metrics are exposed.
Indian deployment readiness is NOT VALIDATED - all predictions are research-only.
"""

from .model_registry import (
    get_available_models,
    get_model_info,
    get_feature_schema,
    validate_model_artifact,
    MODELS,
)

from .predictor import (
    load_model_and_preprocessing,
    validate_input,
    predict,
    ArtifactNotFoundError,
    InvalidInputError,
    ModelLoadError,
)

from .schemas import (
    PredictionRequest,
    UCITaiwanRequest,
    PredictionResponse,
    ModelInfoResponse,
    FeatureSchemaResponse,
)

from .explanations import (
    load_shap_explainer,
    explain_prediction,
    format_explanations,
)

__all__ = [
    "get_available_models",
    "get_model_info",
    "get_feature_schema",
    "validate_model_artifact",
    "MODELS",
    "load_model_and_preprocessing",
    "validate_input",
    "predict",
    "ArtifactNotFoundError",
    "InvalidInputError",
    "ModelLoadError",
    "PredictionRequest",
    "UCITaiwanRequest",
    "PredictionResponse",
    "ModelInfoResponse",
    "FeatureSchemaResponse",
    "load_shap_explainer",
    "explain_prediction",
    "format_explanations",
]
