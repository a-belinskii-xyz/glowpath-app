/**
 * Gradient recipes — named presets for the shared Gradient Engine.
 */

import type { ColorScheme } from './colorScheme'

export type GradientRecipe = {
  /** How strongly to pull lightness toward `targetL` (0–1). */
  washStrength: number
  /** Scales OKLab chroma after the wash. */
  chromaScale: number
  /** Exponent for temporal weights on gradient ends. */
  orderPower: number
  /** CSS `linear-gradient` angle in degrees. */
  angleDeg: number
  /** Insert equal-weight midpoint when color count ≥ this. */
  midStopMinColors: number
  /** Lightness to wash toward. 1 = white; ~0.22 = dark chrome. */
  targetL?: number
}

export const gradientRecipes = {
  /** Soft day-section wash on the entries feed (light chrome). */
  day: {
    washStrength: 0.82,
    chromaScale: 0.48,
    orderPower: 1.35,
    angleDeg: 148,
    midStopMinColors: 3,
    targetL: 1,
  },
  /** Same language on dark chrome: tinted dusk, not pastel paper. */
  dayDark: {
    washStrength: 0.82,
    chromaScale: 0.4,
    orderPower: 1.35,
    angleDeg: 148,
    midStopMinColors: 3,
    targetL: 0.22,
  },
} as const satisfies Record<string, GradientRecipe>

export type GradientRecipeName = keyof typeof gradientRecipes

export function dayWashRecipe(scheme: ColorScheme): GradientRecipeName {
  return scheme === 'dark' ? 'dayDark' : 'day'
}
