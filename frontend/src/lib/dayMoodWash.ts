/**
 * @deprecated Import from `../design` instead.
 * Thin compatibility layer over the Gradient Engine + OKLab primitives.
 */

import {
  buildGradientWash,
  buildGradientWashFromScores,
  earlyBiasWeights,
  gradientRecipes,
  hexToOklab,
  lateBiasWeights,
  oklabToHex,
  washOklab as washOklabCore,
  type GradientWashStyle,
  type Oklab,
} from '../design'

export type { Oklab }

/** @deprecated Use `GradientRecipe` from `design`. */
export type DayMoodWashParams = {
  washStrength: number
  chromaScale: number
  orderPower: number
  angleDeg: number
  midStopMinColors: number
}

/** @deprecated Use `gradientRecipes.day`. */
export const DEFAULT_DAY_MOOD_WASH_PARAMS: DayMoodWashParams = { ...gradientRecipes.day }

export type DayMoodWashStyle = GradientWashStyle

export { hexToOklab, oklabToHex, earlyBiasWeights, lateBiasWeights }

export function washOklab(
  color: Oklab,
  params: DayMoodWashParams = DEFAULT_DAY_MOOD_WASH_PARAMS,
): Oklab {
  return washOklabCore(color, params.washStrength, params.chromaScale)
}

export function dayMoodWashStyle(
  hexColorsChronological: string[],
  params: DayMoodWashParams = DEFAULT_DAY_MOOD_WASH_PARAMS,
): DayMoodWashStyle | null {
  return buildGradientWash(hexColorsChronological, params)
}

export function dayMoodWashFromScores<T extends { score: number; recorded_at: string }>(
  entries: T[],
  getColor: (score: number, entry: T) => string,
  params: DayMoodWashParams = DEFAULT_DAY_MOOD_WASH_PARAMS,
): DayMoodWashStyle | null {
  return buildGradientWashFromScores(entries, getColor, params)
}
