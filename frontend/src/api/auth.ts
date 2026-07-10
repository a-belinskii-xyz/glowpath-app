import { apiRequest, getApiBaseUrl } from './client'
import type {
  LoginRequest,
  MessageResponse,
  PasswordResetRequestResponse,
  RegisterRequest,
  ResetPasswordRequest,
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

export function getGoogleLoginUrl(): string {
  return `${getApiBaseUrl()}/v1/auth/google/login`
}
