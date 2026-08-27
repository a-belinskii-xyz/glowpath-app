import { useState } from 'react'

import { patchMoodPreferences } from '../api/moodPreferences'
import { PageErrorAlert } from './PageErrorAlert'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { ApiError, formatApiError } from '../lib/errors'

export function StreakDisplaySetting() {
  const { t } = useLocale()
  const { showStreak, isLoading, setPreferences } = useMoodPreferences()
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const handleChange = async (checked: boolean) => {
    setError(null)
    setIsSaving(true)
    try {
      const saved = await patchMoodPreferences({ show_streak: checked })
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
          checked={showStreak}
          disabled={isSaving}
          onChange={(event) => void handleChange(event.target.checked)}
        />
        <span>
          <span className="notification-master-title">{t('profile.showStreak')}</span>
          <span className="notification-master-hint">{t('profile.showStreakHint')}</span>
        </span>
      </label>
    </>
  )
}
