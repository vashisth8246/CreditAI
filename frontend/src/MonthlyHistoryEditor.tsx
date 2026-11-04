import { useEffect, useRef, useState } from 'react'
import { currentMonth, historyFields, limitsFor, monthIndex, periodAt, repaymentKeys, repaymentLabel, type HistoryCurrency, type MonthlyRecord, type inspectHistory } from './monthlyHistory'
import './monthlyHistory.css'

const hasData = ({ status, bill, paid }: MonthlyRecord) => Boolean(status || bill || paid)

export function MonthlyHistoryEditor({ records, review, onChange, loadExample, currency }: {
  currency: HistoryCurrency
  records: MonthlyRecord[]
  review: ReturnType<typeof inspectHistory>
  onChange: (records: MonthlyRecord[]) => void
  loadExample: () => void
}) {
  const nextId = useRef(7)
  const addButton = useRef<HTMLButtonElement>(null)
  const confirmButton = useRef<HTMLButtonElement>(null)
  const [confirm, setConfirm] = useState<number | 'all' | 'example' | null>(null)
  const unit = currency === 'INR' ? '₹' : 'TWD'
  const labels = { status: 'Repayment status', bill: 'Statement Balance (' + unit + ')', paid: 'Amount Paid (' + unit + ')' }
  const limits = limitsFor(currency)
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
    <p className="monthly-help">The model was trained on April–September 2005 Taiwan credit-card records. Newer dates are accepted for research demonstrations, but this model has not been validated on recent borrowers.</p>
    <p className="monthly-help">Research inference requires six consecutive complete months because the model has a separate input for each month’s status, balance and payment.</p>
    <div className="monthly-readiness" role="status">
      <strong>{records.length} entered · {review.complete} complete · {review.window.length ? review.missing.length : 6} missing periods</strong>
      <p>{review.needed ? `${review.needed} more complete ${review.needed === 1 ? 'month is' : 'months are'} needed in the latest six-month window. Add missing periods or complete the existing rows.` : review.ready ? currency === 'TWD' ? 'Ready for Taiwan research inference.' : 'Six consecutive months complete. INR history is available for descriptive analysis.' : 'Correct invalid or duplicate reporting periods.'}</p>
      {!!review.missing.length && <p>Missing periods: {review.missing.join(', ')}.</p>}
      {review.ready && <p>{currency === 'TWD' ? 'Selected research window' : 'Latest six-month window'}: {review.window.at(-1)} through {review.window[0]}.{records.length > 6 ? ' Older records are included in descriptive analytics only.' : ''}</p>}
    </div>
    <div className="monthly-actions">
      <button ref={addButton} type="button" className="button-secondary" disabled={records.length >= 120} onClick={() => {
        const indexes = records.flatMap(record => { const index = monthIndex(record.period); return index === null ? [] : [index] })
        const previous = indexes.length ? Math.min(...indexes) - 1 : monthIndex(currentMonth())!
        const id = nextId.current++
        onChange([...records, { id, period: previous >= 12 ? periodAt(previous) : '', status: '', bill: '', paid: '' }])
        setConfirm(null)
        requestAnimationFrame(() => document.getElementById('month-period-' + id)?.focus())
      }}>+ Add Month</button>
      <button type="button" className="button-secondary" onClick={() => {
        if (records.some(hasData)) setConfirm('example')
        else loadExample()
      }}>{currency === 'TWD' ? 'Load 6-Month Research Example' : 'Load INR Example'}</button>
      <button type="button" className="button-quiet" disabled={!records.length} onClick={() => setConfirm('all')}>Clear History</button>
    </div>
    <details className="monthly-help">
      <summary>Repayment codes and research window</summary>
      <p>−2: No consumption · −1: Paid duly · 0: Revolving credit · 1–9: Months late.</p>
      <p>{currency === 'TWD' ? 'Enter whole TWD amounts.' : 'Rupee amounts accept up to two decimal places.'} Negative balances can represent a credit balance.</p>
      {currency === 'TWD' && review.ready && <p>Model positions, newest first: {review.window.map((period, index) =>
        period + ' → ' + repaymentKeys[index] + ', BILL_AMT' + (index + 1) + ', PAY_AMT' + (index + 1)
      ).join(' · ')}.</p>}
    </details>
    {typeof confirm !== 'number' && confirmation}
    {records.length > 0 && <div className="monthly-columns" aria-hidden="true">
      <span>Month</span><span>Repayment status</span><span>{labels.bill}</span><span>{labels.paid}</span><span>Remove</span>
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
          <input className="form-control" id={inputId('period')} type="month" min="0001-01" max={currentMonth()} value={record.period} onChange={event => update('period', event.target.value)} {...invalidProps('period')} />
          {errors.period && <small id={inputId('period') + '-error'}>{errors.period}</small>}
        </label>
        {historyFields.map(field => <label key={field}><span className="monthly-field-label">{labels[field]}</span>
          {field === 'status' ? <select className="form-control" value={record.status} onChange={event => update(field, event.target.value)} {...invalidProps(field)}>
            <option value="">Select status</option>
            {errors.status && record.status && <option value={record.status}>Invalid code ({record.status})</option>}
            {Array.from({ length: 12 }, (_, code) => code - 2).map(code => <option key={code} value={code}>{code} · {repaymentLabel(code)}</option>)}
          </select> : <input className="form-control" type="number" step={currency === 'INR' ? '0.01' : '1'} min={limits[field][0]} max={limits[field][1]} value={record[field]} onChange={event => update(field, event.target.value)} {...invalidProps(field)} />}
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
