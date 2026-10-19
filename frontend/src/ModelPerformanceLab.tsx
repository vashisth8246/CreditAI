import { useEffect, useState } from 'react'
import type { CurvePoint, EvaluationArtifact } from './api'
import { researchApi } from './api'

export function ModelPerformanceLab() {
  const [evalData, setEvalData] = useState<EvaluationArtifact | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedThreshold, setSelectedThreshold] = useState<number>(0.5)

  useEffect(() => {
    let active = true

    researchApi
      .evaluation('uci_taiwan_xgb')
      .then((evaluation) => {
        if (!active) return
        setEvalData(evaluation)
        setLoading(false)
      })
      .catch((err: unknown) => {
        if (!active) return
        setError(err instanceof Error ? err.message : 'Evaluation data could not be loaded.')
        setLoading(false)
      })

    return () => {
      active = false
    }
  }, [])

  if (loading) {
    return (
      <div className="page-body">
        <div className="section-title">
          <div>
            <p className="eyebrow">MODEL EVIDENCE</p>
            <h1>Model Performance Lab</h1>
            <p className="section-detail">Loading verified evaluation artifacts and curve coordinates…</p>
          </div>
          <span className="source-tag source-historical">Historical benchmark</span>
        </div>
        <div className="inline-loading">Loading reproducible evaluation data on untouched test split…</div>
      </div>
    )
  }

  if (error || !evalData) {
    return (
      <div className="page-body">
        <div className="section-title">
          <div>
            <p className="eyebrow">MODEL EVIDENCE</p>
            <h1>Model Performance Lab</h1>
            <p className="section-detail">Inspect reproducible evidence from the UCI Taiwan benchmark.</p>
          </div>
          <span className="source-tag source-historical">Historical benchmark</span>
        </div>
        <div className="api-error" role="alert">
          <strong>Evaluation Data Unavailable</strong>
          <p>{error ?? 'Evaluation artifacts were not found.'}</p>
          <button className="button-secondary" onClick={() => window.location.reload()}>
            Retry
          </button>
        </div>
      </div>
    )
  }

  const { metadata, summary_metrics, curves, risk_deciles, model_comparison, global_feature_importance } = evalData

  // Match closest threshold from sweep for interactive confusion matrix
  const currentThresholdData =
    curves.threshold_sweep.find((row) => Math.abs(row.threshold - selectedThreshold) < 0.02) ||
    curves.threshold_sweep[Math.floor(curves.threshold_sweep.length / 2)]

  return (
    <>
      <div className="section-title">
        <div>
          <p className="eyebrow">REPRODUCIBLE RESEARCH BENCHMARK</p>
          <h1>Model Performance Lab</h1>
          <p className="section-detail">
            Inspect verified evaluation metrics, curves, and risk deciles computed on the untouched 15% stratified test cohort (N = {metadata.test_sample_count.toLocaleString()}).
          </p>
        </div>
        <span className="source-tag source-historical">Test split evaluation</span>
      </div>

      <div className="research-warning" role="note">
        <span className="notice-icon">!</span>
        <div>
          <strong>Provenance & Calibration Integrity:</strong>
          <span>
            {' '}Evaluated strictly on held-out test data (4,500 samples, 22.13% default prevalence). Model parameters and Platt calibrator were fitted on training and validation splits only. Not validated for Indian borrower populations.
          </span>
        </div>
      </div>

      {/* Provenance Strip */}
      <div className="provenance-strip">
        <span>
          <b>Dataset:</b> {metadata.dataset_name} ({metadata.dataset_id})
        </span>
        <span>
          <b>Geography / Time:</b> {metadata.geography} · {metadata.time_coverage}
        </span>
        <span>
          <b>Model / Algorithm:</b> {metadata.primary_model} (Fitted XGBoost)
        </span>
        <span>
          <b>Evaluation Split:</b> Untouched 15% Test Cohort (N = {metadata.test_sample_count.toLocaleString()})
        </span>
        <span>
          <b>Calibration:</b> {metadata.calibration_status} ({metadata.calibration_method})
        </span>
      </div>

      {/* KPI Cards */}
      <div className="kpi-grid">
        <div className="panel kpi-card blue">
          <div className="kpi-top">
            <span>ROC-AUC (Discrimination)</span>
            <b>⌁</b>
          </div>
          <div className="kpi-value">{summary_metrics.test_roc_auc.toFixed(4)}</div>
          <p>Baseline: 0.5000 (Random) · Reproduced from Phase 1</p>
        </div>

        <div className="panel kpi-card green">
          <div className="kpi-top">
            <span>PR-AUC (Precision-Recall)</span>
            <b>↗</b>
          </div>
          <div className="kpi-value">{summary_metrics.test_pr_auc.toFixed(4)}</div>
          <p>Prevalence baseline: {metadata.test_prevalence.toFixed(4)} ({ (metadata.test_prevalence * 100).toFixed(1) }%)</p>
        </div>

        <div className="panel kpi-card amber">
          <div className="kpi-top">
            <span>Brier Score (Calibrated)</span>
            <b>◎</b>
          </div>
          <div className="kpi-value">{summary_metrics.brier_score_calibrated.toFixed(4)}</div>
          <p>Raw: {summary_metrics.brier_score_raw.toFixed(4)} ({summary_metrics.brier_improvement_pct}% improvement)</p>
        </div>

        <div className="panel kpi-card">
          <div className="kpi-top">
            <span>Separation (Gini / KS)</span>
            <b>◈</b>
          </div>
          <div className="kpi-value">
            {summary_metrics.gini_coefficient.toFixed(3)} / {summary_metrics.ks_statistic.toFixed(3)}
          </div>
          <p>Gini coefficient and Kolmogorov-Smirnov statistic</p>
        </div>
      </div>

      {/* Main Charts Grid: ROC & Precision-Recall */}
      <div className="grid-two">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">DISCRIMINATION CAPACITY</p>
              <h2>ROC Curve</h2>
              <p>True Positive Rate vs. False Positive Rate on 4,500 test samples.</p>
            </div>
            <span className="mini-tag">AUC = {curves.roc.auc.toFixed(4)}</span>
          </div>
          <RocCurveSvg points={curves.roc.points} auc={curves.roc.auc} />
          <p className="chart-footnote">
            Dataset: UCI Taiwan (DS003) · Test split n={metadata.test_sample_count.toLocaleString()}. Measures class ranking across all possible thresholds; random guess AUC is 0.500.
          </p>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">IMBALANCED TARGET BENCHMARK</p>
              <h2>Precision-Recall Curve</h2>
              <p>Precision vs. Recall under 22.13% empirical default prevalence.</p>
            </div>
            <span className="mini-tag">PR-AUC = {curves.pr.auc.toFixed(4)}</span>
          </div>
          <PrCurveSvg points={curves.pr.points} baseline={curves.pr.baseline_prevalence} />
          <p className="chart-footnote">
            Dataset: UCI Taiwan (DS003) · High precision at low recall enables conservative underwriting; dashed line marks 22.13% prevalence baseline.
          </p>
        </section>
      </div>

      {/* Row 2: Reliability Curve & Interactive Confusion Matrix */}
      <div className="grid-two">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">PROBABILITY FIDELITY</p>
              <h2>Calibration (Reliability) Curve</h2>
              <p>Mean predicted probability vs. fraction of empirical defaults across 10 bins.</p>
            </div>
            <span className="mini-tag">Platt Scaled</span>
          </div>
          <CalibrationSvg bins={curves.calibration.bins} />
          <p className="chart-footnote">
            Dashed line represents perfect calibration. Calibrated XGBoost (teal) closely tracks empirical default rates, significantly improving on raw model scores (blue).
          </p>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">DECISION CUTOFF SENSITIVITY</p>
              <h2>Interactive Confusion Matrix</h2>
              <p>Simulate classification outcomes across decision thresholds.</p>
            </div>
            <span className="mini-tag">Threshold: {selectedThreshold.toFixed(2)}</span>
          </div>

          <div className="threshold-scrubber">
            <label htmlFor="threshold-slider">
              Decision Cutoff: <strong>{selectedThreshold.toFixed(2)}</strong>
            </label>
            <input
              id="threshold-slider"
              type="range"
              min="0.10"
              max="0.90"
              step="0.05"
              value={selectedThreshold}
              onChange={(e) => setSelectedThreshold(Number(e.target.value))}
            />
            <div className="threshold-labels">
              <span>0.10 (Aggressive)</span>
              <span>0.50 (Standard)</span>
              <span>0.90 (Conservative)</span>
            </div>
          </div>

          <div className="confusion-matrix-grid">
            <div className="cm-cell cm-tn">
              <span className="cm-label">True Negative (Repaid)</span>
              <strong className="cm-val">{currentThresholdData.tn.toLocaleString()}</strong>
              <small>Correctly identified non-defaults</small>
            </div>
            <div className="cm-cell cm-fp">
              <span className="cm-label">False Positive (False Alarm)</span>
              <strong className="cm-val">{currentThresholdData.fp.toLocaleString()}</strong>
              <small>Repaid borrowers flagged as default</small>
            </div>
            <div className="cm-cell cm-fn">
              <span className="cm-label">False Negative (Missed Default)</span>
              <strong className="cm-val">{currentThresholdData.fn.toLocaleString()}</strong>
              <small>Defaults admitted as non-default</small>
            </div>
            <div className="cm-cell cm-tp">
              <span className="cm-label">True Positive (Caught Default)</span>
              <strong className="cm-val">{currentThresholdData.tp.toLocaleString()}</strong>
              <small>Correctly identified defaults</small>
            </div>
          </div>

          <div className="cm-rates-bar">
            <span>Accuracy: <strong>{(currentThresholdData.accuracy * 100).toFixed(1)}%</strong></span>
            <span>Precision: <strong>{(currentThresholdData.precision * 100).toFixed(1)}%</strong></span>
            <span>Recall: <strong>{(currentThresholdData.recall * 100).toFixed(1)}%</strong></span>
            <span>F1 Score: <strong>{currentThresholdData.f1_score.toFixed(3)}</strong></span>
          </div>
        </section>
      </div>

      {/* Row 3: Risk Deciles & Actual vs Predicted Outcomes */}
      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">PORTFOLIO STRATIFICATION</p>
            <h2>Actual vs. Predicted Outcomes by Risk Decile</h2>
            <p>Borrowers grouped into 10 risk deciles (Decile 1 = highest risk, Decile 10 = lowest risk).</p>
          </div>
          <span className="mini-tag">Monotonic risk separation</span>
        </div>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>DECILE</th>
                <th>TEST BORROWERS</th>
                <th>OBSERVED DEFAULTS</th>
                <th>EMPIRICAL DEFAULT RATE</th>
                <th>MEAN CALIBRATED PD</th>
                <th>MEAN RAW SCORE</th>
                <th>RISK ALIGNMENT</th>
              </tr>
            </thead>
            <tbody>
              {risk_deciles.map((row) => {
                const diff = Math.abs(row.empirical_default_rate - row.mean_calibrated_pd)
                return (
                  <tr key={row.decile}>
                    <td>
                      <strong>Decile {row.decile}</strong>
                    </td>
                    <td>{row.borrowers.toLocaleString()}</td>
                    <td>{row.defaults.toLocaleString()}</td>
                    <td className="rate-cell">{(row.empirical_default_rate * 100).toFixed(1)}%</td>
                    <td>
                      <strong>{(row.mean_calibrated_pd * 100).toFixed(1)}%</strong>
                    </td>
                    <td style={{ color: '#8aa0a9' }}>{(row.mean_raw_score * 100).toFixed(1)}%</td>
                    <td>
                      <div className="decile-meter">
                        <i
                          className={`decile-fill ${row.empirical_default_rate > 0.4 ? 'high' : row.empirical_default_rate > 0.15 ? 'med' : 'low'}`}
                          style={{ width: `${Math.min(100, row.empirical_default_rate * 120)}%` }}
                        />
                      </div>
                      <small style={{ fontSize: '10px', color: diff < 0.05 ? '#30c4a9' : '#e0a030' }}>
                        Δ { (diff * 100).toFixed(1) }%
                      </small>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <p className="chart-footnote">
          Deciles sorted from highest predicted risk (Decile 1) to lowest (Decile 10). Demonstrates strong rank ordering across the credit book.
        </p>
      </section>

      {/* Row 4: Multi-Model Benchmark Comparison on Same Test Split */}
      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">CONTROLLED EXPERIMENT</p>
            <h2>Model Comparison on Identical Test Split</h2>
            <p>All models evaluated on the exact same 4,500 samples with identical features and ground-truth labels.</p>
          </div>
          <span className="mini-tag">Target & Cohort Held Constant</span>
        </div>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>ALGORITHM / MODEL</th>
                <th>CALIBRATED?</th>
                <th>ROC-AUC</th>
                <th>PR-AUC</th>
                <th>BRIER SCORE</th>
                <th>LOG LOSS</th>
                <th>KS STAT</th>
                <th>GINI</th>
                <th>ACCURACY</th>
                <th>F1 SCORE</th>
              </tr>
            </thead>
            <tbody>
              {model_comparison.map((m) => (
                <tr key={m.model_name}>
                  <td>
                    <strong>{m.model_name}</strong>
                  </td>
                  <td>
                    <span className={`status-pill ${m.is_calibrated ? 'qualified' : 'historical'}`}>
                      {m.is_calibrated ? 'Yes' : 'No'}
                    </span>
                  </td>
                  <td><strong>{m.roc_auc.toFixed(4)}</strong></td>
                  <td>{m.pr_auc.toFixed(4)}</td>
                  <td style={{ color: m.brier_score < 0.14 ? '#30c4a9' : undefined }}>{m.brier_score.toFixed(4)}</td>
                  <td>{m.log_loss.toFixed(4)}</td>
                  <td>{m.ks_statistic.toFixed(3)}</td>
                  <td>{m.gini_coefficient.toFixed(3)}</td>
                  <td>{(m.accuracy * 100).toFixed(1)}%</td>
                  <td>{m.f1_score.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="chart-footnote">
          Controlled benchmark: XGBoost provides superior discrimination (ROC-AUC 0.7807) and ranking; Platt scaling achieves the lowest Brier score (0.1341) without degrading AUC.
        </p>
      </section>

      {/* Row 5: Global Feature Importance */}
      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">GLOBAL FEATURE ARCHITECTURE</p>
            <h2>Fitted Model Feature Importance</h2>
            <p>Top 15 features by gain in the native XGBoost model artifact.</p>
          </div>
          <span className="mini-tag">50 Total Features</span>
        </div>
        <div className="importance-grid-list">
          {global_feature_importance.map((f, i) => {
            const maxImp = global_feature_importance[0]?.importance || 1
            const pct = (f.importance / maxImp) * 100
            return (
              <div key={f.feature} className="importance-item">
                <span className="imp-rank">#{i + 1}</span>
                <span className="imp-name">{f.feature.replaceAll('_', ' ')}</span>
                <div className="imp-track">
                  <div className="imp-bar" style={{ width: `${pct}%` }} />
                </div>
                <strong className="imp-score">{f.importance.toFixed(3)}</strong>
              </div>
            )
          })}
        </div>
        <p className="chart-footnote">
          Features read from <code>models/creditai_model.joblib</code> aligned to <code>models/feature_names.json</code>. Engineered repayment delinquency metrics (PAY_0, MAX_DELINQUENCY, UTIL) dominate credit risk prediction.
        </p>
      </section>
    </>
  )
}

function RocCurveSvg({ points, auc }: { points: CurvePoint[]; auc: number }) {
  const width = 500
  const height = 300
  const pad = { left: 45, right: 20, top: 20, bottom: 40 }

  const path = points
    .map((pt, i) => {
      const x = pad.left + pt.x * (width - pad.left - pad.right)
      const y = pad.top + (1 - pt.y) * (height - pad.top - pad.bottom)
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`
    })
    .join(' ')

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`ROC Curve with AUC ${auc.toFixed(4)}`}>
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1.0].map((tick) => {
          const y = pad.top + (1 - tick) * (height - pad.top - pad.bottom)
          const x = pad.left + tick * (width - pad.left - pad.right)
          return (
            <g key={tick}>
              <line x1={pad.left} x2={width - pad.right} y1={y} y2={y} className="grid-line" />
              <text x={pad.left - 8} y={y + 4} className="axis-label" textAnchor="end">
                {tick.toFixed(2)}
              </text>
              <line x1={x} x2={x} y1={pad.top} y2={height - pad.bottom} className="grid-line" />
              <text x={x} y={height - pad.bottom + 16} className="axis-label" textAnchor="middle">
                {tick.toFixed(2)}
              </text>
            </g>
          )
        })}

        {/* Diagonal random baseline */}
        <line
          x1={pad.left}
          y1={pad.top + (height - pad.top - pad.bottom)}
          x2={width - pad.right}
          y2={pad.top}
          className="baseline-line"
          strokeDasharray="4 4"
        />

        {/* ROC Path */}
        <path d={path} className="line-path" stroke="#30c4a9" fill="none" strokeWidth="2.5" />

        <text x={width - pad.right - 10} y={height - pad.bottom - 15} className="chart-legend" textAnchor="end">
          XGBoost (AUC = {auc.toFixed(4)})
        </text>
      </svg>
      <div className="axis-caption">False Positive Rate (FPR) → True Positive Rate (TPR)</div>
    </div>
  )
}

function PrCurveSvg({ points, baseline }: { points: CurvePoint[]; baseline: number }) {
  const width = 500
  const height = 300
  const pad = { left: 45, right: 20, top: 20, bottom: 40 }

  const path = points
    .map((pt, i) => {
      const x = pad.left + pt.x * (width - pad.left - pad.right)
      const y = pad.top + (1 - pt.y) * (height - pad.top - pad.bottom)
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`
    })
    .join(' ')

  const baselineY = pad.top + (1 - baseline) * (height - pad.top - pad.bottom)

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Precision-Recall Curve">
        {[0, 0.25, 0.5, 0.75, 1.0].map((tick) => {
          const y = pad.top + (1 - tick) * (height - pad.top - pad.bottom)
          const x = pad.left + tick * (width - pad.left - pad.right)
          return (
            <g key={tick}>
              <line x1={pad.left} x2={width - pad.right} y1={y} y2={y} className="grid-line" />
              <text x={pad.left - 8} y={y + 4} className="axis-label" textAnchor="end">
                {tick.toFixed(2)}
              </text>
              <line x1={x} x2={x} y1={pad.top} y2={height - pad.bottom} className="grid-line" />
              <text x={x} y={height - pad.bottom + 16} className="axis-label" textAnchor="middle">
                {tick.toFixed(2)}
              </text>
            </g>
          )
        })}

        {/* Prevalence baseline */}
        <line
          x1={pad.left}
          y1={baselineY}
          x2={width - pad.right}
          y2={baselineY}
          className="baseline-line"
          strokeDasharray="4 4"
        />

        {/* PR Path */}
        <path d={path} className="line-path" stroke="#6e93f6" fill="none" strokeWidth="2.5" />

        <text x={width - pad.right - 10} y={pad.top + 20} className="chart-legend" textAnchor="end">
          Prevalence Baseline = {(baseline * 100).toFixed(1)}%
        </text>
      </svg>
      <div className="axis-caption">Recall (Sensitivity) → Precision (Positive Predictive Value)</div>
    </div>
  )
}

function CalibrationSvg({ bins }: { bins: EvaluationArtifact['curves']['calibration']['bins'] }) {
  const width = 500
  const height = 300
  const pad = { left: 45, right: 20, top: 20, bottom: 40 }

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Calibration reliability curve">
        {[0, 0.2, 0.4, 0.6, 0.8, 1.0].map((tick) => {
          const y = pad.top + (1 - tick) * (height - pad.top - pad.bottom)
          const x = pad.left + tick * (width - pad.left - pad.right)
          return (
            <g key={tick}>
              <line x1={pad.left} x2={width - pad.right} y1={y} y2={y} className="grid-line" />
              <text x={pad.left - 8} y={y + 4} className="axis-label" textAnchor="end">
                {tick.toFixed(1)}
              </text>
              <line x1={x} x2={x} y1={pad.top} y2={height - pad.bottom} className="grid-line" />
              <text x={x} y={height - pad.bottom + 16} className="axis-label" textAnchor="middle">
                {tick.toFixed(1)}
              </text>
            </g>
          )
        })}

        {/* Ideal diagonal line */}
        <line
          x1={pad.left}
          y1={pad.top + (height - pad.top - pad.bottom)}
          x2={width - pad.right}
          y2={pad.top}
          stroke="#415b68"
          strokeWidth="1.5"
          strokeDasharray="4 4"
        />

        {/* Calibrated Points and Line */}
        {bins
          .filter((b) => b.pred_cal !== null && b.true_cal !== null)
          .map((b, i, arr) => {
            const x = pad.left + (b.pred_cal ?? 0) * (width - pad.left - pad.right)
            const y = pad.top + (1 - (b.true_cal ?? 0)) * (height - pad.top - pad.bottom)
            const prev = i > 0 ? arr[i - 1] : null
            const prevX = prev ? pad.left + (prev.pred_cal ?? 0) * (width - pad.left - pad.right) : 0
            const prevY = prev ? pad.top + (1 - (prev.true_cal ?? 0)) * (height - pad.top - pad.bottom) : 0
            return (
              <g key={b.bin}>
                {prev && <line x1={prevX} y1={prevY} x2={x} y2={y} stroke="#30c4a9" strokeWidth="2.5" />}
                <circle cx={x} cy={y} r="4" fill="#30c4a9" stroke="#0e171b" strokeWidth="1.5">
                  <title>
                    Bin {b.bin}: Pred {((b.pred_cal ?? 0) * 100).toFixed(1)}% vs Actual {((b.true_cal ?? 0) * 100).toFixed(1)}%
                  </title>
                </circle>
              </g>
            )
          })}

        {/* Raw Points and Line */}
        {bins.map((b, i, arr) => {
          const x = pad.left + b.pred_raw * (width - pad.left - pad.right)
          const y = pad.top + (1 - b.true_raw) * (height - pad.top - pad.bottom)
          const prev = i > 0 ? arr[i - 1] : null
          const prevX = prev ? pad.left + prev.pred_raw * (width - pad.left - pad.right) : 0
          const prevY = prev ? pad.top + (1 - prev.true_raw) * (height - pad.top - pad.bottom) : 0
          return (
            <g key={`raw-${b.bin}`}>
              {prev && <line x1={prevX} y1={prevY} x2={x} y2={y} stroke="#6e93f6" strokeWidth="1.5" strokeDasharray="2 2" />}
              <circle cx={x} cy={y} r="3" fill="#6e93f6" opacity="0.8">
                <title>Raw Bin {b.bin}: Pred {(b.pred_raw * 100).toFixed(1)}%</title>
              </circle>
            </g>
          )
        })}

        <text x={width - pad.right - 10} y={pad.top + 20} className="chart-legend" textAnchor="end" fill="#30c4a9">
          ● Calibrated (Platt)
        </text>
        <text x={width - pad.right - 10} y={pad.top + 38} className="chart-legend" textAnchor="end" fill="#6e93f6">
          ○ Raw XGBoost
        </text>
      </svg>
      <div className="axis-caption">Mean Predicted Probability (PD) → Fraction of True Defaults (Empirical)</div>
    </div>
  )
}
