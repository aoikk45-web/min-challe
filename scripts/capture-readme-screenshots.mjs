import { chromium } from 'playwright'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(__dirname, '..')
const outDir = path.join(root, 'docs', 'images')
const baseUrl = 'http://127.0.0.1:48221'

const viewport = { width: 430, height: 932 }

async function waitForApp(page) {
  await page.goto(baseUrl, { waitUntil: 'load' })
  await page.waitForSelector('header h1', { timeout: 15000 })
  await page.waitForFunction(
    () => !document.body.textContent?.includes('よみこみちゅう'),
    { timeout: 15000 },
  )
  await page.waitForTimeout(500)
}

async function main() {
  await mkdir(outDir, { recursive: true })

  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport })

  // 1. Child home
  await waitForApp(page)
  await page.screenshot({ path: path.join(outDir, 'home-child.png'), fullPage: false })

  // 2. Drill page (child)
  await page.goto(`${baseUrl}/drill`, { waitUntil: 'load' })
  await page.waitForSelector('text=さんすう', { timeout: 15000 })
  await page.waitForTimeout(500)
  await page.screenshot({ path: path.join(outDir, 'drill-child.png'), fullPage: false })

  // 3. Parent plan page (switch role in SPA, then navigate via bottom nav)
  await page.goto(baseUrl, { waitUntil: 'load' })
  await waitForApp(page)
  await page.getByRole('button', { name: 'おうちの人' }).click()
  await page.getByRole('link', { name: 'けいかく', exact: true }).click()
  await page.waitForSelector('text=下からついかできるよ', { timeout: 15000 })
  await page.waitForTimeout(500)
  await page.screenshot({ path: path.join(outDir, 'plan-parent.png'), fullPage: false })

  await browser.close()
  console.log('Saved screenshots to', outDir)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
