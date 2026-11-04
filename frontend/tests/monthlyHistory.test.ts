import assert from 'node:assert/strict'
import test from 'node:test'
import { historyFromFeatures, inspectHistory, periodAt, repaymentKeys } from '../src/monthlyHistory.ts'

const payload = Object.fromEntries(repaymentKeys.flatMap((key, index) => [
  [key, String(index - 2)], ['BILL_AMT' + (index + 1), String(index - 15000)], ['PAY_AMT' + (index + 1), String(index)],
]))
const sample = historyFromFeatures(payload)

test('all 18 fields round-trip with no PAY_1, independent of row order', () => {
  assert.equal(sample[0].period, '2005-09')
  assert.equal(sample[5].period, '2005-04')
  const review = inspectHistory(sample.toReversed())
  assert.equal(review.ready, true)
  assert.deepEqual(review.features, payload)
})

test('partial or gapped windows never produce inferred feature values', () => {
  for (const count of [2, 3]) {
    const review = inspectHistory(sample.slice(0, count))
    assert.equal(review.ready, false)
    assert.equal(review.missing.length, 6 - count)
    assert.deepEqual(review.features, {})
  }
  const review = inspectHistory(sample.map(row => row.period === '2005-08' ? { ...row, period: '2005-03' } : row))
  assert.deepEqual(review.missing, ['2005-08'])
  assert.equal(review.ready, false)
})

test('twelve months select only the latest window across a year boundary', () => {
  const rows = Array.from({ length: 12 }, (_, index) => ({
    ...sample[0], id: index, period: periodAt(2026 * 12 + 1 - index), bill: String(index),
  }))
  const review = inspectHistory(rows.toReversed())
  assert.equal(review.ready, true)
  assert.equal(review.complete, 12)
  assert.equal(review.window[5], '2025-09')
  assert.equal(review.features.BILL_AMT1, '0')
  assert.equal(review.features.BILL_AMT6, '5')
})

test('duplicate months and invalid fields block model submission', () => {
  const review = inspectHistory([...sample.slice(0, 5), { ...sample[0], id: 7, status: '99', bill: '-335001', paid: '-1' }])
  assert.equal(review.ready, false)
  assert.deepEqual(Object.keys(review.entries[5].errors), ['period', 'status', 'bill', 'paid'])
})
