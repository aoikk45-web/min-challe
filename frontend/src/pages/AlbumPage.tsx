import { useEffect, useState, type FormEvent } from 'react'
import { addAlbumMemo, fetchAlbum, formatAlbumAt, type AlbumEntry } from '../api'
import type { Role } from '../role'
import { Empty } from './PlanPage'

export default function AlbumPage({ role }: { role: Role }) {
  const [entries, setEntries] = useState<AlbumEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  async function reload() {
    setEntries(await fetchAlbum(role))
  }

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(false)
    fetchAlbum(role)
      .then((rows) => {
        if (!cancelled) setEntries(rows)
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
  if (error) {
    return (
      <p className="rounded-2xl bg-white p-6 text-center text-coral shadow-sm">
        つながらなかったよ。もういちど開いてみてね。
      </p>
    )
  }

  return (
    <div className="space-y-4">
      {role === 'parent' && <MemoForm onSaved={reload} />}
      {entries.length === 0 ? (
        <Empty emoji="📔" title="成長アルバム" body="最初のページは、これからつくられるよ" />
      ) : (
        <ul className="space-y-3">
          {entries.map((entry) => (
            <li key={entry.id}>
              <article className="rounded-3xl bg-white p-5 shadow-sm">
                <div className="flex items-start gap-3">
                  <p className="text-3xl leading-none">{entry.stamp}</p>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-bold text-sky">{formatAlbumAt(entry.created_at)}</p>
                    <h2 className="mt-1 text-lg font-black">{entry.title}</h2>
                    {entry.body && <p className="mt-1 text-sm leading-relaxed text-ink/70">{entry.body}</p>}
                  </div>
                </div>
              </article>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function MemoForm({ onSaved }: { onSaved: () => Promise<void> }) {
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!title.trim()) return
    setBusy(true)
    setFailed(false)
    try {
      await addAlbumMemo(title, body)
      setTitle('')
      setBody('')
      await onSaved()
    } catch {
      setFailed(true)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="rounded-3xl bg-white p-5 shadow-sm">
      <h2 className="font-black">思い出メモ</h2>
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        maxLength={80}
        required
        placeholder="がんばってるね"
        className="mt-2 w-full rounded-2xl bg-cream px-3 py-2"
      />
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        maxLength={200}
        rows={3}
        placeholder="短いひとこと"
        className="mt-2 w-full rounded-2xl bg-cream px-3 py-2"
      />
      {failed && <p className="mt-2 text-sm text-coral">うまくいかなかったよ。もういちどためしてね。</p>}
      <button
        type="submit"
        disabled={busy}
        className="mt-3 rounded-full bg-sky px-5 py-2 text-sm font-black text-white disabled:opacity-50"
      >
        のこす
      </button>
    </form>
  )
}
