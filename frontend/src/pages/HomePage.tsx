import { Link } from 'react-router-dom'

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

  return (
    <section className="page">
      <h1>{t('brand')}</h1>
      <p className="lead">{t('home.lead')}</p>
      <div className="button-row">
        <Link className="button" to="/login">
          {t('nav.logIn')}
        </Link>
        <Link className="button button-secondary" to="/register">
          {t('home.createAccount')}
        </Link>
      </div>
    </section>
  )
}
