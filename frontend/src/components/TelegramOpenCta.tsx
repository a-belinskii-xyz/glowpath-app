import { useEffect, useState } from 'react'

import { getTelegramEntryPoint } from '../api/telegram'
import { useLocale } from '../context/LocaleContext'
import { isTelegramMiniApp } from '../platform/telegram'

export function TelegramOpenCta() {
  const { t } = useLocale()
  const [botUrl, setBotUrl] = useState<string | null>(null)

  useEffect(() => {
    if (isTelegramMiniApp()) {
      return
    }
    let cancelled = false
    void getTelegramEntryPoint()
      .then((payload) => {
        if (!cancelled) {
          setBotUrl(payload.bot_url)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setBotUrl(null)
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (isTelegramMiniApp() || !botUrl) {
    return null
  }

  return (
    <p className="telegram-open-cta">
      <a className="button button-secondary button-block" href={botUrl}>
        {t('auth.openInTelegram')}
      </a>
    </p>
  )
}
