import { Link, NavLink, Navigate, Outlet, useLocation } from 'react-router-dom'
import type { CSSProperties } from 'react'

import { CaptureAttribution } from './CaptureAttribution'
import { LanguageSwitcher } from './LanguageSwitcher'
import { useAmbientGlow } from '../context/AmbientGlowContext'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'

function navClassName({ isActive }: { isActive: boolean }) {
  return `app-nav-link${isActive ? ' is-active' : ''}`
}

function ShellChrome({
  sidebar,
  onboarding,
  guestNav,
}: {
  sidebar: boolean
  onboarding: boolean
  guestNav: boolean
}) {
  const { t } = useLocale()
  const { logout } = useAuth()
  const { cssVars } = useAmbientGlow()
  const shellStyle = cssVars as CSSProperties

  if (onboarding) {
    return (
      <div className="app-shell" style={shellStyle}>
        <CaptureAttribution />
        <header className="app-header">
          <span className="brand">{t('brand')}</span>
          <nav className="nav-links">
            <LanguageSwitcher id="onboarding-language" compact />
            <button type="button" className="app-nav-link app-nav-logout" onClick={logout}>
              {t('nav.logOut')}
            </button>
          </nav>
        </header>
        <main className="app-main">
          <Outlet />
        </main>
      </div>
    )
  }

  if (!sidebar) {
    return (
      <div className="app-shell" style={shellStyle}>
        <CaptureAttribution />
        <header className="app-header">
          <Link to="/" className="brand">
            {t('brand')}
          </Link>
          <nav className="nav-links">
            <LanguageSwitcher id="guest-language" compact />
            {guestNav ? (
              <>
                <Link to="/login">{t('nav.logIn')}</Link>
                <Link to="/register">{t('nav.register')}</Link>
              </>
            ) : null}
          </nav>
        </header>
        <main className="app-main">
          <Outlet />
        </main>
      </div>
    )
  }

  return (
    <div className="app-shell app-shell--sidebar" style={shellStyle}>
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

export function Layout() {
  const { isAuthenticated, isLoading, user } = useAuth()
  const location = useLocation()
  const needsOnboarding = Boolean(isAuthenticated && user && !user.onboarding_completed)
  const onboardingExempt =
    location.pathname === '/onboarding' ||
    location.pathname === '/reset-password' ||
    location.pathname === '/verify-email'

  if (!isLoading && needsOnboarding && !onboardingExempt) {
    return <Navigate to="/onboarding" replace />
  }

  return (
    <ShellChrome
      sidebar={isAuthenticated && !needsOnboarding}
      onboarding={needsOnboarding}
      guestNav={!isLoading && !isAuthenticated}
    />
  )
}
