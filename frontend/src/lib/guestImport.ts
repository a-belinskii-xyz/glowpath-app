import { getVisitorId } from './guestMode'
import { buildGuestImportPayload, clearGuestDiary } from '../guest/store'
import { importGuestDiary } from '../api/guest'
import { isTelegramMiniApp } from '../platform/telegram'

/** Guest entries in this browser that could move into the account just signed in to. */
export type PendingGuestImport = {
  visitorId: string
  entryCount: number
}

export async function tryImportGuestDiaryAfterAuth(): Promise<void> {
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
    await importGuestDiaryNow(visitorId)
  } catch {
    // keep local data if the import was rejected
  }
}

/** For an account that already existed: the person decides whether to move the entries. */
export async function findPendingGuestImport(): Promise<PendingGuestImport | null> {
  const visitorId = getVisitorId()
  if (!visitorId || isTelegramMiniApp()) {
    return null
  }
  const entryCount = await getGuestLocalEntryCount()
  return entryCount > 0 ? { visitorId, entryCount } : null
}

export async function importGuestDiaryNow(visitorId: string): Promise<number> {
  const payload = await buildGuestImportPayload()
  const result = await importGuestDiary({ visitor_id: visitorId, payload })
  if (!result.skipped) {
    await clearGuestDiary()
  }
  return result.imported_entries
}

export async function getGuestLocalEntryCount(): Promise<number> {
  const payload = await buildGuestImportPayload()
  return Array.isArray(payload.entries) ? payload.entries.length : 0
}
