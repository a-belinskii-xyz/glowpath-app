import type { SleepLog } from '../types/body'

const DAY_MINUTES = 24 * 60
const NOON = 12 * 60

/** "23:40:00" → minutes since midnight. */
export function clockMinutes(value: string): number {
  const [hours, minutes] = value.split(':').map(Number)
  return hours * 60 + minutes
}

/** Minutes → "07:05"; wraps around midnight. */
export function formatClock(minutes: number): string {
  const value = ((Math.round(minutes) % DAY_MINUTES) + DAY_MINUTES) % DAY_MINUTES
  return `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`
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
export function nightClock(minutes: number): string {
  return formatClock(minutes + NOON)
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
