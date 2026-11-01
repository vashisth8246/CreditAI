export type Availability = 'loading' | 'error' | 'empty' | 'ready'

export type DataSource = 'historical' | 'synthetic' | 'live-unvalidated' | 'unavailable'

export function displayFeatureName(name: string): string {
  return name.toUpperCase() === 'SEX' ? 'Gender' : name.replaceAll('_', ' ')
}

export function displayUserText(text: string): string {
  return text.replace(/\bsex\b/gi, 'gender')
}

export interface InventoryItem {
  dataset_id: string
  dataset_name: string
  qualification_decision: string
  local_status: string
  source_url: string
  target_definition: string
  [key: string]: unknown
}

export function availabilityState<T>(loading: boolean, error: string | null, data: T[] | null): Availability {
  if (loading) return 'loading'
  if (error) return 'error'
  if (!data || data.length === 0) return 'empty'
  return 'ready'
}

export function formatMetric(value: number | string | null | undefined, digits = 4): string {
  if (value === null || value === undefined || value === '') return '—'
  const parsed = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(parsed)) return '—'
  return parsed.toFixed(digits)
}

export function formatPercent(value: number | string | null | undefined, digits = 1): string {
  if (value === null || value === undefined || value === '') return '—'
  const parsed = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(parsed)) return '—'
  return `${(parsed * 100).toFixed(digits)}%`
}

export function safeProbability(status: string, probability: number | null | undefined): string {
  if (status !== 'validated' || probability === null || probability === undefined || !Number.isFinite(probability)) {
    return 'Not validated'
  }
  if (probability < 0 || probability > 1) return 'Unavailable'
  return formatPercent(probability, 1)
}

export function dataSourceLabel(source: DataSource): string {
  return {
    historical: 'HISTORICAL RESEARCH DATA',
    synthetic: 'SYNTHETIC DEMO',
    'live-unvalidated': 'LIVE API — NOT VALIDATED',
    unavailable: 'SOURCE UNAVAILABLE',
  }[source]
}

export function filterInventory(items: InventoryItem[], query: string, decision: string, source: string = 'all'): InventoryItem[] {
  const needle = query.trim().toLowerCase()
  return items.filter((item) => {
    const matchesQuery = !needle || `${item.dataset_id} ${item.dataset_name} ${item.target_definition}`.toLowerCase().includes(needle)
    const matchesDecision = decision === 'all' || item.qualification_decision === decision
    const isSynthetic = /^DS00[8-9]$|^DS01[0-3]$/.test(item.dataset_id)
    const isExternal = item.dataset_id.startsWith('EXT')
    const itemSource = isExternal ? 'external' : isSynthetic ? 'synthetic' : 'historical'
    const matchesSource = source === 'all' || itemSource === source
    return matchesQuery && matchesDecision && matchesSource
  })
}
