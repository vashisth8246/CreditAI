import { useEffect, useState } from 'react'
import { flushSync } from 'react-dom'
import { calculate, charts, example, metrics, money, parseAmount, profiles, timeline } from './moneyHealth'
import type { Entries, Result } from './moneyHealth'
import { applicationLink, downloadMoneyHealthPdf } from './moneyHealthPdf'
import './moneyHealth.css'

function Chart({ title, rows }: ReturnType<typeof charts>[number]) {
  const extent = Math.max(1, ...rows.map(([, amount]) => Math.abs(amount)))
  const signed = rows.some(([, amount]) => amount < 0)
  return <figure className="mh-chart">
    <figcaption>{title} · INR</figcaption>
    {rows.length === 0 && <p>No categories provided.</p>}
    {rows.map(([label, amount]) => <div key={label} className="mh-bar">
      <div><span>{label}</span><strong>{money(amount)}</strong></div>
      <svg aria-hidden="true" viewBox={signed ? '-100 0 200 8' : '0 0 100 8'} preserveAspectRatio="none">
        <rect x={signed ? -100 : 0} width={signed ? 200 : 100} height="8" fill="#e5eee8" />
        <rect x={amount < 0 ? amount / extent * 100 : 0} width={Math.abs(amount) / extent * 100} height="8" fill={amount < 0 ? '#a53939' : '#18704e'} />
        <path d="M0 0 V8" stroke="#283b32" strokeWidth=".4" />
      </svg>
    </div>)}
  </figure>
}

export default function MoneyHealth() {
  const [profile, select] = useState<number | null>(null)
  const [entries, setEntries] = useState<Entries>({})
  const [source, setSource] = useState(false)
  const [result, setResult] = useState<Result | null>(null)
  const [changes, setChanges] = useState<Entries>({})
  const [error, setError] = useState('')
  const [reportTime, setReportTime] = useState('')
  useEffect(() => {
    const stamp = () => flushSync(() => setReportTime(new Date().toLocaleString('en-IN', { timeZoneName: 'short' })))
    window.addEventListener('beforeprint', stamp)
    return () => window.removeEventListener('beforeprint', stamp)
  }, [])
  const [pdfBusy, setPdfBusy] = useState(false)
  const [pdfError, setPdfError] = useState('')
  const link = applicationLink(window.location.origin)
  const chosen = profile === null ? null : profiles[profile]
  const clear = () => {
    setEntries({})
    setSource(false)
    setResult(null)
    setChanges({})
    setError('')
    setReportTime('')
    setPdfError('')
  }
  const run = (input: Entries) => {
    if (!chosen) return
    try {
      setResult(calculate(chosen.fields, input))
      setError('')
      setChanges({})
    } catch (failure) {
      setError((failure as Error).message)
      setResult(null)
    }
  }
  const load = (immediate: boolean) => {
    if (!chosen) return
    const input = example(chosen.fields)
    clear()
    setEntries(input)
    setSource(true)
    if (immediate) run(input)
  }
  let scenario = result
  let scenarioError = ''
  let goalRows: [string, number][] = []
  let months: number | null = null
  if (result && chosen) {
    try {
      const override = Object.fromEntries(chosen.fields.flatMap(({ id }) => changes[id]?.trim() ? [[id, changes[id]]] : []))
      if (changes.extra?.trim()) {
        const debt = (parseAmount(override.debt ?? entries.debt) ?? 0) + (parseAmount(changes.extra) ?? 0)
        override.debt = (debt / 100).toFixed(2)
      }
      const modified = calculate(chosen.fields, { ...entries, ...override })
      const target = parseAmount(changes.target)
      const allocated = parseAmount(changes.allocated) ?? 0
      const contribution = parseAmount(changes.contribution) ?? 0
      if (allocated > result.savings) throw new Error('Allocated savings cannot exceed accessible savings.')
      months = timeline(target, allocated, contribution)
      if (target !== null) goalRows = [['Purchase target', target], ['Savings allocated to purchase', Math.min(allocated, target)], ['Still to save', Math.max(0, target - allocated)]]
      scenario = modified
    } catch (failure) {
      scenario = null
      scenarioError = (failure as Error).message
    }
  }
  const provenance = source ? 'EXAMPLE INPUT — NOT A REAL VISITOR OR DATASET RECORD' : 'SELF-REPORTED'
  const print = () => window.print()
  const changed = result && scenario ? scenario.register.filter((field, index) => field.amount !== result.register[index].amount) : []
  const scenarioInputs = [
    ...(profile === 1 ? [['extra', 'Additional monthly EMI']] : []),
    ...([0, 3].includes(profile ?? -1) ? [['target', 'Purchase target'], ['allocated', 'Savings explicitly allocated'], ['contribution', 'Planned monthly contribution']] : []),
  ]
  const goalExplanation = goalRows.length === 0 ? '' :
    (months === null ? 'Enter a positive contribution to project the timeline.' :
      `${months} whole months at ${money(parseAmount(changes.contribution) ?? 0)} per month.`) +
    ' The timeline rounds up the remaining target divided by the planned contribution. It assumes a constant contribution and excludes interest and price changes.' +
    ((parseAmount(changes.contribution) ?? 0) > Math.max(0, scenario?.balance ?? 0) ? ' The planned contribution exceeds the available scenario balance.' : '')
  const download = async (generated: string) => {
    if (!result || !scenario || !chosen) return
    setPdfBusy(true)
    setPdfError('')
    try {
      const notes = changed.map(field => {
        const before = result.register.find(item => item.id === field.id)?.amount ?? null
        return `${field.label} changed from ${before === null ? 'unavailable' : money(before)} to ${field.amount === null ? 'unavailable' : money(field.amount)}.`
      })
      if (!notes.length) notes.push('Baseline monthly amounts were retained.')
      for (const [id, label] of scenarioInputs) {
        const amount = parseAmount(changes[id])
        notes.push(`${label}: ${amount === null ? 'not entered' : money(amount)}.`)
      }
      await downloadMoneyHealthPdf({
        profile: chosen.name, provenance, example: source, result, scenario, goalRows,
        goalExplanation, scenarioNotes: notes, origin: window.location.origin,
        generated,
      })
    } catch {
      setPdfError('PDF download could not be prepared. Use Print or save detailed PDF.')
    } finally {
      setPdfBusy(false)
    }
  }
  return <main className="mh">
    <header className="mh-hero">
      <p>CreditAI · Exhibition experience</p>
      <h1>My Money Health</h1>
      <p>Understand Your Money. Plan Your Next Move.</p>
      <small>About 2–3 minutes · Your entries stay in this browser tab.</small>
    </header>
    <section className="mh-panel mh-controls">
      <h2>1. Which best describes you?</h2>
      <div className="mh-grid">{profiles.map((item, index) =>
        <button key={item.name} aria-pressed={profile === index} onClick={() => { if (profile !== index) { clear(); select(index) } }}>{item.name}</button>)}</div>
    </section>
    {chosen && <form className="mh-panel mh-controls" onSubmit={event => { event.preventDefault(); run(entries) }} autoComplete="off">
      <h2>2. Enter your monthly numbers</h2>
      <div className="mh-actions">
        <button type="button" onClick={() => load(false)}>Load Example Input</button>
        <button type="button" onClick={() => load(true)}>Calculate Sample</button>
        <button type="button" onClick={clear}>Use My Own Numbers</button>
        <button type="button" onClick={() => { clear(); select(null) }}>Clear All</button>
      </div>
      {source && <p role="status"><strong>{provenance}</strong>. Edits stay in example mode until you switch to your own numbers.</p>}
      <div className="mh-grid">{chosen.fields.map(field => <div key={field.id}>
        <label htmlFor={field.id}>{field.label} · INR {field.required ? '(required)' : '(optional)'}</label>
        <input id={field.id} inputMode="decimal" required={field.required} aria-describedby={field.id + '-help'}
          value={entries[field.id] ?? ''} onChange={event => {
            setEntries({ ...entries, [field.id]: event.target.value })
            setResult(null)
            setError('')
          }} />
        <details id={field.id + '-help'}><summary>About this amount</summary>{field.help}</details>
      </div>)}</div>
      {error && <p role="alert">{error}</p>}
      <button className="mh-primary" type="submit">Calculate my money health</button>
    </form>}
    {chosen && result && <>
      <section className="mh-panel mh-report-only">
        <h2>My Money Health Report</h2>
        <p>{chosen.name} · {reportTime}</p>
        <strong>{provenance}</strong>
        <h3>5W1H</h3>
        <dl>
          <dt>Who</dt><dd>{chosen.name}</dd>
          <dt>What</dt><dd>Monthly cash flow, spending, debt commitments, accessible savings and scenarios.</dd>
          <dt>When</dt><dd>{reportTime}</dd>
          <dt>Where</dt><dd>{source ? 'Explicitly selected example, possibly edited.' : 'Amounts entered by the visitor.'}</dd>
          <dt>Why</dt><dd>Compare monthly commitments with available funds and see how changes affect the remaining balance.</dd>
          <dt>How</dt><dd>Add reported funds and each distinct expense category in integer paise. Subtract outflow from funds and calculate ratios only when the denominator is positive.</dd>
        </dl>
        <h3>Complete input register</h3>
        {result.register.map(field => <p key={field.id}><strong>{field.label}</strong> · {field.required ? 'Required' : 'Optional'} · INR · {field.amount === null ? 'Unavailable' : field.amount === 0 ? 'Zero' : 'Provided'} · {field.amount === null ? '—' : money(field.amount)} · {source ? (entries[field.id] === String(field.example) ? 'Example' : 'Edited example') : 'Self-reported'}<br />{field.help}</p>)}
      </section>
      <section className="mh-panel" aria-label="Financial dashboard">
        <h2>3. Your monthly picture</h2>
        <p>{chosen.name} · {provenance}</p>
        <div className="mh-grid">{metrics(result).map(([label, value, formula, meaning]) => <article key={label} className="mh-metric">
          <h3>{label}</h3><strong>{value}</strong><p>{meaning}</p>
          <details><summary>Calculation</summary>{formula} → {value}</details>
          <p className="mh-report-only">{formula} → {value}</p>
        </article>)}</div>
        <h3>What stands out</h3>
        <p>{result.balance < 0 ? 'Reported outflows exceed funds' : 'Reported funds cover outflows'} by {money(Math.abs(result.balance))}. This is the difference between {money(result.funds)} in funds and {money(result.outflow)} in total outflows for the reported month.</p>
        <p>Review the largest categories in the spending chart first when testing a reduction. Use the savings coverage figure to see what accessible savings would cover if monthly outflows stayed the same.</p>
        <div className="mh-grid">{charts(result, result).slice(0, 3).map(chart => <Chart key={chart.title} {...chart} />)}</div>
      </section>
      <section className="mh-panel">
        <h2>4. What-If Planner</h2>
        <p>Replace selected amounts to compare one hypothetical month with your baseline. Leave an amount blank to keep its original value.</p>
        <div className="mh-grid mh-controls">
          {chosen.fields.filter(f => ['funds', 'expense', 'goal'].includes(f.kind)).map(field => <label key={field.id}>
            {field.label} · INR <small>Baseline {entries[field.id] ? money(parseAmount(entries[field.id]) ?? 0) : 'unavailable'}</small>
            <input inputMode="decimal" value={changes[field.id] ?? ''} onChange={event => setChanges({ ...changes, [field.id]: event.target.value })} />
          </label>)}
          {scenarioInputs.map(([id, label]) => <label key={id}>{label} · INR
            <input inputMode="decimal" value={changes[id] ?? ''} onChange={event => setChanges({ ...changes, [id]: event.target.value })} />
          </label>)}
          {profile === 1 && <label>Adjust additional monthly EMI · INR
            <input type="range" min="0" max="50000" step="100"
              value={/^\d{1,10}(\.\d{1,2})?$/.test(changes.extra ?? '') ? Math.min(50000, Number(changes.extra)) : 0}
              onChange={event => setChanges({ ...changes, extra: event.target.value })} />
          </label>}
          {profile === 2 && entries.low?.trim() && <button onClick={() => setChanges({ ...changes, primary: entries.low })}>Use lower-income estimate</button>}
          <button onClick={() => setChanges({})}>Reset scenario</button>
        </div>
        {scenarioError && <p role="alert">{scenarioError}</p>}
        {scenario && <>
          <h3>Changed assumptions</h3>
          {changed.length ? <ul>{changed.map(field => {
            const before = result.register.find(item => item.id === field.id)?.amount ?? null
            return <li key={field.id}>{field.label} changed from {before === null ? 'unavailable' : money(before)} to {field.amount === null ? 'unavailable' : money(field.amount)}.</li>
          })}</ul> : <p>Baseline monthly inputs are currently used.</p>}
          <p>Balance changes by {money(scenario.balance - result.balance)} because funds change by {money(scenario.funds - result.funds)}, spending by {money(scenario.expenses - result.expenses)} and debt by {money(scenario.debt - result.debt)}.</p>
          <div className="mh-comparison">{metrics(scenario).map(([label, value], index) => <p key={label}>
            <strong>{label}</strong><br />Baseline {metrics(result)[index][1]} → Scenario {value}
          </p>)}</div>
          <Chart {...charts(result, scenario)[3]} />
          {goalRows.length > 0 && <>
            <Chart title="Purchase savings goal" rows={goalRows} />
            <p>{months === null ? 'Enter a positive contribution to project the timeline.' : `${months} whole months at ${money(parseAmount(changes.contribution) ?? 0)} per month.`} Timeline rounds up the remaining target divided by the planned contribution. It assumes a constant contribution and excludes interest and price changes.</p>
            {(parseAmount(changes.contribution) ?? 0) > Math.max(0, scenario.balance) && <p>The planned contribution exceeds the available scenario balance.</p>}
          </>}
          <p className="mh-report-only">Scenario inputs · {scenarioInputs.map(([id, label]) => `${label}: ${changes[id]?.trim() ? money(parseAmount(changes[id]) ?? 0) : 'Unavailable'}`).join(' · ') || 'Monthly replacements listed above.'}</p>
        </>}
      </section>
      <section className="mh-panel mh-report-only">
        <h2>Assumptions, privacy and limitations</h2>
        <p>The report uses a single reported or illustrative month. Missing optional amounts contribute zero to sums and appear as unavailable in the register. Ratios are displayed to two decimals. No identity data is needed and calculations run in the tab.</p>
        <p>For planning and education. This report provides no verified credit score, lending decision or financial guarantee. The other CreditAI dashboards demonstrate historical credit research.</p>
        <h3>Explore CreditAI</h3><a href={link.url}>{link.label} · {link.url}</a>
      </section>
    </>}
    <footer className="mh-panel mh-controls mh-actions">
            {result && <>
        <button className="mh-primary" disabled={!scenario || pdfBusy} onClick={() => { void download(new Date().toLocaleString('en-IN', { timeZoneName: 'short' })) }}>{pdfBusy ? 'Preparing PDF…' : 'Download PDF'}</button>
        <button disabled={!scenario} onClick={print}>Print or save detailed PDF</button>
      </>}
      {pdfError && <p role="alert">{pdfError}</p>}
      <a href="/">Explore Full CreditAI →</a>
    </footer>
  </main>
}
