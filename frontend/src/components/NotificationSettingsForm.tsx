import { useEffect, useRef, useState } from 'react'

import {
  getNotificationSettings,
  patchNotificationSettings,
} from '../api/notificationSettings'
import { getTelegramLink } from '../api/telegram'
import { PageErrorAlert } from './PageErrorAlert'
import { FormField } from './FormField'
import { useLocale } from '../context/LocaleContext'
import { ApiError, formatApiError } from '../lib/errors'
import type { NotificationChannel, NotificationSettingsPublic } from '../types/notificationSettings'

const DEFAULT_REMINDER_TIME = '20:00'
const TIME_SAVE_DELAY_MS = 400

type SettingsDraft = {
  enabled: boolean
  dailyMood: boolean
  goalReminders: boolean
  reminderTime: string
  telegramChannel: boolean
}

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

function draftFromSettings(settings: NotificationSettingsPublic): SettingsDraft {
  return {
    enabled: settings.enabled,
    dailyMood: settings.daily_mood_reminder_enabled,
    goalReminders: settings.goal_reminders_enabled,
    reminderTime: apiTimeToInput(settings.daily_mood_reminder_time),
    telegramChannel: settings.channels.includes('telegram'),
  }
}

function draftsEqual(left: SettingsDraft, right: SettingsDraft): boolean {
  return (
    left.enabled === right.enabled &&
    left.dailyMood === right.dailyMood &&
    left.goalReminders === right.goalReminders &&
    left.reminderTime === right.reminderTime &&
    left.telegramChannel === right.telegramChannel
  )
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

  const draftRef = useRef<SettingsDraft>({
    enabled: false,
    dailyMood: false,
    goalReminders: false,
    reminderTime: '',
    telegramChannel: false,
  })
  const lastSavedRef = useRef<SettingsDraft | null>(null)
  const telegramLinkedRef = useRef(false)
  const persistChainRef = useRef(Promise.resolve())
  const persistRef = useRef<() => Promise<void>>(async () => {})
  const timeTimerRef = useRef<number | null>(null)
  const persistGenerationRef = useRef(0)
  const mountedRef = useRef(true)

  telegramLinkedRef.current = telegramLinked

  const applyDraft = (next: SettingsDraft) => {
    draftRef.current = next
    setEnabled(next.enabled)
    setDailyMood(next.dailyMood)
    setGoalReminders(next.goalReminders)
    setReminderTime(next.reminderTime)
    setTelegramChannel(next.telegramChannel)
  }

  const applySettings = (settings: NotificationSettingsPublic) => {
    const next = draftFromSettings(settings)
    lastSavedRef.current = next
    applyDraft(next)
  }

  useEffect(() => {
    mountedRef.current = true
    const load = async () => {
      setIsLoading(true)
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
          setError(formatApiError(err, t, 'errors.failedLoadNotifications'))
        }
      } finally {
        setIsLoading(false)
      }
    }
    void load()
    return () => {
      mountedRef.current = false
      persistGenerationRef.current += 1
      if (timeTimerRef.current !== null) {
        window.clearTimeout(timeTimerRef.current)
        timeTimerRef.current = null
      }
      void persistRef.current()
    }
  }, [t])

  const persist = () => {
    persistChainRef.current = persistChainRef.current
      .catch(() => undefined)
      .then(async () => {
        while (true) {
          const draft = { ...draftRef.current }
          if (!lastSavedRef.current || draftsEqual(draft, lastSavedRef.current)) {
            return
          }

          const needsTime = draft.enabled && (draft.dailyMood || draft.goalReminders)
          if (needsTime && !draft.reminderTime) {
            if (mountedRef.current) {
              setError(t('profile.reminderTimeRequired'))
            }
            return
          }

          const channels: NotificationChannel[] = ['email']
          if (draft.telegramChannel && telegramLinkedRef.current) {
            channels.push('telegram')
          }

          const generation = persistGenerationRef.current
          if (mountedRef.current) {
            setIsSaving(true)
            setError(null)
          }
          try {
            const saved = await patchNotificationSettings({
              enabled: draft.enabled,
              channels,
              daily_mood_reminder_enabled: draft.dailyMood,
              daily_mood_reminder_time: draft.reminderTime
                ? inputToApiTime(draft.reminderTime)
                : null,
              goal_reminders_enabled: draft.goalReminders,
            })
            if (generation !== persistGenerationRef.current) {
              return
            }
            lastSavedRef.current = draftFromSettings(saved)
            if (!draftsEqual(draft, draftRef.current)) {
              continue
            }
            if (mountedRef.current) {
              applySettings(saved)
            }
            return
          } catch (err) {
            if (!mountedRef.current) {
              return
            }
            if (err instanceof ApiError && err.status === 403) {
              setError(t('errors.verifyToManageNotifications'))
            } else {
              setError(formatApiError(err, t, 'errors.failedSave'))
            }
            return
          } finally {
            if (mountedRef.current) {
              setIsSaving(false)
            }
          }
        }
      })
    return persistChainRef.current
  }

  persistRef.current = persist

  const commitDraft = (patch: Partial<SettingsDraft>, options?: { debounce?: boolean }) => {
    const next = { ...draftRef.current, ...patch }
    if ((patch.dailyMood === true || patch.goalReminders === true) && !next.reminderTime) {
      next.reminderTime = DEFAULT_REMINDER_TIME
    }
    applyDraft(next)

    if (options?.debounce) {
      if (timeTimerRef.current !== null) {
        window.clearTimeout(timeTimerRef.current)
      }
      timeTimerRef.current = window.setTimeout(() => {
        timeTimerRef.current = null
        void persist()
      }, TIME_SAVE_DELAY_MS)
      return
    }

    if (timeTimerRef.current !== null) {
      window.clearTimeout(timeTimerRef.current)
      timeTimerRef.current = null
    }
    void persist()
  }

  const needsReminderTime = enabled && (dailyMood || goalReminders)

  if (isLoading) {
    return <p className="muted">{t('common.loadingNotifications')}</p>
  }

  return (
    <form
      className="card form profile-notifications-form"
      aria-busy={isSaving}
      onSubmit={(event) => event.preventDefault()}
    >
      <PageErrorAlert error={error} />

      <label className="notification-master">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(event) => commitDraft({ enabled: event.target.checked })}
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
            onChange={(event) => commitDraft({ telegramChannel: event.target.checked })}
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
            onChange={(event) => commitDraft({ dailyMood: event.target.checked })}
          />
          <span>{t('profile.dailyMoodReminder')}</span>
        </label>
        <label className="tag-visibility-toggle">
          <input
            type="checkbox"
            checked={goalReminders}
            onChange={(event) => commitDraft({ goalReminders: event.target.checked })}
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
          onChange={(event) => commitDraft({ reminderTime: event.target.value }, { debounce: true })}
          onBlur={() => {
            if (timeTimerRef.current !== null) {
              window.clearTimeout(timeTimerRef.current)
              timeTimerRef.current = null
            }
            void persist()
          }}
          hint={t('profile.reminderTimeHint')}
        />
      ) : null}

      <p className="form-hint">
        {t('profile.notificationsTimezoneHint', { timezone })}
      </p>
    </form>
  )
}
