import { Navigate } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { EntriesPage } from './EntriesPage'

export function HomePage() {
  const { isAuthenticated, isLoading } = useAuth()
  const { t } = useLocale()

  if (isLoading) {
    return (
      <section className="page">
        <p className="muted">{t('common.loading')}</p>
      </section>
    )
  }

  if (isAuthenticated) {
    return <EntriesPage />
  }

  return <Navigate to="/login" replace />
}
