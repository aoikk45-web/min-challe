import { useEffect, useRef, useState } from 'react'
import { claimGameClear } from '../../api'
import { notifyPointsUpdated } from '../../pointsRefresh'

type Status = 'ready' | 'playing' | 'won' | 'lost'

type Obstacle = { lane: number; y: number }

const W = 360
const H = 480
const LANES = 3
const GOAL = 20

function laneX(lane: number) {
  const roadLeft = 70
  const roadW = W - 140
  const laneW = roadW / LANES
  return roadLeft + laneW * lane + laneW / 2
}

export default function CarGame({ onBack }: { onBack: () => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [status, setStatus] = useState<Status>('ready')
  const [score, setScore] = useState(0)
  const [pointsEarned, setPointsEarned] = useState<number | null>(null)
  const awardedRef = useRef(false)

  const stateRef = useRef({
    status: 'ready' as Status,
    lane: 1,
    cars: [] as Obstacle[],
    spawn: 0,
    passed: 0,
    speed: 3.2,
    left: false,
    right: false,
    moveCd: 0,
  })

  function reset() {
    awardedRef.current = false
    setPointsEarned(null)
    setScore(0)
    const s = stateRef.current
    s.status = 'playing'
    s.lane = 1
    s.cars = []
    s.spawn = 0
    s.passed = 0
    s.speed = 3.2
    s.moveCd = 0
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
    let stripe = 0

    function drawCar(x: number, y: number, color: string, mine: boolean) {
      ctx!.fillStyle = color
      ctx!.fillRect(x - 18, y - 28, 36, 56)
      ctx!.fillStyle = mine ? '#4db6e2' : '#fff8ee'
      ctx!.fillRect(x - 12, y - 18, 24, 14)
      ctx!.fillStyle = '#3d2c1e'
      ctx!.fillRect(x - 20, y - 22, 6, 12)
      ctx!.fillRect(x + 14, y - 22, 6, 12)
      ctx!.fillRect(x - 20, y + 10, 6, 12)
      ctx!.fillRect(x + 14, y + 10, 6, 12)
    }

    function draw() {
      const s = stateRef.current
      ctx!.fillStyle = '#5a8f4a'
      ctx!.fillRect(0, 0, W, H)
      ctx!.fillStyle = '#555'
      ctx!.fillRect(60, 0, W - 120, H)
      ctx!.strokeStyle = '#ffd166'
      ctx!.setLineDash([18, 16])
      ctx!.lineWidth = 3
      ctx!.beginPath()
      ctx!.moveTo(W / 2, ((stripe % 34) - 34))
      ctx!.lineTo(W / 2, H + 34)
      ctx!.stroke()
      ctx!.setLineDash([])

      for (const car of s.cars) {
        drawCar(laneX(car.lane), car.y, '#ff7a45', false)
      }
      drawCar(laneX(s.lane), H - 70, '#ffd166', true)

      ctx!.fillStyle = '#fff8ee'
      ctx!.font = 'bold 16px sans-serif'
      ctx!.fillText(`${s.passed}/${GOAL}`, 16, 28)
    }

    function step() {
      if (!alive) return
      const s = stateRef.current
      if (s.status === 'playing') {
        stripe += s.speed
        s.moveCd = Math.max(0, s.moveCd - 1)
        if (s.moveCd === 0) {
          if (s.left) {
            s.lane = Math.max(0, s.lane - 1)
            s.moveCd = 10
          } else if (s.right) {
            s.lane = Math.min(LANES - 1, s.lane + 1)
            s.moveCd = 10
          }
        }

        s.spawn += 1
        if (s.spawn > Math.max(28, 55 - s.passed)) {
          s.spawn = 0
          let lane = Math.floor(Math.random() * LANES)
          const last = s.cars[s.cars.length - 1]
          if (last && last.y < 120 && last.lane === lane) {
            lane = (lane + 1) % LANES
          }
          s.cars.push({ lane, y: -40 })
        }

        for (const car of s.cars) car.y += s.speed
        const before = s.cars.length
        s.cars = s.cars.filter((c) => c.y < H + 40)
        const dropped = before - s.cars.length
        if (dropped > 0) {
          s.passed += dropped
          setScore(s.passed)
          s.speed = Math.min(7.5, 3.2 + s.passed * 0.12)
        }

        const py = H - 70
        for (const car of s.cars) {
          if (car.lane === s.lane && Math.abs(car.y - py) < 50) {
            s.status = 'lost'
            setStatus('lost')
            break
          }
        }

        if (s.passed >= GOAL) {
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
    claimGameClear('racing')
      .then((res) => {
        setPointsEarned(res.points_earned)
        if (res.points_earned > 0) notifyPointsUpdated()
      })
      .catch(() => setPointsEarned(0))
  }, [status])

  function nudge(dir: -1 | 1) {
    const s = stateRef.current
    if (s.status !== 'playing') return
    s.lane = Math.max(0, Math.min(LANES - 1, s.lane + dir))
    s.moveCd = 8
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <button type="button" onClick={onBack} className="rounded-full bg-cream px-4 py-2 text-sm font-black">
          もどる
        </button>
        <h2 className="text-lg font-black">くるまレース</h2>
        <span className="w-16" />
      </div>

      <div className="rounded-3xl bg-white p-4 shadow-sm">
        <p className="text-center text-sm font-bold text-ink/70">
          {status === 'ready' && `くるまを よけて ${GOAL}だい とおりぬけよう`}
          {status === 'playing' && `←→キーで レーンいどう ・ ${score}/${GOAL}`}
          {status === 'won' && 'ゴール！'}
          {status === 'lost' && 'ぶつかった…'}
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

        <div className="mt-3 grid grid-cols-2 gap-2">
          <button type="button" onClick={() => nudge(-1)} className="rounded-2xl bg-cream py-3 text-xl font-black">
            ←
          </button>
          <button type="button" onClick={() => nudge(1)} className="rounded-2xl bg-cream py-3 text-xl font-black">
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
