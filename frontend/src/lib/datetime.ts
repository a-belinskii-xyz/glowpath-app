function parseGmtOffset(value: string): string {
  const match = value.match(/GMT([+-])(\d{1,2})(?::?(\d{2}))?/)
  if (!match) {
    return '+00:00'
  }
  const sign = match[1]
  const hours = match[2].padStart(2, '0')
  const minutes = (match[3] ?? '00').padStart(2, '0')
  return `${sign}${hours}:${minutes}`
}

function getOffsetForInstant(instant: Date, timeZone: string): string {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone,
    timeZoneName: 'longOffset',
  }).formatToParts(instant)
  const tzName = parts.find((part) => part.type === 'timeZoneName')?.value ?? 'GMT'
  return parseGmtOffset(tzName)
}

function formatLocalParts(instant: Date, timeZone: string) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).formatToParts(instant)

  const get = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value ?? '00'

  return {
    year: Number(get('year')),
    month: Number(get('month')),
    day: Number(get('day')),
    hour: Number(get('hour')),
    minute: Number(get('minute')),
    second: Number(get('second')),
  }
}

function zonedLocalToUtc(
  year: number,
  month: number,
  day: number,
  hour: number,
  minute: number,
  second: number,
  timeZone: string,
): Date {
  let guess = Date.UTC(year, month - 1, day, hour, minute, second)
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const instant = new Date(guess)
    const local = formatLocalParts(instant, timeZone)
    const asUtc = Date.UTC(
      local.year,
      local.month - 1,
      local.day,
      local.hour,
      local.minute,
      local.second,
    )
    const desired = Date.UTC(year, month - 1, day, hour, minute, second)
    const delta = desired - asUtc
    guess += delta
    if (delta === 0) {
      break
    }
  }
  return new Date(guess)
}

export function instantToIsoInTimezone(instant: Date, timeZone: string): string {
  const local = formatLocalParts(instant, timeZone)
  const offset = getOffsetForInstant(instant, timeZone)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${local.year}-${pad(local.month)}-${pad(local.day)}T${pad(local.hour)}:${pad(local.minute)}:${pad(local.second)}${offset}`
}

export function datetimeLocalToIso(value: string, timeZone: string): string {
  const [datePart, timePart = '00:00'] = value.split('T')
  const [year, month, day] = datePart.split('-').map(Number)
  const [hour, minute] = timePart.split(':').map(Number)
  const utc = zonedLocalToUtc(year, month, day, hour, minute, 0, timeZone)
  return instantToIsoInTimezone(utc, timeZone)
}

export function isoToDatetimeLocal(iso: string, timeZone: string): string {
  const instant = new Date(iso)
  const local = formatLocalParts(instant, timeZone)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${local.year}-${pad(local.month)}-${pad(local.day)}T${pad(local.hour)}:${pad(local.minute)}`
}

export function nowDatetimeLocal(timeZone: string): string {
  return isoToDatetimeLocal(new Date().toISOString(), timeZone)
}

export function getMonthBounds(
  year: number,
  month: number,
  timeZone: string,
): { recorded_from: string; recorded_to: string } {
  const fromUtc = zonedLocalToUtc(year, month + 1, 1, 0, 0, 0, timeZone)
  const nextYear = month === 11 ? year + 1 : year
  const nextMonth = month === 11 ? 0 : month + 1
  const toUtc = zonedLocalToUtc(nextYear, nextMonth + 1, 1, 0, 0, 0, timeZone)
  return {
    recorded_from: instantToIsoInTimezone(fromUtc, timeZone),
    recorded_to: instantToIsoInTimezone(toUtc, timeZone),
  }
}

/** Shift a `YYYY-MM-DD` calendar date by a whole number of days. */
export function shiftDateKey(dateKey: string, days: number): string {
  const [year, month, day] = dateKey.split('-').map(Number)
  const utc = new Date(Date.UTC(year, month - 1, day + days))
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${utc.getUTCFullYear()}-${pad(utc.getUTCMonth() + 1)}-${pad(utc.getUTCDate())}`
}

/** Half-open `[week_start, week_end)` ISO week bounds containing `dateKey` (YYYY-MM-DD). */
export function getIsoWeekBounds(
  dateKey: string,
  timeZone: string,
): { recorded_from: string; recorded_to: string; period_start: string; period_end: string } {
  const [year, month, day] = dateKey.split('-').map(Number)
  const utcDay = new Date(Date.UTC(year, month - 1, day))
  const mondayOffset = (utcDay.getUTCDay() + 6) % 7
  const weekStartUtc = new Date(Date.UTC(year, month - 1, day - mondayOffset))
  const weekEndUtc = new Date(Date.UTC(year, month - 1, day - mondayOffset + 7))
  const pad = (value: number) => String(value).padStart(2, '0')
  const period_start = `${weekStartUtc.getUTCFullYear()}-${pad(weekStartUtc.getUTCMonth() + 1)}-${pad(weekStartUtc.getUTCDate())}`
  const period_end = `${weekEndUtc.getUTCFullYear()}-${pad(weekEndUtc.getUTCMonth() + 1)}-${pad(weekEndUtc.getUTCDate())}`
  const [startY, startM, startD] = period_start.split('-').map(Number)
  const [endY, endM, endD] = period_end.split('-').map(Number)
  const fromUtc = zonedLocalToUtc(startY, startM, startD, 0, 0, 0, timeZone)
  const toUtc = zonedLocalToUtc(endY, endM, endD, 0, 0, 0, timeZone)
  return {
    recorded_from: instantToIsoInTimezone(fromUtc, timeZone),
    recorded_to: instantToIsoInTimezone(toUtc, timeZone),
    period_start,
    period_end,
  }
}

/**
 * Human-readable ISO week range. `periodEndExclusive` is the Monday after the week
 * (half-open end from `getIsoWeekBounds`).
 */
export function formatWeekHeading(
  periodStart: string,
  periodEndExclusive: string,
  locale = 'en-GB',
): string {
  const periodEndInclusive = shiftDateKey(periodEndExclusive, -1)
  const [startY, startM, startD] = periodStart.split('-').map(Number)
  const [endY, endM, endD] = periodEndInclusive.split('-').map(Number)
  const start = new Date(Date.UTC(startY, startM - 1, startD))
  const end = new Date(Date.UTC(endY, endM - 1, endD))

  if (startY === endY && startM === endM) {
    const dayFmt = new Intl.DateTimeFormat(locale, { day: 'numeric' })
    const monthYearFmt = new Intl.DateTimeFormat(locale, { month: 'short', year: 'numeric' })
    return `${dayFmt.format(start)}–${dayFmt.format(end)} ${monthYearFmt.format(end)}`
  }
  if (startY === endY) {
    const dayMonthFmt = new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short' })
    const yearFmt = new Intl.DateTimeFormat(locale, { year: 'numeric' })
    return `${dayMonthFmt.format(start)} – ${dayMonthFmt.format(end)} ${yearFmt.format(end)}`
  }
  const fullFmt = new Intl.DateTimeFormat(locale, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
  return `${fullFmt.format(start)} – ${fullFmt.format(end)}`
}

/** First day of month as `YYYY-MM-DD`. `month` is 0-indexed. */
export function monthStartKey(year: number, month: number): string {
  return `${year}-${String(month + 1).padStart(2, '0')}-01`
}

/** Day after last day of month as `YYYY-MM-DD`. `month` is 0-indexed. */
export function monthEndExclusiveKey(year: number, month: number): string {
  const nextYear = month === 11 ? year + 1 : year
  const nextMonth = month === 11 ? 0 : month + 1
  return monthStartKey(nextYear, nextMonth)
}

/** Half-open ISO week `[periodStart, periodEnd)` overlaps calendar month. */
export function weekIntersectsMonth(
  periodStart: string,
  periodEnd: string,
  year: number,
  month: number,
): boolean {
  const start = monthStartKey(year, month)
  const end = monthEndExclusiveKey(year, month)
  return periodStart < end && periodEnd > start
}

/**
 * Keep `dateKey` on an ISO week that intersects `year`/`month`.
 * Prefers today's week when viewing the current month.
 */
export function clampWeekAnchorToMonth(
  dateKey: string,
  year: number,
  month: number,
  timeZone: string,
): string {
  const bounds = getIsoWeekBounds(dateKey, timeZone)
  if (weekIntersectsMonth(bounds.period_start, bounds.period_end, year, month)) {
    return bounds.period_start
  }
  const today = todayKey(timeZone)
  const todayBounds = getIsoWeekBounds(today, timeZone)
  if (weekIntersectsMonth(todayBounds.period_start, todayBounds.period_end, year, month)) {
    return todayBounds.period_start
  }
  return getIsoWeekBounds(monthStartKey(year, month), timeZone).period_start
}

/** Inclusive local calendar day → half-open `[from, to)` bounds in the user timezone. */
export function getDayBounds(
  date: string,
  timeZone: string,
): { recorded_from: string; recorded_to: string } {
  const [year, month, day] = date.split('-').map(Number)
  const fromUtc = zonedLocalToUtc(year, month, day, 0, 0, 0, timeZone)
  const nextUtcDate = new Date(Date.UTC(year, month - 1, day + 1))
  const toUtc = zonedLocalToUtc(
    nextUtcDate.getUTCFullYear(),
    nextUtcDate.getUTCMonth() + 1,
    nextUtcDate.getUTCDate(),
    0,
    0,
    0,
    timeZone,
  )
  return {
    recorded_from: instantToIsoInTimezone(fromUtc, timeZone),
    recorded_to: instantToIsoInTimezone(toUtc, timeZone),
  }
}

/** `month` is 0-indexed. Returns `YYYY-MM`. */
export function formatYearMonthParam(year: number, month: number): string {
  return `${year}-${String(month + 1).padStart(2, '0')}`
}

export function parseYearMonthParam(
  value: string | null | undefined,
): { year: number; month: number } | null {
  if (!value || !/^\d{4}-\d{2}$/.test(value)) {
    return null
  }
  const [year, monthNumber] = value.split('-').map(Number)
  if (monthNumber < 1 || monthNumber > 12) {
    return null
  }
  return { year, month: monthNumber - 1 }
}

export function entriesListPath(options: {
  year: number
  month: number
  day?: string
  entryId?: string
}): string {
  const params = new URLSearchParams()
  params.set('month', formatYearMonthParam(options.year, options.month))
  if (options.day) {
    params.set('day', options.day)
  }
  if (options.entryId) {
    params.set('entry', options.entryId)
  }
  return `/?${params.toString()}`
}

export function entriesListPathForInstant(
  iso: string,
  timeZone: string,
  entryId?: string,
): string {
  const day = dayKey(iso, timeZone)
  const [year, monthNumber] = day.split('-').map(Number)
  return entriesListPath({
    year,
    month: monthNumber - 1,
    day,
    entryId,
  })
}

export function formatDayHeading(iso: string, timeZone: string, locale = 'en-GB'): string {
  const instant = new Date(iso)
  return new Intl.DateTimeFormat(locale, {
    timeZone,
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(instant)
}

export function formatWeekday(iso: string, timeZone: string, locale = 'en-GB'): string {
  const instant = new Date(iso)
  return new Intl.DateTimeFormat(locale, {
    timeZone,
    weekday: 'long',
  }).format(instant)
}

export function formatTime(iso: string, timeZone: string, locale = 'en-GB'): string {
  const instant = new Date(iso)
  return new Intl.DateTimeFormat(locale, {
    timeZone,
    hour: '2-digit',
    minute: '2-digit',
  }).format(instant)
}

export function dayKey(iso: string, timeZone: string): string {
  const instant = new Date(iso)
  const parts = formatLocalParts(instant, timeZone)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${parts.year}-${pad(parts.month)}-${pad(parts.day)}`
}

/** Local `YYYY-MM` in the given timezone. */
export function monthKey(iso: string, timeZone: string): string {
  return dayKey(iso, timeZone).slice(0, 7)
}

export function getCurrentYearMonth(timeZone: string): { year: number; month: number } {
  const parts = formatLocalParts(new Date(), timeZone)
  return { year: parts.year, month: parts.month - 1 }
}

/** `month` is 0-indexed. `delta` is in whole months. */
export function shiftYearMonth(
  year: number,
  month: number,
  delta: number,
): { year: number; month: number } {
  const date = new Date(Date.UTC(year, month + delta, 1))
  return { year: date.getUTCFullYear(), month: date.getUTCMonth() }
}

export function yearMonthFromInstant(
  iso: string,
  timeZone: string,
): { year: number; month: number } {
  const [year, monthNumber] = monthKey(iso, timeZone).split('-').map(Number)
  return { year, month: monthNumber - 1 }
}

export function formatMonthHeading(year: number, month: number, locale = 'en-GB'): string {
  const date = new Date(Date.UTC(year, month, 1))
  return new Intl.DateTimeFormat(locale, {
    month: 'long',
    year: 'numeric',
  }).format(date)
}

/** Short month + year without locale suffixes like «г.», for tight headers. */
export function formatMonthHeadingCompact(
  year: number,
  month: number,
  monthShortLabels: readonly string[],
): string {
  return `${monthShortLabels[month] ?? String(month + 1)} ${year}`
}

export type CalendarCell = {
  key: string
  day: number
  inMonth: boolean
  date: string
}

/** Monday-first 6-week grid (42 cells) so month length does not change layout. */
export function buildMonthCalendarCells(year: number, month: number): CalendarCell[] {
  const firstWeekday = new Date(Date.UTC(year, month, 1)).getUTCDay()
  // Convert Sunday=0 … Saturday=6 → Monday=0 … Sunday=6
  const mondayOffset = (firstWeekday + 6) % 7
  const daysInMonth = new Date(Date.UTC(year, month + 1, 0)).getUTCDate()
  const daysInPrevMonth = new Date(Date.UTC(year, month, 0)).getUTCDate()

  const pad = (value: number) => String(value).padStart(2, '0')
  const prevYear = month === 0 ? year - 1 : year
  const prevMonth = month === 0 ? 11 : month - 1
  const nextYear = month === 11 ? year + 1 : year
  const nextMonth = month === 11 ? 0 : month + 1
  const cells: CalendarCell[] = []

  for (let i = 0; i < mondayOffset; i += 1) {
    const day = daysInPrevMonth - mondayOffset + i + 1
    cells.push({
      key: `prev-${day}`,
      day,
      inMonth: false,
      date: `${prevYear}-${pad(prevMonth + 1)}-${pad(day)}`,
    })
  }

  for (let day = 1; day <= daysInMonth; day += 1) {
    cells.push({
      key: `day-${day}`,
      day,
      inMonth: true,
      date: `${year}-${pad(month + 1)}-${pad(day)}`,
    })
  }

  let nextDay = 1
  while (cells.length < 42) {
    cells.push({
      key: `next-${nextDay}`,
      day: nextDay,
      inMonth: false,
      date: `${nextYear}-${pad(nextMonth + 1)}-${pad(nextDay)}`,
    })
    nextDay += 1
  }

  return cells
}

export function todayKey(timeZone: string): string {
  return dayKey(new Date().toISOString(), timeZone)
}

/** Local hour 0–23 in `timeZone` for an instant (defaults to now). */
export function localHour(timeZone: string, instant: Date = new Date()): number {
  const hour = formatLocalParts(instant, timeZone).hour
  return hour === 24 ? 0 : hour
}

/** Hour 0–23 from a `datetime-local` value (`YYYY-MM-DDTHH:MM`). */
export function hourFromDatetimeLocal(value: string): number {
  const match = value.match(/T(\d{2})/)
  if (!match) {
    return 12
  }
  const hour = Number(match[1])
  if (!Number.isFinite(hour)) {
    return 12
  }
  if (hour === 24) {
    return 0
  }
  return Math.min(23, Math.max(0, hour))
}

/** `datetime-local` value for a calendar date at a fixed local time (default 20:00). */
export function datetimeLocalForDate(date: string, hour = 20, minute = 0): string {
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date}T${pad(hour)}:${pad(minute)}`
}

export function isFutureDate(date: string, timeZone: string): boolean {
  return date > todayKey(timeZone)
}

export function formatCalendarDate(date: string, locale = 'en-GB'): string {
  const [year, month, day] = date.split('-').map(Number)
  const instant = new Date(Date.UTC(year, month - 1, day))
  return new Intl.DateTimeFormat(locale, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(instant)
}
