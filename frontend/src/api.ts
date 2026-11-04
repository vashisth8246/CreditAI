import type { BatchInspectResponse, BatchPredictionResult, Mapping } from './batch'

export type { BatchPredictionResult, BatchRowResult } from './batch'

export type ModelSummary = {
  model_id: string
  dataset_id: string
  dataset_name: string
  geography: string
  model_type: string
  test_roc_auc?: number
  test_pr_auc?: number
  calibration_status: string
  inference_ready: boolean
}

export type FeatureField = {
  type: 'numeric' | 'categorical'
  description: string
  required: boolean
  unit?: string
  range?: number[]
  values?: number[]
  value_labels?: Record<string, string>
}

export type ModelSchema = {
  model_id: string
  raw_features: Record<string, FeatureField>
  engineered_features?: string[]
}

export type ModelDetails = {
  model_id: string
  dataset_id: string
  dataset_name: string
  geography: string
  time_coverage: string
  target: string
  target_meaning: string
  model_type: string
  calibration_status: string
  calibration_method?: string | null
  limitations: string[]
  inference_ready: boolean
  global_feature_importance?: { feature: string; importance: number }[]
}

export type FeatureContribution = {
  feature: string
  contribution: number
  direction: string
}

export type Prediction = {
  model_id: string
  dataset_id: string
  dataset_name: string
  geography: string
  target: string
  target_meaning: string
  prediction_timestamp: string
  predicted_class: string
  probability: number
  risk_category: string
  threshold: number
  calibrated: boolean
  calibration_method: string | null
  limitations: string[]
  feature_contributions: FeatureContribution[] | null
}

export type CurvePoint = {
  x: number
  y: number
}

export type CalibrationBin = {
  bin: number
  pred_raw: number
  true_raw: number
  pred_cal: number | null
  true_cal: number | null
}

export type ThresholdSweepRow = {
  threshold: number
  accuracy: number
  precision: number
  recall: number
  f1_score: number
  tn: number
  fp: number
  fn: number
  tp: number
}

export type DecileRow = {
  decile: number
  borrowers: number
  defaults: number
  empirical_default_rate: number
  mean_calibrated_pd: number
  mean_raw_score: number
}

export type ModelComparisonRow = {
  model_name: string
  roc_auc: number
  pr_auc: number
  brier_score: number
  log_loss: number
  ks_statistic: number
  gini_coefficient: number
  accuracy: number
  precision: number
  recall: number
  f1_score: number
  is_calibrated: boolean
}

export type EvaluationArtifact = {
  metadata: {
    dataset_id: string
    dataset_name: string
    geography: string
    time_coverage: string
    target: string
    target_meaning: string
    split_design: string
    random_seed: number
    test_sample_count: number
    test_defaults: number
    test_prevalence: number
    evaluation_date: string
    primary_model: string
    calibration_status: string
    calibration_method: string
    calibrator_params?: { slope: number; intercept: number }
  }
  summary_metrics: {
    test_roc_auc: number
    test_pr_auc: number
    brier_score_raw: number
    brier_score_calibrated: number
    brier_improvement_pct: number
    log_loss_raw: number
    log_loss_calibrated: number
    ks_statistic: number
    gini_coefficient: number
    accuracy_at_0_5: number
    precision_at_0_5: number
    recall_at_0_5: number
    f1_at_0_5: number
  }
  confusion_matrix_default: {
    threshold: number
    true_negative: number
    false_positive: number
    false_negative: number
    true_positive: number
    total: number
  }
  curves: {
    roc: {
      title: string
      auc: number
      baseline_auc: number
      points: CurvePoint[]
    }
    pr: {
      title: string
      auc: number
      baseline_prevalence: number
      points: CurvePoint[]
    }
    calibration: {
      title: string
      bins: CalibrationBin[]
    }
    threshold_sweep: ThresholdSweepRow[]
  }
  risk_deciles: DecileRow[]
  model_comparison: ModelComparisonRow[]
  global_feature_importance: { feature: string; importance: number }[]
  limitations: string[]
}

export type SystemStatus = {
  backend_connectivity: 'connected' | 'disconnected'
  models_registered: number
  research_inference_ready: boolean
  indian_production_scoring: 'not_validated'
}

export const BATCH_PATH = '/v1/research/taiwan/batch-predict'
export const BATCH_INSPECT_PATH = '/v1/research/taiwan/batch/inspect'
export const BATCH_ANALYZE_PATH = '/v1/research/taiwan/batch/analyze'
export const BATCH_EXPORT_XLSX_PATH = '/v1/research/taiwan/batch/export/xlsx'

export { TAIWAN_REQUIRED_FIELDS } from './batch'

const CONFIGURED_API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const API_BASES = CONFIGURED_API_BASE
  ? [CONFIGURED_API_BASE]
  : import.meta.env.DEV
    ? ['', 'http://127.0.0.1:8000', 'http://localhost:8000']
    : ['']

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let lastError: Error | null = null

  for (const base of API_BASES) {
    try {
      const url = `${base}${path}`
      const response = await fetch(url, init)
      if (!response.ok) {
        let detail = `Request failed (${response.status}).`
        try {
          const body = (await response.json()) as { detail?: unknown; error?: { message?: string } }
          if (typeof body.detail === 'string') detail = body.detail
          else if (body.error?.message) detail = body.error.message
        } catch {
          /* keep status message */
        }
        throw new Error(detail)
      }
      return (await response.json()) as T
    } catch (err) {
      lastError = err instanceof Error ? err : new Error(String(err))
      if (lastError.name === 'AbortError') throw lastError
      // If it was a non-network error (e.g. 422 validation or 404), throw immediately
      if (err instanceof Error && !err.message.includes('Failed to fetch') && !err.message.includes('NetworkError')) {
        throw err
      }
    }
  }

  throw new Error(
    lastError?.message ||
      'The research API is unreachable. Check that the FastAPI backend is running (e.g. on port 8000), then retry.'
  )
}

type GuardianFinding = {
  field: string; code: string; severity: 'error' | 'warning' | 'information'
  explanation: string; evidence: string; action: string; blocks_inference: boolean
}
export type GuardianAssessment = {
  status: 'review_eligible' | 'manual_review_recommended' | 'input_correction_required' | 'reliability_not_evaluated' | 'model_unavailable'
  model_id: string; method: string; valid_fields: number; required_fields: number
  findings: GuardianFinding[]; distribution_findings: GuardianFinding[]
  distribution_evaluated: boolean; evaluation_available: boolean; reasons: string[]
  reference?: { dataset: string; sha256: string; train_count: number } | null
  model_provenance: string; limitations?: string
}
export type GuardianEvaluation = {
  status: 'evaluated' | 'not_evaluated'; reason?: string
  split?: { train: number; validation: number; test: number }
  quality_findings?: Record<string, number>
  evaluation?: { name: string; target_coverage?: number; cutoff?: number; coverage: number; retained: number; abstained: number;
    error_rate: number | null; error_delta_bootstrap_95?: [number, number] | null; roc_auc: number | null; average_precision: number | null; brier: number | null; log_loss: number | null }[]
}

export const researchApi = {
  health: () => request<{ status: string; scoring: string }>('/health'),
  buildInfo: () => request<{ commit_sha: string | null; short_commit: string | null; scoring_status: string }>('/v1/build', { cache: 'no-store' }),
  status: () => request<SystemStatus>('/v1/status'),
  models: () => request<{ models: ModelSummary[]; count: number }>('/v1/models'),
  details: (id: string) => request<ModelDetails>(`/v1/models/${encodeURIComponent(id)}`),
  schema: (id: string) => request<ModelSchema>(`/v1/models/${encodeURIComponent(id)}/schema`),
  evaluation: async (id: string): Promise<EvaluationArtifact> => {
    return request<EvaluationArtifact>(`/v1/models/${encodeURIComponent(id)}/evaluation`)
  },
  dashboardSnapshot: <T,>(signal?: AbortSignal) => request<T>('/v1/dashboard/snapshot', { cache: 'no-store', signal }),
  guardian: (model_id: string, features: Record<string, string>) =>
    request<{ assessment: GuardianAssessment; prediction: Prediction | null }>('/v1/research/reliability-assessment', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ model_id, features }),
    }),
  guardianEvaluation: () => request<GuardianEvaluation>('/v1/research/reliability-evaluation'),
  predict: (model_id: string, features: Record<string, number>) =>
    request<Prediction>('/v1/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_id, features }),
    }),
  batchInspect: (file: File, sheet?: string, mapping?: Mapping) =>
    uploadBatchFile<BatchInspectResponse>(BATCH_INSPECT_PATH, file, {
      ...(sheet ? { sheet } : {}),
      ...(mapping ? { mapping: JSON.stringify(mapping) } : {}),
    }),
  batchAnalyze: (file: File, sheet: string, mapping: Mapping) =>
    uploadBatchFile<BatchInspectResponse>(BATCH_ANALYZE_PATH, file, {
      sheet,
      mapping: JSON.stringify(mapping),
    }),
  batchPredict: (file: File, sheets?: { name: string; mapping: Mapping }[]) =>
    uploadBatchFile<BatchPredictionResult>(BATCH_PATH, file, sheets && sheets.length
      ? { sheets: JSON.stringify(sheets) }
      : {}),
  batchExportXlsx: async (payload: unknown): Promise<Blob> => {
    let lastError: Error | null = null
    for (const base of batchTargets()) {
      try {
        const response = await fetch(`${base}${BATCH_EXPORT_XLSX_PATH}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
        if (!response.ok) {
          throw new Error(await batchDetail(response, `Excel export failed (${response.status}).`))
        }
        return await response.blob()
      } catch (err) {
        lastError = err instanceof Error ? err : new Error(String(err))
        if (err instanceof Error && !err.message.includes('Failed to fetch') && !err.message.includes('NetworkError')) {
          throw err
        }
      }
    }
    throw new Error(lastError?.message || 'The batch research API is unreachable. Check that the FastAPI backend is running on port 8000.')
  },
}

function batchTargets(): string[] {
  return API_BASES
}

async function batchDetail(response: Response, fallback: string): Promise<string> {
  let detail = fallback
  try {
    const body = (await response.json()) as { detail?: unknown; error?: { message?: string } }
    if (typeof body.detail === 'string') detail = body.detail
    else if (body.detail) detail = JSON.stringify(body.detail)
    else if (body.error?.message) detail = body.error.message
  } catch {
    /* keep the status-based fallback */
  }
  return detail
}

async function uploadBatchFile<T>(path: string, file: File, fields: Record<string, string>): Promise<T> {
  let lastError: Error | null = null
  for (const base of batchTargets()) {
    try {
      const form = new FormData()
      form.append('file', file)
      for (const [key, value] of Object.entries(fields)) form.append(key, value)
      const response = await fetch(`${base}${path}`, { method: 'POST', body: form })
      if (!response.ok) {
        throw new Error(await batchDetail(response, `Batch request failed (${response.status}).`))
      }
      return (await response.json()) as T
    } catch (err) {
      lastError = err instanceof Error ? err : new Error(String(err))
      // Retry only when the request never reached the backend.
      if (err instanceof Error && !err.message.includes('Failed to fetch') && !err.message.includes('NetworkError')) {
        throw err
      }
    }
  }
  throw new Error(lastError?.message || 'The batch research API is unreachable. Check that the FastAPI backend is running on port 8000.')
}
