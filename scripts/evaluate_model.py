from pathlib import Path
import sys
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.models.predict import predict_risk
from src.features.financial_features import engineer_financial_features
if __name__=="__main__":
    d=ROOT/"data"/"synthetic_phase1_1"; tx=pd.read_csv(d/"transactions.csv",parse_dates=["date"])
    sample=tx[tx.borrower_id==tx.borrower_id.iloc[0]]
    print(predict_risk(sample,as_of_date="2025-01-01",model_path=ROOT/"models"/"synthetic_phase1_1"/"creditai_risk_engine.joblib"))
