import { ConfidenceGuardian } from './ConfidenceGuardian'
import type { GuardianAssessment } from './api'
import { useCallback, useEffect, useState } from 'react'
import type { FeatureField, FeatureContribution, ModelDetails, ModelSchema, ModelSummary, Prediction, SystemStatus } from './api'
import { researchApi } from './api'
import { displayFeatureName } from './analytics'
import { calculateAssessment, contributionDirection, predictionFiveW } from './assessment'
import { MonthlyHistoryEditor } from './MonthlyHistoryEditor'
import { currentMonth, historyFromFeatures, inspectHistory, monthIndex, periodAt, type HistoryCurrency, type MonthlyRecord } from './monthlyHistory'
import { HistoryInsights } from './HistoryInsights'
import { historyMoney } from './historyAnalytics'

const fieldLabel = displayFeatureName
const profileHints: Record<string, string> = {
  LIMIT_BAL: 'Assigned credit-card limit. It is distinct from income, available cash and outstanding debt.',
  SEX: 'Recorded gender category in the historical dataset.',
  EDUCATION: 'Education level as recorded in the Taiwan dataset.',
  MARRIAGE: 'Marital-status category as recorded in the Taiwan dataset.',
  AGE: 'Age in completed years at the reporting period.',
}
const visitorFields: Record<string, FeatureField> = {
  LIMIT_BAL: { type: 'numeric', description: '', required: false, range: [0, 1e9] },
  SEX: { type: 'categorical', description: '', required: false, values: [1, 2], value_labels: { 1: 'Male', 2: 'Female' } },
  EDUCATION: { type: 'categorical', description: '', required: false, values: [1, 2, 3, 4, 0, 5, 6], value_labels: { 1: 'Graduate school', 2: 'University', 3: 'High school', 4: 'Other', 0: 'Unclassified', 5: 'Unclassified', 6: 'Unclassified' } },
  MARRIAGE: { type: 'categorical', description: '', required: false, values: [1, 2, 3, 0], value_labels: { 1: 'Married', 2: 'Single', 3: 'Other', 0: 'Unclassified' } },
  AGE: { type: 'numeric', description: '', required: false, range: [0, 120] },
}

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
    description: 'High credit limit (TWD 200k), prime age, university degree, zero repayment delays, healthy payment-to-bill ratio.',
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
    description: 'Moderate limit (TWD 80k), revolving balance, 1 month recent delay in September, partially paying statements.',
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
    description: 'Low credit limit (TWD 20k), 2+ months persistent payment delays, near max utilization, minimal repayment amounts.',
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
  const [currency, setCurrency] = useState<HistoryCurrency>('INR')
  const [months, setMonths] = useState<MonthlyRecord[]>([])
  const [exampleHistory, setExampleHistory] = useState(false)
  const monthReview = inspectHistory(months, currency)
  const modelValues = { ...values, ...monthReview.features }
  const [assessment, setAssessment] = useState<GuardianAssessment | null>(null)
  useEffect(() => {
    if (!assessment) return
    const heading = document.getElementById('guardian-evidence-heading')
    heading?.focus({ preventScroll: true })
    heading?.closest('.guardian-panel')?.scrollIntoView({ block: 'start', behavior: 'instant' })
  }, [assessment])
  const [result, setResult] = useState<Prediction | null>(null)
  const [syntheticProfile, setSyntheticProfile] = useState(false)
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
      setAssessment(null)
      setResult(null)
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
      Object.entries(preset.values).map(([k, v]) => [k, Number.isNaN(v) ? '' : String(v)])
    )
    setAssessment(null)
    setResult(null)
    setValues(Object.fromEntries(Object.entries(stringified).filter(([key]) => !key.startsWith('PAY_') && !key.startsWith('BILL_AMT'))))
    setMonths(historyFromFeatures(stringified))
    setExampleHistory(true)
    setSyntheticProfile(true)
    setError(null)
  }

  function clearForm() {
    setAssessment(null)
    setValues({})
    setMonths([])
    setExampleHistory(false)
    setSyntheticProfile(false)
    setResult(null)
    setError(null)
  }

  function updateMonths(records: MonthlyRecord[], example = exampleHistory && records.length > 0) {
    setMonths(records)
    setExampleHistory(example)
    setAssessment(null)
    setResult(null)
    setError(null)
  }

  function switchCurrency(next: HistoryCurrency) {
    if (next === currency || submitting) return
    if ((months.length || Object.values(values).some(Boolean)) && !window.confirm('Switching currency clears the current profile and history. Continue?')) return
    clearForm()
    setCurrency(next)
  }

  function loadHistoryExample() {
    if (currency === 'TWD') {
      updateMonths(historyFromFeatures(Object.fromEntries(
        Object.entries(PRESET_BORROWERS[0].values).map(([key, value]) => [key, String(value)])
      )), true)
      return
    }
    const latest = monthIndex(currentMonth())! - 1
    updateMonths([
      ['0', '20000', '25000'], ['1', '0', '1500'], ['-1', '-2500', '0'], ['-2', '150000', '12500'],
    ].map(([status, bill, paid], index) => ({ id: index + 1, period: periodAt(latest - index), status, bill, paid })), true)
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
    setAssessment(null)
    setResult(null)
    setValues((current) => ({ ...current, [name]: value }))
    setSyntheticProfile(false)
    setError(null)
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setResult(null)
    if (currency !== 'TWD' || !schema || !monthReview.ready) return

    setAssessment(null)
    setSubmitting(true)
    try {
      const response = await researchApi.guardian(modelId, modelValues)
      setAssessment(response.assessment)
      const prediction = response.prediction
      if (!prediction) return
      setResult(prediction)

      // Save to local prediction history (no PII, metadata only)
      const historyEntry: HistoryItem = {
        id: `pred-${Date.now()}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        model_id: prediction.model_id,
        limit_bal: Number(values.LIMIT_BAL) || 0,
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
            <strong>{isConnected ? 'Connected' : 'Disconnected'}</strong>
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

      {currency === 'TWD' && loadError && (
        <div className="api-error" role="alert">
          <strong>Backend Service Unreachable</strong>
          <p>{loadError}</p>
          <button className="button-secondary" onClick={() => void checkConnectivityAndModels()} disabled={loading}>
            {loading ? 'Retrying…' : 'Retry Connectivity'}
          </button>
        </div>
      )}

      <div className={currency === 'INR' ? 'prediction-layout prediction-layout-inr' : 'prediction-layout'}>
        <section className="panel prediction-form-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">BORROWER PROFILE</p>
              <h2>Input Features</h2>
              <p>{currency === 'INR' ? 'Optional profile context for your descriptive history.' : 'Taiwan research inputs use the original New Taiwan dollar (TWD) units.'}</p>
            </div>
            <span className="field-count">{currency === 'INR' ? 'INR · Analytics' : 'TWD · Research'}</span>
          </div>

          <div className="monthly-actions" role="group" aria-label="History currency mode">
            <button type="button" className="button-secondary" disabled={submitting} aria-pressed={currency === 'INR'} onClick={() => switchCurrency('INR')}>INR history analytics</button>
            <button type="button" className="button-secondary" disabled={submitting} aria-pressed={currency === 'TWD'} onClick={() => switchCurrency('TWD')}>Taiwan research mode (TWD)</button>
          </div>
          <p className="monthly-help">Each mode keeps amounts in its own currency. Switching modes clears the current form. INR inputs are for analytics only because there is no validated conversion workflow for this model.</p>
          {currency === 'TWD' && <>
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
              disabled={models.length === 0 || submitting}
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
                  disabled={submitting}
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
                disabled={submitting}
                onClick={clearForm}
                title="Reset all inputs"
              >
                Clear Form
              </button>
            </div>
          </div>

          <details className="guardian-demo">
            <summary>Guardian research demonstrations</summary>
            <div className="preset-buttons">
              {([
                ['Unusual valid profile', { LIMIT_BAL: 1000000, PAY_0: 9, PAY_2: 9, PAY_3: 9 }],
                ['Missing age', { AGE: NaN }],
                ['Invalid repayment code', { PAY_0: 99 }],
                ['Bill exceeds credit limit', { LIMIT_BAL: 20000, BILL_AMT1: 75000 }],
              ] as const).map(([label, overrides]) => <button className="preset-btn" type="button" key={label} disabled={submitting} onClick={() => {
                applyPreset({ ...PRESET_BORROWERS[0], values: { ...PRESET_BORROWERS[0].values, ...overrides } })
              }}>{label}</button>)}
              <button className="preset-btn" type="button" disabled={submitting} onClick={() => {
                setResult(null); setError(null); setAssessment(null); setSubmitting(true)
                void researchApi.guardian('guardian-demo-unavailable', {}).then(response => setAssessment(response.assessment))
                  .catch(() => setError('The evidence check could not reach the research service.'))
                  .finally(() => setSubmitting(false))
              }}>Check unavailable model</button>
            </div>
            <p>KNN has no frozen distribution reference. Select KNN and run a valid sample to see that state.</p>
          </details>
          </>}
          {currency === 'TWD' && loading ? (
            <div className="inline-loading" role="status">
              Loading model schema and calibrator parameters…
            </div>
          ) : currency === 'INR' || schema ? (
            <form noValidate onSubmit={(e) => void submit(e)}><fieldset className="guardian-form-fields" disabled={submitting}>
              {/* Group 1: Demographics */}
              <div className="feature-section">
                <h4 className="feature-section-title">1. Demographics & Credit Capacity</h4>
                <p className="feature-section-desc">These demographic categories are included for historical model compatibility. They are separate from real-world lending requirements.</p>
                <div className="feature-grid">
                  {demographicKeys.map((name) => (
                    <FeatureInput
                      key={name}
                      name={name}
                      field={currency === 'INR' ? visitorFields[name] : schema!.raw_features[name]}
                      currency={currency}
                      value={values[name] ?? ''}
                      onChange={(val) => updateField(name, val)}
                    />
                  ))}
                </div>
              </div>

              {exampleHistory && <p className="source-tag">{currency === 'INR' ? 'Illustrative INR history' : 'Synthetic TWD research history'}</p>}
              <MonthlyHistoryEditor key={currency} records={months} review={monthReview} onChange={updateMonths} currency={currency} loadExample={loadHistoryExample} />
              <HistoryInsights review={monthReview} currency={currency} />
              {error && (
                <div className="form-error" role="alert">
                  {error}
                </div>
              )}

              <div className="form-action-bar">
                <button
                  className="button-primary prediction-submit"
                  type="submit"
                  disabled={currency === 'INR' || submitting || loading || !monthReview.ready}
                >
                  {currency === 'INR' ? 'Prediction unavailable for INR' : submitting ? 'Executing XGBoost & SHAP…' : 'Run Prediction'}
                  <span aria-hidden="true"> →</span>
                </button>
                <button
                  type="button"
                  className="button-quiet"
                  onClick={clearForm} disabled={submitting}
                >
                  Reset
                </button>
              </div>
            </fieldset></form>
          ) : (
            !loadError && <div className="inline-loading">Feature schema is currently unavailable.</div>
          )}
        </section>

        {/* Prediction Results & Explanation Panel */}
        {currency === 'TWD' && <section className="panel prediction-result-panel" aria-live="polite">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">INFERENCE ENGINE</p>
              <h2>Prediction Output</h2>
              <p>Real-time model score, calibrated probability, and SHAP attribution.</p>
            </div>
          </div>

          {assessment && <ConfidenceGuardian assessment={assessment} />}
          {result ? (
            <PredictionResult result={result} details={details} values={modelValues} syntheticProfile={syntheticProfile || exampleHistory} />
          ) : !assessment && (
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
                      <strong>{historyMoney(item.limit_bal, 'TWD')}</strong>
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
        </section>}
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
  currency,
}: {
  name: string
  field: FeatureField
  value: string
  onChange: (value: string) => void
  currency: HistoryCurrency
}) {
  const label = name === 'LIMIT_BAL' ? `Credit Limit (${currency === 'INR' ? '₹' : 'TWD'})` : fieldLabel(name)
  const id = `feature-${name}`
  const hint = [profileHints[name], field.range ? `${field.range[0].toLocaleString('en-IN')} to ${field.range[1].toLocaleString('en-IN')}` : '']
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
          aria-describedby={`${id}-hint`}
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
  values,
  syntheticProfile,
}: {
  result: Prediction
  details: ModelDetails | null
  values: Record<string, string>
  syntheticProfile: boolean
}) {
  const pct = Math.max(0, Math.min(100, result.probability * 100))
  const probability = result.probability
  const assessment = calculateAssessment(probability, result.threshold)
  const { complement, threshold } = assessment
  const decision = { comparison: assessment.comparison, label: assessment.classification }
  const fiveW = predictionFiveW({
    target: result.target_meaning,
    dataset: result.dataset_name,
    geography: result.geography,
    timeCoverage: details?.time_coverage ?? '',
    synthetic: syntheticProfile,
    hasAttribution: (result.feature_contributions?.length ?? 0) > 0,
  })
  const riskClass = probability >= threshold ? 'risk-high' : 'risk-low'
  const contributions = result.feature_contributions ?? []
  const increasing = contributions.filter((item) => contributionDirection(item.direction) === 'increases_risk')
  const decreasing = contributions.filter((item) => contributionDirection(item.direction) === 'decreases_risk')
  const unknown = contributions.filter((item) => contributionDirection(item.direction) === 'unknown')
  const currencyContext = result.geography.toLowerCase() === 'taiwan' ? 'Taiwan dataset values (TWD; original dataset units)' : `${result.geography} dataset units`
  const featureLabel = (name: string) => ({
    PAY_0: 'Most recent repayment status (September 2005)',
    PAY_2: 'Repayment status two months before the target month',
    PAY_3: 'Repayment status three months before the target month',
    PAY_4: 'Repayment status four months before the target month',
    PAY_5: 'Repayment status five months before the target month',
    PAY_6: 'Repayment status six months before the target month',
    BILL_AMT1: 'Most recent bill statement amount',
    PAY_AMT1: 'Most recent payment amount',
  } as Record<string, string>)[name] ?? displayFeatureName(name)
  const contributionRows = (items: FeatureContribution[]) => items.map((item) => {
    const submitted = values[item.feature]
    return <div className="evidence-driver" key={item.feature}>
      <div><strong>{featureLabel(item.feature)}</strong><code>{item.feature}</code></div>
      <span>{submitted !== undefined ? `Submitted value: ${submitted}${/^(LIMIT_BAL|BILL_AMT\d|PAY_AMT\d)$/.test(item.feature) ? ` · ${currencyContext}` : ''}` : 'Engineered signal derived from submitted fields'}</span>
      <b>{item.contribution.toFixed(4)} model-output units</b>
    </div>
  })

  return (
    <div className="prediction-output">
      <section className={`assessment-summary ${riskClass}`}>
        <p className="eyebrow">MODEL RISK ASSESSMENT · RESEARCH ONLY</p>
        <div className="assessment-metrics">
          <div><span>Estimated default probability (PD)</span><strong>{(probability * 100).toFixed(1)}%</strong></div>
          <div><span>Estimated non-default complement</span><strong>{(complement * 100).toFixed(1)}%</strong></div>
        </div>
        <p><b>Research classification:</b> {decision.label}</p>
        <p><b>Research threshold:</b> {(threshold * 100).toFixed(1)}%</p>
        <p>{(probability * 100).toFixed(1)}% {decision.comparison} {(threshold * 100).toFixed(1)}% research threshold; the model assigns the {decision.label.toLowerCase()}.</p>
        <p className="assessment-caveat">{(complement * 100).toFixed(1)}% = 1 − {(probability * 100).toFixed(1)}%. It is a mathematical complement, not a guarantee of repayment.</p>
      </section>

      <div className="probability-gauge-block">
        <div className="gauge-header">
          <span>{result.calibrated ? 'Estimated default probability (calibrated)' : 'Estimated default probability (uncalibrated model output)'}</span>
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
          <span>0%</span>
          <span>Research threshold: {(threshold * 100).toFixed(1)}%</span>
          <span>100%</span>
        </div>
        <small className="gauge-note">This threshold is for research classification only. It is not a lending policy.</small>
      </div>

      <div className="result-facts">
        <div><span>Model ID</span><strong>{result.model_id}</strong></div>
        <div><span>Dataset / Geography</span><strong>{result.dataset_name} ({result.geography})</strong></div>
        <div><span>Calibration</span><strong>{result.calibrated ? result.calibration_method ?? 'Calibrated' : 'Not calibrated'}</strong></div>
        <div><span>Timestamp</span><strong>{new Date(result.prediction_timestamp).toLocaleString()}</strong></div>
      </div>

      <section className="assessment-math">
        <h3>How this result was calculated</h3>
        <p>Estimated PD = {probability.toFixed(4)}</p>
        <p>PD percentage = {probability.toFixed(4)} × 100 = {(probability * 100).toFixed(2)}%</p>
        <p>Estimated non-default complement = 1 − {probability.toFixed(4)} = {complement.toFixed(4)} ({(complement * 100).toFixed(2)}%)</p>
        <p>Research threshold = {threshold.toFixed(4)} ({(threshold * 100).toFixed(1)}%)</p>
        <p>{probability.toFixed(4)} {decision.comparison} {threshold.toFixed(4)} → {decision.label}</p>
        <p className="research-footnote">{result.calibrated ? `Calibration: ${result.calibration_method ?? 'method recorded as calibrated'}. Calibration was fitted for its documented research dataset; it does not establish accuracy for other populations.` : 'This output is not calibrated; interpret it only as the model’s research estimate.'}</p>
      </section>

      <section className="assessment-5w">
        <h3>Understanding this assessment — 5W</h3>
        <dl>
          <dt>WHAT</dt><dd>{fiveW.what}</dd>
          <dt>WHY</dt><dd>{fiveW.why}</dd>
          <dt>WHO</dt><dd>{fiveW.who}</dd>
          <dt>WHEN</dt><dd>{fiveW.when}</dd>
          <dt>WHERE / DATA CONTEXT</dt><dd>{fiveW.where}</dd>
        </dl>
        <details><summary>View submitted feature values · {currencyContext}</summary><div className="submitted-values">{Object.entries(values).map(([name, value]) => <div key={name}><span>{featureLabel(name)} <code>{name}</code></span><strong>{value || 'Not submitted'}{value && /^(LIMIT_BAL|BILL_AMT\d|PAY_AMT\d)$/.test(name) ? ` · ${currencyContext}` : ''}</strong></div>)}</div></details>
      </section>

      {contributions.length > 0 ? (
        <div className="explanation-section">
          <div className="explanation-header">
            <h4>Model contribution explanation</h4>
            <span className="attribution-tag">{result.model_id.includes('knn') ? 'Local neighbor attribution' : 'TreeExplainer SHAP'}</span>
          </div>
          <p className="attribution-caption">Positive-class SHAP sign indicates movement in the model output toward or away from default. Magnitudes are model-output units, not probability percentage points. SHAP describes model attribution, not causation.</p>
          {increasing.length > 0 && <section><h5>Factors moving estimated risk higher</h5><div className="evidence-driver-list">{contributionRows(increasing)}</div></section>}
          {decreasing.length > 0 && <section><h5>Factors moving estimated risk lower</h5><div className="evidence-driver-list">{contributionRows(decreasing)}</div></section>}
          {unknown.length > 0 && <div className="unavailable-note"><strong>Direction not supplied</strong><span>{unknown.map((item) => fieldLabel(item.feature)).join(', ')} are shown without an inferred direction.</span></div>}
        </div>
      ) : (
        <div className="unavailable-note">
          <strong>Feature attribution unavailable</strong>
          <span>No local contributions were returned for this prediction; the interface will not infer or fabricate drivers.</span>
        </div>
      )}

      <div className="result-limit">
        <strong>Research limitation:</strong>{' '}
        {details?.limitations?.[0] ??
          'Research inference only. The model output is not validated for Indian borrower decisions.'}
      </div>
    </div>
  )
}
