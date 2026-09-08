import { useEffect, useRef, useState } from 'react'
import { claimGameClear } from '../../api'
import { notifyPointsUpdated } from '../../pointsRefresh'

type Phase = 'ready' | 'drop' | 'cover' | 'shuffle' | 'pick' | 'result'

const CUP_COUNT = 3
const SHUFFLE_SWAPS = 14
const SHUFFLE_MS_START = 620
const SHUFFLE_MS_END = 130

const SLOT_LEFT = ['16.5%', '50%', '83.5%']
const SLOT_NAME = ['ひだりのカップ', 'まんなかのカップ', 'みぎのカップ']

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function shuffleDuration(step: number, total: number) {
  if (total <= 1) return SHUFFLE_MS_START
  const t = step / (total - 1)
  return Math.round(SHUFFLE_MS_START + (SHUFFLE_MS_END - SHUFFLE_MS_START) * t)
}

export default function CupGame({ onBack }: { onBack: () => void }) {
  const [phase, setPhase] = useState<Phase>('ready')
  const [ballCup, setBallCup] = useState(0)
  /** cupId → slot（ボールは入れた cupId から出さない） */
  const [cupSlot, setCupSlot] = useState([0, 1, 2])
  const [liftedCups, setLiftedCups] = useState<Set<number>>(() => new Set())
  const [pickedCup, setPickedCup] = useState<number | null>(null)
  const [won, setWon] = useState(false)
  const [busy, setBusy] = useState(false)
  const [pointsEarned, setPointsEarned] = useState<number | null>(null)
  const [ballAnim, setBallAnim] = useState<'hidden' | 'up' | 'in'>('hidden')
  const [moveMs, setMoveMs] = useState(SHUFFLE_MS_START)
  const cancelRef = useRef(false)

  useEffect(() => {
    return () => {
      cancelRef.current = true
    }
  }, [])

  async function startRound() {
    cancelRef.current = false
    setBusy(true)
    setLiftedCups(new Set())
    setPickedCup(null)
    setWon(false)
    setPointsEarned(null)
    setBallAnim('hidden')
    setCupSlot([0, 1, 2])

    const cupWithBall = Math.floor(Math.random() * CUP_COUNT)
    setBallCup(cupWithBall)

    setPhase('drop')
    setBallAnim('up')
    await sleep(80)
    if (cancelRef.current) return
    setBallAnim('in')
    await sleep(900)
    if (cancelRef.current) return
    setBallAnim('hidden')

    setPhase('cover')
    await sleep(500)
    if (cancelRef.current) return

    // 1対1（となり／端どうしも可）
    setPhase('shuffle')
    let slots = [0, 1, 2]
    for (let i = 0; i < SHUFFLE_SWAPS; i++) {
      if (cancelRef.current) return
      const duration = shuffleDuration(i, SHUFFLE_SWAPS)
      setMoveMs(duration)
      const a = Math.floor(Math.random() * CUP_COUNT)
      let b = Math.floor(Math.random() * (CUP_COUNT - 1))
      if (b >= a) b += 1
      const cupAtA = slots.indexOf(a)
      const cupAtB = slots.indexOf(b)
      ;[slots[cupAtA], slots[cupAtB]] = [slots[cupAtB], slots[cupAtA]]
      setCupSlot([...slots])
      await sleep(duration)
    }
    if (cancelRef.current) return
    setMoveMs(SHUFFLE_MS_START)

    setPhase('pick')
    setBusy(false)
  }

  async function pickCup(cupId: number) {
    if (phase !== 'pick' || busy) return
    const ok = cupId === ballCup
    setPickedCup(cupId)
    setWon(ok)
    // カップの殻だけ上げる → 床のたまが見える
    setLiftedCups(new Set([cupId, ballCup]))
    setPhase('result')
    if (ok) {
      try {
        const res = await claimGameClear('cups')
        setPointsEarned(res.points_earned)
        if (res.points_earned > 0) notifyPointsUpdated()
      } catch {
        setPointsEarned(0)
      }
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <button type="button" onClick={onBack} className="rounded-full bg-cream px-4 py-2 text-sm font-black">
          もどる
        </button>
        <h2 className="text-lg font-black">カップゲーム</h2>
        <span className="w-16" />
      </div>

      <div className="rounded-3xl bg-white p-5 shadow-sm">
        <p className="text-center text-sm font-bold text-ink/70">
          {phase === 'ready' && 'たまを いれたら、カップを 1対1で いれかえるよ'}
          {phase === 'drop' && 'たまを いれるよ。よくみて…'}
          {phase === 'cover' && 'はいってるよ。つぎ いれかえるね'}
          {phase === 'shuffle' && '1対1で いれかえ中…'}
          {phase === 'pick' && 'たまが はいってる カップは どれ？'}
          {phase === 'result' && (won ? 'せいかい！' : 'ざんねん…')}
        </p>
        {phase === 'result' && won && pointsEarned != null && pointsEarned > 0 && (
          <p className="mt-2 text-center text-sm font-black text-sun">+{pointsEarned}点</p>
        )}

        <div className="relative mx-auto mt-4 h-56 w-full max-w-sm">
          <div className="absolute right-4 bottom-6 left-4 h-2 rounded-full bg-cream" />

          {[0, 1, 2].map((cupId) => {
            const slot = cupSlot[cupId]
            const isBallHere = cupId === ballCup
            const raised = liftedCups.has(cupId)
            const showBallDrop = isBallHere && (ballAnim === 'up' || ballAnim === 'in')
            const showBallReveal = phase === 'result' && isBallHere
            const canPick = phase === 'pick'

            return (
              <div
                key={cupId}
                className="absolute bottom-4 w-[28%]"
                style={{
                  left: SLOT_LEFT[slot],
                  transition: `left ${moveMs}ms cubic-bezier(0.45, 0.05, 0.55, 0.95)`,
                  zIndex: raised ? 20 : 10 + slot,
                  transform: 'translateX(-50%)',
                }}
              >
                {/* たまは床に残す（カップ移動時も cup に付いて一緒に移動／開けたら見える） */}
                {showBallDrop && (
                  <span
                    className="pointer-events-none absolute left-1/2 z-0 h-9 w-9 -translate-x-1/2 rounded-full bg-coral shadow-md transition-all duration-1000 ease-in"
                    style={{ bottom: ballAnim === 'in' ? '0.6rem' : '8.5rem' }}
                  />
                )}
                {showBallReveal && (
                  <span className="pointer-events-none absolute bottom-1 left-1/2 z-0 h-9 w-9 -translate-x-1/2 rounded-full bg-coral shadow-lg ring-2 ring-white" />
                )}

                <button
                  type="button"
                  disabled={!canPick}
                  onClick={() => pickCup(cupId)}
                  aria-label={SLOT_NAME[slot]}
                  className="relative z-10 block w-full disabled:cursor-default"
                  style={{
                    transform: raised ? 'translateY(-3.5rem)' : 'translateY(0)',
                    transition: 'transform 450ms ease',
                  }}
                >
                  <span
                    className={`block h-32 w-full rounded-b-[2.2rem] rounded-t-[45%] border-4 border-ink/10 bg-sky shadow-lg ${
                      phase === 'result' && isBallHere && won ? 'bg-mint' : ''
                    } ${phase === 'result' && pickedCup === cupId && !won ? 'bg-coral' : ''} ${
                      canPick ? 'hover:brightness-105' : ''
                    }`}
                  >
                    <span className="mx-auto mt-3 block h-2 w-10 rounded-full bg-white/35" />
                  </span>
                </button>
              </div>
            )
          })}
        </div>

        <div className="mt-4 flex justify-center">
          {(phase === 'ready' || phase === 'result') && (
            <button
              type="button"
              onClick={startRound}
              disabled={busy}
              className="rounded-full bg-sun px-6 py-3 font-black disabled:opacity-50"
            >
              {phase === 'ready' ? 'はじめる' : 'もういっかい'}
            </button>
          )}
        </div>
      </div>
    </section>
  )
}
