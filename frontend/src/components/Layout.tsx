import { Link, NavLink, Outlet } from 'react-router-dom'

import { CaptureAttribution } from './CaptureAttribution'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'

function navClassName({ isActive }: { isActive: boolean }) {
  return `app-nav-link${isActive ? ' is-active' : ''}`
}

export function Layout() {
  const { isAuthenticated, logout } = useAuth()
  const { t } = useLocale()

  if (!isAuthenticated) {
    return (
      <div className="app-shell">
        <CaptureAttribution />
        <header className="app-header">
          <Link to="/" className="brand">
            {t('brand')}
          </Link>
          <nav className="nav-links">
            <Link to="/login">{t('nav.logIn')}</Link>
            <Link to="/register">{t('nav.register')}</Link>
          </nav>
        </header>
        <main className="app-main">
          <Outlet />
        </main>
      </div>
    )
  }

  return (
    <div className="app-shell app-shell--sidebar">
      <CaptureAttribution />
      <aside className="app-sidebar" aria-label={t('nav.menu')}>
        <Link to="/" className="brand app-sidebar-brand">
          {t('brand')}
        </Link>
        <nav className="app-sidebar-nav">
          <p className="app-sidebar-section">{t('nav.sectionTrack')}</p>
          <NavLink to="/" end className={navClassName}>
            {t('nav.entries')}
          </NavLink>
          <NavLink to="/goals" className={navClassName}>
            {t('nav.goals')}
          </NavLink>
          <NavLink to="/tags" className={navClassName}>
            {t('nav.tags')}
          </NavLink>
          <NavLink to="/tracker-settings" className={navClassName}>
            {t('nav.trackerSettings')}
          </NavLink>
          <p className="app-sidebar-section">{t('nav.sectionAccount')}</p>
          <NavLink to="/profile" className={navClassName}>
            {t('nav.profile')}
          </NavLink>
          <button type="button" className="app-nav-link app-nav-logout" onClick={logout}>
            {t('nav.logOut')}
          </button>
        </nav>
      </aside>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}
