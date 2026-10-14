import { useId, useState } from 'react'

import { patchMoodPreferences } from '../api/moodPreferences'
import { PageErrorAlert } from './PageErrorAlert'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { ApiError, formatApiError } from '../lib/errors'
import { todayKey } from '../lib/datetime'
import type { MoodPreferencesUpdate } from '../types/moodPreferences'

/** GP-45: show the month from the 1st, or from the user's own start. */
export function CalendarStartSetting() {
  const { t } = useLocale()
  const { user } = useAuth()
  const { calendarFromStart, calendarStartOn, firstEntryOn, setPreferences } =
    useMoodPreferences()
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [restarted, setRestarted] = useState(false)
  const titleId = useId()
  const dateId = useId()
  const timeZone = user?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC'
  const today = todayKey(timeZone)
  const startOn = calendarStartOn ?? firstEntryOn

  const save = async (body: MoodPreferencesUpdate) => {
    setError(null)
    setIsSaving(true)
    try {
      setPreferences(await patchMoodPreferences(body))
      return true
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError(t('errors.verifyToManageMoodPreferences'))
      } else {
        setError(formatApiError(err, t, 'errors.failedSave'))
      }
      return false
    } finally {
      setIsSaving(false)
    }
  }

  const options = [
    { value: false, title: t('profile.calendarFullMonth'), hint: t('profile.calendarFullMonthHint') },
    { value: true, title: t('profile.calendarFromStart'), hint: t('profile.calendarFromStartHint') },
  ]

  return (
    <div className="calendar-start-setting">
      <PageErrorAlert error={error} />
      <div className="notification-master calendar-start-card">
        <span id={titleId} className="notification-master-title">
          {t('profile.calendarTitle')}
        </span>
        <div className="calendar-start-options" role="radiogroup" aria-labelledby={titleId}>
          {options.map((option) => (
            <label
              key={String(option.value)}
              className={`calendar-start-option${calendarFromStart === option.value ? ' is-active' : ''}`}
            >
              <input
                type="radio"
                name={titleId}
                checked={calendarFromStart === option.value}
                disabled={isSaving}
                onChange={() => void save({ calendar_from_start: option.value })}
              />
              <span>
                <span className="calendar-start-option-title">{option.title}</span>
                <span className="notification-master-hint">{option.hint}</span>
              </span>
            </label>
          ))}
        </div>

        {calendarFromStart ? (
          <div className="calendar-start-row">
            <label htmlFor={dateId}>
              <span className="calendar-start-option-title">{t('profile.calendarStartOn')}</span>
              <span className="notification-master-hint">
                {calendarStartOn ? t('profile.calendarStartOnHint') : t('profile.calendarStartOnFirst')}
              </span>
            </label>
            <div className="calendar-start-date">
              <input
                id={dateId}
                type="date"
                className="input"
                value={startOn ?? ''}
                max={today}
                disabled={isSaving}
                onChange={(event) => {
                  if (event.target.value) {
                    void save({ calendar_start_on: event.target.value })
                  }
                }}
              />
              {calendarStartOn ? (
                <button
                  type="button"
                  className="link-button"
                  disabled={isSaving}
                  onClick={() => void save({ calendar_start_on: null })}
                >
                  {t('profile.calendarStartReset')}
                </button>
              ) : null}
            </div>
          </div>
        ) : null}

        <div className="calendar-start-row">
          <span>
            <span className="calendar-start-option-title">{t('profile.calendarRestart')}</span>
            <span className="notification-master-hint">
              {restarted ? t('profile.calendarRestartDone') : t('profile.calendarRestartHint')}
            </span>
          </span>
          <button
            type="button"
            className="button button-secondary"
            disabled={isSaving || (calendarFromStart && calendarStartOn === today)}
            onClick={async () => {
              const saved = await save({ calendar_from_start: true, calendar_start_on: today })
              setRestarted(saved)
            }}
          >
            {t('profile.calendarRestartAction')}
          </button>
        </div>
      </div>
    </div>
  )
}
