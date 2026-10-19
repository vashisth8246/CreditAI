"""Phase 1.2 nested validation and signal diagnostics for synthetic data only."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold,train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.metrics import brier_score_loss
from src.features.financial_features import feature_matrix,engineer_financial_features
from src.models.evaluate import evaluate_probabilities
from src.models.train import _select_f1_threshold,SEED
from src.calibration.calibrate import PlattCalibrator
from src.data.generate import generate_synthetic_data

CV_SEED=20261009
FRESH_HOLDOUT_SEED=20261010

def candidate_models(seed=SEED):
    models={"Prevalence Dummy":DummyClassifier(strategy="prior"),
            "Logistic Regression":make_pipeline(StandardScaler(),LogisticRegression(max_iter=1000,class_weight="balanced",random_state=seed)),
            "Random Forest":RandomForestClassifier(n_estimators=160,max_depth=8,min_samples_leaf=5,class_weight="balanced",random_state=seed,n_jobs=2)}
    try:
        from xgboost import XGBClassifier
        models["XGBoost"]=XGBClassifier(n_estimators=140,max_depth=3,learning_rate=.045,subsample=.85,colsample_bytree=.85,reg_lambda=2,eval_metric="logloss",random_state=seed,n_jobs=2)
    except ImportError:
        pass
    return models

def make_nested_splits(y,n_splits=5,seed=CV_SEED):
    """Return positional outer fold indices; every record is test once."""
    cv=StratifiedKFold(n_splits=n_splits,shuffle=True,random_state=seed)
    return list(cv.split(np.zeros(len(y)),np.asarray(y)))

def exclude_historical_test(features,outcomes,historical_splits):
    """Keep Phase 1.1 test borrowers out of Phase 1.2 development analysis."""
    if "split" not in historical_splits or "borrower_id" not in historical_splits: raise ValueError("Historical split assignments are required")
    quarantined=set(historical_splits.loc[historical_splits.split=="test","borrower_id"])
    dev=features.loc[~features.borrower_id.isin(quarantined)].reset_index(drop=True)
    labels=outcomes.loc[~outcomes.borrower_id.isin(quarantined)].copy()
    if set(dev.borrower_id)&quarantined or set(labels.borrower_id)&quarantined: raise AssertionError("Historical test data entered development set")
    return dev,labels,quarantined

def bootstrap_feature_associations(X,y,n_boot=1000,seed=CV_SEED):
    """Point-biserial feature/label association with paired bootstrap percentile CI."""
    from scipy.stats import pointbiserialr
    rng=np.random.default_rng(seed); y=np.asarray(y,dtype=int); n=len(y); rows=[]
    samples=rng.integers(0,n,size=(n_boot,n))
    for col in X.columns:
        x=pd.to_numeric(X[col],errors="coerce").to_numpy(dtype=float)
        r=float(pointbiserialr(x,y).statistic) if np.std(x)>0 and np.std(y)>0 else np.nan
        xb=x[samples]; yb=y[samples]
        xm=xb.mean(axis=1); ym=yb.mean(axis=1)
        cov=((xb-xm[:,None])*(yb-ym[:,None])).mean(axis=1)
        den=xb.std(axis=1)*yb.std(axis=1)
        boot=np.divide(cov,den,out=np.full(n_boot,np.nan),where=den>0)
        lo,hi=np.nanquantile(boot,[.025,.975]) if np.isfinite(boot).any() else (np.nan,np.nan)
        rows.append({"feature":col,"point_biserial_r":r,"bootstrap_95ci_low":lo,"bootstrap_95ci_high":hi,"bootstrap_replicates":n_boot,"n":n})
    return pd.DataFrame(rows).sort_values("point_biserial_r",key=lambda s:s.abs(),ascending=False)

def wilson_interval(successes,n,z=1.959963984540054):
    if n<=0:return (np.nan,np.nan)
    p=successes/n; den=1+z*z/n; mid=(p+z*z/(2*n))/den; half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return (mid-half,mid+half)

def income_cv_risk_bands(features,outcomes):
    """Describe default rates across income-CV quartiles, cutpoints from X only."""
    d=features[["borrower_id","income_cv"]].merge(outcomes[["borrower_id","default_90d"]],on="borrower_id",validate="one_to_one")
    d["risk_band"]=pd.qcut(d.income_cv,4,duplicates="drop")
    rows=[]
    for band,g in d.groupby("risk_band",observed=True):
        lo,hi=wilson_interval(int(g.default_90d.sum()),len(g))
        rows.append({"predefined_feature":"income_cv","risk_band":str(band),"borrowers":len(g),"default_rate":float(g.default_90d.mean()),"wilson_95ci_low":lo,"wilson_95ci_high":hi,"band_cutpoints_fit_without_labels":True})
    return pd.DataFrame(rows)

def _fit_select_calibrate(X,y,fit_idx,val_idx,seed):
    models=candidate_models(seed); rows=[]; val_preds={}
    for name,model in models.items():
        model.fit(X.iloc[fit_idx],y.iloc[fit_idx]); p=model.predict_proba(X.iloc[val_idx])[:,1]; val_preds[name]=p
        rows.append({"model":name,**evaluate_probabilities(y.iloc[val_idx],p),"selection_validation_prevalence":float(y.iloc[val_idx].mean())})
    selected=max(rows,key=lambda row:row["roc_auc"])["model"]
    cal=PlattCalibrator().fit(val_preds[selected],y.iloc[val_idx])
    calibrated=cal.predict_proba(val_preds[selected]); threshold=_select_f1_threshold(y.iloc[val_idx],calibrated)
    return models,rows,selected,cal,threshold

def run_phase12(features,outcomes,historical_splits,output_dir,holdout_borrowers=240,n_boot=1000):
    """Nested 5-fold CV on nonhistorical-test cohort plus a fresh seeded cohort."""
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    dev,labels,quarantined=exclude_historical_test(features,outcomes,historical_splits)
    d=dev.merge(labels[["borrower_id","default_90d"]],on="borrower_id",validate="one_to_one")
    if d.borrower_id.nunique()!=len(d): raise ValueError("Borrowers must be unique")
    X=feature_matrix(dev); y=d.default_90d.astype(int).reset_index(drop=True)
    fold_rows=[]; selected_rows=[]
    for fold,(outer_train,outer_test) in enumerate(make_nested_splits(y),start=1):
        fit_idx,val_idx=train_test_split(outer_train,test_size=.20,stratify=y.iloc[outer_train],random_state=CV_SEED+fold)
        models,val_rows,selected,cal,threshold=_fit_select_calibrate(X,y,fit_idx,val_idx,CV_SEED+fold)
        test_y=y.iloc[outer_test]
        outer_prev=float(test_y.mean())
        for model_row in val_rows:
            name=model_row["model"]; p=models[name].predict_proba(X.iloc[outer_test])[:,1]
            fold_rows.append({"fold":fold,"stage":"outer_test","model":name,"prediction":"raw","outer_test_prevalence":outer_prev,"selected_model_this_fold":selected,"validation_threshold":threshold,**evaluate_probabilities(test_y,p,.5)})
        chosen_p=models[selected].predict_proba(X.iloc[outer_test])[:,1]; chosen_cal=cal.predict_proba(chosen_p)
        fold_rows.append({"fold":fold,"stage":"outer_test","model":selected,"prediction":"calibrated","outer_test_prevalence":outer_prev,"selected_model_this_fold":selected,"validation_threshold":threshold,**evaluate_probabilities(test_y,chosen_cal,threshold)})
        selected_rows.append({"fold":fold,"selected_on_validation":selected,"validation_prevalence":float(y.iloc[val_idx].mean()),"outer_test_prevalence":outer_prev,"threshold_selected_on_validation":threshold,"outer_test_borrowers":len(outer_test)})
    cv_frame=pd.DataFrame(fold_rows); cv_frame.to_csv(out/"cross_validation_fold_metrics.csv",index=False)
    cv_summary=cv_frame.groupby(["model","prediction"],as_index=False).agg(folds=("fold","nunique"),roc_auc_mean=("roc_auc","mean"),roc_auc_sd=("roc_auc","std"),pr_auc_mean=("pr_auc","mean"),pr_auc_sd=("pr_auc","std"),brier_mean=("brier_score","mean"),brier_sd=("brier_score","std"),default_prevalence_mean=("outer_test_prevalence","mean"))
    cv_summary.to_csv(out/"cross_validation_summary.csv",index=False); pd.DataFrame(selected_rows).to_csv(out/"fold_model_selection.csv",index=False)
    assoc=bootstrap_feature_associations(X,y,n_boot=n_boot); assoc.to_csv(out/"feature_associations.csv",index=False)
    bands=income_cv_risk_bands(dev,labels); bands.to_csv(out/"income_cv_risk_bands.csv",index=False)
    # Final model selection/calibration/threshold are confined to this development validation slice.
    fit_idx,val_idx=train_test_split(np.arange(len(X)),test_size=.20,stratify=y,random_state=CV_SEED)
    models,val_rows,selected,cal,threshold=_fit_select_calibrate(X,y,fit_idx,val_idx,CV_SEED)
    tx_hold,label_hold=generate_synthetic_data(n_borrowers=holdout_borrowers,seed=FRESH_HOLDOUT_SEED)
    tx_hold["borrower_id"]="P12-"+tx_hold.borrower_id.astype(str); label_hold["borrower_id"]="P12-"+label_hold.borrower_id.astype(str)
    fresh_features=engineer_financial_features(tx_hold,as_of_date="2025-01-01",observation_start="2024-01-01")
    fresh_labels=label_hold.default_90d.astype(int).reset_index(drop=True); Xfresh=feature_matrix(fresh_features)
    final_rows=[]
    for name,model in models.items():
        p=model.predict_proba(Xfresh)[:,1]
        final_rows.append({"model":name,"prediction":"raw","fresh_holdout_prevalence":float(fresh_labels.mean()),"validation_selected_model":selected,"validation_threshold":threshold,**evaluate_probabilities(fresh_labels,p,.5)})
    raw=models[selected].predict_proba(Xfresh)[:,1]; calibrated=cal.predict_proba(raw)
    final_rows.append({"model":selected,"prediction":"calibrated","fresh_holdout_prevalence":float(fresh_labels.mean()),"validation_selected_model":selected,"validation_threshold":threshold,**evaluate_probabilities(fresh_labels,calibrated,threshold)})
    pd.DataFrame(final_rows).to_csv(out/"fresh_holdout_metrics.csv",index=False)
    hold_prev=float(y.iloc[fit_idx].mean()); pd.DataFrame([{"model":"Prevalence Dummy","prediction":"train prevalence","fresh_holdout_prevalence":float(fresh_labels.mean()),"validation_selected_model":selected,"validation_threshold":threshold,**evaluate_probabilities(fresh_labels,np.full(len(fresh_labels),hold_prev),threshold)}]).to_csv(out/"fresh_holdout_baseline.csv",index=False)
    result={"development_borrowers":len(dev),"quarantined_historical_test_borrowers":len(quarantined),"fresh_holdout_borrowers":len(label_hold),"fresh_holdout_transactions":len(tx_hold),"development_default_prevalence":float(y.mean()),"fresh_holdout_default_prevalence":float(fresh_labels.mean()),"folds":5,"fold_selections":selected_rows,"final_validation_selected_model":selected,"final_validation_selected_threshold":threshold,"fresh_holdout_seed":FRESH_HOLDOUT_SEED,"cv_seed":CV_SEED,"bootstrap_seed":CV_SEED,"bootstrap_replicates":n_boot,"feature_associations":assoc.to_dict(orient="records"),"cv_summary":cv_summary.to_dict(orient="records"),"fresh_holdout_metrics":final_rows,"limitations":"All results are synthetic; historical Phase 1.1 test borrowers were excluded. New-seed holdout validates only repeatability under the same hand-authored simulator, not real repayment prediction."}
    (out/"phase1_2_summary.json").write_text(json.dumps(result,indent=2,default=str),encoding="utf8")
    return result
