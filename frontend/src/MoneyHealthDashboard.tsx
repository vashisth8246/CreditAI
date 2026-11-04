import { money, metrics } from './moneyHealth'
import type { Result } from './moneyHealth'
import { analyzeMoney, analysisCharts, analysisMethod } from './moneyHealthAnalysis'

export function Chart({ title, rows, insight }: { title: string; rows: [string, number][]; insight?: string }) {
  const extent = Math.max(1, ...rows.map(([, amount]) => Math.abs(amount)))
  const signed = rows.some(([, amount]) => amount < 0)
  return <figure className="mh-chart">
    <figcaption>{title} · INR</figcaption>
    {rows.length === 0 && <p>No categories provided.</p>}
    {rows.map(([label, amount]) => <div key={label} className="mh-bar">
      <div><span>{label}</span><strong>{money(amount)}</strong></div>
      <svg aria-hidden="true" viewBox={signed ? '-100 0 200 8' : '0 0 100 8'} preserveAspectRatio="none">
        <rect x={signed ? -100 : 0} width={signed ? 200 : 100} height="8" fill="#e5eee8" />
        <rect x={amount < 0 ? amount / extent * 100 : 0} width={Math.abs(amount) / extent * 100} height="8" fill={amount < 0 ? '#a53939' : '#18704e'} />
        <path d="M0 0 V8" stroke="#283b32" strokeWidth=".4" />
      </svg>
    </div>)}
    {insight && <p className="mh-chart-insight">{insight}</p>}
  </figure>
}

const colors = ['#176445', '#367d6c', '#4d6251', '#a96032', '#5c618d', '#487ab0', '#796144']
function Allocation({ result, analysis }: { result: Result; analysis: ReturnType<typeof analyzeMoney> }) {
  return <figure className="mh-chart mh-allocation">
    <figcaption>Where your money goes</figcaption>
    {analysis.allocationTotal > 0 ? <>
      <div className="mh-donut-layout">
        <div className="mh-donut">
          <svg viewBox="0 0 120 120" aria-hidden="true">
            {analysis.allocation.map(([label, amount], index) => {
              const share = amount / analysis.allocationTotal * 100
              const start = analysis.allocation.slice(0, index).reduce((sum, [, value]) => sum + value, 0) / analysis.allocationTotal * 100
              return <circle key={label} cx="60" cy="60" r="45" pathLength="100" fill="none"
                stroke={colors[index % colors.length]} strokeWidth="18" strokeDasharray={share + ' ' + (100 - share)}
                strokeDashoffset={-start} transform="rotate(-90 60 60)" />
            })}
          </svg>
          <strong>{money(analysis.allocationTotal)}</strong>
        </div>
        <ul className="mh-chart-legend">{analysis.allocation.map(([label, amount], index) => <li key={label}>
          <i aria-hidden="true" style={{ background: colors[index % colors.length] }} />
          <span>{label}</span><strong>{money(amount)} · {(amount / analysis.allocationTotal * 100).toFixed(1)}%</strong>
        </li>)}</ul>
      </div>
      <p className="mh-chart-insight">{result.balance < 0
        ? `Shares are of total spending. The ${money(-result.balance)} shortfall is shown separately.`
        : 'Shares are of total money received. Any money remaining is shown as its own slice.'}</p>
    </> : <p>No positive amounts are available to chart.</p>}
  </figure>
}

export function Dashboard({ result, profile, provenance, example }: {
  result: Result; profile: number; provenance: string; example: boolean
}) {
  const a = analyzeMoney(result, profile)
  const debtEntered = result.register.find(field => field.kind === 'debt')?.amount
  return <section className="mh-panel mh-analysis" aria-label="Financial dashboard">
    <header className="mh-results-hero">
      <p className="mh-kicker">03 · Financial snapshot</p>
      <h2 id="money-health-results" tabIndex={-1}>Your Money Health Analysis</h2>
      <span className="mh-provenance">{example ? provenance : 'SELF-REPORTED · Personal inputs'}</span> <a className="mh-chart-jump mh-controls" href="#money-health-charts">View charts ↓</a>
      <div className="mh-snapshot">
        <div><span>Monthly money received</span><strong>{money(result.funds)}</strong></div>
        <div><span>Total monthly expenses including EMI</span><strong>{money(result.outflow)}</strong></div>
        <div><span>{result.balance < 0 ? 'Monthly shortfall' : 'Money remaining'}</span><strong>{money(Math.abs(result.balance))}</strong></div>
        <div><span>Monthly balance as a share of funds</span><strong>{a.monthlyPercent === null ? 'Unavailable' : a.monthlyPercent.toFixed(2) + '%'}</strong>
          {a.monthlyPercent === null && <small>No positive funds received.</small>}</div>
      </div>
    </header>
    <div className="mh-interpretation">
      <h3>What do your numbers say about your money health?</h3>
      <p>{a.cashFlow}</p>
      {a.missing.length > 0 && <p>Not provided: {a.missing.join(', ')}. These amounts are excluded from totals. {a.blankEssential.length ? 'Missing essential expenses can make spending look lower and coverage look higher.' : 'Conclusions apply only to the amounts entered.'}</p>}
    </div>
    <div className="mh-grid mh-analysis-charts" id="money-health-charts">
      <Allocation result={result} analysis={a} />
      {analysisCharts(result, profile).map(chart => <Chart key={chart.title} {...chart} />)}
    </div>
    <h3>Financial health indicators</h3>
    <div className="mh-grid">
      <article className="mh-metric"><h4>Spending pressure</h4><strong>{a.pressure === null ? 'Unavailable' : a.pressure.toFixed(2) + '%'}</strong>
        <p>Total expenses including EMI divided by funds received. {a.pressure === null ? 'No positive funds received.' : 'This is the share of available money used by spending and debt.'}</p></article>
      <article className="mh-metric"><h4>Emergency savings coverage</h4><strong>{a.emergencyMonths === null ? 'Not calculable from these inputs' : a.emergencyMonths.toFixed(2) + ' months'}</strong>
        <p>{a.coverageText} Essential expenses exclude EMI, optional spending and separate business costs. This estimate assumes the same essential spending rate.</p></article>
      <article className="mh-metric"><h4>Debt payment pressure</h4><strong>{!result.debt ? 'No monthly EMI entered.' : result.debtRatio === null ? 'Unavailable' : result.debtRatio.toFixed(2) + '%'}</strong>
        <p>{debtEntered === null ? 'The debt field was left blank.' : result.debt ? 'Monthly EMI divided by money received. This is a cash-flow measure.' : 'The debt amount was entered as zero.'}</p></article>
      <article className="mh-metric"><h4>Savings goal feasibility</h4><p>{a.goalText}</p></article>
    </div>
    <p className="mh-hint">{analysisMethod}</p>
    <details><summary>Show calculation details</summary><div className="mh-grid">
      {metrics(result).map(([label, value, formula, meaning]) => <article className="mh-metric" key={label}>
        <h4>{label}</h4><strong>{value}</strong><p>{meaning}</p><p>{formula} → {value}</p>
      </article>)}
    </div></details>
  </section>
}
