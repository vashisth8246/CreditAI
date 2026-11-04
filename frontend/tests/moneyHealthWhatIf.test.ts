import assert from 'node:assert/strict'
import test from 'node:test'
import { budgetAmount, calculate, calculateScenario, example, profiles, scenarioPresets } from '../src/moneyHealth.ts'

test('each verified example has an immediately usable starter scenario', () => {
  const expected = [[120000, 150000], [1400000, 900000], [1500000, 700000], [80000, 30000]]
  for (const [index, { fields }] of profiles.entries()) {
    const input = example(fields)
    const before = calculate(fields, input)
    const after = calculateScenario(fields, input, scenarioPresets(index, before)[0].changes)
    assert.deepEqual([before.balance, after.balance], expected[index])
    assert.deepEqual(input, example(fields))
    assert.deepEqual(calculateScenario(fields, input, {}), before)
  }
})

test('budget fields reflect the current profile and reset without writing baseline values', () => {
  for (const { fields } of profiles) {
    const baseline = Object.freeze(example(fields))
    for (const field of fields) assert.equal(budgetAmount(baseline, {}, field.id), baseline[field.id])
    assert.equal(budgetAmount(baseline, {}, 'extra'), '0')
    assert.equal(budgetAmount(baseline, { primary: '0' }, 'primary'), '0')
    assert.equal(budgetAmount(baseline, {}, 'primary'), baseline.primary)
  }
  const { fields } = profiles[1]
  const baseline = Object.freeze(example(fields))
  const changes = { primary: '40000', housing: '12000', food: '6000.25', goal: '8000', extra: '500.10' }
  const after = calculateScenario(fields, baseline, changes)
  assert.equal(after.balance, 749965)
  assert.equal(after.goal, 800000)
  assert.equal(calculate(fields, baseline).balance, 1400000)
  assert.equal(budgetAmount(baseline, changes, 'food'), '6000.25')
  assert.throws(() => calculateScenario(fields, baseline, { food: '-1' }), /Food/)
})

test('advanced values distinguish blanks from zero and add EMI on top of baseline debt', () => {
  const { fields } = profiles[1]
  const input = example(fields)
  const after = calculateScenario(fields, input, { food: ' ', transport: '0', extra: '1234.56', goal: '16000' })
  assert.equal(after.debt, 923456)
  assert.equal(after.expenses, 2500000)
  assert.equal(after.balance, 1576544)
  assert.equal(after.feasibility, 'Exceeds available balance')
  assert.equal(calculateScenario(fields, input, { goal: '17000' }).balance, 1400000)
  assert.equal(calculateScenario(fields, input, { food: '6000' }).balance, 1600000)
})
