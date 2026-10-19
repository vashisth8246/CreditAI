# CreditAI Phase 2 — `/v1/score` API Contract

## Status and intended use

The current endpoint is a safe contract skeleton. CreditAI has no real-data validated scoring model registered; therefore valid requests receive `score_status: "not_validated"`, `default_probability: null`, and `validated_risk_estimate: false`. The endpoint does not load or invoke the synthetic model. No value is silently presented as a real probability. A future demo mode, if added, must use `score_status: "demo_only"`, `provenance.source: "synthetic_demo"`, and must remain visibly distinct from `validated`.

Run locally after installing project requirements with `uvicorn src.api.app:app --reload`. The API is not production-ready and makes no regulatory-compliance claim. There is no Account Aggregator or financial-account integration.

## `POST /v1/score`

Request content type: `application/json`. Version field `schema_version` is required and must be `1.0`. Unknown top-level and transaction fields are rejected by the HTTP schema. No borrower name, PAN, phone, account number, or credentials are requested.

### Request fields

| Field | Required | Type / rule | Missing-data behavior |
|---|---:|---|---|
| `schema_version` | Yes | String; currently `"1.0"` | Reject unsupported/missing version. |
| `observation_start` | Yes | `YYYY-MM-DD`, strictly before prediction cutoff | Reject missing/invalid; observation window cannot be inferred. |
| `prediction_date` | Yes | `YYYY-MM-DD`; exclusive feature cutoff | Reject missing/invalid. All transactions on or after this date are excluded by rejection. |
| `transactions` | Yes | Array (may be empty); each item includes transaction ID, date, type and amount | Reject missing/non-array; an empty list is accepted but does not produce a score. |
| `request_id` | No | Opaque caller-generated string | Omitted/null if absent. Do not put personal information in it. |
| `transaction_id` | Yes per item | Non-empty unique string within request | Reject missing/duplicate. |
| `date` | Yes per item | `YYYY-MM-DD` inside `[observation_start, prediction_date)` | Reject absent/invalid/out-of-window dates. |
| `transaction_type` | Yes per item | `credit` or `debit` | Reject other values. |
| `amount` | Yes per item | Finite number greater than zero | Reject missing, null, zero, negative, nonnumeric, or non-finite values. |
| `category` | No per item | String or null | Missing remains unknown; no category is inferred. |
| `counterparty` | No per item | String or null | Missing remains unknown; callers should avoid sending unnecessary free text. |
| `balance_after_transaction` | No per item | Finite number or null | Missing/null remains unknown; never imputed silently. |

Unknown optional features remain explicitly unknown; this skeleton performs no imputation or risk calculation. Currency/units are not yet modeled; callers must not mix currencies. Add an explicit currency field and normalization policy before calculating any financial features.

### Example request

```json
{
  "schema_version": "1.0",
  "observation_start": "2025-01-01",
  "prediction_date": "2025-02-01",
  "request_id": "opaque-request-123",
  "transactions": [
    {"transaction_id": "txn-001", "date": "2025-01-15", "transaction_type": "credit", "amount": 45000, "category": "salary"},
    {"transaction_id": "txn-002", "date": "2025-01-20", "transaction_type": "debit", "amount": 1200}
  ]
}
```

### Example response when no validated model is available

```json
{
  "score_status": "not_validated",
  "score_type": "none",
  "default_probability": null,
  "validated_risk_estimate": false,
  "model_version": null,
  "timestamp": "2026-10-09T00:00:00+00:00",
  "provenance": {"source": "no_validated_model", "synthetic_demo": false},
  "request_id": "opaque-request-123",
  "message": "No validated CreditAI model is available; no risk score was produced."
}
```

The timestamp above illustrates the format; runtime timestamps are generated at request time. A validated response in a future version must include an immutable model/artifact version and evaluation reference, training-data provenance, target definition, and score provenance. A score alone must not be described as an approval decision.

## Errors, logging, and safety

Errors return HTTP 422 with a structured `error` object (`code`, safe `message`, optional `field` or field/code details). The HTTP adapter intentionally omits rejected input values from validation responses. The core validator rejects duplicate IDs, invalid amounts, invalid dates, and transactions outside the declared observation window. Applications should log request ID, endpoint version, outcome/status, and aggregate latency/error codes only; avoid logging raw transactions, counterparties, or direct identifiers. Apply authentication, authorization, transport security, rate limits, data minimization, retention controls, and operational monitoring before deployment.

The endpoint currently returns no probability, regardless of request content. There is no demo score mode or validated model mode wired into this skeleton.

## Validation plan before any pilot

Use authorized real borrower-level repayment data with an agreed default outcome and sufficient mature follow-up. Define observation and outcome windows, censoring, and treatment of restructures, cures, prepayments, and repeated loans. Prevent leakage by requiring all features to be available as of the scoring cutoff. Split chronologically and keep a later untouched test period. Report ROC-AUC, PR-AUC relative to default prevalence, calibration curves, Brier score against prevalence and current-policy baselines, uncertainty intervals, and subgroup sizes. Select thresholds from lender-defined decision costs and operational capacity rather than 0.50. Review explainability, stability, drift, fairness limitations, intended population, data rights, and monitoring before making any consequential use. Synthetic Phase 1 results do not meet these gates and do not validate Indian borrower risk prediction.
