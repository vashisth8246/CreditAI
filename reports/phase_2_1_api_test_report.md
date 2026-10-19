# CreditAI Phase 2.1 — Live API Integration Test Report

## Executive Summary

Phase 2.1 establishes end-to-end live HTTP integration testing and validation tightening for the CreditAI `/health` and `/v1/score` API endpoints. 

The API runtime dependencies (`fastapi`, `pydantic`, `uvicorn`, `httpx`) were installed and verified in the project's Python 3.11 environment. The application was launched live via `uvicorn src.api.app:app` on `127.0.0.1:8000` and successfully served live HTTP requests.

Validation was tightened to strictly enforce `YYYY-MM-DD` date formatting, reject empty transaction arrays, block unknown request/transaction fields (`extra="forbid"`), and return safe, structured 422/400 JSON errors without echoing sensitive transaction data.

The contract guarantee is preserved: `/v1/score` continues to return `default_probability: null` and `validated_risk_estimate: false` with `score_status: "not_validated"`. No synthetic model or unvalidated ML pipeline is loaded or invoked.

All 35 automated tests (unit, contract, pipeline, financial features, and live HTTP integration tests) passed with zero failures.

---

## 1. Environment & Dependency Installation

### Python Environment Inspection
- **Python Version**: `3.11.9` (Win64)
- **Root Directory**: `f:\NUV ACD\All SEM\7th Sem\ML&DS\New folder (3)\CreditAI`

### Exact Dependency Installation Command
```bash
pip install -r requirements.txt
```

### Installed Runtime Packages
- `fastapi` (`0.143.0`)
- `pydantic` (`2.14.0`)
- `uvicorn` (`0.30.0` / runtime compatible)
- `httpx` (`0.28.1`)
- `pytest` (`9.1.1`)

---

## 2. Server Startup & Live HTTP Verification

### Exact Startup Command
```bash
python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

### Live HTTP Execution Verification

Live HTTP requests were executed against the running Uvicorn process over `http://127.0.0.1:8000` using `httpx.Client`. Below are the actual observed status codes and sanitized responses:

#### 1. `GET /health`
- **HTTP Status**: `200 OK`
- **Response Headers**: `content-type: application/json`, `server: uvicorn`
- **Response Body**:
  ```json
  {
    "status": "ok",
    "scoring": "not_validated"
  }
  ```

#### 2. Valid `POST /v1/score`
- **HTTP Status**: `200 OK`
- **Request ID**: `live-test-req-001`
- **Response Body**:
  ```json
  {
    "score_status": "not_validated",
    "score_type": "none",
    "default_probability": null,
    "validated_risk_estimate": false,
    "model_version": null,
    "timestamp": "2026-10-09T15:16:10.176520+00:00",
    "provenance": {
      "source": "no_validated_model",
      "synthetic_demo": false
    },
    "request_id": "live-test-req-001",
    "message": "No validated CreditAI model is available; no risk score was produced."
  }
  ```

#### 3. Invalid `POST /v1/score` (Transaction Date After Cutoff)
- **HTTP Status**: `422 Unprocessable Entity`
- **Response Body**:
  ```json
  {
    "error": {
      "code": "transaction_outside_window",
      "message": "Transactions must fall within the observation window, before prediction_date.",
      "field": "transactions[0].date"
    }
  }
  ```

#### 4. Invalid `POST /v1/score` (Unknown Request Field & Negative Amount)
- **HTTP Status**: `422 Unprocessable Entity`
- **Response Body**:
  ```json
  {
    "error": {
      "code": "invalid_request",
      "message": "Request validation failed.",
      "details": [
        {
          "field": "body.extra_field",
          "code": "extra_forbidden"
        }
      ]
    }
  }
  ```

---

## 3. Validation Tightening & Security Enforcement

| Validation Requirement | Implementation Mechanism | Behavior / Error Code |
|---|---|---|
| **Exact Date Format (`YYYY-MM-DD`)** | Regex `^\d{4}-\d{2}-\d{2}$` + `strptime` strict parsing | Rejects `2025-1-1`, `2025/01/01`, `2025-02-30` with `invalid_date`. |
| **Empty Transaction Array** | Guard `len(transactions) == 0` & Pydantic `Field(min_length=1)` | Rejects `transactions: []` with `empty_transactions`. |
| **Unknown Top-level Fields** | `ALLOWED_REQUEST_FIELDS` check & Pydantic `extra="forbid"` | Rejects unexpected request keys with `unknown_field` / `extra_forbidden`. |
| **Unknown Transaction Fields** | `ALLOWED_TX_FIELDS` check & Pydantic `extra="forbid"` | Rejects unexpected transaction keys with `unknown_field` / `extra_forbidden`. |
| **Non-Positive / Non-Finite Amounts** | Check `amount <= 0`, `math.isfinite()`, `not isinstance(bool)` | Rejects `0`, `-100`, `NaN`, `Inf`, `true` with `invalid_amount`. |
| **Duplicate Transaction IDs** | `seen` ID set tracking across request transactions | Rejects duplicate IDs with `invalid_transaction_id`. |
| **Out-of-Window Dates** | Enforce `observation_start <= tx.date < prediction_date` | Rejects `tx.date >= prediction_date` or `< observation_start` with `transaction_outside_window`. |
| **Safe Error Responses** | Omit submitted values from exception handlers & responses | Prevents echoing sensitive transaction IDs, counterparties, or amounts in logs/responses. |
| **Malformed JSON** | `StarletteHTTPException` custom handler | Returns clean structured 400/422 JSON without exposing stack traces. |

---

## 4. Contract Preservation & Safety

- **Default Probability**: Remains `null` on all valid requests.
- **Risk Estimate Flag**: `validated_risk_estimate` remains `false`.
- **Score Status**: `score_status` remains `"not_validated"`.
- **Synthetic Pipeline Isolation**: The synthetic demonstration pipeline (`src.data.generate` / `src.models`) is **never** invoked by the API endpoints.

---

## 5. Test Suite Execution & Results

### Dedicated API & Full Suite Test Execution Command
```bash
python -m pytest
```

### Summary of Results
- **Total Test Cases**: 35
- **Passed**: 35
- **Failed**: 0
- **Unresolved Failures**: 0

### Test Breakdown by File
1. `tests/test_api_contract.py` — **9 Passed**: Contract validation logic, strict dates, duplicate IDs, empty transactions, unknown fields, invalid amounts.
2. `tests/test_api_integration.py` — **11 Passed**: FastAPI HTTP client integration tests for `/health` and `/v1/score` (all pass/fail HTTP scenarios).
3. `tests/test_financial_pipeline.py` — **5 Passed**: Synthetic financial data generation, feature engineering, model training, calibration, reload.
4. `tests/test_phase12_signal.py` — **3 Passed**: Chronological splits, historical test exclusion, bootstrap feature associations.
5. `tests/test_pipeline.py` — **7 Passed**: Core CreditAI pipeline end-to-end checks.

---

## 6. Deployment Readiness & Operational Disclaimers

> [!WARNING]
> **NOT PRODUCTION READY FOR COMMERCIAL OR REGULATORY USE**
> - **Authentication & Authorization**: The API endpoint currently operates without API key, JWT, or OAuth2 authentication controls.
> - **Rate Limiting & Denial of Service Protection**: No throttling or rate-limiting middleware is currently configured.
> - **Transport & Deployment Security**: Must be deployed behind a secure TLS reverse proxy (e.g. NGINX / Caddy / Cloud ALB) with strict CORS policies.
> - **Data Retention & Privacy**: Production deployments must enforce explicit data minimization, zero-retention policies for raw transactions, and compliance with applicable privacy regulations.
> - **Model Validation Requirement**: No real borrower loan outcome dataset has been evaluated for this API. Scoring remains disabled until formal model validation gates are satisfied.
