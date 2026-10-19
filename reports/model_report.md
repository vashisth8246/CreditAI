# CreditAI synthetic risk pipeline report

**Development only:** this experiment uses synthetic transactions and labels, not observed borrower records. It does not establish performance for Indian lending.

Selected on validation ROC-AUC: **Random Forest**. Selection did not use test data.

## Validation comparison

model,roc_auc,pr_auc,ks,gini,brier_score,f1,precision,recall,threshold
Random Forest,0.589517625231911,0.2759127302478931,0.2152133580705009,0.17903525046382196,0.19413664243996404,0.2857142857142857,0.25925925925925924,0.3181818181818182,0.5
XGBoost,0.5366419294990723,0.23514273770003577,0.13636363636363635,0.0732838589981446,0.16231846809387207,0.07692307692307693,0.25,0.045454545454545456,0.5
Logistic Regression,0.476808905380334,0.22184356831595498,0.1103896103896104,-0.04638218923933202,0.2357947111836724,0.18518518518518517,0.15625,0.22727272727272727,0.5


## Untouched test metrics

version,roc_auc,pr_auc,ks,gini,brier_score,f1,precision,recall,threshold
raw,0.5396825396825398,0.2356929833529736,0.1385281385281385,0.07936507936507953,0.19944661642360426,0.2127659574468085,0.19230769230769232,0.23809523809523808,0.5
calibrated,0.5396825396825398,0.2356929833529736,0.1385281385281385,0.07936507936507953,0.14410773624164708,0.0,0.0,0.0,0.5


Validation Brier: raw 0.1941; calibrated 0.1471. Calibration fits a sigmoid to validation scores; validation calibration metrics are in-sample. Test metrics are reported separately.

Confusion matrix threshold: 0.50. See risk_deciles.csv and calibration_curve.png.
