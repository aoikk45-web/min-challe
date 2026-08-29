import { useEffect, useState } from 'react'
import {
  answerDrill,
  fetchDrill,
  fetchDrillHistory,
  fetchDrillProgress,
  startDrill,
  type DrillHistoryItem,
  type DrillKind,
  type DrillProgress,
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

function progressFor(progress: DrillProgress[], kind: string) {
  return progress.find((row) => row.kind === kind)
}

const CHICKEN_STAGES = ['🐣', '🐤', '🐥', '🐔', '🐓'] as const

function chickenGrowth(step: number) {
  const level = Math.min(Math.max(step, 1), 100)
  const stageIdx = Math.min(
    CHICKEN_STAGES.length - 1,
    Math.floor(((level - 1) / 99) * (CHICKEN_STAGES.length - 1)),
  )
  const scale = 0.8 + ((level - 1) / 99) * 0.55
  return { level, icon: CHICKEN_STAGES[stageIdx], scale }
}

function LevelBadge({
  step,
  streak = 0,
  needed = 5,
  compact = false,
}: {
  step: number
  streak?: number
  needed?: number
  compact?: boolean
}) {
  const { level, icon, scale } = chickenGrowth(step)
  const filled = Math.min(Math.max(streak, 0), needed)
  const empty = Math.max(0, needed - filled)
  return (
    <div className={`${compact ? 'mt-1' : 'mt-2'} flex flex-col items-center gap-0.5`}>
      <p className={`flex items-center gap-1 font-black ${compact ? 'text-xs' : 'text-sm'}`}>
        <span
          className={`inline-block leading-none ${compact ? 'text-base' : 'text-xl'}`}
          style={{ transform: `scale(${scale})` }}
        >
          {icon}
        </span>
        <span>レベル{level}</span>
      </p>
      <p className={`${compact ? 'text-xs' : 'text-sm'} tracking-tight text-sun`} aria-label={`レベルアップまで ${filled}/${needed}`}>
        {'★'.repeat(filled)}
        {'☆'.repeat(empty)}
      </p>
    </div>
  )
}

export default function DrillPage({ role }: { role: Role }) {
  const [history, setHistory] = useState<DrillHistoryItem[]>([])
  const [progress, setProgress] = useState<DrillProgress[]>([])
  const [session, setSession] = useState<DrillSession | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  async function reloadHistory() {
    const rows = await fetchDrillHistory(role)
    setHistory(rows)
    return rows
  }

  async function reloadProgress() {
    const rows = await fetchDrillProgress(role)
    setProgress(rows)
    return rows
  }

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(false)
    Promise.allSettled([fetchDrillHistory(role), fetchDrillProgress(role)])
      .then(([historyResult, progressResult]) => {
        if (cancelled) return
        if (historyResult.status === 'fulfilled') {
          setHistory(historyResult.value)
        } else {
          setError(true)
        }
        if (progressResult.status === 'fulfilled') {
          setProgress(progressResult.value)
        }
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
      if (!isKokugo(next.kind)) {
        await reloadProgress()
      }
    }
  }

  function backToMenu() {
    setSession(null)
    Promise.all([reloadHistory(), reloadProgress()]).catch(() => setError(true))
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
                      <KindButton item={item} prog={progressFor(progress, item.kind)} onBegin={begin} />
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

      {role === 'parent' && progress.length > 0 && (
        <section className="rounded-3xl bg-white p-5 shadow-sm">
          <h2 className="text-lg font-black">さんすうのレベル</h2>
          <ul className="mt-3 space-y-2 text-sm font-bold">
            {progress.map((row) => (
              <li key={row.kind} className="rounded-2xl bg-cream px-4 py-3">
                <p>{row.kind}</p>
                <LevelBadge step={row.step} streak={row.perfect_streak} needed={row.perfect_needed} compact />
              </li>
            ))}
          </ul>
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
  prog,
  onBegin,
}: {
  item: { kind: DrillKind; emoji: string }
  prog?: DrillProgress
  onBegin: (kind: DrillKind) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onBegin(item.kind)}
      className="flex h-full w-full flex-col items-center rounded-3xl bg-cream px-2 py-4 font-black"
    >
      <span className="text-2xl">{item.emoji}</span>
      <span className="mt-1">{item.kind}</span>
      {prog && <LevelBadge step={prog.step} streak={prog.perfect_streak} needed={prog.perfect_needed} compact />}
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
                {row.step != null ? `レベル${row.step} ・ ` : ''}
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
      {session.step != null && (
        <LevelBadge
          step={session.step}
          streak={session.perfect_streak ?? 0}
          needed={session.perfect_needed}
        />
      )}
      <p className={`mt-6 text-center font-black ${shown.prompt.includes('？') ? 'text-xl leading-relaxed' : 'text-4xl'}`}>
        {shown.prompt}
      </p>
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
        <p className="text-5xl">{session.step_up ? '🚀' : perfect ? '🎉' : '✨'}</p>
        <h2 className="mt-3 text-2xl font-black">
          {session.step_up ? 'レベルアップ！' : perfect ? 'やったね！ぜんぶせいかい' : 'おつかれさま'}
        </h2>
        {session.step != null && (
          <div className="mt-3 flex justify-center">
            <LevelBadge
              step={session.step_up ? session.step + 1 : session.step}
              streak={session.step_up ? 0 : (session.perfect_streak ?? 0)}
              needed={session.perfect_needed}
            />
          </div>
        )}
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
          <li key={q.id} className="flex items-start justify-between gap-3 text-sm font-bold">
            <span className="min-w-0 break-words">
              {q.seq}. {q.prompt}
            </span>
            <span className={`shrink-0 ${q.is_correct ? 'text-mint' : 'text-coral'}`}>
              {q.is_correct ? '○' : `× ${q.correct}`}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
