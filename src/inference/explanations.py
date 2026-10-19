"""Explanation service for model predictions.

This module generates genuine SHAP explanations for predictions, showing which features
contributed most to the prediction and in which direction.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

try:
    import shap

    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

from .schemas import FeatureContribution


class ExplainerError(Exception):
    """Raised when explanation generation fails."""

    pass


# Global cache for explainers
_explainer_cache: Dict[str, Any] = {}


def get_tree_explainer(model: Any, model_id: str) -> Any:
    """Retrieve or initialize a cached SHAP TreeExplainer for the given model."""
    if not SHAP_AVAILABLE:
        raise ExplainerError("SHAP library not available in environment.")

    if model_id in _explainer_cache:
        return _explainer_cache[model_id]

    # Extract base tree model if packed in dictionary
    if isinstance(model, dict):
        base = model.get("base_model", model)
    else:
        base = model

    try:
        explainer = shap.TreeExplainer(base)
        _explainer_cache[model_id] = explainer
        return explainer
    except Exception as e:
        raise ExplainerError(f"Failed to create SHAP TreeExplainer: {e}")


def compute_prediction_explanations(
    model: Any,
    model_id: str,
    feature_dict: Dict[str, float],
    feature_names: List[str],
    top_k: int = 6,
) -> Optional[List[FeatureContribution]]:
    """Compute local SHAP feature contributions for a single prediction."""
    if not SHAP_AVAILABLE:
        return None

    try:
        explainer = get_tree_explainer(model, model_id)
        # Assemble feature array in required column order
        feat_array = np.array(
            [[feature_dict.get(name, 0.0) for name in feature_names]],
            dtype=float,
        )

        shap_values = explainer.shap_values(feat_array)

        # Handle different SHAP output structures
        if isinstance(shap_values, list):
            # Binary classification list [class 0, class 1]
            raw_shap = shap_values[1] if len(shap_values) > 1 else shap_values[0]
        else:
            raw_shap = shap_values

        raw_shap = np.asarray(raw_shap).flatten()
        if len(raw_shap) != len(feature_names):
            return None

        # Build contribution list
        contributions: List[FeatureContribution] = []
        for name, val in zip(feature_names, raw_shap):
            contribution_val = float(val)
            direction = "increases_risk" if contribution_val > 0 else "decreases_risk"
            contributions.append(
                FeatureContribution(
                    feature=name,
                    contribution=round(float(abs(contribution_val)), 4),
                    direction=direction,
                )
            )

        # Sort by absolute contribution descending
        contributions.sort(key=lambda c: c.contribution, reverse=True)
        return contributions[:top_k]

    except Exception as e:
        # Gracefully handle explainability errors without breaking prediction inference
        print(f"[Explanation Warning] Could not generate SHAP contributions: {e}")
        return None


def load_shap_explainer(model: Any, background_data: Optional[np.ndarray] = None) -> Any:
    """Load or create SHAP explainer for a model."""
    if not SHAP_AVAILABLE:
        raise ExplainerError("SHAP library not available in environment.")
    base = model.get("base_model", model) if isinstance(model, dict) else model
    try:
        return shap.TreeExplainer(base)
    except Exception as e:
        raise ExplainerError(f"Failed to create SHAP explainer: {e}")


def explain_prediction(explainer: Any, features: np.ndarray, feature_names: List[str]) -> np.ndarray:
    """Generate SHAP values for a single prediction."""
    try:
        if features.ndim == 1:
            features = features.reshape(1, -1)
        return explainer.shap_values(features)
    except Exception as e:
        raise ExplainerError(f"Failed to generate SHAP values: {e}")


def format_explanations(
    shap_values: np.ndarray,
    feature_names: List[str],
    top_k: int = 5,
) -> Tuple[List[FeatureContribution], List[FeatureContribution]]:
    """Format SHAP values into readable feature contributions."""
    from typing import Tuple
    if isinstance(shap_values, list):
        shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
    shap_arr = np.asarray(shap_values).flatten()

    paired = list(zip(feature_names, shap_arr))
    risk_increasing = [
        FeatureContribution(feature=name, contribution=float(abs(val)), direction="increases_risk")
        for name, val in paired if val > 0
    ]
    risk_decreasing = [
        FeatureContribution(feature=name, contribution=float(abs(val)), direction="decreases_risk")
        for name, val in paired if val <= 0
    ]
    risk_increasing.sort(key=lambda x: x.contribution, reverse=True)
    risk_decreasing.sort(key=lambda x: x.contribution, reverse=True)
    return risk_increasing[:top_k], risk_decreasing[:top_k]


def generate_explanations(
    model_id: str,
    features: Dict[str, float],
    feature_names: List[str],
) -> Tuple[List[FeatureContribution], List[FeatureContribution]]:
    """Generate feature contributions for a prediction."""
    from .predictor import load_model_and_preprocessing
    model, _ = load_model_and_preprocessing(model_id)
    explainer = load_shap_explainer(model)
    feature_array = np.array([features.get(name, 0.0) for name in feature_names])
    shap_values = explain_prediction(explainer, feature_array, feature_names)
    return format_explanations(shap_values, feature_names)
