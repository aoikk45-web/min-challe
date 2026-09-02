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
import { notifyPointsUpdated } from '../pointsRefresh'
import { Empty } from './PlanPage'

function drillImageSrc(url: string): string {
  if (url.startsWith('/shakai/symbols/')) {
    return url.replace(/\.svg$/, '.png')
  }
  return url
}

const MATH_KINDS: { kind: DrillKind; emoji: string }[] = [
  { kind: 'たしざん', emoji: '➕' },
  { kind: 'ひきざん', emoji: '➖' },
  { kind: 'かけざん', emoji: '✖️' },
  { kind: 'わりざん', emoji: '➗' },
]

const KOKUGO_KINDS: { kind: DrillKind; emoji: string }[] = [
  { kind: 'かんじのよみ', emoji: 'あ' },
  { kind: 'じゅくごのよみ', emoji: '語' },
  { kind: 'おはなしのどくかい', emoji: '📖' },
]

const SHAKAI_KINDS: { kind: DrillKind; emoji: string }[] = [
  { kind: 'とどうふけん', emoji: '🗾' },
  { kind: 'にほんのちり', emoji: '🏔️' },
  { kind: 'ちずきごう', emoji: '📍' },
  { kind: 'けんのかたち', emoji: '🗺️' },
]

const RIKA_KINDS: { kind: DrillKind; emoji: string }[] = [
  { kind: 'いきもののせいかつ', emoji: '🐛' },
  { kind: 'じしゃくとでんき', emoji: '🔋' },
  { kind: 'たいようとかげ', emoji: '☀️' },
  { kind: 'ひかりとおと', emoji: '🔔' },
  { kind: 'てんきとみず', emoji: '🌧️' },
]

type SubjectId = 'sansuu' | 'kokugo' | 'rika' | 'shakai'

const SUBJECT_GROUPS: {
  id: SubjectId
  label: string
  emoji: string
  kinds: { kind: DrillKind; emoji: string }[]
}[] = [
  { id: 'sansuu', label: 'さんすう', emoji: '🔢', kinds: MATH_KINDS },
  { id: 'kokugo', label: 'こくご', emoji: '📚', kinds: KOKUGO_KINDS },
  { id: 'rika', label: 'りか', emoji: '🔬', kinds: RIKA_KINDS },
  { id: 'shakai', label: 'しゃかい', emoji: '🗾', kinds: SHAKAI_KINDS },
]

function isKokugo(kind: string) {
  return kind === 'かんじのよみ' || kind === 'じゅくごのよみ'
}

function isDokkai(kind: string) {
  return kind === 'おはなしのどくかい'
}

function isShakai(kind: string) {
  return SHAKAI_KINDS.some((item) => item.kind === kind)
}

function isRika(kind: string) {
  return RIKA_KINDS.some((item) => item.kind === kind)
}

function isStageKind(kind: string) {
  return isShakai(kind) || isDokkai(kind) || isRika(kind)
}

function isChoiceDrill(kind: string) {
  return isKokugo(kind) || isShakai(kind) || isDokkai(kind) || isRika(kind)
}

function progressFor(progress: DrillProgress[], kind: string) {
  return progress.find((row) => row.kind === kind)
}

const CHICKEN_STAGES = ['🐣', '🐤', '🐥', '🐔', '🐓'] as const

function chickenGrowth(step: number, maxStep = 100) {
  const level = Math.min(Math.max(step, 1), maxStep)
  const span = Math.max(maxStep - 1, 1)
  const stageIdx = Math.min(
    CHICKEN_STAGES.length - 1,
    Math.floor(((level - 1) / span) * (CHICKEN_STAGES.length - 1)),
  )
  const scale = 0.8 + ((level - 1) / span) * 0.55
  return { level, icon: CHICKEN_STAGES[stageIdx], scale }
}

function LevelBadge({
  step,
  streak = 0,
  needed = 5,
  compact = false,
  maxStep = 100,
  stage = false,
}: {
  step: number
  streak?: number
  needed?: number
  compact?: boolean
  maxStep?: number
  stage?: boolean
}) {
  const { level, icon, scale } = chickenGrowth(step, maxStep)
  const filled = Math.min(Math.max(streak, 0), needed)
  const empty = Math.max(0, needed - filled)
  const stepText = stage ? `ステージ${level}/${maxStep}` : `レベル${level}/${maxStep}`
  const goalText = stage ? 'ステージアップまで' : 'レベルアップまで'
  return (
    <div className={`${compact ? 'mt-1' : 'mt-2'} flex flex-col items-center gap-0.5`}>
      <p className={`flex items-center gap-1 font-black ${compact ? 'text-xs' : 'text-sm'}`}>
        <span
          className={`inline-block leading-none ${compact ? 'text-base' : 'text-xl'}`}
          style={{ transform: `scale(${scale})` }}
        >
          {icon}
        </span>
        <span>{stepText}</span>
      </p>
      <p className={`${compact ? 'text-xs' : 'text-sm'} tracking-tight text-sun`} aria-label={`${goalText} ${filled}/${needed}`}>
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
  const [openSubject, setOpenSubject] = useState<SubjectId | null>(null)

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
    try {
      const next = await fetchDrill(role, id)
      setSession(next)
    } catch {
      setSession(null)
      await reloadHistory()
      setError(true)
    }
  }

  async function begin(kind: DrillKind) {
    try {
      setOpenSubject(null)
      const next = await startDrill(kind)
      setSession(next)
    } catch {
      setError(true)
    }
  }

  async function onAnswered(next: DrillSession) {
    setSession(next)
    if (next.status === 'finished') {
      await reloadHistory()
      await reloadProgress()
      notifyPointsUpdated()
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
          {inProgress ? (
            <button
              type="button"
              onClick={() => openSession(inProgress.id)}
              className="w-full rounded-full bg-sun py-3 text-base font-black"
            >
              つづける（{inProgress.kind}）
            </button>
          ) : (
            <ul className="grid grid-cols-2 gap-3">
              {SUBJECT_GROUPS.map((subject) => (
                <li key={subject.id}>
                  <SubjectCard
                    subject={subject}
                    open={openSubject === subject.id}
                    onToggle={() =>
                      setOpenSubject((current) => (current === subject.id ? null : subject.id))
                    }
                    onClose={() => setOpenSubject(null)}
                    progress={progress}
                    onBegin={begin}
                  />
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {role === 'parent' && progress.length > 0 && (
        <section className="rounded-3xl bg-white p-5 shadow-sm">
          <h2 className="text-lg font-black">ドリルのレベル</h2>
          <ul className="mt-3 space-y-2 text-sm font-bold">
            {progress.map((row) => (
              <li key={row.kind} className="rounded-2xl bg-cream px-4 py-3">
                <p>{row.kind}</p>
                <LevelBadge
                  step={row.step}
                  streak={row.perfect_streak}
                  needed={row.perfect_needed}
                  maxStep={row.max_step}
                  stage={isStageKind(row.kind)}
                  compact
                />
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

function SubjectCard({
  subject,
  open,
  onToggle,
  onClose,
  progress,
  onBegin,
}: {
  subject: (typeof SUBJECT_GROUPS)[number]
  open: boolean
  onToggle: () => void
  onClose: () => void
  progress: DrillProgress[]
  onBegin: (kind: DrillKind) => void
}) {
  const panelVisible = open ? 'flex' : 'hidden'
  return (
    <div
      className="group relative"
      onMouseLeave={onClose}
    >
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className={`flex w-full flex-col items-center rounded-3xl px-2 py-5 font-black transition ${
          open ? 'bg-sun/40 ring-2 ring-sun' : 'bg-cream hover:bg-sun/20'
        }`}
      >
        <span className="text-3xl">{subject.emoji}</span>
        <span className="mt-2 text-lg">{subject.label}</span>
        <span className="mt-1 text-xs font-bold text-ink/50">
          {open ? 'とじる' : 'タップで えらぶ'}
        </span>
      </button>
      <ul
        className={`absolute top-full right-0 left-0 z-20 max-h-72 flex-col gap-2 overflow-y-auto rounded-2xl bg-white p-2 pt-2 shadow-lg ${panelVisible} md:group-hover:flex md:group-focus-within:flex`}
      >
        {subject.kinds.map((item) => (
          <li key={item.kind}>
            <KindButton
              item={item}
              prog={progressFor(progress, item.kind)}
              onBegin={onBegin}
              compact
            />
          </li>
        ))}
      </ul>
    </div>
  )
}

function KindButton({
  item,
  prog,
  onBegin,
  compact = false,
}: {
  item: { kind: DrillKind; emoji: string }
  prog?: DrillProgress
  onBegin: (kind: DrillKind) => void
  compact?: boolean
}) {
  const step = prog?.step ?? 1
  const streak = prog?.perfect_streak ?? 0
  const needed = prog?.perfect_needed ?? 5
  const stage = isStageKind(item.kind)
  const maxStep = prog?.max_step ?? (stage ? 6 : 100)
  return (
    <button
      type="button"
      onClick={() => onBegin(item.kind)}
      className={`flex h-full w-full flex-col items-center rounded-2xl bg-cream font-black ${
        compact ? 'px-2 py-3' : 'rounded-3xl px-2 py-4'
      }`}
    >
      <span className={compact ? 'text-xl' : 'text-2xl'}>{item.emoji}</span>
      <span className={`mt-1 text-center leading-tight ${compact ? 'text-xs' : 'text-sm'}`}>{item.kind}</span>
      <LevelBadge step={step} streak={streak} needed={needed} maxStep={maxStep} stage={stage} compact />
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
  const choiceDrill = isChoiceDrill(session.kind)
  const stage = isStageKind(session.kind)
  const total = session.questions.length

  async function submit(answer?: string) {
    if (!current) return
    const value = answer ?? draft
    if (value.trim() === '') return
    const kokugo = isKokugo(session.kind)
    if (!kokugo && !choiceDrill) {
      const num = Number(value)
      if (Number.isNaN(num)) return
    }
    setBusy(true)
    try {
      const next = await answerDrill(
        session.id,
        current.id,
        kokugo || choiceDrill ? value.trim() : String(Number(value)),
      )
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

  const promptLines = shown.prompt.split('\n')

  return (
    <section className="rounded-3xl bg-white p-5 shadow-sm">
      <p className="text-sm font-bold text-sky">
        {session.kind} {shown.seq}/{total}
      </p>
      <LevelBadge
        step={session.step ?? 1}
        streak={session.perfect_streak ?? 0}
        needed={session.perfect_needed}
        maxStep={session.max_step ?? (stage ? 6 : 100)}
        stage={stage}
      />
      {session.passage && (
        <div className="mt-4 rounded-2xl bg-cream px-4 py-3 text-left text-sm leading-relaxed">
          {session.passage_title && <p className="mb-2 font-black text-sky">{session.passage_title}</p>}
          <p className="whitespace-pre-wrap">{session.passage}</p>
        </div>
      )}
      {shown.image_url && (
        <div className="mt-4 flex justify-center">
          <img
            key={shown.image_url}
            src={drillImageSrc(shown.image_url)}
            alt=""
            className={`w-full max-w-md rounded-2xl border-2 border-sky/20 bg-white p-3 object-contain ${
              shown.image_url.startsWith('/shakai/maps/') ? 'max-h-72' : 'max-h-48'
            }`}
          />
        </div>
      )}
      <div
        className={`mt-6 text-center font-black ${
          choiceDrill ? 'text-base leading-relaxed sm:text-lg' : shown.prompt.includes('？') ? 'text-xl leading-relaxed' : 'text-4xl'
        }`}
      >
        {choiceDrill || shown.prompt.includes('？') ? (
          <p>{shown.prompt}</p>
        ) : (
          promptLines.map((line, idx) => (
            <p key={idx} className={idx > 0 ? 'mt-2' : ''}>
              {line}
            </p>
          ))
        )}
      </div>
      {feedback ? (
        <div className="mt-6 text-center">
          <p className={`text-2xl font-black ${feedback.is_correct ? 'text-mint' : 'text-coral'}`}>
            {feedback.is_correct ? 'せいかい！' : 'ざんねん'}
          </p>
          {!feedback.is_correct && (
            <>
              {feedback.child_answer && (
                <p className="mt-2 break-words text-sm">あなたのこたえ: {feedback.child_answer}</p>
              )}
              <p className="mt-2 break-words text-sm">こたえは {feedback.correct}</p>
            </>
          )}
          {feedback.explanation && (
            <p className="mt-2 break-words text-left text-sm leading-relaxed text-ink/80">{feedback.explanation}</p>
          )}
          <button type="button" onClick={goNext} className="mt-4 rounded-full bg-sun px-6 py-2 font-black">
            {pending?.status === 'finished' ? 'けっかをみる' : 'つぎ'}
          </button>
        </div>
      ) : choiceDrill && shown.choices ? (
        <div className="mt-6 grid grid-cols-2 gap-3">
          {shown.choices.map((choice) => (
            <button
              key={choice}
              type="button"
              disabled={busy}
              onClick={() => submit(choice)}
              className="rounded-2xl bg-cream px-3 py-4 text-base font-black disabled:opacity-50"
            >
              {choice}
            </button>
          ))}
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
  const total = session.questions.length
  const perfect = session.correct_count === total
  const stage = isStageKind(session.kind)
  const maxStep = session.max_step ?? (stage ? 6 : 100)
  return (
    <section className="space-y-4">
      <div className="rounded-3xl bg-white p-6 text-center shadow-sm">
        <p className="text-5xl">{session.step_up ? '🚀' : perfect ? '🎉' : '✨'}</p>
        <h2 className="mt-3 text-2xl font-black">
          {session.step_up ? (stage ? 'ステージアップ！' : 'レベルアップ！') : perfect ? 'やったね！ぜんぶせいかい' : 'おつかれさま'}
        </h2>
        {session.step != null && (
          <div className="mt-3 flex justify-center">
            <LevelBadge
              step={session.step_up ? session.step + 1 : session.step}
              streak={session.step_up ? 0 : (session.perfect_streak ?? 0)}
              needed={session.perfect_needed}
              maxStep={maxStep}
              stage={stage}
            />
          </div>
        )}
        <p className="mt-2 font-black">
          {session.correct_count ?? 0}/{total}もん ・ {session.duration_sec ?? 0}びょう
        </p>
        {role === 'child' && session.points_earned != null && session.points_earned > 0 && (
          <p className="mt-3 text-lg font-black text-sun">+{session.points_earned}点 もらえた！</p>
        )}
        {role === 'child' && session.points_earned === 0 && (
          <p className="mt-3 text-sm text-ink/60">ポイントは つかなかったよ（おうちの人のルールを確認してね）</p>
        )}
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
      <ul className="space-y-3 rounded-3xl bg-white p-5 shadow-sm">
        {session.questions.map((q) => (
          <li key={q.id} className="text-sm leading-relaxed">
            <p className="font-bold break-words">{q.seq}. {q.prompt}</p>
            <p className={`mt-1 font-black break-words ${q.is_correct ? 'text-mint' : 'text-coral'}`}>
              {q.is_correct ? '○' : `× ${q.correct}`}
            </p>
          </li>
        ))}
      </ul>
    </section>
  )
}
