export type UserPublic = {
  id: string
  email: string
  timezone: string
  email_verified: boolean
  email_verified_at: string | null
  onboarding_completed: boolean
  onboarding_completed_at: string | null
  has_password: boolean
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
