/**
 * Visual system entry — three independent axes:
 *   1. Chrome System  — mood-agnostic UI kit tokens
 *   2. Semantic Mood  — Mood Theme Builder + Gradient Engine
 *   3. Motion System  — shared timing / easing
 */

export { chrome, chromeCssVars, type ChromeTokens } from './chrome'
export { motion, motionCssVars, motionCss, type MotionTokens } from './motion'
export {
  buildMoodTheme,
  impactToGlowLevel,
  moodGlowBoxShadow,
  moodGlowFilter,
  moodGlowForImpact,
  moodSubtleFill,
  GLOW_LEVELS,
  type BuildMoodThemeOptions,
  type GlowLevel,
  type MoodIntensity,
  type MoodSurfaceStep,
  type MoodTheme,
} from './moodTheme'
export {
  gradientRecipes,
  type GradientRecipe,
  type GradientRecipeName,
} from './gradientRecipes'
export {
  buildGradientWash,
  buildGradientWashFromScores,
  type GradientWashStyle,
} from './gradientEngine'
export {
  ambientGlowToCssVars,
  ambientPaletteKey,
  buildAmbientGlowColors,
  buildAmbientGlowCssVars,
  DEFAULT_AMBIENT_GLOW,
  type AmbientGlowColors,
  type AmbientGlowCssVars,
} from './ambientGlow'
export {
  earlyBiasWeights,
  equalWeights,
  hexToOklab,
  lateBiasWeights,
  mixOklab,
  oklabToHex,
  washOklab,
  withHexAlpha,
  type Oklab,
} from './oklab'
