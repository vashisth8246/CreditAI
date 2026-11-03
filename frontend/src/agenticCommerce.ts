import { createElement as h, useState } from 'react'
import type { FormEvent } from 'react'

export type AgenticCommercePageId = 'commerce' | 'commerce-audit'

export const AGENTIC_COMMERCE_NAVIGATION = [
  { id: 'commerce', title: 'Agentic Commerce', icon: '◇', section: 'AGENTIC COMMERCE' },
  { id: 'commerce-audit', title: 'Commerce Audit Trail', icon: '≋' },
] as const

type ComparisonOption = { option_id: string; display_name: string; annual_rate_percent: string; estimated_monthly_payment: string; estimated_total_payment: string; estimated_total_interest: string; payment_to_income_ratio: string | null; estimated_remaining_income_after_obligations: string; research_notes: string }
type ComparisonResult = { currency: string; purchase_price: string; down_payment: string; financed_amount: string; requested_tenure_months: number; options: ComparisonOption[]; preferred_option_id: string; recommendation_explanation: string; comparison_factors: string[]; event_summary: string }
const API_BASE = typeof import.meta.env !== 'undefined' ? import.meta.env.VITE_API_BASE_URL || '' : ''
function money(value: string | number, currency: string) { return new Intl.NumberFormat('en-IN', { style: 'currency', currency, maximumFractionDigits: 0 }).format(Number(value)) }
function createCommerceSessionId() { return globalThis.crypto.randomUUID() }

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
  const [result, setResult] = useState<ComparisonResult | null>(null)
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const [values, setValues] = useState({ product: 'Synthetic laptop example', category: 'electronics', price: '85000', down: '15000', tenure: '18', income: '90000', obligations: '18000', rate1: '8', rate2: '12', rate3: '16' })
  const update = (key: keyof typeof values) => (event: { target: { value: string } }) => setValues((current) => ({ ...current, [key]: event.target.value }))
  async function compare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setPending(true); setError('')
    try {
      const rates = [values.rate1, values.rate2, values.rate3].filter((value) => value.trim() !== '').map(Number)
      const response = await fetch(`${API_BASE}/v1/agentic-commerce/compare`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ intent: { session_id: createCommerceSessionId(), product_name: values.product, product_category: values.category, product_price: values.price, down_payment: values.down, requested_tenure_months: Number(values.tenure), monthly_income: values.income, existing_monthly_obligations: values.obligations, currency: 'INR' }, annual_rate_scenarios_percent: rates }) })
      if (!response.ok) { let message = `Comparison request failed (${response.status}).`; try { const body = await response.json() as { error?: { message?: string } }; message = body.error?.message ?? message } catch { /* status fallback */ }; throw new Error(message) }
      setResult(await response.json() as ComparisonResult)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'The commerce research API could not complete the comparison.'); setResult(null) }
    finally { setPending(false) }
  }
  const field = (label: string, key: keyof typeof values, type = 'text') => h('label', { className: 'commerce-field', key }, h('span', null, label), h('input', { type, min: type === 'number' ? '0' : undefined, step: type === 'number' ? 'any' : undefined, value: values[key], required: true, onChange: update(key) }))

  return h('div', { className: 'page-body commerce-page commerce-workspace' },
    h('div', { className: 'section-title' },
      h('div', null,
        h('p', { className: 'eyebrow' }, 'AC-2 · COMMERCE INTELLIGENCE'),
        h('h1', null, 'Compare research scenarios'),
        h('p', { className: 'section-detail' }, 'Explore transparent payment estimates using editable illustrative rate assumptions.'),
      ),
      h('span', { className: 'source-tag source-synthetic' }, 'RESEARCH SIMULATION'),
    ),
    h('section', { className: 'commerce-safety panel', 'aria-label': 'Agentic Commerce safety boundaries' },
      h('strong', null, 'Research simulation only'),
      h('ul', null,
        h('li', null, 'No lender offers'),
        h('li', null, 'No credit decision'),
        h('li', null, 'No transaction execution'),
        h('li', null, 'Human confirmation remains a future step'),
      ),
    ),
    h('ol', { className: 'commerce-stage-list commerce-stepper', 'aria-label': 'Commerce journey stage status' },
      ...AGENTIC_COMMERCE_STAGES.map((stage, index) => {
        const complete = Boolean(result) && index === 0
        const active = (!result && index === 0) || (Boolean(result) && index >= 2 && index <= 4)
        const notAssessed = index === 1
        return h('li', { key: stage, className: `commerce-stage ${complete ? 'is-complete' : active ? 'is-current' : 'is-future'}` },
          h('span', { className: 'commerce-stage-number', 'aria-hidden': 'true' }, String(index + 1).padStart(2, '0')),
          h('span', { className: 'commerce-stage-name' }, stage),
          h('span', { className: 'commerce-stage-status' }, complete ? 'Complete' : active ? 'AC-2' : notAssessed ? 'Not assessed' : 'Future'))
      }),
    ),
    h('section', { className: 'panel commerce-input-panel' },
      h('div', { className: 'panel-heading' }, h('div', null, h('p', { className: 'eyebrow' }, 'PURCHASE CONTEXT'), h('h2', null, 'Set comparison assumptions'), h('p', null, 'The initial rate values are examples. Edit them to explore scenarios; they are never lender pricing.'))),
      h('form', { className: 'commerce-form', onSubmit: compare },
        h('div', { className: 'commerce-fields' }, field('Product / purchase label', 'product'), field('Category', 'category'), field('Purchase price (INR)', 'price', 'number'), field('Down payment (INR)', 'down', 'number'), field('Requested tenure (months)', 'tenure', 'number'), field('Monthly income context (INR)', 'income', 'number'), field('Existing monthly obligations (INR)', 'obligations', 'number')),
        h('div', { className: 'commerce-rate-assumptions' }, h('div', null, h('strong', null, 'Illustrative annual rate scenarios'), h('span', null, 'Edit two or three distinct rates from 0% to 100%')),
          h('div', { className: 'commerce-rate-fields' }, field('Scenario A · %', 'rate1', 'number'), field('Scenario B · %', 'rate2', 'number'), field('Scenario C · % (optional)', 'rate3', 'number'))),
        h('button', { type: 'submit', className: 'button-primary commerce-submit', disabled: pending }, pending ? h('span', { className: 'commerce-pending' }, h('span', { className: 'commerce-spinner', 'aria-hidden': 'true' }), 'Comparing scenarios…') : 'Compare simulated scenarios'),
        error && h('p', { className: 'commerce-error', role: 'alert' }, error),
      ),
    ),
    result && h('div', { className: 'commerce-results', key: result.preferred_option_id },
      h('section', { className: 'commerce-summary-grid' }, ...[
        ['Purchase price', money(result.purchase_price, result.currency)], ['Down payment', money(result.down_payment, result.currency)], ['Estimated amount financed', money(result.financed_amount, result.currency)], ['Requested tenure', `${result.requested_tenure_months} months`],
      ].map(([label, value]) => h('div', { className: 'panel commerce-summary-card', key: label }, h('span', null, label), h('strong', null, value)))),
      h('section', { className: 'panel commerce-options-panel' },
        h('div', { className: 'panel-heading' }, h('div', null, h('p', { className: 'eyebrow' }, 'SIMULATED FINANCING'), h('h2', null, 'Compare the scenarios'), h('p', null, 'Reducing-balance payment estimates; each scenario uses the same tenure.')), h('span', { className: 'commerce-inactive' }, 'ILLUSTRATIVE ASSUMPTIONS')),
        h('div', { className: 'commerce-options' }, ...result.options.map((option, index) => {
          const interestMax = Math.max(...result.options.map((item) => Number(item.estimated_total_interest)), 1)
          return h('article', { className: `commerce-option ${option.option_id === result.preferred_option_id ? 'is-preferred' : ''}`, key: option.option_id, style: { animationDelay: `${index * 70}ms` } },
            h('div', { className: 'commerce-option-head' }, h('div', null, h('span', { className: 'commerce-demo-badge' }, 'SIMULATED'), h('h3', null, option.display_name)), option.option_id === result.preferred_option_id && h('span', { className: 'commerce-preferred-badge' }, 'Research-preferred')),
            h('div', { className: 'commerce-payment' }, h('strong', null, money(option.estimated_monthly_payment, result.currency)), h('span', null, 'estimated / month')),
            h('div', { className: 'commerce-option-facts' }, h('div', null, h('span', null, 'Assumed annual rate'), h('strong', null, `${Number(option.annual_rate_percent).toFixed(2)}%`)), h('div', null, h('span', null, 'Total repayment'), h('strong', null, money(option.estimated_total_payment, result.currency))), h('div', null, h('span', null, 'Total interest'), h('strong', null, money(option.estimated_total_interest, result.currency))), h('div', null, h('span', null, 'Payment / income'), h('strong', null, option.payment_to_income_ratio === null ? 'Unavailable' : `${(Number(option.payment_to_income_ratio) * 100).toFixed(1)}%`)), h('div', null, h('span', null, 'Income after obligations + payment'), h('strong', null, money(option.estimated_remaining_income_after_obligations, result.currency)))),
            h('div', { className: 'commerce-interest-track', 'aria-label': `Interest comparison for ${option.display_name}` }, h('span', { style: { width: `${Number(option.estimated_total_interest) / interestMax * 100}%` } })),
            h('small', null, option.research_notes),
          )
        })),
      ),
      h('section', { className: 'panel commerce-recommendation' },
        h('div', null, h('p', { className: 'eyebrow' }, 'RESEARCH RECOMMENDATION'), h('h2', null, `Research-preferred: ${result.options.find((option) => option.option_id === result.preferred_option_id)?.display_name ?? 'scenario'}`), h('p', null, result.recommendation_explanation)),
        h('div', { className: 'commerce-why' }, h('strong', null, 'WHY THIS SCENARIO'), h('ul', null, ...result.comparison_factors.map((factor) => h('li', { key: factor }, factor)))),
        h('p', { className: 'commerce-human-boundary' }, 'Human confirmation is required before any later simulation. This AC-2 feature does not execute transactions or store an audit event.'),
      ),
      h('p', { className: 'commerce-event-summary' }, result.event_summary),
    ),
    !result && h('p', { className: 'commerce-research-note' }, 'No comparison has been run yet. Submit purchase context to calculate the scenarios. All estimates are research-only and do not validate borrowers or imply financing eligibility.'),
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
