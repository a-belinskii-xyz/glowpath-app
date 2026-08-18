import { useEffect, useState } from 'react'
import { Link, NavLink, Navigate, Outlet, useLocation } from 'react-router-dom'
import type { CSSProperties } from 'react'

import { CaptureAttribution } from './CaptureAttribution'
import { LanguageSwitcher } from './LanguageSwitcher'
import { NavEntriesIcon, NavGoalsIcon, NavMoreIcon, NavTagsIcon } from './icons'
import { useAmbientGlow } from '../context/AmbientGlowContext'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'

function navClassName({ isActive }: { isActive: boolean }) {
  return `app-nav-link${isActive ? ' is-active' : ''}`
}

function bottomNavClassName({ isActive }: { isActive: boolean }) {
  return `app-bottom-nav-link${isActive ? ' is-active' : ''}`
}

function isMoreSection(pathname: string) {
  return pathname.startsWith('/profile') || pathname.startsWith('/tracker-settings')
}

function isFocusedEntryFlow(pathname: string) {
  return pathname.startsWith('/entries/')
}

function BottomNav() {
  const { t } = useLocale()
  const { logout } = useAuth()
  const location = useLocation()
  const [moreOpen, setMoreOpen] = useState(false)
  const moreActive = isMoreSection(location.pathname)

  useEffect(() => {
    setMoreOpen(false)
  }, [location.pathname])

  useEffect(() => {
    if (!moreOpen) {
      return
    }
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMoreOpen(false)
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [moreOpen])

  return (
    <>
      {moreOpen ? (
        <div className="app-more-backdrop" onClick={() => setMoreOpen(false)}>
          <div
            className="app-more-sheet"
            role="dialog"
            aria-modal="true"
            aria-label={t('nav.moreMenu')}
            onClick={(event) => event.stopPropagation()}
          >
            <NavLink to="/tracker-settings" className={navClassName} onClick={() => setMoreOpen(false)}>
              {t('nav.trackerSettings')}
            </NavLink>
            <NavLink to="/profile" className={navClassName} onClick={() => setMoreOpen(false)}>
              {t('nav.profile')}
            </NavLink>
            <button type="button" className="app-nav-link app-nav-logout" onClick={logout}>
              {t('nav.logOut')}
            </button>
          </div>
        </div>
      ) : null}
      <nav className="app-bottom-nav" aria-label={t('nav.menu')}>
        <NavLink to="/" end className={bottomNavClassName}>
          <NavEntriesIcon />
          <span>{t('nav.entries')}</span>
        </NavLink>
        <NavLink to="/goals" className={bottomNavClassName}>
          <NavGoalsIcon />
          <span>{t('nav.goals')}</span>
        </NavLink>
        <NavLink to="/tags" className={bottomNavClassName}>
          <NavTagsIcon />
          <span>{t('nav.tags')}</span>
        </NavLink>
        <button
          type="button"
          className={`app-bottom-nav-link${moreActive || moreOpen ? ' is-active' : ''}`}
          aria-haspopup="dialog"
          aria-expanded={moreOpen}
          onClick={() => setMoreOpen((open) => !open)}
        >
          <NavMoreIcon />
          <span>{t('nav.more')}</span>
        </button>
      </nav>
    </>
  )
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
  const location = useLocation()
  const shellStyle = cssVars as CSSProperties
  const hideBottomNav = isFocusedEntryFlow(location.pathname)

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
    <div
      className={`app-shell app-shell--sidebar${hideBottomNav ? ' app-shell--no-bottom-nav' : ''}`}
      style={shellStyle}
    >
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
      {hideBottomNav ? null : <BottomNav />}
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
