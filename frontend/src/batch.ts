export type BatchPrediction = {
  model_id: string
  probability: number
  predicted_class: string
  risk_category: string
  calibrated: boolean
  threshold: number
  calibration_method?: string | null
}

export type BatchRowResult = {
  result_index?: number
  sheet_name?: string
  source_row?: number
  row_index: number
  borrower_reference: string | number | null
  status: 'success' | 'error'
  prediction?: BatchPrediction
  error_message?: string
}

export type BatchPredictionResult = {
  model_id: string
  results: BatchRowResult[]
  file_name?: string
  file_format?: string
  generated_at?: string
  calibrated?: boolean
  calibration_method?: string | null
  thresholds?: { classification: number; low_upper: number; medium_upper: number }
  sheets?: BatchSheetOutcome[]
}

export type BatchSheetOutcome = {
  name: string
  total_rows: number
  scored: number
  failed: number
  blank_rows_ignored?: number
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

export const REFERENCE_FIELD = 'borrower_reference'
export const IGNORE_TARGET = ''

/** Header + one clearly synthetic example row using the exact required columns. */
export function buildTemplateCsv(): string {
  const header = [...TAIWAN_REQUIRED_FIELDS, REFERENCE_FIELD].join(',')
  const example = [
    200000, 2, 1, 2, 34, 0, 0, 0, 0, 0, 0,
    15000, 14000, 13000, 12000, 11000, 10000,
    5000, 4500, 4000, 3500, 3000, 2500, 'synthetic-example',
  ].join(',')
  return `${header}\r\n${example}\r\n`
}

export function normalizeHeader(value: string): string {
  return value.trim().replace(/^\uFEFF/, '').toUpperCase().replace(/[^A-Z0-9]+/g, '_').replace(/^_+|_+$/g, '')
}

export function missingRequiredFields(header: string[]): string[] {
  const present = new Set(header.map(normalizeHeader))
  return TAIWAN_REQUIRED_FIELDS.filter((field) => !present.has(normalizeHeader(field)))
}

export type BatchSummary = {
  total: number
  succeeded: number
  failed: number
  meanProbability: number | null
  medianProbability: number | null
  lowRisk: number
  mediumRisk: number
  highRisk: number
  unknownRisk: number
  histogram: HistogramBin[]
  probabilities: number[]
  sheets: SheetStats[]
}

export type HistogramBin = { label: string; count: number; low: number; high: number }

export const HISTOGRAM_BINS = [
  { label: '0â€“5%', low: 0, high: 0.05 },
  { label: '5â€“10%', low: 0.05, high: 0.1 },
  { label: '10â€“20%', low: 0.1, high: 0.2 },
  { label: '20â€“40%', low: 0.2, high: 0.4 },
  { label: '40â€“60%', low: 0.4, high: 0.6 },
  { label: '60â€“100%', low: 0.6, high: 1.0000001 },
] as const

export type SheetStats = {
  name: string
  total: number
  scored: number
  failed: number
  meanProbability: number | null
  lowRisk: number
  mediumRisk: number
  highRisk: number
}

function successProbability(row: BatchRowResult): number | null {
  if (row.status !== 'success' || !row.prediction) return null
  const value = row.prediction.probability
  return Number.isFinite(value) ? value : null
}

export function summarizeBatch(result: BatchPredictionResult): BatchSummary {
  const successes = result.results.filter((row) => successProbability(row) !== null)
  const probabilities = successes.map((row) => row.prediction!.probability)
  const mean = probabilities.length ? probabilities.reduce((a, b) => a + b, 0) / probabilities.length : null
  const tier = (name: string) => successes.filter((row) => row.prediction!.risk_category === name).length
  const unknownRisk = successes.filter((row) => !['Low', 'Medium', 'High'].includes(row.prediction!.risk_category)).length

  const sheetNames = new Set<string>()
  for (const row of result.results) sheetNames.add(row.sheet_name || 'Uploaded file')
  for (const sheet of result.sheets ?? []) sheetNames.add(sheet.name)

  const sheets: SheetStats[] = [...sheetNames].map((name) => {
    const rows = result.results.filter((row) => (row.sheet_name || 'Uploaded file') === name)
    const scored = rows.filter((row) => successProbability(row) !== null)
    const values = scored.map((row) => row.prediction!.probability)
    return {
      name,
      total: rows.length,
      scored: scored.length,
      failed: rows.length - scored.length,
      meanProbability: values.length ? values.reduce((a, b) => a + b, 0) / values.length : null,
      lowRisk: scored.filter((row) => row.prediction!.risk_category === 'Low').length,
      mediumRisk: scored.filter((row) => row.prediction!.risk_category === 'Medium').length,
      highRisk: scored.filter((row) => row.prediction!.risk_category === 'High').length,
    }
  })

  return {
    total: result.results.length,
    succeeded: successes.length,
    failed: result.results.length - successes.length,
    meanProbability: mean,
    medianProbability: median(probabilities),
    lowRisk: tier('Low'),
    mediumRisk: tier('Medium'),
    highRisk: tier('High'),
    unknownRisk,
    histogram: buildHistogram(probabilities),
    probabilities,
    sheets: sheets.sort((a, b) => a.name.localeCompare(b.name)),
  }
}

export function median(values: number[]): number | null {
  const clean = values.filter((value) => Number.isFinite(value)).sort((a, b) => a - b)
  if (!clean.length) return null
  const middle = Math.floor(clean.length / 2)
  return clean.length % 2 ? clean[middle] : (clean[middle - 1] + clean[middle]) / 2
}

export function buildHistogram(probabilities: number[]): HistogramBin[] {
  const bins = HISTOGRAM_BINS.map((bin) => ({ label: bin.label, count: 0, low: bin.low, high: bin.high }))
  for (const probability of probabilities) {
    if (!Number.isFinite(probability)) continue
    const index = bins.findIndex((bin, position) =>
      probability >= bin.low && (position === bins.length - 1 ? probability <= 1 : probability < bin.high),
    )
    if (index >= 0) bins[index].count += 1
  }
  return bins
}

/** Build an export CSV that neutralises spreadsheet formula injection. */
const RESULT_HEADER = [
  'result_index', 'sheet_name', 'source_row', 'sheet_row', 'borrower_reference', 'status',
  'probability', 'probability_percent', 'risk_category', 'predicted_class', 'calibrated',
  'model_id', 'error_message',
]

function csvCell(value: unknown): string {
  const text = value === null || value === undefined ? '' : sanitizeCell(String(value))
  return `"${text.replaceAll('"', '""')}"`
}

export function buildResultCsv(result: BatchPredictionResult): string {
  const lines = [RESULT_HEADER.join(',')]
  for (const row of result.results) {
    const prediction = row.prediction
    lines.push([
      row.result_index ?? '',
      row.sheet_name ?? '',
      row.source_row ?? '',
      row.row_index,
      row.borrower_reference,
      row.status,
      prediction ? prediction.probability : '',
      prediction ? formatProbability(prediction.probability, 2) : '',
      prediction ? prediction.risk_category : '',
      prediction ? prediction.predicted_class : '',
      prediction ? String(prediction.calibrated) : '',
      prediction ? prediction.model_id : '',
      row.error_message ?? '',
    ].map(csvCell).join(','))
  }
  return lines.join('\r\n')
}

export function formatProbability(probability: number | null | undefined, digits = 1): string {
  if (probability === null || probability === undefined || !Number.isFinite(probability)) return 'â€”'
  return `${(probability * 100).toFixed(digits)}%`
}

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return 'â€”'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export function riskClass(risk: string | undefined | null): string {
  if (risk === 'High') return 'risk-high'
  if (risk === 'Medium') return 'risk-medium'
  if (risk === 'Low') return 'risk-low'
  return ''
}

export type ResultFilter = 'all' | 'scored' | 'failed' | 'Low' | 'Medium' | 'High'

export function filterResults(results: BatchRowResult[], filter: ResultFilter, query: string): BatchRowResult[] {
  const needle = query.trim().toLowerCase()
  return results.filter((row) => {
    if (filter === 'scored' && row.status !== 'success') return false
    if (filter === 'failed' && row.status !== 'error') return false
    if (['Low', 'Medium', 'High'].includes(filter)) {
      if (row.status !== 'success' || row.prediction?.risk_category !== filter) return false
    }
    if (!needle) return true
    const haystack = [
      row.borrower_reference ?? '',
      row.sheet_name ?? '',
      row.error_message ?? '',
      row.prediction?.risk_category ?? '',
      row.prediction?.predicted_class ?? '',
      String(row.source_row ?? ''),
    ].join(' ').toLowerCase()
    return haystack.includes(needle)
  })
}

export type ResultSortKey = 'result_index' | 'probability' | 'reference' | 'source_row' | 'sheet'

export function sortResults(results: BatchRowResult[], key: ResultSortKey, direction: 'asc' | 'desc'): BatchRowResult[] {
  const factor = direction === 'asc' ? 1 : -1
  const value = (row: BatchRowResult): number | string => {
    switch (key) {
      case 'probability': return row.prediction?.probability ?? -1
      case 'reference': return String(row.borrower_reference ?? '')
      case 'source_row': return row.source_row ?? row.row_index
      case 'sheet': return row.sheet_name ?? ''
      default: return row.result_index ?? row.row_index
    }
  }
  return [...results].sort((a, b) => {
    const left = value(a)
    const right = value(b)
    if (typeof left === 'number' && typeof right === 'number') return (left - right) * factor
    return String(left).localeCompare(String(right)) * factor
  })
}

// ---------------------------------------------------------------------------
// Mapping helpers
// ---------------------------------------------------------------------------

export type Mapping = Record<string, string>

export function mappingTargets(mapping: Mapping): string[] {
  return Object.values(mapping).filter((target) => target && target !== IGNORE_TARGET && target !== 'ignore' && target !== 'metadata')
}

export function mappingIssues(mapping: Mapping, required: readonly string[] = TAIWAN_REQUIRED_FIELDS): {
  missing: string[]
  duplicated: string[]
} {
  const targets = mappingTargets(mapping)
  const counts = new Map<string, number>()
  for (const target of targets) counts.set(target, (counts.get(target) ?? 0) + 1)
  return {
    missing: required.filter((field) => !counts.has(field)),
    duplicated: [...counts.entries()].filter(([, count]) => count > 1).map(([target]) => target),
  }
}

export function assignMapping(mapping: Mapping, columnIndex: number, target: string): Mapping {
  const next: Mapping = { ...mapping }
  if (!target) {
    delete next[String(columnIndex)]
    return next
  }
  for (const [key, value] of Object.entries(next)) {
    if (value === target && key !== String(columnIndex)) delete next[key]
  }
  next[String(columnIndex)] = target
  return next
}

export function reverseMapping(mapping: Mapping): Record<string, number> {
  const reverse: Record<string, number> = {}
  for (const [column, target] of Object.entries(mapping)) {
    if (target) reverse[target] = Number(column)
  }
  return reverse
}

// ---------------------------------------------------------------------------
// Workbook inspection types
// ---------------------------------------------------------------------------

export type DuplicateHeader = {
  name: string
  normalized: string
  count: number
  indices: number[]
  kind: 'exact' | 'normalized'
}

export type SheetSummary = {
  name: string
  blank: boolean
  row_count: number
  column_count: number
  header_row?: number | null
  headers: string[]
  duplicate_headers: DuplicateHeader[]
  missing_fields: string[]
  auto_mapping: Record<string, string>
  status: string
  note?: string
  mapping_errors?: string[]
  blank_rows_ignored?: number
}

export type ValidationIssue = {
  source_row: number
  column: string
  source_column: string
  message: string
}

export type SheetValidation = {
  total_rows: number
  valid_rows: number
  invalid_rows: number
  warning_rows: number
  errors: ValidationIssue[]
  warnings: ValidationIssue[]
  status: string
  usable: boolean
  missing_fields: string[]
  mapping_errors: string[]
  truncated_errors?: boolean
}

export type SheetAnalysis = {
  name: string
  blank: boolean
  header_row: number | null
  row_count: number
  column_count: number
  blank_rows_ignored: number
  headers: string[]
  rows: string[][]
  row_numbers: number[]
  duplicate_headers: DuplicateHeader[]
  ambiguous_columns: number[]
  mapping: Record<string, string>
  auto_mapping: Record<string, string>
  missing_fields: string[]
  mapping_errors: string[]
  extra_columns: { index: number; name: string }[]
  identifier_columns: { index: number; name: string }[]
  validation: SheetValidation
  status: string
  usable: boolean
  required_fields: string[]
  formula_detection: string
}

export type BatchInspectResponse = {
  file_name: string
  file_format: string
  file_size_bytes: number
  sheet_count: number
  sheets: SheetSummary[]
  selected_sheet: string
  analysis: SheetAnalysis
  limits: { max_bytes: number; max_rows_per_sheet: number; max_sheets: number; max_columns: number }
  multi_sheet_compatible: boolean
  model_id: string
}

// ---------------------------------------------------------------------------
// Exports and report
// ---------------------------------------------------------------------------

export type ValidationExportSheet = { name: string; errors: ValidationIssue[] }

export function buildValidationCsv(sheets: ValidationExportSheet[]): string {
  const lines = ['sheet_name,source_row,column,source_column,message']
  for (const sheet of sheets) {
    for (const issue of sheet.errors) {
      lines.push([
        sheet.name,
        issue.source_row,
        issue.column,
        issue.source_column,
        issue.message,
      ].map(csvCell).join(','))
    }
  }
  return lines.join('\r\n')
}

export function buildXlsxPayload(result: BatchPredictionResult, summary: BatchSummary, metadata: {
  file_name?: string
  sheet_names?: string[]
  generated_at?: string
}) {
  return {
    results: result.results,
    summary: {
      total: summary.total,
      succeeded: summary.succeeded,
      failed: summary.failed,
      meanProbability: summary.meanProbability,
      medianProbability: summary.medianProbability,
      lowRisk: summary.lowRisk,
      mediumRisk: summary.mediumRisk,
      highRisk: summary.highRisk,
      histogram: summary.histogram.map((bin) => ({ label: bin.label, count: bin.count })),
      sheets: summary.sheets,
    },
    metadata: {
      file_name: metadata.file_name ?? result.file_name ?? 'batch upload',
      sheet_names: metadata.sheet_names ?? (result.sheets ?? []).map((sheet) => sheet.name),
      generated_at: metadata.generated_at ?? result.generated_at ?? new Date().toISOString(),
      model_id: result.model_id,
      calibration_method: result.calibration_method ?? null,
    },
  }
}

export type ReportValidationSheet = {
  name: string
  errors: ValidationIssue[]
  warnings: ValidationIssue[]
}

export function buildAnalysisReport(
  result: BatchPredictionResult,
  summary: BatchSummary,
  metadata: { file_name?: string; sheet_names?: string[]; generated_at?: string; format?: string } = {},
  validation: ReportValidationSheet[] = [],
): string {
  const percent = (value: number | null) => (value === null ? 'Not available (no scored rows)' : formatProbability(value, 2))
  const denominator = summary.succeeded
  const riskLine = (label: string, count: number) =>
    `- ${label}: ${count} of ${denominator} scored rows (${denominator ? ((count / denominator) * 100).toFixed(1) : '0.0'}%)`
  const errorRows = result.results.filter((row) => row.status === 'error')

  const lines = [
    '# CreditAI Batch Analysis Report',
    '',
    `**Generated:** ${metadata.generated_at ?? result.generated_at ?? new Date().toISOString()}`,
    `**File:** ${metadata.file_name ?? result.file_name ?? 'batch upload'}`,
    `**Format:** ${(metadata.format ?? result.file_format ?? 'unknown').toUpperCase()}`,
    `**Worksheets:** ${(metadata.sheet_names ?? (result.sheets ?? []).map((sheet) => sheet.name)).join(', ') || 'n/a'}`,
    '',
    '> **Research only.** This report uses the UCI Taiwan credit-card benchmark (2005).',
    '> The model is not validated for Indian borrowers or production lending decisions.',
    '> Predicted probabilities are model estimates, not observed defaults.',
    '',
    '## Model',
    '',
    `- Model identifier: \`${result.model_id}\``,
    `- Calibration: ${result.calibration_method ?? 'Not calibrated'}`,
    `- Calibrated: ${result.calibrated ? 'yes' : 'no'}`,
    `- Classification threshold: ${result.thresholds?.classification ?? 0.5}`,
    `- Risk tiers: Low < 25%; Medium 25% to < 50%; High >= 50%`,
    '',
    '## Row outcomes',
    '',
    `- Total rows submitted: ${summary.total}`,
    `- Successfully scored: ${summary.succeeded}`,
    `- Failed or rejected: ${summary.failed}`,
    `- Mean estimated PD: ${percent(summary.meanProbability)} (denominator: ${denominator} scored rows)`,
    `- Median estimated PD: ${percent(summary.medianProbability)} (denominator: ${denominator} scored rows)`,
    '',
    '## Risk distribution',
    '',
    riskLine('Low risk (<25%)', summary.lowRisk),
    riskLine('Medium risk (25% to <50%)', summary.mediumRisk),
    riskLine('High risk (>=50%)', summary.highRisk),
  ]
  if (summary.unknownRisk) lines.push(`- Unclassified: ${summary.unknownRisk}`)

  lines.push('', '## Probability distribution', '', '| Band | Borrowers | Share of scored rows |', '|---|---:|---:|')
  for (const bin of summary.histogram) {
    const share = denominator ? `${((bin.count / denominator) * 100).toFixed(1)}%` : '0.0%'
    lines.push(`| ${bin.label} | ${bin.count} | ${share} |`)
  }

  lines.push('', '## Results by worksheet', '', '| Worksheet | Total | Scored | Failed | Mean PD |', '|---|---:|---:|---:|---:|')
  for (const sheet of summary.sheets) {
    lines.push(`| ${sheet.name} | ${sheet.total} | ${sheet.scored} | ${sheet.failed} | ${percent(sheet.meanProbability)} |`)
  }

  lines.push('', '## Row-level failures', '')
  if (errorRows.length === 0) {
    lines.push('No row-level failures.')
  } else {
    lines.push('| Sheet | Source row | Reference | Message |', '|---|---:|---|---|')
    for (const row of errorRows.slice(0, 100)) {
      lines.push(`| ${row.sheet_name ?? ''} | ${row.source_row ?? ''} | ${sanitizeCell(String(row.borrower_reference ?? ''))} | ${sanitizeCell(row.error_message ?? '')} |`)
    }
    if (errorRows.length > 100) lines.push('', `_Only the first 100 of ${errorRows.length} failures are listed._`)
  }

  lines.push(
    '',
    '## Validation errors and warnings',
    '',
  )
  const validationErrors = validation.flatMap((sheet) => sheet.errors.map((issue) => ({ sheet: sheet.name, ...issue })))
  const validationWarnings = validation.flatMap((sheet) => sheet.warnings.map((issue) => ({ sheet: sheet.name, ...issue })))
  if (validationErrors.length === 0 && validationWarnings.length === 0) {
    lines.push('No worksheet validation errors or warnings were reported before scoring.')
  } else {
    if (validationErrors.length) {
      lines.push('### Errors', '', '| Worksheet | Source row | Feature | Message |', '|---|---:|---|---|')
      for (const issue of validationErrors.slice(0, 100)) {
        lines.push(`| ${issue.sheet} | ${issue.source_row} | ${issue.column} | ${sanitizeCell(issue.message)} |`)
      }
      if (validationErrors.length > 100) lines.push('', `_Only the first 100 of ${validationErrors.length} validation errors are listed._`)
    }
    if (validationWarnings.length) {
      lines.push('', '### Warnings', '', '| Worksheet | Source row | Feature | Warning |', '|---|---:|---|---|')
      for (const issue of validationWarnings.slice(0, 100)) {
        lines.push(`| ${issue.sheet} | ${issue.source_row} | ${issue.column} | ${sanitizeCell(issue.message)} |`)
      }
      if (validationWarnings.length > 100) lines.push('', `_Only the first 100 of ${validationWarnings.length} warnings are listed._`)
    }
  }

  lines.push(
    '',
    '## Limitations',
    '',
    '- The Taiwan benchmark covers Aprilâ€“September 2005; it does not represent Indian borrowers or current credit behaviour.',
    '- Predicted default probabilities are model outputs. Without verified outcome labels, this report cannot compute actual defaults, actual losses, model accuracy, or portfolio performance.',
    '- The batch endpoint scores rows in memory and does not persist borrower data.',
    '- The production `/v1/score` endpoint remains disabled (`not_validated`); this batch report is research output, not a production credit decision.',
  )

  return lines.join('\n')
}
