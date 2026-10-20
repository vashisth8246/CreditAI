export type BatchRowResult = {
  row_index: number
  borrower_reference: string | number | null
  status: 'success' | 'error'
  prediction?: {
    model_id: string
    probability: number
    predicted_class: string
    risk_category: string
    calibrated: boolean
    threshold: number
  }
  error_message?: string
}

export type BatchPredictionResult = {
  model_id: string
  results: BatchRowResult[]
}

export const TAIWAN_REQUIRED_FIELDS = [
  'LIMIT_BAL', 'SEX', 'EDUCATION', 'MARRIAGE', 'AGE',
  'PAY_0', 'PAY_2', 'PAY_3', 'PAY_4', 'PAY_5', 'PAY_6',
  'BILL_AMT1', 'BILL_AMT2', 'BILL_AMT3', 'BILL_AMT4', 'BILL_AMT5', 'BILL_AMT6',
  'PAY_AMT1', 'PAY_AMT2', 'PAY_AMT3', 'PAY_AMT4', 'PAY_AMT5', 'PAY_AMT6',
] as const

export type ParsedCsv = {
  header: string[]
  rows: string[][]
  delimiter: string
}

/** Minimal RFC-4180 style CSV parser for client-side preview only. */
export function parseCsv(text: string): ParsedCsv {
  const clean = text.replace(/^\uFEFF/, '')
  const firstLine = clean.split(/\r?\n/, 1)[0] ?? ''
  const delimiter = (firstLine.match(/\t/g)?.length ?? 0) > (firstLine.match(/,/g)?.length ?? 0) ? '\t' : ','

  const rows: string[][] = []
  let field = ''
  let row: string[] = []
  let inQuotes = false
  for (let i = 0; i < clean.length; i += 1) {
    const char = clean[i]
    if (inQuotes) {
      if (char === '"') {
        if (clean[i + 1] === '"') { field += '"'; i += 1 } else { inQuotes = false }
      } else {
        field += char
      }
    } else if (char === '"') {
      inQuotes = true
    } else if (char === delimiter) {
      row.push(field); field = ''
    } else if (char === '\n') {
      row.push(field); field = ''
      rows.push(row); row = []
    } else if (char === '\r') {
      /* skip */
    } else {
      field += char
    }
  }
  if (field.length > 0 || row.length > 0) { row.push(field); rows.push(row) }

  const header = (rows.shift() ?? []).map((h) => h.trim())
  return { header, rows: rows.filter((r) => r.some((c) => c.trim() !== '')), delimiter }
}

/** Guards against CSV formula injection when we render/export attacker-controlled text. */
export function sanitizeCell(value: string): string {
  return /^[=+\-@\t\r]/.test(value) ? `'${value}` : value
}

export function missingRequiredFields(header: string[]): string[] {
  const present = new Set(header.map((h) => h.trim()))
  return TAIWAN_REQUIRED_FIELDS.filter((f) => !present.has(f))
}

export type BatchSummary = {
  total: number
  succeeded: number
  failed: number
  meanProbability: number | null
  lowRisk: number
  mediumRisk: number
  highRisk: number
}

export function summarizeBatch(result: BatchPredictionResult): BatchSummary {
  const successes = result.results.filter((r) => r.status === 'success' && r.prediction)
  const probabilities = successes.map((r) => r.prediction!.probability)
  const mean = probabilities.length ? probabilities.reduce((a, b) => a + b, 0) / probabilities.length : null
  const tier = (name: string) => successes.filter((r) => r.prediction!.risk_category === name).length
  return {
    total: result.results.length,
    succeeded: successes.length,
    failed: result.results.length - successes.length,
    meanProbability: mean,
    lowRisk: tier('Low'),
    mediumRisk: tier('Medium'),
    highRisk: tier('High'),
  }
}

/** Build an export CSV that neutralises spreadsheet formula injection. */
export function buildResultCsv(result: BatchPredictionResult): string {
  const header = ['row_index', 'borrower_reference', 'status', 'probability', 'risk_category', 'predicted_class', 'calibrated', 'error_message']
  const quote = (value: unknown): string => {
    const text = value === null || value === undefined ? '' : sanitizeCell(String(value))
    return `"${text.replaceAll('"', '""')}"`
  }
  const lines = [header.join(',')]
  for (const r of result.results) {
    lines.push([
      r.row_index,
      r.borrower_reference,
      r.status,
      r.prediction ? r.prediction.probability : '',
      r.prediction ? r.prediction.risk_category : '',
      r.prediction ? r.prediction.predicted_class : '',
      r.prediction ? String(r.prediction.calibrated) : '',
      r.error_message ?? '',
    ].map(quote).join(','))
  }
  return lines.join('\r\n')
}
