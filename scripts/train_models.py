from pathlib import Path
import sys
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.models.train import train_pipeline
if __name__=="__main__":
    data=ROOT/"data"/"synthetic_phase1_1"; train_pipeline(pd.read_csv(data/"borrower_features.csv"),pd.read_csv(data/"outcomes.csv",parse_dates=["loan_date","outcome_date"]),ROOT)
    print("Training, evaluation, calibration, and artifact saving complete.")
