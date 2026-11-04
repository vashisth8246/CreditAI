import MoneyPassport from './MoneyPassport'
import { loadSaved } from './moneyPassportStorage'
import { useEffect, useState } from 'react'
import { flushSync } from 'react-dom'
import { calculate, charts, example, metrics, money, parseAmount, profiles, scenarioPresets, timeline } from './moneyHealth'
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
  const [saved, setSaved] = useState(loadSaved)
  const [passportVisited, setPassportVisited] = useState(false)
  const [passportOpen, setPassportOpen] = useState(false)
  const [profile, select] = useState<number | null>(null)
  const [entries, setEntries] = useState<Entries>({})
  const [source, setSource] = useState(false)
  const [result, setResult] = useState<Result | null>(null)
  const [preset, setPreset] = useState('')
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
    setPreset('')
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
      setPreset('')
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
      if (target !== null) goalRows = [[profile === 2 ? 'Reserve target' : 'Purchase target', target], ['Savings explicitly allocated', Math.min(allocated, target)], ['Still to save', Math.max(0, target - allocated)]]
      scenario = modified
    } catch (failure) {
      scenario = null
      scenarioError = (failure as Error).message
    }
  }
  const provenance = source ? 'EXAMPLE INPUT — NOT A REAL VISITOR OR DATASET RECORD' : 'SELF-REPORTED'
  const print = () => window.print()
  const changed = result && scenario ? scenario.register.filter((field, index) => field.amount !== result.register[index].amount) : []
  const presets = result && profile !== null ? scenarioPresets(profile, result) : []
  const fieldGroups = [
    { title: 'Money coming in', icon: '↙', matches: (kind: string) => ['funds', 'low'].includes(kind) },
    { title: 'Essential spending', icon: '⌂', matches: (kind: string, id: string) => kind === 'expense' && !['discretionary', 'personal'].includes(id) || kind === 'expense' && id === 'personal' && profile === 2 },
    { title: 'Optional spending', icon: '◇', matches: (kind: string, id: string) => kind === 'expense' && (id === 'discretionary' || id === 'personal' && profile !== 2) },
    { title: 'Loans and debt', icon: '↗', matches: (kind: string) => kind === 'debt' },
    { title: 'Savings and goals', icon: '◎', matches: (kind: string) => ['savings', 'goal'].includes(kind) },
  ]
  const scenarioInputs = [
    ...(profile === 1 ? [['extra', 'Additional monthly EMI']] : []),
    ...([0, 2, 3].includes(profile ?? -1) ? [['target', profile === 2 ? 'Low-income reserve target' : 'Purchase target'], ['allocated', 'Savings explicitly allocated'], ['contribution', 'Planned monthly contribution']] : []),
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
    <div hidden={passportOpen}>
    <header className="mh-hero">
      <p>CreditAI · Exhibition experience</p>
      <h1>My Money Health</h1>
      <p>Understand Your Money. Plan Your Next Move.</p>
      <small>About 2–3 minutes · Your entries stay in this browser tab.</small>
    </header>
    <section className="mh-panel mh-controls">
      <h2>1. Which best describes you?</h2>
      <div className="mh-choice-grid">{profiles.map((item, index) =>
        <button className="mh-choice" key={item.name} aria-label={item.name} aria-pressed={profile === index}
          onClick={() => { if (profile !== index) { clear(); select(index) } }}>
          <span className="mh-choice-icon" aria-hidden="true">{['✎', '▣', '⌁', '◎'][index]}</span>
          <strong>{item.name}</strong>
          <small>{['Plan around pocket money, classes and everyday expenses.', 'See how pay, housing and loans fit together.', 'Plan for income that changes from month to month.', 'Make a plan around support or other available funds.'][index]}</small>
          {profile === index && <span className="mh-choice-check" aria-hidden="true">✓</span>}
        </button>)}</div>
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
      <p className="mh-hint">Leave optional amounts blank if you don’t know them. Enter zero if you know the amount is ₹0. Blank optional amounts add nothing to the total and appear as unavailable in the report.</p>
      {fieldGroups.map(group => {
        const fields = chosen.fields.filter(field => group.matches(field.kind, field.id))
        if (!fields.length) return null
        return <fieldset className="mh-fieldset" key={group.title}>
          <legend><span aria-hidden="true">{group.icon}</span> {group.title}</legend>
          <div className="mh-grid">{fields.map(field => <div key={field.id}>
            <label htmlFor={field.id}>{field.label} <small>{field.required ? 'Required' : 'Optional'}</small></label>
            <div className="mh-currency"><span aria-hidden="true">₹</span><input id={field.id} inputMode="decimal" required={field.required}
              aria-describedby={field.id + '-help'} value={entries[field.id] ?? ''} onChange={event => {
                setEntries({ ...entries, [field.id]: event.target.value }); setResult(null); setError('')
              }} /></div>
            <p id={field.id + '-help'} className="mh-hint">{field.help}</p>
          </div>)}</div>
        </fieldset>
      })}
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
        <p className="mh-kicker">04 · What-If Planner</p><h2>What if your money situation changes?</h2>
        <p>Choose an example change or enter your own amount. CreditAI recalculates your monthly finances instantly. These are hypothetical scenarios, not predictions.</p>
        <div className="mh-choice-grid mh-controls">{presets.map(option =>
          <button key={option.label} className="mh-choice" aria-pressed={preset === option.label}
            onClick={() => { setPreset(option.label); setChanges(option.changes) }}>
            <span className="mh-kicker">Example change</span><strong>{option.label}</strong>
          </button>)}</div>
        <div className="mh-actions mh-controls">
          {preset && <span role="status">Applied: {preset}. The comparison below shows the amounts that changed.</span>}
          <button onClick={() => { setChanges({}); setPreset('') }}>Reset scenario</button>
        </div>
        <details className="mh-custom mh-controls"><summary>Customize My Scenario</summary>
          <p className="mh-hint">Enter replacement amounts in INR. Leave a field blank to keep the original. Enter ₹0 to remove that amount from the scenario.</p>
        <div className="mh-grid mh-controls">
          {chosen.fields.filter(f => ['funds', 'expense', 'goal'].includes(f.kind)).map(field => <label key={field.id}>
            {field.label} · INR <small>Baseline {entries[field.id] ? money(parseAmount(entries[field.id]) ?? 0) : 'unavailable'}</small>
            <input inputMode="decimal" value={changes[field.id] ?? ''} onChange={event => { setPreset(''); setChanges({ ...changes, [field.id]: event.target.value }) }} />
            <small>{field.help}</small>
          </label>)}
          {scenarioInputs.map(([id, label]) => <label key={id}>{label} · INR
            <input inputMode="decimal" value={changes[id] ?? ''} onChange={event => { setPreset(''); setChanges({ ...changes, [id]: event.target.value }) }} />
            <small>{id === 'extra' ? 'Additional monthly loan payment, on top of existing payments.' : id === 'target' ? 'Total you want to have available for this goal.' : id === 'allocated' ? 'Existing accessible savings you choose to set aside for this goal.' : 'Amount you plan to add each month toward this goal.'}</small>
          </label>)}
          {profile === 1 && <label>Adjust additional monthly EMI · INR
            <input type="range" min="0" max="50000" step="100"
              value={/^\d{1,10}(\.\d{1,2})?$/.test(changes.extra ?? '') ? Math.min(50000, Number(changes.extra)) : 0}
              onChange={event => { setPreset(''); setChanges({ ...changes, extra: event.target.value }) }} />
          </label>}
          {profile === 2 && entries.low?.trim() && <button onClick={() => { setPreset(''); setChanges({ ...changes, primary: entries.low }) }}>Use lower-income estimate</button>}

        </div>
        </details>
        {scenarioError && <p role="alert">{scenarioError}</p>}
        {scenario && <>
          <h3>Changed assumptions</h3>
          {changed.length ? <ul>{changed.map(field => {
            const before = result.register.find(item => item.id === field.id)?.amount ?? null
            return <li key={field.id}>{field.label} changed from {before === null ? 'unavailable' : money(before)} to {field.amount === null ? 'unavailable' : money(field.amount)}.</li>
          })}</ul> : <p>Baseline monthly inputs are currently used.</p>}
          <p>Balance changes by {money(scenario.balance - result.balance)} because funds change by {money(scenario.funds - result.funds)}, spending by {money(scenario.expenses - result.expenses)} and debt by {money(scenario.debt - result.debt)}.</p>
          <div className="mh-comparison" key={JSON.stringify(changes)}>{metrics(scenario).map(([label, value], index) => <p className="mh-compare-card" key={label}>
            <strong>{label}</strong><span>Baseline {metrics(result)[index][1]}</span><b>Scenario {value}</b>
          </p>)}</div>
          <Chart {...charts(result, scenario)[3]} />
          {goalRows.length > 0 && <>
            <Chart title={profile === 2 ? "Low-income reserve goal" : "Purchase savings goal"} rows={goalRows} />
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
    <section className="mh-panel mh-controls">
      <h2>Money Challenge</h2>
      <p>Make a plan, record actual progress and keep a Money Passport on this browser if you choose.</p>
      <button onClick={() => { setPassportVisited(true); setPassportOpen(true); window.scrollTo(0, 0) }}>{saved.passports.length ? 'Continue My Money Challenge' : 'Start My Money Challenge'}</button>
    </section>
    <footer className="mh-panel mh-controls mh-actions">
            {result && <>
        <button className="mh-primary" disabled={!scenario || pdfBusy} onClick={() => { void download(new Date().toLocaleString('en-IN', { timeZoneName: 'short' })) }}>{pdfBusy ? 'Preparing PDF…' : 'Download PDF'}</button>
        <button disabled={!scenario} onClick={print}>Print or save detailed PDF</button>
      </>}
      {pdfError && <p role="alert">{pdfError}</p>}
      <a href="/">Explore Full CreditAI →</a>
    </footer>
    </div>
    {passportVisited && <div hidden={!passportOpen}>
      <MoneyPassport initial={saved} onSaved={setSaved} onBack={() => setPassportOpen(false)} onClear={() => { clear(); select(null); setPassportOpen(false) }}
        context={chosen && result ? { profile: chosen.name, balance: result.balance, example: source } : null} />
    </div>}
  </main>
}
