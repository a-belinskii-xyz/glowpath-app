import { Navigate } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'
import { useGuestExperiment } from '../context/GuestExperimentContext'
import { useLocale } from '../context/LocaleContext'
import { isTelegramMiniApp } from '../platform/telegram'
import { EntriesPage } from './EntriesPage'
import { LoginPage } from './LoginPage'

export function HomePage() {
  const { isAuthenticated, isLoading } = useAuth()
  const { isBootstrapLoading, guestLocalDiary } = useGuestExperiment()
  const { t } = useLocale()

  if (isLoading || isBootstrapLoading) {
    return (
      <section className="page">
        <p className="muted">{t('common.loading')}</p>
      </section>
    )
  }

  if (isAuthenticated || guestLocalDiary) {
    return <EntriesPage />
  }

  if (isTelegramMiniApp()) {
    return <Navigate to="/login" replace />
  }

  return <LoginPage />
}
