import { useState, type FormEvent } from 'react'
import {
  completePlan,
  createPlan,
  deletePlan,
  formatPlanDay,
  todayJstISO,
  updatePlan,
  usePlans,
  type PlanBody,
  type StudyPlan,
} from '../api'
import type { Role } from '../role'

const SUBJECTS = ['こくご', 'さんすう', 'りか', 'しゃかい', 'そのた'] as const

export default function PlanPage({ role }: { role: Role }) {
  const { plans, error, loading, reload } = usePlans(role)
  const today = todayJstISO()
  const todayPlans = plans.filter((p) => p.plan_date === today)

  if (loading) {
    return <p className="rounded-2xl bg-white p-6 text-center shadow-sm">ちょっとまってね…</p>
  }
  if (error) {
    return (
      <p className="rounded-2xl bg-white p-6 text-center text-coral shadow-sm">
        つながらなかったよ。もういちど開いてみてね。
      </p>
    )
  }

  return (
    <div className="space-y-4">
      <section className="rounded-3xl bg-white p-5 shadow-sm">
        <h2 className="text-xl font-black">きょうのけいかく</h2>
        {todayPlans.length === 0 ? (
          <p className="mt-2 text-sm text-ink/70">
            {role === 'child'
              ? 'きょうの よては まだないよ。おうちの人につくってもらおう。'
              : 'きょうの よては まだないよ。下からついかできるよ。'}
          </p>
        ) : (
          <ul className="mt-3 space-y-2">
            {todayPlans.map((plan) => (
              <li key={plan.id}>
                <PlanCard plan={plan} role={role} onChange={reload} />
              </li>
            ))}
          </ul>
        )}
      </section>

      {plans.length === 0 && (
        <Empty
          emoji="📒"
          title="学習計画"
          body={
            role === 'child'
              ? 'まだ予定がないよ。おうちの人につくってもらおう。'
              : '今週の計画を下からついかできるよ。'
          }
        />
      )}

      {plans.some((p) => p.plan_date !== today) && (
        <section className="rounded-3xl bg-white p-5 shadow-sm">
          <h2 className="text-xl font-black">こんしゅう</h2>
          <WeekList plans={plans.filter((p) => p.plan_date !== today)} role={role} onChange={reload} />
        </section>
      )}

      {role === 'parent' && <PlanForm onSaved={reload} />}
    </div>
  )
}

function WeekList({
  plans,
  role,
  onChange,
}: {
  plans: StudyPlan[]
  role: Role
  onChange: () => void
}) {
  const dates = [...new Set(plans.map((p) => p.plan_date))]
  return (
    <div className="mt-3 space-y-4">
      {dates.map((day) => (
        <div key={day}>
          <p className="text-sm font-bold text-ink/60">{formatPlanDay(day)}</p>
          <ul className="mt-2 space-y-2">
            {plans
              .filter((p) => p.plan_date === day)
              .map((plan) => (
                <li key={plan.id}>
                  <PlanCard plan={plan} role={role} onChange={onChange} />
                </li>
              ))}
          </ul>
        </div>
      ))}
    </div>
  )
}

function PlanCard({
  plan,
  role,
  onChange,
}: {
  plan: StudyPlan
  role: Role
  onChange: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState(false)
  const done = plan.completed_at != null

  async function markDone() {
    setBusy(true)
    try {
      await completePlan(role, plan.id)
      onChange()
    } catch {
      /* keep card; parent reload shows error via list */
    } finally {
      setBusy(false)
    }
  }

  async function remove() {
    if (!window.confirm('このけいかくを消しますか？')) return
    setBusy(true)
    try {
      await deletePlan(role, plan.id)
      onChange()
    } finally {
      setBusy(false)
    }
  }

  if (editing) {
    return (
      <PlanForm
        initial={plan}
        onCancel={() => setEditing(false)}
        onSaved={() => {
          setEditing(false)
          onChange()
        }}
      />
    )
  }

  return (
    <article className={`rounded-2xl p-4 ${done ? 'bg-mint/15' : 'bg-cream'}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-bold text-sky">{plan.subject}</p>
          <p className="mt-1 font-black">{plan.title}</p>
          <p className="mt-1 text-xs text-ink/60">めやす {plan.minutes}ふん</p>
        </div>
        {done && <span className="text-sm font-black text-mint">できたね</span>}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {!done && (
          <button
            type="button"
            disabled={busy}
            onClick={markDone}
            className="rounded-full bg-sun px-4 py-2 text-sm font-black disabled:opacity-50"
          >
            できた
          </button>
        )}
        {role === 'parent' && (
          <>
            <button
              type="button"
              disabled={busy}
              onClick={() => setEditing(true)}
              className="rounded-full bg-white px-4 py-2 text-sm font-bold shadow-sm"
            >
              なおす
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={remove}
              className="rounded-full bg-white px-4 py-2 text-sm font-bold text-coral shadow-sm"
            >
              けす
            </button>
          </>
        )}
      </div>
    </article>
  )
}

function PlanForm({
  initial,
  onSaved,
  onCancel,
}: {
  initial?: StudyPlan
  onSaved: () => void
  onCancel?: () => void
}) {
  const [planDate, setPlanDate] = useState(initial?.plan_date ?? todayJstISO())
  const [subject, setSubject] = useState(initial?.subject ?? 'さんすう')
  const [title, setTitle] = useState(initial?.title ?? '')
  const [minutes, setMinutes] = useState(String(initial?.minutes ?? 15))
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    const body: PlanBody = {
      plan_date: planDate,
      subject,
      title,
      minutes: Number(minutes),
    }
    setBusy(true)
    setFailed(false)
    try {
      if (initial) {
        await updatePlan('parent', initial.id, body)
      } else {
        await createPlan('parent', body)
        setTitle('')
      }
      onSaved()
    } catch {
      setFailed(true)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3 rounded-3xl bg-white p-5 shadow-sm">
      <h3 className="font-black">{initial ? 'けいかくをなおす' : 'けいかくを追加'}</h3>
      <label className="block text-sm font-bold">
        日付
        <input
          type="date"
          required
          value={planDate}
          onChange={(e) => setPlanDate(e.target.value)}
          className="mt-1 w-full rounded-2xl border-0 bg-cream px-3 py-2 font-normal"
        />
      </label>
      <label className="block text-sm font-bold">
        科目
        <select
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          className="mt-1 w-full rounded-2xl border-0 bg-cream px-3 py-2 font-normal"
        >
          {SUBJECTS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-sm font-bold">
        内容
        <input
          required
          maxLength={120}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="かけ算のれんしゅう"
          className="mt-1 w-full rounded-2xl border-0 bg-cream px-3 py-2 font-normal"
        />
      </label>
      <label className="block text-sm font-bold">
        目安（分）
        <input
          type="number"
          required
          min={1}
          max={240}
          value={minutes}
          onChange={(e) => setMinutes(e.target.value)}
          className="mt-1 w-full rounded-2xl border-0 bg-cream px-3 py-2 font-normal"
        />
      </label>
      {failed && <p className="text-sm text-coral">うまくいかなかったよ。もういちどためしてね。</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={busy}
          className="rounded-full bg-sky px-5 py-2 text-sm font-black text-white disabled:opacity-50"
        >
          {initial ? 'ほぞん' : 'ついか'}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="rounded-full bg-cream px-5 py-2 text-sm font-bold"
          >
            やめる
          </button>
        )}
      </div>
    </form>
  )
}

export function Empty({ emoji, title, body }: { emoji: string; title: string; body: string }) {
  return (
    <section className="rounded-3xl bg-white p-8 text-center shadow-sm">
      <p className="text-5xl">{emoji}</p>
      <h2 className="mt-3 text-xl font-black">{title}</h2>
      <p className="mt-2 text-sm leading-relaxed text-ink/70">{body}</p>
    </section>
  )
}
