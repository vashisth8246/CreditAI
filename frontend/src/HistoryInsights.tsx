import { historyAnalytics, historyCsv, historyMoney } from './historyAnalytics'
import { repaymentLabel, type HistoryCurrency, type inspectHistory } from './monthlyHistory'

const percent = (value: number | null) => value === null ? 'Unavailable' : new Intl.NumberFormat('en-IN', { style: 'percent', maximumFractionDigits: 2 }).format(value)

export function HistoryInsights({ review, currency }: { review: ReturnType<typeof inspectHistory>; currency: HistoryCurrency }) {
  const data = historyAnalytics(review)
  const unit = currency === 'INR' ? '₹' : 'TWD'
  const money = (value: number | null) => historyMoney(value, currency)
  const scale = Math.max(1, ...data.rows.flatMap(row => [Math.abs(row.bill ?? 0), row.paid ?? 0]))
  const ratioScale = Math.max(1, ...data.rows.map(row => row.ratio ?? 0))
  const stats = [
    ['Months entered', review.entries.length], ['Complete months', review.complete],
    ['Sum of Monthly Statement Balances (' + unit + ')', money(data.billTotal)], ['Total Recorded Payments (' + unit + ')', money(data.paidTotal)],
    ['Average Monthly Statement Balance (' + unit + ')', money(data.billAverage)], ['Average Monthly Payment (' + unit + ')', money(data.paidAverage)],
    ['Payment-to-bill ratio', percent(data.ratio)],
  ]
  function exportHistory() {
    const url = URL.createObjectURL(new Blob([historyCsv(data.rows, currency)], { type: 'text/csv;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = 'creditai-monthly-history-' + currency + '.csv'
    link.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  return <section className="history-insights feature-section" aria-labelledby="history-insights-title">
    <h4 className="feature-section-title" id="history-insights-title">Your Monthly Credit History — Insights</h4>
    <p>{currency === 'INR' ? 'INR history is descriptive. The Taiwan model cannot run on rupee inputs.' : 'Taiwan research history in New Taiwan dollars (TWD).'}</p>
    {!review.ready && <p>Your credit-history charts are available as you enter records. The research prediction requires six complete consecutive months.</p>}
    <dl className="history-stats">{stats.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
    <label className="history-progress">Complete in latest six-month window: {6 - review.needed} of 6
      <progress max={6} value={6 - review.needed} />
    </label>
    <p>{review.window.length ? review.missing.length : 6} reporting periods missing · {review.ready && currency === 'TWD' ? 'Research inputs ready' : 'Prediction unavailable'}.</p>
    <p>Statement balances may repeat across periods. Their sum measures neither spending nor total debt. Payments are recorded by reporting period, without assigning them to that period’s bill. The aggregate ratio uses matched payments and positive balances only. Missing or invalid fields are omitted.</p>
    {!!data.rows.length && <>
      <div className="history-chart-grid">
        <section aria-label="Monthly statement balance and payment chart">
          <h5>Monthly balances and payments</h5>
          <p>Statement balance · Amount paid. Negative bars extend left.</p>
          <ul className="history-chart" tabIndex={0} aria-label="Statement balances and payments by month">{data.rows.map(row => <li key={row.period}>
            <strong>{row.period}</strong>
            {([['Statement balance', row.bill], ['Amount paid', row.paid]] as const).map(([label, value]) => <div key={label} title={label + ': ' + money(value)}>
              <span>{label}: {money(value)}</span>
              {value !== null && <div className="history-axis" aria-hidden="true"><i className={label === 'Amount paid' ? 'history-paid' : ''} style={{ width: Math.abs(value) / scale * 50 + '%', left: (value < 0 ? 50 + value / scale * 50 : 50) + '%' }} /></div>}
            </div>)}
          </li>)}</ul>
        </section>
        <section aria-label="Monthly payment-to-bill ratio chart">
          <h5>Payment-to-bill ratio</h5>
          <p>Positive balances only. This descriptive ratio does not measure repayment compliance or default risk.</p>
          <ul className="history-chart" tabIndex={0} aria-label="Payment-to-bill ratios by month">{data.rows.map(row => <li key={row.period} title={row.period + ': ' + percent(row.ratio)}>
            <strong>{row.period}</strong> · {percent(row.ratio)}
            {row.ratio !== null && <div className="history-axis history-ratio" aria-hidden="true"><i style={{ width: row.ratio / ratioScale * 100 + '%' }} /></div>}
          </li>)}</ul>
        </section>
      </div>
      <h5>Repayment-status timeline</h5>
      <p>−2 No consumption · −1 Paid duly · 0 Revolving credit · 1–9 Months delinquent.</p>
      <ul className="history-timeline" tabIndex={0} aria-label="Repayment statuses by month">{data.rows.map(row => <li key={row.period}><strong>{row.period}</strong> · {row.status === null ? 'Unavailable' : row.status + ' · ' + repaymentLabel(row.status)}</li>)}</ul>
      {!!data.insights.length && <ul>{data.insights.map(insight => <li key={insight}>{insight}</li>)}</ul>}
      <button type="button" className="button-secondary" onClick={exportHistory}>Download {currency} history CSV</button>
    </>}
  </section>
}
