export type UserPublic = {
  id: string
  email: string
  timezone: string
  email_verified: boolean
  email_verified_at: string | null
}

export type TokenResponse = {
  access_token: string
  refresh_token: string
  token_type: string
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
}

export type LoginRequest = {
  email: string
  password: string
}

export type ResetPasswordRequest = {
  token: string
  new_password: string
  password_confirm: string
}
