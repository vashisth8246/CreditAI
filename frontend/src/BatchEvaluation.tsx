import { useMemo, useRef, useState } from 'react'
import { researchApi } from './api'
import type { BatchPredictionResult } from './batch'
import { buildResultCsv, missingRequiredFields, parseCsv, sanitizeCell, summarizeBatch } from './batch'

const MAX_ROWS = 5000

export function BatchEvaluation() {
  const fileInput = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string[][] | null>(null)
  const [header, setHeader] = useState<string[]>([])
  const [parseError, setParseError] = useState<string | null>(null)
  const [runState, setRunState] = useState<'idle' | 'running' | 'done' | 'error'>('idle')
  const [runError, setRunError] = useState<string | null>(null)
  const [result, setResult] = useState<BatchPredictionResult | null>(null)

  const missing = useMemo(() => (header.length ? missingRequiredFields(header) : []), [header])
  const summary = useMemo(() => (result ? summarizeBatch(result) : null), [result])

  function reset() {
    setFile(null); setPreview(null); setHeader([]); setParseError(null)
    setRunState('idle'); setRunError(null); setResult(null)
    if (fileInput.current) fileInput.current.value = ''
  }

  async function onFile(selected: File | null) {
    reset()
    if (!selected) return
    setFile(selected)
    const name = selected.name.toLowerCase()
    if (!name.endsWith('.csv')) {
      setParseError('Preview supports .csv files. The server also accepts .xlsx, which cannot be previewed in the browser.')
      return
    }
    try {
      const text = await selected.text()
      const parsed = parseCsv(text)
      setHeader(parsed.header)
      setPreview(parsed.rows.slice(0, 15))
    } catch (err) {
      setParseError(err instanceof Error ? err.message : 'Could not read the selected file.')
    }
  }

  async function runBatch() {
    if (!file) return
    setRunState('running'); setRunError(null); setResult(null)
    try {
      const response = await researchApi.batchPredict(file)
      setResult(response); setRunState('done')
    } catch (err) {
      setRunError(err instanceof Error ? err.message : 'Batch prediction failed.')
      setRunState('error')
    }
  }

  function exportCsv() {
    if (!result) return
    const blob = new Blob([buildResultCsv(result)], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'creditai_batch_results.csv'
    link.click()
    URL.revokeObjectURL(url)
  }

  return <>
    <div className="section-title">
      <div>
        <p className="eyebrow">RESEARCH BATCH INFERENCE</p>
        <h1>Batch evaluation</h1>
        <p className="section-detail">Upload a CSV or XLSX containing the 23 raw Taiwan model fields. Rows are validated and scored individually against the UCI Taiwan research benchmark; an optional <code>borrower_reference</code> column is echoed back but never used as a model feature.</p>
      </div>
      <span className="source-tag source-historical">Historical benchmark</span>
    </div>

    <div className="research-banner">
      <span className="source-tag source-historical">RESEARCH ONLY</span>
      <span>Taiwan credit-card benchmark (DS003) · not validated for Indian underwriting. Exports are sanitised against spreadsheet formula injection.</span>
    </div>

    <div className="grid-two">
      <section className="panel">
        <div className="panel-heading"><div><p className="eyebrow">STEP 1 · UPLOAD</p><h2>Select a file</h2><p>Maximum 5,000 rows. CSV preview is client-side; the server enforces the same limits.</p></div></div>
        <input ref={fileInput} type="file" accept=".csv,.xlsx" aria-label="Batch input file"
          onChange={(event) => void onFile(event.target.files?.[0] ?? null)} />
        {file && <div className="profile-facts"><Fact label="File" value={file.name} /><Fact label="Size" value={`${(file.size / 1024).toFixed(1)} KB`} /><Fact label="Rows detected" value={preview ? String(preview.length) + '+' : 'not previewed'} /></div>}
        {parseError && <div className="inline-error" role="alert">{parseError}</div>}
        {missing.length > 0 && <div className="inline-error" role="alert">Missing required columns: {missing.join(', ')}</div>}
        <div className="hero-actions" style={{ marginTop: '1rem' }}>
          <button className="button-primary" disabled={!file || runState === 'running'} onClick={() => void runBatch()}>
            {runState === 'running' ? 'Running…' : 'Run batch prediction →'}
          </button>
          <button className="button-quiet" onClick={reset}>Clear</button>
        </div>
        {runError && <div className="inline-error" role="alert">{runError}</div>}
      </section>

      <section className="panel">
        <div className="panel-heading"><div><p className="eyebrow">STEP 2 · PREVIEW</p><h2>Header check</h2><p>{header.length} columns detected. Cell text is escaped before rendering.</p></div></div>
        {header.length === 0 ? <div className="empty-state"><p>Upload a CSV to preview its columns.</p></div>
          : <div className="table-scroll"><table className="data-table">
            <thead><tr>{header.map((h, i) => <th key={`${h}-${i}`}>{sanitizeCell(h)}</th>)}</tr></thead>
            <tbody>{(preview ?? []).map((row, ri) => <tr key={ri}>{header.map((_, ci) => <td key={ci}>{sanitizeCell(row[ci] ?? '')}</td>)}</tr>)}</tbody>
          </table>{preview && preview.length >= 15 && <p className="chart-footnote">Showing first 15 rows of {preview.length}+.</p>}</div>}
      </section>
    </div>

    {summary && (
      <section className="panel">
        <div className="panel-heading"><div><p className="eyebrow">STEP 3 · RESULTS</p><h2>Batch outcome</h2><p>Model <strong>{result?.model_id}</strong> · row-level validation failures are reported, never silently dropped.</p></div><button className="button-secondary" onClick={exportCsv}>Export results CSV</button></div>
        <div className="kpi-grid small-kpis">
          <Kpi label="Rows scored" value={String(summary.succeeded)} detail={`of ${summary.total} uploaded`} />
          <Kpi label="Row errors" value={String(summary.failed)} detail="Validation failures, reported per row" accent="red" />
          <Kpi label="Mean PD" value={summary.meanProbability === null ? '–' : `${(summary.meanProbability * 100).toFixed(1)}%`} detail="Successful rows only" accent="blue" />
          <Kpi label="Tier split" value={`${summary.lowRisk}/${summary.mediumRisk}/${summary.highRisk}`} detail="Low / Medium / High at threshold 0.5" accent="green" />
        </div>
        <div className="table-scroll"><table className="data-table">
          <thead><tr><th>ROW</th><th>REFERENCE</th><th>STATUS</th><th>PD</th><th>RISK</th><th>DETAIL</th></tr></thead>
          <tbody>{result?.results.map((r) => <tr key={r.row_index}>
            <td>{r.row_index}</td>
            <td>{r.borrower_reference === null || r.borrower_reference === undefined ? '–' : sanitizeCell(String(r.borrower_reference))}</td>
            <td>{r.status === 'success' ? 'Scored' : 'Error'}</td>
            <td>{r.prediction ? `${(r.prediction.probability * 100).toFixed(2)}%` : '–'}</td>
            <td>{r.prediction ? r.prediction.risk_category : '–'}</td>
            <td>{r.prediction ? (r.prediction.calibrated ? 'Calibrated (Platt)' : 'Uncalibrated') : sanitizeCell(r.error_message ?? '')}</td>
          </tr>)}</tbody>
        </table></div>
      </section>
    )}
    <p className="chart-footnote">Maximum rows enforced server-side: {MAX_ROWS.toLocaleString()}. Uploaded borrower rows are scored in-memory and are not written to application logs.</p>
  </>
}

function Kpi({ label, value, detail, accent = '' }: { label: string; value: string; detail: string; accent?: string }) {
  return <section className={`panel kpi-card ${accent}`}><div className="kpi-top"><span>{label}</span></div><div className="kpi-value">{value}</div><p>{detail}</p></section>
}

function Fact({ label, value }: { label: string; value: string }) {
  return <div className="fact"><span className="fact-label">{label}</span><strong>{value}</strong></div>
}
