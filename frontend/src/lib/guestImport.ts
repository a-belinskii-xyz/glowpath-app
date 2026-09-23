import { getVisitorId } from './guestMode'
import { buildGuestImportPayload, clearGuestDiary } from '../guest/store'
import { importGuestDiary } from '../api/guest'

export async function tryImportGuestDiaryAfterAuth(_userCreated?: boolean): Promise<void> {
  const visitorId = getVisitorId()
  if (!visitorId) {
    return
  }
  const payload = await buildGuestImportPayload()
  const entryCount = Array.isArray(payload.entries) ? payload.entries.length : 0
  if (entryCount === 0 && !(payload.meta as { onboarding_completed?: boolean } | undefined)?.onboarding_completed) {
    return
  }
  try {
    const result = await importGuestDiary({ visitor_id: visitorId, payload })
    if (!result.skipped) {
      await clearGuestDiary()
    }
  } catch {
    // keep local data if import rejected (existing account login)
  }
}

export async function getGuestLocalEntryCount(): Promise<number> {
  const payload = await buildGuestImportPayload()
  return Array.isArray(payload.entries) ? payload.entries.length : 0
}
