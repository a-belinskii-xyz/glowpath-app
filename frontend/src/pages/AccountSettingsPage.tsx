import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { deleteAccount, downloadAccountExport, sendAccountExportToTelegram } from '../api/account'
import { forgotPassword } from '../api/auth'
import { Alert } from '../components/Alert'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { DiaryRestoreCard } from '../components/DiaryRestoreCard'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { SettingsSection } from '../components/SettingsSection'
import { StableButtonLabel } from '../components/StableButtonLabel'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { saveBlob } from '../lib/download'
import { formatApiError } from '../lib/errors'
import { LOCALE_OPTIONS, type ApiLocale } from '../lib/locale'
import { timezoneSelectOptions } from '../lib/timezones'
import { hapticNotification, isTelegramMiniApp } from '../platform/telegram'

export function AccountSettingsPage() {
  const { user, updateTimezone, logout } = useAuth()
  const navigate = useNavigate()
  const { locale, setLocale, t } = useLocale()
  const [timezoneError, setTimezoneError] = useState<string | null>(null)
  const [isSavingTimezone, setIsSavingTimezone] = useState(false)
  const [resetError, setResetError] = useState<string | null>(null)
  const [resetMessage, setResetMessage] = useState<string | null>(null)
  const [isResettingPassword, setIsResettingPassword] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)
  const [isExporting, setIsExporting] = useState(false)
  const [isSendingExport, setIsSendingExport] = useState(false)
  const [exportNotice, setExportNotice] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  if (!user) {
    return null
  }

  // Sign-in is Telegram-only (GP-28); show email only for accounts that have no Telegram yet.
  const showEmailSignIn = Boolean(user.email) && !user.telegram_linked

  const timezoneOptions = timezoneSelectOptions(user.timezone)
  const inMiniApp = isTelegramMiniApp()

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

  const handleExport = async () => {
    setExportError(null)
    setIsExporting(true)
    try {
      const { blob, filename } = await downloadAccountExport()
      saveBlob(blob, filename)
    } catch (err) {
      setExportError(formatApiError(err, t, 'settings.exportFailed'))
    } finally {
      setIsExporting(false)
    }
  }

  const handleSendExport = async () => {
    setExportError(null)
    setExportNotice(null)
    setIsSendingExport(true)
    try {
      const { parts } = await sendAccountExportToTelegram()
      hapticNotification('success')
      setExportNotice(
        parts > 1
          ? t('settings.exportTelegramSentParts', { count: String(parts) })
          : t('settings.exportTelegramSent'),
      )
    } catch {
      hapticNotification('error')
      setExportError(t('settings.exportTelegramFailed'))
    } finally {
      setIsSendingExport(false)
    }
  }

  const handleDelete = async () => {
    setDeleteError(null)
    setIsDeleting(true)
    try {
      await deleteAccount()
      logout()
      navigate('/', { replace: true })
    } catch (err) {
      setDeleteError(formatApiError(err, t, 'settings.deleteFailed'))
      setIsDeleting(false)
    }
  }

  return (
    <SettingsSection title={t('settings.accountTitle')}>
      <PageErrorAlert error={timezoneError} />
      <PageErrorAlert error={resetError} />
      <PageErrorAlert error={exportError} />
      {exportNotice ? <Alert variant="success">{exportNotice}</Alert> : null}
      {resetMessage ? <Alert variant="success">{resetMessage}</Alert> : null}

      <div className="settings-stack">
        <section className="card profile-account" aria-labelledby="settings-signin-heading">
          <h2 id="settings-signin-heading" className="profile-settings-subheading">
            {t('settings.signInTitle')}
          </h2>
          <div className="profile-account-row">
            {showEmailSignIn ? (
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
            ) : (
              <div className="profile-account-email">
                <span className="profile-account-label">{t('profile.telegramTitle')}</span>
                <div className="profile-account-email-value">
                  <span className="profile-account-email-text">{t('profile.signedInWithTelegram')}</span>
                  <span className="status-pill status-pill--ok">{t('profile.telegramLinkedShort')}</span>
                </div>
              </div>
            )}
            {showEmailSignIn && user.has_password ? (
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

        <section className="card profile-account" aria-labelledby="settings-data-heading">
          <h2 id="settings-data-heading" className="profile-settings-subheading">
            {t('settings.dataTitle')}
          </h2>
          {inMiniApp ? null : (
            <div className="profile-account-password">
              <button
                type="button"
                className="button button-secondary"
                disabled={isExporting}
                onClick={() => void handleExport()}
              >
                <StableButtonLabel
                  active={isExporting ? t('settings.exporting') : t('settings.exportButton')}
                  labels={[t('settings.exportButton'), t('settings.exporting')]}
                />
              </button>
              <p className="profile-field-hint">{t('settings.exportHint')}</p>
            </div>
          )}
          {user.telegram_linked ? (
            <div className="profile-account-password">
              <button
                type="button"
                className="button button-secondary"
                disabled={isSendingExport}
                onClick={() => void handleSendExport()}
              >
                <StableButtonLabel
                  active={
                    isSendingExport
                      ? t('settings.exportTelegramSending')
                      : t('settings.exportTelegramButton')
                  }
                  labels={[t('settings.exportTelegramButton'), t('settings.exportTelegramSending')]}
                />
              </button>
              <p className="profile-field-hint">{t('settings.exportTelegramHint')}</p>
            </div>
          ) : null}
          <DiaryRestoreCard />
        </section>

        <section className="card profile-account" aria-labelledby="settings-delete-heading">
          <h2 id="settings-delete-heading" className="profile-settings-subheading">
            {t('settings.deleteTitle')}
          </h2>
          <div className="profile-account-password">
            <button
              type="button"
              className="button button-danger-ghost"
              onClick={() => setConfirmDelete(true)}
            >
              {t('settings.deleteButton')}
            </button>
            <p className="profile-field-hint">{t('settings.deleteHint')}</p>
          </div>
        </section>
      </div>

      {confirmDelete ? (
        <ConfirmDialog
          open
          title={t('settings.deleteConfirmTitle')}
          message={t('settings.deleteConfirmMessage')}
          confirmLabel={t('settings.deleteConfirm')}
          busyLabel={t('settings.deleting')}
          isBusy={isDeleting}
          error={deleteError}
          onCancel={() => {
            if (isDeleting) return
            setConfirmDelete(false)
            setDeleteError(null)
          }}
          onConfirm={() => void handleDelete()}
        />
      ) : null}
    </SettingsSection>
  )
}
