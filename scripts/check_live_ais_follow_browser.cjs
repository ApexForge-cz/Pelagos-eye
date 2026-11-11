// TEST DATA only: intercept every API/socket and block external requests.
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require('@playwright/test')
const fixture = require('../test-fixtures/live-ais/v1-server-events.json')

const endpoint = new URL(process.argv[2] || 'http://localhost:5174')
assert(
  endpoint.protocol === 'http:' &&
    ['localhost', '127.0.0.1', '[::1]'].includes(endpoint.hostname) &&
    endpoint.port &&
    endpoint.pathname === '/' &&
    !endpoint.username &&
    !endpoint.password &&
    !endpoint.search &&
    !endpoint.hash,
  'Use an explicit loopback HTTP port without credentials, path or query',
)
assert.equal(fixture.fixture_label, 'TEST DATA')
const base = endpoint.origin
const output = path.join(__dirname, '../tmp')
fs.mkdirSync(output, { recursive: true })

async function check(browser, label, viewport) {
  const context = await browser.newContext({
    viewport,
    reducedMotion: 'reduce',
  })
  try {
    const page = await context.newPage()
    const errors = []
    page.on('pageerror', (error) => errors.push(error.message))
    const now = new Date().toISOString()
    const boxes = []
    await context.route('**/*', (route) => {
      const url = new URL(route.request().url())
      if (url.origin !== base) return route.abort()
      if (url.pathname === '/ports') boxes.push(url.searchParams)
      if (/^\/(ports|earthquakes|ocean|system|data)(\/|$)/.test(url.pathname)) {
        return route.fulfill({
          status: 503,
          contentType: 'application/problem+json',
          body: JSON.stringify({ title: 'TEST DATA unavailable' }),
        })
      }
      return route.continue()
    })

    let socket
    let sequence = 1
    const snapshot = structuredClone(fixture.events[0])
    const status = structuredClone(fixture.events[1])
    snapshot.emitted_at = status.emitted_at = now
    snapshot.coverage.effective_at = status.coverage.effective_at = now
    snapshot.positions[0].observed_at = now
    snapshot.positions[0].provenance.ingested_at = now
    snapshot.positions[0].provenance.normalized_at = now
    status.last_observation_at = now
    snapshot.positions.push({
      ...structuredClone(snapshot.positions[0]),
      observation_id: 'TEST-DATA-second-position',
      mmsi: '999000002',
      longitude: -73.5,
    })
    await page.routeWebSocket('**/live-ais/ws', (ws) => {
      socket = ws
      ws.send(JSON.stringify(snapshot))
      ws.send(JSON.stringify(status))
    })

    await page.goto(base)
    await page.getByRole('button', { name: /MMSI 999000001/ }).click()
    const locate = page.getByRole('button', { name: '定位船舶', exact: true })
    await locate.click()
    await page.waitForTimeout(500)
    const matchesCenter = (longitude) =>
      boxes.some(
        (box) =>
          Math.abs(
            (Number(box.get('min_longitude')) + Number(box.get('max_longitude'))) / 2 - longitude,
          ) < 0.001,
      )
    assert(matchesCenter(-74.01), 'Locate must move the real map camera to the observation')

    // Select a different list item, then hit-test the first point at the map center.
    // This fails if MapLibre's worker/GeoJSON layer never renders, even if controls work.
    await page.getByRole('button', { name: /MMSI 999000002/ }).click()
    const canvas = page.getByLabel('OceanScope 交互式海事地图', {
      exact: true,
    })
    await canvas.scrollIntoViewIfNeeded()
    await page.waitForTimeout(500)
    const box = await canvas.boundingBox()
    assert(box)
    await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2)
    await page.getByRole('heading', { name: 'MMSI 999000001', exact: true }).waitFor()

    const follow = () => page.getByRole('button', { name: '跟随船舶', exact: true })
    await follow().click()
    socket.send(
      JSON.stringify({
        ...fixture.events[2],
        sequence: ++sequence,
        emitted_at: now,
        position: {
          ...snapshot.positions[0],
          longitude: -73.99,
          latitude: 40.71,
        },
      }),
    )
    await page.waitForTimeout(500)
    assert(matchesCenter(-73.99), 'Follow must move with the current observation')
    await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.6)
    await page.mouse.down()
    await page.mouse.move(box.x + box.width * 0.65, box.y + box.height * 0.65, {
      steps: 8,
    })
    await page.mouse.up()
    await follow().waitFor()
    await follow().focus()
    await page.keyboard.press('Enter')
    await page.getByRole('button', { name: '停止跟随', exact: true }).waitFor()
    await page.evaluate(() => {
      const banner = document.createElement('div')
      banner.textContent = 'TEST DATA · isolated browser acceptance · no provider connection'
      banner.style.cssText =
        'position:fixed;top:0;left:0;background:#fff;color:#111;z-index:99999;padding:4px;font:12px sans-serif'
      document.body.append(banner)
    })
    await page.screenshot({
      path: path.join(output, `follow-${endpoint.port}-${label}-TEST-DATA.png`),
    })

    socket.send(
      JSON.stringify({
        ...fixture.events[3],
        sequence: ++sequence,
        emitted_at: now,
      }),
    )
    await locate.waitFor({ state: 'hidden' })
    socket.send(JSON.stringify({ ...snapshot, sequence: ++sequence }))
    socket.send(JSON.stringify({ ...status, sequence: ++sequence }))
    await follow().waitFor()
    await follow().click()
    // Change only Date: mocking the frame clock would invalidate WebGL acceptance.
    await page.clock.setFixedTime(new Date(Date.parse(now) + 5 * 60_000 + 15_000))
    await locate.waitFor({ state: 'hidden' })
    assert.deepEqual(errors, [], 'No unhandled browser exceptions')
    console.log(
      `PASS: ${label}, actual point hit-test, locate/update/manual pause, keyboard follow, gap reset, silent expiry, reduced motion; TEST DATA only`,
    )
  } finally {
    await context.close()
  }
}

;(async () => {
  const browser = await chromium.launch({ headless: true })
  try {
    await check(browser, 'desktop', { width: 1440, height: 1000 })
    await check(browser, 'mobile', { width: 390, height: 844 })
  } finally {
    await browser.close()
  }
})().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
