import { useState } from 'react'

import { patchMoodPreferences } from '../api/moodPreferences'
import { PageErrorAlert } from './PageErrorAlert'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { ApiError, formatApiError } from '../lib/errors'

export function HistoricalColorsSetting() {
  const { t } = useLocale()
  const { useHistoricalColors, isLoading, setPreferences } = useMoodPreferences()
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const handleChange = async (checked: boolean) => {
    setError(null)
    setIsSaving(true)
    try {
      const saved = await patchMoodPreferences({ use_historical_colors: checked })
      setPreferences(saved)
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError(t('errors.verifyToManageMoodPreferences'))
      } else {
        setError(formatApiError(err, t, 'errors.failedSave'))
      }
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) {
    return <p className="muted">{t('common.loadingMoodPreferences')}</p>
  }

  return (
    <>
      <PageErrorAlert error={error} />
      <label className="notification-master">
        <input
          type="checkbox"
          checked={useHistoricalColors}
          disabled={isSaving}
          onChange={(event) => void handleChange(event.target.checked)}
        />
        <span>
          <span className="notification-master-title">
            {t('profile.keepHistoricalColors')}
          </span>
          <span className="notification-master-hint">
            {t('profile.keepHistoricalColorsHint')}
          </span>
        </span>
      </label>
    </>
  )
}
