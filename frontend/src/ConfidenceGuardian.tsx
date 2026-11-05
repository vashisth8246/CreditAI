import { useEffect, useState } from 'react'
import { researchApi } from './api'
import type { GuardianAssessment, GuardianEvaluation } from './api'
import './confidenceGuardian.css'

const labels: Record<GuardianAssessment['status'], string> = {
  review_eligible: 'Eligible for research review',
  manual_review_recommended: 'Manual review recommended',
  input_correction_required: 'Input correction required',
  reliability_not_evaluated: 'Reliability not evaluated',
  model_unavailable: 'Model unavailable',
}

export function ConfidenceGuardian({ assessment }: { assessment: GuardianAssessment }) {
  const findings = [...assessment.findings, ...assessment.distribution_findings]
  return <section className="guardian-panel" aria-label="Confidence Guardian">
    <p className="eyebrow">RESEARCH EVIDENCE · {assessment.method}</p>
    <h3 id="guardian-evidence-heading" tabIndex={-1}>Confidence Guardian — Prediction Evidence Check</h3>
    <p className="guardian-status">{labels[assessment.status]}</p>
    <div className="guardian-facts">
      <div><strong>Input completeness</strong><span>{assessment.valid_fields} / {assessment.required_fields} supported fields</span></div>
      <div><strong>Training comparison</strong><span>{assessment.distribution_evaluated ? 'Evaluated against the Taiwan training partition' : 'Not evaluated for this submission'}</span></div>
    </div>
    {assessment.reasons.map(reason => <p key={reason}>{reason}</p>)}
    {findings.length > 0 && <ul className="guardian-findings">{findings.map(item => <li key={item.code + item.field}>
      <strong>{item.field} · {item.severity === 'information' ? 'Valid observation' : item.severity}</strong>
      <p>{item.explanation} {item.evidence}</p><small>Next step: {item.action}</small>
    </li>)}</ul>}
    {assessment.reference && <small>{assessment.reference.dataset} · {assessment.reference.train_count.toLocaleString()} training records · <a href="/v1/research/reliability-evaluation">See held-out evidence</a></small>}
    <p className="guardian-limit">{assessment.limitations ?? assessment.model_provenance} No lending recommendation is produced.</p>
  </section>
}

const percentage = (n: number | null) => n === null ? 'Unavailable' : (n * 100).toFixed(2) + '%'
const metric = (n: number | null) => n === null ? 'Unavailable' : n.toFixed(4)
export function GuardianLab() {
  const [artifact, setArtifact] = useState<GuardianEvaluation | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    let active = true
    void researchApi.guardianEvaluation().then(value => { if (active) setArtifact(value) }).catch(() => { if (active) setFailed(true) })
    return () => { active = false }
  }, [])
  const rows = artifact?.evaluation ?? []
  const baseline = rows[0]
  const gated = rows.filter(row => row.name === 'Quality + distribution')
  const selected = gated.find(row => row.target_coverage === .90)
  const plotted = gated.flatMap(row => row.error_rate === null ? [] : [{ coverage: row.coverage, error: row.error_rate }])
    .sort((a, b) => a.coverage - b.coverage)
  const xMin = Math.min(.65, ...plotted.map(row => row.coverage))
  const yMax = Math.max(.3, baseline?.error_rate ?? 0, ...plotted.map(row => row.error))
  const x = (coverage: number) => 50 + (coverage - xMin) / (1 - xMin) * 370
  const y = (error: number) => 150 - error / yMax * 132
  return <section className="panel guardian-lab" aria-label="Guardian evaluation">
    <p className="eyebrow">HELD-OUT RESEARCH · SELECTIVE PREDICTION</p>
    <h2>Confidence Guardian Evaluation</h2>
    {failed ? <p>Evaluation evidence could not be loaded.</p> : !artifact ? <p role="status">Loading evaluation evidence…</p> : !baseline ? <p>{artifact.reason ?? 'Not evaluated.'}</p> : <>
      <p>UCI Taiwan, 2005 · {artifact.split?.train.toLocaleString()} training / {artifact.split?.validation.toLocaleString()} validation / {artifact.split?.test.toLocaleString()} test records. Population thresholds selected on validation. Classification error uses the existing 0.50 threshold.</p>
      {selected && <p><strong>Selected operating point:</strong> {selected.retained.toLocaleString()} retained, {selected.abstained.toLocaleString()} abstained. Retained error {percentage(selected.error_rate)}; all-row error {percentage(baseline.error_rate)}.
        {selected.error_delta_bootstrap_95 && <> Estimated 95% bootstrap interval for the error difference: {selected.error_delta_bootstrap_95.map(value => (value * 100).toFixed(2)).join(' to ')} percentage points.</>}
      </p>}
      <figure className="guardian-chart">
        <figcaption>Held-out coverage versus retained classification error</figcaption>
        <svg viewBox="0 0 440 185" role="img" aria-label="Coverage versus error for the distribution gate, compared with the ungated baseline. Exact values appear below.">
          <path d="M50 15 V150 H420" fill="none" stroke="#69847a"/>
          {[0, 1, 2, 3].map(i => yMax * i / 3).map(n => <g key={n}><text x="2" y={y(n)+4} fontSize="11">{percentage(n)}</text><path d={`M50 ${y(n)} H420`} stroke="#dbe9e1"/></g>)}
          {[.7,.8,.9,1].map(n => <text key={n} x={x(n)} y="170" fontSize="11" textAnchor="middle">{Math.round(n*100)}%</text>)}
          {baseline.error_rate !== null && <path d={`M50 ${y(baseline.error_rate)} H420`} stroke="#986049" strokeDasharray="5 4"/>}
          {plotted.length > 1 && <polyline points={plotted.map(row => `${x(row.coverage)},${y(row.error)}`).join(' ')} fill="none" stroke="#14684a" strokeWidth="2"/>}
          {plotted.map((row, index) => <circle key={index} cx={x(row.coverage)} cy={y(row.error)} r="4" fill="#14684a"><title>{percentage(row.coverage)} coverage · {percentage(row.error)} retained error</title></circle>)}
        </svg>
        <small>Horizontal: actual test coverage. Vertical: classification error among retained cases. Dashed line: all-row error.</small>
      </figure>
      <div className="guardian-table" tabIndex={0} role="region" aria-label="Scrollable evaluation results"><table>
        <caption>Baseline, quality checks and validation threshold sensitivity</caption>
        <thead><tr>{['Gate','Target','Cutoff','Coverage','Retained','Abstained','Error','ROC-AUC','Avg. precision','Brier','Log loss'].map(label => <th key={label} scope="col">{label}</th>)}</tr></thead>
        <tbody>{rows.map(row => <tr key={row.name + row.target_coverage}>
          <th scope="row">{row.name}</th><td>{percentage(row.target_coverage ?? null)}</td><td>{metric(row.cutoff ?? null)}</td><td>{percentage(row.coverage)}</td><td>{row.retained}</td><td>{row.abstained}</td>
          <td>{percentage(row.error_rate)}</td><td>{metric(row.roc_auc)}</td><td>{metric(row.average_precision)}</td><td>{metric(row.brier)}</td><td>{metric(row.log_loss)}</td>
        </tr>)}</tbody>
      </table></div>
      <details><summary>Input evidence counts and interpretation limits</summary>
        <ul>{Object.entries(artifact.quality_findings ?? {}).map(([code,count]) => <li key={code}>{code.replaceAll('_',' ')}: {count} test records</li>)}</ul>
        <p>Each gated row describes a different retained subset. A lower conditional error does not mean a better prediction for the same borrower, or validate Indian lending. Calibration bins, subgroup retention counts, split fingerprints and bootstrap intervals are available in the evaluation artifact.</p>
        <a href="/v1/research/reliability-evaluation">Open evaluation evidence (JSON)</a>
      </details>
    </>}
  </section>
}
