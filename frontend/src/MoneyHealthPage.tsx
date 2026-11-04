import MoneyPassport from './MoneyPassport'
import { loadSaved } from './moneyPassportStorage'
import { useEffect, useRef, useState } from 'react'
import { flushSync } from 'react-dom'
import { budgetAmount, calculate, calculateScenario, charts, example, metrics, money, parseAmount, profiles, scenarioPresets, timeline } from './moneyHealth'
import type { Entries, Field, Result } from './moneyHealth'
import { applicationLink, downloadMoneyHealthPdf } from './moneyHealthPdf'
import { Chart, Dashboard } from './MoneyHealthDashboard'
import { isOptionalExpense, scenarioSuggestions } from './moneyHealthAnalysis'
import type { ChallengeSuggestion } from './moneyHealthAnalysis'
import './moneyHealth.css'

type PlannerState = { mode: 'none' | 'preset' | 'custom'; preset: string; changes: Entries; applied: boolean }
const initialPlanner: PlannerState = { mode: 'none', preset: '', changes: {}, applied: false }

export default function MoneyHealth() {
  const [challenge, setChallenge] = useState<ChallengeSuggestion>()
  const [saved, setSaved] = useState(loadSaved)
  const [passportVisited, setPassportVisited] = useState(false)
  const [passportOpen, setPassportOpen] = useState(false)
  const [profile, select] = useState<number | null>(null)
  const [entries, setEntries] = useState<Entries>({})
  const [source, setSource] = useState(false)
  const [result, setResult] = useState<Result | null>(null)
  const focusPlanner = useRef(false)
  useEffect(() => {
    if (!result) return
    if (focusPlanner.current) {
      focusPlanner.current = false
      const heading = document.getElementById('money-health-planner-heading')
      heading?.focus({ preventScroll: true })
      heading?.closest('section')?.scrollIntoView({ block: 'start', behavior: 'instant' })
      return
    }
    const heading = document.getElementById('money-health-results')
    heading?.focus({ preventScroll: true })
    heading?.closest('header')?.scrollIntoView({ block: 'start', behavior: 'instant' })
  }, [result])
  const [planner, setPlanner] = useState(initialPlanner)
  const { mode, preset, changes, applied } = planner
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
    setChallenge(undefined)
    setEntries({})
    setSource(false)
    setResult(null)
    setPlanner(initialPlanner)
    setError('')
    setReportTime('')
    setPdfError('')
  }
  const run = (input: Entries) => {
    if (!chosen) return
    try {
      setResult(calculate(chosen.fields, input))
      setError('')
      setPlanner(initialPlanner)
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
  const loadPlannerExample = () => {
    if (!chosen || profile === null) return
    if (!source && Object.values(entries).some(value => value.trim()) &&
        !window.confirm('Replace your current personal entries with the example?')) return
    const input = example(chosen.fields)
    const baseline = calculate(chosen.fields, input)
    const first = scenarioPresets(profile, baseline)[0]
    clear()
    setEntries(input)
    setSource(true)
    focusPlanner.current = true
    setResult(baseline)
    setPlanner({ ...initialPlanner, mode: 'preset', preset: first.label, changes: first.changes })
  }
  let scenario = result
  let scenarioError = ''
  let goalRows: [string, number][] = []
  let months: number | null = null
  let hasPlanningInputs = false
  if (result && chosen) {
    try {
      const modified = calculateScenario(chosen.fields, entries, changes)
      const target = parseAmount(changes.target)
      const allocated = parseAmount(changes.allocated) ?? 0
      const contribution = parseAmount(changes.contribution) ?? 0
      if (allocated > modified.savings) throw new Error('Allocated savings cannot exceed accessible savings.')
      hasPlanningInputs = target !== null || allocated > 0 || contribution > 0
      months = timeline(target, allocated, contribution)
      if (target !== null) goalRows = [[profile === 2 ? 'Reserve target' : 'Purchase target', target], ['Savings explicitly allocated', Math.min(allocated, target)], ['Still to save', Math.max(0, target - allocated)]]
      scenario = modified
    } catch (failure) {
      scenario = null
      scenarioError = (failure as Error).message
    }
  }
  const openChallenge = (suggestion?: ChallengeSuggestion) => {
    setChallenge(suggestion ? { ...suggestion } : undefined)
    setPassportVisited(true)
    setPassportOpen(true)
    window.scrollTo(0, 0)
  }
  const provenance = source ? 'EXAMPLE INPUT — NOT A REAL VISITOR OR DATASET RECORD' : 'SELF-REPORTED'
  const print = () => window.print()
  const changed = result && scenario ? scenario.register.filter((field, index) => field.amount !== result.register[index].amount) : []
  const hasScenario = changed.length > 0 || hasPlanningInputs
  const suggestions = result && scenario && profile !== null ? scenarioSuggestions(result, scenario, profile) : []
  const reducedExpense = changed.length === 1 && changed[0].kind === 'expense' ? changed[0] : undefined
  const originalExpense = result?.register.find(field => field.id === reducedExpense?.id)?.amount
  const spendingDraft: ChallengeSuggestion | undefined = reducedExpense?.amount != null && originalExpense != null && reducedExpense.amount < originalExpense
    ? { kind: 'spending', category: reducedExpense.label, baseline: originalExpense, target: originalExpense - reducedExpense.amount }
    : undefined
  const presets = result && profile !== null ? scenarioPresets(profile, result).filter(option => Object.keys(option.changes).length) : []
  if (result && profile === 2 && entries.low?.trim()) presets.push({ label: 'Use lower-income estimate', changes: { primary: entries.low } })
  const selectedPreset = presets.find(option => option.label === preset)
  const selectedField = selectedPreset && Object.keys(selectedPreset.changes)[0]
  const selectedLabel = selectedField === 'extra' ? 'Additional monthly EMI' : selectedField === 'target' ? 'Savings target' :
    chosen?.fields.find(field => field.id === selectedField)?.label
  const baselineValue = selectedField === 'extra' || selectedField === 'target' ? '0' : selectedField ? entries[selectedField] : undefined
  const proposedValue = selectedField ? changes[selectedField] : undefined
  const displayAmount = (raw?: string) => {
    try { const amount = parseAmount(raw); return amount === null ? 'Unavailable' : money(amount) }
    catch { return 'Invalid amount' }
  }
  const editChange = (id: string, value: string, custom = false) => setPlanner(current => ({
    ...current,
    mode: custom ? 'custom' : current.mode,
    preset: custom ? '' : current.preset,
    applied: false,
    changes: { ...(custom && current.mode !== 'custom' ? {} : current.changes), [id]: value },
  }))
  const focusSection = (id: string) => requestAnimationFrame(() => {
    const heading = document.getElementById(id)
    heading?.focus({ preventScroll: true })
    heading?.scrollIntoView({ block: 'start', behavior: 'instant' })
  })
  const chooseMode = (next: 'preset' | 'custom') => {
    if (mode !== next) {
      if (mode === 'custom' && Object.values(changes).some(value => value.trim()) &&
          !window.confirm('Replace your custom scenario with a ready-made change?')) return
      setPlanner({ ...initialPlanner, mode: next })
    }
    if (next === 'custom') {
      requestAnimationFrame(() => {
        const editor = document.getElementById('money-health-budget') as HTMLDetailsElement | null
        if (editor) editor.open = true
      })
      focusSection('money-health-budget-heading')
    }
  }
  const renderEmiSlider = () => {
    let value = 0
    try { value = (parseAmount(changes.extra) ?? 0) / 100 } catch { /* the scenario shows the validation error */ }
    return <label>Adjust additional monthly EMI · INR
      <input type="range" min="0" max={Math.max(50000, value)} step="0.01" value={value}
        onChange={event => editChange('extra', event.target.value)} />
    </label>
  }
  const fieldGroups = [
    { title: 'Money coming in', icon: '↙', matches: (field: Field) => ['funds', 'low'].includes(field.kind) },
    { title: 'Essential spending', icon: '⌂', matches: (field: Field) => field.kind === 'expense' && !isOptionalExpense(field, profile ?? -1) },
    { title: 'Optional spending', icon: '◇', matches: (field: Field) => isOptionalExpense(field, profile ?? -1) },
    { title: 'Loans and debt', icon: '↗', matches: (field: Field) => field.kind === 'debt' },
    { title: 'Savings and goals', icon: '◎', matches: (field: Field) => ['savings', 'goal'].includes(field.kind) },
  ]
  const scenarioInputs = [
    ...(profile === 1 ? [['extra', 'Additional monthly EMI']] : []),
    ...([0, 2, 3].includes(profile ?? -1) ? [['target', profile === 2 ? 'Low-income reserve target' : 'Purchase target'], ['allocated', 'Savings explicitly allocated'], ['contribution', 'Planned monthly contribution']] : []),
  ]
  const budgetLabels: Record<string, string> = {
    primary: ['Pocket money or support', 'Take-home salary', 'Typical income', 'Family support or allowance'][profile ?? 0],
    additional: profile === 0 ? 'Part-time earnings' : 'Other income',
    housing: 'Rent or housing', food: 'Food', personal: 'Other living expenses',
    low: 'Lower-income estimate', business: 'Business expenses', debt: 'Existing monthly EMI',
  }
  const goalExplanation = goalRows.length === 0 ? '' :
    (months === null ? 'Enter a positive contribution to project the timeline.' :
      `${months} whole months at ${money(parseAmount(changes.contribution) ?? 0)} per month.`) +
    ' The timeline rounds up the remaining target divided by the planned contribution. It assumes a constant contribution and excludes interest and price changes.' +
    ((parseAmount(changes.contribution) ?? 0) > Math.max(0, scenario?.balance ?? 0) ? ' The planned contribution exceeds available scenario money by ' + money((parseAmount(changes.contribution) ?? 0) - Math.max(0, scenario?.balance ?? 0)) + '.' : '')
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
        profile: chosen.name, profileIndex: profile ?? 0, provenance, example: source, result, scenario, hasScenario, goalRows,
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
    {chosen && !result && <section className="mh-panel mh-controls" aria-label="What-If Planner example">
      <h2>Try the What-If Planner</h2>
      <p>Use the verified {chosen.name} example to see a before-and-after scenario.</p>
      <button type="button" className="mh-primary" onClick={loadPlannerExample}>Load Example</button>
    </section>}
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
        const fields = chosen.fields.filter(group.matches)
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
      <Dashboard result={result} profile={profile ?? 0} provenance={provenance} example={source} />
      <section className="mh-panel mh-planner" id="money-health-what-if">
        <div className="mh-actions mh-controls"><div><p className="mh-kicker">04 · What-If Planner</p><h2 id="money-health-planner-heading" tabIndex={-1}>What if your money situation changes?</h2></div>
          <button type="button" className="mh-primary" onClick={loadPlannerExample}>Load Example</button>
        </div>
        <p>{chosen.name} · {source ? 'Example baseline' : 'Your entered baseline'}. This comparison uses one hypothetical month.</p>
        <div className="mh-controls">
          <h3>Choose how you want to explore</h3>
          <div className="mh-actions">
            <button type="button" aria-pressed={mode === 'preset'} onClick={() => chooseMode('preset')}>Try a Ready-Made Change</button>
            <button type="button" aria-pressed={mode === 'custom'} onClick={() => chooseMode('custom')}>Create My Own Scenario</button>
          </div>
          {mode === 'preset' && <small>Creating your own scenario starts from your baseline amounts.</small>}
        </div>
        <div className="mh-planner-controls mh-controls">
          {mode === 'preset' && <label>Choose a ready-made change
            <select value={preset} onChange={event => {
              const next = presets.find(option => option.label === event.target.value)
              setPlanner({ ...initialPlanner, mode: 'preset', preset: next?.label ?? '', changes: next?.changes ?? {} })
            }}>
              <option value="">Choose a change</option>
              {['Save More', 'Spend Less', 'Earn More', 'Manage EMI', 'Emergency Planning'].map(group => {
                const options = presets.filter(option => {
                  const keys = Object.keys(option.changes)
                  const category = keys.includes('extra') ? 'Manage EMI' : keys.includes('goal') || (keys.includes('target') && profile !== 2) ? 'Save More' :
                    keys.includes('target') || /less support|earn 20% less|lower-income/i.test(option.label) ? 'Emergency Planning' :
                    keys.includes('primary') ? 'Earn More' : 'Spend Less'
                  return category === group
                })
                return options.length > 0 && <optgroup key={group} label={group}>{options.map(option => <option key={option.label}>{option.label}</option>)}</optgroup>
              })}
            </select>
          </label>}
          {selectedField && <div className="mh-planner-edit">
            <label>2. Adjust {selectedLabel}
              <input inputMode="decimal" value={proposedValue ?? ''} onChange={event => editChange(selectedField, event.target.value)} />
            </label>
            {selectedField === 'extra' && <>{renderEmiSlider()}<small>This payment is added to existing EMI.</small></>}
            <small>Before {displayAmount(baselineValue)} · After {displayAmount(proposedValue?.trim() ? proposedValue : baselineValue)}{(() => {
              try {
                const before = parseAmount(baselineValue)
                const after = parseAmount(proposedValue?.trim() ? proposedValue : baselineValue)
                return before === null || after === null ? '' : ' · Change ' + money(after - before)
              } catch { return '' }
            })()}</small>
            {Object.keys(selectedPreset.changes).length > 1 && <small>The other changes in this preset stay in place.</small>}
          </div>}
        </div>
        {mode !== 'preset' && <details id="money-health-budget" className="mh-custom mh-controls mh-budget"><summary id="money-health-budget-heading">Customize Your Monthly Budget</summary>
          <p className="mh-hint">Change any amount to see how your monthly money situation changes.</p>
          {[
            { title: 'Monthly Income', fields: chosen.fields.filter(f => f.kind === 'funds' || f.kind === 'low').map(f => [f.id, f.label]) },
            { title: 'Monthly Expenses', fields: chosen.fields.filter(f => f.kind === 'expense').map(f => [f.id, f.label]) },
            { title: 'Savings & Loans', fields: [...chosen.fields.filter(f => ['goal', 'debt', 'savings'].includes(f.kind)).map(f => [f.id, f.label]),
              ...scenarioInputs.map(([id, label]) => [id, id === 'extra' ? 'Extra Monthly Loan Payment' : label])] },
          ].map(group => <fieldset className="mh-budget-group" key={group.title}>
            <legend>{group.title}</legend>
            <div className="mh-budget-grid">{group.fields.map(([id, label]) => {
              const value = budgetAmount(entries, changes, id)
              let invalid = ''
              try { parseAmount(value) } catch (failure) { invalid = (failure as Error).message }
              const hint = id === 'extra' ? 'An additional monthly payment on top of your existing EMIs.' : ''
              return <div key={id}>
                <label htmlFor={'budget-' + id}>{budgetLabels[id] ?? label} (₹)</label>
                <div className="mh-currency"><span aria-hidden="true">₹</span><input id={'budget-' + id} inputMode="decimal"
                  aria-invalid={Boolean(invalid)} aria-describedby={invalid || hint ? 'budget-hint-' + id : undefined}
                  value={value} onChange={event => editChange(id, event.target.value, true)}
                  onBlur={() => { if (!value.trim()) setPlanner(current => {
                    const next = { ...current.changes }; delete next[id]; return { ...current, changes: next }
                  }) }} /></div>
                {(invalid || hint) && <small id={'budget-hint-' + id} className={invalid ? 'mh-budget-error' : 'mh-hint'}>{invalid || hint}</small>}
              </div>
            })}</div>
          </fieldset>)}
          <div className="mh-actions">
            <button type="button" className="mh-primary" disabled={!scenario || !hasScenario} aria-describedby="money-health-apply-help" onClick={() => {
              if (!scenario || !hasScenario) return
              setPlanner(current => ({ ...current, applied: true }))
              focusSection('money-health-comparison-heading')
            }}>Apply My Changes</button>
            <button type="button" onClick={() => setPlanner({ ...initialPlanner, mode: 'custom' })}>Reset Changes</button>
            {profile === 2 && (changes.low ?? entries.low)?.trim() && <button type="button" onClick={() => {
              editChange('primary', budgetAmount(entries, changes, 'low'), true)
            }}>Use lower-income estimate</button>}
          </div>
          <p id="money-health-apply-help" className="mh-hint">{scenarioError ? 'Correct the highlighted amounts before applying.' :
            !hasScenario ? 'Change at least one amount to apply a simulation.' : 'The comparison updates as you edit. Apply confirms the simulation for this session.'}</p>
        </details>}

        {scenarioError && <p role="alert">{scenarioError}</p>}
        {scenario && <div className="mh-planner-result" aria-label="Before and after monthly balance">
          <h3 id="money-health-comparison-heading" tabIndex={-1}>Before and after</h3>
          <div role="status">{applied ? `Custom scenario applied. Monthly balance: ${money(scenario.balance)}.` : ''}</div>
          <dl><div><dt>Before</dt><dd>{money(result.balance)}</dd></div><div><dt>After</dt><dd>{money(scenario.balance)}</dd></div>
            <div><dt>Monthly change</dt><dd data-direction={Math.sign(scenario.balance - result.balance)}>{money(scenario.balance - result.balance)}</dd></div></dl>
          <p>Monthly income or support: {money(result.funds)} before · {money(scenario.funds)} after.<br />
            Monthly expenses including debt: {money(result.outflow)} before · {money(scenario.outflow)} after.</p>
          <p>{!hasScenario ? 'No changes yet. Adjust an amount to see what happens.' :
            scenario.balance === result.balance ? (scenario.goal ?? 0) > (result.goal ?? 0) ? 'Your savings target has increased, but the money remaining after expenses is unchanged.' : 'Your monthly balance stays the same.' :
            `Your monthly balance ${scenario.balance > result.balance ? 'increases' : 'decreases'} by ${money(Math.abs(scenario.balance - result.balance))} in this simulation.`}</p>
          <small>{metrics(scenario).filter(([label]) => ['Expense ratio', 'Savings goal', 'Savings coverage'].includes(label)).map(([label, value]) => label + ': ' + value).join(' · ')}</small>
        </div>}
        <div className="mh-actions mh-controls"><button type="button" onClick={() => setPlanner(initialPlanner)}>Reset Scenario</button>
          {spendingDraft && <button type="button" onClick={() => openChallenge(spendingDraft)}>Review a Money Challenge draft</button>}
        </div>

        {scenario && hasScenario && <>
          <h3>Changed assumptions</h3>
          {changed.length ? <ul>{changed.map(field => {
            const before = result.register.find(item => item.id === field.id)?.amount ?? null
            return <li key={field.id}>{field.label} changed from {before === null ? 'unavailable' : money(before)} to {field.amount === null ? 'unavailable' : money(field.amount)}.</li>
          })}</ul> : <p>Baseline monthly inputs are currently used.</p>}
          <p>Balance changes by {money(scenario.balance - result.balance)} because funds change by {money(scenario.funds - result.funds)}, spending by {money(scenario.expenses - result.expenses)} and debt by {money(scenario.debt - result.debt)}.</p>
          <div className="mh-report-only">{metrics(scenario).map(([label, value], index) =>
            <p key={label}>{label} · Baseline {metrics(result)[index][1]} · Scenario {value}</p>)}</div>
          <Chart {...charts(result, scenario)[3]} insight={`Monthly balance changes by ${money(scenario.balance - result.balance)}.`} />
          {goalRows.length > 0 && <>
            <Chart title={profile === 2 ? "Low-income reserve goal" : "Purchase savings goal"} rows={goalRows} />
            <p>{months === null ? 'Enter a positive contribution to project the timeline.' : `${months} whole months at ${money(parseAmount(changes.contribution) ?? 0)} per month.`} Timeline rounds up the remaining target divided by the planned contribution. It assumes a constant contribution and excludes interest and price changes.</p>
            {(parseAmount(changes.contribution) ?? 0) > Math.max(0, scenario.balance) && <p>The planned contribution exceeds available scenario money by {money((parseAmount(changes.contribution) ?? 0) - Math.max(0, scenario.balance))}.</p>}
          </>}
          <p className="mh-report-only">Scenario inputs · {scenarioInputs.map(([id, label]) => `${label}: ${changes[id]?.trim() ? money(parseAmount(changes[id]) ?? 0) : 'Unavailable'}`).join(' · ') || 'Monthly replacements listed above.'}</p>
        </>}
      </section>
      <section className="mh-panel" id="money-health-recommendations">
        <h2>What could you improve?</h2>
        {hasScenario && <p>Based on your current simulation.</p>}
        {suggestions.length ? <div className="mh-grid">{suggestions.map(item =>
          <article className="mh-metric" key={item.text}>
            <p>{item.text}</p>
            <div className="mh-actions mh-controls">
              {item.changes && <button onClick={() => {
                const next = item.changes ?? {}
                if (mode === 'custom' && Object.keys(next).some(key => changes[key]?.trim()) &&
                    !window.confirm('Replace the overlapping amounts in your custom scenario?')) return
                setPlanner({ ...initialPlanner, mode: 'custom', changes: { ...changes, ...next }, applied: true })
                focusSection('money-health-comparison-heading')
              }}>Apply this What-If</button>}
              {item.challenge && <button onClick={() => openChallenge(item.challenge)}>Turn an improvement into a Money Challenge</button>}
            </div>
          </article>)}</div> : <p>Review the entered amounts before choosing a next step.</p>}
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
      <button onClick={() => openChallenge()}>{saved.passports.length ? 'Continue My Money Challenge' : 'Start My Money Challenge'}</button>
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
      <MoneyPassport suggestion={challenge} initial={saved} onSaved={setSaved} onBack={() => setPassportOpen(false)} onClear={() => { clear(); select(null); setPassportOpen(false) }}
        context={chosen && result ? { profile: chosen.name, balance: result.balance, example: source } : null} />
    </div>}
  </main>
}
