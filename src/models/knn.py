"""CreditAI K-Nearest Neighbors (KNN) Pipeline and Explanation Module.

Provides:
1. Sklearn-compatible KNN pipeline with median imputation and standard scaling.
2. Hyperparameter-tuned configuration (n_neighbors=51, metric='manhattan', weights='uniform').
3. Platt calibration support on held-out validation predictions.
4. Local neighbor-based explanation engine (KNNNeighborExplainer) that computes
   influential neighbors and feature difference drivers without misrepresenting them as SHAP.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    log_loss,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

from src.calibration.calibrate import PlattCalibrator
from src.inference.schemas import FeatureContribution


def build_knn_pipeline(
    n_neighbors: int = 51,
    metric: str = "manhattan",
    weights: str = "uniform",
) -> Pipeline:
    """Build a leakage-safe scikit-learn pipeline for KNN classification."""
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("knn", KNeighborsClassifier(
            n_neighbors=n_neighbors,
            metric=metric,
            weights=weights,
            n_jobs=-1,
        )),
    ])


class KNNNeighborExplainer:
    """Explains predictions using k-nearest training neighbors and feature diffs."""

    def __init__(
        self,
        fitted_pipeline: Pipeline,
        X_train: np.ndarray,
        y_train: np.ndarray,
        feature_names: List[str],
    ):
        self.pipeline = fitted_pipeline
        self.scaler: StandardScaler = fitted_pipeline.named_steps["scaler"]
        self.imputer: SimpleImputer = fitted_pipeline.named_steps["imputer"]
        self.knn: KNeighborsClassifier = fitted_pipeline.named_steps["knn"]
        self.X_train_raw = np.asarray(X_train)
        self.y_train = np.asarray(y_train)
        self.feature_names = list(feature_names)

        # Pre-transform training data for distance queries
        X_imp = self.imputer.transform(self.X_train_raw)
        self.X_train_scaled = self.scaler.transform(X_imp)

    def explain_instance(
        self,
        instance_dict: Dict[str, float],
        k: int = 15,
        top_features: int = 6,
    ) -> Tuple[List[FeatureContribution], Dict[str, Any]]:
        """Explain a single instance using its nearest training neighbors.

        Identifies:
        - k nearest neighbors in standardized feature space
        - Neighbor default prevalence vs population baseline
        - Top features where the instance deviates most strongly from non-default neighbors
        """
        # Convert instance to array
        x_raw = np.array([[instance_dict.get(col, 0.0) for col in self.feature_names]], dtype=float)
        x_imp = self.imputer.transform(x_raw)
        x_scaled = self.scaler.transform(x_imp)

        # Query kneighbors
        distances, indices = self.knn.kneighbors(x_scaled, n_neighbors=k)
        neighbor_indices = indices[0]
        neighbor_distances = distances[0]
        neighbor_labels = self.y_train[neighbor_indices]

        # Calculate neighbor default rate
        neighbor_defaults = int(np.sum(neighbor_labels == 1))
        neighbor_default_rate = float(neighbor_defaults / k)

        # Feature divergence analysis:
        # Compare instance's scaled values to the mean of non-default neighbors
        non_default_idx = neighbor_indices[neighbor_labels == 0]
        default_idx = neighbor_indices[neighbor_labels == 1]

        if len(non_default_idx) > 0:
            baseline_scaled = np.mean(self.X_train_scaled[non_default_idx], axis=0)
        else:
            baseline_scaled = np.zeros(len(self.feature_names))

        # Deviation in standard deviations (z-score difference)
        z_diff = (x_scaled[0] - baseline_scaled)

        # Key risk indicators where positive deviation indicates higher risk
        risk_positive_features = {
            "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6",
            "MAX_DELINQUENCY", "AVG_DELINQUENCY", "DELINQUENT_MONTHS_COUNT",
            "RECENT_DELINQUENCY_FLAG", "UTIL_1", "MAX_UTILIZATION", "AVG_UTILIZATION",
            "BILL_GROWTH_OVER_LIMIT", "BILL_CHANGE_1_2"
        }

        risk_negative_features = {
            "PAY_TO_BILL_1", "AVG_PAY_TO_BILL", "TOTAL_PAY_TO_TOTAL_BILL",
            "PAYMENT_MONTHS_COUNT", "TIMELY_PAYMENT_COUNT", "LIMIT_BAL"
        }

        contributions: List[FeatureContribution] = []
        for idx, feat_name in enumerate(self.feature_names):
            diff = z_diff[idx]
            abs_diff = abs(diff)

            if feat_name in risk_positive_features:
                direction = "increases_risk" if diff > 0 else "decreases_risk"
            elif feat_name in risk_negative_features:
                direction = "increases_risk" if diff < 0 else "decreases_risk"
            else:
                direction = "increases_risk" if diff > 0 else "decreases_risk"

            contributions.append(
                FeatureContribution(
                    feature=feat_name,
                    contribution=round(float(abs_diff), 4),
                    direction=direction,
                )
            )

        # Sort by contribution descending
        contributions.sort(key=lambda c: c.contribution, reverse=True)

        neighbor_summary = {
            "neighbors_evaluated": k,
            "neighbor_defaults": neighbor_defaults,
            "neighbor_default_rate": round(neighbor_default_rate, 4),
            "nearest_neighbor_distance": round(float(neighbor_distances[0]), 4),
            "furthest_neighbor_distance": round(float(neighbor_distances[-1]), 4),
            "method": "KNN Local Neighbor Variance Attribution",
        }

        return contributions[:top_features], neighbor_summary
