import type { UserPublic } from '../types/auth'
import { hasAppAccess } from './authAccess'
import { getAccessToken } from './storage'

let guestLocalDiaryEnabled = false
let visitorId: string | null = null

export function setGuestExperimentState(enabled: boolean, id: string | null): void {
  guestLocalDiaryEnabled = enabled
  visitorId = id
}

export function isGuestLocalDiaryEnabled(): boolean {
  return guestLocalDiaryEnabled
}

export function getVisitorId(): string | null {
  return visitorId
}

/** Guest diary mode: treatment cohort and not signed in. */
export function isGuestDiaryMode(): boolean {
  return guestLocalDiaryEnabled && !getAccessToken()
}

export function isGuestTreatmentShell(): boolean {
  return isGuestDiaryMode()
}

/** Verified identity (email or Telegram) or active guest diary experiment. */
export function canUseDiaryFeatures(user: UserPublic | null): boolean {
  return hasAppAccess(user) || isGuestDiaryMode()
}
