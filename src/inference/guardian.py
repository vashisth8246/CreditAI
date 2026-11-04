"""Research input checks and frozen Taiwan population reference. No inference policy for lending."""
import hashlib
import json
import math
import re
from functools import lru_cache
from pathlib import Path

from .model_registry import get_feature_schema

METHOD = "taiwan-marginal-support-v1"
REFERENCE_PATH = Path(__file__).with_name("guardian_reference.json")
DATASET_SHA = "21b3cf4e30878150ae8db9386780e23febb613921747dec9e59dccb32f6104d3"
CONTINUOUS = ("LIMIT_BAL", "AGE", *(f"BILL_AMT{i}" for i in range(1, 7)), *(f"PAY_AMT{i}" for i in range(1, 7)))
CATEGORICAL = ("EDUCATION", "PAY_0", *(f"PAY_{i}" for i in range(2, 7)))
TAIL_LEVELS = (.001, .005, .01, .025, .05, .1)


@lru_cache(maxsize=1)
def load_reference():
    try:
        artifact = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
        if artifact["method"] == METHOD and artifact["dataset_sha256"] == DATASET_SHA:
            root = REFERENCE_PATH.parents[2]
            files = (("creditai_model.joblib", "model_sha256"), ("calibration_model.joblib", "calibration_sha256"))
            if all(hashlib.sha256((root / "models" / name).read_bytes()).hexdigest() == artifact[key] for name, key in files):
                return artifact
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def finding(field, code, severity, explanation, evidence, action):
    return {
        "field": field, "code": code, "severity": severity, "explanation": explanation,
        "evidence": evidence, "action": action, "blocks_inference": severity == "error",
    }


def check_input(features, model_id="uci_taiwan_xgb"):
    schema = get_feature_schema(model_id)["raw_features"]
    clean, findings = {}, []
    for name, rule in schema.items():
        value = features.get(name)
        if value is None or isinstance(value, str) and not value.strip():
            findings.append(finding(name, "missing", "error", "Required research input is missing.", "No value supplied.", "Enter the value from the source record."))
            continue
        # Form controls supply text; only signed, whole-number decimal strings are accepted.
        if isinstance(value, str) and re.fullmatch(r"[+-]?\d{1,18}", value.strip()):
            value = int(value)
        numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
        if not numeric or isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()):
            findings.append(finding(name, "invalid_number", "error", "Expected a finite whole number.", "Value is not a supported integer.", "Check the format and units in the source record."))
            continue
        bounds, allowed = rule.get("range"), rule.get("values")
        if allowed and value not in allowed:
            findings.append(finding(name, "invalid_code", "error", "Code is outside the supported research schema.", f"Allowed codes: {', '.join(map(str, allowed))}.", "Use the documented code for this field."))
        elif bounds and not bounds[0] <= value <= bounds[1]:
            findings.append(finding(name, "out_of_range", "error", "Value is outside the supported inference range.", f"Supported interval: {bounds[0]} to {bounds[1]}.", "Check the source value. Do not clamp or replace an authentic value."))
        else:
            clean[name] = int(value)
    if set(features) - set(schema):
        findings.append(finding("features", "unexpected_field", "error", "Only the documented raw fields are accepted.", "Extra fields supplied.", "Remove extra fields, identifiers and outcomes."))
    if len(clean) != len(schema):
        return clean, findings

    limit = clean["LIMIT_BAL"]
    if limit == 0:
        findings.append(finding("LIMIT_BAL", "zero_credit_limit", "warning", "Zero is accepted by the research contract but merits verification.", "Reported credit limit is zero.", "Check the credit limit and units."))
    bills = [clean[f"BILL_AMT{i}"] for i in range(1, 7)]
    if limit > 0 and max(bills) > 2 * limit:
        findings.append(finding("LIMIT_BAL", "statement_limit_mismatch", "warning", "A bill exceeds twice the credit limit. Over-limit statements can occur.", "Largest bill is more than two times the entered limit.", "Verify that statements and limit belong to the same account and use NT dollars."))
    if any(value < 0 for value in bills):
        findings.append(finding("BILL_AMT1–6", "negative_statement", "information", "A negative statement can represent a credit balance.", "At least one entered bill is negative.", "Confirm the statement sign if it was entered manually."))
    return clean, findings


def distribution_score(features, reference):
    """Sum the three strongest marginal tail/frequency signals; no target or ID."""
    scores = []
    for name in CONTINUOUS:
        value = features[name]
        lower, upper = reference["continuous"][name]
        score = sum(value < lo or value > hi for lo, hi in zip(lower, upper))
        if score:
            scores.append((score, name, "outside nested central training intervals"))
    for name in CATEGORICAL:
        value = features[name]
        if name == "EDUCATION" and value in (0, 5, 6):
            value = 4
        count = reference["categorical"][name].get(str(value), 0)
        frequency = (count + 1) / (reference["train_count"] + 1)
        score = sum(frequency < level for level in TAIL_LEVELS)
        if score:
            scores.append((score, name, "infrequent code in the training partition"))
    strongest = sorted(scores, key=lambda item: (-item[0], item[1]))[:3]
    return sum(item[0] for item in strongest), strongest


def assess(features, model_id="uci_taiwan_xgb"):
    if model_id not in ("uci_taiwan_xgb", "uci_taiwan_knn"):
        return None, {
            "status": "model_unavailable", "model_id": model_id, "method": METHOD,
            "findings": [], "distribution_findings": [], "valid_fields": 0, "required_fields": 23,
            "distribution_evaluated": False, "evaluation_available": False,
            "reasons": ["This model has no supported Guardian inference path."],
        }
    clean, findings = check_input(features, model_id)
    invalid = any(item["blocks_inference"] for item in findings)
    artifact = load_reference() if model_id == "uci_taiwan_xgb" else None
    distribution_findings = []
    evaluated = artifact is not None and not invalid
    reasons = []
    if invalid:
        status = "input_correction_required"
        reasons.append("Correct the input errors before running research inference.")
    elif artifact is None:
        status = "reliability_not_evaluated"
        reasons.append("Training-distribution reliability was not evaluated because the required verified reference data is unavailable for this model.")
    else:
        score, drivers = distribution_score(clean, artifact["reference"])
        flagged = score > artifact["review_threshold"]
        if flagged:
            distribution_findings = [
                finding(name, "low_training_support", "warning", "Unusual relative to the evaluated training population.", evidence, "Check this value against the original record.")
                for _, name, evidence in drivers
            ]
        if flagged or any(item["severity"] == "warning" for item in findings):
            status = "manual_review_recommended"
            reasons.append("Review the reported evidence concerns before using this research output as decision support.")
        else:
            status = "review_eligible"
            reasons.append("No concern crossed the selected checks. This does not establish that the prediction is correct.")
    if artifact is None and not invalid and any(item["severity"] == "warning" for item in findings):
        reasons.append("Review the input-quality warnings even though distribution evidence is unavailable.")
    return (None if invalid else clean), {
        "status": status, "model_id": model_id, "method": METHOD,
        "findings": findings, "distribution_findings": distribution_findings,
        "valid_fields": len(clean), "required_fields": 23, "distribution_evaluated": evaluated,
        "evaluation_available": artifact is not None, "reasons": reasons,
        "reference": {"dataset": "UCI Taiwan credit-card clients (2005)", "sha256": DATASET_SHA,
                      "train_count": artifact["reference"]["train_count"]} if artifact else None,
        "limitations": "Historical Taiwan research only. Input validity, population similarity, predictive performance and calibration do not validate Indian lending use.",
    }
