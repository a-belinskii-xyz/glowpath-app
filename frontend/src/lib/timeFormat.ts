/** The user's clock (GP-53): "auto" follows the device, "24h" / "12h" force one everywhere. */

export type TimeFormat = 'auto' | '24h' | '12h'
export const TIME_FORMATS: TimeFormat[] = ['auto', '24h', '12h']

let preference: TimeFormat = 'auto'

/** Set by AuthContext from the account, so plain helpers can format without a hook. */
export function setTimeFormatPreference(next: TimeFormat): void {
  preference = next
}

function deviceUses12h(): boolean {
  try {
    // resolvedOptions().hour12 is true on devices set to a 12-hour clock.
    return new Intl.DateTimeFormat(undefined, { hour: 'numeric' }).resolvedOptions().hour12 === true
  } catch {
    return false
  }
}

export function uses12h(): boolean {
  return preference === 'auto' ? deviceUses12h() : preference === '12h'
}

/**
 * Minutes since midnight as the user's clock: "23:40" or "11:40 PM".
 * ``short`` drops ":00" in 12-hour mode for chart ticks ("10 PM").
 */
export function formatClockMinutes(minutes: number, options: { short?: boolean } = {}): string {
  const value = ((Math.round(minutes) % 1440) + 1440) % 1440
  const hours = Math.floor(value / 60)
  const mins = String(value % 60).padStart(2, '0')
  if (!uses12h()) return `${String(hours).padStart(2, '0')}:${mins}`
  const period = hours < 12 ? 'AM' : 'PM'
  const hour12 = hours % 12 === 0 ? 12 : hours % 12
  return options.short && mins === '00' ? `${hour12} ${period}` : `${hour12}:${mins} ${period}`
}

/** "23:40" or "23:40:00" → the user's clock. */
export function formatClockString(value: string): string {
  const [hours, minutes] = value.split(':').map(Number)
  return formatClockMinutes(hours * 60 + minutes)
}
