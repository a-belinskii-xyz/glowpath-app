import { useCallback, useEffect, useRef, useState } from 'react'

import { pollTelegramBotLogin, startTelegramBotLogin } from '../api/auth'
import { PageErrorAlert } from './PageErrorAlert'
import { StableButtonLabel } from './StableButtonLabel'
import { useLocale } from '../context/LocaleContext'
import { formatApiError } from '../lib/errors'
import { detectTimezone } from '../lib/timezones'

const POLL_INTERVAL_MS = 2000

type Pending = { pollToken: string; deepLink: string }

/** Sign in by pressing Start in the bot; this page polls until the bot confirms. */
export function TelegramBotLogin({
  onTokens,
}: {
  onTokens: (accessToken: string, refreshToken: string, userCreated: boolean) => Promise<void>
}) {
  const { t } = useLocale()
  const [pending, setPending] = useState<Pending | null>(null)
  const [isStarting, setIsStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const isPolling = useRef(false)

  const start = async () => {
    setIsStarting(true)
    setError(null)
    try {
      const started = await startTelegramBotLogin(detectTimezone())
      setPending({ pollToken: started.poll_token, deepLink: started.deep_link })
    } catch (err) {
      setError(formatApiError(err, t, 'errors.loginFailed'))
    } finally {
      setIsStarting(false)
    }
  }

  const poll = useCallback(async () => {
    if (!pending || isPolling.current) {
      return
    }
    isPolling.current = true
    try {
      const result = await pollTelegramBotLogin(pending.pollToken)
      if (result.status === 'confirmed' && result.access_token && result.refresh_token) {
        setPending(null)
        await onTokens(result.access_token, result.refresh_token, Boolean(result.user_created))
      } else if (result.status === 'expired') {
        setPending(null)
        setError(t('auth.loginViaBotExpired'))
      }
    } catch {
      // Network hiccup: the next tick retries.
    } finally {
      isPolling.current = false
    }
  }, [onTokens, pending, t])

  useEffect(() => {
    if (!pending) {
      return
    }
    const timer = window.setInterval(() => void poll(), POLL_INTERVAL_MS)
    const onVisible = () => {
      if (document.visibilityState === 'visible') {
        void poll()
      }
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      window.clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [pending, poll])

  if (pending) {
    return (
      <div className="telegram-bot-login">
        <a
          className="button button-block"
          href={pending.deepLink}
          target="_blank"
          rel="noopener noreferrer"
        >
          {t('auth.openBot')}
        </a>
        <p className="muted">{t('auth.loginViaBotWaiting')}</p>
        <button
          type="button"
          className="button button-secondary button-block"
          onClick={() => setPending(null)}
        >
          {t('common.cancel')}
        </button>
      </div>
    )
  }

  return (
    <div className="telegram-bot-login">
      <PageErrorAlert error={error} />
      <button
        type="button"
        className="button button-block"
        disabled={isStarting}
        onClick={() => void start()}
      >
        <StableButtonLabel
          active={isStarting ? t('auth.loginViaBotStarting') : t('auth.loginViaBot')}
          labels={[t('auth.loginViaBot'), t('auth.loginViaBotStarting')]}
        />
      </button>
    </div>
  )
}
