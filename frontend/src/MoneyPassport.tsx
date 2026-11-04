import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { money, parseAmount } from './moneyHealth'
import { importPassport, progress, readPassports, savePassports, storageKey, today, types, validatePassport } from './moneyChallenge'
import type { Entry, Kind, Passport } from './moneyChallenge'
import { downloadPassport, saveFile } from './moneyPassportPdf'

export type Context = { profile: string; example: boolean; balance: number }
import type { loadSaved } from './moneyPassportStorage'
const value = (form: FormData, key: string) => String(form.get(key) ?? '').trim()
const amount = (form: FormData, key: string) => parseAmount(value(form, key)) ?? 0
const message = (error: unknown) => error instanceof Error ? error.message : 'The operation failed.'

function Amount({ name, label, help, required = false }: { name: string; label: string; help: string; required?: boolean }) {
  return <label>{label} · INR<input name={name} inputMode="decimal" required={required} /><small>{help}</small></label>
}

export default function MoneyPassport({ initial, context, onBack, onSaved, onClear }: {
  initial: ReturnType<typeof loadSaved>; context: Context | null; onBack: () => void
  onSaved: (state: ReturnType<typeof loadSaved>) => void; onClear: () => void
}) {
  const recordPanel = useRef<HTMLDetailsElement>(null)
  const [passports, setPassports] = useState(initial.passports)
  const [persisted, setPersisted] = useState(initial.passports)
  const [active, setActive] = useState(initial.passports[0]?.id ?? '')
  const [kind, setKind] = useState<Kind>('savings')
  const [preview, setPreview] = useState<Passport | null>(null)
  const [consent, setConsent] = useState(false)
  const [entryId, setEntryId] = useState('')
  const [status, setStatus] = useState('')
  const [error, setError] = useState(initial.error)
  const [busy, setBusy] = useState(false)
  const date = today()
  const passport = passports.find(item => item.id === active)
  const summary = passport ? progress(passport, date) : null
  const edit = passport?.entries.find(entry => entry.id === entryId)
  function attempt(action: () => void) {
    setError('')
    setStatus('')
    try { action() } catch (failure) { setError(message(failure)) }
  }
  function persist(items: Passport[], permission: boolean) {
    const current = readPassports(localStorage, today())
    if (JSON.stringify(current) !== JSON.stringify(persisted)) {
      throw Error('Saved passports changed in another tab. Export your active passport, then reload before saving.')
    }
    savePassports(localStorage, items, permission)
    setPersisted(items)
    onSaved({ passports: items, error: '' })
  }
  function createPreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    attempt(() => {
      const form = new FormData(event.currentTarget)
      const essential = amount(form, 'essential')
      const coverage = value(form, 'coverage')
      if (coverage && !/^[1-9]\d?$/.test(coverage)) throw Error('Coverage must be a whole number of months from 1 to 99.')
      if (coverage && amount(form, 'target')) throw Error('Choose a target amount or coverage duration.')
      const useContext = !!form.get('context') && !!context
      setPreview(validatePassport({
        version: 1, id: crypto.randomUUID(), kind, name: value(form, 'name'), created: date,
        end: value(form, 'end'), target: coverage ? essential * Number(coverage) : amount(form, 'target'),
        start: amount(form, 'start'), planned: amount(form, 'planned'), frequency: value(form, 'frequency') || 'monthly',
        baseline: amount(form, 'baseline'), essential, category: value(form, 'category'),
        profile: useContext ? context.profile : '', example: useContext ? context.example : false,
        snapshot: useContext ? { balance: context.balance } : null, entries: [],
      }, date))
    })
  }
  function add(item: Passport) {
    if (passports.length >= 20) throw Error('Remove a passport before adding another.')
    if (passports.some(existing => existing.id === item.id)) throw Error('This passport is already open. Existing records were preserved.')
    setPassports([...passports, item])
    setActive(item.id)
    setConsent(false)
    setPreview(null)
    setEntryId('')
  }
  function replaceEntries(entries: Entry[]) {
    if (!passport) return
    const updated = validatePassport({ ...passport, entries }, date)
    const next = passports.map(item => item.id === updated.id ? updated : item)
    if (persisted.some(item => item.id === updated.id)) persist(persisted.map(item => item.id === updated.id ? updated : item), true)
    setPassports(next)
    setEntryId('')
  }
  function updateEntry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!passport) return
    const form = event.currentTarget
    attempt(() => {
      const fields = new FormData(form)
      if (!value(fields, 'amount')) throw Error('Enter the actual amount.')
      if (edit && !window.confirm('Save the changes to this recorded entry?')) return
      const entry = {
        id: edit?.id ?? crypto.randomUUID(), date: value(fields, 'date'), amount: amount(fields, 'amount'),
        kind: (passport.kind === 'spending' ? 'spending' : value(fields, 'entryKind')) as Entry['kind'], note: value(fields, 'note'),
      }
      replaceEntries(edit ? passport.entries.map(item => item.id === edit.id ? entry : item) : [...passport.entries, entry])
      form.reset()
      setStatus('Entry recorded.')
    })
  }
  return <section className="mh-panel" aria-label="Money Passport">
    <div className="mh-actions">
      <button onClick={onBack}>Back to My Money Health</button>
      <button onClick={() => { setActive(''); setConsent(false); setPreview(null); setError(''); setStatus('') }}>New challenge</button>
    </div>
    <h2>Money Passport</h2>
    <p>This passport is saved on this device/browser only after you consent and save it. Clearing browser data or changing devices may remove it. Export a backup to restore it later. Anyone using this browser profile can open saved passports.</p>
    {passports.length > 0 && <label>Choose passport <select value={active} onChange={event => { setActive(event.target.value); setConsent(false); setEntryId(''); setPreview(null); setStatus(''); setError('') }}>
      <option value="">New challenge</option>{passports.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
    </select></label>}
    {!passport && <form key={kind} onSubmit={createPreview}>
      <h3>Plan a challenge</h3>
      <p>Pick a goal, review the numbers, then decide whether to start.</p>
      <div className="mh-choice-grid">{(Object.keys(types) as Kind[]).map((option, index) =>
        <button type="button" className="mh-choice" key={option} aria-label={types[option]} aria-pressed={kind === option}
          onClick={() => { setKind(option); setPreview(null) }}>
          <span className="mh-choice-icon" aria-hidden="true">{['◎', '↘', '◇'][index]}</span>
          <strong>{types[option]}</strong>
          <small>{['Put money aside for something specific, like ₹5,000 for a course.', 'Track a category and spend less, like ₹300 less on takeout.', 'Build accessible savings for an unexpected expense or a slow month.'][index]}</small>
          {kind === option && <span className="mh-choice-check" aria-hidden="true">✓</span>}
        </button>)}</div>
      <div className="mh-grid">
        <label>Challenge name<input name="name" required maxLength={80} /><small>Use a goal label without personal identifiers.</small></label>
        {kind === 'spending' ? <>
          <label>Spending category<input name="category" required maxLength={60} /><small>Every spending entry uses this category.</small></label>
          <Amount name="baseline" label="Baseline spending" help="Your usual spending for a comparable period." required />
          <Amount name="target" label="Reduction target" help="How much less you want to spend than the baseline." required />
        </> : <>
          <Amount name="target" label="Target amount" help={kind === 'emergency' ? 'Leave blank if you set a coverage duration below.' : 'The total amount you want to reach.'} required={kind === 'savings'} />
          <Amount name="start" label="Starting allocation" help="Only include money you have explicitly set aside. Blank means zero." />
          <Amount name="planned" label="Planned contribution" help="The amount you plan to add per period. This does not record an actual contribution." />
          <label>Contribution frequency<select name="frequency"><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option></select><small>First planned contribution is one period after the projection date.</small></label>
        </>}
        {kind === 'emergency' && <>
          <Amount name="essential" label="Monthly essential expenses" help="Used to calculate coverage. Enter a positive amount to use a duration target." />
          <label>Coverage target in whole months<input name="coverage" inputMode="numeric" /><small>Optional alternative to an INR target.</small></label>
        </>}
        <label>{kind === 'spending' ? 'Last day of tracking' : 'Target date (optional)'}<input name="end" type="date" min={date} required={kind === 'spending'} />
          <small>{kind === 'spending' ? 'Track from today through this date, inclusive.' : 'Used to calculate the contribution required by your deadline.'}</small></label>
        {context && <label><input type="checkbox" name="context" /> Retain the {context.example ? 'example' : 'personal'} profile and monthly balance ({money(context.balance)}) for this challenge.<small>Optional. This snapshot will appear in your backup and report.</small></label>}
      </div>
      <button type="submit">Review plan</button>
    </form>}
    {preview && <div className="mh-panel">
      <h3>Confirm your plan</h3>
      <p>{preview.name} · {types[preview.kind]} · {preview.example ? 'EXAMPLE-BASED PLAN' : 'VISITOR-ENTERED PLAN'}</p>
      <p>{preview.kind === 'spending'
        ? `Reduce ${preview.category} from ${money(preview.baseline)} by ${money(preview.target)} through ${preview.end}.`
        : `Target ${money(preview.target)} with ${money(preview.start)} allocated and ${money(preview.planned)} contributed ${preview.frequency}.`}</p>
      <p>There are no recorded entries. The challenge opens in this tab until you save it.</p>
      <button className="mh-primary" onClick={() => attempt(() => add(preview))}>Confirm challenge</button>
    </div>}
    {passport && summary && <>
      <header className="mh-passport-hero">
        <div>
          <p className="mh-kicker">{types[passport.kind]} · Money Passport</p>
          <h3>{passport.name}</h3>
          <p>Created {passport.created} · {passport.example ? 'EXAMPLE-BASED PLAN' : 'VISITOR-ENTERED PLAN'}</p>
          <strong className="mh-status">{summary.status}</strong>
        </div>
        <div className="mh-ring" role="img" aria-label={summary.percentage.toFixed(2) + '% of target'}>
          <svg viewBox="0 0 120 120" aria-hidden="true">
            <circle cx="60" cy="60" r="51" fill="none" stroke="#ffffff35" strokeWidth="8" />
            <circle className="mh-ring-value" cx="60" cy="60" r="51" fill="none" stroke="#9cf5ce" strokeWidth="8"
              pathLength="100" strokeDasharray={summary.percentage + ' 100'} transform="rotate(-90 60 60)" />
          </svg>
          <strong>{summary.percentage.toFixed(1)}%</strong>
          <progress hidden max={100} value={summary.percentage} aria-label="Challenge progress" />
        </div>
        <dl className="mh-passport-stats">
          <div><dt>{passport.kind === 'spending' ? 'Reduction goal' : 'Target'}</dt><dd>{money(passport.target)}</dd></div>
          <div><dt>{passport.kind === 'spending' ? 'Recorded spending' : 'Current recorded amount'}</dt><dd>{money(summary.current)}</dd></div>
          <div><dt>{passport.kind === 'spending' ? 'Above limit' : 'Remaining'}</dt><dd>{money(summary.remaining)}</dd></div>
          <div><dt>Next milestone</dt><dd>{summary.milestones.find(item => !item.achieved)?.percent ?? 'All reached'}{summary.milestones.some(item => !item.achieved) ? '%' : ''}</dd></div>
        </dl>
      </header>
      <div className="mh-actions mh-passport-actions">
        <button className="mh-primary" onClick={() => { if (recordPanel.current) { recordPanel.current.open = true; recordPanel.current.scrollIntoView({ block: 'nearest' }); recordPanel.current.querySelector('input')?.focus() } }}>Record Progress</button>
        <button disabled={busy} onClick={async () => {
          setBusy(true)
          setError('')
          try { await downloadPassport(passport, date, window.location.origin) }
          catch (failure) { setError(message(failure)) }
          finally { setBusy(false) }
        }}>{busy ? 'Preparing PDF…' : 'Download Money Passport PDF'}</button>
        <a href="#manage-passport" onClick={event => {
          event.preventDefault()
          const panel = document.getElementById('manage-passport') as HTMLDetailsElement | null
          if (panel) { panel.open = true; panel.scrollIntoView({ block: 'nearest' }); panel.querySelector('summary')?.focus() }
        }}>Manage Passport</a>
      </div>
      <details className="mh-custom"><summary>Plan and calculations</summary>
      {passport.kind === 'spending' ? <p>{passport.category} · Limit {money(summary.limit)} · Baseline less actual {money(summary.comparison)} · Actual less limit {money(summary.targetDifference)}. This comparison does not show a deposit or money set aside. Milestones are evaluated after the period ends and require recorded activity.</p> :
        <p>Starting allocation {money(passport.start)} · Planned {money(passport.planned)} {passport.frequency}.
          {summary.eta && ` Estimated completion ${summary.eta} at the planned pace.`}
          {summary.required !== null && ` To reach ${passport.end}, plan ${money(summary.required)} per period across ${summary.periods} remaining periods.`}
          {summary.feasible !== null && ` Planned contributions ${summary.feasible ? 'fit' : 'exceed'} the retained monthly balance using a 30-day month. Actual capacity may differ.`}
          {summary.coverage !== null && ` Current emergency coverage: ${summary.coverage.toFixed(2)} months at ${money(passport.essential)} per month.`}</p>}
      <p><strong>Next step</strong> · {passport.kind === 'spending' ? (summary.closed ? 'Review the recorded spending against your limit.' : 'Record spending for this category as it occurs.') : summary.remaining ? 'Record your next actual contribution when it occurs.' : 'Review the balance after any future withdrawals.'}</p>
      </details>
      <h4>Planned milestones</h4>
      <ul className="mh-milestones">{summary.milestones.map(milestone => <li className={milestone.achieved ? 'is-reached' : undefined} key={milestone.percent}>{milestone.percent}% · {money(milestone.threshold)} · {milestone.achieved ? 'Reached' : 'Pending'}</li>)}</ul>
      <h4>Recorded timeline</h4>
      <div className="mh-chart">
        <p>{passport.kind === 'spending' ? 'Spending limit' : 'Target balance'}: {money(summary.limit)} · Recorded: {money(summary.current)}</p>
        <meter min={0} max={Math.max(summary.limit, summary.current, 1)} value={summary.current} aria-label="Recorded amount compared with target" />
      </div>
      {!summary.timeline.length && <p>No entries yet. Add an actual entry when it occurs.</p>}
      {summary.timeline.length > 0 && <div className="mh-chart">
        {summary.timeline.map(entry => <div key={entry.id}>
          <p>{entry.date} · {entry.kind} · {money(entry.amount)} · Running total {money(entry.cumulative)}{entry.note ? ' · ' + entry.note : ''}</p>
          <meter min={0} max={Math.max(summary.limit, ...summary.timeline.map(point => point.cumulative), 1)} value={entry.cumulative} aria-label={entry.date + ' running total'} />
          <div className="mh-actions"><button onClick={() => { setEntryId(entry.id); if (recordPanel.current) { recordPanel.current.open = true; recordPanel.current.scrollIntoView({ block: 'nearest' }) } }}>Edit entry</button>
            <button onClick={() => attempt(() => { if (window.confirm('Delete this recorded entry?')) replaceEntries(passport.entries.filter(item => item.id !== entry.id)) })}>Delete entry</button></div>
        </div>)}
      </div>}
      <details className="mh-custom" ref={recordPanel}><summary>Record an entry</summary>
      <form key={passport.id + entryId} onSubmit={updateEntry}>
        <h4>{edit ? 'Edit recorded entry' : 'Record actual progress'}</h4>
        <div className="mh-grid">
          <label>Date<input name="date" type="date" required min={passport.created} max={passport.kind === 'spending' && passport.end < date ? passport.end : date} defaultValue={edit?.date ?? (passport.kind === 'spending' && passport.end < date ? passport.end : date)} /></label>
          {passport.kind !== 'spending' && <label>Entry type<select name="entryKind" defaultValue={edit?.kind ?? 'contribution'}><option value="contribution">Contribution</option><option value="withdrawal">Withdrawal</option></select></label>}
          <label>Actual amount · INR<input name="amount" inputMode="decimal" required defaultValue={edit ? (edit.amount / 100).toFixed(2) : ''} /></label>
          <label>Note (optional)<input name="note" maxLength={160} defaultValue={edit?.note ?? ''} /></label>
        </div>
        <button type="submit">{edit ? 'Save edit' : 'Add entry'}</button>
        {edit && <button type="button" onClick={() => setEntryId('')}>Cancel edit</button>}
      </form>
      </details>
    </>}
    <details id="manage-passport" className="mh-custom mh-manage"><summary>Manage Passport</summary>
      <p>Passports are saved only in this browser after you consent. Export a JSON backup before clearing browser data or switching devices. Anyone using this browser profile can open saved passports.</p>
      <label className="mh-file-picker"><span>Import backup</span><input type="file" accept=".json,application/json" onChange={async event => {
        const file = event.currentTarget.files?.[0]
        event.currentTarget.value = ''
        if (!file) return
        try {
          if (file.size > 250000) throw Error('Passport file is too large.')
          const imported = importPassport(await file.text(), today())
          attempt(() => { add(imported); setStatus('Backup opened. Save it to keep it in this browser.') })
        } catch (failure) { setError(message(failure)) }
      }} /></label>
      {passport && <>
      <p>{persisted.some(item => item.id === passport.id) ? 'Saved in this browser. Entry changes save automatically.' : 'This passport is currently in this tab only.'}</p>
      <label><input type="checkbox" checked={consent} onChange={event => setConsent(event.target.checked)} /> I consent to saving this passport in this browser.</label>
      <div className="mh-actions">
        <button disabled={!consent} onClick={() => attempt(() => {
          persist([...persisted.filter(item => item.id !== passport.id), passport], consent)
          setStatus('Passport saved on this browser.')
        })}>Save Money Passport</button>
        <button onClick={() => saveFile(new Blob([JSON.stringify(passport, null, 2)], { type: 'application/json' }), 'CreditAI-Money-Passport.json')}>Export Passport</button>
        <button onClick={() => attempt(() => {
          if (!window.confirm('Delete this passport? Cancel to export a backup first.')) return
          if (persisted.some(item => item.id === passport.id)) persist(persisted.filter(item => item.id !== passport.id), true)
          setPassports(passports.filter(item => item.id !== passport.id))
          setActive('')
        })}>Delete My Passport</button>
      </div>
    </>}
    <div className="mh-actions">
      <button onClick={() => attempt(() => {
        if (!window.confirm('Clear all Money Health and Passport data? Cancel to export backups first.')) return
        localStorage.removeItem(storageKey)
        setPassports([])
        setPersisted([])
        setActive('')
        setPreview(null)
        setConsent(false)
        setEntryId('')
        onSaved({ passports: [], error: '' })
        onClear()
      })}>Clear All Data</button>
    </div>
    </details>
    <div className="mh-actions"><a href="/">Explore Full CreditAI →</a></div>
    {status && <p role="status">{status}</p>}
    {error && <p role="alert">{error}</p>}
  </section>
}
