import { useEffect, useMemo, useRef, useState } from 'react'
import { claimGameClear } from '../../api'
import { notifyPointsUpdated } from '../../pointsRefresh'

type Card = {
  id: number
  face: string
  matched: boolean
}

const FACES = ['🍎', '🌟', '🐸', '🚗', '🎈', '🐶']

function shuffle<T>(items: T[]): T[] {
  const next = [...items]
  for (let i = next.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[next[i], next[j]] = [next[j], next[i]]
  }
  return next
}

function buildDeck(): Card[] {
  const pairs = FACES.flatMap((face, idx) => [
    { id: idx * 2, face, matched: false },
    { id: idx * 2 + 1, face, matched: false },
  ])
  return shuffle(pairs)
}

export default function MemoryGame({ onBack }: { onBack: () => void }) {
  const [deck, setDeck] = useState<Card[]>(() => buildDeck())
  const [flipped, setFlipped] = useState<number[]>([])
  const [locked, setLocked] = useState(false)
  const [pointsEarned, setPointsEarned] = useState<number | null>(null)
  const awardedRef = useRef(false)

  const cleared = useMemo(() => deck.length > 0 && deck.every((c) => c.matched), [deck])

  useEffect(() => {
    if (!cleared || awardedRef.current) return
    awardedRef.current = true
    claimGameClear('memory')
      .then((res) => {
        setPointsEarned(res.points_earned)
        if (res.points_earned > 0) notifyPointsUpdated()
      })
      .catch(() => setPointsEarned(0))
  }, [cleared])

  function restart() {
    awardedRef.current = false
    setDeck(buildDeck())
    setFlipped([])
    setLocked(false)
    setPointsEarned(null)
  }

  function tap(index: number) {
    if (locked || cleared) return
    const card = deck[index]
    if (card.matched || flipped.includes(index)) return
    if (flipped.length >= 2) return

    const nextFlipped = [...flipped, index]
    setFlipped(nextFlipped)

    if (nextFlipped.length < 2) return

    const [a, b] = nextFlipped
    if (deck[a].face === deck[b].face) {
      setDeck((prev) =>
        prev.map((c, i) => (i === a || i === b ? { ...c, matched: true } : c)),
      )
      setFlipped([])
      return
    }

    setLocked(true)
    window.setTimeout(() => {
      setFlipped([])
      setLocked(false)
    }, 700)
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <button type="button" onClick={onBack} className="rounded-full bg-cream px-4 py-2 text-sm font-black">
          もどる
        </button>
        <h2 className="text-lg font-black">しんけいすいじゃく</h2>
        <span className="w-16" />
      </div>

      <div className="rounded-3xl bg-white p-5 shadow-sm">
        <p className="text-center text-sm font-bold text-ink/70">
          {cleared ? 'ぜんぶ そろった！' : 'おなじ えを みつけよう'}
        </p>
        {cleared && pointsEarned != null && pointsEarned > 0 && (
          <p className="mt-2 text-center text-sm font-black text-sun">+{pointsEarned}点</p>
        )}

        <ul className="mt-5 grid grid-cols-3 gap-2">
          {deck.map((card, index) => {
            const open = card.matched || flipped.includes(index)
            return (
              <li key={card.id}>
                <button
                  type="button"
                  disabled={locked || open}
                  onClick={() => tap(index)}
                  className={`flex aspect-square w-full items-center justify-center rounded-2xl text-3xl font-black shadow-sm transition ${
                    open ? 'bg-cream' : 'bg-sky text-white'
                  } disabled:cursor-default`}
                  aria-label={open ? card.face : 'うら'}
                >
                  {open ? card.face : '?'}
                </button>
              </li>
            )
          })}
        </ul>

        <div className="mt-6 flex justify-center">
          <button type="button" onClick={restart} className="rounded-full bg-sun px-6 py-3 font-black">
            {cleared ? 'もういっかい' : 'やりなおす'}
          </button>
        </div>
      </div>
    </section>
  )
}
