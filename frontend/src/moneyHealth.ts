type Kind = 'funds' | 'expense' | 'debt' | 'savings' | 'goal' | 'low'
export type Field = { id: string; label: string; kind: Kind; required: boolean; example: number; help: string }
const field = (id: string, label: string, kind: Kind, example: number, help: string, required = false): Field =>
  ({ id, label, kind, required, example, help })
const expense = (id: string, label: string, example: number, help: string, required = true) =>
  field(id, label, 'expense', example, help, required)
const common = (debt: number, savings: number, goal: number) => [
  field('debt', 'Existing monthly EMI and debt payments', 'debt', debt, 'Monthly payments toward existing loans. Enter ₹0 if you have none. Keep these out of your other spending.'),
  field('savings', 'Accessible savings', 'savings', savings, 'Money you can use when needed, such as cash or a bank balance. Leave out property and assets that take time to sell.', true),
  field('goal', 'Monthly savings goal', 'goal', goal, 'Money you want to save each month. This is a target and does not count as spending.'),
]
export const profiles = [
  { name: 'Student', fields: [
    field('primary', 'Monthly pocket money or family support', 'funds', 5000, 'Regular monthly support available to spend.', true),
    field('additional', 'Part-time earnings', 'funds', 0, 'Monthly earnings after deductions.'),
    expense('food', 'Food', 1500, 'Meals and groceries you pay for.'),
    expense('transport', 'Transport', 600, 'Monthly fares and travel costs.'),
    expense('education', 'Education', 1000, 'Books, tuition, exam fees or courses. Enter ₹0 if you don’t pay these yourself.', false),
    expense('personal', 'Other personal expenses', 700, 'Spending outside the categories above.'),
    ...common(0, 2500, 1000),
  ] },
  { name: 'Working Professional', fields: [
    field('primary', 'Monthly take-home salary', 'funds', 50000, 'Pay after salary deductions, available for personal spending.', true),
    field('additional', 'Additional monthly income', 'funds', 0, 'Other recurring income after deductions.'),
    expense('housing', 'Rent or housing', 14000, 'Monthly rent or housing costs you pay. Enter ₹0 if you don’t pay rent. Put housing loan payments under debt.', false),
    expense('food', 'Food and household', 8000, 'Groceries, meals and household supplies.'),
    expense('transport', 'Transport', 3000, 'Fares, fuel and regular travel.'),
    expense('personal', 'Other living expenses', 3000, 'Shopping, outings, subscriptions and other personal spending outside the categories above.'),
    ...common(8000, 75000, 10000),
  ] },
  { name: 'Freelancer / Self-Employed', fields: [
    field('primary', 'Typical monthly personal income', 'funds', 40000, 'Use net personal income after business costs, or receipts available before business costs if you enter those costs separately.', true),
    field('low', 'Lower-income month estimate', 'low', 28000, 'Use the same income basis as your typical month.'),
    field('business', 'Business expenses still to deduct', 'expense', 0, 'Leave blank or enter zero if these costs were already deducted from income.'),
    expense('personal', 'Personal living expenses', 25000, 'Personal monthly spending excluding business costs, debt and savings.'),
    ...common(0, 60000, 8000),
  ] },
  { name: 'Other / Not Currently Earning', fields: [
    field('primary', 'Monthly family support or allowance', 'funds', 3000, 'Regular support available each month. Enter ₹0 if you receive no support.', true),
    field('additional', 'Other monthly funds', 'funds', 0, 'Other recurring funds. Exclude withdrawals from accessible savings.'),
    expense('essential', 'Essential expenses', 1800, 'Necessities such as food and housing, excluding debt.'),
    expense('discretionary', 'Discretionary expenses', 400, 'Shopping, movies, outings, games, subscriptions and other spending you can usually reduce.'),
    ...common(0, 1000, 500),
  ] },
]
export type Entries = Record<string, string>
export const example = (fields: Field[]): Entries =>
  Object.fromEntries(fields.map(({ id, example: value }) => [id, String(value)]))
export const money = (paise: number) => new Intl.NumberFormat('en-IN', {
  style: 'currency', currency: 'INR', minimumFractionDigits: 0, maximumFractionDigits: 2,
}).format(paise / 100)
export function parseAmount(raw = ''): number | null {
  const value = raw.trim()
  if (!value) return null
  if (!/^\d{1,10}(\.\d{1,2})?$/.test(value)) throw new Error('Enter up to 10 digits and two decimal places, or zero.')
  const [whole, fraction = ''] = value.split('.')
  return Number(whole) * 100 + Number(fraction.padEnd(2, '0'))
}
export function calculate(fields: Field[], entries: Entries) {
  const register = fields.map(field => {
    let amount: number | null
    try {
      amount = parseAmount(entries[field.id])
    } catch (error) {
      throw new Error(field.label + ': ' + (error as Error).message)
    }
    if (amount === null && field.required) throw new Error(`Enter ${field.label.toLowerCase()} or zero.`)
    return { ...field, amount }
  })
  const sum = (kind: Kind) => register.filter(field => field.kind === kind)
    .reduce((total, field) => total + (field.amount ?? 0), 0)
  const funds = sum('funds')
  const expenses = sum('expense')
  const debt = sum('debt')
  const outflow = expenses + debt
  const balance = funds - outflow
  const savings = sum('savings')
  const goal = register.find(field => field.kind === 'goal')?.amount ?? null
  return { register, funds, expenses, debt, outflow, balance, savings, goal,
    expenseRatio: funds ? expenses / funds * 100 : null,
    debtRatio: funds ? debt / funds * 100 : null,
    coverage: outflow ? savings / outflow : null,
    feasibility: goal === null ? 'Goal unavailable' : goal <= balance ? 'Feasible on these inputs' : 'Exceeds available balance',
  }
}
export type Result = ReturnType<typeof calculate>
export function timeline(target: number | null, allocated: number, contribution: number) {
  if (target === null) return null
  const remaining = Math.max(0, target - allocated)
  if (!remaining) return 0
  return contribution > 0 ? Math.ceil(remaining / contribution) : null
}
export const metrics = (r: Result) => [
  ['Monthly funds', money(r.funds), r.register.filter(f => f.kind === 'funds').map(f => money(f.amount ?? 0)).join(' + '), 'Total available monthly income or support.'],
  ['Living and included business expenses', money(r.expenses), r.register.filter(f => f.kind === 'expense').map(f => money(f.amount ?? 0)).join(' + '), 'Sum of the reported spending categories.'],
  ['Existing debt payments', money(r.debt), money(r.debt), 'Reported recurring debt commitments.'],
  ['Total monthly outflow', money(r.outflow), `${money(r.expenses)} + ${money(r.debt)}`, 'Spending plus debt payments.'],
  ['Monthly balance', money(r.balance), `${money(r.funds)} − ${money(r.outflow)}`, 'Positive is money left over. Negative is a shortfall.'],
  ['Expense ratio', r.expenseRatio === null ? 'Unavailable' : `${r.expenseRatio.toFixed(2)}%`, `${money(r.expenses)} ÷ ${money(r.funds)} × 100`, 'Spending as a percentage of funds. Requires positive funds.'],
  ['Debt payment ratio', r.debtRatio === null ? 'Unavailable' : `${r.debtRatio.toFixed(2)}%`, `${money(r.debt)} ÷ ${money(r.funds)} × 100`, 'Share of monthly funds committed to debt. Requires positive funds.'],
  ['Savings coverage', r.coverage === null ? 'Unavailable' : `${r.coverage.toFixed(2)} months`, `${money(r.savings)} ÷ ${money(r.outflow)}`, 'Months of outflow covered by accessible savings at constant spending with no new funds. Requires positive outflow.'],
  ['Savings goal', r.feasibility, r.goal === null ? 'Monthly goal unavailable' : `Compare ${money(r.goal)} with ${money(r.balance)}`, 'Based on the reported month. Actual future savings may differ.'],
]
export const charts = (r: Result, scenario: Result) => [
  { title: 'Monthly cash flow', rows: [['Funds', r.funds], ['Spending', r.expenses], ['Debt', r.debt], ['Balance', r.balance]] },
  { title: 'Spending breakdown', rows: r.register.flatMap(f => f.kind === 'expense' && f.amount !== null ? [[f.label, f.amount]] : []) },
  { title: 'Monthly funds allocation', rows: [['Available funds', r.funds], ['Total outflow', r.outflow], [r.balance < 0 ? 'Shortfall' : 'Unallocated', r.balance]] },
  { title: 'Baseline vs what-if', rows: [['Baseline balance', r.balance], ['Scenario balance', scenario.balance]] },
] as { title: string; rows: [string, number][] }[]

export function scenarioPresets(profile: number, result: Result): { label: string; changes: Entries }[] {
  const get = (id: string) => result.register.find(field => field.id === id)?.amount ?? 0
  const rupees = (paise: number) => (Math.max(0, Math.min(paise, 999999999999)) / 100).toFixed(2)
  const reduce = (paise: number, onlyOptional = false): Entries => {
    const expenses = result.register.filter(field => field.kind === 'expense' &&
      (!onlyOptional || field.id === 'discretionary')).reverse()
    const changes: Entries = {}
    for (const field of expenses) {
      const cut = Math.min(paise, field.amount ?? 0)
      if (cut > 0) changes[field.id] = rupees((field.amount ?? 0) - cut)
      paise -= cut
    }
    return changes
  }
  return [
    [
      { label: 'Spend ₹300 less monthly', changes: reduce(30000) },
      { label: 'Receive ₹500 more pocket money', changes: { primary: rupees(get('primary') + 50000) } },
      { label: 'Save ₹500 monthly', changes: { goal: '500' } },
      { label: 'Plan a ₹5,000 purchase', changes: { target: '5000' } },
    ],
    [
      { label: 'Add ₹5,000 EMI', changes: { extra: rupees(Math.min(500000, 999999999999 - result.debt)) } },
      { label: 'Increase salary by 10%', changes: { primary: rupees(Math.round(get('primary') * 1.1)) } },
      { label: 'Reduce spending by ₹2,000', changes: reduce(200000) },
      { label: 'Increase savings goal by ₹1,000', changes: { goal: rupees(get('goal') + 100000) } },
    ],
    [
      { label: 'Earn 20% less', changes: { primary: rupees(Math.round(get('primary') * .8)) } },
      { label: 'Increase expenses by ₹1,000', changes: { personal: rupees(get('personal') + 100000) } },
      { label: 'Save ₹1,000 more in a good month', changes: { goal: rupees(get('goal') + 100000) } },
      { label: 'Build a low-income reserve', changes: { target: rupees(Math.max(0, result.outflow - (result.register.find(field => field.id === 'low')?.amount ?? Math.round(get('primary') * .8)))) } },
    ],
    [
      { label: 'Receive ₹500 less support', changes: { primary: rupees(get('primary') - 50000) } },
      { label: 'Reduce optional spending by ₹300', changes: reduce(30000, true) },
      { label: 'Save for a ₹3,000 purchase', changes: { target: '3000' } },
    ],
  ][profile] ?? []
}
