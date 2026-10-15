import { useId, useState } from 'react'

import { PageErrorAlert } from './PageErrorAlert'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { formatApiError } from '../lib/errors'
import { TIME_FORMATS, type TimeFormat, formatClockMinutes } from '../lib/timeFormat'

const OPTION_LABEL_KEYS = {
  auto: 'profile.timeFormatAuto',
  '24h': 'profile.timeFormat24',
  '12h': 'profile.timeFormat12',
} as const satisfies Record<TimeFormat, string>

/** 24-hour or AM/PM clock for every time in the app (GP-53). */
export function TimeFormatSetting() {
  const { t } = useLocale()
  const { user, updateTimeFormat } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<TimeFormat | null>(null)
  const labelId = useId()

  if (!user) {
    return null
  }

  const current = pending ?? user.time_format

  const handleSelect = async (next: TimeFormat) => {
    if (next === current || pending !== null) {
      return
    }
    setError(null)
    setPending(next)
    try {
      await updateTimeFormat(next)
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
            {t('profile.timeFormatTitle')}
          </span>
          <span className="notification-master-hint">
            {t('profile.timeFormatHint', { example: formatClockMinutes(22 * 60 + 30) })}
          </span>
        </span>
        <div className="segmented-control theme-setting-options" role="group" aria-labelledby={labelId}>
          {TIME_FORMATS.map((option) => (
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
