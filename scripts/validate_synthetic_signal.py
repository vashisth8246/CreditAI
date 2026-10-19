"""Run the Phase 1.2 signal audit without changing prior benchmark outputs."""
from pathlib import Path
import sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.models.signal_validation import run_phase12

if __name__=="__main__":
    base=ROOT/"data"/"synthetic_phase1_1"
    features=pd.read_csv(base/"borrower_features.csv")
    outcomes=pd.read_csv(base/"outcomes.csv",parse_dates=["loan_date","outcome_date"])
    split=pd.read_csv(ROOT/"reports"/"synthetic_phase1_1"/"borrower_splits.csv")
    summary=run_phase12(features,outcomes,split,ROOT/"reports"/"synthetic_phase1_2")
    out=ROOT/"reports"/"synthetic_phase1_2"
    cv=pd.read_csv(out/"cross_validation_summary.csv")
    selections=pd.read_csv(out/"fold_model_selection.csv")
    fresh=pd.read_csv(out/"fresh_holdout_metrics.csv")
    baseline=pd.read_csv(out/"fresh_holdout_baseline.csv").iloc[0]
    associations=pd.read_csv(out/"feature_associations.csv").head(8)
    bands=pd.read_csv(out/"income_cv_risk_bands.csv")
    def csv_block(frame): return "```csv\n"+frame.to_csv(index=False)+"```"
    report=f"""# CreditAI Phase 1.2 — Synthetic signal validation

## Decision

**Recommendation: retain the risk pipeline as an engineering prototype and prioritize consented or properly licensed historical repayment data.** The simulator creates a weak, unstable but detectable relationship by construction. It does not establish real borrower or Indian lending performance. Do not build production approval/pricing decisions on these results.

## Data and target audit

Phase 1.1's 120 historical test borrowers were quarantined from Phase 1.2 development, cross-validation, associations, and model selection. The remaining {summary['development_borrowers']} borrowers were used for exploratory development. A separately generated seed-{summary['fresh_holdout_seed']} cohort of {summary['fresh_holdout_borrowers']} borrowers / {summary['fresh_holdout_transactions']} transactions served as the fresh simulation holdout. Dates and labels follow `reports/data_generation_assumptions.md`: 2024 history, 2025-01-01 prediction, and a probabilistic day 1–90 default event. The label shares pre-loan ingredients such as income CV, outflow shortfall, and EMI ratio with feature columns, plus hidden profile adjustments. This is an artificial target mechanism with substantial Bernoulli noise, not independent repayment evidence.

## Cross-validation protocol and results

Reproducible stratified 5-fold outer CV (seed {summary['cv_seed']}) evaluates every development borrower as an outer test record once. Within each outer-training portion, a stratified 80/20 inner fit/validation split trains LR/RF/XGBoost/constant-prior dummy; feature scaling is inside the LR pipeline. Validation ROC-AUC chooses the model; Platt calibration and the experimental maximum-F1 threshold use validation predictions only. Outer-fold test outcomes are used only for metrics. Transaction feature aggregates are deterministic row-wise calculations over the fixed pre-loan window, with no global learned preprocessing.

Average outer-fold default prevalence: **{cv.default_prevalence_mean.mean():.3f}**. A constant-prevalence ranking has ROC-AUC 0.500 and PR-AUC equal to default prevalence. Candidate raw ROC-AUC / PR-AUC / Brier are means ± fold SD:

{csv_block(cv[cv.prediction=='raw'][['model','folds','roc_auc_mean','roc_auc_sd','pr_auc_mean','pr_auc_sd','brier_mean','brier_sd','default_prevalence_mean']])}

Model selection varied by fold: {selections.selected_on_validation.value_counts().to_dict()}. Calibrated rows in the CV summary are conditional on a model being selected in that fold (so their fold counts are less than five); they should not be compared as an unconditional estimator. Full per-fold metrics, including calibrated selected candidates, are in `cross_validation_fold_metrics.csv`.

## Feature associations and risk bands

Point-biserial correlations and paired-bootstrap percentile 95% intervals use only the {summary['development_borrowers']} nonhistorical-test development records ({summary['bootstrap_replicates']} resamples, seed {summary['bootstrap_seed']}). These are unadjusted exploratory associations across 40 correlated features; intervals are not multiplicity-adjusted and do not imply causation.

{csv_block(associations[['feature','point_biserial_r','bootstrap_95ci_low','bootstrap_95ci_high','n']])}

Predefined `income_cv` quartiles are cut using feature values without labels. Default rates rise modestly from the lower to upper band but the Wilson intervals overlap substantially:

{csv_block(bands[['risk_band','borrowers','default_rate','wilson_95ci_low','wilson_95ci_high']])}

The leading associations are small (absolute r near 0.08–0.11). Some features are constant in this simulator and have undefined correlation. This supports weak constructed signal plus random outcome noise, not a strong broad predictive signal.

## Fresh-seed holdout

Final model selection, Platt fit, and threshold selection used only the development fit/validation split; the new cohort was scored once. Validation selected **{summary['final_validation_selected_model']}**, threshold **{summary['final_validation_selected_threshold']:.4f}** by validation F1. Fresh holdout prevalence was **{summary['fresh_holdout_default_prevalence']:.3f}**. The train-prevalence dummy Brier was **{baseline.brier_score:.4f}**.

{csv_block(fresh[['model','prediction','fresh_holdout_prevalence','roc_auc','pr_auc','brier_score','precision','recall','f1','threshold']])}

The holdout's raw XGBoost AUC is higher than the validation-selected Random Forest, but this does not justify switching models after seeing holdout results. The calibrated Random Forest Brier should be compared with the prevalence baseline; any small difference is not calibration evidence on its own. At the validation-selected threshold, many observations are flagged; the objective uses F1 without a lender-approved false-negative/false-positive cost and is illustrative only.

## Validation/test ranking reversal

Historical Phase 1.1 validation/test ROC-AUCs were LR 0.488/0.666 and RF 0.468/0.640. Phase 1.2 did not use the old test borrowers. A 120-person test set had only about 21 defaults and 99 nondefaults, giving 2,079 positive-negative pairs underlying AUC. Rank estimates can move materially with a small number of pair orderings, and the 5-fold CV now shows fold SD around {cv[(cv.model=='Logistic Regression')&(cv.prediction=='raw')].roc_auc_sd.iloc[0]:.3f} for LR and {cv[(cv.model=='Random Forest')&(cv.prediction=='raw')].roc_auc_sd.iloc[0]:.3f} for RF. Different training subsets, noisy Bernoulli outcomes, and chance ordering are plausible reasons for reversal. It cannot be resolved by choosing whichever old test score is larger. The fresh cohort also shows performance depends on simulator draw and still represents only the same generator.

## Preservation, tests, and limits

Historical Phase 1.1 reports and its test metrics were left intact. Phase 1.2 outputs are confined to `reports/synthetic_phase1_2/`; no model artifacts are written. The existing UCI benchmark bundle and recovered metadata were not used for selection or overwritten.

Run `python scripts/validate_synthetic_signal.py` to reproduce the new analyses and `python -m pytest tests/ -q` for tests. The test suite verifies historical-test quarantine, outer-fold disjointness/coverage, deterministic generator behavior and nested event labels, bootstrap association output, validation-only threshold inputs, feature cutoff, and UCI artifact preservation. Phase 1.2 results remain synthetic and are not evidence for a real data pilot. The next meaningful validation needs a real, governed dataset with verified financial-source labels and lender-observed repayment outcomes.
"""
    (out/"phase_1_2_report.md").write_text(report,encoding="utf8")
    print(f"Completed Phase 1.2: {summary['development_borrowers']} development borrowers, {summary['fresh_holdout_borrowers']} fresh simulated holdout borrowers.")
