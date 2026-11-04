import assert from 'node:assert/strict'
import test from 'node:test'
import { historyAnalytics, historyCsv, historyMoney } from '../src/historyAnalytics.ts'
import { inspectHistory, monthIndex, periodAt, repaymentLabel } from '../src/monthlyHistory.ts'

const recent = monthIndex('2025-02')!
const records = Array.from({ length: 12 }, (_, i) => ({
  id: i + 1, period: periodAt(recent - i), bill: String(12000 - i * 1000), paid: String(6000 - i * 500), status: '0',
}))

test('recent windows sort across year boundaries and INR never yields model features', () => {
  for (const count of [2, 3, 4, 6, 12]) {
    const rows = records.slice(0, count).toReversed()
    const inr = inspectHistory(rows, 'INR', '2025-02')
    assert.equal(inr.complete, count)
    assert.equal(inr.needed, Math.max(6 - count, 0))
    assert.deepEqual(inr.features, {})
    assert.equal(historyAnalytics(inr).rows.at(-1)?.period, '2025-02')
    const twd = inspectHistory(rows, 'TWD', '2025-02')
    assert.equal(Object.keys(twd.features).length, count < 6 ? 0 : 18)
    if (count >= 6) {
      assert.equal(twd.window.at(-1), '2024-09')
      assert.equal(twd.features.BILL_AMT6, '7000')
      assert.equal(twd.features.PAY_0, '0')
      assert(!('PAY_1' in twd.features))
    }
  }
})

test('gaps, duplicate periods and future values do not produce model features', () => {
  const rows = [...records.slice(0, 5), { ...records[5], period: '2024-08' }]
  assert.deepEqual(inspectHistory(rows, 'TWD', '2025-02').missing, ['2024-09'])
  const duplicate = inspectHistory([...rows, { ...rows[0], id: 99 }], 'INR', '2025-02')
  assert.equal(historyAnalytics(duplicate).rows.length, 5)
  const future = inspectHistory([{ ...rows[0], period: '2025-03' }], 'TWD', '2025-02')
  assert.match(future.entries[0].errors.period!, /future/)
  assert.deepEqual(future.features, {})
})

test('summaries, positive-denominator ratios, repayment semantics and INR export', () => {
  const inputs = [
    { ...records[0], bill: '20000', paid: '25000', status: '0' },
    { ...records[1], bill: '0', paid: '1500', status: '2' },
    { ...records[2], bill: '-2500', paid: '0', status: '-1' },
  ]
  const result = historyAnalytics(inspectHistory(inputs, 'INR', '2025-02'))
  assert.equal(result.billTotal, 17500)
  assert.equal(result.paidTotal, 26500)
  assert.equal(result.billAverage, 17500 / 3)
  assert.equal(result.paidAverage, 26500 / 3)
  assert.equal(result.ratio, 1.25)
  assert.deepEqual(result.rows.map(row => row.ratio), [null, null, 1.25])
  assert.equal(historyMoney(1250000, 'INR'), '₹12,50,000')
  assert.equal(historyMoney(-2500, 'INR'), '−₹2,500')
  assert.equal(historyMoney(0, 'INR'), '₹0')
  assert.deepEqual([-2, -1, 0, 1, 9].map(repaymentLabel), ['No consumption', 'Paid duly', 'Revolving credit', '1 month delinquent', '9 months delinquent'])
  assert.equal(result.insights.length, 3)
  assert.match(historyCsv(result.rows, 'INR'), /2025-02,INR,20000,25000,125.00,0,Revolving credit/)
  assert.doesNotMatch(historyCsv(result.rows, 'INR'), /TWD/)
  const decimal = records.slice(0, 2).map((row, i) => ({ ...row, bill: i ? '0.20' : '0.10', paid: '0.01' }))
  assert.equal(historyAnalytics(inspectHistory(decimal, 'INR', '2025-02')).billTotal, 0.3)
  assert.equal(inspectHistory(decimal, 'TWD', '2025-02').complete, 0)
})
