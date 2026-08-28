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
