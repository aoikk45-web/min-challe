import { useEffect, useState } from 'react'
import {
  answerDrill,
  fetchDrill,
  fetchDrillHistory,
  startDrill,
  type DrillHistoryItem,
  type DrillKind,
  type DrillSession,
} from '../api'
import type { Role } from '../role'
import { Empty } from './PlanPage'

const MATH_KINDS: { kind: DrillKind; emoji: string }[] = [
  { kind: 'たしざん', emoji: '➕' },
  { kind: 'ひきざん', emoji: '➖' },
  { kind: 'かけざん', emoji: '✖️' },
  { kind: 'わりざん', emoji: '➗' },
]

const KOKUGO_KINDS: { kind: DrillKind; emoji: string }[] = [
  { kind: 'かんじのよみ', emoji: 'あ' },
  { kind: 'じゅくごのよみ', emoji: '語' },
]

function isKokugo(kind: string) {
  return kind === 'かんじのよみ' || kind === 'じゅくごのよみ'
}

export default function DrillPage({ role }: { role: Role }) {
  const [history, setHistory] = useState<DrillHistoryItem[]>([])
  const [session, setSession] = useState<DrillSession | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  async function reloadHistory() {
    const rows = await fetchDrillHistory(role)
    setHistory(rows)
    return rows
  }

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(false)
    fetchDrillHistory(role)
      .then((rows) => {
        if (!cancelled) setHistory(rows)
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

  async function openSession(id: number) {
    const next = await fetchDrill(role, id)
    setSession(next)
  }

  async function begin(kind: DrillKind) {
    const next = await startDrill(kind)
    setSession(next)
  }

  async function onAnswered(next: DrillSession) {
    setSession(next)
    if (next.status === 'finished') {
      await reloadHistory()
    }
  }

  function backToMenu() {
    setSession(null)
    reloadHistory().catch(() => setError(true))
  }

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

  if (session && role === 'child' && session.status === 'in_progress') {
    return <PlayView session={session} onAnswered={onAnswered} />
  }
  if (session && session.status === 'finished') {
    return <ResultView session={session} role={role} onAgain={role === 'child' ? backToMenu : () => setSession(null)} />
  }

  const inProgress = history.find((row) => row.status === 'in_progress')

  return (
    <div className="space-y-4">
      {role === 'child' && (
        <section className="rounded-3xl bg-white p-5 shadow-sm">
          <h2 className="text-xl font-black">10もん やってみよう</h2>
          {inProgress ? (
            <button
              type="button"
              onClick={() => openSession(inProgress.id)}
              className="mt-4 w-full rounded-full bg-sun py-3 text-base font-black"
            >
              つづける（{inProgress.kind}）
            </button>
          ) : (
            <div className="mt-4 space-y-4">
              <div>
                <p className="text-sm font-bold text-sky">さんすう</p>
                <ul className="mt-2 grid grid-cols-2 gap-3">
                  {MATH_KINDS.map((item) => (
                    <li key={item.kind}>
                      <KindButton item={item} onBegin={begin} />
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-sm font-bold text-sky">こくご</p>
                <ul className="mt-2 grid grid-cols-2 gap-3">
                  {KOKUGO_KINDS.map((item) => (
                    <li key={item.kind}>
                      <KindButton item={item} onBegin={begin} />
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </section>
      )}

      <HistoryList
        history={history.filter((row) => row.status === 'finished')}
        empty={role === 'child' ? 'まだ 1かいも やってないよ。' : 'まだ履歴がないよ。'}
        onOpen={(id) => openSession(id)}
      />
    </div>
  )
}

function KindButton({
  item,
  onBegin,
}: {
  item: { kind: DrillKind; emoji: string }
  onBegin: (kind: DrillKind) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onBegin(item.kind)}
      className="flex h-full w-full flex-col items-center rounded-3xl bg-cream py-4 font-black"
    >
      <span className="text-2xl">{item.emoji}</span>
      <span className="mt-1">{item.kind}</span>
    </button>
  )
}

function HistoryList({
  history,
  empty,
  onOpen,
}: {
  history: DrillHistoryItem[]
  empty: string
  onOpen: (id: number) => void
}) {
  if (history.length === 0) {
    return <Empty emoji="✨" title="ドリル" body={empty} />
  }
  return (
    <section className="rounded-3xl bg-white p-5 shadow-sm">
      <h2 className="text-lg font-black">りれき</h2>
      <ul className="mt-3 space-y-2">
        {history.map((row) => (
          <li key={row.id}>
            <button
              type="button"
              onClick={() => onOpen(row.id)}
              className="w-full rounded-2xl bg-cream px-4 py-3 text-left"
            >
              <p className="font-black">{row.kind}</p>
              <p className="text-xs text-ink/60">
                {row.correct_count ?? 0}/10もん ・ {row.duration_sec ?? 0}びょう
              </p>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}

function PlayView({
  session,
  onAnswered,
}: {
  session: DrillSession
  onAnswered: (next: DrillSession) => void
}) {
  const current = session.questions.find((q) => q.child_answer == null)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [feedback, setFeedback] = useState<DrillSession['questions'][0] | null>(null)
  const [pending, setPending] = useState<DrillSession | null>(null)

  async function submit() {
    if (!current || draft.trim() === '') return
    const kokugo = isKokugo(session.kind)
    if (!kokugo) {
      const value = Number(draft)
      if (Number.isNaN(value)) return
    }
    setBusy(true)
    try {
      const next = await answerDrill(session.id, current.id, kokugo ? draft.trim() : String(Number(draft)))
      const answered = next.questions.find((q) => q.id === current.id) ?? null
      setFeedback(answered)
      setPending(next)
      setDraft('')
    } finally {
      setBusy(false)
    }
  }

  function goNext() {
    if (pending) onAnswered(pending)
    setFeedback(null)
    setPending(null)
  }

  const shown = feedback ?? current
  if (!shown) return null

  return (
    <section className="rounded-3xl bg-white p-5 shadow-sm">
      <p className="text-sm font-bold text-sky">
        {session.kind} {shown.seq}/10
      </p>
      <p className="mt-6 text-center text-4xl font-black">{shown.prompt}</p>
      {feedback ? (
        <div className="mt-6 text-center">
          <p className={`text-2xl font-black ${feedback.is_correct ? 'text-mint' : 'text-coral'}`}>
            {feedback.is_correct ? 'せいかい！' : 'ざんねん'}
          </p>
          {!feedback.is_correct && <p className="mt-2 text-sm">こたえは {feedback.correct}</p>}
          <button type="button" onClick={goNext} className="mt-4 rounded-full bg-sun px-6 py-2 font-black">
            {pending?.status === 'finished' ? 'けっかをみる' : 'つぎ'}
          </button>
        </div>
      ) : (
        <form
          className="mt-6 space-y-3"
          onSubmit={(event) => {
            event.preventDefault()
            submit()
          }}
        >
          <input
            inputMode={isKokugo(session.kind) ? 'text' : 'numeric'}
            lang="ja"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="w-full rounded-2xl bg-cream px-4 py-3 text-center text-3xl font-black"
            aria-label="こたえ"
            autoFocus
            placeholder={isKokugo(session.kind) ? 'ひらがな' : ''}
          />
          <button
            type="submit"
            disabled={busy || draft.trim() === ''}
            className="w-full rounded-full bg-sun py-3 font-black disabled:opacity-50"
          >
            こたえる
          </button>
        </form>
      )}
    </section>
  )
}

function ResultView({
  session,
  role,
  onAgain,
}: {
  session: DrillSession
  role: Role
  onAgain: () => void
}) {
  const perfect = session.correct_count === 10
  return (
    <section className="space-y-4">
      <div className="rounded-3xl bg-white p-6 text-center shadow-sm">
        <p className="text-5xl">{perfect ? '🎉' : '✨'}</p>
        <h2 className="mt-3 text-2xl font-black">{perfect ? 'やったね！ぜんぶせいかい' : 'おつかれさま'}</h2>
        <p className="mt-2 font-black">
          {session.correct_count ?? 0}/10もん ・ {session.duration_sec ?? 0}びょう
        </p>
        {role === 'child' && (
          <button type="button" onClick={onAgain} className="mt-5 rounded-full bg-sun px-6 py-3 font-black">
            もういっかい
          </button>
        )}
        {role === 'parent' && (
          <button type="button" onClick={onAgain} className="mt-5 rounded-full bg-cream px-6 py-3 font-black">
            りれきにもどる
          </button>
        )}
      </div>
      <ul className="space-y-2 rounded-3xl bg-white p-5 shadow-sm">
        {session.questions.map((q) => (
          <li key={q.id} className="flex justify-between text-sm font-bold">
            <span>
              {q.seq}. {q.prompt}
            </span>
            <span className={q.is_correct ? 'text-mint' : 'text-coral'}>
              {q.is_correct ? '○' : `× ${q.correct}`}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
