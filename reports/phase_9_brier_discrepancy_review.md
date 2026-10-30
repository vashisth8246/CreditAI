# Phase 9 — Brier Score Discrepancy Review

**Date:** 2026-10-22
**Question:** Why does the Phase 1 report claim a calibrated Brier score of **0.1360**, while the Phase 9 held-out evaluation reports **0.1441** for the same Taiwan model and split?
**Verdict:** The split, data and base model are identical. The difference is the **calibrator object and its fitting procedure**. The shipped artifact's correct held-out Brier is **0.14412**; the historical **0.1360** belongs to a different calibration implementation and cannot be attributed to the deployed artifact.

---

## 1. Evidence reviewed

| Source | Claim / content |
|---|---|
| `reports/CreditAI_Phase1_Report.md` | Validation Brier before `0.17112`, after `0.13635` (+20.32%); test table shows `0.1360`; method: `CalibratedClassifierCV(FrozenEstimator(model), method='sigmoid')` |
| `reports/phase_9_heldout_evaluation.md` | Raw test `0.1709`; calibrated test `0.1441`; 15.69% improvement |
| `reports/phase_9_calibration_evaluation.md` | Validation `0.1711 → 0.1443`; test `0.1709 → 0.1441`; calibrator fitted on validation only |
| `reports/phase_9_evaluation_metrics.csv` | Machine-readable Phase 9 metrics |
| `src/calibration/calibrate.py` | Shipped `PlattCalibrator`: `LogisticRegression(C=1e6)` on `logit(p_raw)` |
| `src/models/train.py` | Phase 9 training path: `PlattCalibrator().fit(raw_val, y_val)` |
| `src/calibration.py` | Phase 1 path: `CalibratedClassifierCV(..., method=...)` on `X_val` |
| `models/calibration_model.joblib` | Shipped calibrator: slope `0.47414482`, intercept `-1.26450292` |
| `logs/brier_reproduction.out.txt` | Earlier reproduction of both implementations |
| `logs/brier_diagnostic_session6.out.log` | Session-6 reproduction |
| `logs/brier_slope_compare.out.log` | Fitted-parameter comparison |
| `logs/brier_split_check.out.log` | Split-provenance check |

No historical report was modified; this review is additive.

---

## 2. Reproduction setup

The reproduction reads the real UCI credit-card data and the real model artifacts. It does not synthesize data or re-train the base model.

| Item | Value |
|---|---|
| Dataset | UCI Default of Credit Card Clients, 30,000 rows |
| Split | 70% train / 15% validation / 15% test, `random_state=42`, stratified |
| Counts | 21,000 / 4,500 / 4,500 |
| Test defaults | 996 |
| Test prevalence | 0.221333 |
| Base model | `models/creditai_model.joblib["base_model"]` (`XGBClassifier`) |
| Features | 23 engineered features, aligned by `feature_names` |
| Calibration fit input | Validation split only (`X_val`, `y_val`) |
| Test use | Evaluation only; never used to fit a reported calibrator |

Raw test Brier reproduces Phase 9 exactly: **0.17094272375106812**. This confirms the data, split, feature pipeline and base model are the same objects used by the Phase 9 evaluation.

---

## 3. Reproduction results

| Implementation | Input to sigmoid | Fitted parameters | Validation Brier | Test Brier | Test PD range |
|---|---|---|---|---:|---:|---|
| Raw model | — | — | 0.17112315 | 0.17094272 | — |
| **Shipped `calibration_model.joblib`** (`PlattCalibrator`) | `logit(p_raw)` | slope `0.47414482`, intercept `-1.26450292` | **0.14428137** | **0.14412179** | 0.03797 – 0.55458 |
| Phase 1 recipe: `CalibratedClassifierCV(FrozenEstimator(base), method='sigmoid')` | `p_raw` (because this `XGBClassifier` has no `decision_function`) | `a_ = -4.35765746`, `b_ = 3.23931307` in `p = expit(-(a·p_raw + b))` | **0.13635378** | **0.13602025** | 0.04025 – 0.71823 |
| Fresh fit of current `PlattCalibrator` on the canonical validation split | `logit(p_raw)` | slope `0.85795861`, intercept `-1.09014010` | — | **0.13546446** | — |

The Phase 1 figures `0.13635` (validation) and `0.1360` (test) match the `CalibratedClassifierCV` row to four decimal places. The Phase 9 figures `0.14428` and `0.14412` match the shipped artifact row exactly.

The sklearn reconstruction is exact: applying `expit(-(a_·p_raw + b_))` to the raw probabilities reproduces `CalibratedClassifierCV.predict_proba` with maximum absolute difference `0.0`. This proves the sklearn calibrator's input was **probability**, not log-odds.

---

## 4. What is identical

- Underlying dataset and row order.
- Random seed and stratified 70/15/15 split.
- Engineered feature matrix and feature order.
- Base XGBoost model artifact.
- Validation and test row sets.
- Brier formula (`sklearn.metrics.brier_score_loss`) and target definition.
- Test prevalence and default count.

Therefore the discrepancy is **not** leakage, a different test set, a different label, a different model, or a metric implementation error.

---

## 5. What differs

### 5.1 Two different calibrator classes are being compared

- **Phase 1 / 0.1360:** `sklearn.calibration.CalibratedClassifierCV` with `FrozenEstimator(base)` and `method='sigmoid'`.
- **Phase 9 / 0.1441:** a custom `PlattCalibrator` persisted as `models/calibration_model.joblib`.

Both are sigmoid calibrators, but they are different objects with different fitting code. A metric computed from one cannot be used to describe the other.

### 5.2 Different input parameterisation

`CalibratedClassifierCV` selects a response method automatically. This `XGBClassifier` exposes `predict_proba` but **not** `decision_function`, so sklearn fits its sigmoid on probabilities in `[0, 1]`:

```text
p_cal = expit(-(a · p_raw + b))
```

The custom calibrator first takes the log-odds and then fits a linear model:

```text
z      = logit(clip(p_raw, 1e-6, 1 - 1e-6))
p_cal  = expit(slope · z + intercept)
```

These are different functional families on different scales. The fitted coefficients are therefore not comparable: sklearn's `a_ = -4.3577` acts on a probability, while the custom `slope = 0.4741` acts on a log-odds value.

### 5.3 Different fitting objective details

sklearn's `_sigmoid_calibration` uses Platt's Bayesian target smoothing:

```text
T = (prior1 + 1) / (prior1 + 2)   for positives
T = 1 / (prior0 + 2)              for negatives
```

and minimises a binomial loss with L-BFGS, without L2 regularisation. The custom calibrator fits `LogisticRegression(C=1e6)` on hard 0/1 labels. With 4,500 validation rows the smoothing is small, but combined with the different input scale it changes the fitted curve.

### 5.4 The shipped coefficients are not reproducible from the current recipe

A fresh fit of the **current** `PlattCalibrator` code on the canonical validation split produces:

```text
slope = 0.85795861, intercept = -1.09014010, test Brier = 0.13546446
```

The shipped artifact contains:

```text
slope = 0.47414482, intercept = -1.26450292, test Brier = 0.14412179
```

Fits on other single splits do not reproduce the shipped values either:

| Fit set (diagnostic only) | Slope | Intercept | Test Brier |
|---|---:|---:|---:|
| Train predictions | 1.51200163 | -1.21003401 | 0.14185736 |
| Validation predictions | 0.85795861 | -1.09014010 | 0.13546446 |
| Test predictions *(not a valid procedure; sanity check only)* | 0.87338895 | -1.09458387 | 0.13544551 |
| Train + validation | 1.35480583 | -1.17095792 | — |

The shipped slope is less than 60% of the lowest fresh fit (`0.4741` vs `0.8580`). This indicates the artifact was **not** produced by the current `PlattCalibrator.fit` on the documented split and base model. It likely comes from an earlier model/split version, a different input representation, or an earlier fitting implementation. The available repository history does not record artifact provenance, so the exact origin cannot be established from the current tree.

This is a provenance finding, not a claim that the stored artifact is corrupt: it loads, predicts monotonically, and is the object the API actually uses.

### 5.5 Two calibration artifacts exist in the repository

The repository contains two different calibrated objects:

| Artifact | Type | Produced by | Used by |
|---|---|---|---|
| `models/creditai_model.joblib["calibrated_model"]` | sklearn `CalibratedClassifierCV` | `src/train.py` (`fit_probability_calibrator`, `method='sigmoid'`) | The Phase 1 report and `src/predict.py` |
| `models/calibration_model.joblib` | custom `PlattCalibrator` | Not recorded in the current training scripts | `src/inference/predictor.py` and the batch API via `model_registry.py` |

`src/train.py` saves the sklearn calibrator **inside the model bundle**; it does not write `models/calibration_model.joblib`. The API nevertheless loads the separate custom joblib. This structural split explains how the documentation and the serving path could legitimately quote different Brier scores for “the model” without either calculation being wrong.

The mismatch is therefore not only numerical but architectural: the evaluation report and the serving path read different calibration artifacts.

---

## 6. Interpretation

1. **Phase 1's 0.1360 is not a false number.** It is a valid result for the sklearn `CalibratedClassifierCV` recipe on this split.
2. **Phase 9's 0.1441 is not a metric bug.** It is the correct held-out Brier for the shipped custom calibrator.
3. **The two numbers answer different questions.** Comparing them as if they described one object created the apparent discrepancy.
4. **The shipped artifact underperforms both fresh calibrators.** A current-code refit would improve held-out Brier from `0.14412` to about `0.13546`; the sklearn recipe gives `0.13602`.
5. **No leakage is implied.** Both valid fits use validation labels only; the test labels were used only for scoring. The test-fit row above is explicitly a diagnostic and is not used for any reported result.
6. **The calibrated probabilities are conservative.** The shipped map compresses the top end to about `0.555`, while the fresh fits reach about `0.718`. That compression explains part of the Brier gap and matters for risk-band assignment near the 50% threshold.

---

## 7. Impact on Phase 9 claims

| Claim | Status |
|---|---|
| Batch predictions are produced by the registered model and shipped calibrator | Valid |
| Batch UI/report statistics use the returned calibrated probabilities | Valid |
| Held-out calibrated Brier is 0.1441 | Valid for the shipped artifact |
| Historical Phase 1 Brier 0.1360 describes the shipped artifact | **Not valid** |
| Calibration reduces Brier versus raw | Valid (0.1709 → 0.1441) |
| The model is production-ready for India | Not claimed; `/v1/score` remains `not_validated` |

No batch workflow result needs to be recomputed. All session-6 probabilities, risk categories and exports are consistent with the artifact that is actually deployed.

---

## 8. Recommendations (non-destructive)

1. **Keep 0.1441 as the current shipped metric** in Phase 9 documentation. Do not replace it with 0.1360.
2. **Add an errata pointer** from the Phase 1 report to this review rather than editing historical numbers in place.
3. **Record provenance** with the calibration artifact: git commit, training script, split hash, sklearn version, input representation (`probability` vs `log-odds`), and fitted parameters.
4. **Add a reproducibility test** that refits the calibrator from the canonical split and asserts the stored coefficients within a tolerance. The current mismatch (`0.4741` vs `0.8580`) would fail such a test and surface stale artifacts early.
5. **If 0.136-class calibration is desired**, regenerate `models/calibration_model.joblib` with a pinned recipe, re-run `scripts/evaluate_calibration_heldout.py`, update `phase_9_calibration_evaluation.*`, `phase_9_heldout_evaluation.*` and `phase_9_evaluation_metrics.csv`, then re-run the batch verification. This is a model change, not a documentation change, and must not be done silently.
6. **State the input representation in every calibration report.** “Platt scaling” alone is ambiguous; the two implementations here are not interchangeable.

---

## 9. Conclusion

The 0.1360 vs 0.1441 discrepancy is fully explained:

- same data, split and base model;
- different calibrator implementations and input parameterisations;
- the historical 0.1360 belongs to sklearn's probability-space sigmoid;
- the deployed custom log-odds sigmoid yields 0.1441;
- the deployed coefficients are not reproducible from the current training code on the documented split, indicating a stale or differently produced artifact.

The correct number for the current shipped model is **0.14412** held-out Brier. The correct interpretation of **0.1360** is “Phase 1 sklearn calibration experiment”, not “current production artifact”.
