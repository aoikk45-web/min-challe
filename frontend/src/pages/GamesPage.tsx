import { useState } from 'react'
import type { Role } from '../role'
import BreakoutGame from './games/BreakoutGame'
import CarGame from './games/CarGame'
import CupGame from './games/CupGame'
import InvadersGame from './games/InvadersGame'
import MemoryGame from './games/MemoryGame'

type GameId = 'cups' | 'memory' | 'invaders' | 'breakout' | 'racing'

const GAMES: { id: GameId; emoji: string; title: string; blurb: string }[] = [
  { id: 'cups', emoji: '🥤', title: 'カップゲーム', blurb: 'たまの ばしょを あてよう' },
  { id: 'memory', emoji: '🃏', title: 'しんけいすいじゃく', blurb: 'おなじ えを ペアにしよう' },
  { id: 'invaders', emoji: '👾', title: 'インベーダー', blurb: 'てきを ぜんぶ たおそう' },
  { id: 'breakout', emoji: '🧱', title: 'ブロックくずし', blurb: 'ブロックを ぜんぶ くずそう' },
  { id: 'racing', emoji: '🚗', title: 'くるまレース', blurb: 'くるまを よけて すすもう' },
]

export default function GamesPage({ role }: { role: Role }) {
  const [active, setActive] = useState<GameId | null>(null)

  if (active === 'cups') return <CupGame onBack={() => setActive(null)} />
  if (active === 'memory') return <MemoryGame onBack={() => setActive(null)} />
  if (active === 'invaders') return <InvadersGame onBack={() => setActive(null)} />
  if (active === 'breakout') return <BreakoutGame onBack={() => setActive(null)} />
  if (active === 'racing') return <CarGame onBack={() => setActive(null)} />

  return (
    <div className="space-y-4">
      <section className="rounded-3xl bg-white p-5 shadow-sm">
        <h2 className="text-xl font-black">ミニゲーム</h2>
        <p className="mt-1 text-sm text-ink/70">
          {role === 'child'
            ? 'クリアすると ポイントが もらえるよ（おうちの人の設定）。'
            : 'クリア時のポイントは「ポイント」画面のルールで設定できます。'}
        </p>
      </section>

      <ul className="grid grid-cols-1 gap-3">
        {GAMES.map((game) => (
          <li key={game.id}>
            <button
              type="button"
              onClick={() => setActive(game.id)}
              className="flex w-full items-center gap-4 rounded-3xl bg-white p-5 text-left shadow-sm ring-2 ring-transparent transition hover:ring-sun"
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
