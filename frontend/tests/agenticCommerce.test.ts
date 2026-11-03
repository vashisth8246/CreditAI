import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import {
  AGENTIC_COMMERCE_NAVIGATION,
  AGENTIC_COMMERCE_STAGES,
  AgenticCommercePage,
  CommerceAuditTrailPage,
} from '../src/agenticCommerce.ts'

test('Agentic Commerce navigation is a distinct section', () => {
  assert.deepEqual(AGENTIC_COMMERCE_NAVIGATION.map(({ id }) => id), ['commerce', 'commerce-audit'])
  assert.equal(AGENTIC_COMMERCE_NAVIGATION[0].section, 'AGENTIC COMMERCE')
  assert.equal(AGENTIC_COMMERCE_NAVIGATION[1].title, 'Commerce Audit Trail')
})

test('AC-2 comparison workspace renders purchase context, assumptions, and truthful stage states', () => {
  const markup = renderToStaticMarkup(createElement(AgenticCommercePage))
  assert.equal((markup.match(/commerce-stage-status/g) ?? []).length, 8)
  for (const stage of AGENTIC_COMMERCE_STAGES) assert.ok(markup.includes(stage))
  for (const boundary of ['RESEARCH SIMULATION', 'No lender offers', 'No credit decision', 'No transaction execution', 'Human confirmation remains a future step']) {
    assert.ok(markup.includes(boundary))
  }
  assert.match(markup, /Compare research scenarios/)
  assert.match(markup, /annual rate scenarios/)
  assert.match(markup, /Not assessed/)
  assert.match(markup, /No comparison has been run yet/)
  assert.match(markup, /research-only/)
})

test('AC-2 workspace declares scoped result and motion presentation hooks', () => {
  const markup = renderToStaticMarkup(createElement(AgenticCommercePage))
  assert.match(markup, /commerce-input-panel/)
  assert.match(markup, /commerce-submit/)
  assert.match(markup, /commerce-stepper/)
  assert.doesNotMatch(markup, /SIMULATED_TRANSACTION_COMPLETE|Demo event/)
})

test('Commerce Audit Trail renders an honest empty state without sample events', () => {
  const markup = renderToStaticMarkup(createElement(CommerceAuditTrailPage))
  assert.match(markup, /No simulated commerce sessions have been recorded yet/)
  assert.match(markup, /audit store and Agentic Commerce workflow are inactive/)
  assert.doesNotMatch(markup, /SIMULATED_TRANSACTION_COMPLETE|event_id|Demo event/)
})
