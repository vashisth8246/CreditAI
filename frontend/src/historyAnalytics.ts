import { repaymentLabel, type HistoryCurrency, type inspectHistory } from './monthlyHistory.ts'

const amounts = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 })
export function historyMoney(value: number | null, currency: HistoryCurrency) {
  if (value === null) return 'Unavailable'
  return (value < 0 ? '−' : '') + (currency === 'INR' ? '₹' : 'TWD ') + amounts.format(Math.abs(value))
}

export function historyAnalytics(review: ReturnType<typeof inspectHistory>) {
  const rows = review.entries.filter(entry => !entry.errors.period).toReversed().map(({ record, errors }) => {
    const bill = errors.bill ? null : Number(record.bill)
    const paid = errors.paid ? null : Number(record.paid)
    const status = errors.status ? null : Number(record.status)
    const ratio = bill !== null && bill > 0 && paid !== null ? paid / bill : null
    return { period: record.period, bill, paid, status, ratio }
  })
  const bills = rows.flatMap(row => row.bill === null ? [] : [row.bill])
  const payments = rows.flatMap(row => row.paid === null ? [] : [row.paid])
  const sum = (values: number[]) => values.reduce((total, value) => total + Math.round(value * 100), 0) / 100
  const matched = rows.filter(row => row.ratio !== null)
  const ratio = matched.length ? sum(matched.map(row => row.paid!)) / sum(matched.map(row => row.bill!)) : null
  const complete = rows.filter(row => row.bill !== null && row.paid !== null && row.status !== null)
  const lastThree = complete.slice(-3)
  const insights: string[] = []
  if (lastThree.length === 3 && lastThree.every((row, i) => i === 0 || row.bill! > lastThree[i - 1].bill!)) {
    insights.push('Statement balances increased across the latest three complete records.')
  }
  const latest = rows.at(-1)
  const prior = rows.at(-2)
  if (latest?.paid != null && prior?.paid != null && latest.paid > prior.paid) {
    insights.push('The latest recorded payment is higher than the previous recorded payment.')
  }
  const delinquent = rows.filter(row => row.status !== null && row.status > 0).length
  if (delinquent) insights.push(delinquent + (delinquent === 1 ? ' entered month has a delinquency code.' : ' entered months have delinquency codes.'))
  return {
    rows, insights, ratio,
    billTotal: bills.length ? sum(bills) : null,
    paidTotal: payments.length ? sum(payments) : null,
    billAverage: bills.length ? sum(bills) / bills.length : null,
    paidAverage: payments.length ? sum(payments) / payments.length : null,
  }
}

export function historyCsv(rows: ReturnType<typeof historyAnalytics>['rows'], currency: HistoryCurrency) {
  return ['Reporting month,Currency,Statement balance,Amount paid,Payment-to-balance percent,Repayment code,Repayment status',
    ...rows.map(row => [row.period, currency, row.bill, row.paid, row.ratio === null ? null : (row.ratio * 100).toFixed(2),
      row.status, row.status === null ? '' : repaymentLabel(row.status)].join(',')),
  ].join('\r\n')
}
