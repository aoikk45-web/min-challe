import { useEffect, useRef, useState } from 'react'
import { claimGameClear } from '../../api'
import { notifyPointsUpdated } from '../../pointsRefresh'

type Status = 'ready' | 'playing' | 'won' | 'lost'

type Kind =
  | 'hiiji_ao'
  | 'hiiba_ao'
  | 'hiiji_mizu'
  | 'hiiba_mizu'
  | 'hiiji_aka'
  | 'hiiba_aka'
  | 'hiiji_orenji'
  | 'hiiba_orenji'
  | 'jiji_ao'
  | 'baba_mizu'
  | 'jiji_aka'
  | 'baba_orenji'
  | 'papa_ao'
  | 'mama_aka'
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
  /** 一度でも点線より下に入ったか（落とす位置は点線より上なので必須） */
  enteredPlay: boolean
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

/** 落とせるのは4色のひいじい／ひいばあ */
const DROP_KINDS: Kind[] = [
  'hiiji_ao',
  'hiiba_ao',
  'hiiji_mizu',
  'hiiba_mizu',
  'hiiji_aka',
  'hiiba_aka',
  'hiiji_orenji',
  'hiiba_orenji',
]

/** ゆうきの直径 = 画面幅のちょうど 1/4。他世代も比例拡大。 */
const R_YUUKI = Math.round(W / 8)
const R_HII = Math.round(R_YUUKI * 0.42)
const R_SOFU = Math.round(R_YUUKI * 0.62)
const R_OYA = Math.round(R_YUUKI * 0.82)

const META: Record<
  Kind,
  { label: string; tip: string; emoji: string; color: string; ring: string; r: number }
> = {
  hiiji_ao: { label: 'ひいじい・あお', tip: 'あお', emoji: '👴', color: '#3b82f6', ring: '#1e3a8a', r: R_HII },
  hiiba_ao: { label: 'ひいばあ・あお', tip: 'あお', emoji: '👵', color: '#60a5fa', ring: '#1e40af', r: R_HII },
  hiiji_mizu: { label: 'ひいじい・みず', tip: 'みず', emoji: '👴', color: '#06b6d4', ring: '#155e75', r: R_HII },
  hiiba_mizu: { label: 'ひいばあ・みず', tip: 'みず', emoji: '👵', color: '#22d3ee', ring: '#0e7490', r: R_HII },
  hiiji_aka: { label: 'ひいじい・あか', tip: 'あか', emoji: '👴', color: '#ef4444', ring: '#991b1b', r: R_HII },
  hiiba_aka: { label: 'ひいばあ・あか', tip: 'あか', emoji: '👵', color: '#f87171', ring: '#b91c1c', r: R_HII },
  hiiji_orenji: { label: 'ひいじい・おれんじ', tip: 'おれんじ', emoji: '👴', color: '#f97316', ring: '#9a3412', r: R_HII },
  hiiba_orenji: { label: 'ひいばあ・おれんじ', tip: 'おれんじ', emoji: '👵', color: '#fb923c', ring: '#c2410c', r: R_HII },
  jiji_ao: { label: 'じいじ・あお', tip: 'あお', emoji: '👴', color: '#1d4ed8', ring: '#172554', r: R_SOFU },
  baba_mizu: { label: 'ばあば・みず', tip: 'みず', emoji: '👵', color: '#0891b2', ring: '#164e63', r: R_SOFU },
  jiji_aka: { label: 'じいじ・あか', tip: 'あか', emoji: '👴', color: '#dc2626', ring: '#7f1d1d', r: R_SOFU },
  baba_orenji: { label: 'ばあば・おれんじ', tip: 'おれんじ', emoji: '👵', color: '#ea580c', ring: '#7c2d12', r: R_SOFU },
  papa_ao: { label: 'パパ・あお', tip: 'あお', emoji: '👨', color: '#2563eb', ring: '#1e3a8a', r: R_OYA },
  mama_aka: { label: 'ママ・あか', tip: 'あか', emoji: '👩', color: '#e11d48', ring: '#881337', r: R_OYA },
  yuuki: { label: 'ゆうき・きいろ', tip: 'きいろ', emoji: '🧒', color: '#facc15', ring: '#a16207', r: R_YUUKI },
}

function mergeResult(a: Kind, b: Kind): Kind | null {
  if (a === b) return null
  const set = new Set([a, b])

  // ①あお ひいじい＋ひいばあ → あおじいじ
  if (set.has('hiiji_ao') && set.has('hiiba_ao')) return 'jiji_ao'
  // ②みず ひいじい＋ひいばあ → みずばあば
  if (set.has('hiiji_mizu') && set.has('hiiba_mizu')) return 'baba_mizu'
  // ③あか ひいじい＋ひいばあ → あかじいじ
  if (set.has('hiiji_aka') && set.has('hiiba_aka')) return 'jiji_aka'
  // ④おれんじ ひいじい＋ひいばあ → おれんじばあば
  if (set.has('hiiji_orenji') && set.has('hiiba_orenji')) return 'baba_orenji'

  // あおじいじ＋みずばあば → あおパパ
  if (set.has('jiji_ao') && set.has('baba_mizu')) return 'papa_ao'
  // あかじいじ＋おれんじばあば → あかママ
  if (set.has('jiji_aka') && set.has('baba_orenji')) return 'mama_aka'
  // あおパパ＋あかママ → きいろゆうき
  if (set.has('papa_ao') && set.has('mama_aka')) return 'yuuki'
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
      enteredPlay: false,
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
                // マージ地点が点線より下ならプレイ済み扱い
                enteredPlay: ny - nr > DANGER_Y,
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

      for (const b of s.balls) {
        // 球の上端が点線より下に入ったら「場に入った」
        if (!b.enteredPlay && b.y - b.r > DANGER_Y + 2) {
          b.enteredPlay = true
        }
      }

      const moving = s.balls.some((b) => Math.abs(b.vx) > 0.4 || Math.abs(b.vy) > 0.4)
      if (!moving) s.dropping = false

      // 一度場に入った球が、落ち着いた状態で点線より上に残っていたら負け
      // （落とした直後・横詰まりで上に留まっただけの球は対象外）
      const overflow =
        !s.dropping &&
        !moving &&
        s.balls.some(
          (b) =>
            b.enteredPlay &&
            b.y - b.r < DANGER_Y &&
            Math.abs(b.vy) < 0.25 &&
            Math.abs(b.vx) < 0.25,
        )
      if (overflow) {
        s.dangerFrames += 1
        if (s.dangerFrames > 75) {
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
      if (b.r <= R_SOFU + 1) {
        const tip = m.tip
        if (tip) {
          ctx!.font = `bold ${Math.max(9, Math.floor(b.r * 0.36))}px sans-serif`
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
        const tip = m.tip
        if (tip) {
          ctx!.font = `bold ${Math.max(9, Math.floor(m.r * 0.36))}px sans-serif`
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

      <p className="text-sm leading-relaxed text-ink/70">
        同じ色のひいじい＋ひいばあ → じいじ／ばあば。あおじいじ＋みずばあば → あおパパ。あかじいじ＋おれんじばあば
        → あかママ。パパ＋ママ → きいろゆうき。点線までつみあがったらおわり。
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
          <p className="text-lg font-black text-coral">点線まで つみあがった…</p>
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
