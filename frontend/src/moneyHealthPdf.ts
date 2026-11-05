import type { Content, TDocumentDefinitions } from 'pdfmake/interfaces'
import { charts, metrics, money } from './moneyHealth'
import type { Result } from './moneyHealth'
import { analyzeMoney, analysisCharts, analysisMethod } from './moneyHealthAnalysis'

type Report = {
  profile: string
  profileIndex: number
  hasScenario: boolean
  provenance: string
  example: boolean
  result: Result
  scenario: Result
  goalRows: [string, number][]
  goalExplanation: string
  scenarioNotes: string[]
  origin: string
  generated: string
}

export function applicationLink(origin: string) {
  const url = new URL('/', origin)
  const local = ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)
  return { url: url.href, label: local ? 'Local rehearsal link' : 'CreditAI on the current host' }
}

function chartBlock(chart: ReturnType<typeof charts>[number]): Content {
  const extent = Math.max(1, ...chart.rows.map(([, value]) => Math.abs(value)))
  const signed = chart.rows.some(([, value]) => value < 0)
  const zero = signed ? 250 : 0
  const scale = signed ? 250 : 500
  return {
    stack: [
      { text: chart.title + ' · INR', style: 'subheading' },
      ...(chart.rows.length ? chart.rows.map(([label, value]): Content => {
        const length = Math.abs(value) / extent * scale
        return {
          unbreakable: true,
          margin: [0, 0, 0, 4],
          stack: [
            { columns: [{ text: label }, { text: money(value), width: 145, alignment: 'right' }] },
            { canvas: [
              { type: 'rect', x: 0, y: 2, w: 500, h: 6, color: '#e4eee8' },
              { type: 'rect', x: value < 0 ? zero - length : zero, y: 2, w: length, h: 6, color: value < 0 ? '#a53939' : '#18704e' },
              { type: 'line', x1: zero, y1: 1, x2: zero, y2: 9, lineWidth: 0.5, lineColor: '#18352a' },
            ] },
          ],
        }
      }) : [{ text: 'No categories provided.' }]),
      { text: signed ? 'Red bars extend left from zero to show deficits.' : 'Green bars extend right from zero. Scale is shared within this chart.', style: 'note' },
    ],
  }
}

export function reportDefinition(report: Report): TDocumentDefinitions {
  const { result, scenario, profile, provenance, generated } = report
  const analysis = analyzeMoney(result, report.profileIndex)
  const baseline = metrics(result)
  const revised = metrics(scenario)
  const metricBlocks = baseline.map(([label, value, formula, meaning]): Content => ({
    unbreakable: true, margin: [0, 0, 0, 7],
    stack: [{ text: `${label}  /  ${value}`, bold: true }, `Calculation: ${formula} = ${value}`, meaning],
  }))
  const link = applicationLink(report.origin)
  const section = (text: string): Content => ({ text, style: 'heading', headlineLevel: 1 })
  const detail = (label: string, text: string): Content => ({
    text: [{ text: label + '  ', bold: true }, text], margin: [0, 0, 0, 5],
  })
  return {
    pageSize: 'A4',
    pageMargins: [44, 45, 44, 48],
    info: { title: 'CreditAI | My Money Health Report', author: 'CreditAI' },
    defaultStyle: { fontSize: 10, color: '#18352a', lineHeight: 1.05 },
    styles: {
      brand: { fontSize: 12, bold: true, color: '#18704e', margin: [0, 0, 0, 8] },
      title: { fontSize: 27, bold: true, margin: [0, 0, 0, 8] },
      heading: { fontSize: 16, bold: true, color: '#16593f', margin: [0, 11, 0, 5] },
      subheading: { fontSize: 11, bold: true, margin: [0, 8, 0, 5] },
      note: { fontSize: 9, color: '#456356', margin: [0, 2, 0, 3] },
    },
    footer: (currentPage, totalPages) => ({
      margin: [44, 12, 44, 0], fontSize: 9, color: '#456356',
      columns: ['CreditAI  /  My Money Health', { text: `Page ${currentPage} of ${totalPages}`, alignment: 'right' }],
    }),
    pageBreakBefore: (node, following) => node.headlineLevel === 1 && following.filter(item => item.text || item.stack || item.columns).length === 0,
    content: [
      { text: 'CREDITAI  /  EXHIBITION EXPERIENCE', style: 'brand' },
      { text: 'My Money Health Report', style: 'title' },
      detail('Profile', profile),
      detail('Generated', generated),
      { text: provenance, bold: true, color: '#16593f' },
      section('5W1H'),
      detail('Who', profile),
      detail('What', 'A snapshot of monthly cash flow, spending, debt commitments, savings and a hypothetical scenario.'),
      detail('When', generated),
      detail('Where', report.example ? 'An explicitly selected example, possibly edited by the visitor.' : 'Amounts entered by the visitor in this browser.'),
      detail('Why', 'Compare commitments with available funds and assess how changes affect the monthly balance.'),
      detail('How', 'Add distinct amounts in integer paise, subtract outflows from funds, and calculate ratios only with a positive denominator.'),
      section('Complete input register'),
      ...result.register.map((field): Content => ({
        unbreakable: true, margin: [0, 0, 0, 5],
        stack: [
          { text: field.label, bold: true },
          `INR · ${field.required ? 'Required' : 'Optional'} · ${field.amount === null ? 'Unavailable' : field.amount === 0 ? 'Zero: ₹0' : 'Provided: ' + money(field.amount)} · ${report.example ? (field.amount === field.example * 100 ? 'Example' : 'Edited example') : 'Self-reported'}`,
          { text: field.help, style: 'note' },
        ],
      })),
      section('Your Money Health Analysis'),
      detail('Monthly money received', money(result.funds)),
      detail('Total monthly expenses including EMI', money(result.outflow)),
      detail(result.balance < 0 ? 'Monthly shortfall' : 'Money remaining', money(Math.abs(result.balance))),
      detail('Balance as a share of funds', analysis.monthlyPercent === null ? 'Unavailable because no positive funds were entered.' : analysis.monthlyPercent.toFixed(2) + '%'),
      analysis.cashFlow,
      detail('Spending pressure', analysis.pressure === null ? 'Unavailable' : `${money(result.outflow)} ÷ ${money(result.funds)} = ${analysis.pressure.toFixed(2)}%`),
      detail('Emergency savings coverage', analysis.coverageText),
      detail('Debt payment pressure', !result.debt ? 'No monthly EMI entered.' : result.debtRatio === null ? 'Unavailable' : result.debtRatio.toFixed(2) + '%'),
      detail('Savings goal feasibility', analysis.goalText),
      ...(analysis.missing.length ? [detail('Not provided', analysis.missing.join(', ') + '. Missing amounts are excluded.' + (analysis.blankEssential.length ? ' Coverage may be overstated.' : ''))] : []),
      analysisMethod,
      section('Financial summary and calculations'),
      { columns: [{ stack: metricBlocks.slice(0, 5) }, { stack: metricBlocks.slice(5) }], columnGap: 20 },
      section('Financial charts'),
      chartBlock({ title: 'Where your money goes', rows: analysis.allocation }),
      ...analysisCharts(result, report.profileIndex).flatMap(chart => [chartBlock(chart), { text: chart.insight, style: 'note' }]),
      ...(report.hasScenario ? [section('What-If Planner'),
      ...report.scenarioNotes.map(note => detail('Assumption', note)),
      detail('Balance difference', `${money(scenario.balance - result.balance)} = funds change ${money(scenario.funds - result.funds)} − spending change ${money(scenario.expenses - result.expenses)} − debt change ${money(scenario.debt - result.debt)}.`),
      { columns: [revised.slice(0, 5), revised.slice(5)].map((group, column) => ({
        stack: group.map(([label, value], index) => detail(label, `Baseline ${baseline[column * 5 + index][1]} / Scenario ${value}`)),
      })), columnGap: 20 },

      chartBlock(charts(result, scenario)[3]),
      ...(report.goalRows.length ? [chartBlock({ title: 'Purchase savings goal', rows: report.goalRows }), detail('Projection', report.goalExplanation)] : []),
      ] : []),
      section('What could you improve?'),
      ...(analysis.suggestions.length ? [] : ['Review the entered amounts before choosing a next step.']),
      ...analysis.suggestions.map(item => ({ text: item.text, margin: [0, 0, 0, 5] as [number, number, number, number] })),
      section('Assumptions, privacy and limitations'),
      detail('Scope', 'One reported or illustrative month. Missing optional amounts contribute zero to sums and remain unavailable in the register. Ratios display to two decimal places.'),
      detail('Privacy', 'The browser generates this report using active tab state. No personal identity is required. Keep the downloaded file private if it contains personal numbers.'),
      detail('Limitations', 'For education and planning. No verified credit score, lending decision or financial guarantee. CreditAI research dashboards use historical research data.'),
      section('Explore CreditAI'),
      { text: `${link.label} · ${link.url}`, link: link.url, color: '#176445', decoration: 'underline' },
    ],
  }
}

export async function downloadMoneyHealthPdf(report: Report) {
  const [{ default: pdfMake }, { default: fonts }] = await Promise.all([
    import('pdfmake/build/pdfmake'), import('pdfmake/build/vfs_fonts'),
  ])

  const blob = await new Promise<Blob>((resolve, reject) => {
    const generator = pdfMake.createPdf(reportDefinition(report), undefined, undefined, fonts)
    generator.getBuffer((buffer) => {
      try {
        resolve(new Blob([new Uint8Array(buffer)], { type: 'application/pdf' }))
      } catch (error) {
        reject(error)
      }
    })
  })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'CreditAI-My-Money-Health.pdf'
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 30_000)
}
