"""Prediction service for verified model artifacts.

This module handles loading models, validating inputs, applying feature engineering,
computing predictions, and applying calibration.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple
import joblib
import numpy as np
import pandas as pd

from .model_registry import MODELS, get_model_info, get_feature_schema
from .schemas import PredictionResponse, FeatureContribution
from .explanations import compute_prediction_explanations


class ArtifactNotFoundError(Exception):
    """Raised when a model artifact cannot be found."""
    pass


class InvalidInputError(Exception):
    """Raised when input validation fails."""
    pass


class ModelLoadError(Exception):
    """Raised when model fails to load."""
    pass


# Cache for loaded models to avoid repeated disk I/O
_model_cache: Dict[str, Tuple[Any, Any, List[str]]] = {}
_calibration_cache: Dict[str, Any] = {}


def load_model_and_preprocessing(model_id: str) -> Tuple[Any, List[str]]:
    """Load model artifact and feature names.

    Args:
        model_id: Model identifier.

    Returns:
        Tuple of (model_object, feature_names_list).

    Raises:
        ArtifactNotFoundError: If artifact not found.
        ModelLoadError: If model fails to load.
    """
    if model_id in _model_cache:
        return _model_cache[model_id]

    if model_id not in MODELS:
        raise ArtifactNotFoundError(
            f"Model '{model_id}' not found in registry."
        )

    model_info = MODELS[model_id]
    artifact_path = Path(model_info["artifact_path"])
    feature_names_path = Path(model_info["feature_names_path"])

    if not artifact_path.exists():
        raise ArtifactNotFoundError(
            f"Model artifact not found: {artifact_path}"
        )

    if not feature_names_path.exists():
        raise ArtifactNotFoundError(
            f"Feature names not found: {feature_names_path}"
        )

    try:
        model = joblib.load(artifact_path)
        with open(feature_names_path, "r") as f:
            import json
            feature_names = json.load(f)

        _model_cache[model_id] = (model, feature_names)
        return model, feature_names

    except Exception as e:
        raise ModelLoadError(f"Failed to load model: {e}")


def load_calibration_model(model_id: str) -> Any:
    """Load calibration model if available.

    Args:
        model_id: Model identifier.

    Returns:
        Calibration model object or None if not available or invalid.
    """
    if model_id in _calibration_cache:
        return _calibration_cache[model_id]

    if model_id not in MODELS:
        return None

    model_info = MODELS[model_id]
    calibration_path = Path(model_info["calibration_path"])

    if not calibration_path.exists():
        return None

    try:
        calibration = joblib.load(calibration_path)
        # Check if calibration model is properly fitted
        if hasattr(calibration, 'slope') and hasattr(calibration, 'intercept'):
            _calibration_cache[model_id] = calibration
            return calibration
        else:
            print(f"Calibration model not properly fitted for {model_id}")
            return None
    except Exception as e:
        print(f"Failed to load calibration model: {e}")
        return None


def validate_input(features: Dict[str, Any], schema: Dict[str, Any]) -> None:
    """Validate input features against schema.

    Args:
        features: Input feature dictionary.
        schema: Feature schema from get_feature_schema.

    Raises:
        InvalidInputError: If validation fails.
    """
    raw_features = schema.get("raw_features", {})

    # Check required fields
    for field_name, field_schema in raw_features.items():
        if field_schema.get("required", False) and field_name not in features:
            raise InvalidInputError(
                f"Required field '{field_name}' is missing."
            )

    # Validate each field
    for field_name, value in features.items():
        if field_name not in raw_features:
            raise InvalidInputError(
                f"Unknown field '{field_name}'. "
                f"Valid fields: {list(raw_features.keys())}"
            )

        field_schema = raw_features[field_name]
        field_type = field_schema.get("type")

        if field_type == "numeric":
            if not isinstance(value, (int, float)):
                raise InvalidInputError(
                    f"Field '{field_name}' must be numeric, got {type(value).__name__}."
                )

            value_range = field_schema.get("range")
            if value_range:
                min_val, max_val = value_range
                if not (min_val <= value <= max_val):
                    raise InvalidInputError(
                        f"Field '{field_name}' must be between {min_val} and {max_val}, got {value}."
                    )

        elif field_type == "categorical":
            valid_values = field_schema.get("values")
            if valid_values and value not in valid_values:
                raise InvalidInputError(
                    f"Field '{field_name}' must be one of {valid_values}, got {value}."
                )


def apply_feature_engineering(raw_features: Dict[str, Any]) -> Dict[str, float]:
    """Apply feature engineering to raw UCI Taiwan features.

    This function computes the 27 engineered features from the 23 raw features
    as defined in the Phase 1 UCI benchmark.

    Args:
        raw_features: Dictionary of raw features (23 fields).

    Returns:
        Dictionary of all 50 features (23 raw + 27 engineered).
    """
    # Extract raw features
    LIMIT_BAL = raw_features["LIMIT_BAL"]
    SEX = raw_features["SEX"]
    EDUCATION = raw_features["EDUCATION"]
    MARRIAGE = raw_features["MARRIAGE"]
    AGE = raw_features["AGE"]

    PAY_0 = raw_features["PAY_0"]
    PAY_2 = raw_features["PAY_2"]
    PAY_3 = raw_features["PAY_3"]
    PAY_4 = raw_features["PAY_4"]
    PAY_5 = raw_features["PAY_5"]
    PAY_6 = raw_features["PAY_6"]

    BILL_AMT1 = raw_features["BILL_AMT1"]
    BILL_AMT2 = raw_features["BILL_AMT2"]
    BILL_AMT3 = raw_features["BILL_AMT3"]
    BILL_AMT4 = raw_features["BILL_AMT4"]
    BILL_AMT5 = raw_features["BILL_AMT5"]
    BILL_AMT6 = raw_features["BILL_AMT6"]

    PAY_AMT1 = raw_features["PAY_AMT1"]
    PAY_AMT2 = raw_features["PAY_AMT2"]
    PAY_AMT3 = raw_features["PAY_AMT3"]
    PAY_AMT4 = raw_features["PAY_AMT4"]
    PAY_AMT5 = raw_features["PAY_AMT5"]
    PAY_AMT6 = raw_features["PAY_AMT6"]

    # Helper function to avoid division by zero
    def safe_divide(numerator, denominator, default=0.0):
        return numerator / max(denominator, 1.0)

    # Credit utilization features
    UTIL_1 = safe_divide(BILL_AMT1, LIMIT_BAL)
    UTIL_2 = safe_divide(BILL_AMT2, LIMIT_BAL)
    UTIL_3 = safe_divide(BILL_AMT3, LIMIT_BAL)
    UTIL_4 = safe_divide(BILL_AMT4, LIMIT_BAL)
    UTIL_5 = safe_divide(BILL_AMT5, LIMIT_BAL)
    UTIL_6 = safe_divide(BILL_AMT6, LIMIT_BAL)

    AVG_UTILIZATION = np.mean([UTIL_1, UTIL_2, UTIL_3, UTIL_4, UTIL_5, UTIL_6])
    MAX_UTILIZATION = max([UTIL_1, UTIL_2, UTIL_3, UTIL_4, UTIL_5, UTIL_6])

    # Payment to bill ratio
    PAY_TO_BILL_1 = safe_divide(PAY_AMT1, max(BILL_AMT1, 1))
    PAY_TO_BILL_2 = safe_divide(PAY_AMT2, max(BILL_AMT2, 1))
    PAY_TO_BILL_3 = safe_divide(PAY_AMT3, max(BILL_AMT3, 1))
    PAY_TO_BILL_4 = safe_divide(PAY_AMT4, max(BILL_AMT4, 1))
    PAY_TO_BILL_5 = safe_divide(PAY_AMT5, max(BILL_AMT5, 1))
    PAY_TO_BILL_6 = safe_divide(PAY_AMT6, max(BILL_AMT6, 1))

    AVG_PAY_TO_BILL = np.mean([PAY_TO_BILL_1, PAY_TO_BILL_2, PAY_TO_BILL_3,
                               PAY_TO_BILL_4, PAY_TO_BILL_5, PAY_TO_BILL_6])

    # Delinquency features
    pay_fields = [PAY_0, PAY_2, PAY_3, PAY_4, PAY_5, PAY_6]
    MAX_DELINQUENCY = max(pay_fields)
    AVG_DELINQUENCY = np.mean(pay_fields)
    DELINQUENT_MONTHS_COUNT = sum(1 for p in pay_fields if p > 0)
    RECENT_DELINQUENCY_FLAG = 1 if PAY_0 > 0 else 0

    # Delinquency trends
    DELINQUENCY_TREND_SHORT = PAY_0 - PAY_2
    DELINQUENCY_TREND_LONG = PAY_0 - PAY_6

    # Bill change and growth
    BILL_CHANGE_1_2 = BILL_AMT1 - BILL_AMT2
    BILL_GROWTH_OVER_LIMIT = safe_divide(BILL_AMT1 - BILL_AMT6, LIMIT_BAL)

    # Payment frequency
    PAYMENT_MONTHS_COUNT = sum(1 for p in [PAY_AMT1, PAY_AMT2, PAY_AMT3,
                                             PAY_AMT4, PAY_AMT5, PAY_AMT6] if p > 0)

    TOTAL_PAY_TO_TOTAL_BILL = safe_divide(
        sum([PAY_AMT1, PAY_AMT2, PAY_AMT3, PAY_AMT4, PAY_AMT5, PAY_AMT6]),
        max(sum([BILL_AMT1, BILL_AMT2, BILL_AMT3, BILL_AMT4, BILL_AMT5, BILL_AMT6]), 1)
    )

    PAYMENT_AMOUNT_STD = np.std([PAY_AMT1, PAY_AMT2, PAY_AMT3,
                                 PAY_AMT4, PAY_AMT5, PAY_AMT6])

    TIMELY_PAYMENT_COUNT = sum(1 for p in pay_fields if p <= 0)

    # Combine all features
    all_features = raw_features.copy()
    all_features.update({
        "UTIL_1": UTIL_1,
        "UTIL_2": UTIL_2,
        "UTIL_3": UTIL_3,
        "UTIL_4": UTIL_4,
        "UTIL_5": UTIL_5,
        "UTIL_6": UTIL_6,
        "AVG_UTILIZATION": AVG_UTILIZATION,
        "MAX_UTILIZATION": MAX_UTILIZATION,
        "PAY_TO_BILL_1": PAY_TO_BILL_1,
        "PAY_TO_BILL_2": PAY_TO_BILL_2,
        "PAY_TO_BILL_3": PAY_TO_BILL_3,
        "PAY_TO_BILL_4": PAY_TO_BILL_4,
        "PAY_TO_BILL_5": PAY_TO_BILL_5,
        "PAY_TO_BILL_6": PAY_TO_BILL_6,
        "AVG_PAY_TO_BILL": AVG_PAY_TO_BILL,
        "MAX_DELINQUENCY": MAX_DELINQUENCY,
        "AVG_DELINQUENCY": AVG_DELINQUENCY,
        "DELINQUENT_MONTHS_COUNT": DELINQUENT_MONTHS_COUNT,
        "RECENT_DELINQUENCY_FLAG": RECENT_DELINQUENCY_FLAG,
        "DELINQUENCY_TREND_SHORT": DELINQUENCY_TREND_SHORT,
        "DELINQUENCY_TREND_LONG": DELINQUENCY_TREND_LONG,
        "BILL_CHANGE_1_2": BILL_CHANGE_1_2,
        "BILL_GROWTH_OVER_LIMIT": BILL_GROWTH_OVER_LIMIT,
        "PAYMENT_MONTHS_COUNT": PAYMENT_MONTHS_COUNT,
        "TOTAL_PAY_TO_TOTAL_BILL": TOTAL_PAY_TO_TOTAL_BILL,
        "PAYMENT_AMOUNT_STD": PAYMENT_AMOUNT_STD,
        "TIMELY_PAYMENT_COUNT": TIMELY_PAYMENT_COUNT,
    })

    return all_features


def predict_proba(model: Any, features: Dict[str, float], feature_names: List[str]) -> float:
    """Get raw probability from model.

    Args:
        model: Loaded model object.
        features: Feature dictionary.
        feature_names: Expected feature names.

    Returns:
        Raw probability of positive class.
    """
    # Extract actual model if saved as dict (common with CalibratedClassifierCV)
    if isinstance(model, dict):
        model = model.get("base_model", model)

    # Convert to DataFrame in correct feature order
    feature_array = np.array([features.get(name, 0) for name in feature_names])
    feature_array = feature_array.reshape(1, -1)

    # Get probability for positive class (index 1)
    proba = model.predict_proba(feature_array)[0, 1]

    return float(proba)


def apply_calibration(proba: float, calibration_model: Any) -> float:
    """Apply Platt scaling calibration.

    Args:
        proba: Raw probability.
        calibration_model: Calibration model (Platt sigmoid or custom calibrator).

    Returns:
        Calibrated probability.
    """
    if calibration_model is None:
        return proba

    # Check if calibrator is properly fitted
    if not (hasattr(calibration_model, 'slope') and hasattr(calibration_model, 'intercept')):
        return proba

    # Handle custom PlattCalibrator from src.calibration.calibrate
    if hasattr(calibration_model, 'predict_proba'):
        # Custom calibrator expects array of probabilities
        calibrated_proba = calibration_model.predict_proba([[proba]])[0]
        return float(calibrated_proba)
    else:
        # Fallback: return uncalibrated
        return proba


def get_risk_category(probability: float, threshold: float = 0.5) -> str:
    """Get risk category based on probability and threshold.

    Args:
        probability: Predicted probability.
        threshold: Decision threshold.

    Returns:
        Risk category string.
    """
    if probability < threshold * 0.5:
        return "Low"
    elif probability < threshold:
        return "Medium"
    else:
        return "High"


def predict(
    model_id: str,
    input_features: Dict[str, Any],
    include_explanations: bool = True,
) -> PredictionResponse:
    """End-to-end prediction pipeline.

    Args:
        model_id: Model identifier.
        input_features: Input feature dictionary (raw features for UCI).
        include_explanations: Compute per-row SHAP values. Batch inference passes
            False because batch exports do not include SHAP and TreeExplainer on
            every row is needlessly expensive.

    Returns:
        PredictionResponse with prediction results.

    Raises:
        ArtifactNotFoundError: If model not found.
        InvalidInputError: If input validation fails.
        ModelLoadError: If model fails to load.
    """
    # Get model info
    model_info = get_model_info(model_id)

    # Get feature schema
    schema = get_feature_schema(model_id)

    # Validate input
    validate_input(input_features, schema)

    # Load model and preprocessing
    model, feature_names = load_model_and_preprocessing(model_id)

    # Apply feature engineering
    all_features = apply_feature_engineering(input_features)

    # Get raw probability
    raw_proba = predict_proba(model, all_features, feature_names)

    # Apply calibration if available
    calibration_model = load_calibration_model(model_id)
    calibrated = calibration_model is not None
    calibration_method = model_info.get("calibration_method") if calibrated else None

    if calibrated:
        probability = apply_calibration(raw_proba, calibration_model)
    else:
        probability = raw_proba

    # Determine class and risk category
    threshold = 0.5  # Default threshold
    if probability >= threshold:
        predicted_class = "Default risk"
    else:
        predicted_class = "Lower predicted default risk"

    risk_category = get_risk_category(probability, threshold)

    # Compute genuine SHAP explanations (single-borrower inference only by default)
    feature_contributions = (
        compute_prediction_explanations(
            model=model,
            model_id=model_id,
            feature_dict=all_features,
            feature_names=feature_names,
            top_k=6,
        )
        if include_explanations
        else None
    )

    # Build response
    response = PredictionResponse(
        model_id=model_id,
        dataset_id=model_info["dataset_id"],
        dataset_name=model_info["dataset_name"],
        geography=model_info["geography"],
        target=model_info["target"],
        target_meaning=model_info["target_meaning"],
        prediction_timestamp=datetime.now(timezone.utc).isoformat(),
        predicted_class=predicted_class,
        probability=probability,
        risk_category=risk_category,
        threshold=threshold,
        calibrated=calibrated,
        calibration_method=calibration_method,
        limitations=model_info["limitations"],
        feature_contributions=feature_contributions,
    )

    return response
