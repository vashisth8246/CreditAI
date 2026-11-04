import assert from 'node:assert/strict'
import { test } from 'node:test'
import { importPassport, periodDate, progress, readPassports, savePassports, validatePassport } from '../src/moneyChallenge.ts'
import type { Passport, Entry } from '../src/moneyChallenge.ts'

const created = '2026-11-01'
const date = '2026-11-04'
const base: Passport = {
  id: 'test-1', version: 1, kind: 'savings', name: 'Laptop', profile: 'Student', example: true,
  created, end: '2026-11-10', target: 100001, start: 0, planned: 20000, frequency: 'daily',
  category: '', essential: 0, baseline: 0, snapshot: { balance: 1000000 }, entries: [],
}
const entry = (id: string, amount: number, kind: Entry['kind'] = 'contribution', at = date): Entry =>
  ({ id, amount, kind, date: at, note: '' })

test('rounds up milestone and deadline amounts while keeping exact paise', () => {
  const result = progress(base, date)
  assert.deepEqual(result.milestones.map(item => item.threshold), [25001, 50001, 75001, 100001])
  assert.equal(result.required, 16667)
  assert.equal(result.eta, '2026-11-10')
  assert.equal(result.feasible, true)
  assert.equal(result.percentage, 0)
  assert.equal(result.timeline.length, 0)
})

test('contributions, withdrawals, edits and deletes update actual progress', () => {
  const entries = [entry('a', 50001), entry('b', 10000, 'withdrawal')]
  const first = progress(validatePassport({ ...base, entries }, date), date)
  assert.equal(first.current, 40001)
  assert.equal(first.remaining, 60000)
  assert.deepEqual(first.milestones.map(item => item.achieved), [true, false, false, false])
  const updated = progress({ ...base, entries: [entry('a', 110001), entries[1]] }, date)
  assert.equal(updated.status, 'Target reached')
  assert.equal(updated.percentage, 100)
  assert.equal(updated.eta, null)
  assert.equal(progress({ ...base, entries: [] }, date).current, 0)
})

test('spending comparison closes only after the inclusive tracking boundary', () => {
  const spending = validatePassport({
    ...base, kind: 'spending', category: 'Food', end: date, baseline: 100000, target: 20000, planned: 0,
    entries: [entry('x', 73000, 'spending')],
  }, date)
  assert.equal(progress(spending, date).status, 'Tracking period open')
  const closed = progress(spending, '2026-11-05')
  assert.equal(closed.limit, 80000)
  assert.equal(closed.targetDifference, -7000)
  assert.equal(closed.comparison, 27000)
  assert.equal(closed.percentage, 100)
  assert.equal(progress({ ...spending, entries: [] }, '2026-11-05').percentage, 0)
})

test('emergency coverage uses reported expenses and net entries', () => {
  const buffer = { ...base, kind: 'emergency' as const, essential: 100000, start: 50000, entries: [entry('a', 25000), entry('b', 10000, 'withdrawal')] }
  assert.equal(progress(buffer, date).coverage, 0.65)
  assert.equal(progress({ ...buffer, essential: 0 }, date).coverage, null)
})

test('calendar schedules clamp month ends and retain weekly dates', () => {
  assert.equal(periodDate('2028-01-31', 'monthly', 1), '2028-02-29')
  assert.equal(periodDate('2028-01-31', 'monthly', 2), '2028-03-31')
  assert.equal(periodDate('2026-11-01', 'weekly', 2), '2026-11-15')
  assert.equal(periodDate('2099-12-31', 'daily', 1), null)
})

test('rejects unsafe amounts, duplicate IDs, invalid dates and overdrawn history', () => {
  for (const entries of [
    [entry('x', -1)], [entry('x', 1.25)], [entry('x', 1e13)], [entry('x', 0)], [entry('x', 1), entry('x', 2)],
    [entry('x', 1, 'contribution', '2026-02-30')], [entry('x', 1, 'contribution', '2026-11-05')],
    [entry('x', 1, 'withdrawal'), entry('y', 10)],
  ]) assert.throws(() => validatePassport({ ...base, entries }, date))
  assert.throws(() => validatePassport({ ...base, version: 2 }, date))
})

test('versioned backup round trip and consent-gated isolated collections', () => {
  const storage = () => {
    const data = new Map<string, string>()
    return { getItem: (key: string) => data.get(key) ?? null, setItem: (key: string, value: string) => data.set(key, value), removeItem: (key: string) => data.delete(key) }
  }
  const local = storage()
  assert.throws(() => savePassports(local, [base], false))
  assert.deepEqual(readPassports(local, date), [])
  assert.deepEqual(importPassport(JSON.stringify(base), date), base)
  assert.throws(() => importPassport('not-json', date))
  assert.throws(() => importPassport('{"version":1}', date))
  assert.throws(() => importPassport(' '.repeat(250001), date))
  savePassports(local, [base, { ...base, id: 'test-2' }], true)
  assert.equal(readPassports(local, date).length, 2)
  assert.deepEqual(readPassports(storage(), date), [])
  savePassports(local, [], true)
  assert.deepEqual(readPassports(local, date), [])
})
