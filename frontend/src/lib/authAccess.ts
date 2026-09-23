import type { UserPublic } from '../types/auth'

/** True when the user may call verified application APIs (email or Telegram). */
export function hasAppAccess(user: UserPublic | null | undefined): boolean {
  if (!user) {
    return false
  }
  return user.email_verified || user.telegram_linked
}
