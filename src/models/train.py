"""Train/evaluate synthetic model candidates without using the test split for decisions."""
from __future__ import annotations
import json,platform
from datetime import datetime,timezone
from importlib.metadata import PackageNotFoundError,version
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import brier_score_loss,f1_score,precision_score,recall_score
from src.features.financial_features import feature_matrix
from src.models.evaluate import evaluate_probabilities,risk_deciles
from src.calibration.calibrate import PlattCalibrator

SEED=42

def _select_f1_threshold(y,p):
    """Maximize validation F1; break ties by higher precision then threshold."""
    candidates=np.unique(np.r_[0.0,np.asarray(p),1.0+1e-12]); scored=[]
    for t in candidates:
        pred=np.asarray(p)>=t
        scored.append((f1_score(y,pred,zero_division=0),precision_score(y,pred,zero_division=0),float(t)))
    return max(scored)[2]

def train_pipeline(features,outcomes,output_root=None):
    root=Path(output_root) if output_root else Path(__file__).resolve().parents[2]
    merged=features.merge(outcomes,on="borrower_id",validate="one_to_one")
    if len(merged)!=len(features) or merged.default_90d.isna().any(): raise ValueError("Each feature row must have exactly one known synthetic outcome")
    if {"default_30d","default_60d","default_90d","loan_amount","loan_date","outcome_date"}.intersection(features.columns): raise ValueError("Target leakage detected")
    X=feature_matrix(features); y=merged.default_90d.astype(int).reset_index(drop=True); ids=features.borrower_id.reset_index(drop=True)
    all_idx=np.arange(len(X)); tr,rem=train_test_split(all_idx,test_size=.30,stratify=y,random_state=SEED); va,te=train_test_split(rem,test_size=.50,stratify=y.iloc[rem],random_state=SEED)
    Xtr,ytr=X.iloc[tr],y.iloc[tr]; Xva,yva=X.iloc[va],y.iloc[va]; Xte,yte=X.iloc[te],y.iloc[te]
    try:
        from xgboost import XGBClassifier
        xgb=XGBClassifier(n_estimators=140,max_depth=3,learning_rate=.045,subsample=.85,colsample_bytree=.85,reg_lambda=2,eval_metric="logloss",random_state=SEED,n_jobs=2)
        xgb_available=True
    except ImportError:
        xgb=None; xgb_available=False
    models={"Prevalence Dummy":DummyClassifier(strategy="prior"),"Logistic Regression":make_pipeline(StandardScaler(),LogisticRegression(max_iter=1000,class_weight="balanced",random_state=SEED)),"Random Forest":RandomForestClassifier(n_estimators=160,max_depth=8,min_samples_leaf=5,class_weight="balanced",random_state=SEED,n_jobs=2)}
    if xgb_available: models["XGBoost"]=xgb
    val_prob={}; val_rows=[]
    for name,model in models.items():
        model.fit(Xtr,ytr); p=model.predict_proba(Xva)[:,1]; val_prob[name]=p
        val_rows.append({"model":name,**evaluate_probabilities(yva,p,threshold=.5),"default_prevalence":float(yva.mean())})
    selected=max(val_rows,key=lambda r:r["roc_auc"])["model"]; model=models[selected]
    raw_val=val_prob[selected]; calibrator=PlattCalibrator().fit(raw_val,yva); cal_val=calibrator.predict_proba(raw_val)
    threshold=_select_f1_threshold(yva,cal_val)
    train_prev=float(ytr.mean()); baseline_val=np.full(len(yva),train_prev); baseline_test=np.full(len(yte),train_prev)
    val_prevalence=float(yva.mean()); test_prevalence=float(yte.mean())
    test_raw=model.predict_proba(Xte)[:,1]; test_cal=calibrator.predict_proba(test_raw)
    # The model, calibrator and threshold are frozen before this single test evaluation.
    phases=[]
    for r in val_rows: phases.append({"phase":"validation","prediction":"raw","default_prevalence":val_prevalence,**r})
    phases.append({"phase":"validation","model":selected,"prediction":"calibrated (in-sample fit)","default_prevalence":val_prevalence,**evaluate_probabilities(yva,cal_val,threshold=threshold)})
    for name,candidate in models.items():
        candidate_test=candidate.predict_proba(Xte)[:,1]
        phases.append({"phase":"test","model":name,"prediction":"raw","default_prevalence":test_prevalence,**evaluate_probabilities(yte,candidate_test,threshold=threshold)})
    phases.append({"phase":"test","model":selected,"prediction":"calibrated","default_prevalence":test_prevalence,**evaluate_probabilities(yte,test_cal,threshold=threshold)})
    model_dir=root/"models"/"synthetic_phase1_1"; report_dir=root/"reports"/"synthetic_phase1_1"
    model_dir.mkdir(parents=True,exist_ok=True); report_dir.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(phases).to_csv(report_dir/"model_comparison.csv",index=False)
    risk_deciles(yte,test_cal).to_csv(report_dir/"risk_deciles.csv",index=False)
    split_frame=pd.DataFrame({"borrower_id":ids,"split":""}); split_frame.loc[tr,"split"]="train"; split_frame.loc[va,"split"]="validation"; split_frame.loc[te,"split"]="test"; split_frame.to_csv(report_dir/"borrower_splits.csv",index=False)
    from sklearn.calibration import calibration_curve
    import matplotlib.pyplot as plt
    plt.figure(figsize=(6,5))
    for label,p in [("Raw",test_raw),("Calibrated",test_cal),("Train prevalence baseline",baseline_test)]:
        obs,pred=calibration_curve(yte,p,n_bins=6,strategy="quantile"); plt.plot(pred,obs,marker="o",label=label)
    plt.plot([0,1],[0,1],"--",color="gray"); plt.xlabel("Predicted PD"); plt.ylabel("Observed default rate"); plt.legend(); plt.tight_layout(); plt.savefig(report_dir/"calibration_curve.png",dpi=130); plt.close()
    pred_summary={}
    for name,p in [("raw",test_raw),("calibrated",test_cal)]: pred_summary[name]={"min":float(np.min(p)),"p10":float(np.quantile(p,.1)),"median":float(np.median(p)),"mean":float(np.mean(p)),"p90":float(np.quantile(p,.9)),"max":float(np.max(p)),"share_at_or_above_0_50":float(np.mean(p>=.5))}
    prevalence_brier=float(brier_score_loss(yte,baseline_test))
    package_versions={}
    for package in ["numpy","pandas","scikit-learn","xgboost","shap"]:
        try: package_versions[package]=version(package)
        except PackageNotFoundError: package_versions[package]="not installed"
    metrics_test={"prevalence_baseline":evaluate_probabilities(yte,baseline_test,threshold),"raw":evaluate_probabilities(yte,test_raw,threshold),"calibrated":evaluate_probabilities(yte,test_cal,threshold)}
    metadata={"model_version":"1.1.0-synthetic","model_type":selected,"training_dataset":"synthetic financial behavior only","training_date_utc":datetime.now(timezone.utc).isoformat(),"python_version":platform.python_version(),"package_versions":package_versions,"random_seed":SEED,"observation_window_months":12,"split_counts":{"train":len(tr),"validation":len(va),"test":len(te)},"default_prevalence":{"train":train_prev,"validation":val_prevalence,"test":test_prevalence},"feature_count":len(X.columns),"feature_names":list(X.columns),"selected_threshold":threshold,"threshold_objective":"maximize validation-set F1; ties favor precision then larger threshold; experimental only, not a lending policy","calibration":"Platt sigmoid fitted only on selected model's validation predictions","validation_calibration_is_in_sample":True,"validation_brier":{"raw":float(brier_score_loss(yva,raw_val)),"calibrated":float(brier_score_loss(yva,cal_val)),"train_prevalence_baseline":float(brier_score_loss(yva,baseline_val))},"test_metrics":metrics_test,"test_brier_baseline":prevalence_brier,"test_probability_distribution":pred_summary,"xgboost_available":xgb_available,"limitations":"Synthetic features and outcomes; no real lender or Indian thin-file validation."}
    explainer=None
    if selected in {"Random Forest","XGBoost"}:
        try:
            import shap
            from src.explainability.shap_explainer import explain_tree_model
            explainer=shap.TreeExplainer(model); explain_tree_model(model,Xva.reset_index(drop=True),list(X.columns),report_dir)
            metadata["shap_status"]="Global and local tree SHAP generated from selected model."
        except Exception as exc: metadata["shap_status"]=f"Unavailable: {type(exc).__name__}: {exc}"
    else: metadata["shap_status"]="Not applicable: validation selected prevalence baseline; no borrower-specific tree model was selected."
    bundle={"model":model,"calibrator":calibrator,"feature_names":list(X.columns),"metadata":metadata,"explainer":explainer,"decision_threshold":threshold}
    joblib.dump(bundle,model_dir/"creditai_risk_engine.joblib"); joblib.dump(calibrator,model_dir/"calibration_model.joblib")
    (model_dir/"feature_names.json").write_text(json.dumps(list(X.columns),indent=2),encoding="utf8"); (model_dir/"model_metadata.json").write_text(json.dumps(metadata,indent=2),encoding="utf8")
    pd.DataFrame([{ "split":s,"rows":len(a),"default_prevalence":float(y.iloc[a].mean())} for s,a in [("train",tr),("validation",va),("test",te)]]).to_csv(report_dir/"split_prevalence.csv",index=False)
    report=f"""# CreditAI Phase 1.1 synthetic model report

**Scope:** synthetic development records only. This does not validate risk for Indian lending or any real borrower population.

## Data splits and model choice

Train/validation/test counts are {len(tr)}/{len(va)}/{len(te)}. Default prevalence is {train_prev:.3f}/{val_prevalence:.3f}/{test_prevalence:.3f}. Models are selected by validation ROC-AUC; selected model: **{selected}**. Test set is not used to select models, calibrate probabilities, or choose the threshold. See `model_comparison.csv` for ROC-AUC, PR-AUC, KS, Gini, Brier, precision, recall, F1, confusion matrices, and phases. PR-AUC should be compared with the corresponding default prevalence; a prevalence-only ranking yields PR-AUC near prevalence.

## Calibration

The Platt sigmoid is fit to validation predictions only. Validation calibration metrics are in-sample and optimistic. On the untouched test set, raw/calibrated/prevalence-baseline Brier scores are {metrics_test['raw']['brier_score']:.4f}/{metrics_test['calibrated']['brier_score']:.4f}/{prevalence_brier:.4f}. A lower Brier score alone does not establish good calibration; inspect the held-out calibration curve and compare with the prevalence baseline. Test probabilities (raw/calibrated): `{json.dumps(pred_summary)}`. When the selected candidate is the constant-prevalence baseline, the fitted sigmoid remains approximately constant near validation prevalence; consequently all scores can be below 0.50 because synthetic default prevalence is far below one half. The fitted sigmoid is constrained to be non-decreasing so calibration cannot reverse the ranking.

## Experimental classification threshold

Threshold {threshold:.6f} maximizes validation F1 on calibrated validation predictions; ties prefer precision then higher threshold. This frozen threshold is evaluated on test once. It is an experiment, not a lending policy. Ranking metrics are threshold independent. Confusion matrices use this same threshold.

## Explainability and limitations

SHAP status: {metadata['shap_status']} Synthetic labels are probabilistic but are generated from observable synthetic-history aggregates, so the task measures recovery of the generator's assumptions, not real-world default risk. Features use transactions strictly before the January 1, 2025 loan date. See `data_generation_assumptions.md` and `phase_1_1_audit.md` for the audit trail.
"""
    (report_dir/"model_report.md").write_text(report,encoding="utf8")
    return bundle
