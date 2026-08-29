import { Link } from 'react-router-dom'
import { useCallback, useState } from 'react'
import {
  fetchPointSummary,
  formatPlanDay,
  todayJstISO,
  usePlans,
  type Household,
  type PointSummary,
  type StudyPlan,
} from '../api'
import type { Role } from '../role'
import { usePointsRefresh } from '../pointsRefresh'

const pillars = [
  { to: '/plan', emoji: '📒', title: 'けいかく', child: 'きょう なにを する？', parent: '今週の予定を置く' },
  { to: '/drill', emoji: '✨', title: 'ドリル', child: 'さんすう・こくご 10もん', parent: '計算とこくごのれんしゅう' },
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
            : `${child.display_name}（小学${child.grade}年生）の学習を見守る画面です。`}
        </p>
      </section>

      <TodayPlans role={role} />
      <HomeBalance role={role} />

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

function TodayPlans({ role }: { role: Role }) {
  const { plans, loading, error } = usePlans(role)
  const today = todayJstISO()
  const todayPlans = plans.filter((p) => p.plan_date === today)

  return (
    <section className="rounded-3xl bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-lg font-black">きょうのけいかく</h3>
        <Link to="/plan" className="text-xs font-bold text-sky">
          ぜんぶみる
        </Link>
      </div>
      {loading && <p className="mt-2 text-sm text-ink/60">よみこみちゅう…</p>}
      {error && <p className="mt-2 text-sm text-coral">つながらなかったよ。もういちど開いてみてね。</p>}
      {!loading && !error && todayPlans.length === 0 && (
        <p className="mt-2 text-sm text-ink/70">
          {role === 'child'
            ? 'きょうの よては まだないよ。おうちの人につくってもらおう。'
            : 'きょうの よては まだないよ。けいかくから追加できるよ。'}
        </p>
      )}
      {!loading && todayPlans.length > 0 && (
        <ul className="mt-3 space-y-2">
          {todayPlans.map((plan) => (
            <li key={plan.id}>
              <HomePlanRow plan={plan} />
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function HomeBalance({ role }: { role: Role }) {
  const [summary, setSummary] = useState<PointSummary | null>(null)
  const [error, setError] = useState(false)
  const [loading, setLoading] = useState(true)

  const reload = useCallback(() => {
    setLoading(true)
    setError(false)
    fetchPointSummary(role)
      .then((data) => setSummary(data))
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [role])

  usePointsRefresh(reload)

  return (
    <section className="rounded-3xl bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-black">ポイント</h3>
        <Link to="/points" className="text-xs font-bold text-sky">
          くわしく
        </Link>
      </div>
      {loading && <p className="mt-2 text-sm text-ink/60">よみこみちゅう…</p>}
      {error && <p className="mt-2 text-sm text-coral">つながらなかったよ。もういちど開いてみてね。</p>}
      {summary && (
        <p className="mt-2 text-3xl font-black">{summary.balance}点</p>
      )}
      {summary?.next_reward && (
        <p className="mt-1 text-sm text-ink/70">
          {summary.next_reward.remaining > 0
            ? `「${summary.next_reward.name}」まで あと${summary.next_reward.remaining}点`
            : `「${summary.next_reward.name}」と こうかんできるよ`}
        </p>
      )}
    </section>
  )
}

function HomePlanRow({ plan }: { plan: StudyPlan }) {
  const done = plan.completed_at != null
  return (
    <div className={`rounded-2xl px-3 py-2 ${done ? 'bg-mint/15' : 'bg-cream'}`}>
      <p className="text-xs font-bold text-sky">{plan.subject}</p>
      <p className="font-black">
        {plan.title}
        {done ? ' ・できたね' : ''}
      </p>
      <p className="text-xs text-ink/50">
        {formatPlanDay(plan.plan_date)} ・ {plan.minutes}ふん
      </p>
    </div>
  )
}
