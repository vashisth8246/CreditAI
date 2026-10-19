"""Tests for Phase 8 features: evaluation endpoints, system status, calibration, and SHAP explanations."""
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.inference.predictor import predict

client = TestClient(app)

SAMPLE_BORROWER = {
    "LIMIT_BAL": 120000,
    "SEX": 2,
    "EDUCATION": 2,
    "MARRIAGE": 1,
    "AGE": 32,
    "PAY_0": 0,
    "PAY_2": 0,
    "PAY_3": 0,
    "PAY_4": 0,
    "PAY_5": 0,
    "PAY_6": 0,
    "BILL_AMT1": 25000,
    "BILL_AMT2": 24000,
    "BILL_AMT3": 23000,
    "BILL_AMT4": 22000,
    "BILL_AMT5": 21000,
    "BILL_AMT6": 20000,
    "PAY_AMT1": 3000,
    "PAY_AMT2": 3000,
    "PAY_AMT3": 3000,
    "PAY_AMT4": 3000,
    "PAY_AMT5": 3000,
    "PAY_AMT6": 3000,
}

HIGH_RISK_BORROWER = {
    "LIMIT_BAL": 20000,
    "SEX": 1,
    "EDUCATION": 3,
    "MARRIAGE": 2,
    "AGE": 25,
    "PAY_0": 3,
    "PAY_2": 3,
    "PAY_3": 3,
    "PAY_4": 3,
    "PAY_5": 3,
    "PAY_6": 3,
    "BILL_AMT1": 20000,
    "BILL_AMT2": 20000,
    "BILL_AMT3": 20000,
    "BILL_AMT4": 20000,
    "BILL_AMT5": 20000,
    "BILL_AMT6": 20000,
    "PAY_AMT1": 0,
    "PAY_AMT2": 0,
    "PAY_AMT3": 0,
    "PAY_AMT4": 0,
    "PAY_AMT5": 0,
    "PAY_AMT6": 0,
}


class TestPhase8SystemStatus:
    """Test /v1/status endpoint and operational status separation."""

    def test_status_endpoint_returns_separated_dimensions(self):
        response = client.get("/v1/status")
        assert response.status_code == 200
        data = response.json()

        assert data["backend_connectivity"] == "connected"
        assert data["models_registered"] >= 1
        assert data["research_inference_ready"] is True
        # CRITICAL: Indian production scoring must be strictly not_validated
        assert data["indian_production_scoring"] == "not_validated"


class TestPhase8ModelEvaluation:
    """Test /v1/models/{model_id}/evaluation endpoint and artifact integrity."""

    def test_evaluation_endpoint_returns_verified_artifacts(self):
        response = client.get("/v1/models/uci_taiwan_xgb/evaluation")
        assert response.status_code == 200
        eval_data = response.json()

        # Check metadata
        meta = eval_data["metadata"]
        assert meta["dataset_id"] == "DS003"
        assert meta["geography"] == "Taiwan"
        assert meta["target"] == "default payment next month"
        assert meta["test_sample_count"] == 4500

        # Check summary metrics match verified Phase 1 reproduction
        summary = eval_data["summary_metrics"]
        assert round(summary["test_roc_auc"], 4) == 0.7807
        assert round(summary["test_pr_auc"], 4) == 0.5588
        assert summary["brier_score_calibrated"] < summary["brier_score_raw"]

        # Check ROC curve points
        roc = eval_data["curves"]["roc"]["points"]
        assert len(roc) > 10
        assert roc[0]["x"] == 0.0 and roc[0]["y"] == 0.0
        assert roc[-1]["x"] == 1.0 and roc[-1]["y"] == 1.0

        # Check PR curve points
        pr = eval_data["curves"]["pr"]["points"]
        assert len(pr) > 10

        # Check calibration curve bins
        cal_bins = eval_data["curves"]["calibration"]["bins"]
        assert len(cal_bins) == 10
        for b in cal_bins:
            assert "bin" in b
            assert "pred_cal" in b
            assert "true_cal" in b

        # Check threshold sweep
        thresholds = eval_data["curves"]["threshold_sweep"]
        assert len(thresholds) >= 15
        assert any(t["threshold"] == 0.5 for t in thresholds)

        # Check risk deciles
        deciles = eval_data["risk_deciles"]
        assert len(deciles) == 10
        # Decile 1 is top risk decile (highest default rate), Decile 10 is lowest risk
        assert deciles[0]["empirical_default_rate"] > deciles[-1]["empirical_default_rate"]

        # Check multi-model comparison
        models = eval_data["model_comparison"]
        assert len(models) >= 4
        xgb_entry = next((m for m in models if m["model_name"] == "XGBoost (Calibrated)"), None)
        assert xgb_entry is not None
        assert round(xgb_entry["roc_auc"], 4) == 0.7807

    def test_evaluation_endpoint_handles_unknown_model(self):
        response = client.get("/v1/models/non_existent_model/evaluation")
        assert response.status_code == 404


class TestPhase8PredictionAndCalibration:
    """Test real calibrated prediction and SHAP explanation generation."""

    def test_prediction_returns_calibrated_probability(self):
        result = predict("uci_taiwan_xgb", SAMPLE_BORROWER)

        assert result.model_id == "uci_taiwan_xgb"
        assert result.calibrated is True
        assert 0.0 <= result.probability <= 1.0
        assert result.risk_category in ("Low", "Medium", "High")

        # Provenance checks
        assert result.dataset_id == "DS003"
        assert result.geography == "Taiwan"
        assert len(result.limitations) > 0

    def test_prediction_generates_shap_explanations(self):
        result = predict("uci_taiwan_xgb", SAMPLE_BORROWER)

        assert result.feature_contributions is not None
        assert len(result.feature_contributions) > 0

        # Features should have positive or negative attributions
        for factor in result.feature_contributions:
            assert factor.feature
            assert isinstance(factor.contribution, float)
            assert factor.direction in ("increases_risk", "decreases_risk")

    def test_high_risk_borrower_scores_higher_than_low_risk(self):
        low_res = predict("uci_taiwan_xgb", SAMPLE_BORROWER)
        high_res = predict("uci_taiwan_xgb", HIGH_RISK_BORROWER)

        assert high_res.probability > low_res.probability
        # High risk borrower has severe delinquency
        assert high_res.probability > 0.30

    def test_api_predict_endpoint_full_contract(self):
        payload = {
            "model_id": "uci_taiwan_xgb",
            "features": SAMPLE_BORROWER,
        }
        response = client.post("/v1/predict", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["model_id"] == "uci_taiwan_xgb"
        assert "predicted_class" in data
        assert 0.0 <= data["probability"] <= 1.0
        assert data["calibrated"] is True
        assert data["geography"] == "Taiwan"
        assert data["feature_contributions"] is not None
        assert len(data["feature_contributions"]) > 0
