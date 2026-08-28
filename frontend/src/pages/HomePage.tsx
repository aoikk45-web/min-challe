import { Link } from 'react-router-dom'
import type { Household } from '../api'
import type { Role } from '../role'

const pillars = [
  { to: '/plan', emoji: '📒', title: 'けいかく', child: 'きょう なにを する？', parent: '今週の予定を置く' },
  { to: '/drill', emoji: '✨', title: 'ドリル', child: 'さんすう 10もん', parent: '計算のれんしゅう' },
  { to: '/points', emoji: '🏅', title: 'ポイント', child: 'がんばりが みえるよ', parent: 'ルールをごほうび' },
  { to: '/album', emoji: '📔', title: 'アルバム', child: 'できた きろく', parent: '成長の記録' },
]

export default function HomePage({ household, role }: { household: Household; role: Role }) {
  const me = role === 'child' ? household.child : household.parent
  const child = household.child

  return (
    <div className="space-y-4">
      <section className="rounded-3xl bg-white p-5 shadow-sm">
        <p className="text-4xl">{me.avatar}</p>
        <h2 className="mt-2 text-2xl font-black">
          {role === 'child' ? `こんにちは、${child.display_name}！` : `${household.name}のページ`}
        </h2>
        <p className="mt-1 text-sm leading-relaxed text-ink/70">
          {role === 'child'
            ? `小学${child.grade}年生。きょうも じぶんで やってみよう。`
            : `${child.display_name}（小学${child.grade}年生）の学習を見守る画面です。4本柱の中身は次のループで足します。`}
        </p>
      </section>

      <ul className="grid grid-cols-2 gap-3">
        {pillars.map((p) => (
          <li key={p.to}>
            <Link
              to={p.to}
              className="block h-full rounded-3xl bg-white p-4 shadow-sm ring-2 ring-transparent transition hover:ring-sun"
            >
              <span className="text-2xl">{p.emoji}</span>
              <p className="mt-2 font-black">{p.title}</p>
              <p className="mt-1 text-xs text-ink/60">{role === 'child' ? p.child : p.parent}</p>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
