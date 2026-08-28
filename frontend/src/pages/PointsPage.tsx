import { useEffect, useMemo, useState } from 'react'
import {
  createReward,
  deleteReward,
  fetchLedger,
  fetchPointSummary,
  fetchRewards,
  fetchRules,
  giveStamp,
  redeemReward,
  saveRules,
  updateReward,
  type LedgerEntry,
  type PointRule,
  type PointSummary,
  type Reward,
} from '../api'
import type { Role } from '../role'

export default function PointsPage({ role }: { role: Role }) {
  const [summary, setSummary] = useState<PointSummary | null>(null)
  const [ledger, setLedger] = useState<LedgerEntry[]>([])
  const [rules, setRules] = useState<PointRule[]>([])
  const [rewards, setRewards] = useState<Reward[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [message, setMessage] = useState('')

  async function reload() {
    const [s, l, ru, rw] = await Promise.all([
      fetchPointSummary(role),
      fetchLedger(role),
      fetchRules(role),
      fetchRewards(role),
    ])
    setSummary(s)
    setLedger(l)
    setRules(ru)
    setRewards(rw)
  }

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(false)
    Promise.all([fetchPointSummary(role), fetchLedger(role), fetchRules(role), fetchRewards(role)])
      .then(([s, l, ru, rw]) => {
        if (cancelled) return
        setSummary(s)
        setLedger(l)
        setRules(ru)
        setRewards(rw)
      })
      .catch(() => {
        if (!cancelled) setError(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [role])

  if (loading) {
    return <p className="rounded-2xl bg-white p-6 text-center shadow-sm">ちょっとまってね…</p>
  }
  if (error || !summary) {
    return (
      <p className="rounded-2xl bg-white p-6 text-center text-coral shadow-sm">
        つながらなかったよ。もういちど開いてみてね。
      </p>
    )
  }

  return (
    <div className="space-y-4">
      <BalanceCard summary={summary} />
      {message && <p className="text-center text-sm font-bold text-coral">{message}</p>}
      <RewardList
        rewards={rewards.filter((r) => r.enabled || role === 'parent')}
        role={role}
        balance={summary.balance}
        onRedeem={async (id) => {
          try {
            setMessage('')
            const next = await redeemReward(id)
            setSummary(next)
            await reload()
          } catch (err) {
            setMessage(err instanceof Error ? err.message : 'うまくいかなかったよ')
          }
        }}
        onToggle={async (reward, enabled) => {
          await updateReward(reward.id, { enabled })
          await reload()
        }}
        onDelete={async (id) => {
          if (!window.confirm('このごほうびを消しますか？')) return
          await deleteReward(id)
          await reload()
        }}
      />
      {role === 'parent' && (
        <>
          <StampForm
            rules={rules}
            onGive={async (note, eventKey) => {
              try {
                setMessage('')
                const next = await giveStamp(note, eventKey)
                setSummary(next)
                await reload()
              } catch (err) {
                setMessage(err instanceof Error ? err.message : 'うまくいかなかったよ')
              }
            }}
          />
          <RuleEditor
            rules={rules}
            onSave={async (next) => {
              setRules(await saveRules(next))
            }}
          />
          <RewardForm
            onCreate={async (name, cost) => {
              await createReward({ name, cost })
              await reload()
            }}
          />
        </>
      )}
      <LedgerList ledger={ledger} />
    </div>
  )
}

function BalanceCard({ summary }: { summary: PointSummary }) {
  const next = summary.next_reward
  const pct = Math.round(summary.progress * 100)
  return (
    <section className="rounded-3xl bg-white p-5 shadow-sm">
      <p className="text-sm font-bold text-sky">いまのポイント</p>
      <p className="mt-1 text-4xl font-black">{summary.balance}点</p>
      {next && (
        <div className="mt-4">
          <p className="text-sm font-bold">
            {next.remaining > 0 ? `つぎの「${next.name}」まで あと${next.remaining}点` : `「${next.name}」と こうかんできるよ`}
          </p>
          <div className="mt-2 h-3 overflow-hidden rounded-full bg-cream">
            <div className="h-full rounded-full bg-sun" style={{ width: `${pct}%` }} />
          </div>
        </div>
      )}
    </section>
  )
}

function RewardList({
  rewards,
  role,
  balance,
  onRedeem,
  onToggle,
  onDelete,
}: {
  rewards: Reward[]
  role: Role
  balance: number
  onRedeem: (id: number) => void
  onToggle: (reward: Reward, enabled: boolean) => void
  onDelete: (id: number) => void
}) {
  return (
    <section className="rounded-3xl bg-white p-5 shadow-sm">
      <h2 className="text-lg font-black">ごほうび</h2>
      {rewards.length === 0 && <p className="mt-2 text-sm text-ink/60">まだごほうびがないよ。</p>}
      <ul className="mt-3 space-y-2">
        {rewards.map((reward) => {
          const lack = Math.max(0, reward.cost - balance)
          return (
            <li key={reward.id} className="rounded-2xl bg-cream p-3">
              <p className="font-black">
                {reward.name} ・ {reward.cost}点
                {!reward.enabled && <span className="ml-2 text-xs text-ink/50">オフ</span>}
              </p>
              {role === 'child' && reward.enabled && (
                <button
                  type="button"
                  onClick={() => onRedeem(reward.id)}
                  disabled={lack > 0}
                  className="mt-2 rounded-full bg-sun px-4 py-1.5 text-sm font-black disabled:bg-white disabled:text-ink/50"
                >
                  {lack > 0 ? `あと${lack}点` : 'こうかん'}
                </button>
              )}
              {role === 'parent' && (
                <div className="mt-2 flex gap-2">
                  <button
                    type="button"
                    onClick={() => onToggle(reward, !reward.enabled)}
                    className="rounded-full bg-white px-3 py-1 text-xs font-bold"
                  >
                    {reward.enabled ? 'オフ' : 'オン'}
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(reward.id)}
                    className="rounded-full bg-white px-3 py-1 text-xs font-bold text-coral"
                  >
                    けす
                  </button>
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}

function LedgerList({ ledger }: { ledger: LedgerEntry[] }) {
  return (
    <section className="rounded-3xl bg-white p-5 shadow-sm">
      <h2 className="text-lg font-black">りれき</h2>
      {ledger.length === 0 && <p className="mt-2 text-sm text-ink/60">まだ動きがないよ。</p>}
      <ul className="mt-3 space-y-2">
        {ledger.map((row) => (
          <li key={row.id} className="flex justify-between text-sm">
            <span>{row.reason}</span>
            <span className={`font-black ${row.delta >= 0 ? 'text-mint' : 'text-coral'}`}>
              {row.delta >= 0 ? '+' : ''}
              {row.delta}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}

function isCustomRule(rule: PointRule) {
  return rule.event_key.startsWith('custom_') || rule.id <= 0
}

function StampForm({
  rules,
  onGive,
}: {
  rules: PointRule[]
  onGive: (note: string, eventKey: string) => Promise<void>
}) {
  const awardable = useMemo(
    () =>
      rules.filter(
        (rule) => rule.enabled && (rule.event_key === 'stamp' || rule.event_key.startsWith('custom_')),
      ),
    [rules],
  )
  const [note, setNote] = useState('')
  const [eventKey, setEventKey] = useState(awardable[0]?.event_key ?? 'stamp')

  useEffect(() => {
    if (!awardable.some((rule) => rule.event_key === eventKey)) {
      setEventKey(awardable[0]?.event_key ?? 'stamp')
    }
  }, [awardable, eventKey])

  if (awardable.length === 0) {
    return (
      <section className="rounded-3xl bg-white p-5 shadow-sm">
        <h2 className="font-black">できたことをほめる</h2>
        <p className="mt-2 text-sm text-ink/60">わたせるルールがオフです。</p>
      </section>
    )
  }

  return (
    <form
      className="rounded-3xl bg-white p-5 shadow-sm"
      onSubmit={(event) => {
        event.preventDefault()
        onGive(note, eventKey).then(() => setNote(''))
      }}
    >
      <h2 className="font-black">できたことをほめる</h2>
      <select
        value={eventKey}
        onChange={(e) => setEventKey(e.target.value)}
        className="mt-2 w-full rounded-2xl bg-cream px-3 py-2"
      >
        {awardable.map((rule) => (
          <option key={rule.event_key} value={rule.event_key}>
            {rule.label} ・ {rule.points}点
          </option>
        ))}
      </select>
      <input
        value={note}
        onChange={(e) => setNote(e.target.value)}
        maxLength={80}
        placeholder="さんすうのテスト、片付け…"
        className="mt-2 w-full rounded-2xl bg-cream px-3 py-2"
      />
      <button type="submit" className="mt-3 rounded-full bg-sky px-5 py-2 text-sm font-black text-white">
        ポイントをわたす
      </button>
    </form>
  )
}

function RuleEditor({ rules, onSave }: { rules: PointRule[]; onSave: (rules: PointRule[]) => Promise<void> }) {
  const [draft, setDraft] = useState(rules)
  const [label, setLabel] = useState('')
  const [points, setPoints] = useState('5')

  useEffect(() => {
    setDraft(rules)
  }, [rules])

  function update(id: number, patch: Partial<PointRule>) {
    setDraft((rows) => rows.map((row) => (row.id === id ? { ...row, ...patch } : row)))
  }

  return (
    <section className="rounded-3xl bg-white p-5 shadow-sm">
      <h2 className="font-black">付与ルール</h2>
      <ul className="mt-3 space-y-3">
        {draft.map((rule) => (
          <li key={`${rule.id}-${rule.event_key}`} className="rounded-2xl bg-cream p-3">
            <p className="text-sm font-bold">{rule.label}</p>
            <div className="mt-2 flex items-center gap-2">
              <input
                type="number"
                min={0}
                max={999}
                value={rule.points}
                onChange={(e) => update(rule.id, { points: Number(e.target.value) })}
                className="w-20 rounded-xl bg-white px-2 py-1"
              />
              <span className="text-sm">点</span>
              <label className="ml-auto text-sm font-bold">
                <input
                  type="checkbox"
                  checked={rule.enabled}
                  onChange={(e) => update(rule.id, { enabled: e.target.checked })}
                  className="mr-1"
                />
                オン
              </label>
              {isCustomRule(rule) && (
                <button
                  type="button"
                  onClick={() => setDraft((rows) => rows.filter((row) => row.id !== rule.id))}
                  className="rounded-full bg-white px-3 py-1 text-xs font-bold text-coral"
                >
                  けす
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
      <div className="mt-3 flex gap-2">
        <input
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="あたらしいルール"
          className="flex-1 rounded-2xl bg-cream px-3 py-2 text-sm"
        />
        <input
          type="number"
          min={0}
          value={points}
          onChange={(e) => setPoints(e.target.value)}
          className="w-16 rounded-2xl bg-cream px-2 py-2 text-sm"
        />
      </div>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={() => {
            if (!label.trim()) return
            const custom = {
              id: -Date.now(),
              event_key: '',
              label: label.trim(),
              points: Number(points) || 0,
              enabled: true,
            }
            setDraft((rows) => [...rows, custom])
            setLabel('')
          }}
          className="rounded-full bg-cream px-4 py-2 text-sm font-bold"
        >
          ルールを足す
        </button>
        <button
          type="button"
          onClick={() => onSave(draft)}
          className="rounded-full bg-sky px-4 py-2 text-sm font-black text-white"
        >
          ほぞん
        </button>
      </div>
    </section>
  )
}

function RewardForm({ onCreate }: { onCreate: (name: string, cost: number) => Promise<void> }) {
  const [name, setName] = useState('')
  const [cost, setCost] = useState('20')
  return (
    <form
      className="rounded-3xl bg-white p-5 shadow-sm"
      onSubmit={(event) => {
        event.preventDefault()
        if (!name.trim()) return
        onCreate(name.trim(), Number(cost) || 1).then(() => {
          setName('')
          setCost('20')
        })
      }}
    >
      <h2 className="font-black">ごほうびを追加</h2>
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="ゲーム 15ふん"
        className="mt-2 w-full rounded-2xl bg-cream px-3 py-2"
      />
      <input
        type="number"
        min={1}
        value={cost}
        onChange={(e) => setCost(e.target.value)}
        className="mt-2 w-full rounded-2xl bg-cream px-3 py-2"
      />
      <button type="submit" className="mt-3 rounded-full bg-sky px-5 py-2 text-sm font-black text-white">
        ついか
      </button>
    </form>
  )
}
