import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

export const POINTS_UPDATED_EVENT = 'minchalle:points-updated'

export function notifyPointsUpdated() {
  window.dispatchEvent(new Event(POINTS_UPDATED_EVENT))
}

export function usePointsRefresh(onRefresh: () => void, onSilentRefresh?: () => void) {
  const location = useLocation()

  useEffect(() => {
    onRefresh()
  }, [location.pathname, onRefresh])

  useEffect(() => {
    const handler = () => (onSilentRefresh ?? onRefresh)()
    window.addEventListener(POINTS_UPDATED_EVENT, handler)
    return () => window.removeEventListener(POINTS_UPDATED_EVENT, handler)
  }, [onRefresh, onSilentRefresh])
}
