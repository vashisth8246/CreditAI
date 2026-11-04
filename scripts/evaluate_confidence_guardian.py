"""Reproduce the Taiwan split and evaluate a frozen Guardian without fitting the credit model."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data_loader import load_uci_credit_card_data
from src.feature_engineering import engineer_credit_features
from src.inference.guardian import CATEGORICAL, CONTINUOUS, DATASET_SHA, METHOD, TAIL_LEVELS, check_input, distribution_score
from src.inference.predictor import apply_calibration, apply_feature_engineering, load_calibration_model, load_model_and_preprocessing
from src.preprocessing import preprocess_data

COVERAGES = (.95, .90, .80, .70)


def split_indices(y):
    train, temp = train_test_split(np.arange(len(y)), train_size=.70, random_state=42, stratify=y)
    val, test = train_test_split(temp, test_size=.50, random_state=42, stratify=y.iloc[temp])
    assert len(set(train) | set(val) | set(test)) == len(y)
    return train, val, test


def fit_reference(train):
    continuous = {
        name: [[float(train[name].quantile(q)) for q in TAIL_LEVELS],
               [float(train[name].quantile(1 - q)) for q in TAIL_LEVELS]]
        for name in CONTINUOUS
    }
    categorical = {name: {str(int(code)): int(count) for code, count in train[name].value_counts().items()}
                   for name in CATEGORICAL}
    return {"train_count": len(train), "continuous": continuous, "categorical": categorical}


def cutoff(validation_scores, coverage):
    """Smallest integer cutoff attaining requested validation coverage, including all ties."""
    return float(np.sort(validation_scores)[max(0, int(np.ceil(len(validation_scores) * coverage)) - 1)])


def evaluate(y, probs, keep, groups):
    count = int(keep.sum())
    observed, predicted = y[keep], probs[keep]
    bins = []
    for lower, upper in zip([0, .1, .2, .3, .4, .5], [.1, .2, .3, .4, .5, 1.01]):
        selected = (predicted >= lower) & (predicted < upper)
        if selected.any():
            bins.append({"lower": lower, "upper": min(1, upper), "count": int(selected.sum()),
                         "predicted_mean": float(predicted[selected].mean()), "observed_rate": float(observed[selected].mean())})
    error = ((probs >= .5) != y).astype(float)
    delta_ci = None
    if count and count < len(y):
        rng = np.random.default_rng(2026)
        draws = rng.integers(0, len(y), size=(500, len(y)))
        sampled_keep = keep[draws]
        samples = (error[draws] * sampled_keep).sum(axis=1) / sampled_keep.sum(axis=1) - error[draws].mean(axis=1)
        delta_ci = np.quantile(samples, [.025, .975]).tolist()
    return {
        "retained": count, "abstained": len(y) - count, "coverage": count / len(y),
        "abstention_rate": 1 - count / len(y), "defaults": int(observed.sum()),
        "roc_auc": float(roc_auc_score(observed, predicted)) if len(np.unique(observed)) == 2 else None,
        "average_precision": float(average_precision_score(observed, predicted)) if observed.sum() else None,
        "brier": float(brier_score_loss(observed, predicted)) if count else None,
        "log_loss": float(log_loss(observed, predicted, labels=[0, 1])) if count else None,
        "error_rate": float(error[keep].mean()) if count else None,
        "error_delta_bootstrap_95": delta_ci, "calibration_bins": bins,
        "subgroups": {name: {"total": int(mask.sum()), "retained": int((keep & mask).sum()),
                              "abstained": int((~keep & mask).sum())} for name, mask in groups.items()},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "src/inference/guardian_reference.json")
    args = parser.parse_args()
    if hashlib.sha256(args.workbook.read_bytes()).hexdigest() != DATASET_SHA:
        raise SystemExit("Workbook hash does not match the verified UCI source.")
    frame = load_uci_credit_card_data(args.workbook, verbose=False)
    assert len(frame) == 30000 and frame["ID"].is_unique
    X, y = preprocess_data(frame)
    train, val, test = split_indices(y)
    reference = fit_reference(X.iloc[train])
    model, names = load_model_and_preprocessing("uci_taiwan_xgb")
    estimator = model["base_model"] if isinstance(model, dict) else model
    calibrator = load_calibration_model("uci_taiwan_xgb")
    assert calibrator is not None

    def serving_probs(rows):
        engineered = [apply_feature_engineering(row) for row in rows]
        aligned = np.array([[row[name] for name in names] for row in engineered])
        return np.array([apply_calibration(float(value), calibrator) for value in estimator.predict_proba(aligned)[:, 1]])

    raw = frame[X.columns]
    val_rows = raw.iloc[val].to_dict("records")
    test_rows = raw.iloc[test].to_dict("records")
    val_scores = np.array([distribution_score(row, reference)[0] for row in val_rows])
    test_scored = [distribution_score(row, reference) for row in test_rows]
    test_scores = np.array([value for value, _ in test_scored])
    thresholds = [(target, cutoff(val_scores, target)) for target in COVERAGES]
    y_test = y.iloc[test].to_numpy()
    archived = json.loads((ROOT / "models/uci_taiwan_eval.json").read_text(encoding="utf-8"))
    archived_matrix = engineer_credit_features(X.iloc[test])[names].to_numpy()
    archived_probs = np.array([apply_calibration(float(value), calibrator) for value in estimator.predict_proba(archived_matrix)[:, 1]])
    assert len(test) == archived["metadata"]["test_sample_count"] and int(y_test.sum()) == archived["metadata"]["test_defaults"]
    assert abs(roc_auc_score(y_test, archived_probs) - archived["summary_metrics"]["test_roc_auc"]) < .00015
    val_probs, test_probs = serving_probs(val_rows), serving_probs(test_rows)
    valid, quality, findings = [], [], {}
    for row in test_rows:
        _, issues = check_input(row)
        valid.append(not any(issue["blocks_inference"] for issue in issues))
        quality.append(not any(issue["severity"] in ("error", "warning") for issue in issues))
        for code in {issue["code"] for issue in issues}:
            findings[code] = findings.get(code, 0) + 1
    valid, quality = np.array(valid), np.array(quality)
    groups = {"gender_code_1": X.iloc[test]["SEX"].to_numpy() == 1, "gender_code_2": X.iloc[test]["SEX"].to_numpy() == 2,
              "age_under_30": X.iloc[test]["AGE"].to_numpy() < 30, "age_30_plus": X.iloc[test]["AGE"].to_numpy() >= 30}
    rows = []
    def add(name, keep, **extra):
        rows.append({"name": name, **extra, **evaluate(y_test, test_probs, keep, groups)})
    add("Ungated XGBoost replay", np.ones(len(test), dtype=bool))
    add("Schema validity only", valid)
    add("Schema and quality warnings", quality)
    for target, threshold in thresholds:
        add("Quality + distribution", quality & (test_scores <= threshold), target_coverage=target, cutoff=threshold,
            validation_distribution_coverage=float((val_scores <= threshold).mean()))
        margin_cutoff = -cutoff(-np.abs(val_probs - .5), target)
        add("Probability margin comparator", valid & (np.abs(test_probs - .5) >= margin_cutoff), target_coverage=target, cutoff=margin_cutoff)
    artifact = {
        "method": METHOD, "dataset_sha256": DATASET_SHA, "model_id": "uci_taiwan_xgb",
        "model_sha256": hashlib.sha256((ROOT / "models/creditai_model.joblib").read_bytes()).hexdigest(),
        "calibration_sha256": hashlib.sha256((ROOT / "models/calibration_model.joblib").read_bytes()).hexdigest(),
        "split": {"train": len(train), "validation": len(val), "test": len(test), "seed": 42,
                  "index_sha256": {name: hashlib.sha256(np.asarray(index, dtype="<i8").tobytes()).hexdigest()
                                   for name, index in [("train", train), ("validation", val), ("test", test)]}},
        "classification_threshold": .5, "review_target_coverage": .90, "review_threshold": thresholds[1][1],
        "reference": reference, "evaluation": rows, "quality_findings": findings,
        "archived_baseline_reproduced": {"roc_auc": float(roc_auc_score(y_test, archived_probs)),
                                         "brier": float(brier_score_loss(y_test, archived_probs))},
    }
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for row in rows:
        print(row["name"], row.get("target_coverage"), row["retained"], row["error_rate"], row["brier"])


if __name__ == "__main__":
    main()
