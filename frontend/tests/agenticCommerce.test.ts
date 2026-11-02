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

test('Agentic Commerce foundation renders all planned stages and safety boundaries', () => {
  const markup = renderToStaticMarkup(createElement(AgenticCommercePage))
  assert.equal((markup.match(/commerce-stage-status/g) ?? []).length, 8)
  for (const stage of AGENTIC_COMMERCE_STAGES) assert.ok(markup.includes(stage))
  for (const boundary of ['RESEARCH / DEMO', 'No real loan', 'No real payment', 'No real purchase', 'Human confirmation required']) {
    assert.ok(markup.includes(boundary))
  }
  assert.match(markup, /Foundation ready/)
  assert.match(markup, /workflow implementation begins in AC-2/)
  assert.match(markup, /No agent run, financing offer, or simulated transaction has been executed/)
})

test('Commerce Audit Trail renders an honest empty state without sample events', () => {
  const markup = renderToStaticMarkup(createElement(CommerceAuditTrailPage))
  assert.match(markup, /No simulated commerce sessions have been recorded yet/)
  assert.match(markup, /audit store and Agentic Commerce workflow are inactive/)
  assert.doesNotMatch(markup, /SIMULATED_TRANSACTION_COMPLETE|event_id|Demo event/)
})
