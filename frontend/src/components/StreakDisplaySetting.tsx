import { useId, useState } from 'react'

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
  const [rulesOpen, setRulesOpen] = useState(false)
  const rulesId = useId()

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
    <div className="streak-display-setting">
      <PageErrorAlert error={error} />
      <div className="notification-master streak-setting-card">
        <label className="streak-setting-main">
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
        <button
          type="button"
          className="streak-info-toggle"
          aria-label={t('profile.showStreakInfo')}
          title={t('profile.showStreakInfo')}
          aria-expanded={rulesOpen}
          aria-controls={rulesId}
          onClick={() => setRulesOpen((open) => !open)}
        >
          i
        </button>
      </div>
      <aside
        id={rulesId}
        className="streak-rules"
        hidden={!rulesOpen}
        aria-label={t('profile.showStreakHow')}
      >
        <p className="streak-rules-title">{t('profile.showStreakHow')}</p>
        <ul>
          <li>{t('profile.showStreakRuleSameDay')}</li>
          <li>{t('profile.showStreakRuleBackdate')}</li>
          <li>{t('profile.showStreakRuleTimezone')}</li>
        </ul>
      </aside>
    </div>
  )
}
