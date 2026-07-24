import { type FormEvent, useEffect, useState } from 'react'

import {
  getNotificationSettings,
  patchNotificationSettings,
} from '../api/notificationSettings'
import { getTelegramLink } from '../api/telegram'
import { Alert } from './Alert'
import { FormField } from './FormField'
import { useLocale } from '../context/LocaleContext'
import { ApiError } from '../lib/errors'
import type { NotificationChannel, NotificationSettingsPublic } from '../types/notificationSettings'

const DEFAULT_REMINDER_TIME = '20:00'

function apiTimeToInput(value: string | null): string {
  if (!value) {
    return ''
  }
  return value.slice(0, 5)
}

function inputToApiTime(value: string): string {
  if (value.length === 5) {
    return `${value}:00`
  }
  return value
}

type NotificationSettingsFormProps = {
  timezone: string
}

export function NotificationSettingsForm({ timezone }: NotificationSettingsFormProps) {
  const { t } = useLocale()

  const [enabled, setEnabled] = useState(false)
  const [dailyMood, setDailyMood] = useState(false)
  const [goalReminders, setGoalReminders] = useState(false)
  const [reminderTime, setReminderTime] = useState('')
  const [telegramChannel, setTelegramChannel] = useState(false)
  const [telegramLinked, setTelegramLinked] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const applySettings = (settings: NotificationSettingsPublic) => {
    setEnabled(settings.enabled)
    setDailyMood(settings.daily_mood_reminder_enabled)
    setGoalReminders(settings.goal_reminders_enabled)
    setReminderTime(apiTimeToInput(settings.daily_mood_reminder_time))
    setTelegramChannel(settings.channels.includes('telegram'))
  }

  useEffect(() => {
    const load = async () => {
      setIsLoading(true)
      setSuccess(null)
      try {
        const [settings, telegram] = await Promise.all([
          getNotificationSettings(),
          getTelegramLink().catch(() => null),
        ])
        applySettings(settings)
        setTelegramLinked(telegram?.linked === true)
        setError(null)
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setError(t('errors.verifyToManageNotifications'))
        } else {
          setError(err instanceof Error ? err.message : t('errors.failedLoadNotifications'))
        }
      } finally {
        setIsLoading(false)
      }
    }
    void load()
  }, [t])

  const needsReminderTime = enabled && (dailyMood || goalReminders)

  const handleEnableReminder = (kind: 'daily' | 'goal', next: boolean) => {
    if (kind === 'daily') {
      setDailyMood(next)
    } else {
      setGoalReminders(next)
    }
    if (next && !reminderTime) {
      setReminderTime(DEFAULT_REMINDER_TIME)
    }
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSuccess(null)

    if (needsReminderTime && !reminderTime) {
      setError(t('profile.reminderTimeRequired'))
      return
    }

    const channels: NotificationChannel[] = ['email']
    if (telegramChannel && telegramLinked) {
      channels.push('telegram')
    }

    setIsSaving(true)
    setError(null)
    try {
      const saved = await patchNotificationSettings({
        enabled,
        channels,
        daily_mood_reminder_enabled: dailyMood,
        daily_mood_reminder_time: reminderTime ? inputToApiTime(reminderTime) : null,
        goal_reminders_enabled: goalReminders,
      })
      applySettings(saved)
      setSuccess(t('profile.notificationsSaved'))
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError(t('errors.verifyToManageNotifications'))
      } else {
        setError(err instanceof Error ? err.message : t('errors.failedSave'))
      }
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) {
    return <p className="muted">{t('common.loadingNotifications')}</p>
  }

  return (
    <form className="card form profile-notifications-form" onSubmit={(e) => void handleSubmit(e)}>
      {error ? <Alert variant="error">{error}</Alert> : null}
      {success ? <Alert variant="success">{success}</Alert> : null}

      <label className="notification-master">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(event) => setEnabled(event.target.checked)}
        />
        <span>
          <span className="notification-master-title">{t('profile.notificationsEnabled')}</span>
          <span className="notification-master-hint">{t('profile.notificationsEnabledHint')}</span>
        </span>
      </label>

      <fieldset className="notification-group" disabled={!enabled}>
        <legend className="notification-group-title">{t('profile.notificationChannels')}</legend>
        <div className="notification-channel-row">
          <span>{t('profile.channelEmail')}</span>
          <span className="status-pill status-pill--ok status-pill--sm">
            {t('profile.channelAlwaysOn')}
          </span>
        </div>
        <label
          className={
            telegramLinked
              ? 'tag-visibility-toggle'
              : 'tag-visibility-toggle notification-channel-disabled'
          }
        >
          <input
            type="checkbox"
            checked={telegramLinked && telegramChannel}
            disabled={!telegramLinked}
            onChange={(event) => setTelegramChannel(event.target.checked)}
          />
          <span>
            {telegramLinked
              ? t('profile.channelTelegram')
              : t('profile.channelTelegramLinkFirst')}
          </span>
        </label>
      </fieldset>

      <fieldset className="notification-group" disabled={!enabled}>
        <legend className="notification-group-title">{t('profile.notificationReminders')}</legend>
        <label className="tag-visibility-toggle">
          <input
            type="checkbox"
            checked={dailyMood}
            onChange={(event) => handleEnableReminder('daily', event.target.checked)}
          />
          <span>{t('profile.dailyMoodReminder')}</span>
        </label>
        <label className="tag-visibility-toggle">
          <input
            type="checkbox"
            checked={goalReminders}
            onChange={(event) => handleEnableReminder('goal', event.target.checked)}
          />
          <span>{t('profile.goalReminders')}</span>
        </label>
      </fieldset>

      {needsReminderTime ? (
        <FormField
          id="notification-reminder-time"
          label={t('profile.reminderTime')}
          type="time"
          required
          value={reminderTime}
          onChange={(event) => setReminderTime(event.target.value)}
          hint={t('profile.reminderTimeHint')}
        />
      ) : null}

      <p className="form-hint">
        {t('profile.notificationsTimezoneHint', { timezone })}
      </p>

      <div className="button-row">
        <button type="submit" className="button" disabled={isSaving}>
          {isSaving ? t('common.saving') : t('profile.saveNotifications')}
        </button>
      </div>
    </form>
  )
}
