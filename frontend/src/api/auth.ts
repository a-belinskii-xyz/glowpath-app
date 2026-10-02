import { apiRequest, getApiBaseUrl } from './client'
import type { ThemePreference } from '../design/themePreference'
import type { ApiLocale } from '../lib/locale'
import { getSignupSource } from '../lib/signupSource'
import type {
  LoginRequest,
  MessageResponse,
  PasswordResetRequestResponse,
  RegisterRequest,
  ResetPasswordRequest,
  TelegramBotLoginPoll,
  TelegramBotLoginStart,
  TokenResponse,
  UserPublic,
  VerificationResendResponse,
} from '../types/auth'

export function register(body: RegisterRequest): Promise<MessageResponse> {
  return apiRequest<MessageResponse>('/v1/auth/register', { method: 'POST', body })
}

export function verifyEmail(token: string): Promise<MessageResponse> {
  return apiRequest<MessageResponse>(
    `/v1/auth/verify-email?token=${encodeURIComponent(token)}`,
  )
}

export function resendVerification(email: string): Promise<VerificationResendResponse> {
  return apiRequest<VerificationResendResponse>('/v1/auth/resend-verification', {
    method: 'POST',
    body: { email },
  })
}

export function login(body: LoginRequest): Promise<TokenResponse> {
  return apiRequest<TokenResponse>('/v1/auth/login', { method: 'POST', body })
}

export function refresh(refreshToken: string): Promise<TokenResponse> {
  return apiRequest<TokenResponse>('/v1/auth/refresh', {
    method: 'POST',
    body: { refresh_token: refreshToken },
    retryOnUnauthorized: false,
  })
}

export function forgotPassword(email: string): Promise<PasswordResetRequestResponse> {
  return apiRequest<PasswordResetRequestResponse>('/v1/auth/forgot-password', {
    method: 'POST',
    body: { email },
  })
}

export function resetPassword(body: ResetPasswordRequest): Promise<MessageResponse> {
  return apiRequest<MessageResponse>('/v1/auth/reset-password', { method: 'POST', body })
}

export function getMe(): Promise<UserPublic> {
  return apiRequest<UserPublic>('/v1/auth/me', { auth: true })
}

export function updateMe(body: {
  timezone?: string
  theme_preference?: ThemePreference
  locale?: ApiLocale
}): Promise<UserPublic> {
  return apiRequest<UserPublic>('/v1/auth/me', {
    method: 'PATCH',
    body,
    auth: true,
  })
}

export function attachEmail(body: {
  email: string
  password: string
  password_confirm: string
}): Promise<UserPublic> {
  return apiRequest<UserPublic>('/v1/auth/attach-email', {
    method: 'POST',
    body,
    auth: true,
  })
}

export function loginTelegram(body: {
  init_data: string
  timezone: string
  signup_source?: string
}): Promise<TokenResponse> {
  return apiRequest<TokenResponse>('/v1/auth/telegram', { method: 'POST', body })
}

export function getGoogleLoginUrl(): string {
  return `${getApiBaseUrl()}/v1/auth/google/login`
}

export function getTelegramBrowserLoginUrl(timezone: string): string {
  const params = new URLSearchParams({ timezone })
  const signupSource = getSignupSource()
  if (signupSource) {
    params.set('signup_source', signupSource)
  }
  return `${getApiBaseUrl()}/v1/auth/telegram/login?${params.toString()}`
}

export function startTelegramBotLogin(timezone: string): Promise<TelegramBotLoginStart> {
  return apiRequest<TelegramBotLoginStart>('/v1/auth/telegram/bot-login', {
    method: 'POST',
    body: { timezone, signup_source: getSignupSource() },
  })
}

export function pollTelegramBotLogin(pollToken: string): Promise<TelegramBotLoginPoll> {
  return apiRequest<TelegramBotLoginPoll>('/v1/auth/telegram/bot-login/poll', {
    method: 'POST',
    body: { poll_token: pollToken },
  })
}
