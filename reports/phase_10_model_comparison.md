# Phase 10 Model Comparison Report
**Project:** CreditAI  
**Phase:** 10 — Unified Dataset Audit, KNN Model Development, Feature Engineering, Evaluation and Lender Research  
**Dataset:** Default of Credit Card Clients (Taiwan, DS003)  
**Evaluation Protocol:** Stratified 70% Train (21,000) / 15% Validation (4,500) / 15% Test (4,500), random_state=42  
**Test Set Size:** 4,500 samples (996 defaults, 22.13% positive prevalence)  

---

## 1. Executive Model Comparison Table

All models were fitted strictly on the 21,000 training observations, calibrated on the 4,500 validation split, and evaluated on the untouched 4,500 held-out test split.

| Model | Status | ROC-AUC | PR-AUC | Brier Score | Log Loss | KS Statistic | Gini | Accuracy | Precision | Recall | F1-Score |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **XGBoost (Calibrated)** | Primary (Calibrated) | **0.7807** | **0.5588** | 0.1441 | 0.4508 | 0.4255 | 0.5613 | 0.7887 | 0.9091 | 0.0502 | 0.0951 |
| **XGBoost (Raw)** | Primary (Raw) | **0.7807** | **0.5588** | 0.1709 | 0.5205 | 0.4255 | 0.5613 | 0.7607 | 0.4692 | **0.6185** | **0.5336** |
| **Random Forest** | Tree Benchmark | 0.7797 | 0.5594 | **0.1348** | **0.4292** | **0.4285** | 0.5593 | **0.8162** | 0.6568 | 0.3554 | 0.4612 |
| **KNN (Calibrated)** | Phase 10 Research | 0.7649 | 0.5235 | 0.1387 | 0.4472 | 0.4078 | 0.5298 | 0.8111 | 0.6547 | 0.3102 | 0.4210 |
| **KNN (Raw)** | Phase 10 Research | 0.7649 | 0.5235 | 0.1385 | 0.4686 | 0.4078 | 0.5298 | 0.8111 | 0.6372 | 0.3404 | 0.4437 |
| **KNN (Optimal Threshold @ 0.28)** | Phase 10 (F1-tuned) | 0.7649 | 0.5235 | 0.1387 | 0.4472 | 0.4078 | 0.5298 | 0.7827 | 0.5082 | 0.5602 | **0.5330** |
| **Logistic Regression** | Linear Baseline | 0.7533 | 0.4973 | 0.1431 | 0.4512 | 0.4022 | 0.5066 | 0.8009 | 0.6025 | 0.2952 | 0.3962 |
| **Prevalence Baseline** | Zero-Skill Baseline | 0.5000 | 0.2213 | 0.1723 | 0.5286 | 0.0211 | 0.0000 | 0.7787 | 0.0000 | 0.0000 | 0.0000 |

---

## 2. Key Scientific Findings

1. **KNN Performance vs. Baselines:**
   - KNN achieves **ROC-AUC of 0.7649** and **PR-AUC of 0.5235**, clearly surpassing Logistic Regression (ROC-AUC 0.7533, PR-AUC 0.4973).
   - XGBoost remains the strongest overall model on discrimination metrics (ROC-AUC 0.7807, PR-AUC 0.5588).
   - Random Forest achieved the lowest raw Brier score (0.1348) and lowest Log Loss (0.4292).
2. **Probability Calibration for KNN:**
   - Platt scaling (fitted on validation raw scores) improved KNN Log Loss from **0.4686 down to 0.4472** (a 4.6% improvement in posterior probability quality).
   - Calibrated Brier score remains stable at 0.1387 (well below the 0.1723 uninformative baseline).
3. **Imbalance & Threshold Selection:**
   - At the default 0.5 threshold, KNN produces conservative predictions: Precision 65.47%, Recall 31.02%, F1 0.4210.
   - When the decision threshold is tuned on the validation split to maximize F1 (optimal threshold = 0.28), test recall increases to **56.02%** and F1 reaches **0.5330** (matching XGBoost's raw F1 of 0.5336).
4. **Local Neighbor Explainability:**
   - KNN explainability uses true local neighbor variance attribution (`KNNNeighborExplainer`), showing neighbor default prevalence and feature divergence z-scores. It does not fabricate or misrepresent tree SHAP values.
