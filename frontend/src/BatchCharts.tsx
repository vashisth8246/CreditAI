import type { BatchSummary, SheetStats } from './batch'
import { formatProbability } from './batch'

function ChartEmpty({ message }: { message: string }) {
  return (
    <div className="batch-chart-empty">
      <span aria-hidden="true">◌</span>
      <p>{message}</p>
    </div>
  )
}

export function RiskDistributionChart({ summary }: { summary: BatchSummary }) {
  const rows = [
    { label: 'Low', hint: '<25%', count: summary.lowRisk, className: 'low' },
    { label: 'Medium', hint: '25% to <50%', count: summary.mediumRisk, className: 'medium' },
    { label: 'High', hint: '>=50%', count: summary.highRisk, className: 'high' },
  ]
  return (
    <section className="panel batch-chart" aria-labelledby="batch-risk-chart-title">
      <div className="panel-heading">
        <div>
          <h2 id="batch-risk-chart-title">Risk distribution</h2>
          <p>Successfully scored rows only. Denominator: {summary.succeeded}.</p>
        </div>
      </div>
      {summary.succeeded === 0 ? (
        <ChartEmpty message="No scored rows yet. Run a batch to populate this chart." />
      ) : (
        <div className="batch-risk-bars">
          {rows.map((row) => (
            <div className="batch-risk-row" key={row.label}>
              <div className="batch-risk-label">
                <strong>{row.label}</strong>
                <span>{row.hint}</span>
                <b>{row.count}</b>
              </div>
              <div className="batch-risk-track" title={`${row.label}: ${row.count} of ${summary.succeeded} scored rows`}>
                <i
                  className={`batch-risk-fill ${row.className}`}
                  style={{ width: `${(row.count / summary.succeeded) * 100}%` }}
                />
              </div>
              <small>
                {summary.succeeded ? ((row.count / summary.succeeded) * 100).toFixed(1) : '0.0'}% of scored rows
              </small>
            </div>
          ))}
          {summary.unknownRisk > 0 && <p className="chart-footnote">{summary.unknownRisk} scored row(s) had no documented risk tier.</p>}
        </div>
      )}
    </section>
  )
}

export function ProbabilityHistogram({ summary }: { summary: BatchSummary }) {
  const values = summary.histogram.map((bin) => bin.count)
  const max = Math.max(1, ...values)
  const total = values.reduce((sum, value) => sum + value, 0)
  return (
    <section className="panel batch-chart" aria-labelledby="batch-histogram-title">
      <div className="panel-heading">
        <div>
          <h2 id="batch-histogram-title">Estimated default probability distribution</h2>
          <p>Distribution of model-estimated PD, not observed default rates. Denominator: {summary.succeeded}.</p>
        </div>
      </div>
      {summary.succeeded === 0 ? (
        <ChartEmpty message="Probability bands appear after at least one row is scored." />
      ) : (
        <>
          <div className="histogram" role="img" aria-label="Histogram of estimated default probabilities in percentage bands">
            {summary.histogram.map((bin) => (
              <div
                className="hist-column"
                key={bin.label}
                tabIndex={0}
                aria-label={`${bin.label}: ${bin.count} of ${total} scored rows`}
              >
                <span className="hist-count">{bin.count}</span>
                <div
                  className="hist-bar"
                  style={{ height: `${(bin.count / max) * 150}px` }}
                />
                <span className="hist-label">{bin.label}</span>
                <span className="chart-tooltip">{bin.count} borrowers ({total ? ((bin.count / total) * 100).toFixed(1) : '0.0'}%)</span>
              </div>
            ))}
          </div>
          <p className="chart-footnote">Bands are mutually exclusive; 100% is included in the final band.</p>
        </>
      )}
    </section>
  )
}

export function CumulativeProbabilityChart({ summary }: { summary: BatchSummary }) {
  const width = 620
  const height = 240
  const padding = { top: 18, right: 18, bottom: 34, left: 44 }
  const plotWidth = width - padding.left - padding.right
  const plotHeight = height - padding.top - padding.bottom
  const sorted = [...summary.probabilities].sort((a, b) => a - b)
  const points: { x: number; y: number; probability: number; share: number }[] = [{ x: 0, y: 0, probability: 0, share: 0 }]
  const step = Math.max(1, Math.ceil(sorted.length / 120))
  for (let index = 0; index < sorted.length; index += step) {
    const probability = sorted[index]
    const share = (index + 1) / sorted.length
    points.push({ x: probability, y: share, probability, share })
  }
  points.push({ x: 1, y: 1, probability: 1, share: 1 })

  const polyline = points
    .map((point) => `${padding.left + point.x * plotWidth},${padding.top + (1 - point.y) * plotHeight}`)
    .join(' ')
  const area = `${padding.left},${padding.top + plotHeight} ${polyline} ${padding.left + plotWidth},${padding.top + plotHeight}`

  return (
    <section className="panel batch-chart" aria-labelledby="batch-cumulative-title">
      <div className="panel-heading">
        <div>
          <h2 id="batch-cumulative-title">Cumulative share by estimated PD</h2>
          <p>How borrowers concentrate at lower predicted risk. Denominator: {summary.succeeded} scored rows.</p>
        </div>
      </div>
      {summary.succeeded === 0 ? (
        <ChartEmpty message="The cumulative curve needs at least one scored row." />
      ) : (
        <div className="batch-cumulative-wrap">
          <svg
            viewBox={`0 0 ${width} ${height}`}
            role="img"
            aria-label="Cumulative share of scored borrowers by estimated default probability"
          >
            {[0, 0.25, 0.5, 0.75, 1].map((tick) => (
              <g key={tick}>
                <line
                  className="grid-line"
                  x1={padding.left}
                  x2={padding.left + plotWidth}
                  y1={padding.top + (1 - tick) * plotHeight}
                  y2={padding.top + (1 - tick) * plotHeight}
                />
                <text className="axis-label" x={padding.left - 8} y={padding.top + (1 - tick) * plotHeight + 3} textAnchor="end">
                  {Math.round(tick * 100)}%
                </text>
              </g>
            ))}
            {[0, 0.25, 0.5, 0.75, 1].map((tick) => (
              <text
                key={`x-${tick}`}
                className="axis-label"
                x={padding.left + tick * plotWidth}
                y={height - 12}
                textAnchor="middle"
              >
                {Math.round(tick * 100)}%
              </text>
            ))}
            <polygon points={area} fill="rgba(22, 160, 137, 0.10)" />
            <polyline points={polyline} fill="none" stroke="#159983" strokeWidth="2.5" />
            {[0.25, 0.5, 0.75].map((tick) => {
              const closest = points.reduce((best, point) =>
                Math.abs(point.x - tick) < Math.abs(best.x - tick) ? point : best,
              )
              return (
                <circle key={tick} cx={padding.left + closest.x * plotWidth} cy={padding.top + (1 - closest.y) * plotHeight} r="3.5" fill="#fff" stroke="#159580" strokeWidth="2">
                  <title>{`At PD ${formatProbability(tick)} or lower: ${(closest.share * 100).toFixed(1)}% of scored borrowers`}</title>
                </circle>
              )
            })}
            <text className="axis-label" x={padding.left + plotWidth / 2} y={height - 24} textAnchor="middle">
              Estimated default probability
            </text>
          </svg>
          <p className="chart-footnote">Curve points are cumulative: x = estimated PD threshold, y = share of scored borrowers at or below it.</p>
        </div>
      )}
    </section>
  )
}

export function StatusChart({ summary }: { summary: BatchSummary }) {
  const total = summary.total
  const rows = [
    { label: 'Successfully scored', count: summary.succeeded, className: 'success' },
    { label: 'Failed or rejected', count: summary.failed, className: 'failed' },
  ]
  return (
    <section className="panel batch-chart" aria-labelledby="batch-status-title">
      <div className="panel-heading">
        <div>
          <h2 id="batch-status-title">Prediction status</h2>
          <p>Every submitted row is counted exactly once. Denominator: {total}.</p>
        </div>
      </div>
      {total === 0 ? (
        <ChartEmpty message="Status counts appear after a batch run." />
      ) : (
        <div className="batch-status-bars">
          {rows.map((row) => (
            <div className="batch-status-row" key={row.label}>
              <div className="batch-status-label">
                <span>{row.label}</span>
                <b>{row.count}</b>
              </div>
              <div className="batch-status-track" title={`${row.label}: ${row.count} of ${total}`}>
                <i className={row.className} style={{ width: `${(row.count / total) * 100}%` }} />
              </div>
              <small>{((row.count / total) * 100).toFixed(1)}% of submitted rows</small>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function SheetRiskRow({ sheet }: { sheet: SheetStats }) {
  const total = Math.max(1, sheet.scored)
  const segments = [
    { key: 'low', value: sheet.lowRisk, label: 'Low' },
    { key: 'medium', value: sheet.mediumRisk, label: 'Medium' },
    { key: 'high', value: sheet.highRisk, label: 'High' },
  ]
  return (
    <div className="batch-sheet-risk-row">
      <div className="batch-sheet-risk-head">
        <strong title={sheet.name}>{sheet.name}</strong>
        <span>n = {sheet.scored} scored / {sheet.total} rows</span>
      </div>
      <div className="batch-sheet-risk-track">
        {segments.map((segment) =>
          segment.value ? (
            <i
              key={segment.key}
              className={segment.key}
              style={{ width: `${(segment.value / total) * 100}%` }}
              title={`${sheet.name} — ${segment.label}: ${segment.value} of ${sheet.scored} scored`}
            />
          ) : null,
        )}
      </div>
      <small>
        Low {sheet.lowRisk} · Medium {sheet.mediumRisk} · High {sheet.highRisk} · Mean {formatProbability(sheet.meanProbability)}
      </small>
    </div>
  )
}

export function RiskBySheetChart({ summary }: { summary: BatchSummary }) {
  const sheets = summary.sheets.filter((sheet) => sheet.scored > 0)
  if (sheets.length < 2) return null
  return (
    <section className="panel batch-chart" aria-labelledby="batch-sheet-risk-title">
      <div className="panel-heading">
        <div>
          <h2 id="batch-sheet-risk-title">Risk distribution by worksheet</h2>
          <p>Sheets are scored independently and never concatenated. Sample size is shown per sheet.</p>
        </div>
      </div>
      <div className="batch-sheet-risk-list">
        {sheets.map((sheet) => <SheetRiskRow key={sheet.name} sheet={sheet} />)}
      </div>
      <div className="batch-chart-legend" aria-hidden="true">
        <span><i className="low" />Low</span>
        <span><i className="medium" />Medium</span>
        <span><i className="high" />High</span>
      </div>
    </section>
  )
}
