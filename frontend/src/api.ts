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
