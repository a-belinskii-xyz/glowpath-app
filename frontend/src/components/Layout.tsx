import { Link, Outlet } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'

export function Layout() {
  const { isAuthenticated, logout } = useAuth()
  const { t } = useLocale()

  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/" className="brand">
          {t('brand')}
        </Link>
        <nav className="nav-links">
          {isAuthenticated ? (
            <>
              <Link to="/">{t('nav.entries')}</Link>
              <Link to="/tags">{t('nav.tags')}</Link>
              <Link to="/templates">{t('nav.templates')}</Link>
              <Link to="/profile">{t('nav.profile')}</Link>
              <button type="button" className="link-button" onClick={logout}>
                {t('nav.logOut')}
              </button>
            </>
          ) : (
            <>
              <Link to="/login">{t('nav.logIn')}</Link>
              <Link to="/register">{t('nav.register')}</Link>
            </>
          )}
        </nav>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}
