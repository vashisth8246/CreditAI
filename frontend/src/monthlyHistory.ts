export const repaymentKeys = ['PAY_0', 'PAY_2', 'PAY_3', 'PAY_4', 'PAY_5', 'PAY_6']
export const historyFields = ['status', 'bill', 'paid'] as const
type HistoryField = typeof historyFields[number]
export type MonthlyRecord = { id: number; period: string } & Record<HistoryField, string>
const keysAt = (index: number) => [repaymentKeys[index], 'BILL_AMT' + (index + 1), 'PAY_AMT' + (index + 1)]
export const historyLimits = { status: [-2, 9], bill: [-335000, 1680000], paid: [0, 873000] }
export type HistoryCurrency = 'INR' | 'TWD'
export function currentMonth(now = new Date()) {
  return periodAt(now.getFullYear() * 12 + now.getMonth())
}
export function limitsFor(currency: HistoryCurrency) {
  return currency === 'TWD' ? historyLimits : { status: historyLimits.status, bill: [-1e9, 1e9], paid: [0, 1e9] }
}
export function repaymentLabel(code: number) {
  return ['No consumption', 'Paid duly', 'Revolving credit'][code + 2] ?? (code + (code === 1 ? ' month delinquent' : ' months delinquent'))
}

export function monthIndex(period: string) {
  if (!/^(?!0000)\d{4}-(0[1-9]|1[0-2])$/.test(period)) return null
  const [year, month] = period.split('-').map(Number)
  return year * 12 + month - 1
}

export function periodAt(index: number) {
  return String(Math.floor(index / 12)).padStart(4, '0') + '-' + String(index % 12 + 1).padStart(2, '0')
}

export function historyFromFeatures(values: Record<string, string>): MonthlyRecord[] {
  return repaymentKeys.map((_, index) => {
    const [status, bill, paid] = keysAt(index)
    return { id: index + 1, period: periodAt(2005 * 12 + 8 - index), status: values[status] ?? '', bill: values[bill] ?? '', paid: values[paid] ?? '' }
  })
}

export function inspectHistory(records: MonthlyRecord[], currency: HistoryCurrency = 'TWD', maximum = currentMonth()) {
  const limits = limitsFor(currency)
  const counts = new Map<number, number>()
  for (const record of records) {
    const index = monthIndex(record.period)
    if (index !== null) counts.set(index, (counts.get(index) ?? 0) + 1)
  }
  const entries = records.map(record => {
    const index = monthIndex(record.period)
    const errors: Partial<Record<HistoryField | 'period', string>> = {}
    if (index === null) errors.period = 'Enter a valid reporting month.'
    else if (record.period > maximum) errors.period = 'Reporting month cannot be in the future.'
    else if ((counts.get(index) ?? 0) > 1) errors.period = 'This reporting month is duplicated.'
    for (const field of historyFields) {
      const value = record[field]
      const [min, max] = limits[field]
      if (!value.trim()) errors[field] = 'Enter a value.'
      else if (!(currency === 'INR' && field !== 'status' ? /^-?\d+(\.\d{1,2})?$/ : /^-?\d+$/).test(value) || Number(value) < min || Number(value) > max) {
        errors[field] = (currency === 'INR' && field !== 'status' ? 'Enter an amount with up to two decimal places from ' : 'Enter a whole number from ') + min.toLocaleString('en-IN') + ' to ' + max.toLocaleString('en-IN') + '.'
      }
    }
    return { record, index, errors }
  })
  const ordered = entries.flatMap(entry => entry.index === null || entry.record.period > maximum ? [] : [{ ...entry, index: entry.index }])
    .sort((a, b) => b.index - a.index)
  const latest = ordered[0]?.index
  const window = latest == null ? [] : Array.from({ length: 6 }, (_, offset) => latest - offset)
  const missing = window.filter(index => !counts.has(index)).map(index => index < 12 ? 'outside supported calendar' : periodAt(index))
  const selected = ordered.filter(entry => window.includes(entry.index))
  const complete = entries.filter(entry => Object.keys(entry.errors).length === 0).length
  const needed = 6 - selected.filter(entry => Object.keys(entry.errors).length === 0).length
  const ready = selected.length === 6 && missing.length === 0 &&
    ordered.length === entries.length && counts.size === ordered.length &&
    selected.every(entry => Object.keys(entry.errors).length === 0)
  const features: Record<string, string> = {}
  if (ready && currency === 'TWD') selected.forEach(({ record }, index) => {
    keysAt(index).forEach((key, field) => { features[key] = record[historyFields[field]] })
  })
  const display = [...entries].sort((a, b) => (b.index ?? -1) - (a.index ?? -1))
  return { entries: display, complete, ready, needed, missing, features, window: selected.map(entry => entry.record.period) }
}
