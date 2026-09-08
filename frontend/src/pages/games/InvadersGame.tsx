import { useEffect, useRef, useState } from 'react'
import { claimGameClear } from '../../api'
import { notifyPointsUpdated } from '../../pointsRefresh'

type Status = 'ready' | 'playing' | 'won' | 'lost'

type Invader = { x: number; y: number; alive: boolean }

const W = 360
const H = 480
const COLS = 6
const ROWS = 3

export default function InvadersGame({ onBack }: { onBack: () => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [status, setStatus] = useState<Status>('ready')
  const [pointsEarned, setPointsEarned] = useState<number | null>(null)
  const awardedRef = useRef(false)

  const stateRef = useRef({
    status: 'ready' as Status,
    playerX: W / 2,
    bullets: [] as { x: number; y: number }[],
    enemyBullets: [] as { x: number; y: number }[],
    invaders: [] as Invader[],
    dir: 1,
    tick: 0,
    moveEvery: 28,
    shootCd: 0,
    left: false,
    right: false,
    fire: false,
  })

  function buildInvaders(): Invader[] {
    const list: Invader[] = []
    for (let r = 0; r < ROWS; r++) {
      for (let c = 0; c < COLS; c++) {
        list.push({ x: 40 + c * 48, y: 48 + r * 40, alive: true })
      }
    }
    return list
  }

  function reset() {
    awardedRef.current = false
    setPointsEarned(null)
    const s = stateRef.current
    s.status = 'playing'
    s.playerX = W / 2
    s.bullets = []
    s.enemyBullets = []
    s.invaders = buildInvaders()
    s.dir = 1
    s.tick = 0
    s.moveEvery = 28
    s.shootCd = 0
    setStatus('playing')
  }

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const s = stateRef.current
      if (e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') {
        e.preventDefault()
        s.left = true
      } else if (e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D') {
        e.preventDefault()
        s.right = true
      } else if (e.key === ' ' || e.key === 'ArrowUp') {
        e.preventDefault()
        s.fire = true
      }
    }
    function onKeyUp(e: KeyboardEvent) {
      const s = stateRef.current
      if (e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') s.left = false
      else if (e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D') s.right = false
      else if (e.key === ' ' || e.key === 'ArrowUp') s.fire = false
    }
    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('keyup', onKeyUp)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('keyup', onKeyUp)
    }
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let raf = 0
    let alive = true

    function draw() {
      const s = stateRef.current
      ctx!.fillStyle = '#1a3344'
      ctx!.fillRect(0, 0, W, H)

      // player
      ctx!.fillStyle = '#ffd166'
      ctx!.fillRect(s.playerX - 22, H - 36, 44, 16)
      ctx!.fillRect(s.playerX - 6, H - 48, 12, 12)

      // invaders
      for (const inv of s.invaders) {
        if (!inv.alive) continue
        ctx!.fillStyle = '#2bb673'
        ctx!.fillRect(inv.x - 14, inv.y - 10, 28, 20)
        ctx!.fillStyle = '#fff8ee'
        ctx!.fillRect(inv.x - 8, inv.y - 4, 5, 5)
        ctx!.fillRect(inv.x + 3, inv.y - 4, 5, 5)
      }

      // bullets
      ctx!.fillStyle = '#ff7a45'
      for (const b of s.bullets) ctx!.fillRect(b.x - 2, b.y - 8, 4, 10)
      ctx!.fillStyle = '#4db6e2'
      for (const b of s.enemyBullets) ctx!.fillRect(b.x - 2, b.y, 4, 10)

      if (s.status === 'ready') {
        ctx!.fillStyle = 'rgba(0,0,0,0.35)'
        ctx!.fillRect(0, 0, W, H)
      }
    }

    function step() {
      if (!alive) return
      const s = stateRef.current
      if (s.status === 'playing') {
        s.tick += 1
        s.shootCd = Math.max(0, s.shootCd - 1)
        if (s.left) s.playerX = Math.max(24, s.playerX - 4)
        if (s.right) s.playerX = Math.min(W - 24, s.playerX + 4)
        if (s.fire && s.shootCd === 0) {
          s.bullets.push({ x: s.playerX, y: H - 50 })
          s.shootCd = 14
        }

        // move bullets
        s.bullets = s.bullets
          .map((b) => ({ ...b, y: b.y - 8 }))
          .filter((b) => b.y > 0)
        s.enemyBullets = s.enemyBullets
          .map((b) => ({ ...b, y: b.y + 5 }))
          .filter((b) => b.y < H)

        // hit invaders
        for (const b of s.bullets) {
          for (const inv of s.invaders) {
            if (!inv.alive) continue
            if (Math.abs(b.x - inv.x) < 16 && Math.abs(b.y - inv.y) < 14) {
              inv.alive = false
              b.y = -99
            }
          }
        }
        s.bullets = s.bullets.filter((b) => b.y > 0)

        // enemy move
        if (s.tick % s.moveEvery === 0) {
          const live = s.invaders.filter((i) => i.alive)
          const minX = Math.min(...live.map((i) => i.x), W)
          const maxX = Math.max(...live.map((i) => i.x), 0)
          let drop = false
          if (s.dir > 0 && maxX > W - 28) {
            s.dir = -1
            drop = true
          } else if (s.dir < 0 && minX < 28) {
            s.dir = 1
            drop = true
          }
          for (const inv of live) {
            if (drop) inv.y += 18
            else inv.x += s.dir * 12
          }
          if (s.moveEvery > 12) s.moveEvery -= 1
        }

        // enemy shoot
        if (s.tick % 45 === 0) {
          const live = s.invaders.filter((i) => i.alive)
          if (live.length) {
            const shooter = live[Math.floor(Math.random() * live.length)]
            s.enemyBullets.push({ x: shooter.x, y: shooter.y + 12 })
          }
        }

        // player hit
        for (const b of s.enemyBullets) {
          if (Math.abs(b.x - s.playerX) < 22 && b.y > H - 48 && b.y < H - 16) {
            s.status = 'lost'
            setStatus('lost')
          }
        }
        if (s.invaders.some((i) => i.alive && i.y > H - 70)) {
          s.status = 'lost'
          setStatus('lost')
        }

        if (s.invaders.every((i) => !i.alive)) {
          s.status = 'won'
          setStatus('won')
        }
      }

      draw()
      raf = requestAnimationFrame(step)
    }

    raf = requestAnimationFrame(step)
    return () => {
      alive = false
      cancelAnimationFrame(raf)
    }
  }, [])

  useEffect(() => {
    if (status !== 'won' || awardedRef.current) return
    awardedRef.current = true
    claimGameClear('invaders')
      .then((res) => {
        setPointsEarned(res.points_earned)
        if (res.points_earned > 0) notifyPointsUpdated()
      })
      .catch(() => setPointsEarned(0))
  }, [status])

  function move(dir: -1 | 1) {
    const s = stateRef.current
    if (s.status !== 'playing') return
    s.playerX = Math.max(24, Math.min(W - 24, s.playerX + dir * 28))
  }

  function shoot() {
    const s = stateRef.current
    if (s.status !== 'playing' || s.shootCd > 0) return
    s.bullets.push({ x: s.playerX, y: H - 50 })
    s.shootCd = 14
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <button type="button" onClick={onBack} className="rounded-full bg-cream px-4 py-2 text-sm font-black">
          もどる
        </button>
        <h2 className="text-lg font-black">インベーダー</h2>
        <span className="w-16" />
      </div>

      <div className="rounded-3xl bg-white p-4 shadow-sm">
        <p className="text-center text-sm font-bold text-ink/70">
          {status === 'ready' && 'てきを ぜんぶ たおそう'}
          {status === 'playing' && '←→キー／ボタンでうごく ・ スペースでうつ'}
          {status === 'won' && 'クリア！'}
          {status === 'lost' && 'ざんねん…'}
        </p>
        {status === 'won' && pointsEarned != null && pointsEarned > 0 && (
          <p className="mt-1 text-center text-sm font-black text-sun">+{pointsEarned}点</p>
        )}

        <canvas
          ref={canvasRef}
          width={W}
          height={H}
          className="mx-auto mt-3 block w-full max-w-sm rounded-2xl"
        />

        <div className="mt-3 grid grid-cols-3 gap-2">
          <button type="button" onClick={() => move(-1)} className="rounded-2xl bg-cream py-3 text-xl font-black">
            ←
          </button>
          <button type="button" onClick={shoot} className="rounded-2xl bg-sun py-3 font-black">
            うつ
          </button>
          <button type="button" onClick={() => move(1)} className="rounded-2xl bg-cream py-3 text-xl font-black">
            →
          </button>
        </div>

        {(status === 'ready' || status === 'won' || status === 'lost') && (
          <div className="mt-3 flex justify-center">
            <button type="button" onClick={reset} className="rounded-full bg-sky px-6 py-3 font-black text-white">
              {status === 'ready' ? 'はじめる' : 'もういっかい'}
            </button>
          </div>
        )}
      </div>
    </section>
  )
}
