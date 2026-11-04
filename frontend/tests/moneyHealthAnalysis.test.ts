import assert from 'node:assert/strict'
import { test } from 'node:test'
import { calculate, example, profiles } from '../src/moneyHealth.ts'
import { analyzeMoney, analysisCharts } from '../src/moneyHealthAnalysis.ts'

const student = profiles[0].fields
const input = example(student)
test('Student snapshot, essential coverage and optional reduction reconcile exactly', () => {
  const result = calculate(student, input)
  const a = analyzeMoney(result, 0)
  assert.deepEqual([result.balance, a.monthlyPercent, a.pressure, a.essential, a.optional], [120000, 24, 76, 310000, 70000])
  assert.equal(a.emergencyMonths?.toFixed(2), '0.81')
  assert.equal(a.allocationTotal, 500000)
  assert.equal(a.spending.reduce((sum, [, value]) => sum + value, 0), 380000)
  const suggestion = a.suggestions.find(item => item.challenge?.kind === 'spending')!
  assert.deepEqual([suggestion.challenge?.baseline, suggestion.challenge?.target], [70000, 30000])
  assert.equal(calculate(student, { ...input, ...suggestion.changes }).balance, 150000)
})

test('Break-even, shortfall, and zero or missing funds are distinct', () => {
  const base = { ...input, primary: '3800' }
  assert.match(analyzeMoney(calculate(student, base), 0).cashFlow, /break-even/)
  const zero = analyzeMoney(calculate(student, { ...base, primary: '0' }), 0)
  assert.match(zero.cashFlow, /exceeds/)
  assert.equal(zero.pressure, null)
  assert.equal(zero.monthlyPercent, null)
  assert.equal(zero.allocationTotal, 380000)
  assert(!zero.allocation.some(([, value]) => value < 0))
  assert.throws(() => calculate(student, { ...base, primary: '' }))
})

test('Blank and explicit zero stay distinct in charts and coverage limits', () => {
  const result = calculate(student, { ...input, education: '', food: '0', transport: '0' })
  const a = analyzeMoney(result, 0)
  assert.deepEqual(a.blankEssential, ['Education'])
  assert.equal(a.emergencyMonths, null)
  assert(a.spending.some(([label, value]) => label === 'Food' && value === 0))
  assert(!a.spending.some(([label]) => label === 'Education'))
  assert.deepEqual(analysisCharts(result, 0)[2].rows, [['Accessible savings', 250000], ['Entered essential monthly expenses', 0]])
})

test('Professional debt and goal pressure use the entered balance and actual outflow', () => {
  const fields = profiles[1].fields
  const result = calculate(fields, { ...example(fields), goal: '16000' })
  const a = analyzeMoney(result, 1)
  assert.equal(a.pressure, 72)
  assert.equal(result.debtRatio, 16)
  assert.equal(a.goalGap, 200000)
  assert(a.suggestions.some(item => item.changes?.goal === '14000.00'))
  assert.equal(a.essential + a.optional + a.business + result.debt, result.outflow)
})
