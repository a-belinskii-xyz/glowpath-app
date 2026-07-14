import { Navigate, Outlet } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth()
  const { t } = useLocale()

  if (isLoading) {
    return <p className="muted">{t('common.loading')}</p>
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
