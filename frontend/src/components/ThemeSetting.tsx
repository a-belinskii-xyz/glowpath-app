import { useId, useState } from 'react'

import { PageErrorAlert } from './PageErrorAlert'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { THEME_PREFERENCES, type ThemePreference } from '../design/themePreference'
import { formatApiError } from '../lib/errors'

const OPTION_LABEL_KEYS = {
  system: 'profile.themeSystem',
  light: 'profile.themeLight',
  dark: 'profile.themeDark',
} as const satisfies Record<ThemePreference, string>

export function ThemeSetting() {
  const { t } = useLocale()
  const { user, isTelegram, updateThemePreference } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<ThemePreference | null>(null)
  const labelId = useId()

  if (!user) {
    return null
  }

  const current = pending ?? user.theme_preference

  const handleSelect = async (next: ThemePreference) => {
    if (next === current || pending !== null) {
      return
    }
    setError(null)
    setPending(next)
    try {
      await updateThemePreference(next)
    } catch (err) {
      setError(formatApiError(err, t, 'errors.failedSave'))
    } finally {
      setPending(null)
    }
  }

  return (
    <div className="theme-setting">
      <PageErrorAlert error={error} />
      <div className="notification-master theme-setting-card">
        <span>
          <span id={labelId} className="notification-master-title">
            {t('profile.themeTitle')}
          </span>
          <span className="notification-master-hint">
            {isTelegram ? t('profile.themeHintTelegram') : t('profile.themeHint')}
          </span>
        </span>
        <div className="segmented-control theme-setting-options" role="group" aria-labelledby={labelId}>
          {THEME_PREFERENCES.map((option) => (
            <button
              key={option}
              type="button"
              className={`segmented-control-option${option === current ? ' is-active' : ''}`}
              aria-pressed={option === current}
              onClick={() => void handleSelect(option)}
            >
              {t(OPTION_LABEL_KEYS[option])}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
