import { entriesListPathForInstant } from './datetime'

export type EntryReaderLocationState = {
  from?: string
  backTo?: string
}

export function entryReaderBackHref(
  entry: { id: string; recorded_at: string },
  timeZone: string,
  from?: string,
): string {
  if (from === '/gallery') {
    return '/gallery'
  }
  return entriesListPathForInstant(entry.recorded_at, timeZone, entry.id)
}
