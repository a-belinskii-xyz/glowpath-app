import type { ThemePreference } from '../design/themePreference'
import type { ApiLocale } from '../lib/locale'
import type { TimeFormat } from '../lib/timeFormat'

export type UserPublic = {
  id: string
  email: string | null
  timezone: string
  email_verified: boolean
  email_verified_at: string | null
  onboarding_completed: boolean
  onboarding_completed_at: string | null
  has_password: boolean
  is_staff?: boolean
  theme_preference: ThemePreference
  /** Clock shown and typed everywhere: device default, 24-hour or AM/PM. */
  time_format: TimeFormat
  /** How the app addresses the user; null means neutral phrases only (GP-57). */
  display_name: string | null
  /** Interface language saved on the account; null until the app has sent it. */
  locale: ApiLocale | null
  telegram_linked: boolean
  can_unlink_telegram: boolean
  features: Record<string, boolean>
  plan: string
  entitlements: string[]
}

export type TokenResponse = {
  access_token: string
  refresh_token: string
  token_type: string
  user_created?: boolean
}

export type MessageResponse = {
  message: string
}

export type VerificationResendStatus =
  | 'email_sent'
  | 'already_verified'
  | 'request_accepted'

export type VerificationResendResponse = {
  message: string
  status: VerificationResendStatus
}

export type PasswordResetRequestStatus = 'email_sent' | 'request_accepted'

export type PasswordResetRequestResponse = {
  message: string
  status: PasswordResetRequestStatus
}

export type RegisterRequest = {
  email: string
  password: string
  password_confirm: string
  timezone: string
  visitor_id?: string
}

export type LoginRequest = {
  email: string
  password: string
  visitor_id?: string
}

export type ResetPasswordRequest = {
  token: string
  new_password: string
  password_confirm: string
}

export type TelegramBotLoginStart = {
  poll_token: string
  deep_link: string
  expires_at: string
}

export type TelegramBotLoginPoll = {
  status: 'pending' | 'confirmed' | 'expired'
  access_token: string | null
  refresh_token: string | null
  user_created: boolean | null
}
