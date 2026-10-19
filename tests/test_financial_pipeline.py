import numpy as np
import pandas as pd
import pytest
import hashlib
from pathlib import Path
from src.data.generate import generate_synthetic_data
from src.data.validation import validate_transactions
from src.features.financial_features import engineer_financial_features,feature_matrix,FEATURE_NAMES
from src.models.evaluate import evaluate_probabilities
from src.calibration.calibrate import PlattCalibrator

@pytest.fixture(scope="module")
def synthetic(): return generate_synthetic_data(160,42)

def test_transaction_schema_and_validation(synthetic):
    tx,_=synthetic; assert validate_transactions(tx)["valid"]
    bad=tx.copy(); bad.loc[0,"amount"]=-1
    with pytest.raises(ValueError): validate_transactions(bad)

def test_features_complete_and_leakage_safe(synthetic):
    tx,outcomes=synthetic; f=engineer_financial_features(tx,as_of_date="2025-01-01",observation_start="2024-01-01")
    assert f[FEATURE_NAMES].notna().all().all(); assert list(feature_matrix(f).columns)==FEATURE_NAMES
    with pytest.raises(ValueError): feature_matrix(f.merge(outcomes,on="borrower_id"))
    assert tx.date.max() < pd.Timestamp("2025-01-01")
    for col in ("outcome_date","default_30d","default_60d","default_90d","loan_amount"):
        with pytest.raises(ValueError): feature_matrix(f.assign(**{col:0}))

def test_train_predict_calibrate_and_reload(synthetic,tmp_path):
    from src.models.train import train_pipeline
    from src.models.predict import predict_risk
    tx,out=synthetic; features=engineer_financial_features(tx,as_of_date="2025-01-01",observation_start="2024-01-01")
    root=Path(__file__).resolve().parents[1]
    preserved=[root/"models"/"creditai_model.joblib",root/"models"/"feature_names.json",root/"models"/"model_metadata.json"]
    before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in preserved}
    bundle=train_pipeline(features,out,tmp_path)
    after={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in preserved}
    assert before==after
    assert 0 <= bundle["calibrator"].predict_proba(bundle["model"].predict_proba(feature_matrix(features).iloc[:1])[:,1])[0] <= 1
    scored=predict_risk(tx[tx.borrower_id==tx.borrower_id.iloc[0]],"2025-01-01",tmp_path/"models"/"synthetic_phase1_1"/"creditai_risk_engine.joblib")
    assert 0 <= scored["default_probability"] <= 1
    y=np.array([0,0,0,1,1,1]); cal=PlattCalibrator().fit([.1,.2,.3,.6,.7,.8],y)
    assert np.isfinite(cal.predict_proba([.15,.75])).all()
    assert cal.slope>=0 and cal.predict_proba([.15,.75])[0]<=cal.predict_proba([.15,.75])[1]
    inverted=PlattCalibrator().fit([.1,.2,.3,.6,.7,.8],[1,1,1,0,0,0])
    assert inverted.slope==0
    assert "roc_auc" in evaluate_probabilities(y,[.1,.2,.3,.6,.7,.8])
    splits=pd.read_csv(tmp_path/"reports"/"synthetic_phase1_1"/"borrower_splits.csv")
    assert splits.borrower_id.is_unique
    assert splits.groupby("borrower_id").split.nunique().max()==1
    assert bundle["metadata"]["validation_calibration_is_in_sample"] is True
    assert bundle["metadata"]["threshold_objective"].startswith("maximize validation-set F1")

def test_calendar_gaps_income_categories_and_distinct_features():
    tx=pd.DataFrame([
        {"borrower_id":"A","transaction_id":"1","date":"2024-01-05","transaction_type":"CREDIT","amount":1000,"category":"SALARY","counterparty":"Employer","balance_after_transaction":1000},
        {"borrower_id":"A","transaction_id":"2","date":"2024-01-06","transaction_type":"CREDIT","amount":500,"category":"TRANSFER_IN","counterparty":"Own account","balance_after_transaction":1500},
        {"borrower_id":"A","transaction_id":"3","date":"2024-03-05","transaction_type":"CREDIT","amount":1000,"category":"OTHER_INCOME","counterparty":"Client","balance_after_transaction":2500},
    ])
    f=engineer_financial_features(tx,as_of_date="2024-04-01",observation_start="2024-01-01").iloc[0]
    assert f.total_income==2000
    assert f.income_months==2
    assert f.avg_monthly_income==pytest.approx(2000/3)
    assert len(FEATURE_NAMES)==len(set(FEATURE_NAMES))==40
    assert not {"cashflow_gap_count","debt_payment_ratio","income_consistency"}.intersection(FEATURE_NAMES)

def test_cutoff_and_seed_reproducibility(synthetic):
    tx,_=synthetic
    cutoff_features=engineer_financial_features(tx,as_of_date="2024-07-01",observation_start="2024-01-01")
    assert cutoff_features.transaction_count.sum()==int((tx.date<pd.Timestamp("2024-07-01")).sum())
    a,b=generate_synthetic_data(12,123); aa,bb=generate_synthetic_data(12,123)
    pd.testing.assert_frame_equal(a,aa); pd.testing.assert_frame_equal(b,bb)
    assert (bb.default_30d<=bb.default_60d).all() and (bb.default_60d<=bb.default_90d).all()
    defaults=bb[bb.default_90d==1]
    assert ((defaults.outcome_date>defaults.loan_date)&(defaults.outcome_date<=defaults.loan_date+pd.Timedelta(days=90))).all()
