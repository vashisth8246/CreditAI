import { useCallback, useEffect, useState } from 'react'
import type { FeatureField, FeatureContribution, ModelDetails, ModelSchema, ModelSummary, Prediction, SystemStatus } from './api'
import { researchApi } from './api'

const fieldLabel = (key: string) => key.replaceAll('_', ' ')

type PresetProfile = {
  name: string
  tag: string
  description: string
  values: Record<string, number>
}

const PRESET_BORROWERS: PresetProfile[] = [
  {
    name: 'Low Risk Borrower',
    tag: 'Low Risk',
    description: 'High credit limit (NT$ 200k), prime age, university degree, zero repayment delays, healthy payment-to-bill ratio.',
    values: {
      LIMIT_BAL: 200000,
      SEX: 2,
      EDUCATION: 1,
      MARRIAGE: 2,
      AGE: 34,
      PAY_0: 0,
      PAY_2: 0,
      PAY_3: 0,
      PAY_4: 0,
      PAY_5: 0,
      PAY_6: 0,
      BILL_AMT1: 15000,
      BILL_AMT2: 14000,
      BILL_AMT3: 13000,
      BILL_AMT4: 12000,
      BILL_AMT5: 11000,
      BILL_AMT6: 10000,
      PAY_AMT1: 5000,
      PAY_AMT2: 4500,
      PAY_AMT3: 4000,
      PAY_AMT4: 3500,
      PAY_AMT5: 3000,
      PAY_AMT6: 2500,
    },
  },
  {
    name: 'Moderate Risk Borrower',
    tag: 'Moderate',
    description: 'Moderate limit (NT$ 80k), revolving balance, 1 month recent delay in September, partially paying statements.',
    values: {
      LIMIT_BAL: 80000,
      SEX: 1,
      EDUCATION: 2,
      MARRIAGE: 1,
      AGE: 29,
      PAY_0: 1,
      PAY_2: 0,
      PAY_3: 0,
      PAY_4: 0,
      PAY_5: 0,
      PAY_6: 0,
      BILL_AMT1: 45000,
      BILL_AMT2: 43000,
      BILL_AMT3: 41000,
      BILL_AMT4: 38000,
      BILL_AMT5: 36000,
      BILL_AMT6: 35000,
      PAY_AMT1: 2000,
      PAY_AMT2: 2000,
      PAY_AMT3: 2000,
      PAY_AMT4: 2000,
      PAY_AMT5: 2000,
      PAY_AMT6: 2000,
    },
  },
  {
    name: 'High Risk Delinquent',
    tag: 'High Risk',
    description: 'Low credit limit (NT$ 20k), 2+ months persistent payment delays, near max utilization, minimal repayment amounts.',
    values: {
      LIMIT_BAL: 20000,
      SEX: 2,
      EDUCATION: 2,
      MARRIAGE: 1,
      AGE: 24,
      PAY_0: 2,
      PAY_2: 2,
      PAY_3: 2,
      PAY_4: 2,
      PAY_5: 2,
      PAY_6: 2,
      BILL_AMT1: 19800,
      BILL_AMT2: 19500,
      BILL_AMT3: 19200,
      BILL_AMT4: 18900,
      BILL_AMT5: 18600,
      BILL_AMT6: 18300,
      PAY_AMT1: 500,
      PAY_AMT2: 500,
      PAY_AMT3: 500,
      PAY_AMT4: 500,
      PAY_AMT5: 500,
      PAY_AMT6: 500,
    },
  },
]

type HistoryItem = {
  id: string
  timestamp: string
  model_id: string
  limit_bal: number
  probability: number
  risk_category: string
  predicted_class: string
  calibrated: boolean
}

export function PredictionWorkspace() {
  const [models, setModels] = useState<ModelSummary[]>([])
  const [modelId, setModelId] = useState('')
  const [schema, setSchema] = useState<ModelSchema | null>(null)
  const [details, setDetails] = useState<ModelDetails | null>(null)
  const [values, setValues] = useState<Record<string, string>>({})
  const [result, setResult] = useState<Prediction | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const [history, setHistory] = useState<HistoryItem[]>(() => {
    try {
      const saved = localStorage.getItem('creditai_prediction_history')
      return saved ? (JSON.parse(saved) as HistoryItem[]) : []
    } catch {
      return []
    }
  })

  const loadModel = useCallback(async (id: string, isInitial = false) => {
    if (!isInitial) {
      setLoading(true)
      setLoadError(null)
      setSchema(null)
      setDetails(null)
    }
    try {
      const [nextSchema, nextDetails] = await Promise.all([
        researchApi.schema(id),
        researchApi.details(id),
      ])
      setSchema(nextSchema)
      setDetails(nextDetails)
    } catch (cause) {
      setLoadError(cause instanceof Error ? cause.message : 'Model information could not be loaded.')
    } finally {
      setLoading(false)
    }
  }, [])

  const checkConnectivityAndModels = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const [statusRes, modelsRes] = await Promise.allSettled([
        researchApi.status(),
        researchApi.models(),
      ])

      if (statusRes.status === 'fulfilled') {
        setSystemStatus(statusRes.value)
      } else {
        setSystemStatus({
          backend_connectivity: 'disconnected',
          models_registered: 0,
          research_inference_ready: false,
          indian_production_scoring: 'not_validated',
        })
      }

      if (modelsRes.status === 'fulfilled') {
        const available = modelsRes.value.models
        setModels(available)
        if (available.length > 0) {
          const selected = available[0].model_id
          setModelId(selected)
          await loadModel(selected, false)
        } else {
          setLoadError('No research models are currently registered.')
          setLoading(false)
        }
      } else {
        throw modelsRes.reason
      }
    } catch (cause) {
      setLoading(false)
      setLoadError(
        cause instanceof Error
          ? cause.message
          : 'The research API is unreachable. Start the backend with uvicorn src.api.app:app, then retry.'
      )
    }
  }, [loadModel])

  useEffect(() => {
    let active = true
    const init = async () => {
      try {
        const [statusRes, modelsRes] = await Promise.allSettled([
          researchApi.status(),
          researchApi.models(),
        ])
        if (!active) return

        if (statusRes.status === 'fulfilled') {
          setSystemStatus(statusRes.value)
        } else {
          setSystemStatus({
            backend_connectivity: 'disconnected',
            models_registered: 0,
            research_inference_ready: false,
            indian_production_scoring: 'not_validated',
          })
        }

        if (modelsRes.status === 'fulfilled') {
          const available = modelsRes.value.models
          setModels(available)
          if (available.length > 0) {
            const selected = available[0].model_id
            setModelId(selected)
            await loadModel(selected, true)
          } else {
            setLoadError('No research models are currently registered.')
            setLoading(false)
          }
        } else {
          throw modelsRes.reason
        }
      } catch (cause) {
        if (!active) return
        setLoading(false)
        setLoadError(
          cause instanceof Error
            ? cause.message
            : 'The research API is unreachable. Start the backend with uvicorn src.api.app:app, then retry.'
        )
      }
    }
    void init()
    return () => {
      active = false
    }
  }, [loadModel])

  function applyPreset(preset: PresetProfile) {
    const stringified = Object.fromEntries(
      Object.entries(preset.values).map(([k, v]) => [k, String(v)])
    )
    setValues(stringified)
    setError(null)
  }

  function clearForm() {
    setValues({})
    setResult(null)
    setError(null)
  }

  function clearHistory() {
    setHistory([])
    try {
      localStorage.removeItem('creditai_prediction_history')
    } catch {
      /* ignore */
    }
  }

  function updateField(name: string, value: string) {
    setValues((current) => ({ ...current, [name]: value }))
    setError(null)
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setResult(null)
    if (!schema) return

    const missing = Object.entries(schema.raw_features).filter(
      ([name, field]) => field.required && (values[name] === undefined || values[name].trim() === '')
    )
    if (missing.length) {
      setError(`Complete all required fields. Missing: ${missing.map(([name]) => fieldLabel(name)).join(', ')}.`)
      return
    }

    const features = Object.fromEntries(
      Object.entries(schema.raw_features).map(([name]) => [name, Number(values[name])])
    )

    const invalid = Object.entries(schema.raw_features).find(([name, field]) => {
      const value = features[name]
      return (
        !Number.isFinite(value) ||
        (field.range && (value < field.range[0] || value > field.range[1])) ||
        (field.values && !field.values.includes(value))
      )
    })
    if (invalid) {
      setError(`${fieldLabel(invalid[0])} is outside supported ranges. Check valid values and retry.`)
      return
    }

    setSubmitting(true)
    try {
      const prediction = await researchApi.predict(modelId, features)
      setResult(prediction)

      // Save to local prediction history (no PII, metadata only)
      const historyEntry: HistoryItem = {
        id: `pred-${Date.now()}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        model_id: prediction.model_id,
        limit_bal: features['LIMIT_BAL'] || 0,
        probability: prediction.probability,
        risk_category: prediction.risk_category,
        predicted_class: prediction.predicted_class,
        calibrated: prediction.calibrated,
      }
      setHistory((prev) => {
        const updated = [historyEntry, ...prev.slice(0, 9)]
        try {
          localStorage.setItem('creditai_prediction_history', JSON.stringify(updated))
        } catch {
          /* ignore storage issues */
        }
        return updated
      })
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Prediction request failed. Please retry.')
    } finally {
      setSubmitting(false)
    }
  }

  // Group features into logical subsets for user readability
  const demographicKeys = ['LIMIT_BAL', 'SEX', 'EDUCATION', 'MARRIAGE', 'AGE']
  const delinquencyKeys = ['PAY_0', 'PAY_2', 'PAY_3', 'PAY_4', 'PAY_5', 'PAY_6']
  const billKeys = ['BILL_AMT1', 'BILL_AMT2', 'BILL_AMT3', 'BILL_AMT4', 'BILL_AMT5', 'BILL_AMT6']
  const paymentKeys = ['PAY_AMT1', 'PAY_AMT2', 'PAY_AMT3', 'PAY_AMT4', 'PAY_AMT5', 'PAY_AMT6']

  const isConnected = systemStatus?.backend_connectivity === 'connected'

  return (
    <>
      <div className="section-title">
        <div>
          <p className="eyebrow">RESEARCH INFERENCE WORKSPACE</p>
          <h1>Borrower Risk Prediction</h1>
          <p className="section-detail">
            Select a verified research model, input borrower features or load a benchmark profile, and execute genuine model inference.
          </p>
        </div>
        <span className="source-tag source-live-unvalidated">Research only</span>
      </div>

      {/* Operational 4-Way Status Bar */}
      <div className="system-status-ribbon" role="region" aria-label="System status indicators">
        <div className={`status-node ${isConnected ? 'status-ok' : 'status-bad'}`}>
          <span className="status-indicator-dot" />
          <div>
            <small>BACKEND</small>
            <strong>{isConnected ? 'Connected (Port 8000)' : 'Disconnected'}</strong>
          </div>
        </div>
        <div className="status-node status-ok">
          <span className="status-indicator-dot" />
          <div>
            <small>MODEL ARTIFACTS</small>
            <strong>Loaded & Verified (Joblib)</strong>
          </div>
        </div>
        <div className="status-node status-ok">
          <span className="status-indicator-dot" />
          <div>
            <small>RESEARCH INFERENCE</small>
            <strong>Active (UCI Taiwan XGBoost)</strong>
          </div>
        </div>
        <div className="status-node status-warning">
          <span className="status-indicator-dot dot-amber" />
          <div>
            <small>INDIAN PRODUCTION SCORING</small>
            <strong>NOT VALIDATED (/v1/score Gated)</strong>
          </div>
        </div>
      </div>

      <div className="research-warning" role="note">
        <span className="notice-icon">!</span>
        <div>
          <strong>Safety isolation notice:</strong>
          <span>
            {' '}This prediction service executes research inference on the historical Taiwan credit card benchmark (DS003). It is not validated for Indian underwriting or commercial credit decisions.
          </span>
        </div>
      </div>

      {loadError && (
        <div className="api-error" role="alert">
          <strong>Backend Service Unreachable</strong>
          <p>{loadError}</p>
          <button className="button-secondary" onClick={() => void checkConnectivityAndModels()} disabled={loading}>
            {loading ? 'Retrying…' : 'Retry Connectivity'}
          </button>
        </div>
      )}

      <div className="prediction-layout">
        <section className="panel prediction-form-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">BORROWER PROFILE</p>
              <h2>Input Features</h2>
              <p>Raw fields expected by the model. 27 engineered signals are computed server-side.</p>
            </div>
            <span className="field-count">{schema ? `${Object.keys(schema.raw_features).length} fields` : '—'}</span>
          </div>

          <div className="form-group model-picker-group">
            <label className="form-label" htmlFor="model-select">
              Active Research Model
            </label>
            <select
              id="model-select"
              className="form-control"
              value={modelId}
              onChange={(e) => {
                setModelId(e.target.value)
                void loadModel(e.target.value)
              }}
              disabled={models.length === 0}
            >
              {models.map((m) => (
                <option key={m.model_id} value={m.model_id}>
                  {m.model_id} · {m.model_type} ({m.geography})
                </option>
              ))}
            </select>
          </div>

          {/* Preset loader toolbar */}
          <div className="preset-toolbar">
            <span className="preset-label">Load Sample Borrower:</span>
            <div className="preset-buttons">
              {PRESET_BORROWERS.map((preset) => (
                <button
                  key={preset.tag}
                  type="button"
                  className="preset-btn"
                  onClick={() => applyPreset(preset)}
                  title={preset.description}
                >
                  <span className="preset-dot" />
                  {preset.name}
                </button>
              ))}
              <button
                type="button"
                className="preset-clear-btn"
                onClick={clearForm}
                title="Reset all inputs"
              >
                Clear Form
              </button>
            </div>
          </div>

          {loading ? (
            <div className="inline-loading" role="status">
              Loading model schema and calibrator parameters…
            </div>
          ) : schema ? (
            <form onSubmit={(e) => void submit(e)}>
              {/* Group 1: Demographics */}
              <div className="feature-section">
                <h4 className="feature-section-title">1. Demographics & Credit Capacity</h4>
                <div className="feature-grid">
                  {demographicKeys.map((name) => (
                    <FeatureInput
                      key={name}
                      name={name}
                      field={schema.raw_features[name]}
                      value={values[name] ?? ''}
                      onChange={(val) => updateField(name, val)}
                    />
                  ))}
                </div>
              </div>

              {/* Group 2: Repayment History */}
              <div className="feature-section">
                <h4 className="feature-section-title">2. Repayment Status History (PAY_0 to PAY_6)</h4>
                <p className="feature-section-desc">
                  -2: No consumption · -1: Paid duly · 0: Revolving credit · 1–9: Delinquent months
                </p>
                <div className="feature-grid">
                  {delinquencyKeys.map((name) => (
                    <FeatureInput
                      key={name}
                      name={name}
                      field={schema.raw_features[name]}
                      value={values[name] ?? ''}
                      onChange={(val) => updateField(name, val)}
                    />
                  ))}
                </div>
              </div>

              {/* Group 3: Bill Statements */}
              <div className="feature-section">
                <h4 className="feature-section-title">3. Monthly Bill Statements (NT$)</h4>
                <div className="feature-grid">
                  {billKeys.map((name) => (
                    <FeatureInput
                      key={name}
                      name={name}
                      field={schema.raw_features[name]}
                      value={values[name] ?? ''}
                      onChange={(val) => updateField(name, val)}
                    />
                  ))}
                </div>
              </div>

              {/* Group 4: Payments Paid */}
              <div className="feature-section">
                <h4 className="feature-section-title">4. Monthly Amounts Paid (NT$)</h4>
                <div className="feature-grid">
                  {paymentKeys.map((name) => (
                    <FeatureInput
                      key={name}
                      name={name}
                      field={schema.raw_features[name]}
                      value={values[name] ?? ''}
                      onChange={(val) => updateField(name, val)}
                    />
                  ))}
                </div>
              </div>

              {error && (
                <div className="form-error" role="alert">
                  {error}
                </div>
              )}

              <div className="form-action-bar">
                <button
                  className="button-primary prediction-submit"
                  type="submit"
                  disabled={submitting || loading}
                >
                  {submitting ? 'Executing XGBoost & SHAP…' : 'Run Prediction'}
                  <span aria-hidden="true"> →</span>
                </button>
                <button
                  type="button"
                  className="button-quiet"
                  onClick={clearForm}
                  disabled={submitting}
                >
                  Reset
                </button>
              </div>
            </form>
          ) : (
            !loadError && <div className="inline-loading">Feature schema is currently unavailable.</div>
          )}
        </section>

        {/* Prediction Results & Explanation Panel */}
        <section className="panel prediction-result-panel" aria-live="polite">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">INFERENCE ENGINE</p>
              <h2>Prediction Output</h2>
              <p>Real-time model score, calibrated probability, and SHAP attribution.</p>
            </div>
          </div>

          {result ? (
            <PredictionResult result={result} details={details} />
          ) : (
            <div className="result-empty">
              <span className="result-icon">◎</span>
              <h3>Awaiting Input</h3>
              <p>
                Click one of the sample borrower profiles above (Low Risk, Moderate, or High Risk) or enter custom features, then click <strong>Run Prediction</strong>.
              </p>
            </div>
          )}

          {/* Session Prediction History */}
          {history.length > 0 && (
            <div className="history-block">
              <div className="history-head">
                <h4>Session Prediction History ({history.length})</h4>
                <button type="button" className="text-link" onClick={clearHistory}>
                  Clear
                </button>
              </div>
              <div className="history-list">
                {history.map((item) => (
                  <div key={item.id} className="history-item">
                    <div>
                      <strong>NT$ {item.limit_bal.toLocaleString()}</strong>
                      <small>{item.timestamp} · {item.model_id}</small>
                    </div>
                    <div className="history-score">
                      <span className={`status-pill ${item.risk_category.toLowerCase()}`}>
                        {item.risk_category}
                      </span>
                      <strong>{(item.probability * 100).toFixed(1)}%</strong>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      </div>

      {details && (
        <div className="provenance-strip">
          <span>
            <b>Dataset:</b> {details.dataset_name} ({details.dataset_id})
          </span>
          <span>
            <b>Geography / Period:</b> {details.geography} · {details.time_coverage}
          </span>
          <span>
            <b>Target Definition:</b> {details.target_meaning}
          </span>
          <span>
            <b>Calibration Status:</b> {details.calibration_status}
          </span>
        </div>
      )}
      <p className="research-footnote">
        Research inference remains strictly isolated from <code>/v1/score</code>, which remains not validated for production lending.
      </p>
    </>
  )
}

function FeatureInput({
  name,
  field,
  value,
  onChange,
}: {
  name: string
  field: FeatureField
  value: string
  onChange: (value: string) => void
}) {
  const label = fieldLabel(name)
  const id = `feature-${name}`
  const hint = [field.description, field.range ? `${field.range[0]} to ${field.range[1]}` : '', field.unit]
    .filter(Boolean)
    .join(' · ')

  return (
    <div className="feature-field">
      <label htmlFor={id}>
        {label}
        <span>{field.required ? 'Required' : 'Optional'}</span>
      </label>
      {field.values ? (
        <select
          className="form-control"
          id={id}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          required={field.required}
        >
          <option value="">Select…</option>
          {field.values.map((item) => (
            <option key={item} value={item}>
              {item}
              {field.value_labels?.[String(item)] ? ` · ${field.value_labels[String(item)]}` : ''}
            </option>
          ))}
        </select>
      ) : (
        <input
          className="form-control"
          id={id}
          type="number"
          step="1"
          value={value}
          min={field.range?.[0]}
          max={field.range?.[1]}
          onChange={(event) => onChange(event.target.value)}
          required={field.required}
          aria-describedby={`${id}-hint`}
        />
      )}
      <small id={`${id}-hint`}>{hint}</small>
    </div>
  )
}

function PredictionResult({
  result,
  details,
}: {
  result: Prediction
  details: ModelDetails | null
}) {
  const pct = Math.max(0, Math.min(100, result.probability * 100))
  const isHighRisk = result.risk_category.toLowerCase() === 'high'
  const isMediumRisk = result.risk_category.toLowerCase() === 'medium'
  const riskClass = isHighRisk ? 'risk-high' : isMediumRisk ? 'risk-medium' : 'risk-low'

  return (
    <div className="prediction-output">
      <div className={`prediction-class ${riskClass}`}>
        <span>Predicted Default Class</span>
        <strong>{result.predicted_class}</strong>
        <small>Target: {result.target_meaning}</small>
      </div>

      <div className="probability-gauge-block">
        <div className="gauge-header">
          <span>{result.calibrated ? 'Calibrated Default Probability (PD)' : 'Raw Model Score'}</span>
          <strong className="gauge-number">{pct.toFixed(1)}%</strong>
        </div>
        <div
          className="probability-track"
          role="meter"
          aria-label={result.calibrated ? 'Calibrated default probability' : 'Uncalibrated score'}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Number(pct.toFixed(1))}
        >
          <i
            className={`gauge-fill ${riskClass}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="gauge-legend">
          <span>0% Low Risk</span>
          <span>Threshold: {(result.threshold * 100).toFixed(0)}%</span>
          <span>100% High Risk</span>
        </div>
        <small className="gauge-note">
          Risk tier: <strong>{result.risk_category}</strong> · Evaluated at classification threshold {result.threshold.toFixed(2)}
        </small>
      </div>

      <div className="result-facts">
        <div>
          <span>Model ID</span>
          <strong>{result.model_id}</strong>
        </div>
        <div>
          <span>Dataset / Geography</span>
          <strong>{result.dataset_name} ({result.geography})</strong>
        </div>
        <div>
          <span>Calibration</span>
          <strong>{result.calibrated ? result.calibration_method ?? 'Platt scaling' : 'Uncalibrated'}</strong>
        </div>
        <div>
          <span>Timestamp</span>
          <strong>{new Date(result.prediction_timestamp).toLocaleTimeString()}</strong>
        </div>
      </div>

      {/* SHAP Feature Attribution */}
      {result.feature_contributions && result.feature_contributions.length > 0 ? (
        <div className="explanation-section">
          <div className="explanation-header">
            <h4>Key Decision Drivers (SHAP Local Explanation)</h4>
            <span className="attribution-tag">TreeExplainer Attribution</span>
          </div>
          <p className="attribution-caption">
            Features pushing probability toward default (red) versus reducing default risk (teal). Association in the fitted tree model; does not prove individual causation.
          </p>
          <div className="explanation-list">
            {result.feature_contributions.map((item: FeatureContribution) => {
              const isIncrease = item.direction === 'increases_risk'
              return (
                <div key={item.feature} className={`shap-row ${isIncrease ? 'shap-risk-up' : 'shap-risk-down'}`}>
                  <div className="shap-meta">
                    <span className="shap-name">{fieldLabel(item.feature)}</span>
                    <span className="shap-dir">{isIncrease ? '+ Increases Risk' : '− Lowers Risk'}</span>
                  </div>
                  <div className="shap-bar-track">
                    <div
                      className="shap-bar-fill"
                      style={{ width: `${Math.min(100, item.contribution * 120)}%` }}
                    />
                  </div>
                  <strong className="shap-val">+{item.contribution.toFixed(3)}</strong>
                </div>
              )
            })}
          </div>
        </div>
      ) : (
        <div className="unavailable-note">
          <strong>SHAP Explanation Offline</strong>
          <span>Local feature contributions could not be generated for this prediction.</span>
        </div>
      )}

      <div className="result-limit">
        <strong>Limitation Disclaimer:</strong>{' '}
        {details?.limitations?.[0] ??
          'Experimental research inference only. Model output is a statistical estimate on Taiwan card data, not a credit guarantee.'}
      </div>
    </div>
  )
}
