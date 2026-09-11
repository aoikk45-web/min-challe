import { useEffect, useRef, useState } from 'react'
import { claimGameClear } from '../../api'
import { notifyPointsUpdated } from '../../pointsRefresh'

type Status = 'ready' | 'playing' | 'won' | 'lost'

type Kind =
  | 'hiiji_f'
  | 'hiiba_f'
  | 'hiiji_m'
  | 'hiiba_m'
  | 'oji_f'
  | 'oba_f'
  | 'oji_m'
  | 'oba_m'
  | 'papa'
  | 'mama'
  | 'yuuki'

type Ball = {
  id: number
  kind: Kind
  x: number
  y: number
  vx: number
  vy: number
  r: number
  settled: boolean
}

const W = 400
const H = 640
const FLOOR = H - 20
const WALL = 14
const DANGER_Y = 124
const DROP_Y = 62
const GRAVITY = 0.34
const REST = 0.18
const FRICTION = 0.988

/** 落とせるのはいちばん小さいひい世代だけ */
const DROP_KINDS: Kind[] = ['hiiji_f', 'hiiba_f', 'hiiji_m', 'hiiba_m']

/** ゆうきの直径 = 画面幅のちょうど 1/4。他世代も比例拡大。 */
const R_YUUKI = Math.round(W / 8)
const META: Record<
  Kind,
  { label: string; emoji: string; color: string; ring: string; r: number }
> = {
  // 落とす4種 — 色をはっきり分ける
  hiiji_f: {
    label: 'ひいじい・あお',
    emoji: '👴',
    color: '#3b82f6',
    ring: '#1e3a8a',
    r: Math.round(R_YUUKI * 0.42),
  },
  hiiba_f: {
    label: 'ひいばあ・みず',
    emoji: '👵',
    color: '#22d3ee',
    ring: '#0e7490',
    r: Math.round(R_YUUKI * 0.42),
  },
  hiiji_m: {
    label: 'ひいじい・あか',
    emoji: '👴',
    color: '#f43f5e',
    ring: '#9f1239',
    r: Math.round(R_YUUKI * 0.42),
  },
  hiiba_m: {
    label: 'ひいばあ・むらさき',
    emoji: '👵',
    color: '#c084fc',
    ring: '#6b21a8',
    r: Math.round(R_YUUKI * 0.42),
  },
  // ひいじい＋ひいばあ の4パターン結果
  oji_f: {
    label: 'じいじ・あお',
    emoji: '👴',
    color: '#1d4ed8',
    ring: '#172554',
    r: Math.round(R_YUUKI * 0.62),
  },
  oba_f: {
    label: 'ばあば・みどり',
    emoji: '👵',
    color: '#10b981',
    ring: '#065f46',
    r: Math.round(R_YUUKI * 0.62),
  },
  oji_m: {
    label: 'じいじ・あか',
    emoji: '👴',
    color: '#be123c',
    ring: '#4c0519',
    r: Math.round(R_YUUKI * 0.62),
  },
  oba_m: {
    label: 'ばあば・むらさき',
    emoji: '👵',
    color: '#7c3aed',
    ring: '#4c1d95',
    r: Math.round(R_YUUKI * 0.62),
  },
  papa: {
    label: 'パパ',
    emoji: '👨',
    color: '#f59e0b',
    ring: '#92400e',
    r: Math.round(R_YUUKI * 0.82),
  },
  mama: {
    label: 'ママ',
    emoji: '👩',
    color: '#ec4899',
    ring: '#9d174d',
    r: Math.round(R_YUUKI * 0.82),
  },
  yuuki: {
    label: 'ゆうき',
    emoji: '🧒',
    color: '#facc15',
    ring: '#a16207',
    r: R_YUUKI,
  },
}

function mergeResult(a: Kind, b: Kind): Kind | null {
  if (a === b) return null
  const set = new Set([a, b])

  // ひいじい＋ひいばあ（4パターン）→ じいじ／ばあば
  // あお＋みず → じいじ・あお
  if (set.has('hiiji_f') && set.has('hiiba_f')) return 'oji_f'
  // あお＋むらさき → ばあば・みどり
  if (set.has('hiiji_f') && set.has('hiiba_m')) return 'oba_f'
  // あか＋みず → じいじ・あか
  if (set.has('hiiji_m') && set.has('hiiba_f')) return 'oji_m'
  // あか＋むらさき → ばあば・むらさき
  if (set.has('hiiji_m') && set.has('hiiba_m')) return 'oba_m'

  // じいじ＋ばあば → パパ／ママ、パパ＋ママ → ゆうき
  if (set.has('oji_f') && set.has('oba_f')) return 'papa'
  if (set.has('oji_m') && set.has('oba_m')) return 'mama'
  if (set.has('papa') && set.has('mama')) return 'yuuki'
  return null
}

function randomDrop(): Kind {
  return DROP_KINDS[Math.floor(Math.random() * DROP_KINDS.length)]
}

let idSeq = 1

export default function FamilyMergeGame({ onBack }: { onBack: () => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [status, setStatus] = useState<Status>('ready')
  const [pointsEarned, setPointsEarned] = useState<number | null>(null)
  const [nextKind, setNextKind] = useState<Kind>(() => randomDrop())
  const awardedRef = useRef(false)
  const tryDropRef = useRef(() => {})

  const stateRef = useRef({
    status: 'ready' as Status,
    balls: [] as Ball[],
    aimX: W / 2,
    next: randomDrop() as Kind,
    dropping: false,
    mergeFlash: 0,
    dangerFrames: 0,
    pointerDown: false,
  })

  function hardReset(toPlaying: boolean) {
    awardedRef.current = false
    setPointsEarned(null)
    const n = randomDrop()
    setNextKind(n)
    const s = stateRef.current
    s.status = toPlaying ? 'playing' : 'ready'
    s.balls = []
    s.aimX = W / 2
    s.next = n
    s.dropping = false
    s.mergeFlash = 0
    s.dangerFrames = 0
    s.pointerDown = false
    setStatus(s.status)
  }

  function canDrop() {
    const s = stateRef.current
    if (s.status !== 'playing' || s.dropping) return false
    return s.balls.every((b) => Math.abs(b.vx) < 0.35 && Math.abs(b.vy) < 0.35)
  }

  function tryDrop() {
    const s = stateRef.current
    if (!canDrop()) return
    const kind = s.next
    const r = META[kind].r
    s.balls.push({
      id: idSeq++,
      kind,
      x: s.aimX,
      y: DROP_Y,
      vx: 0,
      vy: 0.8,
      r,
      settled: false,
    })
    s.dropping = true
    const n = randomDrop()
    s.next = n
    setNextKind(n)
  }
  tryDropRef.current = tryDrop

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const s = stateRef.current
      if (s.status !== 'playing') return
      if (e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') {
        e.preventDefault()
        s.aimX = Math.max(WALL + META[s.next].r, s.aimX - 16)
      } else if (e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D') {
        e.preventDefault()
        s.aimX = Math.min(W - WALL - META[s.next].r, s.aimX + 16)
      } else if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault()
        tryDropRef.current()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let raf = 0
    let alive = true

    function pointerX(clientX: number) {
      const rect = canvas!.getBoundingClientRect()
      const scale = W / rect.width
      return (clientX - rect.left) * scale
    }

    function onPointerDown(e: PointerEvent) {
      const s = stateRef.current
      if (s.status !== 'playing') return
      s.pointerDown = true
      const r = META[s.next].r
      s.aimX = Math.min(W - WALL - r, Math.max(WALL + r, pointerX(e.clientX)))
    }
    function onPointerMove(e: PointerEvent) {
      const s = stateRef.current
      if (s.status !== 'playing' || !s.pointerDown) return
      const r = META[s.next].r
      s.aimX = Math.min(W - WALL - r, Math.max(WALL + r, pointerX(e.clientX)))
    }
    function onPointerUp() {
      const s = stateRef.current
      if (!s.pointerDown) return
      s.pointerDown = false
      tryDropRef.current()
    }

    canvas.addEventListener('pointerdown', onPointerDown)
    window.addEventListener('pointermove', onPointerMove)
    window.addEventListener('pointerup', onPointerUp)

    function stepPhysics() {
      const s = stateRef.current
      if (s.status !== 'playing') return

      for (const b of s.balls) {
        b.vy += GRAVITY
        b.vx *= FRICTION
        b.x += b.vx
        b.y += b.vy

        if (b.x - b.r < WALL) {
          b.x = WALL + b.r
          b.vx = Math.abs(b.vx) * REST
        }
        if (b.x + b.r > W - WALL) {
          b.x = W - WALL - b.r
          b.vx = -Math.abs(b.vx) * REST
        }
        if (b.y + b.r > FLOOR) {
          b.y = FLOOR - b.r
          b.vy = -Math.abs(b.vy) * REST
          b.vx *= 0.9
          if (Math.abs(b.vy) < 0.4) b.vy = 0
        }
      }

      // collisions + merges
      for (let iter = 0; iter < 4; iter++) {
        for (let i = 0; i < s.balls.length; i++) {
          for (let j = i + 1; j < s.balls.length; j++) {
            const a = s.balls[i]
            const b = s.balls[j]
            if (!a || !b) continue
            const dx = b.x - a.x
            const dy = b.y - a.y
            const dist = Math.hypot(dx, dy) || 0.001
            const minDist = a.r + b.r
            if (dist >= minDist) continue

            const next = mergeResult(a.kind, b.kind)
            if (next) {
              const nx = (a.x + b.x) / 2
              const ny = (a.y + b.y) / 2
              const nr = META[next].r
              s.balls.splice(j, 1)
              s.balls.splice(i, 1)
              s.balls.push({
                id: idSeq++,
                kind: next,
                x: nx,
                y: Math.min(FLOOR - nr, ny),
                vx: 0,
                vy: -1.2,
                r: nr,
                settled: false,
              })
              s.mergeFlash = 12
              if (next === 'yuuki' && !awardedRef.current) {
                awardedRef.current = true
                s.status = 'won'
                setStatus('won')
                claimGameClear('family')
                  .then((res) => {
                    setPointsEarned(res.points_earned)
                    if (res.points_earned > 0) notifyPointsUpdated()
                  })
                  .catch(() => setPointsEarned(0))
              }
              return
            }

            const overlap = minDist - dist
            const nx = dx / dist
            const ny = dy / dist
            const push = overlap / 2
            a.x -= nx * push
            a.y -= ny * push
            b.x += nx * push
            b.y += ny * push
            const dvx = b.vx - a.vx
            const dvy = b.vy - a.vy
            const impact = dvx * nx + dvy * ny
            if (impact < 0) {
              const impulse = (-(1 + REST) * impact) / 2
              a.vx -= impulse * nx
              a.vy -= impulse * ny
              b.vx += impulse * nx
              b.vy += impulse * ny
            }
          }
        }
      }

      if (s.mergeFlash > 0) s.mergeFlash -= 1

      const moving = s.balls.some((b) => Math.abs(b.vx) > 0.35 || Math.abs(b.vy) > 0.35)
      if (!moving) s.dropping = false

      const overflow = s.balls.some(
        (b) => b.y - b.r < DANGER_Y && Math.abs(b.vy) < 0.3 && Math.abs(b.vx) < 0.3,
      )
      if (overflow) {
        s.dangerFrames += 1
        if (s.dangerFrames > 45) {
          s.status = 'lost'
          setStatus('lost')
        }
      } else {
        s.dangerFrames = 0
      }
    }

    function drawBall(b: Ball) {
      const m = META[b.kind]
      ctx!.beginPath()
      ctx!.arc(b.x, b.y, b.r, 0, Math.PI * 2)
      ctx!.fillStyle = m.color
      ctx!.fill()
      ctx!.lineWidth = Math.max(3, Math.round(b.r * 0.12))
      ctx!.strokeStyle = m.ring
      ctx!.stroke()
      ctx!.font = `${Math.floor(b.r * 1.15)}px "Segoe UI Emoji", "Apple Color Emoji", sans-serif`
      ctx!.textAlign = 'center'
      ctx!.textBaseline = 'middle'
      ctx!.fillText(m.emoji, b.x, b.y - Math.max(2, b.r * 0.08))
      // 色名のヒント（小さい世代ほど重要）
      if (b.r <= META.oji_f.r + 1) {
        const tip = m.label.includes('・') ? m.label.split('・')[1]! : ''
        if (tip) {
          ctx!.font = `bold ${Math.max(9, Math.floor(b.r * 0.38))}px sans-serif`
          ctx!.fillStyle = '#fff'
          ctx!.strokeStyle = m.ring
          ctx!.lineWidth = 3
          ctx!.strokeText(tip, b.x, b.y + b.r * 0.42)
          ctx!.fillText(tip, b.x, b.y + b.r * 0.42)
        }
      }
    }

    function draw() {
      const s = stateRef.current
      ctx!.clearRect(0, 0, W, H)

      // bowl
      ctx!.fillStyle = '#fff8ee'
      ctx!.fillRect(0, 0, W, H)
      ctx!.fillStyle = '#f3e6d4'
      ctx!.fillRect(0, FLOOR, W, H - FLOOR)

      // danger line
      ctx!.strokeStyle = 'rgba(232, 96, 88, 0.55)'
      ctx!.setLineDash([6, 6])
      ctx!.beginPath()
      ctx!.moveTo(WALL, DANGER_Y)
      ctx!.lineTo(W - WALL, DANGER_Y)
      ctx!.stroke()
      ctx!.setLineDash([])

      // walls
      ctx!.fillStyle = '#e8d4bc'
      ctx!.fillRect(0, 0, WALL, H)
      ctx!.fillRect(W - WALL, 0, WALL, H)

      if (s.mergeFlash > 0) {
        ctx!.fillStyle = `rgba(255, 230, 120, ${s.mergeFlash / 20})`
        ctx!.fillRect(0, 0, W, H)
      }

      for (const b of s.balls) drawBall(b)

      if (s.status === 'playing') {
        const m = META[s.next]
        ctx!.globalAlpha = 0.9
        ctx!.beginPath()
        ctx!.arc(s.aimX, DROP_Y, m.r, 0, Math.PI * 2)
        ctx!.fillStyle = m.color
        ctx!.fill()
        ctx!.lineWidth = Math.max(3, Math.round(m.r * 0.12))
        ctx!.strokeStyle = m.ring
        ctx!.stroke()
        ctx!.font = `${Math.floor(m.r * 1.15)}px "Segoe UI Emoji", "Apple Color Emoji", sans-serif`
        ctx!.textAlign = 'center'
        ctx!.textBaseline = 'middle'
        ctx!.fillText(m.emoji, s.aimX, DROP_Y - Math.max(2, m.r * 0.08))
        const tip = m.label.includes('・') ? m.label.split('・')[1]! : ''
        if (tip) {
          ctx!.font = `bold ${Math.max(9, Math.floor(m.r * 0.38))}px sans-serif`
          ctx!.fillStyle = '#fff'
          ctx!.strokeStyle = m.ring
          ctx!.lineWidth = 3
          ctx!.strokeText(tip, s.aimX, DROP_Y + m.r * 0.42)
          ctx!.fillText(tip, s.aimX, DROP_Y + m.r * 0.42)
        }
        ctx!.globalAlpha = 1
        ctx!.strokeStyle = 'rgba(61,44,30,0.2)'
        ctx!.lineWidth = 1
        ctx!.beginPath()
        ctx!.moveTo(s.aimX, DROP_Y + m.r + 4)
        ctx!.lineTo(s.aimX, FLOOR)
        ctx!.stroke()
      }
    }

    function loop() {
      if (!alive) return
      if (stateRef.current.status === 'playing') stepPhysics()
      draw()
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)

    return () => {
      alive = false
      cancelAnimationFrame(raf)
      canvas.removeEventListener('pointerdown', onPointerDown)
      window.removeEventListener('pointermove', onPointerMove)
      window.removeEventListener('pointerup', onPointerUp)
    }
  }, [])

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <button type="button" onClick={onBack} className="rounded-full bg-cream px-4 py-2 text-sm font-bold">
          ← もどる
        </button>
        <h2 className="text-lg font-black">4世代あわせ</h2>
        <span className="w-16" />
      </div>

      <p className="text-sm text-ink/70">
        ひいじい＋ひいばあ（色のくみあわせ4つ）→ じいじ／ばあば。じいじ＋ばあば → パパ／ママ。パパ＋ママ
        → ゆうき！
      </p>

      <div className="flex items-center gap-2 rounded-2xl bg-white px-3 py-2 text-sm shadow-sm">
        <span className="font-bold text-ink/60">つぎ</span>
        <span className="text-2xl">{META[nextKind].emoji}</span>
        <span className="font-black">{META[nextKind].label}</span>
        <span className="ml-auto text-xs text-ink/50">左右で位置・タップでおとす</span>
      </div>

      <canvas
        ref={canvasRef}
        width={W}
        height={H}
        className="mx-auto block w-full max-w-[400px] touch-none rounded-3xl border-2 border-orange-100 bg-[#fff8ee] shadow-sm"
      />

      {status === 'ready' && (
        <button
          type="button"
          onClick={() => hardReset(true)}
          className="w-full rounded-full bg-sun py-3 text-sm font-black"
        >
          はじめる
        </button>
      )}

      {status === 'won' && (
        <div className="rounded-3xl bg-white p-4 text-center shadow-sm">
          <p className="text-lg font-black text-mint">ゆうきが できた！</p>
          {pointsEarned != null && (
            <p className="mt-1 text-sm text-ink/70">
              {pointsEarned > 0 ? `+${pointsEarned} ポイント` : 'ポイントは つかなかったよ'}
            </p>
          )}
          <button
            type="button"
            onClick={() => hardReset(true)}
            className="mt-3 w-full rounded-full bg-sun py-3 text-sm font-black"
          >
            もういっかい
          </button>
        </div>
      )}

      {status === 'lost' && (
        <div className="rounded-3xl bg-white p-4 text-center shadow-sm">
          <p className="text-lg font-black text-coral">あふれて しまった…</p>
          <button
            type="button"
            onClick={() => hardReset(true)}
            className="mt-3 w-full rounded-full bg-sun py-3 text-sm font-black"
          >
            もういっかい
          </button>
        </div>
      )}
    </div>
  )
}
