import { useEffect, useRef, useState } from 'react'

import { getNotificationSettings, patchNotificationSchedule } from '../api/notificationSettings'
import { getTelegramLink } from '../api/telegram'
import { PageErrorAlert } from './PageErrorAlert'
import { TestingStageNotice, WorkerOfflineNotice } from './NotificationNotices'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { useNotificationStatus } from '../hooks/useNotificationStatus'
import { ApiError, formatApiError } from '../lib/errors'
import type {
  NotificationChannel,
  NotificationSchedule,
  NotificationScheduleKind,
} from '../types/notificationSettings'

const TIME_SAVE_DELAY_MS = 400
const VISIBLE_KINDS: NotificationScheduleKind[] = ['daily_mood', 'goal_tracking']
const INTERVAL_OPTIONS = [1, 2, 3, 7] as const

type ScheduleDraft = {
  enabled: boolean
  timeOfDay: string
  intervalDays: number
  telegramChannel: boolean
}

function draftFromSchedule(schedule: NotificationSchedule): ScheduleDraft {
  return {
    enabled: schedule.enabled,
    timeOfDay: schedule.time_of_day.slice(0, 5),
    intervalDays: schedule.interval_days,
    telegramChannel: schedule.channels.includes('telegram'),
  }
}

export function NotificationSettingsForm({ timezone }: { timezone: string }) {
  const { t } = useLocale()
  const { user } = useAuth()
  const { status, isLoading: statusLoading, error: statusError } = useNotificationStatus()
  const [drafts, setDrafts] = useState<Partial<Record<NotificationScheduleKind, ScheduleDraft>>>({})
  const draftsRef = useRef(drafts)
  draftsRef.current = drafts
  const [telegramLinked, setTelegramLinked] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [savingKind, setSavingKind] = useState<NotificationScheduleKind | null>(null)
  const [error, setError] = useState<string | null>(null)
  const timeTimers = useRef<Partial<Record<NotificationScheduleKind, number>>>({})

  const locked = status?.status_code === 'DISABLED_STAGE_TESTING'
  const showEmailChannel = Boolean(user?.email)
  const telegramRequired = Boolean(user?.telegram_linked && !user.email)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setIsLoading(true)
      try {
        const [settings, telegram] = await Promise.all([
          getNotificationSettings(),
          getTelegramLink().catch(() => null),
        ])
        if (cancelled) {
          return
        }
        const nextDrafts: Partial<Record<NotificationScheduleKind, ScheduleDraft>> = {}
        for (const schedule of settings.schedules) {
          if (VISIBLE_KINDS.includes(schedule.kind)) {
            nextDrafts[schedule.kind] = draftFromSchedule(schedule)
          }
        }
        setDrafts(nextDrafts)
        setTelegramLinked(telegram?.linked === true)
        setError(null)
      } catch (err) {
        if (cancelled) {
          return
        }
        if (err instanceof ApiError && err.status === 403) {
          setError(t('errors.verifyToManageNotifications'))
        } else {
          setError(formatApiError(err, t, 'errors.failedLoadNotifications'))
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [t])

  useEffect(() => {
    const timers = timeTimers.current
    return () => {
      for (const timer of Object.values(timers)) {
        if (timer !== undefined) {
          window.clearTimeout(timer)
        }
      }
    }
  }, [])

  useEffect(() => {
    if (!statusError) {
      return
    }
    setError(formatApiError(statusError, t, 'errors.failedLoadNotifications'))
  }, [statusError, t])

  const persist = async (kind: NotificationScheduleKind, draft: ScheduleDraft) => {
    if (locked) {
      return
    }
    const channels: NotificationChannel[] = []
    if (user?.email) {
      channels.push('email')
    }
    const telegramOn = Boolean(user?.telegram_linked) && (draft.telegramChannel || !user?.email)
    if (telegramOn || (telegramLinked && draft.telegramChannel)) {
      channels.push('telegram')
    }
    if (channels.length === 0) {
      setError(t('profile.reminderTimeRequired'))
      return
    }
    setSavingKind(kind)
    setError(null)
    try {
      const saved = await patchNotificationSchedule(kind, {
        enabled: draft.enabled,
        time_of_day: draft.timeOfDay,
        interval_days: draft.intervalDays,
        channels,
      })
      setDrafts((current) => {
        const next = { ...current }
        for (const schedule of saved.schedules) {
          if (VISIBLE_KINDS.includes(schedule.kind)) {
            next[schedule.kind] = draftFromSchedule(schedule)
          }
        }
        return next
      })
    } catch (err) {
      if (err instanceof ApiError && err.code === 'feature_disabled') {
        setError(t('errors.featureDisabled'))
      } else if (err instanceof ApiError && err.status === 403) {
        setError(t('errors.verifyToManageNotifications'))
      } else {
        setError(formatApiError(err, t, 'errors.failedSave'))
      }
    } finally {
      setSavingKind(null)
    }
  }

  const updateDraft = (
    kind: NotificationScheduleKind,
    patch: Partial<ScheduleDraft>,
    options?: { debounce?: boolean },
  ) => {
    const current = drafts[kind]
    if (!current || locked) {
      return
    }
    const next = { ...current, ...patch }
    setDrafts((prev) => ({ ...prev, [kind]: next }))
    if (options?.debounce) {
      const pending = timeTimers.current[kind]
      if (pending !== undefined) {
        window.clearTimeout(pending)
      }
      timeTimers.current[kind] = window.setTimeout(() => {
        timeTimers.current[kind] = undefined
        const latest = draftsRef.current[kind]
        if (latest) {
          void persist(kind, latest)
        }
      }, TIME_SAVE_DELAY_MS)
      return
    }
    void persist(kind, next)
  }

  if (isLoading || statusLoading) {
    return <p className="muted">{t('common.loadingNotifications')}</p>
  }

  return (
    <form
      className="card form profile-notifications-form"
      aria-busy={savingKind !== null}
      onSubmit={(event) => event.preventDefault()}
    >
      <PageErrorAlert error={error} />
      {status?.status_code === 'DISABLED_STAGE_TESTING' ? <TestingStageNotice /> : null}
      {status?.status_code === 'WORKER_OFFLINE' ? <WorkerOfflineNotice /> : null}

      {VISIBLE_KINDS.map((kind) => {
        const draft = drafts[kind]
        if (!draft) {
          return null
        }
        const displayedEnabled = locked ? false : draft.enabled
        return (
          <fieldset key={kind} className="notification-group" disabled={locked}>
            <legend className="notification-group-title">
              {kind === 'daily_mood' ? t('profile.dailyMoodReminder') : t('profile.goalReminders')}
            </legend>
            <label className="tag-visibility-toggle">
              <input
                type="checkbox"
                checked={displayedEnabled}
                onChange={(event) => updateDraft(kind, { enabled: event.target.checked })}
              />
              <span>{t('profile.scheduleEnabled')}</span>
            </label>
            <label className="form-field" htmlFor={`${kind}-time`}>
              <span className="form-label">{t('profile.reminderTime')}</span>
              <input
                id={`${kind}-time`}
                className="form-input"
                type="time"
                value={draft.timeOfDay}
                onChange={(event) =>
                  updateDraft(kind, { timeOfDay: event.target.value }, { debounce: true })
                }
              />
            </label>
            <label className="form-field" htmlFor={`${kind}-interval`}>
              <span className="form-label">{t('profile.reminderFrequency')}</span>
              <select
                id={`${kind}-interval`}
                className="form-input"
                value={draft.intervalDays}
                onChange={(event) =>
                  updateDraft(kind, { intervalDays: Number(event.target.value) })
                }
              >
                {INTERVAL_OPTIONS.map((days) => (
                  <option key={days} value={days}>
                    {t(`profile.intervalDays.${days}`)}
                  </option>
                ))}
              </select>
            </label>
            <div className="notification-channel-row">
              <span>{t('profile.notificationChannels')}</span>
            </div>
            {showEmailChannel ? (
              <div className="notification-channel-row">
                <span>{t('profile.channelEmail')}</span>
                <span className="status-pill status-pill--ok status-pill--sm">
                  {t('profile.channelAlwaysOn')}
                </span>
              </div>
            ) : null}
            <label
              className={
                telegramLinked
                  ? 'tag-visibility-toggle'
                  : 'tag-visibility-toggle notification-channel-disabled'
              }
            >
              <input
                type="checkbox"
                checked={telegramLinked && (draft.telegramChannel || telegramRequired)}
                disabled={!telegramLinked || telegramRequired || locked}
                onChange={(event) => updateDraft(kind, { telegramChannel: event.target.checked })}
              />
              <span>
                {telegramLinked ? t('profile.channelTelegram') : t('profile.channelTelegramLinkFirst')}
              </span>
            </label>
          </fieldset>
        )
      })}

      <p className="form-hint">{t('profile.notificationsTimezoneHint', { timezone })}</p>
    </form>
  )
}
