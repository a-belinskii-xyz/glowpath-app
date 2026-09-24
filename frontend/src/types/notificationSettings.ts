export type NotificationChannel = 'email' | 'telegram'

export type NotificationScheduleKind = 'daily_mood' | 'goal_tracking' | 'weekly_digest' | 'custom_reminder'

export type WorkerLiveness = 'healthy' | 'degraded' | 'offline'

export type NotificationStatusCode = 'OK' | 'DISABLED_STAGE_TESTING' | 'WORKER_OFFLINE'

export type NotificationSystemStatus = {
  feature_enabled: boolean
  worker_status: WorkerLiveness
  status_code: NotificationStatusCode
  message: string
}

export type NotificationSchedule = {
  kind: NotificationScheduleKind
  enabled: boolean
  time_of_day: string
  interval_days: number
  days_of_week: number[] | null
  channels: NotificationChannel[]
  last_sent_at: string | null
}

export type NotificationSettingsPublic = {
  system_status: NotificationSystemStatus
  schedules: NotificationSchedule[]
}

export type NotificationScheduleUpdate = {
  enabled?: boolean
  time_of_day?: string
  interval_days?: number
  days_of_week?: number[] | null
  channels?: NotificationChannel[]
}
