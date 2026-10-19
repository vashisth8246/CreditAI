"""Run reproducible prediction test cases for Phase 9 audit."""
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from inference import predict


def run_test_cases():
    """Run all test cases and record predictions."""
    test_cases_path = Path(__file__).parent.parent / "reports" / "phase_9_prediction_test_cases.csv"
    output_path = Path(__file__).parent.parent / "reports" / "phase_9_prediction_test_results.csv"

    # Load test cases
    df = pd.read_csv(test_cases_path)

    results = []

    for idx, row in df.iterrows():
        test_case_id = row["test_case_id"]
        profile_type = row["profile_type"]

        # Skip if already has results
        if row["status"] == "COMPLETED":
            print(f"Skipping {test_case_id} (already completed)")
            continue

        # Build feature dict
        features = {
            "LIMIT_BAL": int(row["LIMIT_BAL"]),
            "SEX": int(row["SEX"]),
            "EDUCATION": int(row["EDUCATION"]),
            "MARRIAGE": int(row["MARRIAGE"]),
            "AGE": int(row["AGE"]),
            "PAY_0": int(row["PAY_0"]),
            "PAY_2": int(row["PAY_2"]),
            "PAY_3": int(row["PAY_3"]),
            "PAY_4": int(row["PAY_4"]),
            "PAY_5": int(row["PAY_5"]),
            "PAY_6": int(row["PAY_6"]),
            "BILL_AMT1": int(row["BILL_AMT1"]),
            "BILL_AMT2": int(row["BILL_AMT2"]),
            "BILL_AMT3": int(row["BILL_AMT3"]),
            "BILL_AMT4": int(row["BILL_AMT4"]),
            "BILL_AMT5": int(row["BILL_AMT5"]),
            "BILL_AMT6": int(row["BILL_AMT6"]),
            "PAY_AMT1": int(row["PAY_AMT1"]),
            "PAY_AMT2": int(row["PAY_AMT2"]),
            "PAY_AMT3": int(row["PAY_AMT3"]),
            "PAY_AMT4": int(row["PAY_AMT4"]),
            "PAY_AMT5": int(row["PAY_AMT5"]),
            "PAY_AMT6": int(row["PAY_AMT6"]),
        }

        # Modify invalid test cases to trigger validation errors
        if profile_type == "invalid_categorical_low":
            features["SEX"] = 0  # Invalid (must be 1 or 2)
        elif profile_type == "invalid_categorical_high":
            features["SEX"] = 99  # Invalid (must be 1 or 2)

        try:
            # Run prediction
            result = predict("uci_taiwan_xgb", features)

            # Record results
            row_copy = row.copy()
            row_copy["raw_probability"] = None  # Not exposed in response
            row_copy["calibrated_probability"] = result.probability
            row_copy["predicted_class"] = result.predicted_class
            row_copy["risk_category"] = result.risk_category
            row_copy["threshold"] = result.threshold
            row_copy["calibration_method"] = result.calibration_method
            row_copy["status"] = "COMPLETED"

            print(f"✓ {test_case_id}: {profile_type} -> {result.probability:.4f} ({result.risk_category})")

        except Exception as e:
            # Record error
            row_copy = row.copy()
            row_copy["calibrated_probability"] = None
            row_copy["predicted_class"] = f"ERROR: {str(e)}"
            row_copy["risk_category"] = "ERROR"
            row_copy["status"] = "FAILED"

            print(f"✗ {test_case_id}: {profile_type} -> ERROR: {str(e)}")

        results.append(row_copy)

    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(output_path, index=False)
    print(f"\nResults saved to {output_path}")

    return results_df


if __name__ == "__main__":
    run_test_cases()
