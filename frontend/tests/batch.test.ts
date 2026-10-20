import { test } from 'node:test'
import assert from 'node:assert/strict'
import { buildResultCsv, missingRequiredFields, parseCsv, sanitizeCell, summarizeBatch } from '../src/batch.ts'

test('parseCsv reads header and rows with a trailing empty line removed', () => {
  const parsed = parseCsv('A,B\n1,2\n3,4\n')
  assert.deepEqual(parsed.header, ['A', 'B'])
  assert.deepEqual(parsed.rows, [['1', '2'], ['3', '4']])
})

test('parseCsv handles quoted fields containing the delimiter', () => {
  const parsed = parseCsv('name,note\n"Smith, John",ok\n')
  assert.deepEqual(parsed.rows[0], ['Smith, John', 'ok'])
})

test('missingRequiredFields reports the 23 Taiwan fields that are absent', () => {
  const missing = missingRequiredFields(['LIMIT_BAL', 'SEX'])
  assert.ok(missing.includes('AGE'))
  assert.ok(!missing.includes('LIMIT_BAL'))
  assert.equal(missing.length, 21)
})

test('sanitizeCell neutralises spreadsheet formula injection', () => {
  assert.equal(sanitizeCell('=cmd|calc'), "'=cmd|calc")
  assert.equal(sanitizeCell('+SUM(1+1)'), "'+SUM(1+1)")
  assert.equal(sanitizeCell('-2'), "'-2")
  assert.equal(sanitizeCell('@user'), "'@user")
  assert.equal(sanitizeCell('normal text'), 'normal text')
})

test('summarizeBatch counts outcomes and keeps mean PD over successes only', () => {
  const summary = summarizeBatch({
    model_id: 'uci_taiwan_xgb',
    results: [
      { row_index: 2, borrower_reference: 'a', status: 'success', prediction: { model_id: 'uci_taiwan_xgb', probability: 0.1, predicted_class: 'Lower predicted default risk', risk_category: 'Low', calibrated: true, threshold: 0.5 } },
      { row_index: 3, borrower_reference: 'b', status: 'success', prediction: { model_id: 'uci_taiwan_xgb', probability: 0.3, predicted_class: 'Lower predicted default risk', risk_category: 'Medium', calibrated: true, threshold: 0.5 } },
      { row_index: 4, borrower_reference: 'c', status: 'error', error_message: "Field 'AGE' must be between 21 and 79." },
    ],
  })
  assert.equal(summary.total, 3)
  assert.equal(summary.succeeded, 2)
  assert.equal(summary.failed, 1)
  assert.equal(summary.meanProbability?.toFixed(4), '0.2000')
  assert.equal(summary.lowRisk, 1)
  assert.equal(summary.mediumRisk, 1)
})

test('buildResultCsv escapes quotes and sanitises injected references', () => {
  const csv = buildResultCsv({
    model_id: 'uci_taiwan_xgb',
    results: [
      { row_index: 2, borrower_reference: '=cmd|calc', status: 'error', error_message: 'quoted "message"' },
    ],
  })
  assert.ok(csv.includes("'=cmd|calc"))
  assert.ok(csv.includes('""message""'))
})
