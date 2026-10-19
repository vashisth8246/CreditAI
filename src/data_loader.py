"""
CreditAI: Data Loader Module
Loads and verifies the UCI Default of Credit Card Clients dataset from Excel.
Handles header alignment, column cleaning, and diagnostic summary printing.
"""

from pathlib import Path
import pandas as pd

from src.config import (
    PRIMARY_DATA_PATH,
    LEGACY_DATA_PATH,
    ROOT_DIR,
    TARGET_COLUMN,
    ID_COLUMN,
)


def find_dataset_path(custom_path: str | Path | None = None) -> Path:
    """
    Locates the dataset file using prioritized search locations.
    Fails clearly with a helpful error message if no file is found.
    """
    if custom_path:
        p = Path(custom_path)
        if p.exists():
            return p
        raise FileNotFoundError(f"[CreditAI] Specified dataset file not found at: {custom_path}")

    # Check primary configured path
    if PRIMARY_DATA_PATH.exists():
        return PRIMARY_DATA_PATH

    # Check legacy path
    if LEGACY_DATA_PATH.exists():
        return LEGACY_DATA_PATH

    # Recursive fallback search inside data/ or Data/
    for candidate in ROOT_DIR.glob("**/*.xls"):
        if "default of credit card clients" in candidate.name.lower():
            return candidate

    raise FileNotFoundError(
        "[CreditAI Error] The UCI Credit Card dataset ('default of credit card clients.xls') "
        f"was not found in {PRIMARY_DATA_PATH} or {LEGACY_DATA_PATH}.\n"
        "Please ensure the dataset exists in data/credit_default/."
    )


def load_uci_credit_card_data(
    file_path: str | Path | None = None,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Loads the UCI Default of Credit Card Clients dataset from the .xls file.
    
    Parameters:
    -----------
    file_path : str or Path, optional
        Custom path to the Excel file. If None, uses find_dataset_path().
    verbose : bool, default=True
        Whether to print diagnostic dataset statistics upon loading.
        
    Returns:
    --------
    pd.DataFrame
        The loaded and validated raw DataFrame (30,000 rows, 25 columns).
    """
    target_path = find_dataset_path(file_path)
    if verbose:
        print(f"[CreditAI Data Loader] Loading dataset from: {target_path}")

    # In this dataset, Row 0 contains variable codes (X1, X2...) while Row 1
    # contains the true feature names (ID, LIMIT_BAL, SEX, ... default payment next month).
    # header=1 instructs pandas to read row index 1 as the true header.
    try:
        df = pd.read_excel(target_path, header=1)
    except Exception as exc:
        raise RuntimeError(
            f"[CreditAI Data Loader] Failed to read Excel file at {target_path}.\n"
            f"Error details: {exc}"
        ) from exc

    # Clean whitespace in column names if any
    df.columns = [str(c).strip() for c in df.columns]

    # Verify key columns exist
    if TARGET_COLUMN not in df.columns:
        raise ValueError(
            f"[CreditAI Data Loader] Expected target column '{TARGET_COLUMN}' not found in columns: {list(df.columns)}"
        )
    if ID_COLUMN not in df.columns:
        raise ValueError(
            f"[CreditAI Data Loader] Expected ID column '{ID_COLUMN}' not found in columns: {list(df.columns)}"
        )

    if verbose:
        print("=" * 70)
        print("CREDITAI RAW DATASET DIAGNOSTICS")
        print("=" * 70)
        print(f"Shape: {df.shape[0]:,} rows x {df.shape[1]} columns")
        print(f"Total Columns ({len(df.columns)}): {list(df.columns)}")
        print("\nMissing Values Summary:")
        null_counts = df.isnull().sum()
        total_nulls = null_counts.sum()
        if total_nulls == 0:
            print("  -> Exactly 0 missing values detected across all columns.")
        else:
            print(null_counts[null_counts > 0])

        duplicate_count = df.duplicated().sum()
        print(f"\nDuplicate Rows: {duplicate_count}")

        print(f"\nTarget Variable ('{TARGET_COLUMN}') Distribution:")
        target_counts = df[TARGET_COLUMN].value_counts().sort_index()
        target_pct = df[TARGET_COLUMN].value_counts(normalize=True).sort_index() * 100
        for val, count in target_counts.items():
            meaning = "No Default (Repaid)" if val == 0 else "Default"
            print(f"  Class {val} ({meaning}): {count:,} records ({target_pct[val]:.2f}%)")
        print(f"  Class Imbalance Ratio (Non-default : Default): {target_counts[0] / target_counts[1]:.2f} : 1")
        print("=" * 70)

    return df


if __name__ == "__main__":
    # Test loading when running standalone
    df_raw = load_uci_credit_card_data(verbose=True)
    print("\nFirst 3 rows:")
    print(df_raw.head(3))
