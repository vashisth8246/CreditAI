import { useEffect, useState } from 'react'
import './decisionProof.css'

const endpoint = '/v1/research/decisionproof'
const money = (n: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n)
const label = (name: string) => name.replaceAll('_', ' ')
type Evidence = { id: string; field: string; values: number[]; claimed: number | null; status: string; explanation: string; source: string; period: string; collected_at: string }
type Action = { id: string; label: string; reveals: string[]; cost: number; permitted: boolean }
type Scenario = { id: string; title: string; explanation: string; evidence: Evidence[]; proposed_emi: number }
type Strategy = { actions: string[]; cost: number; resolved: boolean; unresolved_groups: number; possible_observations: number; reveals: string[] }
type Result = { method: string; scenario: Scenario; status: string; policy: { residual_min: number; payment_ratio_bps: number; cost_profile: string }; meets_count: number;
  states: { income: number; expenses: number; existing_emi: number; residual: number; payment_ratio_bps: number | null; outcome: string }[];
  sensitivity: { residual_min: number; meets_count: number }[]; ratio_sensitivity: { payment_ratio_bps: number; meets_count: number }[];
  verification_options: Action[]; consequential: string[]; strategies: Record<string, Strategy>;
  limitation: string; reproducibility_id: string; generated_at: string }
type Benchmark = { profiles: { cost_profile: string; cases: number; reversals: number; elapsed_ms: number;
  strategies: Record<string, { cost: number; actions: number; resolved: number; individually_removable_actions: number }> }[] }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(endpoint + path, init)
  if (!response.ok) throw Error('DecisionProof request failed (HTTP ' + response.status + ').')
  return response.json()
}

function downloadReport(result: Result) {
  const chosen = result.strategies.DecisionProof
  const report = [
    '# CreditAI DecisionProof — Synthetic Research Report', '',
    result.scenario.title, result.scenario.explanation, '',
    '## Policy and evidence',
    'Residual minimum ' + money(result.policy.residual_min) + '; maximum payment-to-income ' + result.policy.payment_ratio_bps / 100 + '%; proposed EMI ' + money(result.scenario.proposed_emi) + '.',
    ...result.scenario.evidence.map(e => '- ' + label(e.field) + ' (' + e.status + '): ' + e.values.map(money).join(' / ') + '. ' + e.source + '. ' + e.explanation),
    '## Stability', result.meets_count + ' of ' + result.states.length + ' modeled states meet policy. ' + label(result.status) + '.',
    'Consequential fields: ' + (result.consequential.map(label).join(', ') || 'none') + '.',
    '## Minimum evidence', ...result.verification_options.filter(a => chosen.actions.includes(a.id)).map(a => '- ' + a.label + ' (' + a.cost + ' effort units).'),
    chosen.resolved ? 'Every possible observation group has a single policy outcome.' : 'The available actions cannot resolve all consequential uncertainty; manual review remains necessary.',
    '## Strategy comparison', ...Object.entries(result.strategies).map(([name, row]) => '- ' + name + ': ' + row.cost + ' units, ' + row.actions.length + ' actions, ' + (row.resolved ? 'resolved' : 'unresolved') + '.'),
    '## Reproducibility and limits', result.method + ' · ' + result.generated_at, result.reproducibility_id, result.limitation,
    '## Reproducible audit payload', '\x60\x60\x60json', JSON.stringify(result, null, 2), '\x60\x60\x60',
  ].join('\n')
  const url = URL.createObjectURL(new Blob([report], { type: 'text/markdown;charset=utf-8' }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'decisionproof-' + result.scenario.id + '.md'
  anchor.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 30_000)
}

export default function DecisionProof() {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [id, setId] = useState('conflicting-income')
  const [residual, setResidual] = useState('20000')
  const [ratio, setRatio] = useState('40')
  const [cost, setCost] = useState('base')
  const [result, setResult] = useState<Result | null>(null)
  const [benchmark, setBenchmark] = useState<Benchmark | null>(null)
  const [showPlan, setShowPlan] = useState(false)
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    void request<{ scenarios: Scenario[] }>('/scenarios')
      .then(data => { if (active) setScenarios(data.scenarios) })
      .catch((cause: Error) => { if (active) setError(cause.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])
  const scenario = scenarios.find(item => item.id === id)
  const clearResult = () => { setResult(null); setShowPlan(false); setError('') }
  const chosen = result?.strategies.DecisionProof
  const maxCost = result ? Math.max(1, ...Object.values(result.strategies).map(row => row.cost)) : 1
  return <div className="page-body dp">
    <header className="dp-hero">
      <p className="eyebrow">CREDITAI RESEARCH LAB · SYNTHETIC APPLICATIONS</p>
      <h1>DecisionProof</h1><p>Find the minimum additional evidence needed to resolve a consequential lending-policy uncertainty.</p>
      <p>This simulated affordability policy is separate from Taiwan XGBoost and Confidence Guardian. No real underwriting, verification, or borrower records.</p>
    </header>
    {error && <p className="form-error" role="alert">{error}</p>}
    <section className="panel">
      <h2>1. Choose an evidence scenario</h2>
      {loading ? <p role="status">Loading synthetic scenarios…</p> : !scenario ? <p>No scenarios are available. Reload to try again.</p> : <>
        <label>Synthetic scenario <select disabled={busy} value={id} onChange={event => { setId(event.target.value); clearResult() }}>
          {scenarios.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}
        </select></label>
        <p>{scenario.explanation}</p>
        <div className="dp-grid" aria-label="Evidence completeness and conflicts">{scenario.evidence.map(item => <article key={item.id}>
          <h3>{label(item.field)}</h3><span className="dp-tag">{item.status}</span>
          <p><strong>Tested values:</strong> {item.values.map(money).join(' · ')}</p>
          <p>Claimed: {item.claimed === null ? 'not provided' : money(item.claimed)}. {item.explanation}</p>
          <small>{item.source} · {item.period}</small>
        </article>)}</div>
      </>}
    </section>
    {scenario && <section className="panel">
      <h2>2. Analyze policy stability</h2><p>Proposed EMI: {money(scenario.proposed_emi)}. These thresholds are illustrative.</p>
      <form onSubmit={async event => {
        event.preventDefault(); clearResult(); setBusy(true)
        try { setResult(await request<Result>('/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
          scenario_id: id, residual_min: Number(residual), payment_ratio_bps: Math.round(Number(ratio) * 100), cost_profile: cost,
        }) })) }
        catch (cause) { setError((cause as Error).message) } finally { setBusy(false) }
      }}>
        <div className="dp-controls">
          <label>Minimum residual (₹)<input required type="number" min="0" max="1000000" step="1" value={residual} disabled={busy} onChange={event => { setResidual(event.target.value); clearResult() }} /></label>
          <label>Maximum payment-to-income (%)<input required type="number" min="0" max="100" step=".01" value={ratio} disabled={busy} onChange={event => { setRatio(event.target.value); clearResult() }} /></label>
          <label>Simulated cost profile<select value={cost} disabled={busy} onChange={event => { setCost(event.target.value); clearResult() }}>
            <option value="base">Base effort</option><option value="income_costly">Income check costs more</option><option value="combined_costly">Combined check costs more</option>
          </select></label>
        </div>
        <button className="button-primary" disabled={busy}>{busy ? 'Analyzing…' : 'Analyze decision stability'}</button>
      </form>
    </section>}
    {result && chosen && <>
      <section className="panel" aria-label="Stability results">
        <h2>{result.status === 'stable_under_tested_scenarios' ? 'Stable across tested states' : 'Sensitive to evidence'}</h2>
        <p role="status">{result.meets_count} of {result.states.length} states meet the simulated policy. Consequential fields: {result.consequential.map(label).join(', ') || 'none'}.</p>
        <meter min={0} max={result.states.length} value={result.meets_count} aria-label="States meeting simulated policy" />
        <div className="dp-table"><table><caption>Modeled states · INR</caption><thead><tr>{['Income','Expenses','Existing EMI','Residual','Payment ratio','Result'].map(text => <th key={text}>{text}</th>)}</tr></thead>
          <tbody>{result.states.map((row, index) => <tr key={index}><td>{money(row.income)}</td><td>{money(row.expenses)}</td><td>{money(row.existing_emi)}</td><td>{money(row.residual)}</td><td>{row.payment_ratio_bps === null ? 'Unavailable' : row.payment_ratio_bps / 100 + '%'}</td><td>{row.outcome.startsWith('meets') ? 'Meets simulated policy' : 'Outside simulated policy'}</td></tr>)}</tbody>
        </table></div>
        <div className="dp-grid" aria-label="Threshold sensitivity">
          {result.sensitivity.map(row => <article key={row.residual_min}><strong>Residual minimum {money(row.residual_min)}</strong><meter min={0} max={result.states.length} value={row.meets_count} aria-label="States meeting policy" /><span>{row.meets_count}/{result.states.length} meet policy</span></article>)}
          {result.ratio_sensitivity.map(row => <article key={row.payment_ratio_bps}><strong>Payment limit {row.payment_ratio_bps / 100}%</strong><meter min={0} max={result.states.length} value={row.meets_count} aria-label="States meeting policy" /><span>{row.meets_count}/{result.states.length} meet policy</span></article>)}
        </div>
      </section>
      <section className="panel">
        <h2>3. Find minimum evidence</h2>
        <button className="button-primary" onClick={() => setShowPlan(true)} disabled={showPlan}>Show verification plan</button>
        {showPlan && <div aria-label="Verification plan">
          <p>{chosen.resolved ? chosen.actions.length ? 'The lowest-cost permitted set separates all modeled states with different policy outcomes.' : 'No additional verification is needed to distinguish the tested policy outcomes.' : 'No permitted set can resolve the modeled uncertainty. Manual review is required.'}</p>
          {result.verification_options.filter(action => chosen.actions.includes(action.id)).map(action => <article key={action.id} className="dp-action">
            <strong>{action.label} · {action.cost} effort units</strong>
            <p>Reveals {action.reveals.map(label).join(' and ')}. These modeled observations can distinguish states with different policy outcomes.</p>
          </article>)}
          <p>{chosen.cost} effort units · {chosen.possible_observations} possible observation groups · {chosen.unresolved_groups} unresolved groups.</p>
          <h3>4. Compare strategies</h3>
          <div className="dp-grid">{Object.entries(result.strategies).map(([name, row]) => <article key={name}>
            <strong>{name}</strong><meter min={0} max={maxCost} value={row.cost} aria-label={name + ' cost'} />
            <p>{row.cost} effort units · {row.actions.length} actions · {row.resolved ? 'Resolved' : 'Unresolved'}</p>
          </article>)}</div>
          <h3>5. Export research evidence</h3>
          <button className="button-secondary" onClick={() => downloadReport(result)}>Download DecisionProof report</button>
          <p className="dp-id">Replay ID: {result.reproducibility_id}</p>
          <p>{result.limitation}</p>
        </div>}
      </section>
    </>}
    <section className="panel">
      <h2>Synthetic benchmark</h2>
      <button className="button-secondary" onClick={() => { void request<Benchmark>('/evaluation').then(setBenchmark).catch((cause: Error) => setError(cause.message)) }}>Run catalog benchmark</button>
      {benchmark?.profiles.map(profile => <div key={profile.cost_profile} className="dp-table"><table>
        <caption>{label(profile.cost_profile)} · {profile.cases} cases · {profile.reversals} evidence-sensitive · {profile.elapsed_ms} ms</caption>
        <thead><tr>{['Strategy', 'Cost', 'Actions', 'Resolved', 'Removable actions'].map(text => <th key={text}>{text}</th>)}</tr></thead>
        <tbody>{Object.entries(profile.strategies).map(([name, row]) => <tr key={name}><td>{name}</td><td>{row.cost}</td><td>{row.actions}</td><td>{row.resolved}</td><td>{row.individually_removable_actions}</td></tr>)}</tbody>
      </table></div>)}
    </section>
  </div>
}
