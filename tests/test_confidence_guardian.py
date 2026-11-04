import json
from pathlib import Path

import pandas as pd

from scripts.evaluate_confidence_guardian import cutoff, split_indices
from src.api.app import ReliabilityAssessmentRequest, reliability_assessment, reliability_evaluation
from src.inference import guardian
from src.inference.model_registry import get_feature_schema


def borrower():
    values = {name: 0 for name in get_feature_schema("uci_taiwan_xgb")["raw_features"]}
    return values | {"LIMIT_BAL": 200000, "SEX": 2, "EDUCATION": 2, "MARRIAGE": 1, "AGE": 35}


def test_legitimate_negative_statement_and_zero_payments():
    clean, findings = guardian.check_input(borrower() | {"BILL_AMT1": -2000})
    assert clean["BILL_AMT1"] == -2000 and clean["PAY_AMT1"] == 0
    assert {item["code"] for item in findings} == {"negative_statement"}
    assert not findings[0]["blocks_inference"]


def test_aggregates_errors_without_silent_repairs():
    profile = borrower() | {"PAY_0": 99, "AGE": float("inf"), "SEX": True, "PAY_AMT1": -1}
    del profile["BILL_AMT2"]
    clean, assessment = guardian.assess(profile)
    assert clean is None and assessment["status"] == "input_correction_required"
    assert {item["field"]: item["code"] for item in assessment["findings"]} == {
        "SEX": "invalid_number", "AGE": "invalid_number", "PAY_0": "invalid_code",
        "BILL_AMT2": "missing", "PAY_AMT1": "out_of_range",
    }
    assert all(item["blocks_inference"] and item["action"] for item in assessment["findings"])


def test_cross_field_warning_and_unusual_valid_reference():
    valid, assessment = guardian.assess(borrower() | {"LIMIT_BAL": 1000000, "PAY_0": 9, "PAY_2": 9})
    assert valid and assessment["status"] == "manual_review_recommended"
    assert assessment["distribution_findings"]
    _, findings = guardian.check_input(borrower() | {"LIMIT_BAL": 20000, "BILL_AMT1": 75000})
    assert findings[0]["code"] == "statement_limit_mismatch" and not findings[0]["blocks_inference"]


def test_reference_unavailable_never_implies_reliability(monkeypatch):
    monkeypatch.setattr(guardian, "load_reference", lambda: None)
    clean, assessment = guardian.assess(borrower())
    assert clean and assessment["status"] == "reliability_not_evaluated"
    assert not assessment["distribution_evaluated"]


def test_invalid_and_unavailable_routes_do_not_produce_a_prediction():
    invalid = reliability_assessment(ReliabilityAssessmentRequest(features=borrower() | {"PAY_0": "99"}))
    assert invalid["prediction"] is None
    assert invalid["assessment"]["status"] == "input_correction_required"
    unavailable = reliability_assessment(ReliabilityAssessmentRequest(model_id="demo-missing", features={}))
    assert unavailable["prediction"] is None and unavailable["assessment"]["status"] == "model_unavailable"


def test_split_reproducibility_and_validation_ties():
    y = pd.Series([0, 1] * 100)
    first = split_indices(y)
    second = split_indices(y)
    assert all(a.tolist() == b.tolist() for a, b in zip(first, second))
    assert [len(part) for part in first] == [140, 30, 30]
    assert len(set.union(*(set(part) for part in first))) == 200
    assert cutoff([0, 1, 1, 2], .5) == 1


def test_frozen_artifact_retention_counts_and_no_label_features():
    artifact = guardian.load_reference()
    assert artifact is not None and reliability_evaluation()["status"] == "evaluated"
    reference_fields = set(artifact["reference"]["continuous"]) | set(artifact["reference"]["categorical"])
    assert reference_fields <= set(get_feature_schema("uci_taiwan_xgb")["raw_features"])
    assert {"ID", "default payment next month", "SEX", "MARRIAGE"}.isdisjoint(reference_fields)
    assert artifact["split"]["train"] == 21000
    assert artifact["split"]["validation"] == artifact["split"]["test"] == 4500
    assert len(set(artifact["split"]["index_sha256"].values())) == 3
    for row in artifact["evaluation"]:
        assert row["retained"] + row["abstained"] == 4500
        assert row["coverage"] == row["retained"] / 4500
        assert sum(item["count"] for item in row["calibration_bins"]) == row["retained"]
    json.loads(Path(guardian.REFERENCE_PATH).read_text(encoding="utf-8"))
