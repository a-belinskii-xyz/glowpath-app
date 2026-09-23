import { useEffect, useState } from 'react'

import {
  createTelegramLinkCode,
  getTelegramLink,
  unlinkTelegram,
} from '../api/telegram'
import { Alert } from './Alert'
import { PageErrorAlert } from './PageErrorAlert'
import { ConfirmDialog } from './ConfirmDialog'
import { StableButtonLabel } from './StableButtonLabel'
import { useLocale } from '../context/LocaleContext'
import { ApiError, formatApiError } from '../lib/errors'
import type { TelegramLinkPublic } from '../types/telegram'

export function TelegramLinkForm() {
  const { t } = useLocale()
  const [status, setStatus] = useState<TelegramLinkPublic | null>(null)
  const [deepLink, setDeepLink] = useState<string | null>(null)
  const [code, setCode] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isBusy, setIsBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [confirmUnlink, setConfirmUnlink] = useState(false)
  const [unlinkError, setUnlinkError] = useState<string | null>(null)

  const load = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const next = await getTelegramLink()
      setStatus(next)
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError(t('errors.verifyToManageTelegram'))
      } else {
        setError(formatApiError(err, t, 'errors.failedLoadTelegram'))
      }
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [t])

  const handleConnect = async () => {
    setIsBusy(true)
    setError(null)
    setSuccess(null)
    try {
      const created = await createTelegramLinkCode()
      setDeepLink(created.deep_link)
      setCode(created.code)
      setSuccess(t('profile.telegramCodeReady'))
    } catch (err) {
      if (
        err instanceof ApiError &&
        (err.code === 'telegram_bot_not_configured' || err.status === 503)
      ) {
        setError(t('errors.telegramBotNotConfigured'))
      } else {
        setError(formatApiError(err, t, 'errors.failedConnectTelegram'))
      }
    } finally {
      setIsBusy(false)
    }
  }

  const handleUnlink = async () => {
    setUnlinkError(null)
    setIsBusy(true)
    setError(null)
    setSuccess(null)
    try {
      const next = await unlinkTelegram()
      setStatus(next)
      setDeepLink(null)
      setCode(null)
      setConfirmUnlink(false)
      setSuccess(t('profile.telegramUnlinked'))
    } catch (err) {
      setUnlinkError(formatApiError(err, t, 'errors.failedUnlinkTelegram'))
    } finally {
      setIsBusy(false)
    }
  }

  const handleRefresh = async () => {
    setDeepLink(null)
    setCode(null)
    setSuccess(null)
    await load()
  }

  if (isLoading) {
    return <p className="muted">{t('common.loadingTelegram')}</p>
  }

  const linked = status?.linked === true

  return (
    <div className="card form profile-telegram-form">
      {confirmUnlink ? (
        <ConfirmDialog
          open
          title={t('confirm.unlinkTelegramTitle')}
          message={t('confirm.unlinkTelegram')}
          confirmLabel={t('profile.telegramUnlink')}
          isBusy={isBusy}
          error={unlinkError}
          onCancel={() => {
            if (isBusy) return
            setConfirmUnlink(false)
            setUnlinkError(null)
          }}
          onConfirm={() => void handleUnlink()}
        />
      ) : null}
      <PageErrorAlert error={error} />
      {success ? <Alert variant="success">{success}</Alert> : null}

      <div className="profile-connection-status">
        <span
          className={`status-pill${linked ? ' status-pill--ok' : ' status-pill--muted'}`}
        >
          {linked ? t('profile.telegramLinkedShort') : t('profile.telegramNotLinked')}
        </span>
      </div>

      {linked ? (
        status?.can_unlink === false ? (
          <p className="form-hint">{t('profile.telegramUnlinkDisabled')}</p>
        ) : (
          <div className="button-row">
            <button
              type="button"
              className="button button-secondary"
              disabled={isBusy}
              onClick={() => void handleRefresh()}
            >
              {t('common.refresh')}
            </button>
            <button
              type="button"
              className="button button-danger"
              disabled={isBusy}
              onClick={() => setConfirmUnlink(true)}
            >
              <StableButtonLabel
                active={isBusy ? t('common.saving') : t('profile.telegramUnlink')}
                labels={[t('profile.telegramUnlink'), t('common.saving')]}
              />
            </button>
          </div>
        )
      ) : (
        <>
          {!status?.bot_configured ? (
            <p className="form-hint">{t('profile.telegramBotHint')}</p>
          ) : null}
          {deepLink && code ? (
            <div className="profile-telegram-code">
              <p>
                <a href={deepLink} target="_blank" rel="noreferrer" className="button">
                  {t('profile.telegramOpenBot')}
                </a>
              </p>
              <p className="form-hint">
                {t('profile.telegramCodeFallback', { code })}
              </p>
            </div>
          ) : null}
          <div className="button-row">
            <button
              type="button"
              className="button"
              disabled={isBusy || !status?.bot_configured}
              onClick={() => void handleConnect()}
            >
              <StableButtonLabel
                active={isBusy ? t('common.saving') : t('profile.telegramConnect')}
                labels={[t('profile.telegramConnect'), t('common.saving')]}
              />
            </button>
            <button
              type="button"
              className="button button-secondary"
              disabled={isBusy}
              onClick={() => void handleRefresh()}
            >
              {t('common.refresh')}
            </button>
          </div>
        </>
      )}
    </div>
  )
}
