"""Tests for inference service.

Tests model registry, prediction pipeline, and API endpoints.
"""

import pytest
import numpy as np
from src.inference import (
    get_available_models,
    get_model_info,
    get_feature_schema,
    validate_model_artifact,
    predict,
    ArtifactNotFoundError,
    InvalidInputError,
    ModelLoadError,
)
from src.inference.schemas import UCITaiwanRequest, PredictionRequest


class TestModelRegistry:
    """Test model registry functionality."""

    def test_model_registry_lists_available_models(self):
        """Test that get_available_models returns a list of models."""
        models = get_available_models()
        assert isinstance(models, list)
        assert len(models) > 0

        # Check that UCI Taiwan model is in the list
        uci_model = next((m for m in models if m["model_id"] == "uci_taiwan_xgb"), None)
        assert uci_model is not None
        assert uci_model["inference_ready"] is True

    def test_get_model_info_returns_correct_metadata(self):
        """Test that get_model_info returns correct model metadata."""
        model_info = get_model_info("uci_taiwan_xgb")

        assert model_info["model_id"] == "uci_taiwan_xgb"
        assert model_info["dataset_id"] == "DS003"
        assert model_info["geography"] == "Taiwan"
        assert model_info["target"] == "default payment next month"
        assert model_info["feature_count"] == 50
        assert model_info["inference_ready"] is True
        assert isinstance(model_info["limitations"], list)
        assert len(model_info["limitations"]) > 0

    def test_get_model_info_includes_artifact_existence(self):
        """Test that get_model_info checks artifact existence."""
        model_info = get_model_info("uci_taiwan_xgb")

        # These should be True if artifacts exist
        assert "artifact_exists" in model_info
        assert "calibration_exists" in model_info
        assert "feature_names_exist" in model_info
        assert "metadata_exists" in model_info

    def test_get_feature_schema_returns_feature_schema(self):
        """Test that get_feature_schema returns feature schema."""
        schema = get_feature_schema("uci_taiwan_xgb")

        assert schema["model_id"] == "uci_taiwan_xgb"
        assert "raw_features" in schema
        assert "engineered_features" in schema
        assert schema["total_feature_count"] == 50

        # Check that raw features include expected fields
        raw_features = schema["raw_features"]
        assert "LIMIT_BAL" in raw_features
        assert "SEX" in raw_features
        assert "EDUCATION" in raw_features
        assert "AGE" in raw_features

    def test_feature_schema_includes_field_types_and_constraints(self):
        """Test that feature schema includes type and constraint information."""
        schema = get_feature_schema("uci_taiwan_xgb")
        raw_features = schema["raw_features"]

        # Check LIMIT_BAL (numeric with range)
        limit_bal = raw_features["LIMIT_BAL"]
        assert limit_bal["type"] == "numeric"
        assert limit_bal["range"] == [0, 1000000]
        assert limit_bal["required"] is True

        # Check SEX (categorical with values)
        sex = raw_features["SEX"]
        assert sex["type"] == "categorical"
        assert sex["values"] == [1, 2]
        assert sex["value_labels"] == {1: "Male", 2: "Female"}

    def test_validate_model_artifact_checks_existence(self):
        """Test that validate_model_artifact checks artifact existence."""
        results = validate_model_artifact("uci_taiwan_xgb")

        assert results["model_id"] == "uci_taiwan_xgb"
        assert "artifact_exists" in results
        assert "artifact_loadable" in results
        assert "all_valid" in results


class TestPrediction:
    """Test prediction pipeline."""

    def test_predict_with_valid_input_returns_probability(self):
        """Test that predict returns a probability for valid input."""
        # Sample UCI Taiwan input
        features = {
            "LIMIT_BAL": 200000,
            "SEX": 2,
            "EDUCATION": 2,
            "MARRIAGE": 1,
            "AGE": 35,
            "PAY_0": 0,
            "PAY_2": 0,
            "PAY_3": 0,
            "PAY_4": 0,
            "PAY_5": 0,
            "PAY_6": 0,
            "BILL_AMT1": 50000,
            "BILL_AMT2": 45000,
            "BILL_AMT3": 40000,
            "BILL_AMT4": 35000,
            "BILL_AMT5": 30000,
            "BILL_AMT6": 25000,
            "PAY_AMT1": 5000,
            "PAY_AMT2": 5000,
            "PAY_AMT3": 5000,
            "PAY_AMT4": 5000,
            "PAY_AMT5": 5000,
            "PAY_AMT6": 5000,
        }

        result = predict("uci_taiwan_xgb", features)

        assert result.model_id == "uci_taiwan_xgb"
        assert result.dataset_id == "DS003"
        assert result.geography == "Taiwan"
        assert 0.0 <= result.probability <= 1.0
        assert result.predicted_class in ["Default risk", "Lower predicted default risk"]
        assert result.risk_category in ["Low", "Medium", "High"]
        assert isinstance(result.limitations, list)

    def test_predict_with_missing_required_field_raises_error(self):
        """Test that missing required field raises InvalidInputError."""
        features = {
            "LIMIT_BAL": 200000,
            "SEX": 2,
            # Missing EDUCATION
            "MARRIAGE": 1,
            "AGE": 35,
            # ... other fields missing
        }

        with pytest.raises(InvalidInputError) as exc_info:
            predict("uci_taiwan_xgb", features)

        assert "missing" in str(exc_info.value).lower()

    def test_predict_with_invalid_value_raises_error(self):
        """Test that invalid value raises InvalidInputError."""
        features = {
            "LIMIT_BAL": 200000,
            "SEX": 2,
            "EDUCATION": 2,
            "MARRIAGE": 1,
            "AGE": 35,
            "PAY_0": 0,
            "PAY_2": 0,
            "PAY_3": 0,
            "PAY_4": 0,
            "PAY_5": 0,
            "PAY_6": 0,
            "BILL_AMT1": 50000,
            "BILL_AMT2": 45000,
            "BILL_AMT3": 40000,
            "BILL_AMT4": 35000,
            "BILL_AMT5": 30000,
            "BILL_AMT6": 25000,
            "PAY_AMT1": 5000,
            "PAY_AMT2": 5000,
            "PAY_AMT3": 5000,
            "PAY_AMT4": 5000,
            "PAY_AMT5": 5000,
            "PAY_AMT6": 5000,
        }

        # Add an invalid field
        features["INVALID_FIELD"] = 999

        with pytest.raises(InvalidInputError):
            predict("uci_taiwan_xgb", features)

    def test_predict_returns_correct_provenance(self):
        """Test that prediction response includes correct provenance."""
        features = {
            "LIMIT_BAL": 200000,
            "SEX": 2,
            "EDUCATION": 2,
            "MARRIAGE": 1,
            "AGE": 35,
            "PAY_0": 0,
            "PAY_2": 0,
            "PAY_3": 0,
            "PAY_4": 0,
            "PAY_5": 0,
            "PAY_6": 0,
            "BILL_AMT1": 50000,
            "BILL_AMT2": 45000,
            "BILL_AMT3": 40000,
            "BILL_AMT4": 35000,
            "BILL_AMT5": 30000,
            "BILL_AMT6": 25000,
            "PAY_AMT1": 5000,
            "PAY_AMT2": 5000,
            "PAY_AMT3": 5000,
            "PAY_AMT4": 5000,
            "PAY_AMT5": 5000,
            "PAY_AMT6": 5000,
        }

        result = predict("uci_taiwan_xgb", features)

        assert result.dataset_name == "Default of Credit Card Clients"
        assert result.target == "default payment next month"
        assert result.target_meaning == "1 = Default next month, 0 = Repaid"
        assert "Taiwan" in result.geography
        assert "2005" in result.geography or "Taiwan" in result.geography


class TestSchemas:
    """Test Pydantic schemas."""

    def test_uci_taiwan_request_validates_correctly(self):
        """Test that UCITaiwanRequest validates correct input."""
        data = {
            "LIMIT_BAL": 200000,
            "SEX": 2,
            "EDUCATION": 2,
            "MARRIAGE": 1,
            "AGE": 35,
            "PAY_0": 0,
            "PAY_2": 0,
            "PAY_3": 0,
            "PAY_4": 0,
            "PAY_5": 0,
            "PAY_6": 0,
            "BILL_AMT1": 50000,
            "BILL_AMT2": 45000,
            "BILL_AMT3": 40000,
            "BILL_AMT4": 35000,
            "BILL_AMT5": 30000,
            "BILL_AMT6": 25000,
            "PAY_AMT1": 5000,
            "PAY_AMT2": 5000,
            "PAY_AMT3": 5000,
            "PAY_AMT4": 5000,
            "PAY_AMT5": 5000,
            "PAY_AMT6": 5000,
        }

        request = UCITaiwanRequest(**data)
        assert request.model_id == "uci_taiwan_xgb"
        assert request.LIMIT_BAL == 200000

    def test_uci_taiwan_request_rejects_invalid_range(self):
        """Test that UCITaiwanRequest rejects values outside valid range."""
        data = {
            "model_id": "uci_taiwan_xgb",
            "LIMIT_BAL": 2000000,  # Above max of 1,000,000
            "SEX": 2,
            "EDUCATION": 2,
            "MARRIAGE": 1,
            "AGE": 35,
            "PAY_0": 0,
            "PAY_2": 0,
            "PAY_3": 0,
            "PAY_4": 0,
            "PAY_5": 0,
            "PAY_6": 0,
            "BILL_AMT1": 50000,
            "BILL_AMT2": 45000,
            "BILL_AMT3": 40000,
            "BILL_AMT4": 35000,
            "BILL_AMT5": 30000,
            "BILL_AMT6": 25000,
            "PAY_AMT1": 5000,
            "PAY_AMT2": 5000,
            "PAY_AMT3": 5000,
            "PAY_AMT4": 5000,
            "PAY_AMT5": 5000,
            "PAY_AMT6": 5000,
        }

        with pytest.raises(Exception):  # Pydantic validation error
            UCITaiwanRequest(**data)

    def test_prediction_request_rejects_extra_fields(self):
        """Test that PredictionRequest rejects unknown fields."""
        data = {
            "model_id": "uci_taiwan_xgb",
            "features": {"LIMIT_BAL": 200000},
            "extra_field": "should_fail",
        }

        with pytest.raises(Exception):  # Pydantic validation error
            PredictionRequest(**data)
