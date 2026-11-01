import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  calculateAssessment,
  classifyResearchProbability,
  contributionDirection,
  datasetReadiness,
  formatIndianRupees,
  hasCurveEvidence,
  predictionFiveW,
  SIMULATED_SCORING_STEPS,
} from '../src/assessment.ts'

test('assessment shows PD complement and uses the research threshold comparison', () => {
  const result = calculateAssessment(0.23, 0.5)
  assert.equal(result.complement, 0.77)
  assert.equal(result.comparison, '<')
  assert.equal(result.classification, 'Lower predicted-default-risk class')
  assert.equal(classifyResearchProbability(0.5, 0.5).comparison, '>=')
  assert.match(classifyResearchProbability(0.5, 0.5).label, /Higher predicted-default-risk/)
  assert.doesNotMatch(result.classification, /approved|rejected|safe borrower/i)
})

test('five-W context retains source scope and synthetic status', () => {
  const context = predictionFiveW({ target: 'default next month', dataset: 'Credit Card Clients', geography: 'Taiwan', timeCoverage: '2005', synthetic: true, hasAttribution: false })
  assert.match(context.what, /Estimated default probability/)
  assert.match(context.who, /Synthetic demonstration/)
  assert.match(context.when, /2005/)
  assert.match(context.where, /Not validated for Indian borrowers/)
  assert.match(context.why, /no genuine local attribution/i)
})

test('attribution direction does not infer a sign when the API omits it', () => {
  assert.equal(contributionDirection('increases_risk'), 'increases_risk')
  assert.equal(contributionDirection('reduces_risk'), 'decreases_risk')
  assert.equal(contributionDirection(''), 'unknown')
})

test('INR formatting is clearly localized and ignores non-finite values', () => {
  assert.match(formatIndianRupees(125000), /1,25,000/)
  assert.match(formatIndianRupees(125000), /₹/)
  assert.doesNotMatch(formatIndianRupees(125000), /\$/)
  assert.equal(formatIndianRupees(Number.NaN), '—')
})

test('dataset readiness distinguishes research, restricted, synthetic and unavailable sources', () => {
  assert.equal(datasetReadiness({ dataset_id: 'DS001', qualification_decision: 'QUALIFIED_FOR_RESEARCH' }), 'Research Ready')
  assert.equal(datasetReadiness({ dataset_id: 'DS001', qualification_decision: 'QUALIFIED_FOR_RESEARCH', local_status: 'not downloaded' }), 'Source Unavailable')
  assert.equal(datasetReadiness({ dataset_id: 'EXT001', qualification_decision: 'BLOCKED', local_status: 'not downloaded' }), 'Source Unavailable')
  assert.equal(datasetReadiness({ dataset_id: 'DS008', qualification_decision: 'BLOCKED' }), 'Synthetic / Demo')
  assert.equal(datasetReadiness({ dataset_id: 'EXT002', qualification_decision: 'REVIEW_REQUIRED' }), 'Needs Review')
  assert.equal(datasetReadiness({ dataset_id: 'EXT003', qualification_decision: 'BLOCKED', provenance_status: 'restricted' }), 'Available — Restricted Use')
})

test('curve evidence gate accepts only finite points and simulated workflow is explicitly bounded', () => {
  assert.equal(hasCurveEvidence([{ x: 0, y: 0 }, { x: 1, y: 1 }]), true)
  assert.equal(hasCurveEvidence([{ x: 0, y: 0 }, { x: Number.NaN, y: 1 }]), false)
  assert.equal(hasCurveEvidence([{ x: 0, y: 0 }]), false)
  assert.ok(SIMULATED_SCORING_STEPS.includes('Validated-model scoring'))
})
