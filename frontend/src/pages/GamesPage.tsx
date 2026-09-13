import { useEffect, useState } from 'react'
import { fetchGameAccess, startGamePlay, type GameAccess } from '../api'
import type { Role } from '../role'
import BreakoutGame from './games/BreakoutGame'
import CarGame from './games/CarGame'
import CupGame from './games/CupGame'
import FamilyMergeGame from './games/FamilyMergeGame'
import InvadersGame from './games/InvadersGame'
import MemoryGame from './games/MemoryGame'

type GameId = 'cups' | 'memory' | 'invaders' | 'breakout' | 'racing' | 'family'

const GAMES: { id: GameId; emoji: string; title: string; blurb: string }[] = [
  { id: 'cups', emoji: '🥤', title: 'カップゲーム', blurb: 'たまの ばしょを あてよう' },
  { id: 'memory', emoji: '🃏', title: 'しんけいすいじゃく', blurb: 'おなじ えを ペアにしよう' },
  { id: 'family', emoji: '👨‍👩‍👦', title: '4世代あわせ', blurb: 'かぞくの なまえを あわせて ゆうきを つくろう' },
  { id: 'invaders', emoji: '👾', title: 'インベーダー', blurb: 'てきを ぜんぶ たおそう' },
  { id: 'breakout', emoji: '🧱', title: 'ブロックくずし', blurb: 'ブロックを ぜんぶ くずそう' },
  { id: 'racing', emoji: '🚗', title: 'くるまレース', blurb: 'くるまを よけて すすもう' },
]

export default function GamesPage({ role }: { role: Role }) {
  const [active, setActive] = useState<GameId | null>(null)
  const [access, setAccess] = useState<GameAccess | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (role !== 'child') return
    let cancelled = false
    fetchGameAccess()
      .then((data) => {
        if (!cancelled) {
          setAccess(data)
          setError(null)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setAccess(null)
          setError('あそび回数を よみこめませんでした。ページを さい読み込みしてね。')
        }
      })
    return () => {
      cancelled = true
    }
  }, [role, active])

  async function openGame(id: GameId) {
    setError(null)
    if (role !== 'child') {
      setActive(id)
      return
    }
    if (busy) return
    setBusy(true)
    try {
      const next = await startGamePlay(id)
      setAccess(next)
      setActive(id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'ミニゲームを始められません')
    } finally {
      setBusy(false)
    }
  }

  if (active === 'cups') return <CupGame onBack={() => setActive(null)} />
  if (active === 'memory') return <MemoryGame onBack={() => setActive(null)} />
  if (active === 'family') return <FamilyMergeGame onBack={() => setActive(null)} />
  if (active === 'invaders') return <InvadersGame onBack={() => setActive(null)} />
  if (active === 'breakout') return <BreakoutGame onBack={() => setActive(null)} />
  if (active === 'racing') return <CarGame onBack={() => setActive(null)} />

  const remaining = access?.plays_remaining ?? 0
  const toward = access?.drills_toward_next ?? 0
  const perPlay = access?.drills_per_play ?? 3
  const locked = role === 'child' && access != null && remaining <= 0

  return (
    <div className="space-y-4">
      <section className="rounded-3xl bg-white p-5 shadow-sm">
        <h2 className="text-xl font-black">ミニゲーム</h2>
        <p className="mt-1 text-sm text-ink/70">
          {role === 'child'
            ? `ドリルを ${perPlay} 回やると ミニゲームが 1 回できるよ。クリアすると ポイントが もらえるよ。`
            : 'クリア時のポイントは「ポイント」画面のルールで設定できます。子どもはドリル3回で1回あそべます。'}
        </p>
        {role === 'child' && access && (
          <p className="mt-3 text-sm font-bold text-ink/80">
            あと <span className="text-coral">{remaining}</span> 回あそべる
            {remaining <= 0
              ? `（ドリルがあと ${perPlay - toward} 回で 1 回）`
              : toward > 0
                ? `（つぎの 1 回まで ドリルあと ${perPlay - toward} 回）`
                : ''}
          </p>
        )}
        {error && <p className="mt-2 text-sm font-bold text-coral">{error}</p>}
      </section>

      <ul className="grid grid-cols-1 gap-3">
        {GAMES.map((game) => (
          <li key={game.id}>
            <button
              type="button"
              disabled={busy || locked}
              onClick={() => openGame(game.id)}
              className="flex w-full items-center gap-4 rounded-3xl bg-white p-5 text-left shadow-sm ring-2 ring-transparent transition hover:ring-sun disabled:cursor-not-allowed disabled:opacity-50"
            >
              <span className="text-4xl">{game.emoji}</span>
              <span>
                <span className="block text-lg font-black">{game.title}</span>
                <span className="mt-1 block text-sm text-ink/60">{game.blurb}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
