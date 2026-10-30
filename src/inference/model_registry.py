"""Model registry for verified inference artifacts.

This module maintains a registry of models that have been verified and
are suitable for research inference. Only models with saved artifacts,
documented evaluation metrics, and clear limitations are exposed.
"""

from pathlib import Path
from typing import Any, Dict, List
import json
import joblib


class ArtifactNotFoundError(Exception):
    """Raised when a model artifact cannot be found or loaded."""
    pass


class ModelValidationError(Exception):
    """Raised when a model fails validation checks."""
    pass


# Registry of verified models
# Note: Historical ROC-AUC and PR-AUC values are from Phase 1 report.
# These will be re-verified in Phase 7.2 by re-evaluating on the test set.
MODELS: Dict[str, Dict[str, Any]] = {
    "uci_taiwan_xgb": {
        "model_id": "uci_taiwan_xgb",
        "artifact_path": "models/creditai_model.joblib",
        "calibration_path": "models/calibration_model.joblib",
        "feature_names_path": "models/feature_names.json",
        "metadata_path": "models/model_metadata.json",
        "dataset_id": "DS003",
        "dataset_name": "Default of Credit Card Clients",
        "dataset_path": "Data/credit_default/default of credit card clients.xls",
        "geography": "Taiwan",
        "time_coverage": "April - September 2005",
        "target": "default payment next month",
        "target_meaning": "1 = Default next month, 0 = Repaid",
        "target_prevalence": "22.12% (6,636/30,000)",
        "feature_count": 50,
        "raw_feature_count": 23,
        "engineered_feature_count": 27,
        "model_type": "XGBoost",
        "training_date": "2026-10-06",
        "random_seed": 42,
        "train_val_test_split": "70% / 15% / 15% (stratified)",
        # Historical metrics from Phase 1 report - to be re-verified
        "test_roc_auc": 0.7807,
        "test_pr_auc": 0.5588,
        "calibration_status": "Calibrated — Platt scaling fitted on validation split (slope: 0.474, intercept: -1.265)",
        "calibration_method": "Platt sigmoid",
        "limitations": [
            "Taiwan credit card data from 2005",
            "Not validated for Indian borrowers",
            "Cross-sectional benchmark, not time-series",
            "Historical evaluation only",
            "Target is next-month default, not fixed-horizon",
            "Population is credit card holders, not general borrowers",
            "No Indian transfer claim or regulatory approval",
        ],
        "inference_ready": True,
        "shap_available": True,
        "source": "UCI Machine Learning Repository",
        "source_url": "https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients",
        "license": "CC BY 4.0",
    },
    "uci_taiwan_knn": {
        "model_id": "uci_taiwan_knn",
        "artifact_path": "models/creditai_knn_model.joblib",
        "calibration_path": "models/calibration_knn_model.joblib",
        "feature_names_path": "models/feature_names.json",
        "metadata_path": "models/knn_model_metadata.json",
        "dataset_id": "DS003",
        "dataset_name": "Default of Credit Card Clients",
        "dataset_path": "Data/credit_default/default of credit card clients.xls",
        "geography": "Taiwan",
        "time_coverage": "April - September 2005",
        "target": "default payment next month",
        "target_meaning": "1 = Default next month, 0 = Repaid",
        "target_prevalence": "22.12% (6,636/30,000)",
        "feature_count": 50,
        "raw_feature_count": 23,
        "engineered_feature_count": 27,
        "model_type": "K-Nearest Neighbors",
        "training_date": "2026-10-27",
        "random_seed": 42,
        "train_val_test_split": "70% / 15% / 15% (stratified)",
        "test_roc_auc": 0.7649,
        "test_pr_auc": 0.5235,
        "calibration_status": "Calibrated — Platt scaling fitted on validation split (slope: 0.8633, intercept: -0.1464)",
        "calibration_method": "Platt sigmoid",
        "limitations": [
            "Taiwan credit card portfolio behavior from 2005",
            "Not validated for Indian borrowers",
            "Distance metric sensitive to feature scaling and collinearity",
            "Historical offline benchmark only",
            "Target is next-month default, not multi-year horizon",
            "Population is credit card holders, not general Indian loan applicants",
            "No Indian transfer claim or regulatory clearance",
        ],
        "inference_ready": True,
        "shap_available": False,
        "explanation_method": "KNN Local Neighbor Variance Attribution",
        "source": "UCI Machine Learning Repository",
        "source_url": "https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients",
        "license": "CC BY 4.0",
    },
}


def get_available_models() -> List[Dict[str, Any]]:
    """Get list of all available models with basic metadata.

    Returns:
        List of model dictionaries with key metadata only.
    """
    available = []
    for model_id, model_info in MODELS.items():
        if model_info.get("inference_ready", False):
            available.append({
                "model_id": model_info["model_id"],
                "dataset_id": model_info["dataset_id"],
                "dataset_name": model_info["dataset_name"],
                "geography": model_info["geography"],
                "model_type": model_info["model_type"],
                "test_roc_auc": model_info["test_roc_auc"],
                "test_pr_auc": model_info["test_pr_auc"],
                "calibration_status": model_info["calibration_status"],
                "inference_ready": model_info["inference_ready"],
            })
    return available


def get_model_info(model_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific model.

    Args:
        model_id: Model identifier (e.g., "uci_taiwan_xgb")

    Returns:
        Dictionary with full model metadata.

    Raises:
        ArtifactNotFoundError: If model_id is not in registry.
    """
    if model_id not in MODELS:
        raise ArtifactNotFoundError(
            f"Model '{model_id}' not found in registry. "
            f"Available models: {list(MODELS.keys())}"
        )

    model_info = MODELS[model_id].copy()

    # Add artifact existence check
    model_info["artifact_exists"] = Path(model_info["artifact_path"]).exists()
    model_info["calibration_exists"] = Path(model_info["calibration_path"]).exists()
    model_info["feature_names_exist"] = Path(model_info["feature_names_path"]).exists()
    model_info["metadata_exists"] = Path(model_info["metadata_path"]).exists()

    # Surface global importance only when it can be read from the genuine model
    # artifact. It describes fitted-model behavior, not a single prediction.
    model_info["global_feature_importance"] = []
    if model_info["artifact_exists"] and model_info["feature_names_exist"]:
        try:
            model = joblib.load(model_info["artifact_path"])
            if isinstance(model, dict):
                model = model.get("base_model", model)
            importances = getattr(model, "feature_importances_", None)
            with open(model_info["feature_names_path"], "r") as feature_file:
                feature_names = json.load(feature_file)
            if importances is not None and len(importances) == len(feature_names):
                model_info["global_feature_importance"] = sorted(
                    [{"feature": name, "importance": float(value)} for name, value in zip(feature_names, importances)],
                    key=lambda row: row["importance"], reverse=True,
                )
        except Exception:
            # Model information remains available if optional chart metadata cannot be loaded.
            pass

    return model_info


def get_feature_schema(model_id: str) -> Dict[str, Any]:
    """Get feature schema for a model.

    Returns the expected input features with types, ranges, and constraints.

    Args:
        model_id: Model identifier.

    Returns:
        Dictionary with feature schema.

    Raises:
        ArtifactNotFoundError: If model_id not found or feature_names file missing.
    """
    if model_id not in MODELS:
        raise ArtifactNotFoundError(
            f"Model '{model_id}' not found in registry."
        )

    model_info = MODELS[model_id]
    feature_names_path = Path(model_info["feature_names_path"])

    if not feature_names_path.exists():
        raise ArtifactNotFoundError(
            f"Feature names file not found: {feature_names_path}"
        )

    with open(feature_names_path, "r") as f:
        feature_names = json.load(f)

    # For UCI Taiwan model, provide detailed schema for raw features
    # Engineered features are computed server-side
    if model_id in ["uci_taiwan_xgb", "uci_taiwan_knn"]:
        raw_features = {
            "LIMIT_BAL": {
                "type": "numeric",
                "description": "Amount of given credit (NT$)",
                "range": [0, 1000000],
                "required": True,
                "unit": "NT$",
            },
            "SEX": {
                "type": "categorical",
                "description": "Gender",
                "values": [1, 2],
                "value_labels": {1: "Male", 2: "Female"},
                "required": True,
            },
            "EDUCATION": {
                "type": "categorical",
                "description": "Education level",
                "values": [1, 2, 3, 4, 5, 6],
                "value_labels": {
                    1: "Graduate school",
                    2: "University",
                    3: "High school",
                    4: "Others",
                    5: "Unknown",
                    6: "Unknown",
                },
                "required": True,
            },
            "MARRIAGE": {
                "type": "categorical",
                "description": "Marital status",
                "values": [1, 2, 3],
                "value_labels": {1: "Married", 2: "Single", 3: "Others"},
                "required": True,
            },
            "AGE": {
                "type": "numeric",
                "description": "Age in years",
                "range": [21, 79],
                "required": True,
                "unit": "years",
            },
        }

        # Add repayment status fields (PAY_0, PAY_2 to PAY_6)
        # Note: UCI dataset naming convention skips PAY_1
        raw_features["PAY_0"] = {
            "type": "numeric",
            "description": "Repayment status in September 2005 (-2=no consumption, -1=pay duly, 0=revolving, 1-9=delay months)",
            "values": list(range(-2, 10)),
            "value_labels": {
                -2: "No consumption",
                -1: "Pay duly",
                0: "Revolving credit",
                1: "Payment delay 1 month",
                2: "Payment delay 2 months",
                3: "Payment delay 3 months",
                4: "Payment delay 4 months",
                5: "Payment delay 5 months",
                6: "Payment delay 6 months",
                7: "Payment delay 7 months",
                8: "Payment delay 8 months",
                9: "Payment delay 9+ months",
            },
            "required": True,
        }

        for i in range(2, 7):
            pay_field = f"PAY_{i}"
            month_map = {2: "August", 3: "July", 4: "June", 5: "May", 6: "April"}
            raw_features[pay_field] = {
                "type": "numeric",
                "description": f"Repayment status in {month_map[i]} 2005 (-2=no consumption, -1=pay duly, 0=revolving, 1-9=delay months)",
                "values": list(range(-2, 10)),
                "value_labels": {
                    -2: "No consumption",
                    -1: "Pay duly",
                    0: "Revolving credit",
                    1: "Payment delay 1 month",
                    2: "Payment delay 2 months",
                    3: "Payment delay 3 months",
                    4: "Payment delay 4 months",
                    5: "Payment delay 5 months",
                    6: "Payment delay 6 months",
                    7: "Payment delay 7 months",
                    8: "Payment delay 8 months",
                    9: "Payment delay 9+ months",
                },
                "required": True,
            }

        # Add bill amount fields (BILL_AMT1 to BILL_AMT6)
        for i in range(1, 7):
            raw_features[f"BILL_AMT{i}"] = {
                "type": "numeric",
                "description": f"Bill statement amount for month -{i}",
                "range": [-335000, 1680000],
                "required": True,
                "unit": "NT$",
            }

        # Add payment amount fields (PAY_AMT1 to PAY_AMT6)
        for i in range(1, 7):
            raw_features[f"PAY_AMT{i}"] = {
                "type": "numeric",
                "description": f"Amount paid in month -{i}",
                "range": [0, 873000],
                "required": True,
                "unit": "NT$",
            }

        return {
            "model_id": model_id,
            "raw_features": raw_features,
            "engineered_features": [
                "UTIL_1", "UTIL_2", "UTIL_3", "UTIL_4", "UTIL_5", "UTIL_6",
                "AVG_UTILIZATION", "MAX_UTILIZATION",
                "PAY_TO_BILL_1", "PAY_TO_BILL_2", "PAY_TO_BILL_3",
                "PAY_TO_BILL_4", "PAY_TO_BILL_5", "PAY_TO_BILL_6",
                "AVG_PAY_TO_BILL",
                "MAX_DELINQUENCY", "AVG_DELINQUENCY", "DELINQUENT_MONTHS_COUNT",
                "RECENT_DELINQUENCY_FLAG",
                "DELINQUENCY_TREND_SHORT", "DELINQUENCY_TREND_LONG",
                "BILL_CHANGE_1_2", "BILL_GROWTH_OVER_LIMIT",
                "PAYMENT_MONTHS_COUNT", "TOTAL_PAY_TO_TOTAL_BILL",
                "PAYMENT_AMOUNT_STD", "TIMELY_PAYMENT_COUNT",
            ],
            "total_feature_count": len(feature_names),
            "note": "Engineered features are computed server-side from raw features",
        }

    # Generic schema for other models
    return {
        "model_id": model_id,
        "features": feature_names,
        "total_feature_count": len(feature_names),
    }


def validate_model_artifact(model_id: str) -> Dict[str, bool]:
    """Validate that a model's artifacts exist and can be loaded.

    Args:
        model_id: Model identifier.

    Returns:
        Dictionary with validation results.

    Raises:
        ArtifactNotFoundError: If model_id not found.
    """
    if model_id not in MODELS:
        raise ArtifactNotFoundError(
            f"Model '{model_id}' not found in registry."
        )

    model_info = MODELS[model_id]
    results = {
        "model_id": model_id,
        "artifact_exists": False,
        "artifact_loadable": False,
        "calibration_exists": False,
        "calibration_loadable": False,
        "feature_names_exist": False,
        "metadata_exists": False,
        "all_valid": False,
    }

    # Check artifact existence
    artifact_path = Path(model_info["artifact_path"])
    results["artifact_exists"] = artifact_path.exists()

    if results["artifact_exists"]:
        try:
            joblib.load(artifact_path)
            results["artifact_loadable"] = True
        except Exception as e:
            print(f"Failed to load artifact: {e}")

    # Check calibration existence
    calibration_path = Path(model_info["calibration_path"])
    results["calibration_exists"] = calibration_path.exists()

    if results["calibration_exists"]:
        try:
            joblib.load(calibration_path)
            results["calibration_loadable"] = True
        except Exception as e:
            print(f"Failed to load calibration: {e}")

    # Check feature names
    results["feature_names_exist"] = Path(model_info["feature_names_path"]).exists()

    # Check metadata
    results["metadata_exists"] = Path(model_info["metadata_path"]).exists()

    # Overall validation
    results["all_valid"] = all([
        results["artifact_exists"],
        results["artifact_loadable"],
        results["feature_names_exist"],
    ])

    return results
