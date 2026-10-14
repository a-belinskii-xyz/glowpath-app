import { Link, NavLink, Navigate, Outlet, useLocation } from 'react-router-dom'
import type { CSSProperties, ReactNode } from 'react'

import { CaptureAttribution } from './CaptureAttribution'
import { GuestDataBanner } from './GuestDataBanner'
import { LanguageSwitcher } from './LanguageSwitcher'
import { NavEntriesIcon, NavGalleryIcon, NavGoalsIcon, NavProfileIcon } from './icons'
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

/** Everything reachable from the Profile hub lights up the Profile tab on mobile. */
const PROFILE_HUB_PREFIXES = ['/profile', '/settings', '/achievements', '/market', '/plans']

function isProfileHubSection(pathname: string) {
  return PROFILE_HUB_PREFIXES.some((prefix) => pathname.startsWith(prefix))
}

/** "Me" holds the week's goals, so the goal list lights the same tab. */
function isMySection(pathname: string) {
  return pathname.startsWith('/me') || pathname.startsWith('/goals')
}

function isFocusedEntryFlow(pathname: string) {
  return pathname.startsWith('/entries/')
}

function BottomNav() {
  const { t } = useLocale()
  const location = useLocation()
  const profileActive = isProfileHubSection(location.pathname)
  const myActive = isMySection(location.pathname)

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
      <NavLink to="/me" className={() => `app-bottom-nav-link${myActive ? ' is-active' : ''}`}>
        <NavGoalsIcon />
        <span>{t('nav.my')}</span>
      </NavLink>
      <NavLink
        to="/profile"
        className={() => `app-bottom-nav-link${profileActive ? ' is-active' : ''}`}
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
  const showMarket = Boolean(user?.features?.icon_marketplace)
  const showAchievements = Boolean(user?.features?.achievements) || guestShell
  // Plans has no sidebar entry of its own; it lives under the Profile hub.
  const profileLinkActive =
    location.pathname.startsWith('/profile') || location.pathname.startsWith('/plans')

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
                {/* `/` and `/login` already show the sign-in block. */}
                {location.pathname !== '/' && location.pathname !== '/login' ? (
                  <Link to="/login">{t('nav.logIn')}</Link>
                ) : null}
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
          <NavLink to="/me" className={navClassName}>
            {t('nav.my')}
          </NavLink>
          <NavLink to="/goals" className={navClassName}>
            {t('nav.goals')}
          </NavLink>
          <p className="app-sidebar-section">{t('nav.sectionAccount')}</p>
          {showAchievements ? (
            <NavLink to="/achievements" className={navClassName}>
              {t('nav.achievements')}
            </NavLink>
          ) : null}
          {showMarket ? (
            <NavLink to="/market" className={navClassName}>
              {t('nav.market')}
            </NavLink>
          ) : null}
          <NavLink
            to="/profile"
            className={() => navClassName({ isActive: profileLinkActive })}
          >
            {t('nav.profile')}
          </NavLink>
          <NavLink to="/settings" className={navClassName}>
            {t('nav.settings')}
          </NavLink>
          {guestShell ? (
            <Link to="/login" className="app-nav-link">
              {t('guest.banner.signIn')}
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
