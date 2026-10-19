# CreditAI Phase 5 — Test Report

**Date:** 13 October 2026 (Updated for Phase 5.1 verification)
**Status:** EXECUTED (Phase 5.1 verification)
**Python:** 3.11.9 (system Python, no virtual environment)
**pytest:** 9.1.1

This report records tests that were actually run. It does not treat module imports or the existence of a test file as a pass.

---

## Environment

| Item | Value |
|---|---|
| Interpreter | `C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe` |
| Version | Python 3.11.9 |
| Virtual environment | None (system Python used) |
| Dependency source | `requirements.txt` (already installed in system environment) |
| Git | Not a git repository — version-control comparison was not possible |

Installation command: Dependencies were already installed. No installation was required for this verification.

---

## Tests actually executed

### 1. Phase 5 suite

**Command:**

```text
python -m pytest tests/test_phase5_data_validation.py -v --tb=short
```

| Metric | Count |
|---|---|
| Collected | 45 |
| Passed | 45 |
| Failed | 0 |
| Skipped | 0 |
| Errors | 0 |
| Duration | 20.94s |

The previous Phase 5 write-up claimed 42 tests and marked them passing without execution. The current file contains **45** tests after regression cases were added in Phase 5.1.

### 2. Complete project suite (includes API tests)

**Command:**

```text
python -m pytest tests/ -v --tb=short
```

| Metric | Count |
|---|---|
| Collected | 98 |
| Passed | 98 |
| Failed | 0 |
| Skipped | 0 |
| Errors | 0 |
| Duration | 186.39s (0:03:06) |
| Warnings | 5 (Starlette TestClient deprecation, SHAP colormap deprecation, sklearn lbfgs non-convergence in `test_pipeline.py`) |

Files executed:

- `tests/test_api_contract.py`
- `tests/test_api_integration.py`
- `tests/test_financial_pipeline.py`
- `tests/test_phase12_signal.py`
- `tests/test_phase22_audit.py`
- `tests/test_phase23_benchmark.py`
- `tests/test_phase5_data_validation.py`
- `tests/test_pipeline.py`

---

## Tests that passed

All 45 Phase 5 tests passed, including:

- Manifest contract (valid, missing field, invalid permission)
- Schema, duplicates, chronology, monetary, imbalance
- Combined data-quality `passed` flag after child ERROR issues
- Future-feature leakage, immature labels, contradictory labels
- Combined temporal-audit `passed` flag after child ERROR issues
- `QUALIFIED_FOR_RESEARCH` for a mature, authorized synthetic fixture
- Invalid manifest → `BLOCKED`
- Pending permission + `require_human_permission_review=True` → `BLOCKED`
- Pending permission + review flag false → `REVIEW_REQUIRED` (not qualified)
- Missing manifest evidence → not qualified
- Ranking metrics unavailable when only one class is present (`value is None`, `available is False`)
- Log loss unavailable at probability 0/1 boundaries
- Chronological splits do not cross date boundaries
- Grouped splits assign no overlapping borrower IDs
- Confusion matrix uses the caller-supplied threshold
- API `not_validated` helper
- Error messages do not contain a synthetic sensitive ID
- Rejected permission → `BLOCKED`

All 53 non–Phase 5 tests in `tests/` also passed, including `/health` and `/v1/score` integration tests.

---

## Tests that failed

None in the executed pytest sessions.

---

## Tests not executed

| Item | Reason |
|---|---|
| `scripts/verify_live_api.py` (live uvicorn on port 8000) | Not required after FastAPI `TestClient` integration tests passed. No live HTTP process was started. |
| End-to-end qualification of a real lender extract | No authorized real borrower dataset is in this workspace. |
| Automatic threshold selection on chronological splits | Phase 5 `src/evaluation` does not implement threshold search. |

---

## Manual checks

| Check | Result |
|---|---|
| Invalid manifests cannot qualify | Demonstrated: missing `dataset_id` → `BLOCKED` |
| Missing / rejected authorization | Pending → `BLOCKED` or `REVIEW_REQUIRED`; rejected → `BLOCKED`; never `QUALIFIED_FOR_RESEARCH` |
| Future-dated features | `future_feature_leakage` ERROR |
| Immature labels | `immature_labels` WARNING |
| Censoring | Counted as INFORMATION when `censoring_field` is present; missing field is a WARNING. Records are not auto-excluded from a modeling table. |
| Undefined ranking metrics | ROC-AUC / PR-AUC / KS / Gini return `available=False` and `value=None` (not zero) when only one class is present |
| Chronological split time boundaries | Train ≤ train_end; validation in (train_end, validation_end]; test in (validation_end, test_end] |
| Grouped split borrower overlap | Groups assigned by earliest date; no group shared across splits |
| Threshold selection vs test set | **Not implemented in Phase 5.** Metrics apply a caller-supplied threshold (default 0.5). Existing Phase 1.1 training code selects F1 on validation only; that is outside this phase. |
| Missing evidence as approval | Gate never returns `QUALIFIED_FOR_RESEARCH` when the manifest is invalid or permission is not processable |
| Raw financial records in errors | Duplicate/type messages use counts, not row payloads. Future-leakage details may include observation/prediction **dates** (not account numbers). |
| `/health` | `{"status": "ok", "scoring": "not_validated"}` |
| `/v1/score` | `score_status: not_validated`, `default_probability: null`, no model call |
| Model training in Phase 5 modules | Qualification path does not fit models |
| Phase 1–4 report artifacts | Not edited in this verification. No git history to prove they are bitwise unchanged. |

---

## Failures found before the passing run (Phase 5.1)

An earlier unauthenticated pytest run (global Python 3.11) showed 7 then 2 failing tests. Root causes, not “tests exist”:

1. Combined `run_full_validation` / `run_full_temporal_audit` never set `passed=False` when child checks added ERROR issues.
2. Outcome / observation-end dates after the prediction timestamp were treated as feature leakage.
3. The “valid” synthetic fixture used a few-day observation window against a 12-month horizon, so qualification could not reach `QUALIFIED_FOR_RESEARCH`.
4. Several tests had been relaxed to accept `REVIEW_REQUIRED` or empty grouped splits instead of asserting the intended rule.

Justified implementation fixes (not API contract changes):

- Propagate ERROR issues onto combined `passed` flags.
- Exclude documented outcome and observation-end fields from the feature-availability check.

Regression tests added for those fixes. Tests were not edited solely to hide remaining defects.

---

## Remaining limitations

- No git repository; integrity of Phase 1–4 artifacts cannot be diffed against a commit.
- Sensitive field-name warnings in `contract.py` are computed and discarded.
- `check_qualification_criteria()["authorization_documented"]` is true for any status other than `pending_review`, including `rejected`.
- Censoring is documented, not applied as an exclusion rule.
- Phase 5 does not select operating thresholds; it cannot prove “threshold not fit on test” by itself.
- Live uvicorn script was not run.
- No authorized Indian lender sample was ingested.

---

## API contract (executed)

From `tests/test_api_integration.py` via FastAPI TestClient:

- `GET /health` → 200, `scoring: not_validated`
- `POST /v1/score` (valid payload) → 200, `score_status: not_validated`, `default_probability: null`, `validated_risk_estimate: false`, `model_version: null`
- Request validation and safe error bodies remain in place

The API contract was not changed.

---

*End of Phase 5 Test Report*
