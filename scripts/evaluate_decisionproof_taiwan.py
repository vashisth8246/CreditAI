"""Sensitivity replay on the previously reconstructed Taiwan holdout, separate from synthetic policy."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from sklearn.metrics import brier_score_loss, log_loss

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_confidence_guardian import split_indices
from src.data_loader import load_uci_credit_card_data
from src.inference.guardian import DATASET_SHA, assess, load_reference
from src.inference.predictor import apply_calibration, apply_feature_engineering, load_calibration_model, load_model_and_preprocessing
from src.preprocessing import preprocess_data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if hashlib.sha256(args.workbook.read_bytes()).hexdigest() != DATASET_SHA:
        raise SystemExit("Workbook SHA-256 mismatch")
    raw = load_uci_credit_card_data(args.workbook, verbose=False)
    X, y = preprocess_data(raw, verbose=False)
    _, _, test = split_indices(y)
    reference = load_reference()
    if not reference or hashlib.sha256(np.asarray(test, dtype="<i8").tobytes()).hexdigest() != reference["split"]["index_sha256"]["test"]:
        raise SystemExit("Held-out split fingerprint or Guardian reference unavailable")
    rows = raw[X.columns].iloc[test].to_dict("records")
    original, indices = [], []
    for index, row in enumerate(rows):
        clean, _ = assess(row)
        if clean is not None:
            original.append(clean)
            indices.append(index)
    observed = y.iloc[test].to_numpy()[indices]
    bundle, names = load_model_and_preprocessing("uci_taiwan_xgb")
    estimator = bundle["base_model"] if isinstance(bundle, dict) else bundle
    calibrator = load_calibration_model("uci_taiwan_xgb")

    def measure(profiles):
        values = [apply_feature_engineering(profile) for profile in profiles]
        matrix = np.array([[row[name] for name in names] for row in values])
        prob = np.array([apply_calibration(float(p), calibrator) for p in estimator.predict_proba(matrix)[:, 1]])
        statuses = [assess(row)[1]["status"] for row in profiles]
        review = sum(status != "review_eligible" for status in statuses)
        return prob, dict(error_rate=float(((prob >= .5) != observed).mean()),
                          brier=float(brier_score_loss(observed, prob)), log_loss=float(log_loss(observed, prob)),
                          guardian_review=review, guardian_eligible=len(prob)-review)

    base, baseline = measure(original)
    variants = {
        "pay0_one_code_lower": [row | {"PAY_0": max(-2, row["PAY_0"] - 1)} for row in original],
        "pay0_one_code_higher": [row | {"PAY_0": min(9, row["PAY_0"] + 1)} for row in original],
        "credit_limit_minus_10pct": [row | {"LIMIT_BAL": row["LIMIT_BAL"] * 9 // 10} for row in original],
        "credit_limit_plus_10pct": [row | {"LIMIT_BAL": min(1_000_000, row["LIMIT_BAL"] * 11 // 10)} for row in original],
    }
    outputs = {}
    for name, profiles in variants.items():
        prob, metrics = measure(profiles)
        outputs[name] = metrics | {
            "mean_absolute_probability_change": float(np.abs(prob-base).mean()),
            "classification_reversals_at_0_5": int(((prob >= .5) != (base >= .5)).sum()),
            "changed_input_count": sum(a != b for a, b in zip(original, profiles)),
        }
    artifact = dict(dataset_sha256=DATASET_SHA, heldout=len(test), schema_valid=len(original),
                    baseline=baseline, variants=outputs,
                    limitation="Original labels are used for a sensitivity replay, not labels for the perturbed inputs. No causal, document-verification, or Indian affordability claim.")
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(artifact, indent=2))


if __name__ == "__main__":
    main()
