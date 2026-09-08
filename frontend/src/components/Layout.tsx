import { Link, NavLink, Navigate, Outlet, useLocation } from 'react-router-dom'
import type { CSSProperties, ReactNode } from 'react'

import { CaptureAttribution } from './CaptureAttribution'
import { GuestDataBanner } from './GuestDataBanner'
import { LanguageSwitcher } from './LanguageSwitcher'
import {
  NavEntriesIcon,
  NavGalleryIcon,
  NavGoalsIcon,
  NavMarketIcon,
  NavProfileIcon,
  NavTagsIcon,
} from './icons'
import { useAmbientGlow } from '../context/AmbientGlowContext'
import { useAuth } from '../context/AuthContext'
import { useGuestExperiment } from '../context/GuestExperimentContext'
import { useLocale } from '../context/LocaleContext'
import { isGuestDiaryMode } from '../lib/guestMode'

function navClassName({ isActive }: { isActive: boolean }) {
  return `app-nav-link${isActive ? ' is-active' : ''}`
}

function bottomNavClassName({ isActive }: { isActive: boolean }) {
  return `app-bottom-nav-link${isActive ? ' is-active' : ''}`
}

function isAccountSection(pathname: string) {
  return (
    pathname.startsWith('/profile') ||
    pathname.startsWith('/tracker-settings') ||
    pathname.startsWith('/achievements') ||
    pathname.startsWith('/plans')
  )
}

function isFocusedEntryFlow(pathname: string) {
  return pathname.startsWith('/entries/')
}

function BottomNav() {
  const { t } = useLocale()
  const { user } = useAuth()
  const location = useLocation()
  const accountActive = isAccountSection(location.pathname)
  const guestShell = isGuestDiaryMode()
  const showMarket = Boolean(user?.features?.icon_marketplace) || guestShell

  return (
    <nav className="app-bottom-nav" aria-label={t('nav.menu')}>
      <NavLink to="/" end className={bottomNavClassName}>
        <NavEntriesIcon />
        <span>{t('nav.entries')}</span>
      </NavLink>
      <NavLink to="/gallery" className={bottomNavClassName}>
        <NavGalleryIcon />
        <span>{t('nav.gallery')}</span>
      </NavLink>
      <NavLink to="/goals" className={bottomNavClassName}>
        <NavGoalsIcon />
        <span>{t('nav.goals')}</span>
      </NavLink>
      <NavLink to="/tags" className={bottomNavClassName}>
        <NavTagsIcon />
        <span>{t('nav.tags')}</span>
      </NavLink>
      {showMarket ? (
        <NavLink to="/market" className={bottomNavClassName}>
          <NavMarketIcon />
          <span>{t('nav.market')}</span>
        </NavLink>
      ) : null}
      <NavLink
        to="/profile"
        className={() => `app-bottom-nav-link${accountActive ? ' is-active' : ''}`}
      >
        <NavProfileIcon />
        <span>{t('nav.profile')}</span>
      </NavLink>
    </nav>
  )
}

function AppFrame({ className, children }: { className: string; children: ReactNode }) {
  const { cssVars } = useAmbientGlow()
  const rootStyle = cssVars as CSSProperties

  return (
    <div className="app-root" style={rootStyle}>
      <div className="app-ambient" aria-hidden="true" />
      <div className={className}>{children}</div>
    </div>
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
  const { logout, user, isTelegram } = useAuth()
  const location = useLocation()
  const hideBottomNav = isFocusedEntryFlow(location.pathname)
  const guestShell = isGuestDiaryMode()
  const showMarket = Boolean(user?.features?.icon_marketplace) || guestShell
  const showAchievements = Boolean(user?.features?.achievements) || guestShell

  if (onboarding) {
    return (
      <AppFrame className="app-shell">
        <CaptureAttribution />
        <header className="app-header">
          <span className="brand">{t('brand')}</span>
          <nav className="nav-links">
            <LanguageSwitcher id="onboarding-language" compact />
            {isTelegram ? null : guestShell ? (
              <>
                <Link to="/login">{t('nav.logIn')}</Link>
                <Link to="/register">{t('nav.register')}</Link>
              </>
            ) : (
              <button type="button" className="app-nav-link app-nav-logout" onClick={logout}>
                {t('nav.logOut')}
              </button>
            )}
          </nav>
        </header>
        <main className="app-main">
          <GuestDataBanner />
          <Outlet />
        </main>
      </AppFrame>
    )
  }

  if (!sidebar) {
    return (
      <AppFrame className="app-shell">
        <CaptureAttribution />
        <header className="app-header">
          <Link to="/" className="brand">
            {t('brand')}
          </Link>
          <nav className="nav-links">
            <LanguageSwitcher id="guest-language" compact />
            {guestNav ? (
              <>
                {location.pathname !== '/login' ? (
                  <Link to="/login">{t('nav.logIn')}</Link>
                ) : null}
                {location.pathname !== '/register' ? (
                  <Link to="/register">{t('nav.register')}</Link>
                ) : null}
                {location.pathname !== '/plans' ? <Link to="/plans">{t('nav.plans')}</Link> : null}
              </>
            ) : null}
          </nav>
        </header>
        <main className="app-main">
          <GuestDataBanner />
          <Outlet />
        </main>
      </AppFrame>
    )
  }

  return (
    <AppFrame
      className={`app-shell app-shell--sidebar${hideBottomNav ? ' app-shell--no-bottom-nav' : ''}`}
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
          <NavLink to="/gallery" className={navClassName}>
            {t('nav.gallery')}
          </NavLink>
          <NavLink to="/goals" className={navClassName}>
            {t('nav.goals')}
          </NavLink>
          <NavLink to="/tags" className={navClassName}>
            {t('nav.tags')}
          </NavLink>
          {showMarket ? (
            <NavLink to="/market" className={navClassName}>
              {t('nav.market')}
            </NavLink>
          ) : null}
          <NavLink to="/tracker-settings" className={navClassName}>
            {t('nav.trackerSettings')}
          </NavLink>
          <p className="app-sidebar-section">{t('nav.sectionAccount')}</p>
          {showAchievements ? (
            <NavLink to="/achievements" className={navClassName}>
              {t('nav.achievements')}
            </NavLink>
          ) : null}
          <NavLink to="/plans" className={navClassName}>
            {t('nav.plans')}
          </NavLink>
          <NavLink to="/profile" className={navClassName}>
            {t('nav.profile')}
          </NavLink>
          {guestShell ? (
            <Link to="/register" className="app-nav-link">
              {t('guest.banner.createAccount')}
            </Link>
          ) : isTelegram ? null : (
            <button type="button" className="app-nav-link app-nav-logout" onClick={logout}>
              {t('nav.logOut')}
            </button>
          )}
        </nav>
      </aside>
      <main className="app-main">
        <GuestDataBanner />
        <Outlet />
      </main>
      {hideBottomNav ? null : <BottomNav />}
    </AppFrame>
  )
}

export function Layout() {
  const { isAuthenticated, isLoading, user, isTelegram, telegramAuthError } = useAuth()
  const { guestLocalDiary, guestOnboardingCompleted, isBootstrapLoading } = useGuestExperiment()
  const location = useLocation()
  const { t } = useLocale()
  const guestShell = isGuestDiaryMode()
  const needsOnboarding = Boolean(
    (isAuthenticated && user && !user.onboarding_completed) ||
      (guestShell && !guestOnboardingCompleted),
  )
  const onboardingExempt =
    location.pathname === '/onboarding' ||
    location.pathname === '/reset-password' ||
    location.pathname === '/verify-email'

  if (isTelegram && isLoading) {
    return (
      <AppFrame className="app-shell">
        <main className="app-main">
          <p className="muted">{t('common.loading')}</p>
        </main>
      </AppFrame>
    )
  }

  if (isTelegram && !isAuthenticated) {
    return (
      <AppFrame className="app-shell">
        <main className="app-main">
          <section className="page">
            <h1>{t('telegramApp.authFailedTitle')}</h1>
            <p className="muted">{t('telegramApp.reopen')}</p>
            {telegramAuthError ? <p className="muted">{t('telegramApp.authFailed')}</p> : null}
          </section>
        </main>
      </AppFrame>
    )
  }

  if (!isLoading && !isBootstrapLoading && needsOnboarding && !onboardingExempt) {
    return <Navigate to="/onboarding" replace />
  }

  const showSidebar = (isAuthenticated && !needsOnboarding) || (guestShell && !needsOnboarding)

  return (
    <ShellChrome
      sidebar={showSidebar}
      onboarding={needsOnboarding}
      guestNav={!isLoading && !isAuthenticated && !guestLocalDiary && !isTelegram}
    />
  )
}
