import { useEffect, useMemo, useRef, useState, type DragEvent, type ChangeEvent, type KeyboardEvent } from 'react'
import { researchApi } from './api'
import { displayFeatureName, displayUserText } from './analytics'
import { classifyResearchProbability } from './assessment'
import { useCountUpValue } from './motion'
import type {
  BatchInspectResponse,
  BatchPredictionResult,
  Mapping,
  ResultFilter,
  ResultSortKey,
  SheetAnalysis,
} from './batch'
import {
  assignMapping,
  buildAnalysisReport,
  buildResultCsv,
  buildTemplateCsv,
  buildValidationCsv,
  buildXlsxPayload,
  filterResults,
  formatBytes,
  formatProbability,
  repaymentComplement,
  mappingIssues,
  reverseMapping,
  riskClass,
  sanitizeCell,
  sortResults,
  selectPdExamples,
  summarizeBatch,
  TAIWAN_REQUIRED_FIELDS,
} from './batch'
import {
  CumulativeProbabilityChart,
  ProbabilityHistogram,
  RiskBySheetChart,
  RiskDistributionChart,
  StatusChart,
} from './BatchCharts'

const PREVIEW_PAGE_SIZE = 15
const RESULTS_PAGE_SIZE = 25
const MAX_FILE_BYTES = 10 * 1024 * 1024

const STEPS = [
  { number: 1 as const, title: 'Upload and select data', hint: 'CSV or Excel workbook' },
  { number: 2 as const, title: 'Preview, map and validate', hint: 'Check schema and rows' },
  { number: 3 as const, title: 'Predict and analyse', hint: 'Run, review, export' },
]

const FILTERS: { id: ResultFilter; label: string }[] = [
  { id: 'all', label: 'All rows' },
  { id: 'scored', label: 'Scored' },
  { id: 'failed', label: 'Needs review' },
  { id: 'Low', label: 'Low risk' },
  { id: 'Medium', label: 'Medium risk' },
  { id: 'High', label: 'High risk' },
]

function downloadBlob(content: BlobPart, type: string, filename: string) {
  const url = URL.createObjectURL(new Blob([content], { type }))
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function sheetStatusLabel(status: string): string {
  switch (status) {
    case 'ready': return 'Ready'
    case 'ready_with_errors': return 'Ready with row errors'
    case 'needs_mapping': return 'Needs mapping'
    case 'blank': return 'Blank sheet'
    case 'empty': return 'No data rows'
    default: return status
  }
}

function sheetStatusClass(status: string): string {
  if (status === 'ready') return 'ok'
  if (status === 'ready_with_errors') return 'warn'
  if (status === 'needs_mapping') return 'review'
  return 'blocked'
}

function batchFeatureLabel(feature: string): string {
  return ({
    PAY_0: 'Most recent repayment status',
    PAY_AMT1: 'Most recent payment amount',
    BILL_AMT1: 'Most recent bill statement amount',
  } as Record<string, string>)[feature] ?? displayFeatureName(feature)
}

function batchFeatureExplanation(feature: string): string {
  return ({
    PAY_0: 'The latest reported repayment status in the Taiwan research dataset.',
    PAY_2: 'Repayment status from two months before the target month.',
    PAY_3: 'Repayment status from three months before the target month.',
    BILL_AMT1: 'The latest statement amount recorded in the Taiwan research dataset.',
    PAY_AMT1: 'The latest payment amount recorded in the Taiwan research dataset.',
    LIMIT_BAL: 'The reported credit limit in the Taiwan research dataset.',
  } as Record<string, string>)[feature] ?? 'This feature contributed to the fitted model output; contribution is not a causal effect.'
}

export function BatchEvaluation() {
  const fileInput = useRef<HTMLInputElement>(null)
  const loadInFlight = useRef<Set<string>>(new Set())
  const analyzeSeq = useRef<Record<string, number>>({})

  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [dragActive, setDragActive] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [inspect, setInspect] = useState<BatchInspectResponse | null>(null)
  const [inspectState, setInspectState] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle')
  const [inspectError, setInspectError] = useState('')
  const [selectedSheets, setSelectedSheets] = useState<string[]>([])
  const [activeSheet, setActiveSheet] = useState('')
  const [analyses, setAnalyses] = useState<Record<string, SheetAnalysis>>({})
  const [mappings, setMappings] = useState<Record<string, Mapping>>({})
  const [analyzing, setAnalyzing] = useState<Record<string, boolean>>({})
  const [analysisError, setAnalysisError] = useState('')
  const [analysisErrorSheet, setAnalysisErrorSheet] = useState('')

  const [previewPage, setPreviewPage] = useState(1)
  const [previewQuery, setPreviewQuery] = useState('')
  const [hiddenColumns, setHiddenColumns] = useState<Set<number>>(new Set())
  const [columnPanelOpen, setColumnPanelOpen] = useState(false)
  const [mappingOpen, setMappingOpen] = useState(true)

  const [runState, setRunState] = useState<'idle' | 'running' | 'done' | 'error'>('idle')
  const [runError, setRunError] = useState('')
  const [result, setResult] = useState<BatchPredictionResult | null>(null)
  const [exportError, setExportError] = useState('')
  const [exporting, setExporting] = useState(false)
  const [exportNotice, setExportNotice] = useState('')
  const exportNoticeTimer = useRef<number | null>(null)

  const [filter, setFilter] = useState<ResultFilter>('all')
  const [resultQuery, setResultQuery] = useState('')
  const [sortKey, setSortKey] = useState<ResultSortKey>('result_index')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [resultPage, setResultPage] = useState(1)

  const activeAnalysis = activeSheet ? analyses[activeSheet] : null
  const activeMapping = activeSheet ? (mappings[activeSheet] ?? {}) : {}
  const summary = useMemo(() => (result ? summarizeBatch(result) : null), [result])
  const pdExamples = useMemo(() => result ? selectPdExamples(result) : { lowest: null, highest: null }, [result])
  const animatedTotal = useCountUpValue(String(summary?.total ?? 0), Boolean(summary))
  const animatedSucceeded = useCountUpValue(String(summary?.succeeded ?? 0), Boolean(summary))
  const animatedFailed = useCountUpValue(String(summary?.failed ?? 0), Boolean(summary))
  const animatedMean = useCountUpValue(summary ? formatProbability(summary.meanProbability, 2) : '0.00%', Boolean(summary))
  const animatedMedian = useCountUpValue(summary ? formatProbability(summary.medianProbability, 2) : '0.00%', Boolean(summary))

  useEffect(() => () => {
    if (exportNoticeTimer.current !== null) window.clearTimeout(exportNoticeTimer.current)
  }, [])

  function showExportNotice(message: string) {
    if (exportNoticeTimer.current !== null) window.clearTimeout(exportNoticeTimer.current)
    setExportNotice(message)
    exportNoticeTimer.current = window.setTimeout(() => setExportNotice(''), 2400)
  }

  const sheetReadiness = useMemo(() => {
    const issues: string[] = []
    let ready = selectedSheets.length > 0
    for (const name of selectedSheets) {
      const analysis = analyses[name]
      if (!analysis) {
        ready = false
        issues.push(`${name}: still loading worksheet metadata.`)
        continue
      }
      if (analyzing[name]) {
        ready = false
        issues.push(`${name}: re-validating the column mapping.`)
      }
      if (analysis.blank) {
        ready = false
        issues.push(`${name}: blank worksheet.`)
        continue
      }
      const mappingProblem = mappingIssues(mappings[name] ?? {}, analysis.required_fields.length ? analysis.required_fields : TAIWAN_REQUIRED_FIELDS)
      if (mappingProblem.missing.length) {
        ready = false
        issues.push(`${name}: ${mappingProblem.missing.length} required feature(s) not mapped.`)
      }
      if (mappingProblem.duplicated.length) {
        ready = false
        issues.push(`${name}: feature(s) mapped more than once (${mappingProblem.duplicated.map(displayFeatureName).join(', ')}).`)
      }
      if (!analysis.usable) {
        ready = false
        issues.push(`${name}: no scorable rows.`)
      }
      if (analysisError && analysisErrorSheet === name) {
        ready = false
        issues.push(`${name}: the last mapping validation failed.`)
      }
    }
    return { ready, issues }
  }, [selectedSheets, analyses, mappings, analyzing, analysisError, analysisErrorSheet])

  const canContinue = sheetReadiness.ready

  const filteredResults = useMemo(
    () => (result ? sortResults(filterResults(result.results, filter, resultQuery), sortKey, sortDir) : []),
    [result, filter, resultQuery, sortKey, sortDir],
  )
  const resultPageCount = Math.max(1, Math.ceil(filteredResults.length / RESULTS_PAGE_SIZE))
  const safeResultPage = Math.min(resultPage, resultPageCount)
  const visibleResults = filteredResults.slice((safeResultPage - 1) * RESULTS_PAGE_SIZE, safeResultPage * RESULTS_PAGE_SIZE)

  const previewColumns = useMemo(() => {
    if (!activeAnalysis) return [] as { header: string; index: number }[]
    const query = previewQuery.trim().toLowerCase()
    return activeAnalysis.headers
      .map((header, index) => ({ header, index }))
      .filter(({ header, index }) => {
        if (hiddenColumns.has(index)) return false
        return !query || header.toLowerCase().includes(query)
      })
  }, [activeAnalysis, hiddenColumns, previewQuery])

  const previewPageCount = Math.max(1, Math.ceil((activeAnalysis?.rows.length ?? 0) / PREVIEW_PAGE_SIZE))
  const safePreviewPage = Math.min(previewPage, previewPageCount)
  const previewRows = activeAnalysis
    ? activeAnalysis.rows.slice((safePreviewPage - 1) * PREVIEW_PAGE_SIZE, safePreviewPage * PREVIEW_PAGE_SIZE)
    : []

  const validationErrorCount = selectedSheets.reduce(
    (total, name) => total + (analyses[name]?.validation.errors.length ?? 0),
    0,
  )

  function resetDerivedState() {
    setAnalyses({})
    setMappings({})
    setAnalyzing({})
    setAnalysisError('')
    setAnalysisErrorSheet('')
    setPreviewPage(1)
    setPreviewQuery('')
    setHiddenColumns(new Set())
    setColumnPanelOpen(false)
    setRunState('idle')
    setRunError('')
    setResult(null)
    setExportError('')
    setFilter('all')
    setResultQuery('')
    setResultPage(1)
    setStep(1)
  }

  async function handleFile(nextFile: File) {
    if (nextFile.size > MAX_FILE_BYTES) {
      setInspectError(`This file is ${formatBytes(nextFile.size)}. The limit is 10 MB.`)
      setInspectState('error')
      return
    }
    resetDerivedState()
    setFile(nextFile)
    setInspect(null)
    setSelectedSheets([])
    setActiveSheet('')
    setInspectError('')
    setInspectState('loading')
    try {
      const response = await researchApi.batchInspect(nextFile)
      setInspect(response)
      setAnalyses({ [response.selected_sheet]: response.analysis })
      setMappings({ [response.selected_sheet]: response.analysis.mapping })
      setSelectedSheets([response.selected_sheet])
      setActiveSheet(response.selected_sheet)
      setInspectState('ready')
    } catch (error) {
      setInspectError(error instanceof Error ? error.message : String(error))
      setInspectState('error')
    }
  }

  function onFileInput(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0]
    if (nextFile) void handleFile(nextFile)
    event.target.value = ''
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setDragActive(false)
    const nextFile = event.dataTransfer.files?.[0]
    if (nextFile) void handleFile(nextFile)
  }

  function onDropzoneKey(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      fileInput.current?.click()
    }
  }

  async function loadSheet(name: string) {
    if (!file || analyses[name] || loadInFlight.current.has(name)) return
    loadInFlight.current.add(name)
    setAnalyzing((previous) => ({ ...previous, [name]: true }))
    setAnalysisError('')
    try {
      const response = await researchApi.batchInspect(file, name)
      setAnalyses((previous) => ({ ...previous, [name]: response.analysis }))
      setMappings((previous) => ({ ...previous, [name]: response.analysis.mapping }))
    } catch (error) {
      setAnalysisErrorSheet(name)
      setAnalysisError(error instanceof Error ? error.message : String(error))
    } finally {
      loadInFlight.current.delete(name)
      setAnalyzing((previous) => ({ ...previous, [name]: false }))
    }
  }

  function chooseActiveSheet(name: string) {
    setActiveSheet(name)
    setAnalysisError('')
    setPreviewPage(1)
    setPreviewQuery('')
    if (!analyses[name]) void loadSheet(name)
  }

  function toggleSheet(name: string, included: boolean) {
    if (included) {
      setSelectedSheets((previous) => (previous.includes(name) ? previous : [...previous, name]))
      chooseActiveSheet(name)
    } else {
      const remaining = selectedSheets.filter((candidate) => candidate !== name)
      setSelectedSheets(remaining)
      if (activeSheet === name) {
        const fallback = remaining[0] ?? ''
        setActiveSheet(fallback)
        if (fallback) chooseActiveSheet(fallback)
      }
    }
    setResult(null)
    setRunState('idle')
    setExportError('')
  }

  async function changeMapping(columnIndex: number, target: string) {
    if (!file || !activeSheet) return
    const analysis = analyses[activeSheet]
    if (!analysis) return
    const next = assignMapping(activeMapping, columnIndex, target)
    const seq = (analyzeSeq.current[activeSheet] ?? 0) + 1
    analyzeSeq.current[activeSheet] = seq
    setMappings((previous) => ({ ...previous, [activeSheet]: next }))
    setAnalyzing((previous) => ({ ...previous, [activeSheet]: true }))
    setAnalysisError('')
    setAnalysisErrorSheet('')
    setResult(null)
    setRunState('idle')
    try {
      const response = await researchApi.batchAnalyze(file, activeSheet, next)
      if (analyzeSeq.current[activeSheet] !== seq) return
      setAnalyses((previous) => ({ ...previous, [activeSheet]: response.analysis }))
      setMappings((previous) => ({ ...previous, [activeSheet]: response.analysis.mapping }))
      setInspect((previous) => previous
        ? {
            ...previous,
            sheets: previous.sheets.map((sheet) => sheet.name === activeSheet
              ? { ...sheet, status: response.analysis.status, missing_fields: response.analysis.missing_fields }
              : sheet),
          }
        : previous)
    } catch (error) {
      if (analyzeSeq.current[activeSheet] !== seq) return
      setAnalysisErrorSheet(activeSheet)
      setAnalysisError(error instanceof Error ? error.message : String(error))
    } finally {
      if (analyzeSeq.current[activeSheet] === seq) {
        setAnalyzing((previous) => ({ ...previous, [activeSheet]: false }))
      }
    }
  }

  function toggleColumn(index: number) {
    setHiddenColumns((previous) => {
      const next = new Set(previous)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  async function runBatch() {
    if (!file || !canContinue) return
    setRunState('running')
    setRunError('')
    setResult(null)
    setExportError('')
    try {
      const selections = selectedSheets.map((name) => ({ name, mapping: mappings[name] ?? {} }))
      const response = await researchApi.batchPredict(file, selections)
      setResult(response)
      setRunState('done')
      setFilter('all')
      setResultQuery('')
      setResultPage(1)
    } catch (error) {
      setRunError(error instanceof Error ? error.message : String(error))
      setRunState('error')
    }
  }

  function changeFilter(next: ResultFilter) {
    setFilter(next)
    setResultPage(1)
  }

  function changeSort(next: ResultSortKey) {
    if (sortKey === next) setSortDir((previous) => (previous === 'asc' ? 'desc' : 'asc'))
    else {
      setSortKey(next)
      setSortDir('asc')
    }
    setResultPage(1)
  }

  function downloadTemplate() {
    downloadBlob(`\uFEFF${buildTemplateCsv()}`, 'text/csv;charset=utf-8', 'creditai_batch_template.csv')
    showExportNotice('Template CSV download started')
  }

  function downloadPredictionsCsv() {
    if (!result) return
    setExportError('')
    downloadBlob(`\uFEFF${buildResultCsv(result)}`, 'text/csv;charset=utf-8', 'creditai_batch_predictions.csv')
    showExportNotice('Predictions CSV download started')
  }

  async function downloadPredictionsXlsx() {
    if (!result || !summary) return
    setExporting(true)
    setExportError('')
    try {
      const payload = buildXlsxPayload(result, summary, {
        file_name: file?.name ?? result.file_name,
        sheet_names: selectedSheets,
        generated_at: result.generated_at,
      })
      const blob = await researchApi.batchExportXlsx(payload)
      downloadBlob(blob, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'creditai_batch_predictions.xlsx')
      showExportNotice('Excel download started')
    } catch (error) {
      setExportError(error instanceof Error ? error.message : String(error))
    } finally {
      setExporting(false)
    }
  }

  function downloadValidationErrors() {
    const sheets = selectedSheets.map((name) => ({
      name,
      errors: analyses[name]?.validation.errors ?? [],
    }))
    if (!validationErrorCount) {
      setExportError('There are no validation errors to export.')
      return
    }
    setExportError('')
    downloadBlob(`\uFEFF${buildValidationCsv(sheets)}`, 'text/csv;charset=utf-8', 'creditai_validation_errors.csv')
    showExportNotice('Validation CSV download started')
  }

  function downloadReport() {
    if (!result || !summary) return
    const validation = selectedSheets.map((name) => ({
      name,
      errors: analyses[name]?.validation.errors ?? [],
      warnings: analyses[name]?.validation.warnings ?? [],
    }))
    const report = buildAnalysisReport(result, summary, {
      file_name: file?.name ?? result.file_name,
      sheet_names: selectedSheets,
      generated_at: result.generated_at,
      format: inspect?.file_format ?? result.file_format,
    }, validation)
    downloadBlob(report, 'text/markdown;charset=utf-8', 'creditai_batch_analysis_report.md')
    showExportNotice('Analysis report download started')
  }

  function startNewBatch() {
    setFile(null)
    setInspect(null)
    setInspectState('idle')
    setInspectError('')
    setSelectedSheets([])
    setActiveSheet('')
    resetDerivedState()
  }

  function goToStep(target: 1 | 2 | 3) {
    if (target === 2 && (!inspect || !selectedSheets.length)) return
    if (target === 3 && !canContinue && !result) return
    setStep(target)
  }

  const activeReverse = reverseMapping(activeMapping)
  const activeRequired = activeAnalysis?.required_fields.length ? activeAnalysis.required_fields : [...TAIWAN_REQUIRED_FIELDS]
  const activeMappingProblem = mappingIssues(activeMapping, activeRequired)

  const selectedRowTotal = selectedSheets.reduce((total, name) => total + (analyses[name]?.row_count ?? 0), 0)

  return (
    <div className={`batch-page exhibition-batch-page ${inspect ? 'has-inspected-file' : ''} ${runState === 'running' ? 'is-processing' : ''} ${result ? 'has-results' : ''}`}>
      {exportNotice && <div className="exhibition-export-toast" role="status" aria-live="polite">✓ {exportNotice}</div>}
      <div className="batch-progress exhibition-batch-workflow" role="navigation" aria-label="Batch evaluation progress">
        {STEPS.map((item) => {
          const disabled = (item.number === 2 && (!inspect || !selectedSheets.length)) || (item.number === 3 && !canContinue && !result)
          const active = step === item.number
          const complete = (item.number === 1 && inspectState === 'ready' && step > 1)
            || (item.number === 2 && canContinue && step > 2)
            || (item.number === 3 && Boolean(result))
          return (
            <button
              key={item.number}
              type="button"
              className={`batch-progress-step ${active ? 'active' : ''} ${complete ? 'complete' : ''}`}
              aria-current={active ? 'step' : undefined}
              disabled={disabled}
              onClick={() => goToStep(item.number)}
            >
              <span className="batch-step-number">{complete && !active ? '✓' : item.number}</span>
              <span className="batch-step-copy">
                <strong>{item.title}</strong>
                <small>{item.hint}</small>
              </span>
            </button>
          )
        })}
      </div>

      <div className="research-warning">
        <span className="notice-icon" aria-hidden="true">i</span>
        <strong>
          Research only: the Taiwan UCI credit-card benchmark is not validated for Indian borrowers or production
          underwriting. Estimated probabilities are model outputs, not observed defaults, and this workflow cannot
          measure actual defaults, losses or accuracy without outcome labels.
        </strong>
      </div>

      {step === 1 && (
        <div className="batch-step-panel">
          <section className="panel batch-upload-panel exhibition-upload-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">STEP 1</p>
                <h2>Upload and select data</h2>
                <p>CSV or Excel. Excel worksheets are inspected individually; sheets are never concatenated.</p>
              </div>
              <span className="source-tag">Taiwan research model</span>
            </div>

            <div
              className={`batch-dropzone exhibition-upload-zone ${dragActive ? 'drag-active' : ''} ${inspectState === 'loading' ? 'is-loading' : ''}`}
              role="button"
              tabIndex={0}
              aria-label="Upload a CSV or Excel workbook"
              onClick={() => fileInput.current?.click()}
              onKeyDown={onDropzoneKey}
              onDragOver={(event) => { event.preventDefault(); setDragActive(true) }}
              onDragLeave={() => setDragActive(false)}
              onDrop={onDrop}
            >
              <input
                ref={fileInput}
                type="file"
                accept=".csv,.xlsx,.xls"
                hidden
                onChange={onFileInput}
              />
              <div className="batch-drop-icon" aria-hidden="true">↑</div>
              <h3>{inspectState === 'loading' ? 'Inspecting workbook…' : 'Drag and drop a CSV or Excel workbook'}</h3>
              <p>or choose a file from your computer. The file is parsed in memory and is not stored by this UI.</p>
              <button
                type="button"
                className="button-primary"
                onClick={(event) => { event.stopPropagation(); fileInput.current?.click() }}
                disabled={inspectState === 'loading'}
              >
                {inspectState === 'loading' ? 'Working…' : 'Choose file'}
              </button>
              <small>Limits: 10 MB · 5,000 rows per sheet · 20 worksheets · .csv, .xlsx, .xls</small>
            </div>

            <div className="batch-template-row">
              <div>
                <strong>Need the expected columns?</strong>
                <p>The template contains all 23 Taiwan research features plus the optional borrower_reference identifier, with one synthetic example row.</p>
              </div>
              <button type="button" className="button-secondary" onClick={downloadTemplate}>Download CSV template</button>
            </div>

            {inspectError && (
              <div className="api-error" role="alert">
                <strong>Could not inspect the file.</strong>
                <p>{inspectError}</p>
                <button type="button" className="button-secondary" onClick={() => fileInput.current?.click()}>Choose another file</button>
              </div>
            )}
          </section>

          {inspect && inspectState === 'ready' && (
            <>
              <section className="panel">
                <div className="panel-heading">
                  <div>
                    <h2>Workbook contents</h2>
                    <p>Select one worksheet, or several worksheets to score independently. Each sheet needs its own usable mapping.</p>
                  </div>
                  <span className="source-tag">{inspect.file_format.toUpperCase()}</span>
                </div>
                <div className="batch-file-facts">
                  <div><span>File</span><strong title={inspect.file_name}>{inspect.file_name}</strong></div>
                  <div><span>Size</span><strong>{formatBytes(inspect.file_size_bytes)}</strong></div>
                  <div><span>Detected format</span><strong>{inspect.file_format.toUpperCase()}</strong></div>
                  <div><span>Worksheets</span><strong>{inspect.sheet_count}</strong></div>
                </div>
                <div className="batch-sheet-list" role="table" aria-label="Worksheets in the uploaded workbook">
                  <div className="batch-sheet-row batch-sheet-head" role="row">
                    <span role="columnheader">Include</span>
                    <span role="columnheader">Worksheet</span>
                    <span role="columnheader">Rows</span>
                    <span role="columnheader">Columns</span>
                    <span role="columnheader">Status</span>
                    <span role="columnheader">Details</span>
                  </div>
                  {inspect.sheets.map((sheet) => {
                    const included = selectedSheets.includes(sheet.name)
                    const details = [
                      sheet.missing_fields.length ? `${sheet.missing_fields.length} required feature(s) missing` : '',
                      sheet.duplicate_headers.length ? `${sheet.duplicate_headers.length} duplicate header group(s)` : '',
                      sheet.blank_rows_ignored ? `${sheet.blank_rows_ignored} blank row(s) ignored` : '',
                    ].filter(Boolean).join(' · ') || 'Schema complete'
                    return (
                      <div
                        key={sheet.name}
                        role="row"
                        className={`batch-sheet-row ${activeSheet === sheet.name ? 'active' : ''} ${included ? 'included' : ''}`}
                        onClick={() => { chooseActiveSheet(sheet.name); if (!included && !sheet.blank) toggleSheet(sheet.name, true) }}
                      >
                        <span role="cell" onClick={(event) => event.stopPropagation()}>
                          <input
                            type="checkbox"
                            aria-label={`Include worksheet ${sheet.name}`}
                            checked={included}
                            disabled={sheet.blank}
                            onChange={(event) => toggleSheet(sheet.name, event.target.checked)}
                          />
                        </span>
                        <span role="cell" className="batch-sheet-name" title={sheet.name}>{sheet.name}</span>
                        <span role="cell">{sheet.blank ? '—' : sheet.row_count}</span>
                        <span role="cell">{sheet.blank ? '—' : sheet.column_count}</span>
                        <span role="cell"><span className={`batch-status ${sheetStatusClass(sheet.status)}`}>{sheetStatusLabel(sheet.status)}</span></span>
                        <span role="cell" className="batch-sheet-detail">{details}</span>
                      </div>
                    )
                  })}
                </div>
                <div className="batch-note">
                  <strong>{selectedSheets.length} worksheet(s) selected.</strong> Multi-sheet runs preserve the worksheet
                  name and original source row for every result. Sheets with missing features must be mapped in Step 2 or
                  excluded.
                </div>
                <div className="batch-actions">
                  <button type="button" className="button-secondary" onClick={() => fileInput.current?.click()}>Replace file</button>
                  <button
                    type="button"
                    className="button-primary"
                    disabled={!selectedSheets.length || !canContinue}
                    onClick={() => goToStep(2)}
                  >
                    Continue to validation
                  </button>
                </div>
                {!canContinue && sheetReadiness.issues.length > 0 && (
                  <p className="batch-inline-hint">Before continuing: {sheetReadiness.issues[0]}</p>
                )}
              </section>
            </>
          )}
        </div>
      )}

      {step === 2 && inspect && (
        <div className="batch-step-panel">
          <section className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">STEP 2</p>
                <h2>Preview, map and validate</h2>
                <p>{inspect.file_name} · {selectedSheets.length} selected worksheet(s) · nothing has been sent to the model yet.</p>
              </div>
              <div className="batch-head-actions">
                <button type="button" className="button-secondary" onClick={() => setStep(1)}>Back to upload</button>
              </div>
            </div>

            <div className="batch-sheet-tabs" role="tablist" aria-label="Selected worksheets">
              {selectedSheets.map((name) => {
                const analysis = analyses[name]
                return (
                  <button
                    key={name}
                    type="button"
                    role="tab"
                    aria-selected={activeSheet === name}
                    className={`batch-sheet-tab ${activeSheet === name ? 'active' : ''}`}
                    onClick={() => chooseActiveSheet(name)}
                  >
                    <span title={name}>{name}</span>
                    <i className={`batch-status ${sheetStatusClass(analysis?.status ?? 'ready')}`}>
                      {analysis ? sheetStatusLabel(analysis.status) : (analyzing[name] ? 'Loading…' : 'Pending')}
                    </i>
                  </button>
                )
              })}
            </div>

            {!selectedSheets.length && (
              <div className="empty-state batch-empty">
                <span className="empty-icon" aria-hidden="true">◌</span>
                <h3>No worksheet selected</h3>
                <p>Return to Step 1 and include at least one worksheet before validating.</p>
                <button type="button" className="button-secondary" onClick={() => setStep(1)}>Back to upload</button>
              </div>
            )}

            {selectedSheets.length > 0 && !activeAnalysis && (
              <div className="inline-loading" role="status">Loading worksheet preview…</div>
            )}

            {activeAnalysis && activeAnalysis.blank && (
              <div className="empty-state batch-empty">
                <span className="empty-icon" aria-hidden="true">◌</span>
                <h3>This worksheet is blank</h3>
                <p>Choose a different worksheet in Step 1. Blank sheets cannot be mapped or scored.</p>
              </div>
            )}

            {activeAnalysis && !activeAnalysis.blank && (
              <>
                <div className="batch-validation-grid">
                  <div className="batch-stat"><span>Total rows</span><strong>{activeAnalysis.row_count}</strong><small>{activeAnalysis.blank_rows_ignored} blank row(s) ignored</small></div>
                  <div className="batch-stat"><span>Valid rows</span><strong>{activeAnalysis.validation.status === 'needs_mapping' ? '—' : activeAnalysis.validation.valid_rows}</strong><small>{activeAnalysis.validation.status === 'needs_mapping' ? 'Complete the mapping first' : 'Ready to score'}</small></div>
                  <div className="batch-stat"><span>Invalid rows</span><strong>{activeAnalysis.validation.status === 'needs_mapping' ? '—' : activeAnalysis.validation.invalid_rows}</strong><small>{activeAnalysis.validation.status === 'needs_mapping' ? 'Not calculated yet' : 'Will be returned as row errors'}</small></div>
                  <div className="batch-stat"><span>Rows with warnings</span><strong>{activeAnalysis.validation.status === 'needs_mapping' ? '—' : activeAnalysis.validation.warning_rows}</strong><small>e.g. numbers stored as text</small></div>
                  <div className="batch-stat"><span>Required features found</span><strong>{activeRequired.length - activeAnalysis.missing_fields.length}/{activeRequired.length}</strong><small>Taiwan research contract</small></div>
                  <div className={`batch-stat ${activeAnalysis.missing_fields.length ? 'is-bad' : ''}`}><span>Missing required</span><strong>{activeAnalysis.missing_fields.length}</strong><small>{activeAnalysis.missing_fields.length ? activeAnalysis.missing_fields.slice(0, 3).map(displayFeatureName).join(', ') + (activeAnalysis.missing_fields.length > 3 ? '…' : '') : 'None'}</small></div>
                  <div className="batch-stat"><span>Extra columns</span><strong>{activeAnalysis.extra_columns.length}</strong><small>Ignored as metadata unless mapped</small></div>
                  <div className={`batch-stat ${activeAnalysis.duplicate_headers.length ? 'is-warn' : ''}`}><span>Duplicate headers</span><strong>{activeAnalysis.duplicate_headers.length}</strong><small>{activeAnalysis.ambiguous_columns.length ? `${activeAnalysis.ambiguous_columns.length} ambiguous column(s)` : 'No ambiguous headers'}</small></div>
                </div>

                {activeAnalysis.missing_fields.length > 0 && (
                  <div className="api-error" role="alert">
                    <strong>Required model features are not mapped.</strong>
                    <p>Missing: {activeAnalysis.missing_fields.map(displayFeatureName).join(', ')}. Map each field to a source column below. Missing financial values are never imputed.</p>
                  </div>
                )}

                <div className="batch-section-head">
                  <div>
                    <h3>Column mapping</h3>
                    <p>Header matching ignores case, spaces and punctuation only when the match is unique. Ambiguous or duplicate headers are never guessed.</p>
                  </div>
                  <button type="button" className="button-secondary" onClick={() => setMappingOpen((open) => !open)}>
                    {mappingOpen ? 'Hide mapping' : 'Show mapping'}
                  </button>
                </div>

                {mappingOpen && (
                  <div className="batch-mapping-panel">
                    <div className="batch-required-grid">
                      {activeRequired.map((field) => {
                        const sourceIndex = activeReverse[field]
                        return (
                          <div key={field} className={`batch-required-item ${sourceIndex === undefined ? 'missing' : ''}`}>
                            <strong>{field}</strong>
                            <span>{sourceIndex === undefined ? 'Not mapped' : `${activeAnalysis.headers[sourceIndex]} · col ${sourceIndex + 1}`}</span>
                          </div>
                        )
                      })}
                      <div className={`batch-required-item ${activeReverse.borrower_reference === undefined ? 'optional' : ''}`}>
                        <strong>borrower_reference</strong>
                        <span>{activeReverse.borrower_reference === undefined ? 'Optional identifier — not mapped' : `${activeAnalysis.headers[activeReverse.borrower_reference]} · col ${activeReverse.borrower_reference + 1}`}</span>
                      </div>
                    </div>

                    {activeMappingProblem.duplicated.length > 0 && (
                      <p className="batch-inline-error">A model feature is mapped to more than one column: {activeMappingProblem.duplicated.map(displayFeatureName).join(', ')}.</p>
                    )}

                    <div className="batch-mapping-scroll">
                      <table className="batch-data-table batch-mapping-table">
                        <thead>
                          <tr>
                            <th>#</th>
                            <th>Uploaded column</th>
                            <th>Maps to model feature</th>
                            <th>Note</th>
                          </tr>
                        </thead>
                        <tbody>
                          {activeAnalysis.headers.map((header, index) => {
                            const duplicate = activeAnalysis.duplicate_headers.find((item) => item.indices.includes(index))
                            return (
                              <tr key={`${header}-${index}`}>
                                <td>{index + 1}</td>
                                <td title={sanitizeCell(header)}>{header ? displayFeatureName(header) : '—'}</td>
                                <td>
                                  <select
                                    aria-label={`Mapping for column ${index + 1}: ${displayFeatureName(header)}`}
                                    value={activeMapping[String(index)] ?? ''}
                                    onChange={(event) => void changeMapping(index, event.target.value)}
                                  >
                                    <option value="">Ignore / metadata</option>
                                    <option value="borrower_reference">borrower_reference (identifier only)</option>
                                    {TAIWAN_REQUIRED_FIELDS.map((field) => (
                                      <option key={field} value={field}>{displayFeatureName(field)}</option>
                                    ))}
                                  </select>
                                </td>
                                <td>
                                  {duplicate
                                    ? <span className="batch-inline-badge warn">Duplicate header</span>
                                    : activeAnalysis.identifier_columns.some((column) => column.index === index)
                                      ? <span className="batch-inline-badge">Identifier / metadata</span>
                                      : activeAnalysis.extra_columns.some((column) => column.index === index)
                                        ? <span className="batch-inline-badge">Extra column</span>
                                        : <span className="batch-inline-badge ok">Matched</span>}
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                    <p className="batch-inline-hint">Selecting a feature that is already mapped elsewhere moves the mapping to this column. Extra columns are never sent to the model. Formula cells in required fields are rejected; values are never invented.</p>
                    {analyzing[activeSheet] && <div className="inline-loading" role="status">Re-validating worksheet with the new mapping…</div>}
                    {analysisError && analysisErrorSheet === activeSheet && <div className="api-error" role="alert"><strong>Mapping validation failed.</strong><p>{analysisError}</p></div>}
                  </div>
                )}

                <div className="batch-section-head">
                  <div>
                    <h3>Data preview</h3>
                    <p>First {Math.min(activeAnalysis.rows.length, PREVIEW_PAGE_SIZE)} rows shown per page. Only this table scrolls horizontally.</p>
                  </div>
                  <div className="batch-preview-tools">
                    <input
                      type="search"
                      value={previewQuery}
                      onChange={(event) => { setPreviewQuery(event.target.value); setPreviewPage(1) }}
                      placeholder="Search columns…"
                      aria-label="Search preview columns"
                    />
                    <button type="button" className="button-secondary" onClick={() => setColumnPanelOpen((open) => !open)}>
                      Columns ({activeAnalysis.headers.length - hiddenColumns.size}/{activeAnalysis.headers.length})
                    </button>
                  </div>
                </div>

                {columnPanelOpen && (
                  <div className="batch-column-panel">
                    <div className="batch-column-list">
                      {activeAnalysis.headers.map((header, index) => (
                        <label key={`${header}-${index}`}>
                          <input type="checkbox" checked={!hiddenColumns.has(index)} onChange={() => toggleColumn(index)} />
                          <span title={header}>{header ? displayFeatureName(header) : `Column ${index + 1}`}</span>
                        </label>
                      ))}
                    </div>
                    <button type="button" className="button-secondary" onClick={() => setHiddenColumns(new Set())}>Show all columns</button>
                  </div>
                )}

                <div className="batch-table-scroll">
                  <table className="batch-data-table">
                    <thead>
                      <tr>
                        <th className="batch-row-number">Source row</th>
                        {previewColumns.map(({ header, index }) => (
                          <th key={`${header}-${index}`} title={header}>{header ? displayFeatureName(header) : `Column ${index + 1}`}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {previewRows.length === 0 && (
                        <tr><td colSpan={Math.max(1, previewColumns.length + 1)} className="batch-table-empty">No preview rows match the current column filter.</td></tr>
                      )}
                      {previewRows.map((row, rowPosition) => (
                        <tr key={`${activeAnalysis.row_numbers[(safePreviewPage - 1) * PREVIEW_PAGE_SIZE + rowPosition]}-${rowPosition}`}>
                          <td className="batch-row-number">{activeAnalysis.row_numbers[(safePreviewPage - 1) * PREVIEW_PAGE_SIZE + rowPosition]}</td>
                          {previewColumns.map(({ index }) => (
                            <td key={index} title={row[index] ?? ''}>{row[index] ?? ''}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="batch-pagination">
                  <span>
                    Page {safePreviewPage} of {previewPageCount} · rows {activeAnalysis.rows.length ? (safePreviewPage - 1) * PREVIEW_PAGE_SIZE + 1 : 0}–
                    {Math.min(safePreviewPage * PREVIEW_PAGE_SIZE, activeAnalysis.rows.length)} of {activeAnalysis.rows.length}
                  </span>
                  <div>
                    <button type="button" className="button-secondary" disabled={safePreviewPage <= 1} onClick={() => setPreviewPage(safePreviewPage - 1)}>Previous</button>
                    <button type="button" className="button-secondary" disabled={safePreviewPage >= previewPageCount} onClick={() => setPreviewPage(safePreviewPage + 1)}>Next</button>
                  </div>
                </div>

                {activeAnalysis.validation.errors.length > 0 && (
                  <details className="batch-errors" open>
                    <summary>
                      Validation errors ({activeAnalysis.validation.errors.length}{activeAnalysis.validation.truncated_errors ? '+' : ''})
                    </summary>
                    <div className="batch-table-scroll">
                      <table className="batch-data-table batch-error-table">
                        <thead><tr><th>Source row</th><th>Feature</th><th>Source column</th><th>Message</th></tr></thead>
                        <tbody>
                          {activeAnalysis.validation.errors.slice(0, 100).map((issue, index) => (
                            <tr key={`${issue.source_row}-${issue.column}-${index}`}>
                              <td>{issue.source_row}</td>
                              <td>{displayFeatureName(issue.column)}</td>
                              <td>{displayFeatureName(issue.source_column)}</td>
                              <td>{displayUserText(issue.message)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <button type="button" className="button-secondary" onClick={downloadValidationErrors}>Download validation errors CSV</button>
                  </details>
                )}

                {activeAnalysis.validation.warnings.length > 0 && (
                  <details className="batch-errors">
                    <summary>Warnings ({activeAnalysis.validation.warning_rows} row(s))</summary>
                    <div className="batch-table-scroll">
                      <table className="batch-data-table batch-error-table">
                        <thead><tr><th>Source row</th><th>Feature</th><th>Source column</th><th>Warning</th></tr></thead>
                        <tbody>
                          {activeAnalysis.validation.warnings.slice(0, 50).map((issue, index) => (
                            <tr key={`${issue.source_row}-${issue.column}-${index}`}>
                              <td>{issue.source_row}</td>
                              <td>{displayFeatureName(issue.column)}</td>
                              <td>{displayFeatureName(issue.source_column)}</td>
                              <td>{displayUserText(issue.message)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                )}

                <div className="batch-actions">
                  <button type="button" className="button-secondary" onClick={() => setStep(1)}>Back to upload</button>
                  <button type="button" className="button-primary" disabled={!canContinue} onClick={() => goToStep(3)}>
                    Continue to Step 3
                  </button>
                </div>
                {!canContinue && (
                  <p className="batch-inline-hint">
                    {sheetReadiness.issues[0] ?? 'Map all required features and ensure at least one valid row before continuing.'}
                  </p>
                )}
              </>
            )}
          </section>
        </div>
      )}

      {step === 3 && (
        <div className="batch-step-panel">
          {!result && (
            <section className="panel batch-run-panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">STEP 3</p>
                  <h2>Run batch prediction</h2>
                  <p>The validated rows will be sent to the live Taiwan research endpoint. No example or fallback predictions are used.</p>
                </div>
                <span className="source-tag source-live-unvalidated">Research inference</span>
              </div>
              <div className="batch-run-summary">
                {selectedSheets.map((name) => {
                  const analysis = analyses[name]
                  return (
                    <div key={name} className="batch-run-sheet">
                      <strong title={name}>{name}</strong>
                      <span>{analysis?.row_count ?? 0} rows · {analysis?.validation.valid_rows ?? 0} valid · {analysis?.validation.invalid_rows ?? 0} invalid</span>
                      <small>{mappingIssues(mappings[name] ?? {}, analysis?.required_fields ?? TAIWAN_REQUIRED_FIELDS).missing.length === 0 ? 'Schema mapped' : 'Needs mapping'}</small>
                    </div>
                  )
                })}
              </div>
              <div className="batch-run-total">
                <span>Total rows to submit</span>
                <strong>{selectedRowTotal}</strong>
                <small>Rows with validation errors will be returned individually as failed rows; nothing is imputed.</small>
              </div>
              {runState === 'running' ? (
                <div className="batch-running" role="status">
                  <span className="batch-spinner" aria-hidden="true" />
                  <div>
                    <strong>Scoring {selectedRowTotal} row(s) across {selectedSheets.length} worksheet(s)…</strong>
                    <p>The request is running against the backend. Predictions appear only after the backend responds.</p>
                  </div>
                </div>
              ) : (
                <div className="batch-actions">
                  <button type="button" className="button-secondary" onClick={() => setStep(2)}>Back to validation</button>
                  <button type="button" className="button-primary" disabled={!canContinue} onClick={() => void runBatch()}>
                    Run batch prediction
                  </button>
                </div>
              )}
              {runError && (
                <div className="api-error" role="alert">
                  <strong>The batch request failed.</strong>
                  <p>{runError}</p>
                  <button type="button" className="button-secondary" onClick={() => void runBatch()}>Retry</button>
                </div>
              )}
            </section>
          )}

          {result && summary && (
            <>
              <div className={`batch-success ${summary.failed ? 'with-failures' : ''}`} role="status">
                <div>
                  <strong>
                    Prediction complete — {summary.succeeded} of {summary.total} row(s) scored
                    {summary.failed ? `, ${summary.failed} failed` : ''}.
                  </strong>
                  <p>
                    Returned by the backend at {result.generated_at ?? 'an unrecorded time'} · model {result.model_id} ·
                    {' '}{result.calibrated ? (result.calibration_method ?? 'calibrated') : 'not calibrated'}.
                  </p>
                </div>
                <button type="button" className="button-secondary" onClick={() => setStep(2)}>Back to validation</button>
              </div>

              <div className="batch-kpi-grid exhibition-result-kpis">
                <div className="panel batch-kpi"><span>Total rows submitted</span><strong>{animatedTotal}</strong><small>All rows returned by the backend</small></div>
                <div className="panel batch-kpi"><span>Successfully scored</span><strong>{animatedSucceeded}</strong><small>Denominator for probability statistics</small></div>
                <div className="panel batch-kpi"><span>Rows needing review / correction</span><strong>{animatedFailed}</strong><small>Validation or inference did not complete</small></div>
                <div className="panel batch-kpi"><span>Mean estimated PD</span><strong>{animatedMean}</strong><small>{summary.succeeded ? `Denominator: ${summary.succeeded} scored rows` : 'No scored rows'}</small></div>
                <div className="panel batch-kpi"><span>Median estimated PD</span><strong>{animatedMedian}</strong><small>{summary.succeeded ? `Denominator: ${summary.succeeded} scored rows` : 'No scored rows'}</small></div>
                <div className="panel batch-kpi batch-kpi-risk">
                  <span>Risk mix</span>
                  <strong>L {summary.lowRisk} · M {summary.mediumRisk} · H {summary.highRisk}</strong>
                  <small>Low &lt;25% · Medium 25% to &lt;50% · High ≥50% · denominator {summary.succeeded}</small>
                </div>
              </div>

              {summary.succeeded > 0 && <div className="batch-example-grid"><section className="panel"><h3>Lowest estimated PD example</h3><p>{pdExamples.lowest?.borrower_reference ?? `Row ${pdExamples.lowest?.row_index}`} · {formatProbability(pdExamples.lowest?.prediction?.probability, 2)}</p><small>Research estimate only; not a lending decision.</small></section><section className="panel"><h3>Highest estimated PD example</h3><p>{pdExamples.highest?.borrower_reference ?? `Row ${pdExamples.highest?.row_index}`} · {formatProbability(pdExamples.highest?.prediction?.probability, 2)}</p><small>Research estimate only; not a lending decision.</small></section></div>}

              {summary.succeeded === 0 && (
                <div className="empty-state">
                  <span className="empty-icon" aria-hidden="true">◌</span>
                  <h3>No rows could be scored</h3>
                  <p>Every submitted row failed validation or inference. Probability statistics are unavailable rather than zero; review the row errors below.</p>
                </div>
              )}

              {summary.succeeded > 0 && (
                <div className="batch-charts-grid exhibition-result-charts">
                  <RiskDistributionChart summary={summary} />
                  <ProbabilityHistogram summary={summary} />
                  <CumulativeProbabilityChart summary={summary} />
                  <StatusChart summary={summary} />
                  <div className="batch-chart-wide"><RiskBySheetChart summary={summary} /></div>
                </div>
              )}

              <section className="panel exhibition-results-table-panel">
                <div className="panel-heading">
                  <div>
                    <h2>Individual borrower results</h2>
                    <p>Model PD and the reported non-default complement (1 − PD) are estimates, not observed outcomes or a repayment guarantee.</p>
                  </div>
                  <span className="source-tag">{filteredResults.length} matching row(s)</span>
                </div>

                <div className="batch-result-toolbar">
                  <div className="batch-filter-group" role="group" aria-label="Filter results">
                    {FILTERS.map((item) => {
                      const count = item.id === 'all'
                        ? result.results.length
                        : item.id === 'scored'
                          ? summary.succeeded
                          : item.id === 'failed'
                            ? summary.failed
                            : result.results.filter((row) => row.prediction?.risk_category === item.id).length
                      return (
                        <button
                          key={item.id}
                          type="button"
                          className={filter === item.id ? 'active' : ''}
                          aria-pressed={filter === item.id}
                          onClick={() => changeFilter(item.id)}
                        >
                          {item.label} <span>{count}</span>
                        </button>
                      )
                    })}
                  </div>
                  <input
                    type="search"
                    value={resultQuery}
                    onChange={(event) => { setResultQuery(event.target.value); setResultPage(1) }}
                    placeholder="Search reference, sheet, row, error…"
                    aria-label="Search batch results"
                  />
                </div>

                <div className="batch-table-scroll batch-results-scroll">
                  <table className="batch-data-table batch-results-table">
                    <thead>
                      <tr>
                        <th aria-sort={sortKey === 'result_index' ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}>
                          <button type="button" className="batch-sort" onClick={() => changeSort('result_index')}># {sortKey === 'result_index' ? (sortDir === 'asc' ? '↑' : '↓') : ''}</button>
                        </th>
                        <th aria-sort={sortKey === 'reference' ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}>
                          <button type="button" className="batch-sort" onClick={() => changeSort('reference')}>Borrower reference {sortKey === 'reference' ? (sortDir === 'asc' ? '↑' : '↓') : ''}</button>
                        </th>
                        <th aria-sort={sortKey === 'sheet' ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}>
                          <button type="button" className="batch-sort" onClick={() => changeSort('sheet')}>Worksheet {sortKey === 'sheet' ? (sortDir === 'asc' ? '↑' : '↓') : ''}</button>
                        </th>
                        <th aria-sort={sortKey === 'source_row' ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}>
                          <button type="button" className="batch-sort" onClick={() => changeSort('source_row')}>Source row {sortKey === 'source_row' ? (sortDir === 'asc' ? '↑' : '↓') : ''}</button>
                        </th>
                        <th>Status</th>
                        <th aria-sort={sortKey === 'probability' ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}>
                          <button type="button" className="batch-sort" onClick={() => changeSort('probability')}>Estimated PD {sortKey === 'probability' ? (sortDir === 'asc' ? '↑' : '↓') : ''}</button>
                        </th>
                        <th>Estimated non-default complement</th>
                        <th>Risk</th>
                        <th>Detail</th>
                      </tr>
                    </thead>
                    <tbody>
                      {visibleResults.length === 0 && (
                        <tr><td colSpan={9} className="batch-table-empty">No results match this filter or search.</td></tr>
                      )}
                      {visibleResults.map((row) => (
                        <tr key={`${row.result_index ?? row.row_index}-${row.sheet_name ?? ''}-${row.source_row ?? ''}`} className={riskClass(row.prediction?.risk_category)}>
                          <td>{row.result_index ?? row.row_index}</td>
                          <td title={String(row.borrower_reference ?? '')}>{row.borrower_reference ?? '—'}</td>
                          <td title={row.sheet_name ?? ''}>{row.sheet_name ?? '—'}</td>
                          <td>{row.source_row ?? row.row_index}</td>
                          <td>
                            <span className={`batch-status ${row.status === 'success' ? 'ok' : 'blocked'}`}>
                              {row.status === 'success' ? 'Scored' : 'Failed'}
                            </span>
                          </td>
                          <td className="batch-probability">{formatProbability(row.prediction?.probability, 2)}</td>
                          <td className="batch-probability">{formatProbability(repaymentComplement(row.prediction?.probability), 2)}</td>
                          <td>
                            {row.prediction?.risk_category
                              ? <span className={`batch-risk-pill ${riskClass(row.prediction.risk_category)}`}>{row.prediction.risk_category}</span>
                              : '—'}
                          </td>
                          <td className="batch-error-cell" title={displayUserText(row.error_message ?? '')}>
                            {row.error_message ? displayUserText(row.error_message) : row.prediction ? <details className="batch-row-explanation"><summary>View explanation</summary><div className="batch-explanation-body">
                              <p><b>Assessment:</b> {formatProbability(row.prediction.probability, 2)} estimated PD; {formatProbability(repaymentComplement(row.prediction.probability), 2)} mathematical complement.</p>
                              <p><b>Research classification:</b> {classifyResearchProbability(row.prediction.probability, row.prediction.threshold).label}; {row.prediction.probability.toFixed(4)} {row.prediction.probability < row.prediction.threshold ? '<' : '>='} {row.prediction.threshold.toFixed(4)} research threshold.</p>
                              <p><b>Factors moving estimated risk higher:</b> {(row.prediction.feature_contributions ?? []).filter((item) => item.direction === 'increases_risk').map((item) => `${batchFeatureLabel(item.feature)} (${item.feature}) — ${batchFeatureExplanation(item.feature)} Submitted ${row.submitted_features?.[item.feature] ?? 'derived'} value${item.feature.match(/^(LIMIT_BAL|BILL_AMT\d|PAY_AMT\d)$/) ? ' · Taiwan dataset monetary units (NT$)' : ''}; contribution ${item.contribution.toFixed(4)} model-output units.`).join(' ') || 'No risk-increasing attribution returned.'}</p>
                              <p><b>Factors moving estimated risk lower:</b> {(row.prediction.feature_contributions ?? []).filter((item) => item.direction === 'decreases_risk').map((item) => `${batchFeatureLabel(item.feature)} (${item.feature}) — ${batchFeatureExplanation(item.feature)} Submitted ${row.submitted_features?.[item.feature] ?? 'derived'} value${item.feature.match(/^(LIMIT_BAL|BILL_AMT\d|PAY_AMT\d)$/) ? ' · Taiwan dataset monetary units (NT$)' : ''}; contribution ${item.contribution.toFixed(4)} model-output units.`).join(' ') || 'No risk-decreasing attribution returned.'}</p>
                              <p><b>Model / data:</b> {row.prediction.model_id} · {row.prediction.dataset_name ?? 'Default of Credit Card Clients'} · {row.prediction.geography ?? 'Taiwan'} · {row.prediction.calibration_method ?? 'not calibrated'}.</p>
                              <p><b>Limitation:</b> Research/demo output only; not validated for Indian borrowers or lending. The complement is arithmetic, not a repayment guarantee.</p>
                              <p className="batch-explanation-footnote">Attribution is a model explanation, not a causal explanation.</p>
                            </div></details> : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="batch-pagination">
                  <span>Page {safeResultPage} of {resultPageCount} · {filteredResults.length} matching row(s)</span>
                  <div>
                    <button type="button" className="button-secondary" disabled={safeResultPage <= 1} onClick={() => setResultPage(safeResultPage - 1)}>Previous</button>
                    <button type="button" className="button-secondary" disabled={safeResultPage >= resultPageCount} onClick={() => setResultPage(safeResultPage + 1)}>Next</button>
                  </div>
                </div>
              </section>

              <section className="panel">
                <div className="panel-heading">
                  <div>
                    <h2>Export results</h2>
                    <p>Exports use the actual backend results and preserve order, worksheet names and source rows. Text cells are neutralised against spreadsheet formula injection.</p>
                  </div>
                </div>
                <div className="batch-export-actions">
                  <button type="button" className="button-primary" onClick={downloadPredictionsCsv}>Download predictions CSV</button>
                  <button type="button" className="button-secondary" disabled={exporting} onClick={() => void downloadPredictionsXlsx()}>
                    {exporting ? 'Building Excel…' : 'Download predictions Excel'}
                  </button>
                  <button type="button" className="button-secondary" disabled={!validationErrorCount} onClick={downloadValidationErrors}>
                    Download validation errors {validationErrorCount ? `(${validationErrorCount})` : ''}
                  </button>
                  <button type="button" className="button-secondary" onClick={downloadReport}>Download analysis report (.md)</button>
                </div>
                {exportError && <div className="api-error" role="alert"><p>{exportError}</p></div>}
                <p className="chart-footnote">
                  The Excel download is generated by the backend with a summary sheet. CSV and Markdown files are generated
                  in the browser from the same response. No row-level borrower data is written to server logs by this workflow.
                </p>
                <div className="batch-actions">
                  <button type="button" className="button-secondary" onClick={startNewBatch}>Start a new batch</button>
                </div>
              </section>
            </>
          )}
        </div>
      )}
    </div>
  )
}
