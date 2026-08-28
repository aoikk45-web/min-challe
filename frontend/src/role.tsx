import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'

export type Role = 'child' | 'parent'

type Ctx = { role: Role; setRole: (role: Role) => void }

const RoleContext = createContext<Ctx | null>(null)

export function RoleProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<Role>('child')
  const value = useMemo(() => ({ role, setRole }), [role])
  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>
}

export function useRole() {
  const ctx = useContext(RoleContext)
  if (!ctx) throw new Error('useRole outside provider')
  return ctx
}
