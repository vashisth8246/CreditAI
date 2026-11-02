import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  assignMapping,
  buildAnalysisReport,
  buildHistogram,
  buildResultCsv,
  buildTemplateCsv,
  buildValidationCsv,
  buildXlsxPayload,
  filterResults,
  formatBytes,
  formatProbability,
  mappingIssues,
  median,
  missingRequiredFields,
  parseCsv,
  reverseMapping,
  repaymentComplement,
  sanitizeCell,
  sortResults,
  selectPdExamples,
  summarizeBatch,
  TAIWAN_REQUIRED_FIELDS,
} from '../src/batch.ts'
import type { BatchPredictionResult, BatchRowResult, Mapping } from '../src/batch.ts'

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
  assert.equal(summary.medianProbability?.toFixed(4), '0.2000')
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

test('buildTemplateCsv contains every required header plus a synthetic row', () => {
  const csv = buildTemplateCsv()
  const [header, row] = csv.trim().split('\r\n')
  const cols = header.split(',')
  assert.equal(cols.length, 24)
  for (const field of TAIWAN_REQUIRED_FIELDS) assert.ok(cols.includes(field), `missing ${field}`)
  assert.ok(cols.includes('borrower_reference'))
  assert.equal(row.split(',').length, 24)
})

test('missingRequiredFields tolerates case and space differences', () => {
  const headers = TAIWAN_REQUIRED_FIELDS.map((f) => f.toLowerCase().replaceAll('_', ' '))
  assert.deepEqual(missingRequiredFields(headers), [])
})

test('assignMapping moves a target and removes empty assignments', () => {
  const mapping: Mapping = { '0': 'LIMIT_BAL', '1': 'SEX' }
  const moved = assignMapping(mapping, 2, 'LIMIT_BAL')
  assert.deepEqual(moved, { '1': 'SEX', '2': 'LIMIT_BAL' })
  assert.deepEqual(assignMapping(moved, 1, ''), { '2': 'LIMIT_BAL' })
  assert.deepEqual(reverseMapping(moved), { SEX: 1, LIMIT_BAL: 2 })
})

test('mappingIssues reports missing and duplicated model features', () => {
  const mapping: Mapping = { '0': 'LIMIT_BAL', '1': 'SEX', '2': 'LIMIT_BAL' }
  const issues = mappingIssues(mapping, ['LIMIT_BAL', 'SEX', 'AGE'])
  assert.deepEqual(issues.duplicated, ['LIMIT_BAL'])
  assert.deepEqual(issues.missing, ['AGE'])
})

test('buildHistogram assigns every finite probability exactly once', () => {
  const bins = buildHistogram([0, 0.049, 0.05, 0.2, 0.399, 0.4, 0.99, 1, Number.NaN])
  assert.deepEqual(bins.map((bin) => bin.count), [2, 1, 0, 2, 1, 2])
  assert.equal(bins.reduce((total, bin) => total + bin.count, 0), 8)
})

test('median handles odd, even and empty inputs', () => {
  assert.equal(median([0.4, 0.1, 0.2]), 0.2)
  assert.equal(median([0.4, 0.1, 0.2, 0.3]), 0.25)
  assert.equal(median([]), null)
  assert.equal(median([Number.NaN]), null)
})

test('formatProbability and formatBytes keep unavailable values readable', () => {
  assert.equal(formatProbability(0.08206632971007599, 2), '8.21%')
    assert.equal(formatProbability(null), String.fromCharCode(0x2014))
    assert.equal(formatProbability(Number.NaN), String.fromCharCode(0x2014))
  assert.equal(formatBytes(512), '512 B')
  assert.equal(formatBytes(2048), '2.0 KB')
    assert.equal(formatBytes(-1), String.fromCharCode(0x2014))
})

test('repayment complement is only computed for a valid binary PD', () => {
  assert.equal(repaymentComplement(0.23), 0.77)
  assert.equal(repaymentComplement(0), 1)
  assert.equal(repaymentComplement(1), 0)
  assert.equal(repaymentComplement(null), null)
  assert.equal(repaymentComplement(Number.NaN), null)
  assert.equal(repaymentComplement(1.01), null)
})

function row(overrides: Partial<BatchRowResult> & { row_index: number }): BatchRowResult {
  return {
    borrower_reference: `ref-${overrides.row_index}`,
    status: 'success',
    prediction: {
      model_id: 'uci_taiwan_xgb',
      probability: 0.1,
      predicted_class: 'Lower predicted default risk',
      risk_category: 'Low',
      calibrated: true,
      threshold: 0.5,
    },
    ...overrides,
  }
}

function sampleResult(): BatchPredictionResult {
  return {
    model_id: 'uci_taiwan_xgb',
    file_name: 'portfolio.xlsx',
    file_format: 'xlsx',
    generated_at: '2026-10-21T00:00:00+00:00',
    calibrated: true,
    calibration_method: 'Platt scaling (sigmoid)',
    thresholds: { classification: 0.5, low_upper: 0.25, medium_upper: 0.5 },
    sheets: [
      { name: 'Alpha', total_rows: 2, scored: 2, failed: 0 },
      { name: 'Beta', total_rows: 2, scored: 1, failed: 1 },
    ],
    results: [
      row({ result_index: 1, sheet_name: 'Alpha', source_row: 2, row_index: 1, borrower_reference: 'alpha-1', prediction: { model_id: 'uci_taiwan_xgb', probability: 0.04, predicted_class: 'Lower predicted default risk', risk_category: 'Low', calibrated: true, threshold: 0.5 } }),
      row({ result_index: 2, sheet_name: 'Alpha', source_row: 3, row_index: 2, borrower_reference: 'alpha-2', prediction: { model_id: 'uci_taiwan_xgb', probability: 0.32, predicted_class: 'Lower predicted default risk', risk_category: 'Medium', calibrated: true, threshold: 0.5 } }),
      row({ result_index: 3, sheet_name: 'Beta', source_row: 2, row_index: 1, borrower_reference: 'beta-1', prediction: { model_id: 'uci_taiwan_xgb', probability: 0.72, predicted_class: 'Higher predicted default risk', risk_category: 'High', calibrated: true, threshold: 0.5 } }),
      row({ result_index: 4, sheet_name: 'Beta', source_row: 3, row_index: 2, borrower_reference: 'beta-bad', status: 'error', prediction: undefined, error_message: 'EDUCATION: value is not one of the allowed category codes.' }),
    ],
  }
}

test('summarizeBatch keeps sheet denominators and actual risk counts', () => {
  const summary = summarizeBatch(sampleResult())
  assert.equal(summary.total, 4)
  assert.equal(summary.succeeded, 3)
  assert.equal(summary.failed, 1)
  assert.equal(summary.lowRisk, 1)
  assert.equal(summary.mediumRisk, 1)
  assert.equal(summary.highRisk, 1)
  assert.equal(summary.unknownRisk, 0)
  assert.equal(summary.medianProbability, 0.32)
  const alpha = summary.sheets.find((sheet) => sheet.name === 'Alpha')
  const beta = summary.sheets.find((sheet) => sheet.name === 'Beta')
  assert.deepEqual(alpha, { name: 'Alpha', total: 2, scored: 2, failed: 0, meanProbability: 0.18, lowRisk: 1, mediumRisk: 1, highRisk: 0 })
  assert.deepEqual(beta, { name: 'Beta', total: 2, scored: 1, failed: 1, meanProbability: 0.72, lowRisk: 0, mediumRisk: 0, highRisk: 1 })
})

test('summarizeBatch returns unavailable statistics when no row is scored', () => {
  const summary = summarizeBatch({
    model_id: 'uci_taiwan_xgb',
    results: [row({ row_index: 1, status: 'error', prediction: undefined, error_message: 'bad' })],
  })
  assert.equal(summary.succeeded, 0)
  assert.equal(summary.meanProbability, null)
  assert.equal(summary.medianProbability, null)
  assert.equal(summary.histogram.reduce((total, bin) => total + bin.count, 0), 0)
})

test('filterResults combines status, risk and free-text search', () => {
  const results = sampleResult().results
  assert.deepEqual(filterResults(results, 'High', '').map((item) => item.borrower_reference), ['beta-1'])
  assert.deepEqual(filterResults(results, 'failed', '').map((item) => item.borrower_reference), ['beta-bad'])
  assert.deepEqual(filterResults(results, 'all', 'alpha').map((item) => item.result_index), [1, 2])
  assert.deepEqual(filterResults(results, 'all', 'not one of').map((item) => item.result_index), [4])
  assert.deepEqual(filterResults(results, 'scored', 'alpha-1').map((item) => item.result_index), [1])
})

test('sortResults sorts without mutating the source order', () => {
  const results = sampleResult().results
  const original = results.map((item) => item.result_index)
  assert.deepEqual(sortResults(results, 'probability', 'desc').map((item) => item.result_index), [3, 2, 1, 4])
  assert.deepEqual(sortResults(results, 'reference', 'asc').map((item) => item.borrower_reference), ['alpha-1', 'alpha-2', 'beta-1', 'beta-bad'])
  assert.deepEqual(results.map((item) => item.result_index), original)
})

test('buildResultCsv keeps order, sheet, source row, reference and failures', () => {
  const csv = buildResultCsv(sampleResult())
  const lines = csv.split('\r\n')
  assert.equal(lines.length, 5)
  assert.ok(lines[0].startsWith('result_index,sheet_name,source_row'))
  assert.ok(lines[1].includes('"Alpha","2","1","alpha-1"'))
  assert.ok(lines[0].includes('non_default_complement_percent'))
  assert.ok(lines[1].includes('"0.96","96.00%"'))
  assert.ok(lines[3].includes('"Beta","2","1","beta-1"'))
  assert.ok(lines[4].includes('"beta-bad","error"'))
  assert.ok(csv.indexOf('alpha-1') < csv.indexOf('beta-1'))
})

test('batch explanation CSV includes threshold, model drivers, context and limitations', () => {
  const sample = sampleResult()
  const first = sample.results[0]
  if (first.prediction) {
    first.prediction.feature_contributions = [
      { feature: 'PAY_0', contribution: 0.31, direction: 'increases_risk' },
      { feature: 'PAY_AMT1', contribution: 0.08, direction: 'decreases_risk' },
    ]
    first.prediction.dataset_name = 'Default of Credit Card Clients'
    first.prediction.geography = 'Taiwan'
    first.prediction.calibration_method = 'Platt scaling'
  }
  first.submitted_features = { PAY_0: 2, PAY_AMT1: 500 }
  const csv = buildResultCsv(sample)
  assert.match(csv, /research_classification/)
  assert.match(csv, /threshold_comparison/)
  assert.match(csv, /risk_increasing_drivers/)
  assert.match(csv, /Default of Credit Card Clients \(Taiwan\); Platt scaling/)
  assert.match(csv, /not validated for Indian borrowers or lending/)
})

test('portfolio PD examples use the scored rows without changing their order', () => {
  const sample = sampleResult()
  const examples = selectPdExamples(sample)
  assert.equal(examples.lowest?.borrower_reference, 'alpha-1')
  assert.equal(examples.highest?.borrower_reference, 'beta-1')
  assert.equal(selectPdExamples({ model_id: 'x', results: [] }).lowest, null)
})

test('buildValidationCsv exports real validation issues and neutralises formulas', () => {
  const csv = buildValidationCsv([
    {
      name: 'Portfolio A',
      errors: [
        { source_row: 4, column: 'EDUCATION', source_column: 'EDUCATION', message: '=HYPERLINK("http://bad")' },
      ],
    },
  ])
  const lines = csv.split('\r\n')
  assert.equal(lines[0], 'sheet_name,source_row,column,source_column,message')
  assert.ok(lines[1].includes('"Portfolio A","4","EDUCATION"'))
  assert.ok(lines[1].includes("'=HYPERLINK"))
})

test('buildXlsxPayload sends real results with denominators and metadata', () => {
  const result = sampleResult()
  const summary = summarizeBatch(result)
  const payload = buildXlsxPayload(result, summary, { file_name: 'portfolio.xlsx', sheet_names: ['Alpha', 'Beta'] })
  assert.equal(payload.results.length, 4)
  assert.equal(payload.summary.total, 4)
  assert.equal(payload.summary.succeeded, 3)
  assert.equal(payload.summary.failed, 1)
  assert.deepEqual(payload.summary.histogram.map((bin) => bin.count), [1, 0, 0, 1, 0, 1])
  assert.equal(payload.metadata.file_name, 'portfolio.xlsx')
  assert.deepEqual(payload.metadata.sheet_names, ['Alpha', 'Beta'])
  assert.equal(payload.metadata.calibration_method, 'Platt scaling (sigmoid)')
})

test('buildAnalysisReport includes evidence, denominators, limitations and validation errors', () => {
  const result = sampleResult()
  const summary = summarizeBatch(result)
  const report = buildAnalysisReport(result, summary, { file_name: 'portfolio.xlsx', sheet_names: ['Alpha', 'Beta'] }, [
    {
      name: 'Beta',
      errors: [{ source_row: 3, column: 'EDUCATION', source_column: 'EDUCATION', message: 'Invalid category code' }],
      warnings: [],
    },
  ])
  assert.ok(report.startsWith('# CreditAI Batch Analysis Report'))
  assert.ok(report.includes('portfolio.xlsx'))
  assert.ok(report.includes('Total rows submitted: 4'))
  assert.ok(report.includes('Successfully scored: 3'))
  assert.ok(report.includes('Failed or rejected: 1'))
  assert.ok(report.includes('Mean estimated PD: 36.00% (denominator: 3 scored rows)'))
  assert.ok(report.includes('Median estimated PD: 32.00% (denominator: 3 scored rows)'))
  assert.ok(report.includes('Low risk (<25%): 1 of 3 scored rows (33.3%)'))
    assert.ok(report.includes('| 60' + String.fromCharCode(0x2013) + '100% | 1 | 33.3% |'))
  assert.ok(report.includes('Invalid category code'))
  assert.ok(report.includes('not validated for Indian borrowers'))
  assert.ok(report.includes('not_validated'))
})
