import { Link, Navigate } from 'react-router-dom'

import { TelegramOpenCta } from '../components/TelegramOpenCta'
import { useAuth } from '../context/AuthContext'
import { useGuestExperiment } from '../context/GuestExperimentContext'
import { useLocale } from '../context/LocaleContext'
import { isTelegramMiniApp } from '../platform/telegram'
import { EntriesPage } from './EntriesPage'

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

  return (
    <section className="page telegram-first-landing">
      <h1>{t('brand')}</h1>
      <p className="muted">{t('home.lead')}</p>
      <TelegramOpenCta variant="hero" />
      <p className="muted telegram-first-or">{t('home.orWebsite')}</p>
      <p className="button-row telegram-first-web">
        <Link className="button button-secondary" to="/login">
          {t('nav.logIn')}
        </Link>
      </p>
    </section>
  )
}
