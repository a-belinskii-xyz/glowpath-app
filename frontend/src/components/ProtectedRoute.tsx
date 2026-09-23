import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { parseMoodEntrySource, setStoredMoodEntrySource } from '../lib/moodEntrySource'

export function ProtectedRoute() {
  const { isAuthenticated, isLoading, user } = useAuth()
  const { t } = useLocale()
  const location = useLocation()

  if (isLoading) {
    return <p className="muted">{t('common.loading')}</p>
  }

  if (!isAuthenticated) {
    const source = parseMoodEntrySource(new URLSearchParams(location.search).get('from'))
    if (source) {
      setStoredMoodEntrySource(source)
    }
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  const onOnboarding = location.pathname === '/onboarding'
  if (!user?.onboarding_completed && !onOnboarding) {
    return <Navigate to="/onboarding" replace />
  }

  return <Outlet />
}
