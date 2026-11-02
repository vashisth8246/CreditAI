import { createElement as h } from 'react'

export type AgenticCommercePageId = 'commerce' | 'commerce-audit'

export const AGENTIC_COMMERCE_NAVIGATION = [
  { id: 'commerce', title: 'Agentic Commerce', icon: '◇', section: 'AGENTIC COMMERCE' },
  { id: 'commerce-audit', title: 'Commerce Audit Trail', icon: '≋' },
] as const

export const AGENTIC_COMMERCE_STAGES = [
  'Purchase Intent',
  'Affordability / Risk Research',
  'Financing Options',
  'Comparison',
  'Recommendation',
  'Human Confirmation',
  'Simulated Transaction',
  'Audit Trail',
] as const

export function AgenticCommercePage() {
  return h('div', { className: 'page-body commerce-page' },
    h('div', { className: 'section-title' },
      h('div', null,
        h('p', { className: 'eyebrow' }, 'AC-1 FOUNDATION'),
        h('h1', null, 'Agentic Commerce'),
        h('p', { className: 'section-detail' }, 'A planned, human-controlled research/demo workflow for exploring a purchase and simulated financing options.'),
      ),
      h('span', { className: 'source-tag source-synthetic' }, 'RESEARCH / DEMO'),
    ),
    h('section', { className: 'commerce-safety panel', 'aria-label': 'Agentic Commerce safety boundaries' },
      h('strong', null, 'Research / demo only'),
      h('ul', null,
        h('li', null, 'No real loan'),
        h('li', null, 'No real payment'),
        h('li', null, 'No real purchase'),
        h('li', null, 'Human confirmation required'),
      ),
    ),
    h('section', { className: 'panel commerce-foundation' },
      h('div', { className: 'panel-heading' },
        h('div', null,
          h('h2', null, 'Foundation ready'),
          h('p', null, 'The workflow and typed contracts are documented. No agent run, financing offer, or simulated transaction has been executed.'),
        ),
        h('span', { className: 'commerce-inactive' }, 'WORKFLOW INACTIVE'),
      ),
      h('p', { className: 'commerce-next-phase' }, 'Agent workflow implementation begins in AC-2.'),
    ),
    h('section', { className: 'panel commerce-workflow' },
      h('div', { className: 'panel-heading' },
        h('div', null,
          h('h2', null, 'Approved future workflow'),
          h('p', null, 'All stages are planned and inactive in AC-1.'),
        ),
      ),
      h('ol', { className: 'commerce-stage-list', 'aria-label': 'Eight planned Agentic Commerce workflow stages' },
        ...AGENTIC_COMMERCE_STAGES.map((stage, index) => h('li', { key: stage, className: 'commerce-stage' },
          h('span', { className: 'commerce-stage-number', 'aria-hidden': 'true' }, String(index + 1).padStart(2, '0')),
          h('span', { className: 'commerce-stage-name' }, stage),
          h('span', { className: 'commerce-stage-status' }, 'Planned'),
        )),
      ),
    ),
    h('p', { className: 'commerce-research-note' }, 'Any future model output must be described as “Research risk information”. It is not a credit approval decision and does not validate Indian borrowers.'),
  )
}

export function CommerceAuditTrailPage() {
  return h('div', { className: 'page-body commerce-page' },
    h('div', { className: 'section-title' },
      h('div', null,
        h('p', { className: 'eyebrow' }, 'AGENTIC COMMERCE · AC-1'),
        h('h1', null, 'Commerce Audit Trail'),
        h('p', { className: 'section-detail' }, 'Audit event contracts are defined for a future simulation workflow. AC-1 does not persist or fabricate events.'),
      ),
      h('span', { className: 'source-tag source-unavailable' }, 'NO EVENTS'),
    ),
    h('section', { className: 'panel commerce-audit-empty', 'aria-label': 'Commerce audit trail empty state' },
      h('span', { className: 'empty-icon', 'aria-hidden': 'true' }, '≋'),
      h('h2', null, 'No simulated commerce sessions have been recorded yet.'),
      h('p', null, 'The audit store and Agentic Commerce workflow are inactive in AC-1.'),
    ),
  )
}
