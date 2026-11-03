import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import {
  AGENTIC_COMMERCE_NAVIGATION,
  AGENTIC_COMMERCE_STAGES,
  AgenticCommercePage,
  CommerceAuditTrailPage,
  EXHIBITION_EXAMPLE,
  parseResearchProfile,
} from '../src/agenticCommerce.ts'
import { RESEARCH_FIELD_PRESENTATION, researchFieldTitle } from '../src/commerceFieldGuidance.ts'

test('Agentic Commerce navigation remains a distinct section', () => {
  assert.deepEqual(AGENTIC_COMMERCE_NAVIGATION.map(({ id }) => id), ['commerce', 'commerce-audit'])
  assert.equal(AGENTIC_COMMERCE_NAVIGATION[0].section, 'AGENTIC COMMERCE')
  assert.equal(AGENTIC_COMMERCE_NAVIGATION[1].title, 'Commerce Audit Trail')
})

test('AC-3 journey lists each stage without claiming future work is complete', () => {
  const markup = renderToStaticMarkup(createElement(AgenticCommercePage))
  for (const stage of AGENTIC_COMMERCE_STAGES) assert.ok(markup.includes(stage))
  assert.match(markup, /Awaiting input/)
  assert.match(markup, /Pending · not executed/)
  assert.match(markup, /Pending · no events recorded/)
})

test('AC-3 starts with empty user fields, transparent provenance, and explicit confirmation boundary', () => {
  const markup = renderToStaticMarkup(createElement(AgenticCommercePage))
  for (const label of ['USER INPUT', 'RESEARCH DATA SOURCE', 'no sample borrower will be substituted', 'Human confirmation required']) {
    assert.ok(markup.includes(label), `missing ${label}`)
  }
  assert.match(markup, /The form starts blank/)
  assert.match(markup, /User-entered hypothetical rates/)
  assert.match(markup, /Load exhibition example/)
  assert.doesNotMatch(markup, /EXAMPLE \/ TEST INPUT/)
  assert.doesNotMatch(markup, /Confirm Simulation/)
  assert.doesNotMatch(markup, /Synthetic laptop example|₹85,000|90,000/)
  assert.match(markup, /No payment or order/)
})

test('commerce starts with user purchase intent and explains the AC-1 to AC-2 research flow', () => {
  const markup = renderToStaticMarkup(createElement(AgenticCommercePage))
  assert.match(markup, /AC-1 → AC-2 → AC-3/)
  assert.match(markup, /aria-label="AC-1 purchase intent"/)
  assert.match(markup, /Continue to research profile/)
  assert.doesNotMatch(markup, /LIMIT_BAL/)
})

test('research profile parsing requires every current-schema field and validates categories and bounds', () => {
  const rawFeatures = ['LIMIT_BAL', 'SEX', 'EDUCATION', 'MARRIAGE', 'AGE', 'PAY_0', 'PAY_2', 'PAY_3', 'PAY_4', 'PAY_5', 'PAY_6', ...Array.from({ length: 6 }, (_, i) => `BILL_AMT${i + 1}`), ...Array.from({ length: 6 }, (_, i) => `PAY_AMT${i + 1}`)]
  const schema = { model_id: 'uci_taiwan_xgb', raw_features: Object.fromEntries(rawFeatures.map((name) => [name, { type: 'numeric' as const, description: name, required: true, ...(name === 'SEX' ? { values: [1, 2] } : {}), ...(name === 'AGE' ? { range: [21, 79] } : {}) }])) }
  const blank = Object.fromEntries(rawFeatures.map((name) => [name, '']))
  assert.throws(() => parseResearchProfile(blank, schema), /LIMIT_BAL is required/)
  const populated = Object.fromEntries(rawFeatures.map((name) => [name, name === 'SEX' ? '2' : name === 'AGE' ? '35' : '0']))
  assert.equal(Object.keys(parseResearchProfile(populated, schema)).length, 23)
  assert.throws(() => parseResearchProfile({ ...populated, SEX: '3' }, schema), /SEX must be one of 1, 2/)
  assert.throws(() => parseResearchProfile({ ...populated, AGE: '80' }, schema), /AGE must be between 21 and 79/)
})

test('AC-2 comparison remains available as a simulation-only route boundary', () => {
  const markup = renderToStaticMarkup(createElement(AgenticCommercePage))
  assert.match(markup, /Research simulation only/)
  assert.match(markup, /No lender offer/)
  assert.match(markup, /Simulated annual rate assumptions/)
  assert.match(markup, /not lender offers or market pricing/)
})

test('exhibition example is explicit, complete, and distinct from the verified dataset workflow', () => {
  assert.equal(Object.keys(EXHIBITION_EXAMPLE.research).length, 23)
  const schema = { model_id: 'uci_taiwan_xgb', raw_features: Object.fromEntries(Object.keys(EXHIBITION_EXAMPLE.research).map((name) => [name, { type: 'numeric' as const, description: name, required: true, ...(name === 'SEX' ? { values: [1, 2] } : name === 'EDUCATION' ? { values: [1, 2, 3, 4, 5, 6] } : name === 'MARRIAGE' ? { values: [1, 2, 3] } : name.startsWith('PAY_') && !name.startsWith('PAY_AMT') ? { values: [-2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9] } : {}) }])) }
  assert.equal(Object.keys(parseResearchProfile(EXHIBITION_EXAMPLE.research, schema)).length, 23)
  assert.equal(EXHIBITION_EXAMPLE.purchase.price, '85000')
})

test('every current Taiwan raw model field has centralized title and group metadata', () => {
  const names = ['LIMIT_BAL', 'SEX', 'EDUCATION', 'MARRIAGE', 'AGE', 'PAY_0', 'PAY_2', 'PAY_3', 'PAY_4', 'PAY_5', 'PAY_6', ...Array.from({ length: 6 }, (_, i) => `BILL_AMT${i + 1}`), ...Array.from({ length: 6 }, (_, i) => `PAY_AMT${i + 1}`)]
  assert.equal(Object.keys(RESEARCH_FIELD_PRESENTATION).length, 23)
  for (const name of names) assert.notEqual(researchFieldTitle(name), name)
  assert.match(researchFieldTitle('PAY_0'), /September 2005/)
  assert.match(researchFieldTitle('BILL_AMT6'), /April 2005/)
})

test('Commerce Audit Trail shows an honest empty state before any local session exists', () => {
  const markup = renderToStaticMarkup(createElement(CommerceAuditTrailPage))
  assert.match(markup, /No simulated commerce sessions are recorded in this browser/)
  assert.match(markup, /No audit events are fabricated/)
  assert.match(markup, /WORKFLOW PREVIEW · NO EVENTS RECORDED YET/)
  assert.match(markup, /Go to Agentic Commerce/)
})
