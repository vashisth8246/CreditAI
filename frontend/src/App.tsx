import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { DataSource, InventoryItem } from './analytics'
import { availabilityState, dataSourceLabel, displayFeatureName, displayUserText, filterInventory, formatMetric, formatPercent, safeProbability } from './analytics'
import { DatasetInventoryTable } from './DatasetInventoryTable'
import { datasetReadiness, formatIndianRupees, SIMULATED_SCORING_STEPS } from './assessment'
import { PredictionWorkspace } from './PredictionWorkspace'
import { ModelPerformanceLab } from './ModelPerformanceLab'
import { BatchEvaluation } from './BatchEvaluation'
import { researchApi } from './api'
import { useCountUpValue } from './motion'
import './App.css'

type Page = 'overview' | 'prediction' | 'batch' | 'discovery' | 'portfolio' | 'lab' | 'performance' | 'explorer' | 'explainability' | 'monitoring' | 'architecture'
type Segment = 'vintage' | 'grade' | 'purpose'
type MetricRow = Record<string, string | number | null>
type SegmentRow = { segment: string; records: number; closed: number; defaults: number; observed_closed_default_rate: number | null }
type Summary = {
  generated_at: string
  dataset: { id: string; name: string; source_file: string; records: number; source_columns: number; origination_period: string; raw_default_share: number; closed_records: number; closed_defaults: number; closed_default_rate: number; unresolved_or_censored: number; status_distribution: { status: string; count: number }[] }
  evaluation: { id: string; evaluation_date: string; target: string; split_design: string; calibration: string; curve_coordinates_available: boolean; saved_prediction_rows_available: boolean; metrics: MetricRow[]; all_split_metrics: MetricRow[]; splits: MetricRow[] }
  portfolio: { vintage: SegmentRow[]; grade: SegmentRow[]; purpose: SegmentRow[]; term: SegmentRow[]; loan_amount_histogram: { bin: string; count: number }[]; numeric_correlation_fields: string[]; numeric_correlation_complete_rows: number; numeric_correlation: { feature: string; values: Record<string, number> }[] }
  limitations: string[]
}
type Feature = { dataset_id: string; feature: string; missing_percentage_all_source_rows: string; meaning: string; phase_2_3_decision: string }
type DashboardSnapshot = { summary: Summary; inventory: InventoryItem[]; features: Feature[]; source: string; retrieved_at: string; source_snapshot_date: string }
type BuildInfo = { commit_sha: string | null; short_commit: string | null; scoring_status: string }

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const nav: { id: Page; title: string; icon: string; section?: string }[] = [
  { id: 'overview', title: 'Executive overview', icon: '◫', section: 'WORKSPACE' },
  { id: 'prediction', title: 'Borrower prediction', icon: '◎' },
  { id: 'batch', title: 'Batch evaluation', icon: '▤' },
  { id: 'discovery', title: 'Data discovery', icon: '◈' },
  { id: 'portfolio', title: 'Portfolio intelligence', icon: '▤' },
  { id: 'lab', title: 'Model lab', icon: '⌁', section: 'RESEARCH' },
  { id: 'performance', title: 'Model performance lab', icon: '▥' },
  { id: 'explorer', title: 'Risk explorer', icon: '◎' },
  { id: 'explainability', title: 'Explainability', icon: '✳' },
  { id: 'monitoring', title: 'Monitoring', icon: '⌁' },
  { id: 'architecture', title: 'Architecture & audit', icon: '⌘', section: 'SYSTEM' },
]

function metricNumber(row: MetricRow | undefined, key: string): number | null {
  if (!row || row[key] === null || row[key] === undefined || row[key] === '') return null
  const n = Number(row[key])
  return Number.isFinite(n) ? n : null
}

function compact(n: number): string {
  return new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 2 }).format(n)
}

function SourceTag({ source }: { source: DataSource }) {
  return <span className={`source-tag source-${source}`}>{dataSourceLabel(source)}</span>
}

function SectionTitle({ eyebrow, title, detail, source = 'historical' }: { eyebrow: string; title: string; detail: string; source?: DataSource }) {
  return <div className="section-title exhibition-page-heading"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="section-detail">{detail}</p></div><SourceTag source={source} /></div>
}

function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}>{children}</section>
}

function EmptyState({ title, message, icon = '◌' }: { title: string; message: string; icon?: string }) {
  return <div className="empty-state"><span className="empty-icon" aria-hidden="true">{icon}</span><h3>{title}</h3><p>{message}</p></div>
}

function EvidenceGapCard({ icon, title, message, required }: { icon: string; title: string; message: string; required: string }) {
  return <Card className="evidence-gap-card">
    <div className="evidence-gap-top"><span className="evidence-gap-icon" aria-hidden="true">{icon}</span><span className="evidence-gap-status"><i /> Not saved</span></div>
    <h3>{title}</h3>
    <p>{message}</p>
    <div className="evidence-gap-needed"><span>Evidence needed</span><strong>{required}</strong></div>
  </Card>
}

function LineChart({ data }: { data: SegmentRow[] }) {
  const width = 760
  const height = 248
  const pad = { left: 46, right: 18, top: 18, bottom: 36 }
  const values = data.filter((item) => item.observed_closed_default_rate !== null)
  const points = values.map((item, index) => {
    const x = pad.left + (values.length < 2 ? 0 : index * (width - pad.left - pad.right) / (values.length - 1))
    const y = pad.top + (1 - (item.observed_closed_default_rate ?? 0) / 0.4) * (height - pad.top - pad.bottom)
    return { x, y, item }
  })
  const path = points.map((point, i) => `${i ? 'L' : 'M'} ${point.x} ${point.y}`).join(' ')
  return <div className="chart-wrap"><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Observed closed-loan default rate by origination year">
    {[0, 10, 20, 30, 40].map((tick) => { const y = pad.top + (1 - tick / 40) * (height - pad.top - pad.bottom); return <g key={tick}><line x1={pad.left} x2={width - pad.right} y1={y} y2={y} className="grid-line"/><text x={pad.left - 9} y={y + 4} className="axis-label" textAnchor="end">{tick}%</text></g> })}
    <path d={path} className="line-path" />
    {points.map(({ x, y, item }) => <g key={item.segment}><circle cx={x} cy={y} r="4.5" className="line-point" tabIndex={0}><title>{`${item.segment}: ${formatPercent(item.observed_closed_default_rate)} · ${item.closed.toLocaleString()} closed loans`}</title></circle><text x={x} y={height - 12} className="axis-label" textAnchor="middle">{item.segment}</text></g>)}
  </svg><div className="chart-footnote">Terminal outcomes by origination vintage · closed loans only · denominator shown on hover</div></div>
}

function HorizontalBars({ data, valueKey, valueLabel, color = 'teal', maxValue }: { data: { label: string; value: number; sub?: string }[]; valueKey?: string; valueLabel?: string; color?: string; maxValue?: number }) {
  const max = maxValue ?? Math.max(...data.map((row) => row.value), 1)
  return <div className="horizontal-bars" aria-label={valueLabel ?? 'Bar chart'}>{data.map((row) => <div className="hbar-row" key={row.label}><div className="hbar-head"><span>{row.label}</span><strong>{valueKey === 'percent' ? `${row.value.toFixed(1)}%` : row.value.toLocaleString()}</strong></div><div className="hbar-track"><div className={`hbar-fill ${color}`} style={{ width: `${Math.min(100, Math.max(1, row.value / max * 100))}%` }} /></div>{row.sub && <small>{row.sub}</small>}</div>)}</div>
}

function TrendBars({ data }: { data: { bin: string; count: number }[] }) {
  const max = Math.max(...data.map((x) => x.count), 1)
  return <div className="histogram" role="img" aria-label="Loan amount distribution in US dollars">{data.map((item) => <div className="hist-column" key={item.bin} tabIndex={0} aria-label={`${item.bin}: ${item.count.toLocaleString()} records`}><div className="hist-count">{compact(item.count)}</div><div className="hist-bar" style={{ height: `${Math.max(4, item.count / max * 100)}%` }}><span className="chart-tooltip">{`${item.bin}: ${item.count.toLocaleString()} loans`}</span></div><span className="hist-label">{item.bin}</span></div>)}</div>
}

function CorrelationMap({ summary }: { summary: Summary }) {
  const fields = summary.portfolio.numeric_correlation_fields
  const matrix = summary.portfolio.numeric_correlation
  if (!matrix.length) return <EmptyState title="Correlation summary unavailable" message="The source summary did not contain enough complete numeric observations." />
  return <div className="corr-scroll"><table className="corr-table"><thead><tr><th></th>{fields.map((name) => <th key={name}>{displayFeatureName(name)}</th>)}</tr></thead><tbody>{matrix.map((row) => <tr key={row.feature}><th>{displayFeatureName(row.feature)}</th>{fields.map((name) => { const value = row.values[name] ?? 0; const opacity = Math.min(0.8, Math.abs(value) * 0.8); return <td key={name} style={{ backgroundColor: value >= 0 ? `rgba(48, 196, 169, ${opacity})` : `rgba(110, 147, 246, ${opacity})` }} title={`${displayFeatureName(row.feature)} × ${displayFeatureName(name)}: ${value.toFixed(2)}`}>{value.toFixed(2)}</td> })}</tr>)}</tbody></table><p className="chart-footnote">Pearson correlation, complete observations only (n={summary.portfolio.numeric_correlation_complete_rows.toLocaleString()}); association is not causation.</p></div>
}

function App() {
  const [page, setPage] = useState<Page>('overview')
  const [summary, setSummary] = useState<Summary | null>(null)
  const [inventory, setInventory] = useState<InventoryItem[] | null>(null)
  const [features, setFeatures] = useState<Feature[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [datasetQuery, setDatasetQuery] = useState('')
  const [qualificationFilter, setQualificationFilter] = useState('all')
  const [sourceFilter, setSourceFilter] = useState('all')
  const [selectedDataset, setSelectedDataset] = useState('DS001')
  const [segment, setSegment] = useState<Segment>('vintage')
  const [segmentQuery, setSegmentQuery] = useState('')
  const [selectedModel, setSelectedModel] = useState('HistGradientBoosting')
  const [selectedSplit, setSelectedSplit] = useState('Test')
  const [apiState, setApiState] = useState<'idle' | 'checking' | 'online' | 'offline'>('idle')
  const [scoreState, setScoreState] = useState<'idle' | 'loading' | 'done' | 'error'>('idle')
  const [scorePayload, setScorePayload] = useState<Record<string, unknown> | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const [retrievedAt, setRetrievedAt] = useState<string | null>(null)
  const [buildInfo, setBuildInfo] = useState<BuildInfo | null>(null)
  const [showDatasetDetail, setShowDatasetDetail] = useState(false)

  useEffect(() => {
    let active = true
    void checkHealth()
    const controller = new AbortController()
    researchApi.dashboardSnapshot<DashboardSnapshot>(controller.signal).then((snapshot) => {
      if (!active) return
      setSummary(snapshot.summary); setInventory(snapshot.inventory); setFeatures(snapshot.features); setRetrievedAt(snapshot.retrieved_at); setLoading(false)
    }).catch((error: unknown) => { if (!active || (error instanceof Error && error.name === 'AbortError')) return; setLoadError(error instanceof Error ? error.message : 'Research artifacts could not be loaded.'); setLoading(false) })
    return () => { active = false; controller.abort() }
  }, [retryCount])

  useEffect(() => {
    let active = true
    researchApi.buildInfo().then((info) => {
      if (active) setBuildInfo(info)
    }).catch(() => {
      if (active) setBuildInfo({ commit_sha: null, short_commit: null, scoring_status: 'not_validated' })
    })
    return () => { active = false }
  }, [])

  function retryLoad() {
    if (loading) return
    setLoading(true)
    setLoadError(null)
    setRetryCount((prev) => prev + 1)
  }

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.altKey || event.ctrlKey || event.metaKey) return
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLSelectElement) return
      
      const keyMap: Record<string, Page> = {
        '1': 'overview',
        '2': 'prediction',
        '3': 'batch',
        '4': 'discovery',
        '5': 'portfolio',
        '6': 'lab',
        '7': 'performance',
        '8': 'explorer',
        '9': 'explainability',
      }
      if (keyMap[event.key]) {
        go(keyMap[event.key])
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const viewState = availabilityState(loading, loadError, summary ? [summary] : null)
  const filteredInventory = useMemo(() => filterInventory(inventory ?? [], datasetQuery, qualificationFilter, sourceFilter), [inventory, datasetQuery, qualificationFilter, sourceFilter])
  const chosenDataset = inventory?.find((item) => item.dataset_id === selectedDataset)
  const scoreMessage = scorePayload ? safeProbability(String(scorePayload.score_status ?? ''), typeof scorePayload.default_probability === 'number' ? scorePayload.default_probability : null) : 'No probability produced'
  const currentEval = summary?.evaluation.all_split_metrics.find((row) => row.model_name === selectedModel && row.split_name === selectedSplit)
  const selectedSegments = summary?.portfolio[segment] ?? []
  const searchedSegments = selectedSegments.filter((item) => item.segment.toLowerCase().includes(segmentQuery.toLowerCase()))
  const bestTest = summary?.evaluation.metrics.find((row) => row.model_name === 'HistGradientBoosting')
  const researchCount = inventory?.filter((item) => item.qualification_decision === 'QUALIFIED_FOR_RESEARCH').length ?? 0

  async function checkHealth() {
    setApiState('checking')
    try { const response = await fetch(`${API_BASE}/health`); setApiState(response.ok ? 'online' : 'offline') } catch { setApiState('offline') }
  }

  async function sendContractExample() {
    setScoreState('loading'); setScorePayload(null)
    const body = { schema_version: '1.0', observation_start: '2025-01-01', prediction_date: '2025-02-01', request_id: `phase61-demo-${Date.now()}`, transactions: [{ transaction_id: 'synthetic-credit-1', date: '2025-01-15', transaction_type: 'credit', amount: 45000, category: 'salary' }, { transaction_id: 'synthetic-debit-1', date: '2025-01-20', transaction_type: 'debit', amount: 1200, category: 'groceries' }] }
    try {
      const response = await fetch(`${API_BASE}/v1/score`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      if (!response.ok) throw new Error('API request failed')
      setScorePayload(await response.json()); setScoreState('done')
    } catch { setScoreState('error') }
  }

  function go(target: Page) { setPage(target); window.scrollTo({ top: 0, behavior: 'smooth' }) }

  return <div className="shell exhibition-shell">
    <aside className="sidebar exhibition-sidebar">
      <div className="brand"><div className="brand-mark"><span>c</span><i /></div><div><strong>creditai</strong><small>RISK WORKBENCH</small></div></div>
      <div className="workspace-switch"><span className="workspace-dot" /><div><strong>Research workspace</strong><small>Phase 9 · Research</small></div><span className="chevron">⌄</span></div>
      <nav className="side-nav" aria-label="Main navigation">{nav.map((item, index) => <div key={item.id}>{item.section && <div className="nav-section">{item.section}</div>}<button className={`nav-item ${page === item.id ? 'active' : ''}`} onClick={() => go(item.id)} aria-current={page === item.id ? 'page' : undefined} title={index < 9 ? `Press ${index + 1} to navigate` : item.title}><span className="nav-symbol" aria-hidden="true">{item.icon}</span><span>{item.title}</span>{item.id === 'explorer' && <span className="nav-pill">LAB</span>}{index < 9 && <span className="nav-shortcut" aria-hidden="true">{index + 1}</span>}</button></div>)}</nav>
      <div className="sidebar-foot"><div className="foot-status"><span className="pulse-dot" /><span>Research environment</span></div><p>Historical analysis only<br />Production risk score disabled</p><div className="sidebar-version">CREDITAI <span>·</span> 9</div></div>
    </aside>

    <main className="main-shell exhibition-main">
      <header className="topbar exhibition-topbar"><button className="mobile-brand" onClick={() => go('overview')}>◉ CreditAI</button><div className="crumb">Research <span>/</span> {nav.find((item) => item.id === page)?.title}</div><div className="top-actions"><span className="platform-state"><i /><span>Research environment</span><small>Production score disabled</small></span><span className="top-date" title="Historical source snapshot; retrieval does not make it current">Historical snapshot · {summary?.generated_at ?? 'date unavailable'} · retrieved {retrievedAt ? new Date(retrievedAt).toLocaleString() : 'not yet'}</span><span className="build-chip" title={buildInfo?.commit_sha ?? 'Build identity is unavailable'}>Build {buildInfo?.short_commit ?? (buildInfo ? 'local' : '…')}</span><div className={`api-chip api-${apiState}`}><span className="api-dot" />API {apiState === 'online' ? 'online' : apiState === 'checking' ? 'checking' : apiState === 'offline' ? 'offline' : 'not checked'}</div><button className="icon-button" aria-label="Check API health" onClick={() => { void checkHealth(); retryLoad() }} disabled={apiState === 'checking'} title="Check API health">↻</button><div className="avatar">CA</div></div></header>

      {page === 'prediction' ? <div key={page} className="page-body exhibition-page-body"><PredictionWorkspace /></div>
        : page === 'batch' ? <div key={page} className="page-body exhibition-page-body"><BatchEvaluation /></div>
        : page === 'performance' ? <div key={page} className="page-body exhibition-page-body"><ModelPerformanceLab /></div>
        : viewState === 'loading' ? <div key={page} className="page-body exhibition-page-body"><EmptyState title="Preparing research workspace" message="Loading verified summaries and qualification metadata." icon="◌" /></div>
        : viewState === 'error' || viewState === 'empty' || !summary || !inventory || !features ? <div key={page} className="page-body exhibition-page-body"><SourceTag source="unavailable" /><EmptyState title="Research data unavailable" message={loadError ?? 'The backend did not return the historical research snapshot.'} icon="!" />{retryCount > 0 && <p style={{ marginTop: '0.5rem', fontSize: '12px', color: '#617984' }}>Retry attempts: {retryCount}</p>}<button className="button-secondary" onClick={retryLoad} style={{ marginTop: '1rem' }}>Retry loading</button></div>
          : <div key={page} className="page-body exhibition-page-body">
            <div className="research-banner"><SourceTag source="historical" /><span>Source snapshot: {summary.generated_at} · Retrieved from the backend: {retrievedAt ? new Date(retrievedAt).toLocaleString() : 'not yet'} · Historical research data, not live portfolio activity.</span><button type="button" onClick={() => { void checkHealth(); retryLoad() }} disabled={loading}>Refresh</button></div>
            {page === 'overview' && <>
              <div className="hero-panel exhibition-hero"><div className="hero-copy"><div className="hero-kicker"><span className="hero-kicker-dot" />CREDIT RISK DECISION WORKBENCH</div><h1>Historical credit<br /><em>risk research.</em></h1><p>Explore a leakage-audited historical loan benchmark, inspect portfolio outcomes and evaluate model evidence — with every limitation visible.</p><div className="hero-actions"><button className="button-primary" onClick={() => go('portfolio')}>Start research demo <span>→</span></button><button className="button-quiet" onClick={() => go('discovery')}>Explore datasets</button></div><div className="hero-proof"><span><i /> Historical evidence</span><span><i /> Research only</span><span><i /> Production scoring disabled</span></div></div><div className="hero-art" aria-hidden="true"><div className="orbit orbit-outer" /><div className="orbit orbit-inner" /><div className="hero-core"><span>RISK</span><strong>↗</strong><small>RESEARCH</small></div><div className="hero-float float-a"><small>TEST AUC</small><strong>{formatMetric(metricNumber(bestTest, 'roc_auc'))}</strong><i>HISTORICAL</i></div><div className="hero-float float-b"><small>DATA STATUS</small><strong>Qualified</strong><i>WITH LIMITATIONS</i></div><div className="hero-beam" /></div><div className="hero-watermark">CREDIT INTELLIGENCE · RESEARCH ONLY</div></div>
              <div className="notice-strip"><span className="notice-icon">!</span><div><strong>Indian production performance has not been validated.</strong><span>All model metrics below refer to a historical U.S. LendingClub closed-loan cohort; the score API remains disabled.</span></div><button onClick={() => go('architecture')}>View validation gates <span>→</span></button></div>
              <div className="kpi-grid exhibition-kpi-grid"><Kpi animateValue label="Source records" value={compact(summary.dataset.records)} suffix="loans" detail="LendingClub · U.S. · 2007–2018Q4" icon="◫" /><Kpi animateValue label="Observed closed default" value={formatPercent(summary.dataset.closed_default_rate, 2)} suffix="" detail={`${summary.dataset.closed_defaults.toLocaleString()} of ${summary.dataset.closed_records.toLocaleString()} terminal outcomes`} icon="↗" accent="red" /><Kpi animateValue label="Test ROC-AUC" value={formatMetric(metricNumber(bestTest, 'roc_auc'))} suffix="" detail="HistGradientBoosting · untouched 2016–18 test" icon="⌁" accent="blue" /><Kpi animateValue label="Research-qualified" value={String(researchCount)} suffix="datasets" detail="Each for its scoped research use only" icon="◈" accent="green" /></div>
              <div className="grid-two overview-grid"><Card className="analytics-panel"><div className="panel-heading"><div><p className="eyebrow">COHORT PERFORMANCE</p><h2>Default rate by vintage</h2><p>Closed-loan outcomes across issue years</p></div><span className="mini-tag">N = {summary.dataset.closed_records.toLocaleString()}</span></div><LineChart data={summary.portfolio.vintage} /></Card><Card className="analytics-panel"><div className="panel-heading"><div><p className="eyebrow">HELD-OUT TEST</p><h2>Model comparison</h2><p>Saved metrics · cohort and target held constant</p></div><button className="text-link" onClick={() => go('lab')}>Full evaluation →</button></div><ModelComparison summary={summary} compactView /></Card></div>
              <div className="workflow-strip"><div><p className="eyebrow">FROM RAW DATA TO DECISION SUPPORT</p><h2>A traceable path from intake to insight.</h2></div><div className="workflow-steps"><span>01 <b>Qualify data</b></span><i>→</i><span>02 <b>Audit time</b></span><i>→</i><span>03 <b>Evaluate</b></span><i>→</i><span className="planned">04 <b>Partner pilot</b></span></div></div>
            </>}

            {page === 'discovery' && <>
              <SectionTitle eyebrow="EVIDENCE CATALOG" title="Data discovery & readiness" detail="Know what each dataset can support before it enters an experiment." source="historical" />
              <div className="filter-row"><div className="search-box"><span>⌕</span><input aria-label="Search datasets" placeholder="Search by dataset, source or target…" value={datasetQuery} onChange={(event) => setDatasetQuery(event.target.value)} /></div><select aria-label="Filter qualification status" value={qualificationFilter} onChange={(event) => setQualificationFilter(event.target.value)}><option value="all">All evidence states</option><option value="QUALIFIED_FOR_RESEARCH">Research Ready</option><option value="REVIEW_REQUIRED">Needs Review</option><option value="BLOCKED">Evidence Gap / restricted</option></select><select aria-label="Filter data source" value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value)}><option value="all">All sources</option><option value="historical">Historical</option><option value="synthetic">Synthetic</option><option value="external">External</option></select><span className="result-count">{filteredInventory.length} records</span></div>
              <div className="discovery-layout"><Card className="inventory-panel"><div className="table-scroll"><table className="data-table"><thead><tr><th>DATASET</th><th>ROWS</th><th>TARGET</th><th>ACCESS / LICENSE</th><th>DECISION</th><th>ACTION</th></tr></thead><DatasetInventoryTable items={filteredInventory} selectedId={selectedDataset} onSelect={setSelectedDataset} showDetailButton={true} onDetailClick={(id) => { setSelectedDataset(id); setShowDatasetDetail(true) }} /></table>{filteredInventory.length === 0 && <EmptyState title="No matching datasets" message="Try a broader search or another qualification filter." />}</div></Card>
                <Card className="profile-panel"><div className="panel-heading"><div><p className="eyebrow">DATA PROFILE</p><h2>{chosenDataset?.dataset_name ?? 'Select a dataset'}</h2></div>{chosenDataset && <StatusBadge dataset={chosenDataset} />}</div>{chosenDataset ? <><div className="profile-facts"><Fact label="Source" value={String(chosenDataset.provenance_status)} /><Fact label="Time coverage" value={String(chosenDataset.time_coverage ?? 'Not verified')} /><Fact label="Missingness" value={String(chosenDataset.missing_value_percentage ?? 'Not calculated')} /><Fact label="Duplicate rows" value={String(chosenDataset.duplicate_row_count ?? 'Not measured')} /></div><div className="profile-target"><span className="fact-label">TARGET DEFINITION</span><p>{displayUserText(String(chosenDataset.target_definition ?? 'No outcome label available.'))}</p><small>Prevalence: {String(chosenDataset.target_prevalence ?? 'not established')}</small></div>{chosenDataset.dataset_id === 'DS001' ? <><div className="subchart"><h3>Loan amount distribution</h3><p>Original U.S. dollar amount · entire accepted-loan source</p><TrendBars data={summary.portfolio.loan_amount_histogram} /></div><div className="subchart"><h3>Highest missingness features</h3><p>Column-level rates from the Phase 2.2 full-source audit</p><HorizontalBars data={(features ?? []).filter((item) => item.dataset_id === 'DS001').map((item) => ({ label: displayFeatureName(item.feature), value: Number(item.missing_percentage_all_source_rows) || 0 })).sort((a, b) => b.value - a.value).slice(0, 6)} valueKey="percent" maxValue={100} color="blue" /></div><div className="subchart"><h3>Numeric feature relationships</h3><p>Descriptive correlation, complete observations only</p><CorrelationMap summary={summary} /></div></> : <div className="profile-unavailable"><span>◈</span><div><strong>Profile data is limited for this source</strong><p>Only verified metadata is shown. No raw rows are loaded into the browser, and no target chart is created from inferred labels.</p></div></div>}{String(chosenDataset.source_url ?? '').startsWith('http') && <a className="source-link" href={String(chosenDataset.source_url)} target="_blank" rel="noreferrer">Open source record <span>↗</span></a>}</> : <EmptyState title="Choose a dataset" message="Select a row to inspect its qualification profile." />}</Card></div>
              <div className="callout-soft"><strong>Decision rule</strong><span>Research qualification is scoped to a dataset and use. It is not commercial-use permission, Indian population validation, or production approval.</span></div>
            </>}

            {page === 'portfolio' && <>
              <SectionTitle eyebrow="HISTORICAL COHORTS" title="Portfolio intelligence" detail="Explore terminal loan outcomes by origination vintage and observed segments." />
              <div className="research-banner"><SourceTag source="historical" /><span>Historical closed-loan cohort · {summary.dataset.origination_period} · final loan status observed through 2018Q4</span><button onClick={() => go('discovery')}>Data profile →</button></div>
              <div className="kpi-grid small-kpis"><Kpi label="Total source rows" value={summary.dataset.records.toLocaleString()} detail="Includes open, censored and closed loans" /><Kpi label="Closed outcomes" value={summary.dataset.closed_records.toLocaleString()} detail="Fully paid or terminal bad status" /><Kpi label="Unresolved / censored" value={summary.dataset.unresolved_or_censored.toLocaleString()} detail={`${formatPercent(summary.dataset.unresolved_or_censored / summary.dataset.records)} of the source`} accent="amber" /><Kpi label="Observed closed default rate" value={formatPercent(summary.dataset.closed_default_rate, 2)} detail="269,360 bad / 1,348,099 closed" accent="red" /></div>
              <div className="grid-two portfolio-charts"><Card><div className="panel-heading"><div><p className="eyebrow">VINTAGE VIEW</p><h2>Closed-outcome rate by origination year</h2><p>Each point includes only terminal statuses</p></div></div><LineChart data={summary.portfolio.vintage} /><div className="insight-note"><span>i</span><p>These are descriptive terminal-outcome shares, not fixed-horizon default probabilities. Years have different follow-up lengths.</p></div></Card><Card><div className="panel-heading"><div><p className="eyebrow">ORIGINATION DISTRIBUTION</p><h2>Loan amount distribution</h2><p>U.S. dollars · full accepted-loan file</p></div></div><TrendBars data={summary.portfolio.loan_amount_histogram} /><div className="chart-footnote">Amounts shown as binned counts; no loan-level records are exposed.</div></Card></div>
              <Card className="segment-panel"><div className="panel-heading"><div><p className="eyebrow">SEGMENT EXPLORER</p><h2>Observed outcome by segment</h2><p>Search a grade, vintage year or purpose. Rates use the closed denominator.</p></div><div className="segment-controls"><select value={segment} aria-label="Portfolio segment" onChange={(event) => { setSegment(event.target.value as Segment); setSegmentQuery('') }}><option value="vintage">Origination year</option><option value="grade">Credit grade</option><option value="purpose">Loan purpose</option></select><input aria-label="Filter portfolio segment" placeholder="Filter segments" value={segmentQuery} onChange={(event) => setSegmentQuery(event.target.value)} /></div></div><div className="segment-table-wrap"><table className="data-table segment-table"><thead><tr><th>SEGMENT</th><th>ALL RECORDS</th><th>CLOSED</th><th>OBSERVED BAD</th><th>RATE OF CLOSED</th><th>SHARE OF CLOSED BOOK</th></tr></thead><tbody>{searchedSegments.sort((a, b) => b.closed - a.closed).map((row) => <tr key={row.segment}><td><strong>{row.segment}</strong></td><td>{row.records.toLocaleString()}</td><td>{row.closed.toLocaleString()}</td><td>{row.defaults.toLocaleString()}</td><td className="rate-cell">{formatPercent(row.observed_closed_default_rate, 2)}</td><td><div className="table-meter"><i style={{ width: `${row.closed / summary.dataset.closed_records * 100}%` }} /></div></td></tr>)}</tbody></table>{searchedSegments.length === 0 && <EmptyState title="No matching segment" message="Try another segment name." />}</div></Card>
            </>}

            {page === 'lab' && <>
              <SectionTitle eyebrow="MODEL EVIDENCE" title="Model lab" detail="Compare saved research results without inventing curve data or tuning on the test set." />
              <div className="research-banner"><SourceTag source="historical" /><span>Phase 2.3 · LendingClub · closed-loan terminal outcome · time split</span><button onClick={() => go('discovery')}>Inspect qualification →</button></div>
              <div className="lab-filter-row"><label>MODEL<select value={selectedModel} onChange={(event) => setSelectedModel(event.target.value)}><option>HistGradientBoosting</option><option>Logistic Regression</option><option>Prevalence Baseline</option></select></label><label>EVALUATION SPLIT<select value={selectedSplit} onChange={(event) => setSelectedSplit(event.target.value)}><option>Test</option><option>Validation</option><option>Train</option></select></label><span className="split-period">{String(summary.evaluation.splits.find((row) => row.split_name === selectedSplit)?.start_date)} — {String(summary.evaluation.splits.find((row) => row.split_name === selectedSplit)?.end_date)}</span></div>
              <div className="kpi-grid lab-kpis"><Kpi label="ROC-AUC" value={formatMetric(metricNumber(currentEval, 'roc_auc'))} detail="Ranking discrimination" accent="blue" /><Kpi label="PR-AUC" value={formatMetric(metricNumber(currentEval, 'pr_auc'))} detail={`Test prevalence baseline ${formatMetric(metricNumber(summary.evaluation.all_split_metrics.find((row) => row.model_name === 'Prevalence Baseline' && row.split_name === selectedSplit), 'pr_auc'))}`} /><Kpi label="Brier score" value={formatMetric(metricNumber(currentEval, 'brier_score'))} detail={`Prevalence baseline ${formatMetric(metricNumber(summary.evaluation.all_split_metrics.find((row) => row.model_name === 'Prevalence Baseline' && row.split_name === selectedSplit), 'brier_score'))}`} accent="green" /><Kpi label="Threshold" value={formatMetric(metricNumber(currentEval, 'selected_threshold'), 2)} detail="Chosen on validation split" accent="amber" /></div>
              <div className="grid-two lab-charts"><Card><div className="panel-heading"><div><p className="eyebrow">SAVED TEST METRICS</p><h2>Model comparison</h2><p>ROC-AUC and PR-AUC are separate scales from 0 to 1</p></div></div><ModelComparison summary={summary} /></Card><Card><div className="panel-heading"><div><p className="eyebrow">THRESHOLD SNAPSHOT</p><h2>Confusion matrix</h2><p>{selectedModel} · {selectedSplit} · threshold {formatMetric(metricNumber(currentEval, 'selected_threshold'), 2)}</p></div></div>{currentEval && <ConfusionMatrix row={currentEval} />}</Card></div>
              <Card><div className="panel-heading"><div><p className="eyebrow">EVALUATION RECORD</p><h2>Evidence, not just a score</h2></div><span className="mini-tag">SAVED ARTIFACT</span></div><div className="evaluation-meta"><Fact label="Target" value={summary.evaluation.target} /><Fact label="Split design" value={summary.evaluation.split_design} /><Fact label="Calibration" value={summary.evaluation.calibration} /><Fact label="Evaluation audit" value="Independently reproduced · 11 Oct 2026" /></div><div className="metric-table-wrap"><table className="data-table metric-table"><thead><tr><th>MODEL</th><th>ROC-AUC</th><th>PR-AUC</th><th>PREVALENCE</th><th>BRIER</th><th>LOG LOSS</th><th>KS</th><th>GINI</th><th>PRECISION</th><th>RECALL</th><th>F1</th></tr></thead><tbody>{summary.evaluation.all_split_metrics.filter((row) => row.split_name === selectedSplit).map((row) => <tr key={String(row.model_name)}><td><strong>{String(row.model_name)}</strong></td>{['roc_auc','pr_auc','prevalence_baseline','brier_score','log_loss','ks_statistic','gini_coefficient','precision','recall','f1_score'].map((metric) => <td key={metric}>{formatMetric(metricNumber(row, metric))}</td>)}</tr>)}</tbody></table></div></Card>
              <section className="lab-evidence-section" aria-labelledby="lab-evidence-heading">
                <div className="lab-evidence-heading">
                  <div><p className="eyebrow">VISUAL DIAGNOSTICS</p><h2 id="lab-evidence-heading">Evidence availability</h2><p>These plots need saved scores or evaluation outputs that this benchmark does not contain.</p></div>
                  <span className="evidence-boundary-pill"><i /> Historical artifact boundary</span>
                </div>
                <div className="unavailable-grid">
                  <EvidenceGapCard icon="↗" title="ROC curve" message="No per-loan held-out scores or ROC coordinates were saved. Aggregate AUC values cannot recreate the curve." required="Per-loan held-out scores and observed labels" />
                  <EvidenceGapCard icon="◎" title="Calibration plot" message="No fitted calibration model or calibration-bin probabilities are present in this benchmark." required="Calibrated scores, outcome labels, and bin definitions" />
                  <EvidenceGapCard icon="⌁" title="Threshold sensitivity" message="The artifact records one validation-selected threshold per model, not a threshold sweep." required="Validation scores evaluated across documented cutoffs" />
                </div>
              </section>
            </>}

            {page === 'explorer' && <>
              <SectionTitle eyebrow="RESEARCH-ONLY EXPLORATION" title="Risk explorer" detail="Prediction-level outputs are only shown when reproducible scores are actually saved." />
              <div className="research-banner"><SourceTag source="historical" /><span>Historical U.S. research benchmark · no individual prediction scores are available</span></div>
              <Card className="explorer-empty"><div className="lock-orbit"><span>◎</span><i /></div><p className="eyebrow">PREDICTION OUTPUTS NOT SAVED</p><h2>There are no historical risk scores to explore yet.</h2><p>The Phase 2.3 evaluation saved cohort metrics and confusion matrices, but not per-loan probability scores, stable research IDs, or fitted model artifacts. CreditAI will not fabricate individual predictions to fill this view.</p><div className="explorer-facts"><Fact label="Benchmark" value="LendingClub · U.S." /><Fact label="Observed label" value="Terminal closed-loan status" /><Fact label="Test set" value="2016–2018 · 518,744 closed loans" /></div><button className="button-primary" onClick={() => go('lab')}>View saved model evidence <span>→</span></button></Card>
              <Card className="simulated-workflow-card"><div className="panel-heading"><div><p className="eyebrow">EDUCATIONAL FUTURE STATE</p><h2>How a future validated scoring API would work</h2><p>This is a simulated workflow and does not call the production score endpoint.</p></div><span className="source-tag source-live-unvalidated">SIMULATED WORKFLOW — NOT A LIVE LENDING API</span></div><div className="simulated-payload"><strong>Synthetic Indian product example · display currency INR</strong><pre>{JSON.stringify({ borrower_reference: 'SYNTHETIC-001', monthly_income_display: formatIndianRupees(45000), requested_amount_display: formatIndianRupees(125000), source: 'synthetic_demo', score: 'not produced' }, null, 2)}</pre><p>Display examples use INR; no exchange-rate conversion or model score is implied.</p></div><ol className="simulated-steps">{SIMULATED_SCORING_STEPS.map((step) => <li key={step}>{step}</li>)}</ol><p className="research-footnote">Before any Indian lending API: authorized Indian borrower data, observed repayment outcomes, leakage controls, train/validation/test methodology, calibration, fairness and subgroup evaluation, stability/drift testing, governance, monitoring, and controlled deployment are required.</p></Card>
              <Card className="safe-score-card"><div><SourceTag source="live-unvalidated" /><h3>Real score API safety check</h3><p>The real <code>/v1/score</code> contract remains gated. This synthetic contract request contains no real person and must return no probability.</p></div><button className="button-secondary" disabled={scoreState === 'loading'} onClick={sendContractExample}>{scoreState === 'loading' ? 'Checking contract…' : 'Check not_validated contract'}</button>{scoreState === 'done' && <div className="api-result" role="status"><span>API status</span><strong>{String(scorePayload?.score_status ?? 'unknown')}</strong><span>Default probability</span><strong>{scoreMessage}</strong><small>Model version: {String(scorePayload?.model_version ?? 'none')} · Source: {String((scorePayload?.provenance as { source?: string } | undefined)?.source ?? 'unknown')}</small></div>}{scoreState === 'error' && <div className="inline-error" role="alert">API unavailable; no risk score was produced.</div>}</Card>
            </>}

            {page === 'explainability' && <>
              <SectionTitle eyebrow="MODEL INTERPRETATION" title="Explainability" detail="A model contribution explains fitted-model behavior; it does not prove a cause." />
              <div className="research-banner"><SourceTag source="historical" /><span>Only explanations tied to the historical LendingClub fit are in scope</span></div>
              <Card className="explorer-empty"><div className="lock-orbit"><span>✳</span><i /></div><p className="eyebrow">LENDINGCLUB EVIDENCE GAP</p><h2>Historical LendingClub feature explanations are unavailable.</h2><p>The verified Phase 2.3 LendingClub artifact contains aggregate metrics, but no fitted model, per-loan scores, or local SHAP outputs. Phase 1 synthetic SHAP artifacts are excluded here so they are not presented as historical LendingClub evidence.</p><div className="explorer-facts"><Fact label="LendingClub fit artifact" value="Not saved" /><Fact label="Per-loan feature values" value="Not exposed" /><Fact label="Synthetic SHAP outputs" value="Excluded from this view" /></div><div className="callout-soft"><strong>Available scoped explanation</strong><span>The Taiwan research prediction workspace can return local model attribution alongside an individual research estimate.</span></div><button className="button-secondary" onClick={() => go('prediction')}>Open research prediction explanation</button></Card>
            </>}

            {page === 'monitoring' && <>
              <SectionTitle eyebrow="POPULATION SIGNALS" title="Monitoring & stability" detail="Historical cohort patterns are available; there is no live production traffic or monitoring stream." />
              <div className="monitoring-state"><span className="monitor-icon">⌁</span><div><strong>Awaiting validated deployment</strong><p>No production requests, model versions, or matured live labels exist. Historical benchmark evidence remains available below.</p></div><span className="status-badge readiness-evidence-gap">Future validation gate</span></div>
              <div className="grid-two"><Card><div className="panel-heading"><div><p className="eyebrow">HISTORICAL ONLY</p><h2>Observed outcome by vintage</h2><p>Origination year versus terminal outcome among closed loans</p></div></div><LineChart data={summary.portfolio.vintage} /></Card><Card><div className="panel-heading"><div><p className="eyebrow">EVIDENCE STATUS</p><h2>Monitoring signals</h2><p>Historical evidence and future validation gates</p></div></div><div className="monitor-list"><MonitorRow status="Historical" title="Target prevalence by time" detail="Historical evidence available from closed-loan cohort summaries." /><MonitorRow status="Future validation gate" title="Population Stability Index" detail="Awaiting production comparison population." /><MonitorRow status="Future validation gate" title="Missingness drift" detail="Awaiting live request stream." /><MonitorRow status="Future validation gate" title="Performance by live period" detail="Awaiting matured outcomes." /></div></Card></div>
              <Card><div className="panel-heading"><div><p className="eyebrow">COHORT COVERAGE</p><h2>Benchmark split periods</h2><p>Chronological partitions from the verified Phase 2.3 artifact</p></div></div><div className="split-cards">{summary.evaluation.splits.map((row) => <div className="split-card" key={String(row.split_name)}><span>{String(row.split_name)}</span><strong>{compact(Number(row.total_samples))}</strong><small>{String(row.start_date)} — {String(row.end_date)}</small><div className="split-meter"><i style={{ width: `${Number(row.default_prevalence) * 100 * 4}%` }} /></div><small>Closed-cohort outcome share · {formatPercent(Number(row.default_prevalence))}</small></div>)}</div></Card>
            </>}

            {page === 'architecture' && <>
              <SectionTitle eyebrow="TRACEABILITY & CONTROL" title="Architecture & audit" detail="What exists today, what is research-only and what depends on a lender partnership." />
              <div className="status-ribbon"><span className="pulse-dot" />PRODUCTION SCORE STATUS <strong>SAFETY LOCK ACTIVE</strong><span className="divider" />MODEL VERSION <strong>NONE</strong><span className="divider" />LIVE TRAFFIC <strong>NONE</strong></div>
              <h2 className="roadmap-title">Validation & Evidence Roadmap</h2><Card className="architecture-panel"><div className="panel-heading"><div><p className="eyebrow">SYSTEM FLOW</p><h2>Evidence-first credit research</h2><p>Research path implemented in the workspace; production integration remains gated.</p></div><span className="status-badge readiness-evidence-gap">Future validation gate</span></div><div className="architecture-flow"><ArchitectureNode n="01" title="Dataset intake" status="Implemented" detail="Local source inventory · gated access"/><span className="flow-arrow">→</span><ArchitectureNode n="02" title="Quality checks" status="Implemented" detail="Schema · missingness · duplicates"/><span className="flow-arrow">→</span><ArchitectureNode n="03" title="Temporal & target audit" status="Implemented" detail="Point-in-time · maturity · leakage"/><span className="flow-arrow">→</span><ArchitectureNode n="04" title="Research models" status="Historical only" detail="U.S. LendingClub benchmark"/><span className="flow-arrow">→</span><ArchitectureNode n="05" title="Evaluation & explainability" status="Evidence gap" detail="LendingClub saved aggregate metrics; no ROC coordinates"/><span className="flow-arrow">→</span><ArchitectureNode n="06" title="Lender workflow" status="Evidence required" detail="Authorized Indian outcomes required"/></div></Card>
              <div className="grid-two"><Card><div className="panel-heading"><div><p className="eyebrow">AUDIT TRAIL</p><h2>Latest verified experiment</h2></div></div><div className="audit-facts"><Fact label="Experiment" value="Phase 2.3 LendingClub historical benchmark" /><Fact label="Dataset version" value="accepted 2007–2018Q4 · 2,260,701 source rows" /><Fact label="Target" value={summary.evaluation.target} /><Fact label="Split" value="Train 2007–13 · Validation 2014–15 · Test 2016–18" /><Fact label="Threshold method" value="Selected using validation split only" /><Fact label="Calibration" value="Not fitted" /><Fact label="Metric artifact" value="reports/phase_2_3_metrics.csv · independently reproduced" /><Fact label="Evaluation evidence date" value="11 Oct 2026" /></div></Card><Card><div className="panel-heading"><div><p className="eyebrow">VALIDATION & EVIDENCE ROADMAP</p><h2>Next evidence gates</h2></div></div><div className="monitor-list"><MonitorRow status="Evidence required" title="Indian borrower outcomes" detail="No authorized Indian repayment sample in the workspace." /><MonitorRow status="Rights review required" title="Commercial data rights" detail="LendingClub local-copy commercial terms remain unverified." /><MonitorRow status="Awaiting validated deployment" title="Model monitoring" detail="No live endpoint traffic, version registry or matured labels." /><MonitorRow status="Safety lock active" title="/v1/score" detail="Production scoring intentionally remains disabled and returns not_validated with a null probability." /></div></Card></div>
              <Card><div className="panel-heading"><div><p className="eyebrow">NEXT BEST ACTION</p><h2>Prepare a lender research pilot</h2><p>Keep the scope narrow and make each evidence gate auditable.</p></div></div><div className="next-steps"><Step n="01" title="Secure data-use agreement" detail="Agree purpose, consent/legal basis, retention, access and deletion."/><Step n="02" title="Define observed default" detail="Fix product, DPD/write-off definition, observation cutoff and follow-up horizon."/><Step n="03" title="Receive pseudonymized sample" detail="Application-time fields plus dated repayment events; no raw identifiers in model store."/><Step n="04" title="Run temporal validation" detail="Later time holdout, prevalence and current-policy baselines, calibration and subgroup review."/></div></Card>
            </>}
            <footer className="page-footer"><span>CreditAI Research Workbench <i>·</i> Phase 6.1</span><span>Historical evidence, clearly scoped. No production underwriting.</span></footer>
          </div>}
      {showDatasetDetail && chosenDataset && <DatasetDetailModal dataset={chosenDataset} onClose={() => setShowDatasetDetail(false)} />}
    </main>
  </div>
}

function Kpi({ label, value, suffix, detail, icon, accent = '', animateValue = true }: { label: string; value: string; suffix?: string; detail: string; icon?: string; accent?: string; animateValue?: boolean }) {
  const displayValue = useCountUpValue(value, animateValue)

  const help: Record<string, string> = {
    'ROC-AUC': 'Ranking discrimination across classification cutoffs; 0.5 is random ranking.',
    'PR-AUC': 'Precision-recall summary; compare with default prevalence.',
    'Brier score': 'Average squared difference between predicted probability and observed outcome; lower is better.',
    Threshold: 'Research class cutoff chosen on validation evidence; not a lending policy.',
  }
  return <Card className={`kpi-card exhibition-kpi ${accent}`}><div className="kpi-top"><span title={help[label]}>{label}</span><b>{icon}</b></div><div className="kpi-value">{displayValue}<small>{suffix}</small></div><p>{detail}</p></Card>
}

function StatusBadge({ dataset }: { dataset: InventoryItem }) {
  const readiness = datasetReadiness(dataset)
  const modifier = readiness.toLowerCase().replaceAll(/[^a-z]+/g, '-')
  return <span className={`status-badge readiness-${modifier}`}><i />{readiness}</span>
}

function Fact({ label, value }: { label: string; value: string }) {
  return <div className="fact"><span className="fact-label">{label}</span><strong>{value}</strong></div>
}

function ModelComparison({ summary, compactView = false }: { summary: Summary; compactView?: boolean }) {
  const test = summary.evaluation.metrics
  const models = ['Logistic Regression', 'HistGradientBoosting', 'Prevalence Baseline']
  const values = models.map((name) => {
    const row = test.find((item) => item.model_name === name)
    return { label: name, roc: metricNumber(row, 'roc_auc'), pr: metricNumber(row, 'pr_auc') }
  })
  return <div className={`model-compare ${compactView ? 'compact' : ''}`}><div className="metric-legend"><span><i className="legend-blue" />ROC-AUC</span><span><i className="legend-teal" />PR-AUC</span><small>Untouched test · 2016–18</small></div>{values.map((row) => <div className="model-bars" key={row.label}><div className="model-bar-name">{row.label}{row.roc === null && <small>Constant score · ranking undefined</small>}</div><div className="model-bar-pair">{row.roc !== null ? <div className="model-track"><i className="blue-fill" style={{ width: `${row.roc * 100}%` }} /><b>{formatMetric(row.roc)}</b></div> : <div className="not-defined">ROC-AUC undefined</div>}<div className="model-track"><i className="teal-fill" style={{ width: `${(row.pr ?? 0) * 100}%` }} /><b>{formatMetric(row.pr)}</b></div></div></div>)}<p className="chart-footnote">PR-AUC baseline is test prevalence (0.2242). Metrics describe closed-loan terminal outcomes, not calibrated fixed-horizon PD.</p></div>
}

function ConfusionMatrix({ row }: { row: MetricRow }) {
  const cells = [{ label: 'True negative', key: 'tn', color: 'tn' }, { label: 'False positive', key: 'fp', color: 'fp' }, { label: 'False negative', key: 'fn', color: 'fn' }, { label: 'True positive', key: 'tp', color: 'tp' }]
  return <div className="confusion-grid">{cells.map((cell) => <div className={`confusion-cell ${cell.color}`} key={cell.key}><small>{cell.label}</small><strong>{metricNumber(row, cell.key)?.toLocaleString() ?? '—'}</strong></div>)}</div>
}

function MonitorRow({ status, title, detail }: { status: string; title: string; detail: string }) {
  return <div className="monitor-row"><span className={`monitor-status ${status.toLowerCase().replaceAll(' ', '-')}`}>{status}</span><div><strong>{title}</strong><p>{detail}</p></div></div>
}

function ArchitectureNode({ n, title, status, detail }: { n: string; title: string; status: string; detail: string }) {
  return <div className={`arch-node arch-${status.toLowerCase().replaceAll(' ', '-')}`}><span>{n}</span><strong>{title}</strong><small>{detail}</small><i>{status}</i></div>
}

function Step({ n, title, detail }: { n: string; title: string; detail: string }) {
  return <div className="step-card"><span>{n}</span><div><strong>{title}</strong><p>{detail}</p></div></div>
}

function DatasetDetailModal({ dataset, onClose }: { dataset: InventoryItem; onClose: () => void }) {
  const sizeInMB = typeof dataset.size_bytes === 'number' ? `${(dataset.size_bytes / 1024 / 1024).toFixed(2)} MB` : 'Unknown'
  const readiness = datasetReadiness(dataset)
  const nextEvidence = readiness === 'Source Unavailable'
    ? 'Obtain the source through its documented source route, verify file identity and hash, then inspect schema and license before use.'
    : readiness === 'Synthetic / Demo'
      ? 'Keep use limited to software demonstration. Real outcome labels and authorized population data would be required for borrower research.'
      : readiness === 'Needs Review' || readiness === 'Available — Restricted Use'
        ? 'Resolve data-use rights, target definition, source provenance, and population/time coverage before expanding research use.'
        : 'Document the intended use and confirm all evidence gates for that specific use.'
  const blockers = [dataset.license_and_access, dataset.commercial_use, dataset.leakage_temporal_risks]
    .filter((value) => value && String(value).toLowerCase() !== 'none')
    .map(String)
  return <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="dataset-detail-title"><div className="modal-content" onClick={(e) => e.stopPropagation()}><div className="modal-header"><h2 id="dataset-detail-title">{dataset.dataset_name}</h2><button className="modal-close" onClick={onClose} aria-label="Close modal">×</button></div><div className="modal-body"><span className={`status-badge readiness-${readiness.toLowerCase().replaceAll(/[^a-z]+/g, '-')}`}>{readiness}</span><div className="detail-grid"><Fact label="Dataset ID" value={String(dataset.dataset_id)} /><Fact label="Source URL" value={String(dataset.source_url || 'Not specified')} /><Fact label="Local status" value={String(dataset.local_status || 'Not recorded')} /><Fact label="Local Path" value={String(dataset.local_path || 'Not available')} /><Fact label="Format" value={String(dataset.format || 'Unknown')} /><Fact label="Size" value={sizeInMB} /><Fact label="Rows" value={String(dataset.row_count?.toLocaleString() || 'Unknown')} /><Fact label="Columns" value={String(dataset.column_count?.toLocaleString() || 'Unknown')} /><Fact label="Target Column" value={String(dataset.target_column || 'None')} /><Fact label="Target Definition" value={String(dataset.target_definition || 'Not defined')} /><Fact label="Target Prevalence" value={String(dataset.target_prevalence || 'Unknown')} /><Fact label="Time Coverage" value={String(dataset.time_coverage || 'Unknown')} /><Fact label="Missing Value %" value={String(dataset.missing_value_percentage || 'Not calculated')} /><Fact label="Duplicate Rows" value={String(dataset.duplicate_row_count?.toLocaleString() || 'Not measured')} /><Fact label="Provenance Status" value={String(dataset.provenance_status || 'Unknown')} /><Fact label="License / Access" value={String(dataset.license_and_access || 'Not verified')} /><Fact label="Commercial Use" value={String(dataset.commercial_use || 'Not established')} /><Fact label="PII Concerns" value={displayUserText(String(dataset.pii_sensitive_concerns || 'None noted'))} /><Fact label="Temporal Risks" value={String(dataset.leakage_temporal_risks || 'None noted')} /><Fact label="Proposed Use" value={String(dataset.proposed_research_use || 'Not specified')} /></div><div className="evidence-detail"><h3>What the catalog review found</h3><p>Current recorded availability: {String(dataset.local_status || 'No local status recorded')}. The visible findings are from the repository inventory metadata; they do not imply that an external dataset was acquired or independently rechecked.</p><h3>Why it cannot advance further</h3><p>{blockers.length ? blockers.join(' ') : readiness === 'Research Ready' ? 'The current evidence qualifies only for the documented research use.' : 'The inventory does not contain enough verified evidence to advance this dataset.'}</p><h3>Evidence needed next</h3><p>{nextEvidence}</p></div></div><div className="modal-footer"><button className="button-secondary" onClick={onClose}>Close</button></div></div></div>
}

export default App
