import type { Content, TDocumentDefinitions } from 'pdfmake/interfaces'
import { money } from './moneyHealth'
import { progress, types } from './moneyChallenge'
import type { Passport } from './moneyChallenge'
import { applicationLink } from './moneyHealthPdf'

export function saveFile(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 30_000)
}

export function passportReport(passport: Passport, date: string, origin: string): TDocumentDefinitions {
  const result = progress(passport, date)
  const spending = passport.kind === 'spending'
  const link = applicationLink(origin)
  const heading = (text: string): Content => ({ text, style: 'heading', headlineLevel: 1 })
  const barMax = Math.max(result.limit, result.current, 1)
  const bar = (label: string, value: number): Content => ({
    unbreakable: true, margin: [0, 0, 0, 8],
    stack: [
      { columns: [label, { text: money(value), alignment: 'right' }] },
      { canvas: [
        { type: 'rect', x: 0, y: 3, w: 500, h: 7, color: '#e4eee8' },
        { type: 'rect', x: 0, y: 3, w: 500 * value / barMax, h: 7, color: '#18704e' },
      ] },
    ],
  })
  return {
    pageSize: 'A4', pageMargins: [44, 45, 44, 48],
    info: { title: 'CreditAI | Money Passport', author: 'CreditAI' },
    defaultStyle: { fontSize: 10, color: '#18352a', lineHeight: 1.12 },
    styles: {
      title: { fontSize: 27, bold: true, margin: [0, 0, 0, 8] },
      heading: { fontSize: 15, bold: true, color: '#16593f', margin: [0, 11, 0, 5] },
    },
    footer: (page, total) => ({
      margin: [44, 12, 44, 0], fontSize: 9,
      columns: ['CreditAI / Money Passport', { text: `Page ${page} of ${total}`, alignment: 'right' }],
    }),
    pageBreakBefore: (node, following) => node.headlineLevel === 1 && !following.length,
    content: [
      { text: 'CREDITAI / VISITOR PROGRESS REPORT', bold: true, color: '#18704e' },
      { text: 'Money Passport', style: 'title' },
      { text: passport.name, bold: true },
      `${types[passport.kind]} · Created ${passport.created} · Report date ${date}`,
      passport.example ? 'EXAMPLE-BASED PLAN' : 'VISITOR-ENTERED PLAN',
      heading('Original challenge plan'),
      passport.profile ? `Retained profile: ${passport.profile}` : 'Visitor profile not retained.',
      passport.snapshot ? `Retained monthly balance: ${money(passport.snapshot.balance)}.` : 'Initial financial snapshot not retained.',
      `Target ${spending ? 'reduction' : 'amount'}: ${money(passport.target)}.`,
      spending ? `${passport.category} · Baseline ${money(passport.baseline)} · Track through ${passport.end}, inclusive.`
        : `Starting allocation ${money(passport.start)} · Planned contribution ${money(passport.planned)} ${passport.frequency} · Target date ${passport.end || 'not specified'}.`,
      heading('Calculated progress and next steps'),
      `${result.status} · ${result.percentage.toFixed(2)}% of target · ${spending ? 'Above limit' : 'Remaining'}: ${money(result.remaining)}.`,
      spending ? `Limit = ${money(passport.baseline)} − ${money(passport.target)} = ${money(result.limit)}. Actual spending ${money(result.current)}. Baseline less actual ${money(result.comparison)}. Actual less limit ${money(result.targetDifference)}. This comparison does not represent money deposited or set aside. Milestones require a closed period and recorded activity.`
        : `Current balance = starting allocation ${money(passport.start)} + net recorded entries ${money(result.total)} = ${money(result.current)}. Remaining target is the positive difference between target and current balance.`,
      ...(result.coverage === null ? [] : [`Emergency coverage = ${money(result.current)} ÷ ${money(passport.essential)} = ${result.coverage.toFixed(2)} months, assuming essential expenses stay constant.`]),
      ...(result.eta ? [`Estimated completion: ${result.eta}, assuming planned contributions continue at the stated amount and frequency.`] : []),
      ...(result.required === null ? [] : [`Deadline projection: ${money(result.required)} per period over ${result.periods} remaining periods.`]),
      ...(result.feasible === null ? [] : [`Planned contributions ${result.feasible ? 'fit' : 'exceed'} the retained monthly balance using a 30-day month. The snapshot does not guarantee capacity.`]),
      spending ? 'Next step: record spending for the selected category and review the comparison after the period closes.'
        : result.remaining ? 'Next step: record actual contributions or withdrawals and review the remaining amount.' : 'Next step: review the balance after any future entries.',
      heading('Target versus recorded progress · INR'),
      bar(spending ? 'Spending limit' : 'Target balance', result.limit),
      bar(spending ? 'Recorded spending' : 'Current reported balance', result.current),
      heading('Planned milestones'),
      ...result.milestones.map(item => `${item.percent}% · ${money(item.threshold)} · ${item.achieved ? 'Reached' : 'Pending'}`),
      heading('Actual recorded timeline'),
      'Entries are self-reported. Running totals use recorded dates and the order of entries on the same date.',
      ...(result.timeline.length ? result.timeline.map(entry => ({
        text: `${entry.date} · ${entry.kind} · ${money(entry.amount)} · Running total ${money(entry.cumulative)}${entry.note ? ' · ' + entry.note : ''}`,
        margin: [0, 4, 0, 0] as [number, number, number, number],
      })) : ['No recorded entries.']),
      heading('Privacy and limitations'),
      'This report uses a visitor-entered plan, explicitly retained context if provided, and self-reported entries. Entries are not bank verified. Projections are estimates. CreditAI creates this report on this device. Protect downloaded reports and backups.',
      { unbreakable: true, stack: [heading('Explore CreditAI'),
      { text: `${link.label} · ${link.url}`, link: link.url, decoration: 'underline' }] },
    ],
  }
}
export async function downloadPassport(passport: Passport, date: string, origin: string) {
  const [{ default: pdfMake }, { default: fonts }] = await Promise.all([
    import('pdfmake/build/pdfmake'), import('pdfmake/build/vfs_fonts'),
  ])
  const pdf = pdfMake.createPdf(passportReport(passport, date, origin), undefined, undefined, fonts)
  pdf.getBlob(blob => saveFile(blob, 'CreditAI-Money-Passport.pdf'))
}
