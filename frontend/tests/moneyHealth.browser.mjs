// Run against the connected production build and a local Chromium debugging port.
import assert from 'node:assert/strict'
import { mkdir, readFile, rename, writeFile } from 'node:fs/promises'

const app = process.env.MH_APP ?? 'http://localhost:8765'
const debugging = process.env.MH_DEBUG ?? 'http://localhost:9222'
const tab = await fetch(debugging + '/json/new?about:blank', { method: 'PUT' }).then(r => r.json())
async function connect(url) {
  const socket = new WebSocket(url)
  await new Promise((resolve, reject) => {
    socket.addEventListener('open', resolve, { once: true })
    socket.addEventListener('error', reject, { once: true })
  })
  let sequence = 0
  const pending = new Map()
  socket.onmessage = event => {
    const message = JSON.parse(event.data)
    const callback = pending.get(message.id)
    if (callback) { pending.delete(message.id); callback(message) }
  }
  const call = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
    const id = ++sequence
    pending.set(id, message => message.error ? reject(new Error(message.error.message)) : resolve(message.result))
    socket.send(JSON.stringify({ id, method, params, sessionId }))
  })
  return { socket, call }
}
const { socket, call } = await connect(tab.webSocketDebuggerUrl)
const evaluate = async expression => {
  const response = await call('Runtime.evaluate', { expression, returnByValue: true })
  if (response.exceptionDetails) throw Error(response.exceptionDetails.text)
  return response.result.value
}
const output = new URL('../build/mh-verification-' + Date.now() + '/', import.meta.url)
await mkdir(output, { recursive: true })
const delay = () => new Promise(resolve => setTimeout(resolve, 100))
const ready = async selector => {
  for (let attempt = 0; attempt < 100; attempt++) {
    if (await evaluate(`Boolean(document.querySelector(${JSON.stringify(selector)}))`)) return
    await delay()
  }
  throw Error('Missing ' + selector)
}
const click = label => evaluate(`[...document.querySelectorAll('button')].find(el => el.textContent.trim() === ${JSON.stringify(label)}).click()`)
try {
  let readyResponse
  for (let attempt = 0; attempt < 150 && !readyResponse?.ok; attempt++) {
    readyResponse = await fetch(app + '/money-health').catch(() => null)
    if (!readyResponse?.ok) await delay()
  }
  assert(readyResponse?.ok, 'Connected app did not become ready')
  const response = await fetch(app + '/v1/score', {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      schema_version: '1.0', observation_start: '2025-01-01', prediction_date: '2025-02-01',
      request_id: 'mh-rehearsal-synthetic', transactions: [
        { transaction_id: 'synthetic-credit', date: '2025-01-15', transaction_type: 'credit', amount: 45000, category: 'salary' },
      ],
    }),
  })
  assert.equal(response.status, 200)
  const score = await response.json()
  assert.deepEqual([score.score_status, score.score_type, score.default_probability, score.validated_risk_estimate, score.model_version],
    ['not_validated', 'none', null, false, null])
  await call('Page.navigate', { url: app + '/money-health' })
  await ready('.mh')
  for (const width of [320, 375, 390, 430, 1366, 1440, 1920]) {
    await call('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false })
    assert(await evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Overflow at ' + width)
  }
  const outputPath = (await import('node:url')).fileURLToPath(output)
  await call('Page.setDownloadBehavior', { behavior: 'allow', downloadPath: outputPath })
  const download = async name => {
    await click('Download PDF')
    const source = new URL('CreditAI-My-Money-Health.pdf', output)
    for (let attempt = 0; attempt < 150; attempt++) {
      const bytes = await readFile(source).catch(() => null)
      if (bytes?.length && bytes.subarray(-16).toString().includes("%%EOF")) {
        assert.equal(bytes.subarray(0, 5).toString(), '%PDF-')
        const pageCount = [...bytes.toString('latin1').matchAll(/\/Type\s*\/Page\b/g)].length
        assert(pageCount > 1)
        await rename(source, new URL(name + '.pdf', output))
        console.log(name + ': ' + pageCount + ' pages, ' + bytes.length + ' bytes')
        return
      }
      assert(!(await evaluate('document.body.innerText.includes("PDF download could not")')), 'Download rejected')
      await delay()
    }
    throw Error('PDF did not download')
  }
  const fill = (id, value, byLabel = false) => evaluate(`{
    const input = ${byLabel} ? [...document.querySelectorAll("label")].find(label => label.textContent.includes(${JSON.stringify(id)})).querySelector("input") : document.getElementById(${JSON.stringify(id)})
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, ${JSON.stringify(value)})
    input.dispatchEvent(new Event('input', { bubbles: true }))
  }`)
  await click('Student')
  assert(await evaluate('[...document.querySelectorAll("input")].every(input => input.value === "")'))
  for (const [profile, balance] of [
    ['Student', '₹1,200'], ['Working Professional', '₹14,000'],
    ['Freelancer / Self-Employed', '₹15,000'], ['Other / Not Currently Earning', '₹800'],
  ]) {
    await click(profile)
    await click('Calculate Sample')
    await ready('.mh-metric')
    assert(await evaluate(`document.querySelector('[aria-label="Financial dashboard"]').textContent.includes(${JSON.stringify(balance)})`))
    assert.equal(await evaluate('document.querySelectorAll(".mh-chart svg").length > 0'), true)
    await download('sample-' + profile.split(' ')[0])
  }
  const manual = [
    ['Student', { primary: '5000.29', food: '1500', transport: '600', education: '1000', personal: '700', savings: '2500' }, '₹1,200.29'],
    ['Working Professional', { primary: '50000', housing: '14000', food: '8000', transport: '3000', personal: '3000', debt: '8000', savings: '75000' }, '₹14,000'],
    ['Freelancer / Self-Employed', { primary: '40000', low: '28000', personal: '25000', savings: '60000' }, '₹15,000'],
    ['Other / Not Currently Earning', { primary: '0', essential: '3.25', discretionary: '0', savings: '0' }, '-₹3.25'],
  ]
  for (const [profile, fields, balance] of manual) {
    await click(profile)
    await click('Use My Own Numbers')
    for (const [id, amount] of Object.entries(fields)) await fill(id, amount)
    await click('Calculate my money health')
    await ready('.mh-metric')
    assert(await evaluate(`document.querySelector('[aria-label="Financial dashboard"]').textContent.includes(${JSON.stringify(balance)})`))
    assert(await evaluate('document.body.innerText.includes("SELF-REPORTED")'))
    for (const width of [320, 375, 390, 430]) {
      await call('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false })
      assert(await evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Dashboard overflow at ' + width)
    }
    if (profile === 'Working Professional') {
      await evaluate(`{
        const slider = document.querySelector('input[type=range]')
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(slider, '6000')
        slider.dispatchEvent(new Event('change', { bubbles: true }))
      }`)
      assert(await evaluate('document.body.innerText.includes("Scenario ₹8,000")'))
    }
    if (profile === 'Student') {
      await fill('Purchase target', '1500', true)
      await fill('Savings explicitly allocated', '500', true)
      await fill('Planned monthly contribution', '250', true)
      assert(await evaluate('document.body.innerText.includes("4 whole months")'))
    }
    await download('personal-' + profile.split(' ')[0])
    await click('Clear All')
    assert.equal(await evaluate('document.querySelectorAll("input").length'), 0)
  }
  await click('Freelancer / Self-Employed')
  await click('Calculate Sample')
  await click('Use lower-income estimate')
  assert(await evaluate('document.body.innerText.includes("Scenario ₹3,000")'))
  await evaluate('window.print = () => { window.printRequested = true }')
  await click('Print or save detailed PDF')
  assert.equal(await evaluate('window.printRequested'), true)
  assert.deepEqual(await evaluate('[localStorage.length, sessionStorage.length, location.search]'), [0, 0, ''])
  const browser = await fetch(debugging + '/json/version').then(response => response.json())
  const isolated = await connect(browser.webSocketDebuggerUrl)
  try {
    const { browserContextId } = await isolated.call('Target.createBrowserContext')
    const { targetId } = await isolated.call('Target.createTarget', { url: app + '/money-health', browserContextId })
    const { sessionId } = await isolated.call('Target.attachToTarget', { targetId, flatten: true })
    let independent
    for (let attempt = 0; attempt < 100 && !independent; attempt++) {
      const check = await isolated.call('Runtime.evaluate', {
        expression: 'document.querySelector(".mh") && [document.querySelectorAll("input").length, localStorage.length, sessionStorage.length]',
        returnByValue: true,
      }, sessionId)
      independent = check.result.value
      if (!independent) await delay()
    }
    assert.deepEqual(independent, [0, 0, 0])
    await isolated.call('Target.disposeBrowserContext', { browserContextId })
  } finally {
    isolated.socket.close()
  }
  const pdf = await call('Page.printToPDF', { printBackground: true, preferCSSPageSize: true })
  const bytes = Buffer.from(pdf.data, 'base64')
  assert.equal(bytes.subarray(0, 5).toString(), '%PDF-')
  const pageCount = [...bytes.toString('latin1').matchAll(/\/Type\s*\/Page\b/g)].length
  assert(pageCount > 1)
  await writeFile(new URL('print-fallback.pdf', output), bytes)
  console.log('Generated PDF with ' + pageCount + ' pages and ' + bytes.length + ' bytes')
  await call('Page.reload')
  await ready('.mh')
  assert.equal(await evaluate('document.querySelectorAll("input").length'), 0)
  await evaluate('document.querySelector(".mh footer a").click()')
  await ready('.side-nav')
  for (const label of ['Borrower prediction', 'Batch evaluation']) {
    await evaluate(`[...document.querySelectorAll('.side-nav button')].find(button => button.textContent.includes(${JSON.stringify(label)})).click()`)
    assert(await evaluate(`document.querySelector('.crumb').textContent.includes(${JSON.stringify(label)})`))
  }
  await evaluate("[...document.querySelectorAll('.side-nav button')].find(button => button.textContent.includes('Agentic Commerce')).click()")
  assert(await evaluate("document.querySelector('.crumb').textContent.includes('Agentic Commerce')"))
  console.log('Browser checks passed for route, refresh, samples, lower-income scenario, navigation and seven widths.')
} finally {
  socket.close()
}
