"""Run isolated, reproducible Taiwan UCI research experiments for Phase 11.

Outputs are research evidence only. This script never writes under models/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
import shap
import xgboost
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from src.data_loader import load_uci_credit_card_data, find_dataset_path
from src.preprocessing import preprocess_data
from src.feature_engineering import engineer_credit_features
from src.config import RANDOM_STATE
from src.research.phase11.core import (
    apply_isotonic, apply_platt, fit_isotonic, fit_platt,
    probability_metrics, reliability_bins, select_review_margin, selective_metrics,
)
from scripts.fetch_phase11_dataset import verify_file

OUT = ROOT / "reports" / "phase11"
SEED = int(RANDOM_STATE)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def split_hash(indices: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(indices, dtype=np.int64).tobytes()).hexdigest()


def json_safe(value):
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def shap_matrix(explainer, matrix: pd.DataFrame) -> np.ndarray:
    values = explainer.shap_values(matrix)
    if isinstance(values, list):
        values = values[1]
    values = np.asarray(values)
    if values.ndim == 3:
        values = values[:, :, 1]
    return values


def main(argv: list[str] | None = None) -> None:
    global OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUT,
        help="Write experiment evidence here (default: reports/phase11).",
    )
    args = parser.parse_args(argv)
    OUT = args.output_dir.resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    dataset_path = find_dataset_path()
    verify_file(dataset_path)
    raw = load_uci_credit_card_data(dataset_path, verbose=False)
    X_pre, y_series = preprocess_data(raw, is_training=True, verbose=False)
    X = engineer_credit_features(X_pre, verbose=False)
    y = y_series.to_numpy(dtype=int)
    positions = np.arange(len(y))
    train_idx, other_idx = train_test_split(positions, train_size=0.70, random_state=SEED, stratify=y)
    val_idx, test_idx = train_test_split(other_idx, test_size=0.50, random_state=SEED, stratify=y[other_idx])
    X_train, X_val, X_test = X.iloc[train_idx], X.iloc[val_idx], X.iloc[test_idx]
    y_train, y_val, y_test = y[train_idx], y[val_idx], y[test_idx]

    positive_weight = float((y_train == 0).sum() / (y_train == 1).sum())
    models = {
        "logistic_regression": make_pipeline(
            StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=1000, random_state=SEED)
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200, max_depth=10, min_samples_leaf=20, class_weight="balanced",
            random_state=SEED, n_jobs=-1,
        ),
        "xgboost": XGBClassifier(
            n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.8,
            colsample_bytree=0.8, scale_pos_weight=positive_weight, random_state=SEED,
            eval_metric="logloss", n_jobs=-1,
        ),
    }
    test_predictions: dict[str, np.ndarray] = {}
    validation_predictions: dict[str, np.ndarray] = {}
    for name, model in models.items():
        print(f"Training research model: {name}", flush=True)
        model.fit(X_train, y_train)
        validation_predictions[name] = model.predict_proba(X_val)[:, 1]
        test_predictions[name] = model.predict_proba(X_test)[:, 1]

    rows: list[dict] = []
    reliability: dict[str, list] = {}
    calibrated_predictions: dict[str, np.ndarray] = {}
    for name in models:
        raw_val = validation_predictions[name]
        raw_test = test_predictions[name]
        calibrators = {
            "raw": None,
            "platt": fit_platt(raw_val, y_val),
            "isotonic": fit_isotonic(raw_val, y_val),
        }
        for method, calibrator in calibrators.items():
            if method == "raw":
                pred = raw_test
            elif method == "platt":
                pred = apply_platt(calibrator, raw_test)
            else:
                pred = apply_isotonic(calibrator, raw_test)
            key = f"{name}_{method}"
            if name == "xgboost":
                calibrated_predictions[method] = pred
            metrics = probability_metrics(y_test, pred)
            rows.append({"model": name, "probability_method": method, "evaluation_split": "locked_test", **metrics})
            reliability[key] = reliability_bins(y_test, pred)

    metric_df = pd.DataFrame(rows)
    metric_df.to_csv(OUT / "probability_metrics.csv", index=False)
    (OUT / "probability_metrics.json").write_text(
        json.dumps(json_safe(rows), indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "reliability_bins.json").write_text(
        json.dumps(json_safe(reliability), indent=2) + "\n", encoding="utf-8"
    )
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), sharex=True, sharey=True)
    for ax, name in zip(axes, models):
        for method in ("raw", "platt", "isotonic"):
            bins = reliability[f"{name}_{method}"]
            ax.plot([b["mean_predicted"] for b in bins], [b["observed_rate"] for b in bins], marker="o", label=method)
        ax.plot([0, 1], [0, 1], linestyle="--", color="gray")
        ax.set_title(name.replace("_", " "))
        ax.set_xlabel("Mean predicted probability")
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Observed default rate")
    axes[-1].legend()
    fig.suptitle("Taiwan UCI locked-test reliability (research only)")
    fig.tight_layout()
    fig.savefig(OUT / "reliability_diagrams.png", dpi=160)
    plt.close(fig)

    margin, validation_candidates = select_review_margin(y_val, apply_platt(
        fit_platt(validation_predictions["xgboost"], y_val), validation_predictions["xgboost"]
    ), min_coverage=0.80)
    xgb_cal = calibrated_predictions["platt"]
    selective = {
        "selection_split": "validation",
        "evaluation_split": "locked_test",
        "model": "xgboost",
        "probability_method": "platt fitted on validation split",
        "minimum_validation_coverage": 0.80,
        "selected_margin": margin,
        "validation_selected_candidate": next(row for row in validation_candidates if row["review_margin"] == margin),
        "test": selective_metrics(y_test, xgb_cal, margin),
        "interpretation": "Confidence-based referral screen at a 0.5 threshold; not a guarantee of epistemic uncertainty or safe credit decisions.",
    }
    (OUT / "selective_review.json").write_text(json.dumps(json_safe(selective), indent=2) + "\n", encoding="utf-8")

    # Local explanation stability: empirical single-column replacements from training rows.
    # Each perturbed row remains inside the observed marginal support of the replaced column.
    # Other columns are held fixed; this is not a causal or joint-distribution claim.
    print("Computing bounded SHAP perturbation stability", flush=True)
    xgb = models["xgboost"]
    explainer = shap.TreeExplainer(xgb)
    base = X_test.iloc[:100].copy().reset_index(drop=True)
    base_shap = shap_matrix(explainer, base)
    rng = np.random.default_rng(SEED)
    features = list(X_train.columns)
    changed_features = features[:: max(1, len(features) // 12)][:12]
    stability_rows = []
    for feature in changed_features:
        perturbed = base.copy()
        donor_positions = rng.integers(0, len(X_train), size=len(base))
        perturbed[feature] = X_train.iloc[donor_positions][feature].to_numpy()
        altered = shap_matrix(explainer, perturbed)
        for i in range(len(base)):
            base_rank = pd.Series(np.abs(base_shap[i]), index=features).rank(method="average", ascending=False)
            alt_rank = pd.Series(np.abs(altered[i]), index=features).rank(method="average", ascending=False)
            rank_corr = float(base_rank.corr(alt_rank, method="spearman"))
            k = min(10, len(features))
            a = set(np.argsort(np.abs(base_shap[i]))[-k:])
            b = set(np.argsort(np.abs(altered[i]))[-k:])
            stability_rows.append({
                "row_in_fixed_test_sample": i,
                "replaced_feature": feature,
                "top10_jaccard": float(len(a & b) / len(a | b)),
                "spearman_abs_shap_rank": rank_corr,
            })
    shap_df = pd.DataFrame(stability_rows)
    shap_df.to_csv(OUT / "shap_stability.csv", index=False)
    summary = shap_df.groupby("replaced_feature").agg(
        perturbation_count=("row_in_fixed_test_sample", "count"),
        mean_top10_jaccard=("top10_jaccard", "mean"),
        mean_spearman_abs_shap_rank=("spearman_abs_shap_rank", "mean"),
    ).reset_index()
    summary.to_csv(OUT / "shap_stability_summary.csv", index=False)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(summary["replaced_feature"], summary["mean_top10_jaccard"])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Mean top-10 Jaccard overlap")
    ax.set_title("XGBoost SHAP rank stability under marginal single-feature replacement")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(OUT / "shap_stability.png", dpi=160)
    plt.close(fig)

    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        worktree_dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    except Exception:
        commit, worktree_dirty = None, None
    metadata = {
        "study": "CreditAI Phase 11 Taiwan UCI research; not production validation",
        "dataset": {
            "name": "UCI Default of Credit Card Clients",
            "path_at_run": str(dataset_path.relative_to(ROOT)),
            "sha256": sha256(dataset_path),
            "rows": len(raw),
            "columns": len(raw.columns),
            "missing_values": int(raw.isna().sum().sum()),
            "target_column": str(raw.columns[-1]),
            "target_counts": {str(k): int(v) for k, v in pd.Series(y).value_counts().sort_index().items()},
        },
        "reproducibility": {
            "seed": SEED,
            "commit_sha": commit,
            "worktree_was_dirty": worktree_dirty,
            "split": {
                "train": {"rows": len(train_idx), "index_sha256": split_hash(train_idx)},
                "validation": {"rows": len(val_idx), "index_sha256": split_hash(val_idx)},
                "test": {"rows": len(test_idx), "index_sha256": split_hash(test_idx)},
                "stratified": True,
                "proportions": {"train": 0.70, "validation": 0.15, "test": 0.15},
            },
            "python": platform.python_version(),
            "numpy": np.__version__, "pandas": pd.__version__, "scikit_learn": sklearn.__version__,
            "xgboost": xgboost.__version__, "shap": shap.__version__,
        },
        "models": {
            "logistic_regression": "StandardScaler + class_weight=balanced LogisticRegression(max_iter=1000)",
            "random_forest": "200 trees, max_depth=10, min_samples_leaf=20, class_weight=balanced",
            "xgboost": "300 estimators, depth 5, learning_rate .05, subsample/colsample .8, train-derived scale_pos_weight",
        },
        "calibration": "Platt logistic regression on clipped probability logits and isotonic regression, fit only on validation labels/probabilities; test split used only for final metrics.",
        "shap_stability": "TreeExplainer absolute-value rank comparisons for 100 fixed test rows, 12 observed marginal feature replacements per row; not causal and not a joint-distribution perturbation.",
        "limitations": [
            "Taiwan 2005 research data are not representative evidence for India or another deployment population.",
            "No production validation or authorization is implied; /v1/score remains not_validated.",
            "The checkout was dirty at run time; recorded commit identifies HEAD only, not all uncommitted source changes.",
            "SHAP perturbations preserve each replaced feature's empirical marginal support but may create implausible cross-feature combinations.",
            "No shipped model, calibrator, evaluation JSON, or model metadata was overwritten.",
        ],
    }
    (OUT / "run_metadata.json").write_text(json.dumps(json_safe(metadata), indent=2) + "\n", encoding="utf-8")
    print(f"Research outputs written to {OUT}", flush=True)
    print(metric_df.to_string(index=False), flush=True)
    print("SHAP stability means:", summary.mean(numeric_only=True).to_dict(), flush=True)
    print("Selective test result:", selective["test"], flush=True)


if __name__ == "__main__":
    main()
