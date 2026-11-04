import { GuardianLab } from './ConfidenceGuardian'
// ModelPerformanceLab.tsx – updated for model selection and KNN feature contributions
import { useEffect, useState } from 'react';
import type { EvaluationArtifact } from './api';
import { researchApi } from './api';
import { hasCurveEvidence } from './assessment'

export function ModelPerformanceLab() {
  // ---------- State ----------
  const [evalData, setEvalData] = useState<EvaluationArtifact | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  // New state: which model to display (XGBoost or KNN)
  const [selectedModelId, setSelectedModelId] = useState<string>('uci_taiwan_xgb');

  // ---------- Effect: fetch evaluation ----------
  useEffect(() => {
    let active = true;
    // Load the evaluation JSON for the currently selected model
    researchApi
      .evaluation(selectedModelId)
      .then((evaluation) => {
        if (!active) return;
        setEvalData(evaluation);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : 'Evaluation data could not be loaded.');
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedModelId]); // re‑run when model changes

  // ---------- Loading / Error UI ----------
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
    );
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
    );
  }

  // ---------- Destructure evaluation data ----------
  const {
    metadata,
    summary_metrics,
    curves,
  } = evalData;
  const calibrationPoints = curves.calibration.bins.flatMap((bin) => bin.pred_cal === null || bin.true_cal === null ? [] : [{ x: bin.pred_cal, y: bin.true_cal }])
  const rocEvidenceAvailable = hasCurveEvidence(curves.roc.points)
  const calibrationEvidenceAvailable = hasCurveEvidence(calibrationPoints)

  // ---------- UI: model selector ----------
  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedModelId(e.target.value);
    // Reset UI state for new model
    // setSelectedThreshold(0.5);
    setLoading(true);
    setError(null);
    setEvalData(null);
  };

  return (
    <>
      {/* Header with model selector */}
      <div className="section-title">
        <div>
          <p className="eyebrow">REPRODUCIBLE RESEARCH BENCHMARK</p>
          <h1>Model Performance Lab</h1>
          <p className="section-detail">
            Inspect verified evaluation metrics, curves, and risk deciles computed on the untouched 15% stratified test cohort (N ={' '}
            {metadata.test_sample_count.toLocaleString()}).
          </p>
        </div>
        <span className="source-tag source-historical">Test split evaluation</span>
      </div>

      <GuardianLab />
      {/* Model selector dropdown */}
      <div className="model-selector" style={{ marginBottom: '1rem' }}>
        <label htmlFor="model-select" style={{ marginRight: '0.5rem' }}>
          Choose model:
        </label>
        <select id="model-select" value={selectedModelId} onChange={handleModelChange}>
          <option value="uci_taiwan_xgb">XGBoost (baseline)</option>
          <option value="uci_taiwan_knn">K‑Nearest Neighbors (research)</option>
        </select>
      </div>

      {/* Provenance strip – now uses dynamic metadata.primary_model */}
      <div className="provenance-strip">
        <span>
          <b>Dataset:</b> {metadata.dataset_name} ({metadata.dataset_id})
        </span>
        <span>
          <b>Geography / Time:</b> {metadata.geography} · {metadata.time_coverage}
        </span>
        <span>
          <b>Model / Algorithm:</b> {metadata.primary_model}
        </span>
        <span>
          <b>Evaluation Split:</b> Untouched 15% Test Cohort (N ={' '}
          {metadata.test_sample_count.toLocaleString()})
        </span>
        <span>
          <b>Calibration:</b> {metadata.calibration_status} ({metadata.calibration_method})
        </span>
      </div>

      {/* KPI Cards – same as before, data driven */}
      <div className="kpi-grid">
        <div className="panel kpi-card blue">
          <div className="kpi-top">
            <span>ROC‑AUC (Discrimination)</span>
            <b>⌁</b>
          </div>
          <div className="kpi-value">{summary_metrics.test_roc_auc.toFixed(4)}</div>
          <p>Baseline: 0.5000 (Random) · Reproduced from Phase 1</p>
        </div>
        <div className="panel kpi-card green">
          <div className="kpi-top">
            <span>PR‑AUC (Precision‑Recall)</span>
            <b>↗</b>
          </div>
          <div className="kpi-value">{summary_metrics.test_pr_auc.toFixed(4)}</div>
          <p>Prevalence baseline: {metadata.test_prevalence.toFixed(4)} ({(metadata.test_prevalence * 100).toFixed(1)}%)</p>
        </div>
        <div className="panel kpi-card amber">
          <div className="kpi-top">
            <span>Brier Score (Calibrated)</span>
            <b>◎</b>
          </div>
          <div className="kpi-value">{summary_metrics.brier_score_calibrated.toFixed(4)}</div>
          <p>
            Raw: {summary_metrics.brier_score_raw.toFixed(4)} ({summary_metrics.brier_improvement_pct}% improvement)
          </p>
        </div>
        <div className="panel kpi-card">
          <div className="kpi-top">
            <span>Separation (Gini / KS)</span>
            <b>◈</b>
          </div>
          <div className="kpi-value">
            {summary_metrics.gini_coefficient.toFixed(3)} / {summary_metrics.ks_statistic.toFixed(3)}
          </div>
          <p>Gini coefficient and Kolmogorov‑Smirnov statistic</p>
        </div>
      </div>

      <div className="grid-two performance-evidence-charts">
        <section className="panel">
          <div className="panel-heading"><div><p className="eyebrow">LOCKED TEST EVIDENCE</p><h2 title="ROC-AUC summarizes ranking discrimination on the documented held-out test set.">Receiver operating characteristic (ROC)</h2><p>{metadata.primary_model} · {metadata.geography} · test AUC {curves.roc.auc.toFixed(4)} · n={metadata.test_sample_count.toLocaleString()}</p></div></div>
          {rocEvidenceAvailable ? <><EvidenceCurve title="ROC curve on held-out test data" points={curves.roc.points} xLabel="False-positive rate" yLabel="True-positive rate" baseline /><p className="chart-footnote">The diagonal is the random-ranking reference. This curve uses the saved genuine test scores; it does not establish Indian borrower performance.</p></> : <div className="callout-soft"><strong>Evidence required</strong><span>Saved held-out false-positive and true-positive coordinates are missing; aggregate AUC is not used to invent a curve.</span></div>}
        </section>
        <section className="panel">
          <div className="panel-heading"><div><p className="eyebrow">LOCKED TEST EVIDENCE</p><h2 title="Calibration compares average predicted probability with observed event frequency.">Calibration curve</h2><p>{curves.calibration.bins.filter((bin) => bin.pred_cal !== null && bin.true_cal !== null).length} saved bins · {metadata.calibration_method}</p></div></div>
          {calibrationEvidenceAvailable ? <><EvidenceCurve title="Calibration curve on held-out test data" points={calibrationPoints} xLabel="Mean predicted probability" yLabel="Observed default rate" baseline /><p className="chart-footnote">Points use the saved calibrated predictions and observed test labels. The reference line indicates perfect agreement.</p></> : <div className="callout-soft"><strong>Evidence required</strong><span>At least two saved held-out pairs of mean predicted probability and observed event rate are required to render this plot.</span></div>}
        </section>
      </div>

      <section className="panel threshold-evidence">
        <div className="panel-heading"><div><p className="eyebrow">THRESHOLD METHOD</p><h2 title="Precision, recall and F1 depend on the chosen probability cutoff.">Research threshold analysis</h2><p>Thresholds must be selected using validation evidence, then frozen before test evaluation.</p></div><span className="status-badge readiness-evidence-gap">Evidence required</span></div>
        <div className="callout-soft"><strong>Not plotted from the current artifact</strong><span>The saved threshold sweep in the Taiwan evaluation artifact was computed from the locked test labels (`y_test`) by `scripts/generate_evaluation_artifacts.py`. Reusing those results to compare cutoffs would tune on the test set. A validation-split label/probability export is not present, so this view does not display a threshold curve.</span></div>
      </section>

      <section className="panel">
        <div className="panel-heading"><div><p className="eyebrow">INTERPRETING THE METRICS</p><h2>Plain-English guide</h2></div></div>
        <dl className="metric-glossary">
          <div><dt>ROC-AUC</dt><dd>How often a default case ranks above a non-default case across cutoffs.</dd></div>
          <div><dt>PR-AUC</dt><dd>Precision and recall summarized together; compare it with the dataset’s default prevalence.</dd></div>
          <div><dt>Brier score</dt><dd>Average squared gap between predicted probabilities and observed outcomes; lower is better.</dd></div>
          <div><dt>Calibration</dt><dd>Whether groups assigned similar probabilities experience similar observed outcome rates.</dd></div>
          <div><dt>Research threshold</dt><dd>A cutoff used to label classes in this experiment; it is not a production lending policy.</dd></div>
        </dl>
      </section>

      {/* ----- Feature Contribution Panel (KNN only) ----- */}
      {/* Disabled: feature_contributions not yet populated in evaluation artifacts.
          KNN local neighbor explanation requires per-instance prediction context,
          which is not included in the aggregate evaluation JSON. */}
    </>
  );
}

function EvidenceCurve({ title, points, xLabel, yLabel, baseline }: { title: string; points: { x: number; y: number }[]; xLabel: string; yLabel: string; baseline: boolean }) {
  const width = 520
  const height = 300
  const pad = { left: 52, right: 20, top: 18, bottom: 44 }
  const x = (value: number) => pad.left + Math.max(0, Math.min(1, value)) * (width - pad.left - pad.right)
  const y = (value: number) => height - pad.bottom - Math.max(0, Math.min(1, value)) * (height - pad.top - pad.bottom)
  const path = points.map((point, index) => `${index ? 'L' : 'M'} ${x(point.x)} ${y(point.y)}`).join(' ')
  return <div className="chart-wrap"><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
    {[0, .25, .5, .75, 1].map((tick) => <g key={tick}><line x1={pad.left} x2={width - pad.right} y1={y(tick)} y2={y(tick)} className="grid-line"/><line x1={x(tick)} x2={x(tick)} y1={pad.top} y2={height - pad.bottom} className="grid-line"/><text x={pad.left - 9} y={y(tick) + 4} className="axis-label" textAnchor="end">{tick.toFixed(2)}</text><text x={x(tick)} y={height - pad.bottom + 20} className="axis-label" textAnchor="middle">{tick.toFixed(2)}</text></g>)}
    {baseline && <line x1={x(0)} y1={y(0)} x2={x(1)} y2={y(1)} stroke="#98a9aa" strokeDasharray="5 5" strokeWidth="2"/>}
    {points.length > 1 && <path d={path} fill="none" stroke="#128b78" strokeWidth="3"/>}
    <text x={width / 2} y={height - 4} className="axis-label" textAnchor="middle">{xLabel}</text>
    <text x="14" y={height / 2} className="axis-label" textAnchor="middle" transform={`rotate(-90 14 ${height / 2})`}>{yLabel}</text>
  </svg></div>
}
