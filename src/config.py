"""
CreditAI: Configuration Module
Defines project paths, feature groups, random seed, and dataset constants.
All paths are relative to the project root using pathlib.
"""

from pathlib import Path

# -----------------------------------------------------------------------------
# 1. Project Directory Structure
# -----------------------------------------------------------------------------
# ROOT_DIR is the top-level CreditAI directory
ROOT_DIR = Path(__file__).resolve().parent.parent

# Data directory
DATA_DIR = ROOT_DIR / "data"

# Primary raw dataset candidates (checked in order)
PRIMARY_DATA_PATH = DATA_DIR / "credit_default" / "default of credit card clients.xls"
LEGACY_DATA_PATH = (
    ROOT_DIR
    / "Data"
    / "credit_default"
    / "Dataset #2 \u2014 UCI Default of Credit Card Clients"
    / "default+of+credit+card+clients"
    / "default of credit card clients.xls"
)

# Output directories
MODELS_DIR = ROOT_DIR / "models"
REPORTS_DIR = ROOT_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
NOTEBOOKS_DIR = ROOT_DIR / "notebooks"

# Ensure output directories exist
MODELS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# 2. Saved Artifact File Paths
# -----------------------------------------------------------------------------
SAVED_MODEL_PATH = MODELS_DIR / "creditai_model.joblib"
CALIBRATED_MODEL_PATH = MODELS_DIR / "creditai_calibrated_model.joblib"
FEATURE_NAMES_PATH = MODELS_DIR / "feature_names.json"
MODEL_METADATA_PATH = MODELS_DIR / "model_metadata.json"

# -----------------------------------------------------------------------------
# 3. Target and Identifier Constants
# -----------------------------------------------------------------------------
TARGET_COLUMN = "default payment next month"
ID_COLUMN = "ID"

# -----------------------------------------------------------------------------
# 4. Feature Groups Definition
# -----------------------------------------------------------------------------
# Credit limit facility
CREDIT_LIMIT_FEATURE = ["LIMIT_BAL"]

# Demographic features
DEMOGRAPHIC_FEATURES = ["SEX", "EDUCATION", "MARRIAGE", "AGE"]

# Monthly repayment status (-2 = inactive, -1 = paid in full, 0 = revolving, 1-8 = delay months)
# Note: PAY_0 corresponds to September, PAY_2 to August, etc.
REPAYMENT_STATUS_FEATURES = [
    "PAY_0",
    "PAY_2",
    "PAY_3",
    "PAY_4",
    "PAY_5",
    "PAY_6",
]

# Monthly statement bill amounts (NT$)
BILL_AMT_FEATURES = [
    "BILL_AMT1",
    "BILL_AMT2",
    "BILL_AMT3",
    "BILL_AMT4",
    "BILL_AMT5",
    "BILL_AMT6",
]

# Monthly previous payment amounts (NT$)
PAY_AMT_FEATURES = [
    "PAY_AMT1",
    "PAY_AMT2",
    "PAY_AMT3",
    "PAY_AMT4",
    "PAY_AMT5",
    "PAY_AMT6",
]

# All raw input features expected from the raw file (excluding ID and TARGET)
RAW_FEATURE_COLUMNS = (
    CREDIT_LIMIT_FEATURE
    + DEMOGRAPHIC_FEATURES
    + REPAYMENT_STATUS_FEATURES
    + BILL_AMT_FEATURES
    + PAY_AMT_FEATURES
)

# -----------------------------------------------------------------------------
# 5. Train / Validation / Test Split Configuration
# -----------------------------------------------------------------------------
# 70% Train, 15% Validation, 15% Test
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

RANDOM_STATE = 42
