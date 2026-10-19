import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { availabilityState, dataSourceLabel, filterInventory, formatMetric, formatPercent, safeProbability } from '../src/analytics.ts'
import { DatasetInventoryTable } from '../src/DatasetInventoryTable.ts'

describe('Phase 6.1 dashboard helpers', () => {
  it('formats metrics and preserves missing values as unavailable', () => {
    assert.equal(formatMetric(0.7056), '0.7056')
    assert.equal(formatMetric(null), '—')
    assert.equal(formatMetric('not-a-number'), '—')
    assert.equal(formatPercent(0.1998), '20.0%')
    assert.equal(formatPercent(null), '—')
  })

  it('never converts a not_validated null score into a numeric probability', () => {
    assert.equal(safeProbability('not_validated', null), 'Not validated')
    assert.equal(safeProbability('demo_only', 0.2), 'Not validated')
    assert.equal(safeProbability('validated', null), 'Not validated')
    assert.equal(safeProbability('validated', 1.2), 'Unavailable')
    assert.equal(safeProbability('validated', 0.2), '20.0%')
  })

  it('exposes source labels and distinct data availability states', () => {
    assert.equal(dataSourceLabel('historical'), 'HISTORICAL RESEARCH DATA')
    assert.equal(dataSourceLabel('synthetic'), 'SYNTHETIC DEMO')
    assert.equal(dataSourceLabel('live-unvalidated'), 'LIVE API — NOT VALIDATED')
    assert.equal(dataSourceLabel('unavailable'), 'DATA UNAVAILABLE')
    assert.equal(availabilityState(true, null, null), 'loading')
    assert.equal(availabilityState(false, 'offline', null), 'error')
    assert.equal(availabilityState(false, null, []), 'empty')
    assert.equal(availabilityState(false, null, [1]), 'ready')
  })

  it('filters dataset inventory by name, target and qualification decision', () => {
    const items = [
      { dataset_id: 'DS001', dataset_name: 'LendingClub', qualification_decision: 'QUALIFIED_FOR_RESEARCH', local_status: 'present', source_url: '', target_definition: 'Closed loan outcome' },
      { dataset_id: 'EXT001', dataset_name: 'Vehicle Finance', qualification_decision: 'BLOCKED', local_status: 'not downloaded', source_url: '', target_definition: 'First EMI default' },
    ]
    assert.equal(filterInventory(items, 'first emi', 'all').length, 1)
    assert.equal(filterInventory(items, '', 'QUALIFIED_FOR_RESEARCH').length, 1)
    assert.equal(filterInventory(items, 'missing', 'all').length, 0)
  })

  it('renders inventory rows with target, source, record count and qualification state', () => {
    const item = {
      dataset_id: 'DS001', dataset_name: 'LendingClub', qualification_decision: 'QUALIFIED_FOR_RESEARCH',
      local_status: 'present', source_url: '', target_definition: 'Closed loan outcome',
      row_count: 2260701, target_column: 'loan_status', license_and_access: 'Terms unverified',
    }
    const html = renderToStaticMarkup(createElement(DatasetInventoryTable, { items: [item] }))
    assert.match(html, /LendingClub/)
    assert.match(html, /2,260,701/)
    assert.match(html, /loan_status/)
    assert.match(html, /HISTORICAL RESEARCH DATA/)
    assert.match(html, /Qualified for research/)
    assert.doesNotMatch(html, /borrower_id|default_probability/)
  })
})
