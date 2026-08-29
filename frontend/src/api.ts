import { useEffect, useState } from 'react'
import type { Role } from './role'

export type Member = {
  id: number
  display_name: string
  role: string
  grade: number | null
  avatar: string
}

export type Household = {
  id: number
  name: string
  child: Member
  parent: Member
}

export type StudyPlan = {
  id: number
  plan_date: string
  subject: string
  title: string
  minutes: number
  completed_at: string | null
}

export type PlanBody = {
  plan_date: string
  subject: string
  title: string
  minutes: number
}

export function todayJstISO(): string {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Tokyo' })
}

export function formatPlanDay(iso: string): string {
  const d = new Date(`${iso}T00:00:00+09:00`)
  const week = ['日', '月', '火', '水', '木', '金', '土'][d.getDay()]
  return `${d.getMonth() + 1}/${d.getDate()}（${week}）`
}

async function readJson<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error('request failed')
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export function usePlans(role: Role) {
  const [plans, setPlans] = useState<StudyPlan[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)
  const reload = () => setTick((n) => n + 1)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fetch(`/api/plans?role=${role}`)
      .then((res) => readJson<StudyPlan[]>(res))
      .then((json) => {
        if (!cancelled) setPlans(json)
      })
      .catch(() => {
        if (!cancelled) setError('load failed')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [role, tick])

  return { plans, error, loading, reload }
}

export function createPlan(role: Role, body: PlanBody) {
  return fetch(`/api/plans?role=${role}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then((res) => readJson<StudyPlan>(res))
}

export function updatePlan(role: Role, id: number, body: Partial<PlanBody>) {
  return fetch(`/api/plans/${id}?role=${role}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then((res) => readJson<StudyPlan>(res))
}

export function deletePlan(role: Role, id: number) {
  return fetch(`/api/plans/${id}?role=${role}`, { method: 'DELETE' }).then((res) => {
    if (!res.ok) throw new Error('request failed')
  })
}

export function completePlan(role: Role, id: number) {
  return fetch(`/api/plans/${id}/complete?role=${role}`, { method: 'POST' }).then((res) =>
    readJson<StudyPlan>(res),
  )
}

export type DrillKind =
  | 'たしざん'
  | 'ひきざん'
  | 'かけざん'
  | 'わりざん'
  | 'かんじのよみ'
  | 'じゅくごのよみ'

export type DrillQuestion = {
  id: number
  seq: number
  prompt: string
  child_answer: string | null
  is_correct: boolean | null
  correct: string | null
}

export type DrillSession = {
  id: number
  kind: string
  grade: number
  status: 'in_progress' | 'finished'
  correct_count: number | null
  duration_sec: number | null
  started_at: string
  finished_at: string | null
  questions: DrillQuestion[]
}

export type DrillHistoryItem = Omit<DrillSession, 'questions'>

export function startDrill(kind: DrillKind) {
  return fetch('/api/drills/start?role=child', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kind }),
  }).then((res) => readJson<DrillSession>(res))
}

export function fetchDrill(role: Role, id: number) {
  return fetch(`/api/drills/${id}?role=${role}`).then((res) => readJson<DrillSession>(res))
}

export function answerDrill(sessionId: number, questionId: number, answer: string) {
  return fetch(`/api/drills/${sessionId}/answer?role=child`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question_id: questionId, answer }),
  }).then((res) => readJson<DrillSession>(res))
}

export function fetchDrillHistory(role: Role) {
  return fetch(`/api/drills/history?role=${role}`).then((res) => readJson<DrillHistoryItem[]>(res))
}

export type PointRule = {
  id: number
  event_key: string
  label: string
  points: number
  enabled: boolean
}

export type Reward = {
  id: number
  name: string
  cost: number
  enabled: boolean
}

export type LedgerEntry = {
  id: number
  delta: number
  reason: string
  event_key: string
  created_at: string
}

export type PointSummary = {
  balance: number
  progress: number
  next_reward: { id: number; name: string; cost: number; remaining: number } | null
}

export function fetchPointSummary(role: Role) {
  return fetch(`/api/points/summary?role=${role}`).then((res) => readJson<PointSummary>(res))
}

export function fetchLedger(role: Role) {
  return fetch(`/api/points/ledger?role=${role}`).then((res) => readJson<LedgerEntry[]>(res))
}

export function fetchRules(role: Role) {
  return fetch(`/api/points/rules?role=${role}`).then((res) => readJson<PointRule[]>(res))
}

export function saveRules(rules: Array<Partial<PointRule> & Pick<PointRule, 'label' | 'points' | 'enabled'>>) {
  const payload = rules.map((rule) => {
    const body: Record<string, unknown> = {
      label: rule.label,
      points: rule.points,
      enabled: rule.enabled,
    }
    if (rule.id && rule.id > 0) body.id = rule.id
    if (rule.event_key) body.event_key = rule.event_key
    return body
  })
  return fetch('/api/points/rules?role=parent', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }).then((res) => readJson<PointRule[]>(res))
}

export function fetchRewards(role: Role) {
  return fetch(`/api/points/rewards?role=${role}`).then((res) => readJson<Reward[]>(res))
}

export function createReward(body: { name: string; cost: number }) {
  return fetch('/api/points/rewards?role=parent', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then((res) => readJson<Reward>(res))
}

export function updateReward(id: number, body: Partial<Pick<Reward, 'name' | 'cost' | 'enabled'>>) {
  return fetch(`/api/points/rewards/${id}?role=parent`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then((res) => readJson<Reward>(res))
}

export function deleteReward(id: number) {
  return fetch(`/api/points/rewards/${id}?role=parent`, { method: 'DELETE' }).then((res) => {
    if (!res.ok) throw new Error('request failed')
  })
}

export async function redeemReward(id: number) {
  const res = await fetch(`/api/points/rewards/${id}/redeem?role=child`, { method: 'POST' })
  if (res.status === 400) {
    const body = (await res.json()) as { detail?: string }
    throw new Error(typeof body.detail === 'string' ? body.detail : 'request failed')
  }
  if (!res.ok) throw new Error('request failed')
  return (await res.json()) as PointSummary
}

export async function giveStamp(note: string, eventKey = 'stamp') {
  const res = await fetch('/api/points/stamp?role=parent', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ note, event_key: eventKey }),
  })
  if (res.status === 400) {
    const body = (await res.json()) as { detail?: string }
    throw new Error(typeof body.detail === 'string' ? body.detail : 'request failed')
  }
  if (!res.ok) throw new Error('request failed')
  return (await res.json()) as PointSummary
}

export type AlbumKind = 'plan' | 'drill' | 'redeem' | 'stamp' | 'memo'

export type AlbumEntry = {
  id: number
  kind: AlbumKind
  title: string
  body: string
  stamp: string
  created_at: string
}

export function formatAlbumAt(iso: string): string {
  const aware = iso.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(iso) ? iso : `${iso}+09:00`
  const d = new Date(aware)
  return d.toLocaleString('ja-JP', {
    timeZone: 'Asia/Tokyo',
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function fetchAlbum(role: Role) {
  return fetch(`/api/album?role=${role}`).then((res) => readJson<AlbumEntry[]>(res))
}

export function addAlbumMemo(title: string, body: string) {
  return fetch('/api/album?role=parent', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, body }),
  }).then((res) => readJson<AlbumEntry>(res))
}

export function useHousehold(role: Role) {
  const [data, setData] = useState<Household | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fetch(`/api/household?role=${role}`)
      .then(async (res) => {
        if (!res.ok) throw new Error('load failed')
        return (await res.json()) as Household
      })
      .then((json) => {
        if (!cancelled) setData(json)
      })
      .catch(() => {
        if (!cancelled) setError('load failed')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [role])

  return { data, error, loading }
}
