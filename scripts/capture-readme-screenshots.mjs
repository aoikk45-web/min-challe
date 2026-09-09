import { chromium } from 'playwright'
import { mkdir, unlink } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(__dirname, '..')
const outDir = path.join(root, 'docs', 'images')
const baseUrl = 'http://127.0.0.1:48221'

const viewport = { width: 430, height: 932 }

async function shot(page, name) {
  await page.waitForTimeout(450)
  await page.screenshot({ path: path.join(outDir, name), fullPage: false })
  console.log('  saved', name)
}

/** Skip unlock gate without knowing the household PIN (session flag only). */
async function markUnlocked(page) {
  await page.evaluate(() => sessionStorage.setItem('minchalle_unlocked', '1'))
}

async function waitReady(page) {
  await page.waitForSelector('header h1', { timeout: 20000 })
  await page.waitForFunction(
    () => {
      const t = document.body.textContent || ''
      return !t.includes('よみこみちゅう') && !t.includes('ちょっとまってね')
    },
    { timeout: 20000 },
  )
}

async function enterApp(page) {
  await page.goto(baseUrl, { waitUntil: 'load' })
  await markUnlocked(page)
  await page.reload({ waitUntil: 'load' })
  await waitReady(page)
}

async function switchToParent(page) {
  // Capture script only: accept any parent PIN so screenshots work on family DBs.
  await page.route('**/api/auth/verify-parent', async (route) => {
    await route.fulfill({ status: 204, body: '' })
  })
  await page.getByRole('button', { name: 'おうちの人' }).click()
  const pinField = page.getByLabel('4桁のPIN')
  if (await pinField.isVisible({ timeout: 3000 }).catch(() => false)) {
    await pinField.fill('0000')
    await page.getByRole('button', { name: 'OK' }).click()
  }
  await page.waitForTimeout(400)
}

async function main() {
  await mkdir(outDir, { recursive: true })
  await unlink(path.join(outDir, '_dbg-unlock.png')).catch(() => {})

  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport })

  console.log('Capturing README screenshots…')

  // 1. Unlock / PIN gate (real UI, before session unlock)
  await page.goto(baseUrl, { waitUntil: 'load' })
  await page.evaluate(() => sessionStorage.removeItem('minchalle_unlocked'))
  await page.reload({ waitUntil: 'load' })
  await page.waitForSelector('text=はいる', { timeout: 15000 }).catch(() => null)
  await page.waitForSelector('text=はじめる', { timeout: 2000 }).catch(() => null)
  if (
    (await page.getByLabel('起動PIN').isVisible().catch(() => false)) ||
    (await page.getByRole('button', { name: 'はじめる' }).isVisible().catch(() => false))
  ) {
    await shot(page, 'unlock-pin.png')
  }

  // Enter as child via session unlock (does not need the real PIN)
  await enterApp(page)
  await shot(page, 'home-child.png')

  await page.goto(`${baseUrl}/drill`, { waitUntil: 'load' })
  await markUnlocked(page)
  await waitReady(page)
  await page.waitForSelector('text=えいご', { timeout: 15000 })
  await shot(page, 'drill-child.png')

  await page.goto(`${baseUrl}/games`, { waitUntil: 'load' })
  await markUnlocked(page)
  await waitReady(page)
  await page.waitForSelector('text=ミニゲーム', { timeout: 15000 })
  await shot(page, 'games-child.png')

  await page.getByRole('button', { name: /カップゲーム/ }).click()
  await page.waitForSelector('text=カップゲーム', { timeout: 10000 })
  await shot(page, 'games-cups.png')

  await page.goto(`${baseUrl}/promises`, { waitUntil: 'load' })
  await markUnlocked(page)
  await waitReady(page)
  await page.waitForSelector('text=毎日のおやくそく', { timeout: 15000 })
  await shot(page, 'promises-child.png')

  await page.goto(`${baseUrl}/points`, { waitUntil: 'load' })
  await markUnlocked(page)
  await waitReady(page)
  await page.waitForSelector('text=ポイント', { timeout: 15000 })
  await shot(page, 'points-child.png')

  await page.goto(`${baseUrl}/album`, { waitUntil: 'load' })
  await markUnlocked(page)
  await waitReady(page)
  await page.waitForTimeout(500)
  await shot(page, 'album-child.png')

  // Parent mode
  await enterApp(page)
  await switchToParent(page)

  await page.getByRole('link', { name: 'けいかく', exact: true }).click()
  await page.waitForSelector('text=けいかくを追加', { timeout: 15000 })
  await shot(page, 'plan-parent.png')

  await page.getByRole('link', { name: 'ポイント', exact: true }).click()
  await page.waitForSelector('text=付与ルール', { timeout: 15000 })
  await shot(page, 'points-parent.png')

  await page.getByRole('link', { name: 'やくそく', exact: true }).click()
  await page.waitForSelector('text=毎日のおやくそく', { timeout: 15000 })
  await shot(page, 'promises-parent.png')

  await browser.close()
  console.log('Saved screenshots to', outDir)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
