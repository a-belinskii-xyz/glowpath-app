import { formatClockMinutes } from './timeFormat'
import type { SleepLog } from '../types/body'

const DAY_MINUTES = 24 * 60
const NOON = 12 * 60

/** "23:40:00" → minutes since midnight. */
export function clockMinutes(value: string): number {
  const [hours, minutes] = value.split(':').map(Number)
  return hours * 60 + minutes
}

/** Minutes → "07:05" or "7:05 AM"; wraps around midnight. */
export function formatClock(minutes: number, options: { short?: boolean } = {}): string {
  return formatClockMinutes(minutes, options)
}

export type Night = {
  day: string
  /** Minutes from noon of the evening before, so a night is one increasing span. */
  bed: number
  wake: number
  up: number | null
  /** Minutes asleep, taken as wake − bed: falling asleep is not asked, it would be a guess. */
  sleep: number
  /** Minutes lying in bed after waking. */
  lying: number
}

export function toNight(log: SleepLog): Night {
  const bed = (clockMinutes(log.bed_time) - NOON + DAY_MINUTES) % DAY_MINUTES
  let wake = (clockMinutes(log.wake_time) - NOON + DAY_MINUTES) % DAY_MINUTES
  if (wake < bed) wake += DAY_MINUTES
  let up: number | null = null
  if (log.up_time) {
    up = (clockMinutes(log.up_time) - NOON + DAY_MINUTES) % DAY_MINUTES
    while (up < wake) up += DAY_MINUTES
    // "Got up" a whole day later is a typo, not a lie-in.
    if (up - wake > 6 * 60) up = null
  }
  return { day: log.day, bed, wake, up, sleep: wake - bed, lying: up === null ? 0 : up - wake }
}

/** Anchored minutes back to a clock time. */
export function nightClock(minutes: number, options: { short?: boolean } = {}): string {
  return formatClock(minutes + NOON, options)
}

function mean(values: number[]): number | null {
  return values.length === 0 ? null : values.reduce((sum, value) => sum + value, 0) / values.length
}

export type NightAverage = {
  count: number
  bed: number
  wake: number
  up: number | null
  sleep: number
  lying: number | null
}

export function averageNights(nights: Night[]): NightAverage | null {
  if (nights.length === 0) return null
  const ups = nights.filter((night) => night.up !== null)
  return {
    count: nights.length,
    bed: mean(nights.map((night) => night.bed)) ?? 0,
    wake: mean(nights.map((night) => night.wake)) ?? 0,
    up: mean(ups.map((night) => night.up ?? 0)),
    sleep: mean(nights.map((night) => night.sleep)) ?? 0,
    lying: ups.length === 0 ? null : mean(ups.map((night) => night.lying)),
  }
}

type Translate = (key: string, params?: Record<string, string | number>) => string

export function formatDuration(t: Translate, minutes: number): string {
  const total = Math.round(minutes)
  const hours = Math.floor(total / 60)
  const rest = total % 60
  return hours > 0 ? t('body.sleepHours', { h: hours, m: rest }) : t('body.sleepMinutes', { m: rest })
}

/**
 * Typing in a clock field: digits only (phone keypads have no colon), the colon is added for you.
 * "2340" → "23:40", "730" → "7:30", "7" → "7".
 */
export function typeClock(raw: string): string {
  const digits = raw.replace(/\D/g, '').slice(0, 4)
  if (digits.length < 3) return digits
  // "730" means 7:30, "123" means 12:3 on the way to 12:30.
  const short = digits.length === 3 && (Number(digits[0]) > 2 || Number(digits.slice(0, 2)) > 23)
  const hours = short ? digits.slice(0, 1) : digits.slice(0, 2)
  return `${hours}:${digits.slice(hours.length, hours.length + 2)}`
}

/** A typed clock as "HH:MM", or null when it is not a time yet. "7" → "07:00", "7:30" → "07:30". */
export function normalizeClock(value: string): string | null {
  const match = /^(\d{1,2})(?::(\d{2}))?$/.exec(value.trim())
  if (!match) return null
  const hours = Number(match[1])
  const minutes = Number(match[2] ?? '0')
  if (hours > 23 || minutes > 59) return null
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
}

/** The person's own sleep range in minutes (GP-61). */
export type SleepNorm = { min: number; max: number }
export type SleepBand = 'short' | 'normal' | 'long'

export function sleepNormOf(settings: { sleep_norm_min: number | null; sleep_norm_max: number | null }): SleepNorm | null {
  return settings.sleep_norm_min !== null && settings.sleep_norm_max !== null
    ? { min: settings.sleep_norm_min, max: settings.sleep_norm_max }
    : null
}

/** Where a night falls against the norm; null when no norm is set. */
export function sleepBand(minutes: number, norm: SleepNorm | null): SleepBand | null {
  if (!norm) return null
  if (minutes < norm.min) return 'short'
  if (minutes > norm.max) return 'long'
  return 'normal'
}
