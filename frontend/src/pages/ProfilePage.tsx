import { useState } from 'react'

import { forgotPassword } from '../api/auth'
import { Alert } from '../components/Alert'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { HistoricalColorsSetting } from '../components/HistoricalColorsSetting'
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

export function ProfilePage() {
  const { user, refreshUser, updateTimezone } = useAuth()
  const { locale, setLocale, t } = useLocale()
  const { scores } = useMoodPreferences()
  usePageAmbientGlow(Object.values(scores).map((style) => style.color))
  const [timezoneError, setTimezoneError] = useState<string | null>(null)
  const [isSavingTimezone, setIsSavingTimezone] = useState(false)
  const [resetError, setResetError] = useState<string | null>(null)
  const [resetMessage, setResetMessage] = useState<string | null>(null)
  const [isResettingPassword, setIsResettingPassword] = useState(false)

  if (!user) {
    return null
  }

  const timezoneOptions = timezoneSelectOptions(user.timezone)

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
    <section className="page">
      <EmailVerificationBanner />
      <div className="page-header">
        <h1>{t('profile.title')}</h1>
        <button type="button" className="button button-secondary" onClick={() => void refreshUser()}>
          {t('common.refresh')}
        </button>
      </div>

      <PageErrorAlert error={timezoneError} />
      <PageErrorAlert error={resetError} />
      {resetMessage ? <Alert variant="success">{resetMessage}</Alert> : null}

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

      <section className="profile-section" aria-labelledby="profile-appearance-heading">
        <h2 id="profile-appearance-heading">{t('profile.appearanceTitle')}</h2>
        <p className="profile-section-lead">{t('profile.appearanceLead')}</p>
        <HistoricalColorsSetting />
      </section>

      <section className="profile-section" aria-labelledby="profile-telegram-heading">
        <h2 id="profile-telegram-heading">{t('profile.telegramTitle')}</h2>
        <p className="profile-section-lead">{t('profile.telegramLead')}</p>
        <TelegramLinkForm />
      </section>

      <section className="profile-section" aria-labelledby="profile-notifications-heading">
        <h2 id="profile-notifications-heading">{t('profile.notificationsTitle')}</h2>
        <p className="profile-section-lead">{t('profile.notificationsLead')}</p>
        <NotificationSettingsForm timezone={user.timezone} />
      </section>
    </section>
  )
}
