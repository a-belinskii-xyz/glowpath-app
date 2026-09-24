/** Fake cold-start progress: fast to 70%, then a slow crawl toward 95%. */
const FAST_WINDOW_SEC = 7
const FAST_TARGET = 70
const SLOW_CAP = 95
const SLOW_TAU_SEC = 18

export const BOOT_PHASE_BOUNDS_SEC = [3, 8, 15, 35] as const
export const BOOT_RETRY_AFTER_SEC = 60
export const BOOT_CARD_MS = 4500
export const BOOT_FADE_MS = 360

export function bootPhaseIndex(elapsedSec: number): number {
  const t = Math.max(0, elapsedSec)
  for (let i = 0; i < BOOT_PHASE_BOUNDS_SEC.length; i += 1) {
    if (t < BOOT_PHASE_BOUNDS_SEC[i]) {
      return i
    }
  }
  return BOOT_PHASE_BOUNDS_SEC.length
}

export function bootProgressPercent(elapsedSec: number, settled: boolean): number {
  if (settled) {
    return 100
  }
  const t = Math.max(0, elapsedSec)
  if (t <= FAST_WINDOW_SEC) {
    const x = t / FAST_WINDOW_SEC
    const eased = 1 - (1 - x) ** 3
    return eased * FAST_TARGET
  }
  const tail = 1 - Math.exp(-(t - FAST_WINDOW_SEC) / SLOW_TAU_SEC)
  return FAST_TARGET + (SLOW_CAP - FAST_TARGET) * tail
}
