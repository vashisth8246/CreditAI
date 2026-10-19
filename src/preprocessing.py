"""
CreditAI: Data Validation & Preprocessing Module
Validates dataset integrity, handles categorical consolidation, removes ID,
and structures clean feature and target matrices without data leakage.
"""

import pandas as pd
import numpy as np

from src.config import (
    TARGET_COLUMN,
    ID_COLUMN,
    RAW_FEATURE_COLUMNS,
    DEMOGRAPHIC_FEATURES,
)


def validate_raw_data(df: pd.DataFrame, verbose: bool = True) -> bool:
    """
    Performs integrity checks on the raw dataset.
    
    Checks:
    1. Presence of required target and ID columns.
    2. Missing value evaluation.
    3. Duplicate row evaluation.
    4. Target binary validity (must be {0, 1}).
    """
    if verbose:
        print("[Preprocessing Validation] Running data validation checks...")

    # 1. Column existence
    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Missing target column '{TARGET_COLUMN}' in dataset.")
    if ID_COLUMN not in df.columns:
        raise ValueError(f"Missing ID column '{ID_COLUMN}' in dataset.")

    # 2. Missing values check
    missing_count = df.isnull().sum().sum()
    if missing_count > 0:
        if verbose:
            print(f"  [Warning] Found {missing_count} missing values across DataFrame.")
    else:
        if verbose:
            print("  [Pass] Zero missing values detected across all columns.")

    # 3. Duplicate rows check
    duplicates = df.duplicated().sum()
    if duplicates > 0:
        if verbose:
            print(f"  [Warning] Detected {duplicates} exact duplicate rows.")
    else:
        if verbose:
            print("  [Pass] Zero duplicate rows detected.")

    # 4. Target validity
    unique_targets = set(df[TARGET_COLUMN].dropna().unique())
    if not unique_targets.issubset({0, 1}):
        raise ValueError(
            f"Target contains invalid classes: {unique_targets}. Expected only {{0, 1}}."
        )
    if verbose:
        print(f"  [Pass] Target column '{TARGET_COLUMN}' is strictly binary {unique_targets}.")

    return True


def clean_categorical_features(df: pd.DataFrame, verbose: bool = False) -> pd.DataFrame:
    """
    Standardizes documented and undocumented categorical levels in demographic features.
    
    Rationale:
    - EDUCATION:
      Documented: 1=Graduate School, 2=University, 3=High School, 4=Others.
      The raw dataset contains undocumented values {0, 5, 6} (345 records, 1.15%).
      In standard risk modeling, undocumented values are mapped into Category 4 ("Others").
    - MARRIAGE:
      Documented: 1=Married, 2=Single, 3=Others.
      The raw dataset contains 54 records with value 0.
      These are mapped into Category 3 ("Others").
    """
    df_clean = df.copy()

    if "EDUCATION" in df_clean.columns:
        # Map {0, 5, 6} to 4 (Others)
        raw_edu_counts = df_clean["EDUCATION"].value_counts().to_dict()
        df_clean["EDUCATION"] = df_clean["EDUCATION"].replace({0: 4, 5: 4, 6: 4})
        if verbose:
            print(f"  [Clean] EDUCATION consolidated. Raw distribution: {raw_edu_counts}")

    if "MARRIAGE" in df_clean.columns:
        # Map {0} to 3 (Others)
        raw_mar_counts = df_clean["MARRIAGE"].value_counts().to_dict()
        df_clean["MARRIAGE"] = df_clean["MARRIAGE"].replace({0: 3})
        if verbose:
            print(f"  [Clean] MARRIAGE consolidated. Raw distribution: {raw_mar_counts}")

    return df_clean


def preprocess_data(
    df: pd.DataFrame,
    is_training: bool = True,
    verbose: bool = True,
) -> tuple[pd.DataFrame, pd.Series | None]:
    """
    Executes the full preprocessing pipeline:
    1. Validates raw DataFrame.
    2. Drops non-predictive ID column to prevent identifier leakage.
    3. Standardizes categorical columns (EDUCATION, MARRIAGE).
    4. Separates target variable y from feature matrix X.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Raw input dataframe.
    is_training : bool, default=True
        If True, extracts target y. If False (inference), y is None.
    verbose : bool, default=True
        Whether to print preprocessing status.
        
    Returns:
    --------
    X : pd.DataFrame
        Cleaned feature matrix without ID and without TARGET.
    y : pd.Series or None
        Target array if is_training=True, otherwise None.
    """
    if verbose:
        print("[Preprocessing] Starting data preprocessing...")

    # Copy to prevent mutation of the input dataset
    data = df.copy()

    # 1. Validation
    if is_training:
        validate_raw_data(data, verbose=verbose)

    # 2. Extract and separate Target
    y = None
    if TARGET_COLUMN in data.columns and is_training:
        y = data[TARGET_COLUMN].astype(int)
        data = data.drop(columns=[TARGET_COLUMN])
        if verbose:
            print(f"  [Step 1] Target '{TARGET_COLUMN}' separated from feature matrix.")
    elif TARGET_COLUMN in data.columns and not is_training:
        # Inference with target present (e.g. testing)
        data = data.drop(columns=[TARGET_COLUMN])

    # 3. Drop ID column to avoid data leakage
    if ID_COLUMN in data.columns:
        data = data.drop(columns=[ID_COLUMN])
        if verbose:
            print(f"  [Step 2] Dropped identifier column '{ID_COLUMN}' (zero leakage).")

    # 4. Standardize categorical features
    data = clean_categorical_features(data, verbose=verbose)
    if verbose:
        print("  [Step 3] Categorical features standardized.")

    # 5. Ensure numeric data types for all remaining features
    for col in data.columns:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    # Check for NaN introduced by conversion
    n_nans = data.isnull().sum().sum()
    if n_nans > 0:
        raise ValueError(f"Numeric conversion introduced {n_nans} NaN values in feature matrix.")

    if verbose:
        print(f"  [Complete] Feature matrix ready with shape: {data.shape}")

    return data, y


if __name__ == "__main__":
    from src.data_loader import load_uci_credit_card_data

    raw_df = load_uci_credit_card_data(verbose=False)
    X, y = preprocess_data(raw_df, is_training=True, verbose=True)
    print(f"\nFinal Preprocessed X shape: {X.shape}, y shape: {y.shape}")
    print("Columns in X:\n", list(X.columns))
