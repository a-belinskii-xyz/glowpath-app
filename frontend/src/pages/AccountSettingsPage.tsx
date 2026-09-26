import { useState } from 'react'

import { forgotPassword } from '../api/auth'
import { Alert } from '../components/Alert'
import { AttachEmailForm } from '../components/AttachEmailForm'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { SettingsSection } from '../components/SettingsSection'
import { StableButtonLabel } from '../components/StableButtonLabel'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { formatApiError } from '../lib/errors'
import { LOCALE_OPTIONS, type ApiLocale } from '../lib/locale'
import { timezoneSelectOptions } from '../lib/timezones'

export function AccountSettingsPage() {
  const { user, updateTimezone } = useAuth()
  const { locale, setLocale, t } = useLocale()
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
    if (!user.email) {
      return
    }
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
    <SettingsSection title={t('settings.accountTitle')}>
      <PageErrorAlert error={timezoneError} />
      <PageErrorAlert error={resetError} />
      {resetMessage ? <Alert variant="success">{resetMessage}</Alert> : null}

      <div className="settings-stack">
        <section className="card profile-account" aria-labelledby="settings-signin-heading">
          <h2 id="settings-signin-heading" className="profile-settings-subheading">
            {t('settings.signInTitle')}
          </h2>
          <div className="profile-account-row">
            <div className="profile-account-email">
              <span className="profile-account-label">{t('common.email')}</span>
              <div className="profile-account-email-value">
                <span className="profile-account-email-text">
                  {user.email ?? t('profile.signedInWithTelegram')}
                </span>
                {user.email ? (
                  <span
                    className={`status-pill${user.email_verified ? ' status-pill--ok' : ' status-pill--warn'}`}
                  >
                    {user.email_verified
                      ? t('profile.emailVerifiedShort')
                      : t('profile.emailUnverifiedShort')}
                  </span>
                ) : (
                  <span className="status-pill status-pill--ok">
                    {t('profile.telegramLinkedShort')}
                  </span>
                )}
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
        </section>

        {!user.email ? (
          <div className="card">
            <AttachEmailForm />
          </div>
        ) : null}

        <section className="card profile-account" aria-labelledby="settings-region-heading">
          <h2 id="settings-region-heading" className="profile-settings-subheading">
            {t('settings.regionTitle')}
          </h2>
          <div className="profile-account-grid">
            <div>
              <label className="profile-account-label" htmlFor="settings-timezone">
                {t('common.timezone')}
              </label>
              <select
                id="settings-timezone"
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
              <label className="profile-account-label" htmlFor="settings-locale">
                {t('common.language')}
              </label>
              <select
                id="settings-locale"
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
        </section>
      </div>
    </SettingsSection>
  )
}
