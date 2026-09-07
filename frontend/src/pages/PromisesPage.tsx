import { useCallback, useState } from 'react'
import {
  createPromiseItem,
  deletePromiseItem,
  fetchPromises,
  setPromiseCheck,
  updatePromiseItem,
  type PromiseDay,
  type PromiseItem,
} from '../api'
import type { Role } from '../role'
import { usePointsRefresh } from '../pointsRefresh'

export default function PromisesPage({ role }: { role: Role }) {
  const [day, setDay] = useState<PromiseDay | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [message, setMessage] = useState('')

  const reload = useCallback(async () => {
    const next = await fetchPromises(role)
    setDay(next)
    if (next.deducted_total > 0) {
      setMessage(`きのうの おおやくそくで ${next.deducted_total}点 へったよ`)
    }
  }, [role])

  const load = useCallback(() => {
    setLoading(true)
    setError(false)
    reload()
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [reload])

  usePointsRefresh(load, () => {
    reload().catch(() => setError(true))
  })

  if (loading) {
    return <p className="rounded-2xl bg-white p-6 text-center shadow-sm">ちょっとまってね…</p>
  }
  if (error || !day) {
    return (
      <p className="rounded-2xl bg-white p-6 text-center text-coral shadow-sm">
        つながらなかったよ。もういちど開いてみてね。
      </p>
    )
  }

  return (
    <div className="space-y-4">
      <section className="rounded-3xl bg-white p-5 shadow-sm">
        <h2 className="text-lg font-black">毎日おおやくそく</h2>
        <p className="mt-1 text-sm text-ink/60">
          {role === 'child'
            ? 'できたものに チェックしてね。わすれたら ポイントが へるよ。'
            : '項目と できなかったときの 減点を せっていできます。'}
        </p>
        {message && <p className="mt-3 text-sm font-bold text-coral">{message}</p>}
      </section>

      {role === 'parent' && (
        <PromiseForm
          onCreate={async (name, penalty) => {
            try {
              setMessage('')
              await createPromiseItem({ name, penalty })
              await reload()
              setMessage(`「${name}」を ついかしたよ`)
            } catch {
              setMessage('ついか できなかったよ')
            }
          }}
        />
      )}

      <ul className="space-y-2">
        {day.items.length === 0 && (
          <li className="rounded-3xl bg-white p-5 text-sm text-ink/60 shadow-sm">
            {role === 'parent' ? 'まだ項目がありません。上から追加できます。' : 'まだ やくそくが ないよ。'}
          </li>
        )}
        {day.items.map((item) => (
          <li key={item.id} className="rounded-3xl bg-white p-4 shadow-sm">
            {role === 'child' ? (
              <ChildCheckRow
                item={item}
                onToggle={async (checked) => {
                  try {
                    setMessage('')
                    await setPromiseCheck(item.id, checked)
                    await reload()
                  } catch {
                    setMessage('うまくいかなかったよ')
                  }
                }}
              />
            ) : (
              <ParentItemRow
                item={item}
                onToggle={async (enabled) => {
                  await updatePromiseItem(item.id, { enabled })
                  await reload()
                }}
                onSave={async (name, penalty) => {
                  await updatePromiseItem(item.id, { name, penalty })
                  await reload()
                }}
                onDelete={async () => {
                  if (!window.confirm('このやくそくを消しますか？')) return
                  await deletePromiseItem(item.id)
                  await reload()
                }}
              />
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

function ChildCheckRow({
  item,
  onToggle,
}: {
  item: PromiseItem
  onToggle: (checked: boolean) => void
}) {
  return (
    <label className="flex cursor-pointer items-center gap-3">
      <input
        type="checkbox"
        checked={item.checked}
        onChange={(e) => onToggle(e.target.checked)}
        className="h-6 w-6 accent-sun"
      />
      <span className="flex-1">
        <span className="font-black">{item.name}</span>
        <span className="mt-0.5 block text-xs text-ink/50">できなかったら −{item.penalty}点</span>
      </span>
    </label>
  )
}

function ParentItemRow({
  item,
  onToggle,
  onSave,
  onDelete,
}: {
  item: PromiseItem
  onToggle: (enabled: boolean) => void
  onSave: (name: string, penalty: number) => Promise<void>
  onDelete: () => void
}) {
  const [name, setName] = useState(item.name)
  const [penalty, setPenalty] = useState(String(item.penalty))

  return (
    <div className="space-y-2">
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="w-full rounded-2xl bg-cream px-3 py-2 font-bold"
      />
      <label className="flex items-center gap-2 text-xs font-bold text-ink/60">
        減点
        <input
          type="number"
          min={1}
          max={999}
          value={penalty}
          onChange={(e) => setPenalty(e.target.value)}
          className="w-20 rounded-xl bg-cream px-2 py-1 text-sm text-ink"
        />
        点
      </label>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => onSave(name.trim() || item.name, Math.max(1, Math.min(999, Number(penalty) || 1)))}
          className="rounded-full bg-sky px-3 py-1 text-xs font-black text-white"
        >
          ほぞん
        </button>
        <button
          type="button"
          onClick={() => onToggle(!item.enabled)}
          className="rounded-full bg-cream px-3 py-1 text-xs font-bold"
        >
          {item.enabled ? 'オフ' : 'オン'}
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="rounded-full bg-cream px-3 py-1 text-xs font-bold text-coral"
        >
          けす
        </button>
      </div>
      {!item.enabled && <p className="text-xs text-ink/50">オフ中（子どもには出ません）</p>}
    </div>
  )
}

function PromiseForm({ onCreate }: { onCreate: (name: string, penalty: number) => Promise<void> }) {
  const [name, setName] = useState('')
  const [penalty, setPenalty] = useState('5')
  const [busy, setBusy] = useState(false)
  return (
    <form
      className="rounded-3xl bg-white p-5 shadow-sm"
      onSubmit={(event) => {
        event.preventDefault()
        const trimmed = name.trim()
        const points = Math.max(1, Math.min(999, Number(penalty) || 1))
        if (!trimmed || busy) return
        setBusy(true)
        onCreate(trimmed, points)
          .then(() => {
            setName('')
            setPenalty('5')
          })
          .finally(() => setBusy(false))
      }}
    >
      <p className="text-sm font-black">やくそくを追加</p>
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="はをみがく"
        maxLength={80}
        required
        className="mt-2 w-full rounded-2xl bg-cream px-3 py-2"
      />
      <label className="mt-2 block text-xs font-bold text-ink/60">できなかったときの減点</label>
      <input
        type="number"
        min={1}
        max={999}
        value={penalty}
        onChange={(e) => setPenalty(e.target.value)}
        className="mt-1 w-full rounded-2xl bg-cream px-3 py-2"
      />
      <button
        type="submit"
        disabled={busy || !name.trim()}
        className="mt-3 rounded-full bg-sky px-5 py-2 text-sm font-black text-white disabled:bg-ink/20"
      >
        {busy ? 'ちょっとまって…' : 'ついか'}
      </button>
    </form>
  )
}
