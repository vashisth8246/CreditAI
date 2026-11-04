import assert from 'node:assert/strict'
import test from 'node:test'
import { budgetAmount, calculate, calculateScenario, example, profiles, scenarioPresets } from '../src/moneyHealth.ts'
import { scenarioSuggestions } from '../src/moneyHealthAnalysis.ts'

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

test('recommendations use the combined simulation and can layer over unrelated edits', () => {
  const { fields } = profiles[1]
  const entries = Object.freeze(example(fields))
  const before = calculate(fields, entries)
  const edits = { primary: '40000', extra: '500.10', food: '6000' }
  const preview = calculateScenario(fields, entries, edits)
  assert.equal(preview.balance, 549990)
  const advice = scenarioSuggestions(before, preview, 1)
  assert(advice.some(item => item.text.includes('₹32,000 in primary income')))
  assert(!advice.some(item => item.text.includes('₹40,000 in primary income')))
  const goal = advice.find(item => item.changes?.goal)?.changes
  assert(goal)
  const applied = calculateScenario(fields, entries, { ...edits, ...goal })
  assert.equal(applied.goal, preview.balance)
  assert.equal(applied.balance, preview.balance)
  assert.equal(calculate(fields, entries).balance, before.balance)
})

test('recommendations skip completed expense reductions and an already-applied freelancer estimate', () => {
  const student = profiles[0].fields
  const input = example(student)
  assert(!scenarioSuggestions(calculate(student, input), calculateScenario(student, input, { personal: '400' }), 0)
    .some(item => item.changes?.personal))
  const freelancer = profiles[2].fields
  const free = example(freelancer)
  assert(!scenarioSuggestions(calculate(freelancer, free), calculateScenario(freelancer, free, { primary: '28000' }), 2)
    .some(item => item.changes?.primary))
})
