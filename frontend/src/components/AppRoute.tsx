import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'
import { useGuestExperiment } from '../context/GuestExperimentContext'
import { useLocale } from '../context/LocaleContext'

export function AppRoute() {
  const { isAuthenticated, isLoading } = useAuth()
  const { isBootstrapLoading, guestLocalDiary, guestOnboardingCompleted } = useGuestExperiment()
  const { t } = useLocale()
  const location = useLocation()

  if (isLoading || isBootstrapLoading) {
    return <p className="muted">{t('common.loading')}</p>
  }

  if (isAuthenticated) {
    return <Outlet />
  }

  if (!guestLocalDiary) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  const onOnboarding = location.pathname === '/onboarding'
  if (!guestOnboardingCompleted && !onOnboarding) {
    return <Navigate to="/onboarding" replace />
  }

  return <Outlet />
}

export function AccountRoute() {
  const { isAuthenticated, isLoading } = useAuth()
  const { guestLocalDiary, isBootstrapLoading } = useGuestExperiment()
  const { t } = useLocale()
  const location = useLocation()

  if (isLoading || isBootstrapLoading) {
    return <p className="muted">{t('common.loading')}</p>
  }

  if (isAuthenticated) {
    return <Outlet />
  }

  if (guestLocalDiary) {
    return <Outlet />
  }

  return <Navigate to="/login" replace state={{ from: location }} />
}

/** Plans and checkout are for allowlisted testers only (GP-15). */
export function BillingOnly() {
  const { user, isLoading } = useAuth()
  const { t } = useLocale()

  if (isLoading) {
    return <p className="muted">{t('common.loading')}</p>
  }

  return user?.features?.billing ? <Outlet /> : <Navigate to="/" replace />
}

/** Account-backed settings have nothing to show in the local guest diary. */
export function RegisteredOnly() {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <Outlet /> : <Navigate to="/settings" replace />
}
