import { useEffect, useRef, useState } from 'react'
import { historyFields, historyLimits, monthIndex, periodAt, type MonthlyRecord, type inspectHistory } from './monthlyHistory'
import './monthlyHistory.css'

const labels = { status: 'Repayment status', bill: 'Bill amount (NT$)', paid: 'Amount paid (NT$)' }
const statuses = ['No consumption', 'Paid duly', 'Revolving credit']
const describe = (code: number) => statuses[code + 2] ?? (code + (code === 1 ? ' month late' : ' months late'))
const hasData = ({ status, bill, paid }: MonthlyRecord) => Boolean(status || bill || paid)

export function MonthlyHistoryEditor({ records, review, onChange, loadExample }: {
  records: MonthlyRecord[]
  review: ReturnType<typeof inspectHistory>
  onChange: (records: MonthlyRecord[]) => void
  loadExample: () => void
}) {
  const nextId = useRef(7)
  const addButton = useRef<HTMLButtonElement>(null)
  const confirmButton = useRef<HTMLButtonElement>(null)
  const [confirm, setConfirm] = useState<number | 'all' | 'example' | null>(null)
  useEffect(() => {
    if (confirm !== null) confirmButton.current?.focus()
  }, [confirm])
  function remove(id: number) {
    onChange(records.filter(record => record.id !== id))
    setConfirm(null)
    addButton.current?.focus()
  }
  const confirmation = confirm === null ? null : <div className="monthly-confirm" role="group" aria-label="Confirm history change">
    <span>{confirm === 'example' ? 'Replace the monthly history with synthetic example data?' : confirm === 'all' ? 'Clear all monthly records?' : 'Remove this entered monthly record?'}</span>
    <button ref={confirmButton} type="button" className="button-secondary" onClick={() => {
      if (confirm === 'example') loadExample()
      else if (confirm === 'all') onChange([])
      else remove(confirm)
      setConfirm(null)
      addButton.current?.focus()
    }}>Confirm</button>
    <button type="button" className="button-quiet" onClick={() => {
      setConfirm(null)
      if (typeof confirm === 'number') document.getElementById('month-remove-' + confirm)?.focus()
      else addButton.current?.focus()
    }}>Cancel</button>
  </div>
  return <section className="feature-section monthly-history" aria-labelledby="monthly-history-heading">
    <h4 className="feature-section-title" id="monthly-history-heading">2. Monthly credit history</h4>
    <div className="monthly-readiness" role="status">
      <strong>{records.length} entered · {review.complete} complete · {review.window.length ? review.missing.length : 6} missing periods</strong>
      <p>{review.ready ? 'Ready for research inference.' : records.length < 6 ? 'Insufficient history. Add six complete consecutive months to run a prediction.' : 'History requires review. Complete the latest six consecutive months and resolve invalid or duplicated reporting periods.'}</p>
      {!!review.missing.length && <p>Missing periods: {review.missing.join(', ')}.</p>}
      {review.ready && <p>Research window: {review.window.at(-1)} through {review.window[0]}.{records.length > 6 ? ' Older records remain visible for context and are excluded from inference.' : ''}</p>}
    </div>
    <div className="monthly-actions">
      <button ref={addButton} type="button" className="button-secondary" disabled={records.length >= 120} onClick={() => {
        const indexes = records.flatMap(record => { const index = monthIndex(record.period); return index === null ? [] : [index] })
        const previous = indexes.length ? Math.min(...indexes) - 1 : 2005 * 12 + 8
        const id = nextId.current++
        onChange([...records, { id, period: previous >= 12 ? periodAt(previous) : '', status: '', bill: '', paid: '' }])
        setConfirm(null)
        requestAnimationFrame(() => document.getElementById('month-period-' + id)?.focus())
      }}>+ Add Month</button>
      <button type="button" className="button-secondary" onClick={() => {
        if (records.some(hasData)) setConfirm('example')
        else loadExample()
      }}>Load 6-Month Research Example</button>
      <button type="button" className="button-quiet" disabled={!records.length} onClick={() => setConfirm('all')}>Clear History</button>
    </div>
    <details className="monthly-help">
      <summary>Repayment codes and research window</summary>
      <p>−2: No consumption · −1: Paid duly · 0: Revolving credit · 1–9: Months late.</p>
      <p>Use whole NT$ amounts. Negative bills can represent a credit balance. The latest six consecutive months map onto the September–April 2005 model positions for research only.</p>
    </details>
    {typeof confirm !== 'number' && confirmation}
    {records.length > 0 && <div className="monthly-columns" aria-hidden="true">
      <span>Month</span><span>Repayment status</span><span>Bill (NT$)</span><span>Paid (NT$)</span><span>Remove</span>
    </div>}
    {review.entries.map(({ record, errors }, index) => {
      const update = (field: 'period' | typeof historyFields[number], value: string) =>
        onChange(records.map(item => item.id === record.id ? { ...item, [field]: value } : item))
      const inputId = (field: string) => 'month-' + field + '-' + record.id
      const invalidProps = (field: keyof typeof errors) => ({
        'aria-invalid': Boolean(errors[field]), 'aria-describedby': errors[field] ? inputId(field) + '-error' : undefined,
      })
      return <div className="monthly-record" role="group" aria-label={'Monthly record ' + (index + 1)} key={record.id}>
        <label><span className="monthly-field-label">Reporting month</span>
          <input className="form-control" id={inputId('period')} type="month" value={record.period} onChange={event => update('period', event.target.value)} {...invalidProps('period')} />
          {errors.period && <small id={inputId('period') + '-error'}>{errors.period}</small>}
        </label>
        {historyFields.map(field => <label key={field}><span className="monthly-field-label">{labels[field]}</span>
          {field === 'status' ? <select className="form-control" value={record.status} onChange={event => update(field, event.target.value)} {...invalidProps(field)}>
            <option value="">Select status</option>
            {errors.status && record.status && <option value={record.status}>Invalid code ({record.status})</option>}
            {Array.from({ length: 12 }, (_, code) => code - 2).map(code => <option key={code} value={code}>{code} · {describe(code)}</option>)}
          </select> : <input className="form-control" type="number" step={1} min={historyLimits[field][0]} max={historyLimits[field][1]} value={record[field]} onChange={event => update(field, event.target.value)} {...invalidProps(field)} />}
          {errors[field] && <small id={inputId(field) + '-error'}>{errors[field]}</small>}
        </label>)}
        <button id={'month-remove-' + record.id} type="button" className="monthly-remove" title={'Remove month ' + (record.period || index + 1)} aria-label={'Remove month ' + (record.period || index + 1)} onClick={() => {
          if (hasData(record)) setConfirm(record.id)
          else remove(record.id)
        }}><svg aria-hidden="true" viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="m5 5 10 10M15 5 5 15" /></svg></button>
        {confirm === record.id && confirmation}
      </div>
    })}
  </section>
}
