/**
 * Gradient Engine — builds soft multi-stop washes from mood/goal colors.
 * Recipes live in gradientRecipes.ts; OKLab math in oklab.ts.
 */

import {
  earlyBiasWeights,
  equalWeights,
  hexToOklab,
  lateBiasWeights,
  mixOklab,
  oklabToHex,
  washOklab,
  type Oklab,
} from './oklab'
import {
  gradientRecipes,
  type GradientRecipe,
  type GradientRecipeName,
} from './gradientRecipes'

export type GradientWashStyle = {
  backgroundImage: string
  backgroundColor: string
}

function nearlySameHex(a: string, b: string): boolean {
  return a.toLowerCase() === b.toLowerCase()
}

function resolveRecipe(
  recipe: GradientRecipe | GradientRecipeName = 'day',
): GradientRecipe {
  return typeof recipe === 'string' ? gradientRecipes[recipe] : recipe
}

/**
 * Build a soft CSS wash from hex colors in chronological order (oldest → newest).
 * Returns null when there are no valid colors.
 */
export function buildGradientWash(
  hexColorsChronological: string[],
  recipe: GradientRecipe | GradientRecipeName = 'day',
): GradientWashStyle | null {
  const params = resolveRecipe(recipe)
  const washed: Oklab[] = []
  for (const hex of hexColorsChronological) {
    const lab = hexToOklab(hex)
    if (lab) {
      washed.push(washOklab(lab, params.washStrength, params.chromaScale))
    }
  }
  if (washed.length === 0) {
    return null
  }

  const n = washed.length
  const average = mixOklab(washed, equalWeights(n))
  const averageHex = oklabToHex(average)

  if (n === 1) {
    return {
      backgroundColor: averageHex,
      backgroundImage: 'none',
    }
  }

  const startHex = oklabToHex(mixOklab(washed, earlyBiasWeights(n, params.orderPower)))
  const endHex = oklabToHex(mixOklab(washed, lateBiasWeights(n, params.orderPower)))

  if (nearlySameHex(startHex, endHex)) {
    return {
      backgroundColor: averageHex,
      backgroundImage: 'none',
    }
  }

  const angle = Number.isFinite(params.angleDeg) ? params.angleDeg : gradientRecipes.day.angleDeg
  const stops =
    n >= params.midStopMinColors &&
    !nearlySameHex(averageHex, startHex) &&
    !nearlySameHex(averageHex, endHex)
      ? `${startHex} 0%, ${averageHex} 48%, ${endHex} 100%`
      : `${startHex} 0%, ${endHex} 100%`

  return {
    backgroundColor: averageHex,
    backgroundImage: `linear-gradient(${angle}deg, ${stops})`,
  }
}

/**
 * Resolve wash style from mood scores + a color lookup, sorting by recorded time.
 */
export function buildGradientWashFromScores<T extends { score: number; recorded_at: string }>(
  entries: T[],
  getColor: (score: number, entry: T) => string,
  recipe: GradientRecipe | GradientRecipeName = 'day',
): GradientWashStyle | null {
  const chronological = [...entries].sort(
    (a, b) => new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime(),
  )
  return buildGradientWash(
    chronological.map((entry) => getColor(entry.score, entry)),
    recipe,
  )
}
