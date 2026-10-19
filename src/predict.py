"""
CreditAI: Single Borrower Prediction & Explainability Module
Loads the serialized Stage 1 ML model pipeline, accepts raw borrower features,
applies the full preprocessing and feature engineering transforms, and computes
the calibrated Probability of Default (PD) alongside top SHAP risk drivers.
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

from src.config import (
    SAVED_MODEL_PATH,
    FEATURE_NAMES_PATH,
    MODEL_METADATA_PATH,
    RAW_FEATURE_COLUMNS,
)
from src.preprocessing import clean_categorical_features
from src.feature_engineering import engineer_credit_features


class CreditAIPredictor:
    """
    Inference engine for CreditAI Phase 1.
    Loads trained models and executes inference on raw borrower feature dictionaries.
    """

    def __init__(self, model_bundle_path: Path | str | None = None):
        if model_bundle_path is None:
            model_bundle_path = SAVED_MODEL_PATH
        self.model_bundle_path = Path(model_bundle_path)

        if not self.model_bundle_path.exists():
            raise FileNotFoundError(
                f"[CreditAI Predictor] Model file not found at: {self.model_bundle_path}.\n"
                "Please run `python -m src.train` first to train and save the model."
            )

        print(f"[CreditAI Predictor] Loading model artifacts from: {self.model_bundle_path}...")
        self.bundle = joblib.load(self.model_bundle_path)
        self.base_model = self.bundle["base_model"]
        self.calibrated_model = self.bundle.get("calibrated_model", self.base_model)
        self.feature_names = self.bundle["feature_names"]
        self.model_name = self.bundle.get("model_name", "CreditAI Classifier")

        # Load metadata if available
        self.metadata = {}
        if MODEL_METADATA_PATH.exists():
            with open(MODEL_METADATA_PATH, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)

    def predict_single_borrower(
        self, borrower_dict: dict, include_shap: bool = False
    ) -> dict:
        """
        Executes prediction on a single borrower record.
        
        Parameters:
        -----------
        borrower_dict : dict
            Dictionary mapping raw feature names to borrower values.
            e.g. {'LIMIT_BAL': 50000, 'SEX': 1, 'EDUCATION': 2, 'PAY_0': 2, ...}
        include_shap : bool, default=False
            Whether to compute local SHAP risk driver explanations.
            
        Returns:
        --------
        dict
            Prediction payload containing Probability of Default, risk classification,
            and optional SHAP explanations.
        """
        # Convert dictionary to single-row DataFrame
        df_single = pd.DataFrame([borrower_dict])

        # Step 1: Categorical standardization
        df_clean = clean_categorical_features(df_single, verbose=False)

        # Step 2: Ensure all required raw features exist
        for col in RAW_FEATURE_COLUMNS:
            if col not in df_clean.columns:
                # Default to 0 if a feature is omitted
                df_clean[col] = 0.0
            else:
                df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce").fillna(0.0)

        # Step 3: Feature Engineering
        df_engineered = engineer_credit_features(df_clean, verbose=False)

        # Step 4: Align columns to exact feature set used during training
        X_aligned = df_engineered.reindex(columns=self.feature_names, fill_value=0.0)

        # Step 5: Probability of Default prediction (using calibrated model)
        pd_prob = float(self.calibrated_model.predict_proba(X_aligned)[0, 1])

        # Binary decision threshold (0.5 default)
        threshold = 0.5
        prediction_label = "High Default Risk" if pd_prob >= threshold else "Low Default Risk"

        result = {
            "risk_probability": round(pd_prob, 4),
            "probability_percentage": f"{pd_prob * 100:.2f}%",
            "model": self.model_name,
            "prediction": prediction_label,
            "threshold": threshold,
        }

        # Step 6: Optional SHAP feature attributions
        if include_shap:
            try:
                import shap

                explainer = shap.TreeExplainer(self.base_model)
                shap_vals = explainer.shap_values(X_aligned)
                if isinstance(shap_vals, list):
                    shap_vals = shap_vals[1]
                shap_vals = shap_vals.flatten()

                shap_df = pd.DataFrame({
                    "feature": self.feature_names,
                    "value": X_aligned.values.flatten(),
                    "impact": shap_vals,
                })

                top_increasing = (
                    shap_df.sort_values(by="impact", ascending=False)
                    .head(3)
                    .to_dict(orient="records")
                )
                top_decreasing = (
                    shap_df.sort_values(by="impact", ascending=True)
                    .head(3)
                    .to_dict(orient="records")
                )

                result["shap_explanations"] = {
                    "top_risk_increasing": top_increasing,
                    "top_risk_decreasing": top_decreasing,
                }
            except Exception as e:
                result["shap_explanations"] = f"SHAP calculation unavailable: {e}"

        return result


def get_sample_borrower_high_risk() -> dict:
    """Returns a realistic high-risk borrower profile (recent delinquency, high utilization)."""
    return {
        "LIMIT_BAL": 30000.0,
        "SEX": 2,
        "EDUCATION": 2,
        "MARRIAGE": 1,
        "AGE": 28,
        "PAY_0": 2,  # 2 months delay in September
        "PAY_2": 2,  # 2 months delay in August
        "PAY_3": 1,
        "PAY_4": 0,
        "PAY_5": 0,
        "PAY_6": 0,
        "BILL_AMT1": 29500.0,  # ~98% utilization
        "BILL_AMT2": 28900.0,
        "BILL_AMT3": 27000.0,
        "BILL_AMT4": 25000.0,
        "BILL_AMT5": 20000.0,
        "BILL_AMT6": 18000.0,
        "PAY_AMT1": 500.0,     # Small token payment
        "PAY_AMT2": 0.0,
        "PAY_AMT3": 1000.0,
        "PAY_AMT4": 1000.0,
        "PAY_AMT5": 1000.0,
        "PAY_AMT6": 1000.0,
    }


def get_sample_borrower_low_risk() -> dict:
    """Returns a realistic low-risk borrower profile (clean payment history, low utilization)."""
    return {
        "LIMIT_BAL": 250000.0,
        "SEX": 1,
        "EDUCATION": 1,
        "MARRIAGE": 2,
        "AGE": 38,
        "PAY_0": -1,  # Paid in full
        "PAY_2": -1,
        "PAY_3": -1,
        "PAY_4": 0,
        "PAY_5": 0,
        "PAY_6": -1,
        "BILL_AMT1": 15000.0,  # ~6% utilization
        "BILL_AMT2": 18000.0,
        "BILL_AMT3": 12000.0,
        "BILL_AMT4": 14000.0,
        "BILL_AMT5": 9000.0,
        "BILL_AMT6": 11000.0,
        "PAY_AMT1": 15000.0,   # Full balance paid
        "PAY_AMT2": 18000.0,
        "PAY_AMT3": 12000.0,
        "PAY_AMT4": 14000.0,
        "PAY_AMT5": 9000.0,
        "PAY_AMT6": 11000.0,
    }


if __name__ == "__main__":
    import pprint

    try:
        predictor = CreditAIPredictor()
        print("\n=== RUNNING PREDICTION ON SAMPLE HIGH-RISK BORROWER ===")
        high_risk_input = get_sample_borrower_high_risk()
        result_high = predictor.predict_single_borrower(high_risk_input, include_shap=True)
        pprint.pprint(result_high)

        print("\n=== RUNNING PREDICTION ON SAMPLE LOW-RISK BORROWER ===")
        low_risk_input = get_sample_borrower_low_risk()
        result_low = predictor.predict_single_borrower(low_risk_input, include_shap=True)
        pprint.pprint(result_low)
    except FileNotFoundError as err:
        print(f"\n[Info] {err}")
