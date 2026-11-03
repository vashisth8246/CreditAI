import { createElement as h, useEffect, useState } from 'react'
import type { FormEvent } from 'react'

export type AgenticCommercePageId = 'commerce' | 'commerce-audit'

export const AGENTIC_COMMERCE_NAVIGATION = [
  { id: 'commerce', title: 'Agentic Commerce', icon: '◇', section: 'AGENTIC COMMERCE' },
  { id: 'commerce-audit', title: 'Commerce Audit Trail', icon: '≋' },
] as const

export const AGENTIC_COMMERCE_STAGES = [
  'Purchase Intent', 'Research Context', 'Financing Options', 'Comparison',
  'Recommendation', 'Human Confirmation', 'Simulated Execution', 'Audit Trail',
] as const

type Option = {
  option_id: string
  display_name: string
  tenure_months: number
  annual_rate_percent: string
  estimated_monthly_payment: string
  estimated_total_payment: string
  estimated_total_interest: string
  payment_to_income_ratio: string | null
  estimated_remaining_income_after_obligations: string
  research_notes: string
}
type ResearchRecord = {
  reference: string
  dataset_name: string
  source_row: number
  features: Record<string, number>
  credit_limit_twd: number
  age_years: number
  repayment_status_codes: number[]
  statement_balances_twd: number[]
  payments_twd: number[]
  target_included: false
  model_inference_performed: boolean
}
type DataStatus = { status: 'available' | 'unavailable'; dataset_name: string; sha256: string; row_count: number | null; message: string }
type Session = {
  session_id: string
  status: 'awaiting_confirmation' | 'simulation_completed'
  comparison: {
    currency: string
    purchase_price: string
    down_payment: string
    financed_amount: string
    requested_tenure_months: number
    options: Option[]
    preferred_option_id: string
    recommendation_explanation: string
    comparison_factors: string[]
  }
  research_record: ResearchRecord | null
  research_output: ResearchPrediction | null
  provenance: Record<string, string>
  audit_events: { event_id: string; event_type: string; actor: string; summary: string; timestamp: string; provenance: Record<string, string> }[]
  transaction: null | {
    simulation_id: string
    selected_option: Option
    purchase_price: string
    down_payment: string
    financed_amount: string
    monthly_payment: string
    tenure_months: number
    total_estimated_repayment: string
    timestamp: string
    audit_reference: string
    real_transaction_executed: false
  }
  idempotent_replay?: boolean
}
type RecordList = { status: 'available' | 'unavailable'; records: ResearchRecord[]; message: string }
type ResearchField = { type: 'numeric' | 'categorical'; description: string; required: boolean; range?: number[]; values?: number[]; value_labels?: Record<string, string> }
type ResearchSchema = { model_id: string; raw_features: Record<string, ResearchField> }
type ResearchPrediction = { model_id: string; probability: number; predicted_class: string; limitations: string[]; calibrated: boolean }
type WorkflowStep = 'purchase' | 'profile' | 'results'
const RESEARCH_MODEL_ID = 'uci_taiwan_xgb'

export function parseResearchProfile(values: Record<string, string>, schema: ResearchSchema): Record<string, number> {
  const entries = Object.entries(schema.raw_features).map(([name, field]) => {
    const raw = values[name]?.trim() ?? ''
    if (field.required && raw === '') throw new Error(`${name} is required.`)
    if (raw === '') return [name, undefined] as const
    const parsed = Number(raw)
    if (!Number.isFinite(parsed)) throw new Error(`${name} must be numeric.`)
    if (field.values && !field.values.includes(parsed)) throw new Error(`${name} must be one of ${field.values.join(', ')}.`)
    if (field.range && (parsed < field.range[0] || parsed > field.range[1])) throw new Error(`${name} must be between ${field.range[0]} and ${field.range[1]}.`)
    if (!Number.isInteger(parsed)) throw new Error(`${name} must be a whole number.`)
    return [name, parsed] as const
  })
  return Object.fromEntries(entries.filter((entry): entry is readonly [string, number] => entry[1] !== undefined))
}

const API_BASE = typeof import.meta.env !== 'undefined' ? import.meta.env.VITE_API_BASE_URL || '' : ''
const SESSION_STORAGE_KEY = 'creditai_agentic_commerce_sessions'
const SESSION_STORAGE_LIMIT = 10
let sessionSequence = 0

function nextSessionId() {
  sessionSequence += 1
  return `ac3-${Date.now().toString(36)}-${sessionSequence.toString(36)}`
}

function money(value: string | number, currency: string) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency, maximumFractionDigits: 2 }).format(Number(value))
}
function rememberSession(sessionId: string) {
  try {
    const current = JSON.parse(globalThis.localStorage.getItem(SESSION_STORAGE_KEY) || '[]') as string[]
    globalThis.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify([sessionId, ...current.filter((id) => id !== sessionId)].slice(0, SESSION_STORAGE_LIMIT)))
  } catch { /* local history is optional; the API session remains authoritative */ }
}
async function responseMessage(response: Response) {
  try {
    const payload = await response.json() as { error?: { message?: string }; detail?: string }
    return payload.error?.message ?? payload.detail ?? `Request failed (${response.status}).`
  } catch { return `Request failed (${response.status}).` }
}

export function AgenticCommercePage() {
  const [session, setSession] = useState<Session | null>(null)
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const [dataStatus, setDataStatus] = useState<DataStatus | null>(null)
  const [dataStatusChecking, setDataStatusChecking] = useState(false)
  const [recordList, setRecordList] = useState<RecordList | null>(null)
  const [recordLoading, setRecordLoading] = useState(false)
  const [recordReference, setRecordReference] = useState('')
  const [selectedOptionId, setSelectedOptionId] = useState('')
  const [step, setStep] = useState<WorkflowStep>('purchase')
  const [researchSchema, setResearchSchema] = useState<ResearchSchema | null>(null)
  const [profileValues, setProfileValues] = useState<Record<string, string>>({})
  const [profileMode, setProfileMode] = useState<'manual' | 'dataset'>('manual')
  const [researchPrediction, setResearchPrediction] = useState<ResearchPrediction | null>(null)
  const [values, setValues] = useState({ product: '', category: '', price: '', down: '', tenure: '', income: '', obligations: '', rate1: '', rate2: '', rate3: '' })

  useEffect(() => {
    let active = true
    fetch(`${API_BASE}/v1/agentic-commerce/research-data`)
      .then(async (response) => { if (!response.ok) throw new Error(await responseMessage(response)); return response.json() as Promise<DataStatus> })
      .then((status) => { if (active) setDataStatus(status) })
      .catch((cause: unknown) => { if (active) setDataStatus({ status: 'unavailable', dataset_name: 'UCI Taiwan Default of Credit Card Clients', sha256: '', row_count: null, message: cause instanceof Error ? cause.message : 'Research dataset status is unavailable.' }) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    let active = true
    fetch(`${API_BASE}/v1/models/${RESEARCH_MODEL_ID}/schema`)
      .then(async (response) => { if (!response.ok) throw new Error(await responseMessage(response)); return response.json() as Promise<ResearchSchema> })
      .then((schema) => { if (active) { setResearchSchema(schema); setProfileValues(Object.fromEntries(Object.keys(schema.raw_features).map((name) => [name, '']))) } })
      .catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause.message : 'Research model input schema is unavailable.') })
    return () => { active = false }
  }, [])

  const update = (key: keyof typeof values) => (event: { target: { value: string } }) => setValues((current) => ({ ...current, [key]: event.target.value }))
  async function recheckDataStatus() {
    setDataStatusChecking(true)
    try {
      const response = await fetch(`${API_BASE}/v1/agentic-commerce/research-data`)
      if (!response.ok) throw new Error(await responseMessage(response))
      setDataStatus(await response.json() as DataStatus)
    } catch (cause) {
      setDataStatus((current) => ({ status: 'unavailable', dataset_name: 'UCI Taiwan Default of Credit Card Clients', sha256: current?.sha256 ?? '', row_count: null, message: cause instanceof Error ? cause.message : 'Research dataset status is unavailable.' }))
    } finally { setDataStatusChecking(false) }
  }
  async function loadRecords() {
    setRecordLoading(true); setError('')
    try {
      const response = await fetch(`${API_BASE}/v1/agentic-commerce/research-records?offset=0&limit=25`)
      const records = await response.json() as RecordList
      setRecordList(records)
      if (!response.ok || records.status !== 'available') throw new Error(records.message || await responseMessage(response))
    } catch (cause) {
      setRecordList((current) => current ?? { status: 'unavailable', records: [], message: cause instanceof Error ? cause.message : 'Research dataset unavailable.' })
    } finally { setRecordLoading(false) }
  }

  function continueToProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setStep('profile')
  }

  function clearResearchProfile() {
    setProfileMode('manual'); setRecordReference(''); setResearchPrediction(null)
    setProfileValues(Object.fromEntries(Object.keys(researchSchema?.raw_features ?? {}).map((name) => [name, ''])))
  }

  async function prepare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setPending(true); setError(''); setSession(null); setSelectedOptionId('')
    try {
      if (!researchSchema) throw new Error('The current model input schema could not be loaded from the connected backend.')
      const features = parseResearchProfile(profileValues, researchSchema)
      const rates = [values.rate1, values.rate2, values.rate3].filter((value) => value.trim() !== '').map(Number)
      const response = await fetch(`${API_BASE}/v1/agentic-commerce/sessions`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          intent: {
            session_id: nextSessionId(), product_name: values.product, product_category: values.category,
            product_price: values.price, down_payment: values.down, requested_tenure_months: Number(values.tenure),
            monthly_income: values.income, existing_monthly_obligations: values.obligations, currency: 'INR',
          },
          annual_rate_scenarios_percent: rates,
          research_record_reference: recordReference || null,
          research_profile: recordReference ? null : features,
        }),
      })
      if (!response.ok) throw new Error(await responseMessage(response))
      const created = await response.json() as Session
      setSession(created); setResearchPrediction(created.research_output); setSelectedOptionId(''); rememberSession(created.session_id)
      setStep('results')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'The research simulation could not be prepared.') }
    finally { setPending(false) }
  }

  async function confirm() {
    if (!session || !selectedOptionId || session.transaction) return
    setPending(true); setError('')
    try {
      const response = await fetch(`${API_BASE}/v1/agentic-commerce/sessions/${encodeURIComponent(session.session_id)}/confirm`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision: 'confirm_simulation', option_id: selectedOptionId }),
      })
      if (!response.ok) throw new Error(await responseMessage(response))
      setSession(await response.json() as Session)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'The simulation could not be completed.') }
    finally { setPending(false) }
  }

  const field = (label: string, key: keyof typeof values, type = 'text', required = true) => h('label', { className: 'commerce-field', key },
    h('span', null, label, h('small', { className: 'provenance-label' }, 'USER INPUT')),
    h('input', { type, min: type === 'number' ? (key === 'tenure' ? '1' : '0') : undefined, max: key.startsWith('rate') ? '100' : undefined, step: type === 'number' ? 'any' : undefined, value: values[key], required, onChange: update(key), autoComplete: 'off' }))
  const comparison = session?.comparison
  const selectedOption = comparison?.options.find((option) => option.option_id === selectedOptionId)
  const stageStates = [
    session ? 'Complete' : 'Awaiting input',
    session?.research_record ? 'Verified dataset record' : researchPrediction ? 'Manual research estimate ready' : dataStatus?.status === 'unavailable' ? 'Dataset unavailable · manual input available' : 'Manual input available',
    comparison ? 'Simulated options created' : 'Pending', comparison ? 'Compared' : 'Pending',
    comparison ? 'Research output ready' : 'Pending',
    session?.transaction ? 'Confirmed by user' : session ? 'Waiting for user' : 'Pending',
    session?.transaction ? 'Simulation complete' : 'Not executed',
    session ? `${session.audit_events.length} factual events` : 'No events',
  ]

  return h('div', { className: 'page-body commerce-page commerce-workspace' },
    h('div', { className: 'section-title' }, h('div', null,
      h('p', { className: 'eyebrow' }, 'AGENTIC COMMERCE · AC-1 → AC-2 → AC-3'),
      h('h1', null, 'A research workflow from intent to audit'),
      h('p', { className: 'section-detail' }, 'Enter purchase context, provide a research profile, review calculated scenarios, then decide whether to record a local simulation.'),
    ), h('span', { className: 'source-tag source-synthetic' }, 'NO REAL TRANSACTION')),
    h('section', { className: 'commerce-safety panel', 'aria-label': 'Agentic Commerce safety boundaries' },
      h('strong', null, 'Research simulation only'),
      h('ul', null, h('li', null, 'No lending decision'), h('li', null, 'No lender offer'), h('li', null, 'No payment or order'), h('li', null, 'Human confirmation required')),
    ),
    h('ol', { className: 'commerce-stage-list commerce-stepper', 'aria-label': 'Commerce journey stage status' },
      ...AGENTIC_COMMERCE_STAGES.map((stage, index) => {
        const status = stageStates[index]
        const complete = status === 'Complete' || status === 'Simulated options created' || status === 'Compared' || status === 'Research output ready' || status === 'Simulation complete' || status.endsWith('factual events') || status.startsWith('Record loaded')
        const current = !complete && ((index === 0 && !session) || (index === 5 && session && !session.transaction))
        return h('li', { key: stage, className: `commerce-stage ${complete ? 'is-complete' : current ? 'is-current' : 'is-future'}` },
          h('span', { className: 'commerce-stage-number', 'aria-hidden': 'true' }, String(index + 1).padStart(2, '0')),
          h('span', { className: 'commerce-stage-name' }, stage), h('span', { className: 'commerce-stage-status' }, status))
      }),
    ),
    h('section', { className: 'panel commerce-research-source', 'aria-label': 'Research dataset source' },
      h('div', null, h('p', { className: 'eyebrow' }, 'RESEARCH DATA SOURCE'), h('h2', null, dataStatus?.dataset_name ?? 'UCI Taiwan Default of Credit Card Clients'),
        h('p', null, dataStatus?.status === 'available' ? `${dataStatus.row_count?.toLocaleString()} verified rows · target excluded from displayed records` : dataStatus?.status === 'unavailable' ? 'Research dataset unavailable in this runtime. No sample borrower is substituted.' : 'Checking dataset availability. If the verified workbook is absent, no sample borrower will be substituted.')),
      h('span', { className: `source-tag ${dataStatus?.status === 'available' ? '' : 'source-unavailable'}` }, dataStatus?.status === 'available' ? 'VERIFIED RESEARCH DATA' : 'RESEARCH ONLY'),
      h('div', { className: 'commerce-record-controls' },
        dataStatus?.status === 'unavailable' && h('button', { type: 'button', className: 'button-secondary commerce-record-load', onClick: recheckDataStatus, disabled: dataStatusChecking }, dataStatusChecking ? 'Checking dataset…' : 'Recheck verified dataset'),
        h('button', { type: 'button', className: 'button-secondary commerce-record-load', onClick: loadRecords, disabled: recordLoading || dataStatus?.status !== 'available' }, recordLoading ? 'Loading records…' : 'Load verified research records'),
        recordList?.status === 'available' && h('label', { className: 'commerce-field' }, h('span', null, 'Research record · separate context'),
          h('select', { value: recordReference, onChange: (event: { target: { value: string } }) => {
            const selected = recordList.records.find((record) => record.reference === event.target.value)
            setRecordReference(event.target.value); setProfileMode('dataset')
            if (selected) setProfileValues(Object.fromEntries(Object.entries(selected.features).map(([name, value]) => [name, String(value)])))
          } },
            h('option', { value: '' }, 'Choose a verified record'),
            ...recordList.records.map((record) => h('option', { key: record.reference, value: record.reference }, `${record.reference} · row ${record.source_row}`)))),
        recordList?.status === 'available' && recordReference && (() => {
          const record = recordList.records.find((item) => item.reference === recordReference)
          return record ? h('p', { className: 'commerce-record-facts' }, `Dataset row ${record.source_row} · Taiwan dollar credit limit ${record.credit_limit_twd.toLocaleString()} · age ${record.age_years} · historical target withheld`) : null
        })(),
        recordList?.status === 'unavailable' && h('p', { className: 'commerce-error', role: 'status' }, recordList.message),
      ),
      dataStatus?.sha256 && h('small', { className: 'commerce-dataset-hash' }, `Expected SHA-256: ${dataStatus.sha256}`),
    ),
    step === 'purchase' && h('section', { className: 'panel commerce-input-panel', 'aria-label': 'AC-1 purchase intent' },
      h('div', { className: 'panel-heading' }, h('div', null, h('p', { className: 'eyebrow' }, 'PURCHASE CONTEXT'), h('h2', null, 'Enter the assumptions to compare'), h('p', null, 'No borrower or purchase example is prefilled. The income and obligation context is user-entered and is not dataset-backed.'))),
      h('form', { className: 'commerce-form', onSubmit: continueToProfile },
        h('div', { className: 'commerce-fields' }, field('Purchase label', 'product'), field('Category', 'category'), field('Purchase price (INR)', 'price', 'number'), field('Down payment (INR)', 'down', 'number'), field('Requested tenure (months)', 'tenure', 'number'), field('Monthly income context (INR)', 'income', 'number'), field('Existing monthly obligations (INR)', 'obligations', 'number')),
        h('div', { className: 'commerce-rate-assumptions' }, h('div', null, h('strong', null, 'Simulated annual rate parameters'), h('span', null, 'User-entered assumptions · 0% to 100% · no lender pricing')),
          h('div', { className: 'commerce-rate-fields' }, field('Scenario A · %', 'rate1', 'number'), field('Scenario B · %', 'rate2', 'number'), field('Scenario C · optional %', 'rate3', 'number', false))),
        h('button', { type: 'submit', className: 'button-primary commerce-submit' }, 'Continue to research profile →'),
      ),
    ),
    step === 'profile' && h('section', { className: 'panel commerce-input-panel', 'aria-label': 'AC-2 research profile' },
      h('div', { className: 'panel-heading' }, h('div', null, h('p', { className: 'eyebrow' }, 'AC-2 · MANUAL RESEARCH INPUT'), h('h2', null, 'Enter the model-required research fields'), h('p', null, 'This form is generated from the connected backend model schema. Fields start empty. Manual values are USER INPUT; they are not dataset-backed or validated lending evidence.'))),
      h('div', { className: 'commerce-record-controls' },
        h('button', { type: 'button', className: `button-secondary ${profileMode === 'manual' ? 'is-selected' : ''}`, onClick: clearResearchProfile }, 'Manual Research Input'),
        dataStatus?.status === 'available'
          ? h('button', { type: 'button', className: `button-secondary ${profileMode === 'dataset' ? 'is-selected' : ''}`, onClick: loadRecords, disabled: recordLoading }, recordLoading ? 'Loading verified record…' : 'Verified Dataset Record')
          : h('button', { type: 'button', className: 'button-secondary', disabled: true, title: dataStatus?.message }, 'Verified Dataset Record · unavailable'),
        dataStatus?.status === 'unavailable' && h('p', { className: 'commerce-research-note' }, 'Dataset-backed mode is unavailable until the workbook passes the recorded SHA-256 check. Manual research input remains available.'),
        profileMode === 'dataset' && recordReference && h('p', { className: 'commerce-record-facts' }, `DATASET · ${recordReference} · verified source row selected; historical target withheld.`),
      ),
      researchSchema
        ? h('form', { className: 'commerce-form', onSubmit: prepare },
          h('div', { className: 'commerce-fields commerce-research-fields' }, ...Object.entries(researchSchema.raw_features).map(([name, field]) => h('label', { className: 'commerce-field', key: name },
            h('span', null, name, h('small', { className: 'provenance-label' }, profileMode === 'dataset' ? 'DATASET' : 'USER INPUT')),
            field.values ? h('select', { value: profileValues[name] ?? '', required: field.required, disabled: profileMode === 'dataset', onChange: (event: { target: { value: string } }) => setProfileValues((current) => ({ ...current, [name]: event.target.value })) },
              h('option', { value: '' }, `Select ${name}`), ...field.values.map((value) => h('option', { key: value, value: String(value) }, `${value}${field.value_labels?.[String(value)] ? ` · ${field.value_labels[String(value)]}` : ''}`)))
              : h('input', { type: 'number', min: field.range?.[0], max: field.range?.[1], step: '1', required: field.required, disabled: profileMode === 'dataset', value: profileValues[name] ?? '', placeholder: field.range ? `${field.range[0]} to ${field.range[1]}` : '', onChange: (event: { target: { value: string } }) => setProfileValues((current) => ({ ...current, [name]: event.target.value })), autoComplete: 'off' }),
          ))),
          h('p', { className: 'commerce-research-note' }, 'Research inference uses the Taiwan-trained artifact and is not validated for Indian borrowers. It is not an approval, eligibility or lending decision.'),
          h('div', { className: 'commerce-form-actions' }, h('button', { type: 'button', className: 'button-secondary', onClick: () => setStep('purchase') }, '← Back to purchase intent'), h('button', { type: 'submit', className: 'button-primary commerce-submit', disabled: pending }, pending ? 'Running research comparison…' : 'Run research comparison →')),
          error && h('p', { className: 'commerce-error', role: 'alert' }, error),
        )
        : h('p', { className: 'commerce-research-note', role: 'status' }, 'Loading the exact required input fields from the connected backend…'),
    ),
    comparison && session && h('div', { className: 'commerce-results', key: session.session_id },
      researchPrediction && h('section', { className: 'panel commerce-research-output', 'aria-label': 'Research model output' }, h('p', { className: 'eyebrow' }, 'RESEARCH OUTPUT · UCI TAIWAN MODEL'), h('h2', null, 'Research estimate'), h('p', null, `Model output: ${(researchPrediction.probability * 100).toFixed(1)}% estimated historical default probability · ${researchPrediction.predicted_class}. This research result is not a lending decision and is not validated for Indian borrowers.`), h('span', { className: 'source-tag source-unavailable' }, session.research_record ? 'DATASET INPUT' : 'USER-ENTERED INPUT')),
      h('div', { className: 'commerce-provenance-row', 'aria-label': 'Data provenance' }, ...[
        ['PURCHASE', 'USER INPUT'], ['PAYMENT', 'CALCULATED'], ['RATES', 'SIMULATED'], ['RECOMMENDATION', 'RESEARCH OUTPUT'],
      ].map(([label, value]) => h('span', { key: label }, h('strong', null, label), value))),
      session.research_record && h('section', { className: 'panel commerce-loaded-record' },
        h('p', { className: 'eyebrow' }, 'DATASET-BACKED · SEPARATE RESEARCH CONTEXT'), h('h2', null, session.research_record.dataset_name),
        h('p', null, `${session.research_record.reference} · row ${session.research_record.source_row} · Taiwan dollar credit limit ${session.research_record.credit_limit_twd.toLocaleString()} · age ${session.research_record.age_years}`),
        h('p', null, 'This verified row supplies the research model input; its historical target is withheld. The Taiwan estimate is separate from financing calculations and is not an affordability claim.'),
      ),
      h('section', { className: 'commerce-summary-grid' }, ...[
        ['Purchase price', money(comparison.purchase_price, comparison.currency)], ['Down payment', money(comparison.down_payment, comparison.currency)], ['Amount financed', money(comparison.financed_amount, comparison.currency)], ['Tenure', `${comparison.requested_tenure_months} months`],
      ].map(([label, value]) => h('div', { className: 'panel commerce-summary-card', key: label }, h('span', null, label), h('strong', null, value)))),
      h('section', { className: 'panel commerce-options-panel' },
        h('div', { className: 'panel-heading' }, h('div', null, h('p', { className: 'eyebrow' }, 'SIMULATED FINANCING OPTIONS'), h('h2', null, 'Review each scenario'), h('p', null, 'Reducing-balance estimates using the same requested tenure. No affordability or eligibility decision is made.'))),
        h('div', { className: 'commerce-options' }, ...comparison.options.map((option) => h('article', { className: `commerce-option ${option.option_id === comparison.preferred_option_id ? 'is-preferred' : ''}`, key: option.option_id },
          h('div', { className: 'commerce-option-head' }, h('div', null, h('span', { className: 'commerce-demo-badge' }, 'SIMULATED OPTION'), h('h3', null, option.display_name)), option.option_id === comparison.preferred_option_id && h('span', { className: 'commerce-preferred-badge' }, 'Research-preferred')),
          h('div', { className: 'commerce-payment' }, h('strong', null, money(option.estimated_monthly_payment, comparison.currency)), h('span', null, 'calculated monthly payment')),
          h('div', { className: 'commerce-option-facts' }, h('div', null, h('span', null, 'Simulated rate'), h('strong', null, `${Number(option.annual_rate_percent).toFixed(2)}%`)), h('div', null, h('span', null, 'Total repayment'), h('strong', null, money(option.estimated_total_payment, comparison.currency))), h('div', null, h('span', null, 'Total interest'), h('strong', null, money(option.estimated_total_interest, comparison.currency))), h('div', null, h('span', null, 'Payment / income · descriptive'), h('strong', null, option.payment_to_income_ratio === null ? 'Unavailable' : `${(Number(option.payment_to_income_ratio) * 100).toFixed(1)}%`))),
          h('small', null, option.research_notes),
        ))),
      ),
      h('section', { className: 'panel commerce-recommendation' }, h('div', null,
        h('p', { className: 'eyebrow' }, 'CALCULATED / RESEARCH OUTPUT'), h('h2', null, 'Research-preferred option'), h('p', null, comparison.recommendation_explanation)),
        h('div', { className: 'commerce-why' }, h('strong', null, 'COMPARISON FACTORS'), h('ul', null, ...comparison.comparison_factors.map((factor) => h('li', { key: factor }, factor)))),
        h('p', { className: 'commerce-human-boundary' }, 'This comparison is not a credit decision, a lender offer, or validated affordability assessment. Select an option and explicitly confirm to create only a local simulation.'),
      ),
      !session.transaction && h('section', { className: 'panel commerce-confirmation', 'aria-label': 'Human confirmation' },
        h('p', { className: 'eyebrow' }, 'HUMAN CONFIRMATION REQUIRED'), h('h2', null, 'Review the selected simulated option'),
        h('label', { className: 'commerce-field' }, h('span', null, 'Choose the option to simulate'), h('select', { value: selectedOptionId, onChange: (event: { target: { value: string } }) => setSelectedOptionId(event.target.value) }, h('option', { value: '' }, 'Select an option'), ...comparison.options.map((option) => h('option', { key: option.option_id, value: option.option_id }, `${option.display_name} · ${money(option.estimated_monthly_payment, comparison.currency)} / month`)))),
        selectedOption && h('div', { className: 'commerce-confirmation-summary' },
          h('p', null, `Purchase: ${money(comparison.purchase_price, comparison.currency)} · Down payment: ${money(comparison.down_payment, comparison.currency)} · Financed: ${money(comparison.financed_amount, comparison.currency)}`),
          h('p', null, `${selectedOption.display_name} · ${money(selectedOption.estimated_monthly_payment, comparison.currency)} / month · ${selectedOption.tenure_months} months · total estimated repayment ${money(selectedOption.estimated_total_payment, comparison.currency)}`)),
        h('p', { className: 'commerce-research-note' }, 'Confirm Simulation creates only a local research record. No money moves, no lender receives data, and no order or loan is created.'),
        h('button', { type: 'button', className: 'button-primary commerce-submit', onClick: confirm, disabled: pending || !selectedOption || Boolean(session.transaction) }, pending ? 'Recording simulation…' : 'Confirm Simulation'),
        error && h('p', { className: 'commerce-error', role: 'alert' }, error),
      ),
      session.transaction && h('section', { className: 'panel commerce-completion', 'aria-label': 'Simulation completion' },
        h('span', { className: 'commerce-completion-mark', 'aria-hidden': 'true' }, '✓'), h('p', { className: 'eyebrow' }, 'RESEARCH TRANSACTION SIMULATED'), h('h2', null, 'Simulation complete'),
        h('p', null, 'NO REAL TRANSACTION WAS EXECUTED.'),
        h('dl', null, h('div', null, h('dt', null, 'Simulation reference'), h('dd', null, session.transaction.simulation_id)), h('div', null, h('dt', null, 'Selected option'), h('dd', null, session.transaction.selected_option.display_name)), h('div', null, h('dt', null, 'Monthly payment'), h('dd', null, money(session.transaction.monthly_payment, comparison.currency))), h('div', null, h('dt', null, 'Total estimated repayment'), h('dd', null, money(session.transaction.total_estimated_repayment, comparison.currency)), h('div', null, h('dt', null, 'Audit reference'), h('dd', null, session.transaction.audit_reference)))),
      ),
      h('section', { className: 'panel commerce-timeline', 'aria-label': 'Factual audit timeline' }, h('div', { className: 'panel-heading' }, h('div', null, h('p', { className: 'eyebrow' }, 'AUDIT TRAIL'), h('h2', null, 'Recorded system events'))),
        h('ol', null, ...session.audit_events.map((event) => h('li', { key: event.event_id }, h('span', { className: 'commerce-timeline-dot', 'aria-hidden': 'true' }), h('div', null, h('strong', null, event.event_type.replaceAll('_', ' ')), h('p', null, event.summary), h('small', null, `${new Date(event.timestamp).toLocaleString()} · ${event.actor}`))))),
      ),
    ),
    error && !session && h('p', { className: 'commerce-error', role: 'alert' }, error),
  )
}

export function CommerceAuditTrailPage() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [unavailable, setUnavailable] = useState(false)
  useEffect(() => {
    let active = true
    Promise.resolve().then(() => {
      const ids = JSON.parse(globalThis.localStorage.getItem(SESSION_STORAGE_KEY) || '[]') as string[]
      if (!ids.length) return []
      return Promise.all(ids.slice(0, SESSION_STORAGE_LIMIT).map(async (id) => {
        const response = await fetch(`${API_BASE}/v1/agentic-commerce/sessions/${encodeURIComponent(id)}`)
        if (!response.ok) throw new Error('Session unavailable')
        return response.json() as Promise<Session>
      }))
    }).then((items) => { if (active) setSessions(items) }).catch(() => { if (active) setUnavailable(true) })
    return () => { active = false }
  }, [])
  return h('div', { className: 'page-body commerce-page' },
    h('div', { className: 'section-title' }, h('div', null, h('p', { className: 'eyebrow' }, 'AGENTIC COMMERCE · AC-3'), h('h1', null, 'Commerce Audit Trail'), h('p', { className: 'section-detail' }, 'Factual events recorded by this running research-simulation process. Session data is in memory and is cleared when the backend restarts.')),
      h('span', { className: `source-tag ${sessions.length ? '' : 'source-unavailable'}` }, sessions.length ? `${sessions.length} LOCAL SESSION${sessions.length === 1 ? '' : 'S'}` : 'NO SESSION')),
    unavailable && h('p', { className: 'commerce-research-note', role: 'status' }, 'A prior session is no longer available. This can happen after the backend restarts; no audit event is fabricated.'),
    sessions.length ? sessions.map((session) => h('section', { className: 'panel commerce-timeline', key: session.session_id }, h('div', { className: 'panel-heading' }, h('div', null, h('p', { className: 'eyebrow' }, 'LOCAL SIMULATION'), h('h2', null, `Session ${session.session_id}`))), h('ol', null, ...session.audit_events.map((event) => h('li', { key: event.event_id }, h('span', { className: 'commerce-timeline-dot', 'aria-hidden': 'true' }), h('div', null, h('strong', null, event.event_type.replaceAll('_', ' ')), h('p', null, event.summary), h('small', null, `${new Date(event.timestamp).toLocaleString()} · ${event.actor} · ${Object.entries(event.provenance).map(([key, value]) => `${key}: ${value}`).join(' · ')}`)))))))
      : !unavailable && h('section', { className: 'panel commerce-audit-empty' }, h('span', { className: 'empty-icon', 'aria-hidden': 'true' }, '≋'), h('h2', null, 'No simulated commerce sessions are recorded in this browser.'), h('p', null, 'Complete an AC-3 comparison and explicit confirmation to create factual local audit events. No audit events are fabricated.')),
  )
}
