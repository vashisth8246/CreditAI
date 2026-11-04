export const repaymentKeys = ['PAY_0', 'PAY_2', 'PAY_3', 'PAY_4', 'PAY_5', 'PAY_6']
export const historyFields = ['status', 'bill', 'paid'] as const
type HistoryField = typeof historyFields[number]
export type MonthlyRecord = { id: number; period: string } & Record<HistoryField, string>
const keysAt = (index: number) => [repaymentKeys[index], 'BILL_AMT' + (index + 1), 'PAY_AMT' + (index + 1)]
export const historyLimits = { status: [-2, 9], bill: [-335000, 1680000], paid: [0, 873000] }

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

export function inspectHistory(records: MonthlyRecord[]) {
  const counts = new Map<number, number>()
  for (const record of records) {
    const index = monthIndex(record.period)
    if (index !== null) counts.set(index, (counts.get(index) ?? 0) + 1)
  }
  const entries = records.map(record => {
    const index = monthIndex(record.period)
    const errors: Partial<Record<HistoryField | 'period', string>> = {}
    if (index === null) errors.period = 'Enter a valid reporting month.'
    else if ((counts.get(index) ?? 0) > 1) errors.period = 'This reporting month is duplicated.'
    for (const field of historyFields) {
      const value = record[field]
      const [min, max] = historyLimits[field]
      if (!value.trim()) errors[field] = 'Enter a value.'
      else if (!/^-?\d+$/.test(value) || Number(value) < min || Number(value) > max) {
        errors[field] = 'Enter a whole number from ' + min.toLocaleString('en-US') + ' to ' + max.toLocaleString('en-US') + '.'
      }
    }
    return { record, index, errors }
  })
  const ordered = entries.flatMap(entry => entry.index === null ? [] : [{ ...entry, index: entry.index }])
    .sort((a, b) => b.index - a.index)
  const latest = ordered[0]?.index
  const window = latest == null ? [] : Array.from({ length: 6 }, (_, offset) => latest - offset)
  const missing = window.filter(index => !counts.has(index)).map(index => index < 12 ? 'outside supported calendar' : periodAt(index))
  const selected = ordered.slice(0, 6)
  const complete = entries.filter(entry => Object.keys(entry.errors).length === 0).length
  const ready = selected.length === 6 && missing.length === 0 &&
    ordered.length === entries.length && counts.size === ordered.length &&
    selected.every(entry => Object.keys(entry.errors).length === 0)
  const features: Record<string, string> = {}
  if (ready) selected.forEach(({ record }, index) => {
    keysAt(index).forEach((key, field) => { features[key] = record[historyFields[field]] })
  })
  return { entries, complete, ready, missing, features, window: selected.map(entry => entry.record.period) }
}
