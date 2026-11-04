import { test } from 'node:test'
import assert from 'node:assert/strict'
import { calculate, charts, example, parseAmount, profiles, scenarioPresets, timeline } from '../src/moneyHealth.ts'

for (const [index, funds, expenses, debt, balance] of [
  [0, 5000, 3800, 0, 1200], [1, 50000, 28000, 8000, 14000],
  [2, 40000, 25000, 0, 15000], [3, 3000, 2200, 0, 800],
]) {
  test(profiles[index].name + ' example', () => {
    const { fields } = profiles[index]
    const result = calculate(fields, example(fields))
    assert.deepEqual([result.funds, result.expenses, result.debt, result.balance], [funds, expenses, debt, balance].map(value => value * 100))
    assert.deepEqual(charts(result, result)[0].rows.at(-1), ['Balance', balance * 100])
  })
}
test('blank, invalid, decimal and large inputs', () => {
  assert.equal(parseAmount(''), null)
  assert.equal(parseAmount('9999999999.99'), 999999999999)
  assert.equal(parseAmount('0.29'), 29)
  for (const invalid of ['-1', 'NaN', 'Infinity', '1.001', '1e8']) assert.throws(() => parseAmount(invalid))
  assert.throws(() => calculate(profiles[0].fields, {}))
})
test('zero funds, deficit, zero outflow and unknown goal', () => {
  const { fields } = profiles[3]
  const input = { primary: '0', essential: '5.01', discretionary: '0', savings: '0', extraneous: '40' }
  const result = calculate(fields, input)
  assert.equal(result.balance, -501)
  assert.equal(result.expenseRatio, null)
  assert.equal(result.debtRatio, null)
  assert.equal(result.coverage, 0)
  assert.equal(result.feasibility, 'Goal unavailable')
  assert.equal(calculate(fields, { ...input, essential: '0' }).coverage, null)
})
test('freelancer income estimate and professional extra debt', () => {
  const { fields } = profiles[2]
  const input = example(fields)
  assert.equal(calculate(fields, { ...input, primary: input.low }).balance, 300000)
  const professional = profiles[1].fields
  const baseline = example(professional)
  const scenario = calculate(professional, { ...baseline, debt: '14000' })
  assert.equal(scenario.balance - calculate(professional, baseline).balance, -600000)
  assert.equal(scenario.feasibility, 'Exceeds available balance')
})
test('purchase timeline uses only allocated savings', () => {
  assert.equal(timeline(10000, 1000, 2000), 5)
  assert.equal(timeline(10000, 10000, 0), 0)
  assert.equal(timeline(10000, 0, 0), null)
})


test('professional ratios and savings coverage use the correct denominators', () => {
  const { fields } = profiles[1]
  const result = calculate(fields, example(fields))
  assert.equal(result.outflow, 3600000)
  assert.equal(result.expenseRatio?.toFixed(2), '56.00')
  assert.equal(result.debtRatio?.toFixed(2), '16.00')
  assert.equal(result.coverage?.toFixed(2), '2.08')
  assert.equal(result.feasibility, 'Feasible on these inputs')
  assert.equal(calculate(fields, { ...example(fields), goal: '14000.01' }).feasibility, 'Exceeds available balance')
})

test('student balance retains individual paise across expense categories', () => {
  const { fields } = profiles[0]
  const input = { primary: '10.01', additional: '0.09', food: '0.10', transport: '0.20', education: '0.29', personal: '0.31', savings: '1.80', goal: '9.20' }
  const result = calculate(fields, input)
  assert.equal(result.funds, 1010)
  assert.equal(result.expenses, 90)
  assert.equal(result.balance, 920)
  assert.equal(result.coverage, 2)
  assert.equal(result.feasibility, 'Feasible on these inputs')
  assert.equal(result.register.find(field => field.id === 'debt')?.amount, null)
  assert.deepEqual(charts(result, result)[1].rows.map(([, value]) => value), [10, 20, 29, 31])
})

test('education and housing distinguish missing amounts from explicit zero', () => {
  for (const [index, id] of [[0, 'education'], [1, 'housing']] as const) {
    const { fields } = profiles[index]
    const input = example(fields)
    delete input[id]
    const blank = calculate(fields, input)
    const zero = calculate(fields, { ...input, [id]: '0' })
    assert.equal(blank.register.find(field => field.id === id)?.amount, null)
    assert.equal(zero.register.find(field => field.id === id)?.amount, 0)
    assert.equal(blank.expenses, zero.expenses)
    assert.throws(() => calculate(fields, { ...input, [id]: '-1' }))
  }
})

test('presets use the baseline and keep low or missing spending nonnegative', () => {
  const expected = [[150000, 170000, 120000, 120000], [900000, 1900000, 1600000, 1400000],
    [700000, 1400000, 1500000, 1500000], [30000, 110000, 80000]]
  for (const [profile, { fields }] of profiles.entries()) {
    const input = example(fields)
    const base = calculate(fields, input)
    const presets = scenarioPresets(profile, base)
    assert.deepEqual(presets.map(({ changes }) => calculate(fields, {
      ...input, ...changes, ...(changes.extra ? { debt: (base.debt / 100 + Number(changes.extra)).toFixed(2) } : {}),
    }).balance), expected[profile])
  }
  const { fields } = profiles[0]
  const input = { ...example(fields), food: '20', transport: '0', education: '', personal: '10' }
  const base = calculate(fields, input)
  const lowered = calculate(fields, { ...input, ...scenarioPresets(0, base)[0].changes })
  assert.equal(lowered.expenses, 0)
  assert.equal(lowered.register.find(field => field.id === 'education')?.amount, null)
})
