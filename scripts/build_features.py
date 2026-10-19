from pathlib import Path
import sys
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.features.financial_features import engineer_financial_features
if __name__=="__main__":
    data=ROOT/"data"/"synthetic_phase1_1"; tx=pd.read_csv(data/"transactions.csv",parse_dates=["date"])
    engineered=engineer_financial_features(tx,as_of_date="2025-01-01",observation_start="2024-01-01"); engineered.to_csv(data/"borrower_features.csv",index=False)
    print(f"Saved {len(engineered)} borrower rows with {engineered.shape[1]-1} features")
