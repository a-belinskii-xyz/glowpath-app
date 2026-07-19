/**
 * Gradient recipes — named presets for the shared Gradient Engine.
 * Day / week / strip use the same math with different knobs.
 */

export type GradientRecipe = {
  /** How strongly to pull lightness toward white (0–1). */
  washStrength: number
  /** Scales OKLab chroma after the wash. */
  chromaScale: number
  /** Exponent for temporal weights on gradient ends. */
  orderPower: number
  /** CSS `linear-gradient` angle in degrees. */
  angleDeg: number
  /** Insert equal-weight midpoint when color count ≥ this. */
  midStopMinColors: number
}

export const gradientRecipes = {
  /** Soft day-section wash on the entries feed. */
  day: {
    washStrength: 0.82,
    chromaScale: 0.48,
    orderPower: 1.35,
    angleDeg: 148,
    midStopMinColors: 3,
  },
  /** Calendar week band (goals mode). */
  week: {
    washStrength: 0.78,
    chromaScale: 0.58,
    orderPower: 1.35,
    angleDeg: 90,
    midStopMinColors: 2,
  },
  /** Richer bottom strip under a highlighted week. */
  weekStrip: {
    washStrength: 0.55,
    chromaScale: 0.72,
    orderPower: 1.35,
    angleDeg: 90,
    midStopMinColors: 2,
  },
} as const satisfies Record<string, GradientRecipe>

export type GradientRecipeName = keyof typeof gradientRecipes
