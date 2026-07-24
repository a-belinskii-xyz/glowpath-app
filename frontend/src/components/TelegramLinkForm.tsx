import { useEffect, useState } from 'react'

import {
  createTelegramLinkCode,
  getTelegramLink,
  unlinkTelegram,
} from '../api/telegram'
import { Alert } from './Alert'
import { ConfirmDialog } from './ConfirmDialog'
import { useLocale } from '../context/LocaleContext'
import { ApiError } from '../lib/errors'
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
        setError(err instanceof Error ? err.message : t('errors.failedLoadTelegram'))
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
      if (err instanceof ApiError && err.status === 503) {
        setError(t('errors.telegramBotNotConfigured'))
      } else {
        setError(err instanceof Error ? err.message : t('errors.failedConnectTelegram'))
      }
    } finally {
      setIsBusy(false)
    }
  }

  const handleUnlink = async () => {
    setConfirmUnlink(false)
    setIsBusy(true)
    setError(null)
    setSuccess(null)
    try {
      const next = await unlinkTelegram()
      setStatus(next)
      setDeepLink(null)
      setCode(null)
      setSuccess(t('profile.telegramUnlinked'))
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.failedUnlinkTelegram'))
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
          onCancel={() => setConfirmUnlink(false)}
          onConfirm={() => void handleUnlink()}
        />
      ) : null}
      {error ? <Alert variant="error">{error}</Alert> : null}
      {success ? <Alert variant="success">{success}</Alert> : null}

      <div className="profile-connection-status">
        <span
          className={`status-pill${linked ? ' status-pill--ok' : ' status-pill--muted'}`}
        >
          {linked ? t('profile.telegramLinkedShort') : t('profile.telegramNotLinked')}
        </span>
      </div>

      {linked ? (
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
              {isBusy ? t('common.saving') : t('profile.telegramUnlink')}
            </button>
        </div>
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
              {isBusy ? t('common.saving') : t('profile.telegramConnect')}
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
