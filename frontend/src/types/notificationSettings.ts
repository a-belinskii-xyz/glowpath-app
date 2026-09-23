export type NotificationChannel = 'email' | 'telegram'

export type NotificationSettingsPublic = {
  enabled: boolean
  channels: NotificationChannel[]
  daily_mood_reminder_enabled: boolean
  daily_mood_reminder_time: string | null
  goal_reminders_enabled: boolean
}

export type NotificationSettingsUpdate = {
  enabled?: boolean
  channels?: NotificationChannel[]
  daily_mood_reminder_enabled?: boolean
  daily_mood_reminder_time?: string | null
  goal_reminders_enabled?: boolean
}
