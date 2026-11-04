import { money, parseAmount } from './moneyHealth.ts'
import type { Entries, Field, Result } from './moneyHealth.ts'

export type ChallengeSuggestion = {
  kind: 'savings' | 'spending' | 'emergency'
  category?: string
  baseline?: number
  target?: number
  essential?: number
  planned?: number
}
type Suggestion = { text: string; changes?: Entries; challenge?: ChallengeSuggestion }

export function isOptionalExpense(field: Field, profile: number) {
  return field.kind === 'expense' && (field.id === 'discretionary' || (field.id === 'personal' && profile !== 2))
}

export function analyzeMoney(result: Result, profile: number) {
  const expenses = result.register.filter(field => field.kind === 'expense')
  const essentialFields = expenses.filter(field => !isOptionalExpense(field, profile) && field.id !== 'business')
  const essential = essentialFields.reduce((sum, field) => sum + (field.amount ?? 0), 0)
  const optionalFields = expenses.filter(field => isOptionalExpense(field, profile))
  const optional = optionalFields.reduce((sum, field) => sum + (field.amount ?? 0), 0)
  const business = result.expenses - essential - optional
  const spending = expenses.flatMap(field => field.amount === null ? [] : [[field.label, field.amount] as [string, number]])
    .sort((a, b) => b[1] - a[1])
  const allocation = [...spending.filter(([, amount]) => amount > 0),
    ...(result.debt > 0 ? [['Existing EMI', result.debt] as [string, number]] : []),
    ...(result.balance > 0 ? [['Money remaining', result.balance] as [string, number]] : [])]
  const allocationTotal = allocation.reduce((sum, [, amount]) => sum + amount, 0)
  const monthlyPercent = result.funds > 0 ? result.balance / result.funds * 100 : null
  const pressure = result.funds > 0 ? result.outflow / result.funds * 100 : null
  const emergencyMonths = essential > 0 ? result.savings / essential : null
  const goalGap = result.goal === null ? null : Math.max(0, result.goal - Math.max(0, result.balance))
  const blankEssential = essentialFields.filter(field => field.amount === null).map(field => field.label)
  const missing = result.register.filter(field => field.amount === null).map(field => field.label)
  const cashFlow = result.balance < 0
    ? `Monthly spending of ${money(result.outflow)} exceeds money received of ${money(result.funds)} by ${money(-result.balance)}. If this continues, you may need additional funds or lower spending.`
    : result.balance === 0
      ? `Money received and spending both total ${money(result.funds)}. This is a break-even month on the entered amounts.`
      : `You receive ${money(result.funds)} and spend ${money(result.outflow)} monthly, leaving ${money(result.balance)}.`
  const goalText = result.goal === null ? 'No monthly savings contribution was entered.'
    : result.balance < 0 && !goalGap ? 'No contribution is planned, and the entered month already has a shortfall.'
    : goalGap ? `Your ${money(result.goal)} contribution exceeds available monthly money by ${money(goalGap)}.`
      : `Your ${money(result.goal)} contribution fits within the entered monthly balance. Future savings may vary.`
  const largest = spending[0]?.[1] ?? 0
  const leaders = largest ? spending.filter(([, amount]) => amount === largest).map(([label]) => label) : []
  const largestText = leaders.length > 1 ? `${leaders.join(', ')} tie for the largest entered expense at ${money(largest)} each.`
    : leaders.length ? `${leaders[0]} is your largest entered expense at ${money(largest)}.` : 'No positive expense category was entered.'
  const coverageText = emergencyMonths === null ? 'Not calculable from these inputs.'
    : `${money(result.savings)} ÷ ${money(essential)} gives ${emergencyMonths.toFixed(2)} months at the entered essential spending rate.`
  const suggestions: Suggestion[] = []
  const optionalCut = optionalFields.find(field => (field.amount ?? 0) > 0)
  if (optionalCut && (result.balance <= 0 || profile === 0 || profile === 3)) {
    const cut = Math.min(optionalCut.amount!, 30000)
    suggestions.push({
      text: `Try reducing ${optionalCut.label.toLowerCase()} by ${money(cut)}. Your monthly balance would increase by the same amount if other figures stay unchanged.`,
      changes: { [optionalCut.id]: ((optionalCut.amount! - cut) / 100).toFixed(2) },
      challenge: { kind: 'spending', category: optionalCut.label, baseline: optionalCut.amount!, target: cut },
    })
  }
  if (result.balance < 0 && !optionalCut) suggestions.push({
    text: 'Review recurring commitments or explore additional funds. There is no positive optional expense entered to reduce.',
  })
  if (goalGap) suggestions.push({
    text: `Test a monthly savings contribution of ${money(Math.max(0, result.balance))}, the amount available on these inputs.`,
    changes: { goal: (Math.max(0, result.balance) / 100).toFixed(2) },
  })
  if (result.balance > 0 && result.savings === 0 && essential > 0) suggestions.push({
    text: 'Consider setting aside some of the remaining money for an emergency buffer. Review the target before starting.',
    challenge: { kind: 'emergency', target: essential, essential },
  })
  const primary = result.register.find(field => field.id === 'primary')?.amount ?? 0
  if (profile === 2 || (result.debt > 0 && primary > 0)) {
    const lower = result.register.find(field => field.id === 'low')?.amount ?? Math.round(primary * .8)
    suggestions.push({
      text: `Test a month with ${money(lower)} in primary income and the same spending and debt payments.`,
      changes: { primary: (lower / 100).toFixed(2) },
    })
  }
  if (!suggestions.some(item => item.challenge) && result.balance > 0) suggestions.push({
    text: 'Set a savings target and choose how much of the remaining money to contribute.',
    challenge: { kind: 'savings', planned: Math.min(result.balance, result.goal ?? result.balance, 999999999999) },
  })
  return { essential, optional, business, spending, allocation, allocationTotal, monthlyPercent, pressure,
    emergencyMonths, goalGap, cashFlow, goalText, largestText, coverageText, blankEssential, missing, suggestions }
}

export const analysisMethod = 'Your Money Health is a descriptive analysis of the numbers you entered. It is not a credit score, investment recommendation, or prediction of future income.'

export function scenarioSuggestions(baseline: Result, scenario: Result, profile: number) {
  return analyzeMoney(scenario, profile).suggestions.filter(suggestion =>
    !suggestion.changes || Object.entries(suggestion.changes).some(([id, value]) => {
      const current = scenario.register.find(field => field.id === id)
      const original = baseline.register.find(field => field.id === id)
      return parseAmount(value) !== current?.amount &&
        !(current?.kind === 'expense' && (current.amount ?? 0) < (original?.amount ?? 0))
    })
  )
}

export function analysisCharts(result: Result, profile: number) {
  const a = analyzeMoney(result, profile)
  return [
    { title: 'Monthly cash-flow comparison', rows: [
      ['Money received', result.funds], ['Entered essential expenses', a.essential], ['Entered optional expenses', a.optional],
      ...(a.business ? [['Business expenses', a.business]] : []), ['Monthly EMI', result.debt],
      [result.balance < 0 ? 'Monthly shortfall' : 'Money remaining', result.balance],
    ] as [string, number][], insight: a.cashFlow },
    { title: 'Expense breakdown', rows: a.spending, insight: a.largestText },
    { title: 'Savings and emergency coverage', rows: [
      ['Accessible savings', result.savings], ['Entered essential monthly expenses', a.essential],
    ] as [string, number][], insight: a.coverageText },
  ]
}
