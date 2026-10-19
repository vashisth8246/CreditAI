"""Load the Phase-1 bundle and score transaction histories."""
from pathlib import Path
import joblib
import pandas as pd
from src.features.financial_features import engineer_financial_features,feature_matrix

def predict_risk(transaction_dataframe, as_of_date=None, model_path=None):
    path=Path(model_path) if model_path else Path(__file__).resolve().parents[2]/"models"/"synthetic_phase1_1"/"creditai_risk_engine.joblib"
    bundle=joblib.load(path)
    cutoff=pd.Timestamp(as_of_date) if as_of_date is not None else pd.to_datetime(transaction_dataframe["date"]).max()+pd.Timedelta(days=1)
    months=int(bundle["metadata"].get("observation_window_months",12)); start=cutoff-pd.DateOffset(months=months)
    feats=engineer_financial_features(transaction_dataframe,as_of_date=cutoff,observation_start=start); X=feature_matrix(feats)
    p=float(bundle["calibrator"].predict_proba(bundle["model"].predict_proba(X)[:,1])[0])
    factors=[]
    if bundle.get("explainer") is not None:
        import numpy as np
        sv=bundle["explainer"].shap_values(X)
        if isinstance(sv,list): sv=sv[-1]
        vals=np.asarray(sv); vals=vals[0,:,1] if vals.ndim==3 else vals.reshape(-1)
        factors=[{"feature":str(k),"contribution":float(v),"direction":"increases risk" if v>0 else "reduces risk"} for k,v in sorted(zip(X.columns,vals),key=lambda kv:abs(kv[1]),reverse=True)[:6]]
    return {"default_probability":p,"risk_factors":factors,"model_version":bundle["metadata"]["model_version"]}
