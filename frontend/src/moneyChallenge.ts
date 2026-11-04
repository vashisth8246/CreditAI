export const types = { savings: 'Savings Goal', spending: 'Spending Reduction', emergency: 'Emergency Buffer' }
export type Kind = keyof typeof types
export type Frequency = 'daily' | 'weekly' | 'monthly'
export type Entry = { id: string; date: string; amount: number; kind: 'contribution' | 'withdrawal' | 'spending'; note: string }
export type Passport = {
  version: 1; id: string; kind: Kind; name: string; profile: string; example: boolean
  created: string; end: string; target: number; start: number; planned: number
  frequency: Frequency; baseline: number; essential: number; category: string
  snapshot: { balance: number } | null; entries: Entry[]
}
const limit = 999999999999
export const storageKey = 'creditai.money-passports.v1'
export function today() {
  const date = new Date()
  return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'), String(date.getDate()).padStart(2, '0')].join('-')
}
export function validDate(value: unknown): value is string {
  if (typeof value !== 'string' || !/^20\d\d-\d\d-\d\d$/.test(value)) return false
  const date = new Date(value)
  return Number.isFinite(+date) && date.toISOString().slice(0, 10) === value
}
function dayDifference(start: string, end: string) {
  return (Date.parse(end) - Date.parse(start)) / 86400000
}
export function periodDate(start: string, frequency: Frequency, count: number) {
  if (!Number.isSafeInteger(count) || count < 0 || count > 30000) return null
  const date = new Date(start)
  if (frequency === 'monthly') {
    const day = date.getUTCDate()
    date.setUTCDate(1)
    date.setUTCMonth(date.getUTCMonth() + count)
    const lastDay = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0)).getUTCDate()
    date.setUTCDate(Math.min(day, lastDay))
  } else date.setUTCDate(date.getUTCDate() + count * (frequency === 'weekly' ? 7 : 1))
  const value = date.toISOString().slice(0, 10)
  return validDate(value) ? value : null
}
export function progress(passport: Passport, asOf: string) {
  const { kind, target, start, baseline, essential, planned, frequency, created, end } = passport
  const spending = kind === 'spending'
  const entries = [...passport.entries].sort((a, b) => a.date.localeCompare(b.date))
  const total = entries.reduce((sum, entry) => sum + (entry.kind === 'withdrawal' ? -entry.amount : entry.amount), 0)
  const current = spending ? total : start + total
  const limit = spending ? baseline - target : target
  const remaining = spending ? Math.max(0, current - limit) : Math.max(0, target - current)
  const comparison = baseline - current
  const closed = spending && asOf > end
  const earned = spending ? (closed && entries.length ? Math.max(0, comparison) : 0) : Math.max(0, current)
  const percentage = Math.min(100, earned / target * 100)
  const milestones = [25, 50, 75, 100].map(percent => {
    const threshold = Math.ceil(target * percent / 100)
    return { percent, threshold, achieved: earned >= threshold }
  })
  let periods = 0
  if (!spending && end && end > asOf) {
    const days = dayDifference(asOf, end)
    if (frequency === 'monthly') {
      const first = new Date(asOf)
      const last = new Date(end)
      periods = (last.getUTCFullYear() - first.getUTCFullYear()) * 12 + last.getUTCMonth() - first.getUTCMonth()
      if (periods && (periodDate(asOf, frequency, periods) ?? '9999') > end) periods--
    } else periods = Math.floor(days / (frequency === 'weekly' ? 7 : 1))
  }
  const required = periods ? Math.ceil(remaining / periods) : null
  const eta = spending || !remaining || !planned ? null : periodDate(asOf, frequency, Math.ceil(remaining / planned))
  const monthly = planned * (frequency === 'daily' ? 30 : frequency === 'weekly' ? 30 / 7 : 1)
  let cumulative = spending ? 0 : start
  const timeline = entries.map(entry => {
    cumulative += entry.kind === 'withdrawal' ? -entry.amount : entry.amount
    return { ...entry, cumulative }
  })
  return { current, remaining, limit, comparison, targetDifference: current - limit, percentage, milestones, required, eta,
    coverage: essential ? current / essential : null, timeline, periods, total,
    feasible: !spending && passport.snapshot ? monthly <= passport.snapshot.balance : null,
    status: spending ? (!closed ? 'Tracking period open' : !entries.length ? 'Closed · no recorded spending entries' : earned >= target ? 'Target met on recorded entries' : 'Closed · target not met on recorded entries')
      : current >= target ? 'Target reached' : 'In progress',
    created, closed,
  }
}

const isRecord = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value)
const label = (value: unknown, length: number): value is string =>
  typeof value === 'string' && value.trim().length > 0 && value.length <= length && [...value].every(character => character.charCodeAt(0) >= 32 && character.charCodeAt(0) !== 127)
const amount = (value: unknown): value is number =>
  typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 && value <= limit
const identifier = (value: unknown): value is string => typeof value === 'string' && /^[a-zA-Z0-9-]{1,64}$/.test(value)

export function validatePassport(raw: unknown, asOf: string): Passport {
  if (!isRecord(raw) || raw.version !== 1 || !identifier(raw.id) || !label(raw.name, 80)
    || typeof raw.profile !== 'string' || (raw.profile !== '' && !label(raw.profile, 80)) || typeof raw.example !== 'boolean'
    || !validDate(raw.created) || raw.created > asOf || (raw.end !== '' && (!validDate(raw.end) || raw.end < raw.created))
    || !amount(raw.target) || raw.target === 0 || !amount(raw.start) || !amount(raw.planned)
    || !amount(raw.baseline) || !amount(raw.essential) || typeof raw.category !== 'string'
    || (raw.kind !== 'savings' && raw.kind !== 'emergency' && raw.kind !== 'spending')
    || (raw.frequency !== 'daily' && raw.frequency !== 'weekly' && raw.frequency !== 'monthly')
    || !Array.isArray(raw.entries) || raw.entries.length > 500) throw Error('Invalid passport configuration or version.')
  const { kind, id, name, profile, example, created, end, target, start, planned, frequency, baseline, essential, category } = raw
  if (kind === 'spending' && (!label(category, 60) || !end || target > baseline || start !== 0 || planned !== 0))
    throw Error('Spending needs a category, end date and reduction no greater than baseline.')
  if (kind !== 'spending' && (baseline !== 0 || category !== '')) throw Error('Unexpected spending configuration.')
  let snapshot: Passport['snapshot'] = null
  if (raw.snapshot !== null) {
    if (!isRecord(raw.snapshot) || !amount(Math.abs(typeof raw.snapshot.balance === 'number' ? raw.snapshot.balance : NaN)))
      throw Error('Invalid retained snapshot.')
    snapshot = { balance: raw.snapshot.balance as number }
  }
  const ids = new Set<string>()
  const entries: Entry[] = raw.entries.map(entry => {
    if (!isRecord(entry) || !identifier(entry.id) || ids.has(entry.id) || !validDate(entry.date)
      || entry.date < created || entry.date > asOf || (kind === 'spending' && entry.date > end)
      || !amount(entry.amount) || (entry.amount === 0 && kind !== 'spending')
      || typeof entry.note !== 'string' || (entry.note !== '' && !label(entry.note, 160))
      || (kind === 'spending' ? entry.kind !== 'spending' : entry.kind !== 'contribution' && entry.kind !== 'withdrawal'))
      throw Error('Invalid or duplicate progress entry. Check dates, amounts and notes.')
    ids.add(entry.id)
    return { id: entry.id, date: entry.date, amount: entry.amount, kind: entry.kind as Entry['kind'], note: entry.note }
  })
  const passport: Passport = { version: 1, kind, id, name, profile, example, created, end, target, start, planned, frequency, baseline, essential, category, snapshot, entries }
  if (kind !== 'spending' && progress(passport, asOf).timeline.some(entry => entry.cumulative < 0))
    throw Error('Withdrawals cannot exceed the balance available on the recorded timeline.')
  return passport
}

export function importPassport(text: string, asOf: string) {
  if (text.length > 250000) throw Error('Passport file is too large.')
  return validatePassport(JSON.parse(text), asOf)
}
export function readPassports(storage: Pick<Storage, 'getItem'>, asOf: string): Passport[] {
  const raw = storage.getItem(storageKey)
  if (!raw) return []
  const envelope: unknown = JSON.parse(raw)
  if (!isRecord(envelope) || envelope.version !== 1 || envelope.consent !== true
    || !Array.isArray(envelope.passports) || envelope.passports.length > 20) throw Error('Invalid saved passport collection.')
  const passports = envelope.passports.map(item => validatePassport(item, asOf))
  if (new Set(passports.map(item => item.id)).size !== passports.length) throw Error('Duplicate saved passport.')
  return passports
}
export function savePassports(storage: Pick<Storage, 'setItem' | 'removeItem'>, passports: Passport[], consent: boolean) {
  if (!consent) throw Error('Storage consent is required.')
  if (passports.length > 20) throw Error('This browser can save up to 20 passports.')
  if (!passports.length) storage.removeItem(storageKey)
  else storage.setItem(storageKey, JSON.stringify({ version: 1, consent: true, passports }))
}
