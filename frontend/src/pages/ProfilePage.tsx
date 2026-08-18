import { memo, type ReactNode, useLayoutEffect, useRef, useState } from 'react'

import { forgotPassword } from '../api/auth'
import { Alert } from '../components/Alert'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { HistoricalColorsSetting } from '../components/HistoricalColorsSetting'
import { BellIcon, ChevronRightIcon, PaletteIcon, SettingsIcon } from '../components/icons'
import { NotificationSettingsForm } from '../components/NotificationSettingsForm'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { StableButtonLabel } from '../components/StableButtonLabel'
import { TelegramLinkForm } from '../components/TelegramLinkForm'
import { usePageAmbientGlow } from '../context/AmbientGlowContext'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { LOCALE_OPTIONS, type ApiLocale } from '../lib/locale'
import { timezoneSelectOptions } from '../lib/timezones'
import { formatApiError } from '../lib/errors'
import { TrackerSettingsContent } from './TrackerSettingsPage'

type SettingsPanelId = 'tracker' | 'notifications' | 'appearance'

const TrackerSettingsPanelBody = memo(function TrackerSettingsPanelBody() {
  return <TrackerSettingsContent />
})

const NotificationSettingsPanelBody = memo(function NotificationSettingsPanelBody({
  timezone,
}: {
  timezone: string
}) {
  const { t } = useLocale()

  return (
    <>
      <section aria-labelledby="profile-telegram-heading">
        <h2 id="profile-telegram-heading" className="profile-settings-subheading">
          {t('profile.telegramTitle')}
        </h2>
        <p className="profile-section-lead">{t('profile.telegramLead')}</p>
        <TelegramLinkForm />
      </section>
      <NotificationSettingsForm timezone={timezone} />
    </>
  )
})

const AppearanceSettingsPanelBody = memo(function AppearanceSettingsPanelBody() {
  return <HistoricalColorsSetting />
})

function getScrollParent(element: HTMLElement): HTMLElement | Window {
  let current = element.parentElement
  while (current) {
    const { overflowY } = window.getComputedStyle(current)
    if (
      (overflowY === 'auto' || overflowY === 'scroll' || overflowY === 'overlay') &&
      current.scrollHeight > current.clientHeight
    ) {
      return current
    }
    current = current.parentElement
  }
  return window
}

function keepElementViewportTop(element: HTMLElement, top: number) {
  for (let pass = 0; pass < 3; pass += 1) {
    const delta = element.getBoundingClientRect().top - top
    if (Math.abs(delta) < 0.5) {
      return
    }
    const scroller = getScrollParent(element)
    if (scroller === window) {
      window.scrollBy(0, delta)
    } else {
      scroller.scrollTop += delta
    }
  }
}

function ProfileSettingsPanel({
  id,
  icon,
  title,
  lead,
  open,
  onToggle,
  children,
}: {
  id: SettingsPanelId
  icon: ReactNode
  title: string
  lead: string
  open: boolean
  onToggle: () => void
  children: ReactNode
}) {
  const contentId = `profile-settings-${id}`
  const headerRef = useRef<HTMLButtonElement>(null)
  const lockTopRef = useRef<number | null>(null)
  const [mounted, setMounted] = useState(false)
  const [stickTop, setStickTop] = useState<number | null>(null)

  const handleToggle = () => {
    const top = headerRef.current?.getBoundingClientRect().top ?? null
    lockTopRef.current = top
    if (!open && top !== null) {
      setStickTop(top)
    }
    onToggle()
  }

  useLayoutEffect(() => {
    if (open && !mounted) {
      setMounted(true)
    }

    const header = headerRef.current
    const top = lockTopRef.current
    if (header === null || top === null) {
      return
    }

    keepElementViewportTop(header, top)

    if (open && !mounted) {
      return
    }

    const frame = window.requestAnimationFrame(() => {
      keepElementViewportTop(header, top)
      lockTopRef.current = null
      if (!open) {
        setStickTop(null)
      }
    })
    return () => window.cancelAnimationFrame(frame)
  }, [open, mounted])

  return (
    <div className={`profile-settings-panel${open ? ' is-open' : ''}`}>
      <button
        ref={headerRef}
        type="button"
        className="profile-shortcut"
        aria-expanded={open}
        aria-controls={contentId}
        style={stickTop === null ? undefined : { top: stickTop }}
        onClick={handleToggle}
      >
        <span className="profile-shortcut-icon" aria-hidden="true">
          {icon}
        </span>
        <span className="profile-shortcut-copy">
          <span className="profile-shortcut-title">{title}</span>
          <span className="profile-shortcut-lead">{lead}</span>
        </span>
        <ChevronRightIcon className="profile-shortcut-chevron" />
      </button>
      {mounted ? (
        <div id={contentId} className="profile-settings-panel-body" hidden={!open}>
          {children}
        </div>
      ) : null}
    </div>
  )
}

export function ProfilePage() {
  const { user, logout, updateTimezone } = useAuth()
  const { locale, setLocale, t } = useLocale()
  const { scores } = useMoodPreferences()
  usePageAmbientGlow(Object.values(scores).map((style) => style.color))
  const [timezoneError, setTimezoneError] = useState<string | null>(null)
  const [isSavingTimezone, setIsSavingTimezone] = useState(false)
  const [resetError, setResetError] = useState<string | null>(null)
  const [resetMessage, setResetMessage] = useState<string | null>(null)
  const [isResettingPassword, setIsResettingPassword] = useState(false)
  const [openPanel, setOpenPanel] = useState<SettingsPanelId | null>(null)

  if (!user) {
    return null
  }

  const timezoneOptions = timezoneSelectOptions(user.timezone)

  const togglePanel = (id: SettingsPanelId) => {
    setOpenPanel((current) => (current === id ? null : id))
  }

  const handleTimezoneChange = async (nextTimezone: string) => {
    if (nextTimezone === user.timezone) {
      return
    }
    setTimezoneError(null)
    setIsSavingTimezone(true)
    try {
      await updateTimezone(nextTimezone)
    } catch (err) {
      setTimezoneError(formatApiError(err, t, 'errors.failedSaveTimezone'))
    } finally {
      setIsSavingTimezone(false)
    }
  }

  const handleResetPassword = async () => {
    setResetError(null)
    setResetMessage(null)
    setIsResettingPassword(true)
    try {
      await forgotPassword(user.email)
      setResetMessage(t('profile.resetPasswordSent'))
    } catch (err) {
      setResetError(formatApiError(err, t, 'errors.requestFailed'))
    } finally {
      setIsResettingPassword(false)
    }
  }

  return (
    <section className="page page-profile">
      <EmailVerificationBanner />
      <header className="page-header">
        <h1>{t('profile.title')}</h1>
      </header>

      <PageErrorAlert error={timezoneError} />
      <PageErrorAlert error={resetError} />
      {resetMessage ? <Alert variant="success">{resetMessage}</Alert> : null}

      <div className="profile-shortcuts" role="region" aria-label={t('profile.settingsMenu')}>
        <ProfileSettingsPanel
          id="tracker"
          icon={<SettingsIcon />}
          title={t('nav.trackerSettings')}
          lead={t('profile.trackerSettingsLink')}
          open={openPanel === 'tracker'}
          onToggle={() => togglePanel('tracker')}
        >
          <TrackerSettingsPanelBody />
        </ProfileSettingsPanel>
        <ProfileSettingsPanel
          id="notifications"
          icon={<BellIcon />}
          title={t('profile.notificationsTitle')}
          lead={t('profile.notificationsLink')}
          open={openPanel === 'notifications'}
          onToggle={() => togglePanel('notifications')}
        >
          <NotificationSettingsPanelBody timezone={user.timezone} />
        </ProfileSettingsPanel>
        <ProfileSettingsPanel
          id="appearance"
          icon={<PaletteIcon />}
          title={t('profile.appearanceTitle')}
          lead={t('profile.appearanceLink')}
          open={openPanel === 'appearance'}
          onToggle={() => togglePanel('appearance')}
        >
          <AppearanceSettingsPanelBody />
        </ProfileSettingsPanel>
      </div>

      <div className="card profile-account">
        <div className="profile-account-row">
          <div className="profile-account-email">
            <span className="profile-account-label">{t('common.email')}</span>
            <div className="profile-account-email-value">
              <span className="profile-account-email-text">{user.email}</span>
              <span
                className={`status-pill${user.email_verified ? ' status-pill--ok' : ' status-pill--warn'}`}
              >
                {user.email_verified
                  ? t('profile.emailVerifiedShort')
                  : t('profile.emailUnverifiedShort')}
              </span>
            </div>
          </div>
          {user.has_password ? (
            <div className="profile-account-password">
              <button
                type="button"
                className="button button-secondary"
                disabled={isResettingPassword}
                onClick={() => void handleResetPassword()}
              >
                <StableButtonLabel
                  active={
                    isResettingPassword
                      ? t('profile.resetPasswordSending')
                      : t('profile.resetPassword')
                  }
                  labels={[t('profile.resetPassword'), t('profile.resetPasswordSending')]}
                />
              </button>
              <p className="profile-field-hint">{t('profile.resetPasswordHint')}</p>
            </div>
          ) : null}
        </div>

        <div className="profile-account-grid">
          <div>
            <label className="profile-account-label" htmlFor="profile-timezone">
              {t('common.timezone')}
            </label>
            <select
              id="profile-timezone"
              className="form-input profile-locale-select"
              value={user.timezone}
              disabled={isSavingTimezone}
              onChange={(event) => void handleTimezoneChange(event.target.value)}
            >
              {timezoneOptions.map((zone) => (
                <option key={zone} value={zone}>
                  {zone}
                </option>
              ))}
            </select>
            <p className="profile-field-hint">{t('profile.timezoneHint')}</p>
          </div>
          <div>
            <label className="profile-account-label" htmlFor="profile-locale">
              {t('common.language')}
            </label>
            <select
              id="profile-locale"
              className="form-input profile-locale-select"
              value={locale}
              onChange={(event) => setLocale(event.target.value as ApiLocale)}
            >
              {LOCALE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="profile-logout">
        <button type="button" className="button button-secondary profile-logout-button" onClick={logout}>
          {t('nav.logOut')}
        </button>
        <p className="profile-field-hint">{t('profile.logOutHint')}</p>
      </div>
    </section>
  )
}
