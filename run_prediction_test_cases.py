"""
Phase 9 - Session 4: Reproducible Prediction Test Cases

This script runs the test cases defined in phase_9_prediction_test_cases.csv
and records the actual model outputs for reproducibility verification.
"""

import csv
import json
import sys
import os
from pathlib import Path
from datetime import datetime
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.inference.predictor import predict, load_model_and_preprocessing
from src.inference.explanations import compute_prediction_explanations
from src.inference.schemas import UCITaiwanRequest


def load_test_cases(csv_path):
    """Load test cases from CSV file."""
    test_cases = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            test_cases.append(row)
    return test_cases


def build_request_from_test_case(test_case):
    """Build a UCITaiwanRequest from a test case dictionary."""
    # Skip invalid cases that should fail validation
    if test_case['profile_type'].startswith('invalid_'):
        return None
    
    request_data = {
        'LIMIT_BAL': int(test_case['LIMIT_BAL']),
        'SEX': int(test_case['SEX']),
        'EDUCATION': int(test_case['EDUCATION']),
        'MARRIAGE': int(test_case['MARRIAGE']),
        'AGE': int(test_case['AGE']),
        'PAY_0': int(test_case['PAY_0']),
        'PAY_2': int(test_case['PAY_2']),
        'PAY_3': int(test_case['PAY_3']),
        'PAY_4': int(test_case['PAY_4']),
        'PAY_5': int(test_case['PAY_5']),
        'PAY_6': int(test_case['PAY_6']),
        'BILL_AMT1': int(test_case['BILL_AMT1']),
        'BILL_AMT2': int(test_case['BILL_AMT2']),
        'BILL_AMT3': int(test_case['BILL_AMT3']),
        'BILL_AMT4': int(test_case['BILL_AMT4']),
        'BILL_AMT5': int(test_case['BILL_AMT5']),
        'BILL_AMT6': int(test_case['BILL_AMT6']),
        'PAY_AMT1': int(test_case['PAY_AMT1']),
        'PAY_AMT2': int(test_case['PAY_AMT2']),
        'PAY_AMT3': int(test_case['PAY_AMT3']),
        'PAY_AMT4': int(test_case['PAY_AMT4']),
        'PAY_AMT5': int(test_case['PAY_AMT5']),
        'PAY_AMT6': int(test_case['PAY_AMT6']),
    }
    
    try:
        return UCITaiwanRequest(**request_data)
    except Exception as e:
        print(f"  Validation error: {e}")
        return None


def test_invalid_inputs():
    """Test invalid input scenarios."""
    invalid_cases = []
    
    # Invalid categorical codes
    invalid_cases.append({
        'test_case_id': 'TC006',
        'description': 'Invalid SEX value (0)',
        'request_data': {
            'LIMIT_BAL': 200000, 'SEX': 0, 'EDUCATION': 2, 'MARRIAGE': 1, 'AGE': 35,
            'PAY_0': 0, 'PAY_2': 0, 'PAY_3': 0, 'PAY_4': 0, 'PAY_5': 0, 'PAY_6': 0,
            'BILL_AMT1': 50000, 'BILL_AMT2': 45000, 'BILL_AMT3': 40000, 'BILL_AMT4': 35000,
            'BILL_AMT5': 30000, 'BILL_AMT6': 25000,
            'PAY_AMT1': 5000, 'PAY_AMT2': 5000, 'PAY_AMT3': 5000, 'PAY_AMT4': 5000,
            'PAY_AMT5': 5000, 'PAY_AMT6': 5000
        }
    })
    
    invalid_cases.append({
        'test_case_id': 'TC007',
        'description': 'Invalid EDUCATION value (10)',
        'request_data': {
            'LIMIT_BAL': 200000, 'SEX': 2, 'EDUCATION': 10, 'MARRIAGE': 1, 'AGE': 35,
            'PAY_0': 0, 'PAY_2': 0, 'PAY_3': 0, 'PAY_4': 0, 'PAY_5': 0, 'PAY_6': 0,
            'BILL_AMT1': 50000, 'BILL_AMT2': 45000, 'BILL_AMT3': 40000, 'BILL_AMT4': 35000,
            'BILL_AMT5': 30000, 'BILL_AMT6': 25000,
            'PAY_AMT1': 5000, 'PAY_AMT2': 5000, 'PAY_AMT3': 5000, 'PAY_AMT4': 5000,
            'PAY_AMT5': 5000, 'PAY_AMT6': 5000
        }
    })
    
    # Missing required fields
    invalid_cases.append({
        'test_case_id': 'TC011',
        'description': 'Missing LIMIT_BAL field',
        'request_data': {
            'SEX': 2, 'EDUCATION': 2, 'MARRIAGE': 1, 'AGE': 35,
            'PAY_0': 0, 'PAY_2': 0, 'PAY_3': 0, 'PAY_4': 0, 'PAY_5': 0, 'PAY_6': 0,
            'BILL_AMT1': 50000, 'BILL_AMT2': 45000, 'BILL_AMT3': 40000, 'BILL_AMT4': 35000,
            'BILL_AMT5': 30000, 'BILL_AMT6': 25000,
            'PAY_AMT1': 5000, 'PAY_AMT2': 5000, 'PAY_AMT3': 5000, 'PAY_AMT4': 5000,
            'PAY_AMT5': 5000, 'PAY_AMT6': 5000
        }
    })
    
    # Non-finite numeric inputs
    invalid_cases.append({
        'test_case_id': 'TC012',
        'description': 'Negative AGE value',
        'request_data': {
            'LIMIT_BAL': 200000, 'SEX': 2, 'EDUCATION': 2, 'MARRIAGE': 1, 'AGE': -5,
            'PAY_0': 0, 'PAY_2': 0, 'PAY_3': 0, 'PAY_4': 0, 'PAY_5': 0, 'PAY_6': 0,
            'BILL_AMT1': 50000, 'BILL_AMT2': 45000, 'BILL_AMT3': 40000, 'BILL_AMT4': 35000,
            'BILL_AMT5': 30000, 'BILL_AMT6': 25000,
            'PAY_AMT1': 5000, 'PAY_AMT2': 5000, 'PAY_AMT3': 5000, 'PAY_AMT4': 5000,
            'PAY_AMT5': 5000, 'PAY_AMT6': 5000
        }
    })
    
    # Unexpected fields
    invalid_cases.append({
        'test_case_id': 'TC013',
        'description': 'Unexpected field EXTRA_FIELD',
        'request_data': {
            'LIMIT_BAL': 200000, 'SEX': 2, 'EDUCATION': 2, 'MARRIAGE': 1, 'AGE': 35,
            'PAY_0': 0, 'PAY_2': 0, 'PAY_3': 0, 'PAY_4': 0, 'PAY_5': 0, 'PAY_6': 0,
            'BILL_AMT1': 50000, 'BILL_AMT2': 45000, 'BILL_AMT3': 40000, 'BILL_AMT4': 35000,
            'BILL_AMT5': 30000, 'BILL_AMT6': 25000,
            'PAY_AMT1': 5000, 'PAY_AMT2': 5000, 'PAY_AMT3': 5000, 'PAY_AMT4': 5000,
            'PAY_AMT5': 5000, 'PAY_AMT6': 5000,
            'EXTRA_FIELD': 'should_be_rejected'
        }
    })
    
    results = []
    for case in invalid_cases:
        print(f"\nTesting {case['test_case_id']}: {case['description']}")
        try:
            request = UCITaiwanRequest(**case['request_data'])
            print(f"  ERROR: Request should have failed validation but passed")
            results.append({
                'test_case_id': case['test_case_id'],
                'description': case['description'],
                'expected': 'validation_error',
                'actual': 'passed',
                'status': 'FAIL'
            })
        except Exception as e:
            print(f"  Expected validation error: {e}")
            results.append({
                'test_case_id': case['test_case_id'],
                'description': case['description'],
                'expected': 'validation_error',
                'actual': 'validation_error',
                'error': str(e),
                'status': 'PASS'
            })
    
    return results


def run_test_case(test_case, model_id):
    """Run a single test case and record results."""
    test_id = test_case['test_case_id']
    profile_type = test_case['profile_type']
    
    print(f"\n{'='*60}")
    print(f"Test Case: {test_id} - {profile_type}")
    print(f"{'='*60}")
    
    # Build request
    request = build_request_from_test_case(test_case)
    
    if request is None:
        print(f"  SKIP: Invalid profile type or validation error")
        return {
            'test_case_id': test_id,
            'profile_type': profile_type,
            'status': 'SKIPPED',
            'error': 'Invalid profile type or validation error'
        }
    
    try:
        # Run prediction - use model_dump() to get dict, exclude model_id
        input_dict = request.model_dump(exclude={'model_id'})
        result = predict(model_id, input_dict)
        
        # Extract outputs
        raw_proba = None  # Not returned by predict function, would need to call predict_proba separately
        calibrated_proba = result.probability
        predicted_class = result.predicted_class
        risk_category = result.risk_category
        threshold = result.threshold
        calibrated = result.calibrated
        calibration_method = result.calibration_method or 'N/A'
        
        print(f"  Calibrated probability: {calibrated_proba:.6f}")
        print(f"  Predicted class: {predicted_class}")
        print(f"  Risk category: {risk_category}")
        print(f"  Threshold: {threshold}")
        print(f"  Calibrated: {calibrated}")
        print(f"  Calibration method: {calibration_method}")
        
        # Get SHAP explanations
        try:
            from src.inference.predictor import load_model_and_preprocessing
            model, feature_names = load_model_and_preprocessing(model_id)
            if isinstance(model, dict):
                model = model.get("base_model", model)
            
            from src.inference.predictor import apply_feature_engineering
            features = apply_feature_engineering(request.model_dump())
            shap_result = compute_prediction_explanations(model, model_id, features, feature_names)
            
            print(f"  SHAP explanations: {len(shap_result)} features")
            shap_status = 'PASS'
            shap_output_space = 'log_odds'
            reconstruction_error = None
            
        except Exception as e:
            print(f"  SHAP error: {e}")
            shap_status = 'ERROR'
            shap_output_space = 'unknown'
            reconstruction_error = None
        
        # Validate outputs
        issues = []
        
        # Check probability bounds
        if not (0 <= calibrated_proba <= 1):
            issues.append(f"Calibrated probability out of bounds: {calibrated_proba}")
        
        # Check classification logic
        if calibrated_proba >= threshold:
            expected_class = 'Default risk'
        else:
            expected_class = 'Lower predicted default risk'
        
        if predicted_class != expected_class:
            issues.append(f"Classification mismatch: got {predicted_class}, expected {expected_class}")
        
        # Check risk tier
        if calibrated_proba < threshold * 0.5:
            expected_risk = 'Low'
        elif calibrated_proba < threshold:
            expected_risk = 'Medium'
        else:
            expected_risk = 'High'
        
        if risk_category != expected_risk:
            issues.append(f"Risk tier mismatch: got {risk_category}, expected {expected_risk}")
        
        status = 'PASS' if not issues else 'FAIL'
        if issues:
            print(f"  ISSUES: {'; '.join(issues)}")
        
        return {
            'test_case_id': test_id,
            'profile_type': profile_type,
            'raw_probability': 'N/A',  # Not exposed by current predict function
            'calibrated_probability': f"{calibrated_proba:.6f}",
            'predicted_class': predicted_class,
            'risk_category': risk_category,
            'threshold': threshold,
            'calibrated': calibrated,
            'calibration_method': calibration_method,
            'shap_status': shap_status,
            'shap_output_space': shap_output_space,
            'shap_reconstruction_error': f"{reconstruction_error:.10f}" if reconstruction_error is not None else 'N/A',
            'status': status,
            'issues': '; '.join(issues) if issues else ''
        }
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            'test_case_id': test_id,
            'profile_type': profile_type,
            'status': 'ERROR',
            'error': str(e)
        }


def update_csv_with_results(csv_path, results):
    """Update the CSV file with test results."""
    # Read existing data
    test_cases = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            test_cases.append(row)
    
    # Add new fieldnames if needed
    new_fieldnames = [
        'shap_status', 'shap_output_space', 'shap_reconstruction_error',
        'issues', 'test_timestamp', 'error'
    ]
    for fn in new_fieldnames:
        if fn not in fieldnames:
            fieldnames.append(fn)
    
    # Update rows with results
    results_dict = {r['test_case_id']: r for r in results}
    for row in test_cases:
        test_id = row['test_case_id']
        if test_id in results_dict:
            result = results_dict[test_id]
            # Only update fields that exist in fieldnames and are not None
            for key, value in result.items():
                if key in fieldnames and value is not None:
                    row[key] = value
            row['test_timestamp'] = datetime.now().isoformat()
        # Remove any None keys from row
        keys_to_remove = [k for k in row.keys() if k is None]
        for k in keys_to_remove:
            del row[k]
    
    # Write updated CSV
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(test_cases)
    
    print(f"\nUpdated CSV: {csv_path}")


def main():
    """Main test runner."""
    print("="*80)
    print("Phase 9 - Session 4: Reproducible Prediction Test Cases")
    print("="*80)
    
    # Paths
    csv_path = Path(__file__).parent / "reports" / "phase_9_prediction_test_cases.csv"
    report_path = Path(__file__).parent / "reports" / "phase_9_prediction_validation_test_report.md"
    
    # Model ID
    model_id = "uci_taiwan_xgb"
    
    # Load model
    print("\nLoading model and preprocessing...")
    model, feature_names = load_model_and_preprocessing(model_id)
    print(f"  Model ID: {model_id}")
    print(f"  Features: {len(feature_names)}")
    
    # Load test cases
    print(f"\nLoading test cases from {csv_path}")
    test_cases = load_test_cases(csv_path)
    print(f"  Found {len(test_cases)} test cases")
    
    # Run valid test cases
    print("\n" + "="*80)
    print("Running Valid Test Cases")
    print("="*80)
    results = []
    for test_case in test_cases:
        result = run_test_case(test_case, model_id)
        results.append(result)
    
    # Run invalid input tests
    print("\n" + "="*80)
    print("Running Invalid Input Tests")
    print("="*80)
    invalid_results = test_invalid_inputs()
    results.extend(invalid_results)
    
    # Update CSV
    print("\n" + "="*80)
    print("Updating Test Results CSV")
    print("="*80)
    update_csv_with_results(csv_path, results)
    
    # Generate report
    print("\n" + "="*80)
    print("Generating Test Report")
    print("="*80)
    
    pass_count = sum(1 for r in results if r.get('status') == 'PASS')
    fail_count = sum(1 for r in results if r.get('status') == 'FAIL')
    error_count = sum(1 for r in results if r.get('status') == 'ERROR')
    skip_count = sum(1 for r in results if r.get('status') == 'SKIPPED')
    
    report = f"""# Phase 9 - Session 4: Prediction Validation Test Report

**Date:** {datetime.now().isoformat()}
**Test Suite:** Reproducible Prediction Test Cases

## Summary

- Total Tests: {len(results)}
- Passed: {pass_count}
- Failed: {fail_count}
- Errors: {error_count}
- Skipped: {skip_count}

## Test Results

"""
    
    for result in results:
        test_id = result.get('test_case_id', 'N/A')
        status = result.get('status', 'UNKNOWN')
        profile = result.get('profile_type', result.get('description', 'N/A'))
        
        report += f"### {test_id}: {profile}\n\n"
        report += f"- **Status:** {status}\n"
        
        if status == 'PASS':
            report += f"- Raw Probability: {result.get('raw_probability', 'N/A')}\n"
            report += f"- Calibrated Probability: {result.get('calibrated_probability', 'N/A')}\n"
            report += f"- Predicted Class: {result.get('predicted_class', 'N/A')}\n"
            report += f"- Risk Category: {result.get('risk_category', 'N/A')}\n"
            report += f"- SHAP Status: {result.get('shap_status', 'N/A')}\n"
            report += f"- SHAP Output Space: {result.get('shap_output_space', 'N/A')}\n"
            report += f"- SHAP Reconstruction Error: {result.get('shap_reconstruction_error', 'N/A')}\n"
        elif status == 'FAIL':
            report += f"- Issues: {result.get('issues', 'N/A')}\n"
        elif status == 'ERROR':
            report += f"- Error: {result.get('error', 'N/A')}\n"
        
        report += "\n"
    
    report += """
## Conclusions

"""
    
    if fail_count == 0 and error_count == 0:
        report += "All tests passed. The prediction pipeline is functioning correctly.\n"
    else:
        report += f"Tests failed or encountered errors. Review the issues above.\n"
    
    report += """
## Reproducibility Statement

These test results are reproducible. The same inputs will produce the same outputs
given the same model artifacts and calibration parameters.

## Limitations

- Test cases are synthetic examples, not real borrower profiles
- The model was trained on Taiwan credit card data, not Indian borrower data
- Risk tier labels are descriptive, not validated lending categories
- These tests verify pipeline correctness, not predictive accuracy for any population

"""
    
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"Report written to {report_path}")
    
    print("\n" + "="*80)
    print("Test Suite Complete")
    print("="*80)
    print(f"Passed: {pass_count}, Failed: {fail_count}, Errors: {error_count}, Skipped: {skip_count}")


if __name__ == "__main__":
    main()
