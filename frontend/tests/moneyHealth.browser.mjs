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
const reload = async () => {
  await evaluate('window.__creditaiRehearsalPage = true')
  await call('Page.reload', { ignoreCache: true })
  for (let attempt = 0; attempt < 100; attempt++) {
    const ready = await evaluate('!window.__creditaiRehearsalPage && Boolean(document.querySelector(".mh"))').catch(() => false)
    if (ready) return
    await delay()
  }
  throw Error('Reload did not reach a fresh Money Health page')
}
const click = label => evaluate(`[...document.querySelectorAll('button')].find(el => (el.getAttribute("aria-label") || el.textContent.trim()) === ${JSON.stringify(label)}).click()`)
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
  for (const width of [320, 375, 390, 430, 768, 1366, 1440, 1920]) {
    await call('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false })
    assert(await evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth'), 'Overflow at ' + width)
  }
  const screenshot = async (name, selector) => {
    if (selector) await evaluate(`document.querySelector(${JSON.stringify(selector)}).scrollIntoView({block: "start", behavior: "instant"})`)
    for (let frame = 0; frame < 3; frame++) await delay()
    const shot = await call('Page.captureScreenshot', { format: 'png' })
    await writeFile(new URL(name + '.png', output), Buffer.from(shot.data, 'base64'))
  }
  await call('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false })
  await screenshot('profile-cards-and-sidebar')
  for (const width of [320, 375, 390, 430, 768, 1366, 1920]) {
    await call('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false })
    await screenshot('profiles-' + width, '.mh-choice-grid')
  }
  await call('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false })
  const outputPath =(await import('node:url')).fileURLToPath(output)
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
  assert(!(await evaluate('document.querySelector("#education").required')))
  await click('Calculate my money health')
  assert(await evaluate('document.querySelector("#primary").validity.valueMissing && !document.querySelector(".mh-analysis")'))
  await evaluate('document.querySelector("fieldset").scrollIntoView()')
  await screenshot('grouped-inputs', 'fieldset')
  assert(await evaluate('[...document.querySelectorAll("input")].every(input => input.value === "")'))
  for (const [profile, balance] of [
    ['Student', '₹1,200'], ['Working Professional', '₹14,000'],
    ['Freelancer / Self-Employed', '₹15,000'], ['Other / Not Currently Earning', '₹800'],
  ]) {
    await click(profile)
    await click('Load Example Input')
    await click('Calculate my money health')
    await ready('.mh-metric')
    assert(await evaluate(`document.querySelector('[aria-label="Financial dashboard"]').textContent.includes(${JSON.stringify(balance)})`))
    assert(await evaluate('document.activeElement.id === "money-health-results"'))
    assert(await evaluate('document.querySelector(".mh-analysis-charts").getBoundingClientRect().top < innerHeight'))
    assert.equal(await evaluate('document.querySelectorAll(".mh-analysis-charts figure").length'), 4)
    assert(!await evaluate('document.body.innerText.includes("Baseline vs what-if")'))
    await screenshot('analysis-' + profile.split(' ')[0])
    if (profile === 'Student') {
      assert(await evaluate('document.querySelector(".mh-analysis").innerText.includes("76.00%") && document.querySelector(".mh-snapshot").innerText.includes("24.00%")'))
      await screenshot('analysis-charts', '.mh-analysis-charts')
      await screenshot('analysis-recommendations', '#money-health-recommendations')
      await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false})
      await screenshot('analysis-mobile', '.mh-results-hero')
      await call('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false})
    }
    const presetNames = await evaluate('[...document.querySelectorAll(".mh-choice-grid button")].filter(button => button.textContent.includes("Example change")).map(button => button.querySelector("strong").textContent)')
    assert.equal(presetNames.length, profile.startsWith('Other') ? 3 : 4)
    for (const name of presetNames) {
      await evaluate(`[...document.querySelectorAll('.mh-choice-grid button')].find(button => button.querySelector('strong')?.textContent === ${JSON.stringify(name)}).click()`)
      assert(await evaluate('document.body.innerText.includes("Applied:") && !document.querySelector(".mh [role=alert]")'))
      if (profile === 'Student' && name.startsWith('Spend')) {
        assert(await evaluate('document.body.innerText.includes("Scenario ₹1,500")'))
        await evaluate('document.querySelector(".mh-custom").scrollIntoView({block:"center"})')
        await screenshot('what-if-presets', '#money-health-what-if')
        await screenshot('analysis-what-if-comparison', '.mh-comparison')
      }
    }
    await click('Reset scenario')
    if (profile === 'Student') {
      await click('Apply this What-If')
      assert(await evaluate('document.body.innerText.includes("Scenario ₹1,500")'))
    }
    await download('sample-' + profile.split(' ')[0])
    await click('Turn an improvement into a Money Challenge')
    await ready('[aria-label="Money Passport"] form')
    assert(await evaluate(`document.querySelector('[aria-label="Money Passport"] form').innerText.includes('Suggested from your analysis')`))

    if (profile === 'Student') assert.equal(await evaluate('document.querySelector("[name=baseline]").value'), '700.00')
    await click('Back to My Money Health')
  }
  const manual = [
    ['Student', { primary: '5000.29', food: '2500', transport: '600', personal: '700', savings: '2500' }, '₹1,200.29'],
    ['Working Professional', { primary: '50000', food: '22000', transport: '3000', personal: '3000', debt: '8000', savings: '75000' }, '₹14,000'],
    ['Freelancer / Self-Employed', { primary: '40000', low: '28000', personal: '25000', savings: '60000' }, '₹15,000'],
    ['Other / Not Currently Earning', { primary: '0', essential: '3.25', discretionary: '0', savings: '0' }, '₹3.25'],
  ]
  for (const [profile, fields, balance] of manual) {
    await click(profile)
    await click('Use My Own Numbers')
    for (const [id, amount] of Object.entries(fields)) await fill(id, amount)
    await click('Calculate my money health')
    await ready('.mh-metric')
    assert(await evaluate(`document.querySelector('[aria-label="Financial dashboard"]').textContent.includes(${JSON.stringify(balance)})`))
    assert(await evaluate('document.body.innerText.includes("SELF-REPORTED")'))
    for (const width of [320, 375, 390, 430, 768]) {
      await call('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false })
      assert(await evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth'), 'Dashboard overflow at ' + width)
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
    assert.equal(await evaluate('[...document.querySelectorAll("input")].filter(input=>input.getClientRects().length).length'), 0)
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
        expression: 'document.querySelector(".mh") && [[...document.querySelectorAll("input")].filter(input=>input.getClientRects().length).length, localStorage.length, sessionStorage.length]',
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
  // Rehearse all three challenge types and the browser-local return journey.
  const passport = () => evaluate(`document.querySelector('[aria-label="Money Passport"]').innerText`)

  const setField = (name, value) => evaluate(`{
    const field = document.querySelector('[aria-label="Money Passport"] [name="' + ${JSON.stringify(name)} + '"]')
    field.value = ${JSON.stringify(value)}
  }`)
  const chooseKind = kind => click({ savings: 'Savings Goal', spending: 'Spending Reduction', emergency: 'Emergency Buffer' }[kind])
  socket.addEventListener('message', event => {
    if (JSON.parse(event.data).method === 'Page.javascriptDialogOpening') {
      void call('Page.handleJavaScriptDialog', { accept: true })
    }
  })
  await call('Page.enable')
  await reload()
  await ready('.mh')
  const challengeCases = [
    ['Student', 'savings', 'Student laptop', { target: '1000', planned: '100' }],
    ['Working Professional', 'spending', 'Professional food', { category: 'Food', baseline: '1000', target: '300', end: '2099-01-01' }],
    ['Freelancer / Self-Employed', 'emergency', 'Freelancer buffer', { essential: '1000', coverage: '2' }],
    ['Other / Not Currently Earning', 'savings', 'Other goal', { target: '500' }],
  ]
  for (const [profile, type, name, values] of challengeCases) {
    await click(profile)
    await click('Calculate Sample')
    await click((await evaluate('localStorage.length')) ? 'Continue My Money Challenge' : 'Start My Money Challenge')
    await click('New challenge')
    await chooseKind(type)
    await setField('name', name)
    for (const [field, value] of Object.entries(values)) await setField(field, value)
    await evaluate("document.querySelector('[name=context]').click()")
    if (profile === 'Student') await screenshot('challenge-creation', '[aria-label="Money Passport"] form')
    await click('Review plan')
    await click('Confirm challenge')
    assert((await passport()).includes(name))
    assert((await passport()).includes('EXAMPLE-BASED PLAN'))
    assert((await passport()).includes('No entries yet'))
    assert.equal(await evaluate('document.querySelector("progress").value'), 0)
    for (const width of [320, 375, 390, 430, 768]) {
      await call('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false })
      assert(await evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth'), 'Passport overflow at ' + width)
    }
    assert(await evaluate('[...document.querySelectorAll("button")].find(x => x.textContent === "Save Money Passport").disabled'))
    await evaluate('document.querySelector(\'[aria-label="Money Passport"] input[type=checkbox]\').click()')
    await evaluate('document.querySelector("#manage-passport > summary").click()')
    await click('Save Money Passport')
    assert((await passport()).includes('Passport saved on this browser'))
    await click('Back to My Money Health')
  }
  await reload()
  await ready('.mh')
  await click('Continue My Money Challenge')
  assert((await passport()).includes('Student laptop'))
  await click('Record Progress')
  await setField('amount', '300.25')
  await setField('note', 'Recorded contribution')
  await click('Add entry')
  assert((await passport()).includes('₹300.25'))
  assert((await passport()).includes('25% · ₹250 · Reached'))
  await click('Edit entry')
  await setField('amount', '550.50')
  await click('Save edit')
  assert((await passport()).includes('50% · ₹500 · Reached'))
  await evaluate('document.querySelector(".mh-passport-hero").scrollIntoView()')
  await screenshot('passport-progress', '.mh-passport-hero')
  await evaluate('document.querySelector(".mh-passport-actions a").click()')
  await screenshot('manage-passport', '#manage-passport')
  await click('Export Passport')
  await click('Download Money Passport PDF')
  const backupPath = new URL('CreditAI-Money-Passport.json', output)
  const reportPath = new URL('CreditAI-Money-Passport.pdf', output)
  let backup, passportPdf
  for (let attempt = 0; attempt < 150 && (!backup || !passportPdf); attempt++) {
    const raw = await readFile(backupPath, 'utf8').catch(() => '')
    if (raw.endsWith('}')) backup = JSON.parse(raw)
    const bytes = await readFile(reportPath).catch(() => null)
    if (bytes?.subarray(-16).toString().includes('%%EOF')) passportPdf = bytes
    if (!backup || !passportPdf) await delay()
  }
  assert.equal(backup?.entries[0]?.amount, 55050)
  assert.equal(passportPdf?.subarray(0, 5).toString(), '%PDF-')
  await click('Delete entry')
  assert((await passport()).includes('No entries yet'))
  await click('Delete My Passport')
  const root = await call('DOM.getDocument')
  const input = await call('DOM.querySelector', { nodeId: root.root.nodeId, selector: 'input[type=file]' })
  await call('DOM.setFileInputFiles', { nodeId: input.nodeId, files: [(await import('node:url')).fileURLToPath(backupPath)] })
  for (let attempt = 0; attempt < 100 && !(await passport()).includes('₹550.5'); attempt++) await delay()
  assert((await passport()).includes('₹550.5'))
  const passportBrowser = await fetch(debugging + '/json/version').then(response => response.json())
  const privateClient = await connect(passportBrowser.webSocketDebuggerUrl)
  try {
    const { browserContextId } = await privateClient.call('Target.createBrowserContext')
    const { targetId } = await privateClient.call('Target.createTarget', { url: app + '/money-health', browserContextId })
    const { sessionId } = await privateClient.call('Target.attachToTarget', { targetId, flatten: true })
    let fresh
    for (let attempt = 0; attempt < 100 && !fresh; attempt++) {
      const check = await privateClient.call('Runtime.evaluate', {
        expression: 'document.querySelector(".mh") && [localStorage.length, document.body.innerText.includes("Start My Money Challenge"), location.search]',
        returnByValue: true,
      }, sessionId)
      fresh = check.result.value
      if (!fresh) await delay()
    }
    assert.deepEqual(fresh, [0, true, ''])
    await privateClient.call('Target.disposeBrowserContext', { browserContextId })
  } finally {
    privateClient.socket.close()
  }
  await click('Clear All Data')
  assert.equal(await evaluate('localStorage.length'), 0)
  console.log('Passport checks passed: four profiles, three types, consent, refresh, milestones, edit/delete, backup restore, PDF, private context and responsive widths.')
  await reload()
  await ready('.mh')
  assert.equal(await evaluate('[...document.querySelectorAll("input")].filter(input=>input.getClientRects().length).length'), 0)
  await evaluate('document.querySelector(".mh footer a").click()')
  await ready('.crumb')
  for (const label of ['Borrower prediction', 'Batch evaluation']) {
    await evaluate(`[...document.querySelectorAll('.side-nav button')].find(button => button.textContent.includes(${JSON.stringify(label)})).click()`)
    assert(await evaluate(`document.querySelector('.crumb').textContent.includes(${JSON.stringify(label)})`))
  }
  await evaluate("[...document.querySelectorAll('.side-nav button')].find(button => button.textContent.includes('Agentic Commerce')).click()")
  assert(await evaluate("document.querySelector('.crumb').textContent.includes('Agentic Commerce')"))
  console.log('Browser checks passed for route, refresh, samples, lower-income scenario, navigation and eight widths.')
} finally {
  socket.close()
}
