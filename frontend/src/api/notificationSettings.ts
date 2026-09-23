import { apiRequest } from './client'
import { apiLocaleHeaders } from '../lib/locale'
import type {
  NotificationSettingsPublic,
  NotificationSettingsUpdate,
} from '../types/notificationSettings'

export function getNotificationSettings(): Promise<NotificationSettingsPublic> {
  return apiRequest<NotificationSettingsPublic>('/v1/notification-settings', {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function patchNotificationSettings(
  body: NotificationSettingsUpdate,
): Promise<NotificationSettingsPublic> {
  return apiRequest<NotificationSettingsPublic>('/v1/notification-settings', {
    method: 'PATCH',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}
