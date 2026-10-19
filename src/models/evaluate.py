"""Risk model metrics and decile analysis."""
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score,average_precision_score,brier_score_loss,f1_score,precision_score,recall_score,confusion_matrix

def evaluate_probabilities(y, p, threshold=.5):
    y=np.asarray(y); p=np.clip(np.asarray(p),0,1); auc=roc_auc_score(y,p)
    fpr,tpr,_=__import__('sklearn.metrics',fromlist=['roc_curve']).roc_curve(y,p)
    return {"roc_auc":float(auc),"pr_auc":float(average_precision_score(y,p)),"ks":float(np.max(tpr-fpr)),"gini":float(2*auc-1),"brier_score":float(brier_score_loss(y,p)),"f1":float(f1_score(y,p>=threshold,zero_division=0)),"precision":float(precision_score(y,p>=threshold,zero_division=0)),"recall":float(recall_score(y,p>=threshold,zero_division=0)),"threshold":threshold,"confusion_matrix":confusion_matrix(y,p>=threshold).tolist()}

def risk_deciles(y,p):
    d=pd.DataFrame({"observed_default":np.asarray(y),"predicted_pd":np.asarray(p)})
    d["risk_decile"]=pd.qcut(d.predicted_pd.rank(method="first"),10,labels=False)+1
    return d.groupby("risk_decile",as_index=False,observed=True).agg(borrowers=("observed_default","size"),mean_pd=("predicted_pd","mean"),observed_default_rate=("observed_default","mean"))
