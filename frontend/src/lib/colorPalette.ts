/**
 * Curated swatches for mood / goal color pickers.
 * Tuned to GlowPath chrome + default mood scale (slate → blue → green → amber).
 * Room later for “popular” / pattern suggestions without changing the picker API.
 */
export const COLOR_PALETTE_SWATCHES = [
  '#64748b',
  '#94a3b8',
  '#60a5fa',
  '#2563eb',
  '#0ea5e9',
  '#14b8a6',
  '#34d399',
  '#84cc16',
  '#eab308',
  '#f59e0b',
  '#f97316',
  '#ef4444',
  '#f472b6',
  '#a78bfa',
] as const

export type ColorPaletteSwatch = (typeof COLOR_PALETTE_SWATCHES)[number]
