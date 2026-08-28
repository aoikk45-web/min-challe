import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { BookOpen, Home, Sparkles, Star, Trophy } from 'lucide-react'
import type { ReactNode } from 'react'
import { RoleProvider, useRole } from './role'
import { useHousehold } from './api'
import HomePage from './pages/HomePage'
import PlanPage from './pages/PlanPage'
import DrillPage from './pages/DrillPage'
import PointsPage from './pages/PointsPage'
import AlbumPage from './pages/AlbumPage'

function Shell() {
  const { role, setRole } = useRole()
  const { data, error, loading } = useHousehold(role)

  return (
    <div className="mx-auto flex min-h-svh max-w-lg flex-col bg-cream">
      <header className="flex items-center justify-between gap-3 px-4 pb-2 pt-4">
        <div>
          <p className="text-xs font-semibold tracking-wide text-coral">みんチャレ</p>
          <h1 className="text-lg font-bold">
            {data ? `${data.name}` : 'よみこみちゅう'}
          </h1>
        </div>
        <div className="flex rounded-full bg-white p-1 shadow-sm">
          <button
            type="button"
            onClick={() => setRole('child')}
            className={`rounded-full px-3 py-1.5 text-sm font-bold ${
              role === 'child' ? 'bg-sun text-ink' : 'text-ink/50'
            }`}
          >
            こども
          </button>
          <button
            type="button"
            onClick={() => setRole('parent')}
            className={`rounded-full px-3 py-1.5 text-sm font-bold ${
              role === 'parent' ? 'bg-sky text-white' : 'text-ink/50'
            }`}
          >
            おうちの人
          </button>
        </div>
      </header>

      <main className="flex-1 px-4 pb-28 pt-2">
        {loading && (
          <p className="rounded-2xl bg-white p-6 text-center shadow-sm">ちょっとまってね…</p>
        )}
        {error && (
          <p className="rounded-2xl bg-white p-6 text-center text-coral shadow-sm">
            つながらなかったよ。もういちど開いてみてね。
          </p>
        )}
        {data && (
          <Routes>
            <Route path="/" element={<HomePage household={data} role={role} />} />
            <Route path="/plan" element={<PlanPage role={role} />} />
            <Route path="/drill" element={<DrillPage role={role} />} />
            <Route path="/points" element={<PointsPage role={role} />} />
            <Route path="/album" element={<AlbumPage role={role} />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        )}
      </main>

      <nav className="fixed bottom-0 left-1/2 z-10 w-full max-w-lg -translate-x-1/2 border-t border-orange-100 bg-white/95 px-2 py-2 backdrop-blur">
        <ul className="grid grid-cols-5 gap-1 text-center text-[11px] font-bold">
          <NavItem to="/" icon={<Home size={22} />} label="ホーム" />
          <NavItem to="/plan" icon={<BookOpen size={22} />} label="けいかく" />
          <NavItem to="/drill" icon={<Sparkles size={22} />} label="ドリル" />
          <NavItem to="/points" icon={<Trophy size={22} />} label="ポイント" />
          <NavItem to="/album" icon={<Star size={22} />} label="アルバム" />
        </ul>
      </nav>
    </div>
  )
}

function NavItem({
  to,
  icon,
  label,
}: {
  to: string
  icon: ReactNode
  label: string
}) {
  return (
    <li>
      <NavLink
        to={to}
        end={to === '/'}
        className={({ isActive }) =>
          `flex flex-col items-center gap-0.5 rounded-2xl py-1 ${
            isActive ? 'bg-sun/80 text-ink' : 'text-ink/45'
          }`
        }
      >
        {icon}
        {label}
      </NavLink>
    </li>
  )
}

export default function App() {
  return (
    <RoleProvider>
      <Shell />
    </RoleProvider>
  )
}
