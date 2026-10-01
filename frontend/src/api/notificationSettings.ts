import { apiRequest } from './client'
import { apiLocaleHeaders } from '../lib/locale'
import type {
  NotificationScheduleUpdate,
  NotificationSettingsPublic,
  NotificationSystemStatus,
} from '../types/notificationSettings'

export function getNotificationStatus(): Promise<NotificationSystemStatus> {
  return apiRequest<NotificationSystemStatus>('/v1/notification-settings/status', {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function getNotificationSettings(): Promise<NotificationSettingsPublic> {
  return apiRequest<NotificationSettingsPublic>('/v1/notification-settings', {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function patchNotificationSchedule(
  kind: string,
  body: NotificationScheduleUpdate,
): Promise<NotificationSettingsPublic> {
  return apiRequest<NotificationSettingsPublic>(`/v1/notification-settings/${kind}`, {
    method: 'PATCH',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}

export function unsubscribeFromEmails(token: string): Promise<{ unsubscribed: boolean }> {
  return apiRequest<{ unsubscribed: boolean }>(
    `/v1/notification-settings/unsubscribe?${new URLSearchParams({ token }).toString()}`,
    { method: 'POST' },
  )
}
