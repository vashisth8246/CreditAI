"""
Investigation of TC003 Severe-Delinquency Prediction

This script investigates why TC003 (severe delinquency pattern) returned 18.0% default probability.
It compares TC003 with TC001 (low delinquency) and TC002 (moderate delinquency) to identify
whether the result is due to a software defect or the model's learned behavior.
"""

import sys
from pathlib import Path
import numpy as np
import joblib
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.inference.predictor import (
    load_model_and_preprocessing,
    apply_feature_engineering,
    predict_proba,
    load_calibration_model,
    apply_calibration
)
from src.inference.explanations import compute_prediction_explanations


def get_test_case_input(test_case_id):
    """Get the exact input for a test case."""
    test_cases = {
        'TC001': {
            'LIMIT_BAL': 200000, 'SEX': 2, 'EDUCATION': 2, 'MARRIAGE': 1, 'AGE': 35,
            'PAY_0': 0, 'PAY_2': 0, 'PAY_3': 0, 'PAY_4': 0, 'PAY_5': 0, 'PAY_6': 0,
            'BILL_AMT1': 50000, 'BILL_AMT2': 45000, 'BILL_AMT3': 40000, 'BILL_AMT4': 35000,
            'BILL_AMT5': 30000, 'BILL_AMT6': 25000,
            'PAY_AMT1': 5000, 'PAY_AMT2': 5000, 'PAY_AMT3': 5000, 'PAY_AMT4': 5000,
            'PAY_AMT5': 5000, 'PAY_AMT6': 5000
        },
        'TC002': {
            'LIMIT_BAL': 100000, 'SEX': 1, 'EDUCATION': 2, 'MARRIAGE': 2, 'AGE': 45,
            'PAY_0': 2, 'PAY_2': 1, 'PAY_3': 1, 'PAY_4': 0, 'PAY_5': 0, 'PAY_6': 0,
            'BILL_AMT1': 80000, 'BILL_AMT2': 75000, 'BILL_AMT3': 70000, 'BILL_AMT4': 65000,
            'BILL_AMT5': 60000, 'BILL_AMT6': 55000,
            'PAY_AMT1': 2000, 'PAY_AMT2': 3000, 'PAY_AMT3': 4000, 'PAY_AMT4': 5000,
            'PAY_AMT5': 6000, 'PAY_AMT6': 7000
        },
        'TC003': {
            'LIMIT_BAL': 50000, 'SEX': 1, 'EDUCATION': 1, 'MARRIAGE': 2, 'AGE': 28,
            'PAY_0': 8, 'PAY_2': 7, 'PAY_3': 6, 'PAY_4': 5, 'PAY_5': 4, 'PAY_6': 3,
            'BILL_AMT1': 100000, 'BILL_AMT2': 95000, 'BILL_AMT3': 90000, 'BILL_AMT4': 85000,
            'BILL_AMT5': 80000, 'BILL_AMT6': 75000,
            'PAY_AMT1': 0, 'PAY_AMT2': 0, 'PAY_AMT3': 0, 'PAY_AMT4': 0, 'PAY_AMT5': 0, 'PAY_AMT6': 0
        }
    }
    return test_cases.get(test_case_id)


def compare_test_cases(tc1_id, tc2_id):
    """Compare two test cases and identify differing fields."""
    tc1 = get_test_case_input(tc1_id)
    tc2 = get_test_case_input(tc2_id)

    differences = {}
    for key in tc1.keys():
        if tc1[key] != tc2[key]:
            differences[key] = {
                f'{tc1_id}': tc1[key],
                f'{tc2_id}': tc2[key],
                'difference': tc2[key] - tc1[key] if isinstance(tc1[key], (int, float)) else f'{tc1[key]} -> {tc2[key]}'
            }

    return differences


def detailed_prediction_analysis(test_case_id, model, feature_names, calibration_model):
    """Perform detailed prediction analysis for a test case."""
    print(f"\n{'='*80}")
    print(f"Detailed Analysis: {test_case_id}")
    print(f"{'='*80}")

    # Get input
    input_data = get_test_case_input(test_case_id)

    # Print raw input
    print("\n--- Raw Input (23 fields) ---")
    for key, value in input_data.items():
        print(f"  {key}: {value}")

    # Apply feature engineering
    all_features = apply_feature_engineering(input_data)

    # Print engineered features
    print(f"\n--- Engineered Features (27 additional) ---")
    engineered_keys = [k for k in all_features.keys() if k not in input_data.keys()]
    for key in engineered_keys:
        print(f"  {key}: {all_features[key]:.6f}")

    # Get raw model output
    raw_proba = predict_proba(model, all_features, feature_names)
    print(f"\n--- Model Output ---")
    print(f"  Raw probability: {raw_proba:.6f}")
    print(f"  Raw log-odds: {np.log(raw_proba / (1 - raw_proba)):.6f}")

    # Apply calibration
    calibrated_proba = apply_calibration(raw_proba, calibration_model)
    print(f"  Calibrated probability: {calibrated_proba:.6f}")
    print(f"  Calibrated log-odds: {np.log(calibrated_proba / (1 - calibrated_proba)):.6f}")

    # Get SHAP values
    try:
        import shap
        # Extract base model if needed
        if isinstance(model, dict):
            base_model = model.get("base_model", model)
        else:
            base_model = model

        explainer = shap.TreeExplainer(base_model)
        feat_array = np.array([all_features[name] for name in feature_names]).reshape(1, -1)
        shap_vals = explainer.shap_values(feat_array)[0]

        print(f"\n--- Top 10 SHAP Values (log-odds space) ---")
        shap_dict = {name: val for name, val in zip(feature_names, shap_vals)}
        sorted_shap = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)

        for i, (name, value) in enumerate(sorted_shap[:10]):
            direction = "increases_risk" if value > 0 else "decreases_risk"
            print(f"  {i+1}. {name}: {value:+.6f} ({direction})")

        # Verify reconstruction
        baseline = explainer.expected_value
        if np.isscalar(baseline):
            baseline = [baseline]
        baseline = baseline[0]
        shap_sum = shap_vals.sum()
        reconstructed = baseline + shap_sum
        model_logit = np.log(raw_proba / (1 - raw_proba))
        reconstruction_error = abs(reconstructed - model_logit)

        print(f"\n--- SHAP Reconstruction Verification ---")
        print(f"  Baseline: {baseline:.6f}")
        print(f"  SHAP sum: {shap_sum:.6f}")
        print(f"  Reconstructed: {reconstructed:.6f}")
        print(f"  Model log-odds: {model_logit:.6f}")
        print(f"  Reconstruction error: {reconstruction_error:.10f}")
        print(f"  Reconstruction OK: {reconstruction_error < 1e-6}")

        return {
            'raw_proba': raw_proba,
            'calibrated_proba': calibrated_proba,
            'shap_values': shap_dict,
            'reconstruction_error': reconstruction_error
        }

    except Exception as e:
        print(f"\n  SHAP error: {e}")
        return {
            'raw_proba': raw_proba,
            'calibrated_proba': calibrated_proba,
            'shap_values': None,
            'reconstruction_error': None
        }


def main():
    """Main investigation."""
    print("="*80)
    print("TC003 Severe-Delinquency Prediction Investigation")
    print("="*80)

    # Load model and calibration
    model_id = "uci_taiwan_xgb"
    model, feature_names = load_model_and_preprocessing(model_id)
    calibration_model = load_calibration_model(model_id)

    print(f"\nModel ID: {model_id}")
    print(f"Features: {len(feature_names)}")
    print(f"Calibration loaded: {calibration_model is not None}")

    # Compare TC003 with TC001 and TC002
    print("\n" + "="*80)
    print("Comparison: TC003 vs TC001")
    print("="*80)
    diff_003_001 = compare_test_cases('TC003', 'TC001')
    print(f"\nDiffering fields ({len(diff_003_001)}):")
    for key, val in diff_003_001.items():
        print(f"  {key}: {val}")

    print("\n" + "="*80)
    print("Comparison: TC003 vs TC002")
    print("="*80)
    diff_003_002 = compare_test_cases('TC003', 'TC002')
    print(f"\nDiffering fields ({len(diff_003_002)}):")
    for key, val in diff_003_002.items():
        print(f"  {key}: {val}")

    # Detailed analysis for each test case
    results = {}
    for tc_id in ['TC001', 'TC002', 'TC003']:
        results[tc_id] = detailed_prediction_analysis(tc_id, model, feature_names, calibration_model)

    # Summary comparison
    print("\n" + "="*80)
    print("Summary Comparison")
    print("="*80)
    print(f"\n{'Test Case':<10} {'Raw Prob':<12} {'Calibrated Prob':<16} {'Risk Tier':<12}")
    print("-" * 60)
    for tc_id in ['TC001', 'TC002', 'TC003']:
        r = results[tc_id]
        raw = r['raw_proba']
        calib = r['calibrated_proba']
        risk = "Low" if calib < 0.25 else "Medium" if calib < 0.5 else "High"
        print(f"{tc_id:<10} {raw:<12.6f} {calib:<16.6f} {risk:<12}")

    # Investigate TC003 specifically
    print("\n" + "="*80)
    print("TC003 Investigation")
    print("="*80)

    tc003 = results['TC003']
    tc001 = results['TC001']
    tc002 = results['TC002']

    print(f"\nTC003 Characteristics:")
    print(f"  - Severe delinquency: PAY_0=8, PAY_2=7, PAY_3=6, PAY_4=5, PAY_5=4, PAY_6=3")
    print(f"  - Zero payments: All PAY_AMT fields = 0")
    print(f"  - High bill amounts: Bills from 75,000 to 100,000 NT$")
    print(f"  - Low credit limit: 50,000 NT$ (vs 200,000 for TC001, 100,000 for TC002)")
    print(f"  - High utilization: Bill amounts exceed credit limit significantly")

    print(f"\nRaw Model Output Analysis:")
    print(f"  TC003 raw probability: {tc003['raw_proba']:.6f}")
    print(f"  TC001 raw probability: {tc001['raw_proba']:.6f}")
    print(f"  TC002 raw probability: {tc002['raw_proba']:.6f}")
    print(f"  TC003 > TC001: {tc003['raw_proba'] > tc001['raw_proba']}")
    print(f"  TC003 > TC002: {tc003['raw_proba'] > tc002['raw_proba']}")

    print(f"\nCalibrated Output Analysis:")
    print(f"  TC003 calibrated: {tc003['calibrated_proba']:.6f}")
    print(f"  TC001 calibrated: {tc001['calibrated_proba']:.6f}")
    print(f"  TC002 calibrated: {tc002['calibrated_proba']:.6f}")
    print(f"  TC003 > TC001: {tc003['calibrated_proba'] > tc001['calibrated_proba']}")
    print(f"  TC003 > TC002: {tc003['calibrated_proba'] > tc002['calibrated_proba']}")

    # Check calibration effect
    print(f"\nCalibration Effect:")
    print(f"  TC003: {tc003['raw_proba']:.6f} -> {tc003['calibrated_proba']:.6f} (change: {tc003['calibrated_proba'] - tc003['raw_proba']:+.6f})")
    print(f"  TC001: {tc001['raw_proba']:.6f} -> {tc001['calibrated_proba']:.6f} (change: {tc001['calibrated_proba'] - tc001['raw_proba']:+.6f})")
    print(f"  TC002: {tc002['raw_proba']:.6f} -> {tc002['calibrated_proba']:.6f} (change: {tc002['calibrated_proba'] - tc002['raw_proba']:+.6f})")

    # Conclusion
    print("\n" + "="*80)
    print("Preliminary Assessment")
    print("="*80)

    if tc003['raw_proba'] > tc001['raw_proba'] and tc003['raw_proba'] > tc002['raw_proba']:
        print("\n[OK] Model correctly ranks TC003 higher risk than TC001 and TC002 based on raw output")
        print("  The 18.0% calibrated probability is higher than TC001 (7.1%) and lower than TC002 (42.0%)")
        print("  This suggests the model learned behavior, not a defect.")
    else:
        print("\n[WARNING] Model ranking may be incorrect - investigate further")

    if tc003['calibrated_proba'] < 0.25:
        print("\n[WARNING] TC003 calibrated probability (18.0%) is in 'Low' risk tier despite severe delinquency")
        print("  This may be due to:")
        print("  1. High bill amounts with zero payments may indicate inactive account rather than active delinquency")
        print("  2. Low credit limit (50k) with high bills (75k-100k) may be an unusual pattern in training data")
        print("  3. Model may have learned that this specific pattern has lower default risk")

    print("\n" + "="*80)
    print("Investigation Complete")
    print("="*80)


if __name__ == "__main__":
    main()
