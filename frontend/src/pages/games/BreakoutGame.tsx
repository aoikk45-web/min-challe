import { useEffect, useRef, useState } from 'react'
import { claimGameClear } from '../../api'
import { notifyPointsUpdated } from '../../pointsRefresh'

type Status = 'ready' | 'playing' | 'won' | 'lost'

type Brick = { x: number; y: number; alive: boolean; color: string }

const W = 360
const H = 480
const PADDLE_W = 72
const PADDLE_H = 14
const BALL_R = 7
const BRICK_ROWS = 4
const BRICK_COLS = 7
const COLORS = ['#ff7a45', '#ffd166', '#4db6e2', '#2bb673']

export default function BreakoutGame({ onBack }: { onBack: () => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [status, setStatus] = useState<Status>('ready')
  const [pointsEarned, setPointsEarned] = useState<number | null>(null)
  const awardedRef = useRef(false)

  const stateRef = useRef({
    status: 'ready' as Status,
    paddleX: W / 2,
    ballX: W / 2,
    ballY: H - 60,
    vx: 3.2,
    vy: -3.8,
    bricks: [] as Brick[],
    left: false,
    right: false,
  })

  function buildBricks(): Brick[] {
    const list: Brick[] = []
    const bw = 44
    const bh = 18
    const gap = 6
    const offsetX = (W - (BRICK_COLS * (bw + gap) - gap)) / 2
    for (let r = 0; r < BRICK_ROWS; r++) {
      for (let c = 0; c < BRICK_COLS; c++) {
        list.push({
          x: offsetX + c * (bw + gap),
          y: 56 + r * (bh + gap),
          alive: true,
          color: COLORS[r % COLORS.length],
        })
      }
    }
    return list
  }

  function reset() {
    awardedRef.current = false
    setPointsEarned(null)
    const s = stateRef.current
    s.status = 'playing'
    s.paddleX = W / 2
    s.ballX = W / 2
    s.ballY = H - 60
    s.vx = 3.2 * (Math.random() > 0.5 ? 1 : -1)
    s.vy = -3.8
    s.bricks = buildBricks()
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
      }
    }
    function onKeyUp(e: KeyboardEvent) {
      const s = stateRef.current
      if (e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') s.left = false
      else if (e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D') s.right = false
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
      ctx!.fillStyle = '#fff8ee'
      ctx!.fillRect(0, 0, W, H)
      ctx!.strokeStyle = '#3d2c1e22'
      ctx!.strokeRect(1, 1, W - 2, H - 2)

      for (const b of s.bricks) {
        if (!b.alive) continue
        ctx!.fillStyle = b.color
        ctx!.fillRect(b.x, b.y, 44, 18)
      }

      ctx!.fillStyle = '#3d2c1e'
      ctx!.fillRect(s.paddleX - PADDLE_W / 2, H - 32, PADDLE_W, PADDLE_H)

      ctx!.fillStyle = '#ff7a45'
      ctx!.beginPath()
      ctx!.arc(s.ballX, s.ballY, BALL_R, 0, Math.PI * 2)
      ctx!.fill()
    }

    function step() {
      if (!alive) return
      const s = stateRef.current
      if (s.status === 'playing') {
        if (s.left) s.paddleX = Math.max(PADDLE_W / 2, s.paddleX - 5)
        if (s.right) s.paddleX = Math.min(W - PADDLE_W / 2, s.paddleX + 5)
        s.ballX += s.vx
        s.ballY += s.vy

        if (s.ballX < BALL_R || s.ballX > W - BALL_R) s.vx *= -1
        if (s.ballY < BALL_R) s.vy *= -1

        // paddle
        const py = H - 32
        if (
          s.ballY + BALL_R >= py &&
          s.ballY + BALL_R <= py + PADDLE_H + 6 &&
          s.ballX > s.paddleX - PADDLE_W / 2 - 4 &&
          s.ballX < s.paddleX + PADDLE_W / 2 + 4 &&
          s.vy > 0
        ) {
          s.vy *= -1
          const offset = (s.ballX - s.paddleX) / (PADDLE_W / 2)
          s.vx = Math.max(-5.5, Math.min(5.5, s.vx + offset * 1.4))
          s.ballY = py - BALL_R
        }

        // bricks
        for (const b of s.bricks) {
          if (!b.alive) continue
          if (
            s.ballX + BALL_R > b.x &&
            s.ballX - BALL_R < b.x + 44 &&
            s.ballY + BALL_R > b.y &&
            s.ballY - BALL_R < b.y + 18
          ) {
            b.alive = false
            s.vy *= -1
            break
          }
        }

        if (s.ballY > H + 20) {
          s.status = 'lost'
          setStatus('lost')
        }
        if (s.bricks.every((b) => !b.alive)) {
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
    claimGameClear('breakout')
      .then((res) => {
        setPointsEarned(res.points_earned)
        if (res.points_earned > 0) notifyPointsUpdated()
      })
      .catch(() => setPointsEarned(0))
  }, [status])

  function move(dir: -1 | 1) {
    const s = stateRef.current
    if (s.status !== 'playing') return
    s.paddleX = Math.max(PADDLE_W / 2, Math.min(W - PADDLE_W / 2, s.paddleX + dir * 36))
  }

  function onPointer(e: React.PointerEvent<HTMLCanvasElement>) {
    const s = stateRef.current
    if (s.status !== 'playing') return
    const rect = e.currentTarget.getBoundingClientRect()
    const x = ((e.clientX - rect.left) / rect.width) * W
    s.paddleX = Math.max(PADDLE_W / 2, Math.min(W - PADDLE_W / 2, x))
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <button type="button" onClick={onBack} className="rounded-full bg-cream px-4 py-2 text-sm font-black">
          もどる
        </button>
        <h2 className="text-lg font-black">ブロックくずし</h2>
        <span className="w-16" />
      </div>

      <div className="rounded-3xl bg-white p-4 shadow-sm">
        <p className="text-center text-sm font-bold text-ink/70">
          {status === 'ready' && 'ブロックを ぜんぶ くずそう'}
          {status === 'playing' && '←→キー／ボタン／ドラッグで うごかす'}
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
          onPointerMove={onPointer}
          onPointerDown={onPointer}
          className="mx-auto mt-3 block w-full max-w-sm touch-none rounded-2xl border border-ink/10"
        />

        <div className="mt-3 grid grid-cols-2 gap-2">
          <button type="button" onClick={() => move(-1)} className="rounded-2xl bg-cream py-3 text-xl font-black">
            ←
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
