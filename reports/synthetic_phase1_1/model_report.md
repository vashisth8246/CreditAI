# CreditAI Phase 1.1 synthetic model report

**Scope:** synthetic development records only. This does not validate risk for Indian lending or any real borrower population.

## Data splits and model choice

Train/validation/test counts are 560/120/120. Default prevalence is 0.177/0.183/0.175. Models are selected by validation ROC-AUC; selected model: **Prevalence Dummy**. Test set is not used to select models, calibrate probabilities, or choose the threshold. See `model_comparison.csv` for ROC-AUC, PR-AUC, KS, Gini, Brier, precision, recall, F1, confusion matrices, and phases. PR-AUC should be compared with the corresponding default prevalence; a prevalence-only ranking yields PR-AUC near prevalence.

## Calibration

The Platt sigmoid is fit to validation predictions only. Validation calibration metrics are in-sample and optimistic. On the untouched test set, raw/calibrated/prevalence-baseline Brier scores are 0.1444/0.1444/0.1444. A lower Brier score alone does not establish good calibration; inspect the held-out calibration curve and compare with the prevalence baseline. Test probabilities (raw/calibrated): `{"raw": {"min": 0.1767857142857143, "p10": 0.1767857142857143, "median": 0.1767857142857143, "mean": 0.1767857142857143, "p90": 0.1767857142857143, "max": 0.1767857142857143, "share_at_or_above_0_50": 0.0}, "calibrated": {"min": 0.18333303980702004, "p10": 0.18333303980702004, "median": 0.18333303980702004, "mean": 0.18333303980702007, "p90": 0.18333303980702004, "max": 0.18333303980702004, "share_at_or_above_0_50": 0.0}}`. When the selected candidate is the constant-prevalence baseline, the fitted sigmoid remains approximately constant near validation prevalence; consequently all scores can be below 0.50 because synthetic default prevalence is far below one half. The fitted sigmoid is constrained to be non-decreasing so calibration cannot reverse the ranking.

## Experimental classification threshold

Threshold 0.183333 maximizes validation F1 on calibrated validation predictions; ties prefer precision then higher threshold. This frozen threshold is evaluated on test once. It is an experiment, not a lending policy. Ranking metrics are threshold independent. Confusion matrices use this same threshold.

## Explainability and limitations

SHAP status: Not applicable: validation selected prevalence baseline; no borrower-specific tree model was selected. Synthetic labels are probabilistic but are generated from observable synthetic-history aggregates, so the task measures recovery of the generator's assumptions, not real-world default risk. Features use transactions strictly before the January 1, 2025 loan date. See `data_generation_assumptions.md` and `phase_1_1_audit.md` for the audit trail.
