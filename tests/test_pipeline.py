"""
CreditAI: Pipeline Unit Tests
Verifies:
1. Data loading integrity
2. Target column presence and binary validity
3. ID removal to prevent identifier leakage
4. Feature engineering completeness
5. Absence of target leakage
6. Stratified split ratios and sizes
7. Prediction output range within [0, 1]
"""

import unittest
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from src.config import (
    TARGET_COLUMN,
    ID_COLUMN,
    TRAIN_RATIO,
    VAL_RATIO,
    TEST_RATIO,
    RANDOM_STATE,
)
from src.data_loader import load_uci_credit_card_data
from src.preprocessing import preprocess_data
from src.feature_engineering import engineer_credit_features


class TestCreditAIPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Loads and preprocessed data once for the test suite."""
        cls.raw_df = load_uci_credit_card_data(verbose=False)
        cls.X_pre, cls.y = preprocess_data(cls.raw_df, is_training=True, verbose=False)
        cls.X_feat = engineer_credit_features(cls.X_pre, verbose=False)

    def test_01_data_loader_shape(self):
        """Verify the raw dataset has exactly 30,000 rows and 25 columns."""
        self.assertEqual(self.raw_df.shape[0], 30000)
        self.assertEqual(self.raw_df.shape[1], 25)

    def test_02_target_exists_and_binary(self):
        """Verify the target exists and contains strictly binary labels (0 and 1)."""
        self.assertIn(TARGET_COLUMN, self.raw_df.columns)
        unique_targets = set(self.y.unique())
        self.assertEqual(unique_targets, {0, 1})
        # Default rate should be approximately 22.12%
        bad_rate = self.y.mean()
        self.assertAlmostEqual(bad_rate, 0.2212, places=3)

    def test_03_id_removed(self):
        """Verify ID column is strictly dropped from the feature matrix."""
        self.assertNotIn(ID_COLUMN, self.X_pre.columns)
        self.assertNotIn(ID_COLUMN, self.X_feat.columns)

    def test_04_engineered_features_created(self):
        """Verify key engineered risk features exist in the final matrix."""
        expected_features = [
            "UTIL_1",
            "AVG_UTILIZATION",
            "MAX_UTILIZATION",
            "PAY_TO_BILL_1",
            "AVG_PAY_TO_BILL",
            "MAX_DELINQUENCY",
            "AVG_DELINQUENCY",
            "DELINQUENT_MONTHS_COUNT",
            "RECENT_DELINQUENCY_FLAG",
            "DELINQUENCY_TREND_SHORT",
            "DELINQUENCY_TREND_LONG",
            "BILL_CHANGE_1_2",
            "BILL_GROWTH_OVER_LIMIT",
            "PAYMENT_MONTHS_COUNT",
            "TOTAL_PAY_TO_TOTAL_BILL",
            "TIMELY_PAYMENT_COUNT",
        ]
        for feat in expected_features:
            self.assertIn(feat, self.X_feat.columns, f"Missing engineered feature: {feat}")
        self.assertEqual(self.X_feat.shape[1], 50)

    def test_05_no_target_leakage(self):
        """Verify target is completely absent from X_pre and X_feat."""
        self.assertNotIn(TARGET_COLUMN, self.X_pre.columns)
        self.assertNotIn(TARGET_COLUMN, self.X_feat.columns)
        self.assertEqual(len(self.X_feat), len(self.y))

    def test_06_train_val_test_splits(self):
        """Verify stratified split yields exact 70/15/15 partition sizes."""
        X_train, X_temp, y_train, y_temp = train_test_split(
            self.X_feat, self.y, train_size=TRAIN_RATIO, random_state=RANDOM_STATE, stratify=self.y
        )
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp, test_size=0.50, random_state=RANDOM_STATE, stratify=y_temp
        )

        # 30,000 * 0.70 = 21,000
        self.assertEqual(len(X_train), 21000)
        # 30,000 * 0.15 = 4,500
        self.assertEqual(len(X_val), 4500)
        # 30,000 * 0.15 = 4,500
        self.assertEqual(len(X_test), 4500)

        # Check stratification balance
        train_bad_rate = y_train.mean()
        val_bad_rate = y_val.mean()
        test_bad_rate = y_test.mean()

        self.assertAlmostEqual(train_bad_rate, 0.2212, places=3)
        self.assertAlmostEqual(val_bad_rate, 0.2212, places=3)
        self.assertAlmostEqual(test_bad_rate, 0.2212, places=3)

    def test_07_prediction_output_range(self):
        """Verify a lightweight logistic model produces valid probability in [0, 1]."""
        from sklearn.linear_model import LogisticRegression

        clf = LogisticRegression(max_iter=200, random_state=42)
        clf.fit(self.X_feat.iloc[:1000], self.y.iloc[:1000])

        probs = clf.predict_proba(self.X_feat.iloc[1000:1050])[:, 1]
        self.assertTrue(np.all(probs >= 0.0))
        self.assertTrue(np.all(probs <= 1.0))


if __name__ == "__main__":
    unittest.main()
