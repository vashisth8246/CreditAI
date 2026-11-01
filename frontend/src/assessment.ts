import type { InventoryItem } from './analytics'

export type Direction = 'increases_risk' | 'decreases_risk' | 'unknown'

export function classifyResearchProbability(probability: number, threshold: number): {
  comparison: '<' | '>='
  label: string
} {
  return probability < threshold
    ? { comparison: '<', label: 'Lower predicted-default-risk class' }
    : { comparison: '>=', label: 'Higher predicted-default-risk class' }
}

export function calculateAssessment(probability: number, threshold: number) {
  const classification = classifyResearchProbability(probability, threshold)
  return {
    probability,
    complement: 1 - probability,
    threshold,
    comparison: classification.comparison,
    classification: classification.label,
  }
}

export function predictionFiveW(input: {
  target: string
  dataset: string
  geography: string
  timeCoverage: string
  synthetic: boolean
  hasAttribution: boolean
}) {
  return {
    what: `Estimated default probability for the target “${input.target}”. The complement is arithmetic only.`,
    why: input.hasAttribution
      ? 'The genuine model attribution below shows which inputs moved this fitted model output. It describes model behavior, not cause.'
      : 'No genuine local attribution was returned for this result, so no drivers are inferred.',
    who: input.synthetic
      ? 'Synthetic demonstration profile — no real person.'
      : 'The submitted feature profile shown below; identity is not collected or inferred here.',
    when: `Target outcome: ${input.target}. Dataset period: ${input.timeCoverage || 'not supplied by the model metadata'}. No additional horizon is inferred.`,
    where: `${input.dataset} — ${input.geography}.${input.geography.toLowerCase() === 'taiwan' ? ' Not validated for Indian borrowers.' : ''}`,
  }
}

export function formatIndianRupees(value: number): string {
  if (!Number.isFinite(value)) return '—'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value)
}

export function contributionDirection(direction: string): Direction {
  if (direction === 'increases_risk') return 'increases_risk'
  if (direction === 'decreases_risk' || direction === 'reduces_risk') return 'decreases_risk'
  return 'unknown'
}

export type ReadinessStatus = 'Research Ready' | 'Available — Restricted Use' | 'Evidence Gap' | 'Synthetic / Demo' | 'Needs Review' | 'Source Unavailable'

export function datasetReadiness(item: InventoryItem): ReadinessStatus {
  const id = String(item.dataset_id ?? '')
  const local = String(item.local_status ?? '').toLowerCase()
  const decision = String(item.qualification_decision ?? '').toUpperCase()
  if (/not downloaded|missing|unavailable|not present|damaged|unreadable/.test(local)) return 'Source Unavailable'
  if (decision === 'QUALIFIED_FOR_RESEARCH') return 'Research Ready'
  if (/^DS00[8-9]$|^DS01[0-3]$/.test(id)) return 'Synthetic / Demo'
  if (decision === 'REVIEW_REQUIRED') return 'Needs Review'
  if (decision === 'BLOCKED' && item.provenance_status) return 'Available — Restricted Use'
  return 'Evidence Gap'
}

export function hasCurveEvidence(points: unknown): boolean {
  return Array.isArray(points) && points.length >= 2 && points.every((point) =>
    typeof point === 'object' && point !== null &&
    Number.isFinite((point as { x?: unknown }).x) && Number.isFinite((point as { y?: unknown }).y),
  )
}

export const SIMULATED_SCORING_STEPS = [
  'Request',
  'Schema validation',
  'Data-quality validation',
  'Feature processing',
  'Validated-model scoring',
  'Response',
  'Monitoring and audit logging',
] as const
