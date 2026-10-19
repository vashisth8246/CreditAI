"""Pydantic schemas for inference request/response validation.

This module defines the schemas for prediction requests and responses,
ensuring type safety and validation for the inference API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, StrictInt, StrictFloat, confloat


class PredictionRequest(BaseModel):
    """Base prediction request schema."""

    model_id: str = Field(
        ...,
        description="Model identifier (e.g., 'uci_taiwan_xgb')",
        example="uci_taiwan_xgb",
    )
    features: Dict[str, Any] = Field(
        ...,
        description="Feature dictionary matching model's expected schema",
    )

    class Config:
        extra = "forbid"  # Reject unknown fields


class UCITaiwanRequest(BaseModel):
    """Specific request schema for UCI Taiwan model.

    This schema validates the 23 raw features required for the UCI Taiwan model.
    Engineered features are computed server-side.
    """

    model_id: str = Field(default="uci_taiwan_xgb")

    # Demographics
    LIMIT_BAL: StrictInt = Field(
        ...,
        ge=0,
        le=1000000,
        description="Amount of given credit in NT dollars",
    )
    SEX: StrictInt = Field(..., ge=1, le=2, description="1=male, 2=female")
    EDUCATION: StrictInt = Field(
        ...,
        ge=1,
        le=6,
        description="1=graduate, 2=university, 3=high school, 4=others, 5=unknown, 6=unknown",
    )
    MARRIAGE: StrictInt = Field(
        ...,
        ge=1,
        le=3,
        description="1=married, 2=single, 3=others",
    )
    AGE: StrictInt = Field(..., ge=21, le=79, description="Age in years")

    # Repayment status (PAY_0 to PAY_6)
    PAY_0: StrictInt = Field(
        ...,
        ge=-2,
        le=9,
        description="Repayment status in September 2005 (-2=no consumption, -1=pay duly, 0=revolving, 1-9=delay months)",
    )
    PAY_2: StrictInt = Field(
        ...,
        ge=-2,
        le=9,
        description="Repayment status in August 2005",
    )
    PAY_3: StrictInt = Field(
        ...,
        ge=-2,
        le=9,
        description="Repayment status in July 2005",
    )
    PAY_4: StrictInt = Field(
        ...,
        ge=-2,
        le=9,
        description="Repayment status in June 2005",
    )
    PAY_5: StrictInt = Field(
        ...,
        ge=-2,
        le=9,
        description="Repayment status in May 2005",
    )
    PAY_6: StrictInt = Field(
        ...,
        ge=-2,
        le=9,
        description="Repayment status in April 2005",
    )

    # Bill amounts (BILL_AMT1 to BILL_AMT6)
    BILL_AMT1: StrictInt = Field(
        ...,
        ge=-335000,
        le=1680000,
        description="Bill statement amount in September 2005 (NT$)",
    )
    BILL_AMT2: StrictInt = Field(
        ...,
        ge=-335000,
        le=1680000,
        description="Bill statement amount in August 2005 (NT$)",
    )
    BILL_AMT3: StrictInt = Field(
        ...,
        ge=-335000,
        le=1680000,
        description="Bill statement amount in July 2005 (NT$)",
    )
    BILL_AMT4: StrictInt = Field(
        ...,
        ge=-335000,
        le=1680000,
        description="Bill statement amount in June 2005 (NT$)",
    )
    BILL_AMT5: StrictInt = Field(
        ...,
        ge=-335000,
        le=1680000,
        description="Bill statement amount in May 2005 (NT$)",
    )
    BILL_AMT6: StrictInt = Field(
        ...,
        ge=-335000,
        le=1680000,
        description="Bill statement amount in April 2005 (NT$)",
    )

    # Payment amounts (PAY_AMT1 to PAY_AMT6)
    PAY_AMT1: StrictInt = Field(
        ...,
        ge=0,
        le=873000,
        description="Amount paid in September 2005 (NT$)",
    )
    PAY_AMT2: StrictInt = Field(
        ...,
        ge=0,
        le=873000,
        description="Amount paid in August 2005 (NT$)",
    )
    PAY_AMT3: StrictInt = Field(
        ...,
        ge=0,
        le=873000,
        description="Amount paid in July 2005 (NT$)",
    )
    PAY_AMT4: StrictInt = Field(
        ...,
        ge=0,
        le=873000,
        description="Amount paid in June 2005 (NT$)",
    )
    PAY_AMT5: StrictInt = Field(
        ...,
        ge=0,
        le=873000,
        description="Amount paid in May 2005 (NT$)",
    )
    PAY_AMT6: StrictInt = Field(
        ...,
        ge=0,
        le=873000,
        description="Amount paid in April 2005 (NT$)",
    )

    class Config:
        extra = "forbid"
        schema_extra = {
            "example": {
                "model_id": "uci_taiwan_xgb",
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
        }


class FeatureContribution(BaseModel):
    """Single feature contribution to prediction."""

    feature: str = Field(..., description="Feature name")
    contribution: float = Field(..., description="SHAP value or contribution score")
    direction: str = Field(..., description="increases_risk or decreases_risk")


class PredictionResponse(BaseModel):
    """Standardized prediction response."""

    model_id: str = Field(..., description="Model identifier used for prediction")
    dataset_id: str = Field(..., description="Dataset identifier")
    dataset_name: str = Field(..., description="Dataset name")
    geography: str = Field(..., description="Geography of training data")
    target: str = Field(..., description="Target variable name")
    target_meaning: str = Field(..., description="Meaning of target values")
    prediction_timestamp: str = Field(
        ...,
        description="ISO timestamp of prediction",
        example="2026-10-17T10:30:00Z",
    )
    predicted_class: str = Field(
        ...,
        description="Predicted class label",
        example="Default risk",
    )
    probability: confloat(ge=0.0, le=1.0) = Field(
        ...,
        description="Predicted probability of positive class (default)",
    )
    risk_category: str = Field(
        ...,
        description="Risk category based on threshold",
        example="Medium",
    )
    threshold: float = Field(
        ...,
        description="Decision threshold used for class assignment",
        example=0.5,
    )
    calibrated: bool = Field(
        ...,
        description="Whether probability was calibrated",
    )
    calibration_method: Optional[str] = Field(
        None,
        description="Calibration method if applicable",
    )
    limitations: List[str] = Field(
        ...,
        description="List of model limitations and caveats",
    )
    feature_contributions: Optional[List[FeatureContribution]] = Field(
        None,
        description="Feature contributions if explanations available",
    )

    class Config:
        schema_extra = {
            "example": {
                "model_id": "uci_taiwan_xgb",
                "dataset_id": "DS003",
                "dataset_name": "Default of Credit Card Clients",
                "geography": "Taiwan",
                "target": "default payment next month",
                "target_meaning": "1 = Default next month, 0 = Repaid",
                "prediction_timestamp": "2026-10-17T10:30:00Z",
                "predicted_class": "Lower predicted default risk",
                "probability": 0.342,
                "risk_category": "Low",
                "threshold": 0.5,
                "calibrated": True,
                "calibration_method": "Platt sigmoid",
                "limitations": [
                    "Taiwan credit card data from 2005",
                    "Not validated for Indian borrowers",
                ],
                "feature_contributions": [
                    {
                        "feature": "LIMIT_BAL",
                        "contribution": -0.15,
                        "direction": "decreases_risk",
                    }
                ],
            }
        }


class ModelInfoResponse(BaseModel):
    """Model information response."""

    model_id: str
    dataset_id: str
    dataset_name: str
    geography: str
    time_coverage: str
    target: str
    target_meaning: str
    target_prevalence: str
    feature_count: int
    model_type: str
    training_date: str
    test_roc_auc: Optional[float] = None
    test_pr_auc: Optional[float] = None
    calibration_status: str
    calibration_method: Optional[str] = None
    limitations: List[str]
    inference_ready: bool
    shap_available: bool
    source: str
    source_url: str
    license: str
    artifact_exists: bool
    calibration_exists: bool
    feature_names_exist: bool
    metadata_exists: bool


class FeatureField(BaseModel):
    """Single feature field schema."""

    type: str = Field(..., description="Feature type: numeric or categorical")
    description: str = Field(..., description="Feature description")
    required: bool = Field(..., description="Whether field is required")
    unit: Optional[str] = Field(None, description="Unit if numeric")
    range: Optional[List[float]] = Field(None, description="Valid range if numeric")
    values: Optional[List[int]] = Field(None, description="Valid values if categorical")
    value_labels: Optional[Dict[int, str]] = Field(None, description="Value labels if categorical")


class FeatureSchemaResponse(BaseModel):
    """Feature schema response."""

    model_id: str
    raw_features: Dict[str, FeatureField]
    engineered_features: List[str]
    total_feature_count: int
    note: Optional[str] = None
