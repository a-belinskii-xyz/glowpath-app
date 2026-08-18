/**
 * Mood Theme Builder — Semantic Mood System.
 *
 * User sets one hex; this derives a full palette of surfaces, glows, accents,
 * and CSS vars so components never re-implement wash / glow / audio tint.
 */

import {
  clamp01,
  hexToOklab,
  oklabToHex,
  washOklab,
  withHexAlpha,
  type Oklab,
} from './oklab'

/** Emotional intensity — scales wash softness, chroma, and glow strength. */
export type MoodIntensity = 'calm' | 'moderate' | 'expressive'

export type GlowLevel = 'xs' | 'sm' | 'md' | 'lg'

/** Surface steps — Tailwind-like scale generated from one mood color. */
export type MoodSurfaceStep = 50 | 100 | 200 | 300

type WashStep = { washStrength: number; chromaScale: number }

/**
 * Base wash steps before intensity adjustment.
 * Tuned to match historical day / audio / week-strip looks.
 */
const SURFACE_STEPS: Record<MoodSurfaceStep, WashStep> = {
  50: { washStrength: 0.9, chromaScale: 0.42 },
  100: { washStrength: 0.82, chromaScale: 0.48 },
  200: { washStrength: 0.78, chromaScale: 0.55 },
  300: { washStrength: 0.55, chromaScale: 0.72 },
}

const ACCENT_STEP: WashStep = { washStrength: 0.22, chromaScale: 0.92 }

const INTENSITY: Record<
  MoodIntensity,
  { washDelta: number; chromaScale: number; glowAlphaScale: number }
> = {
  calm: { washDelta: 0.08, chromaScale: 0.85, glowAlphaScale: 0.85 },
  moderate: { washDelta: 0, chromaScale: 1, glowAlphaScale: 1 },
  expressive: { washDelta: -0.1, chromaScale: 1.15, glowAlphaScale: 1.15 },
}

/** Glow blur + base alpha (0–255). `sm` preserves the historical `…88` look. */
export const GLOW_LEVELS: Record<GlowLevel, { blur: string; blurPx: number; alpha: number }> = {
  xs: { blur: '0.15rem', blurPx: 2.4, alpha: 0x55 },
  sm: { blur: '0.35rem', blurPx: 5.6, alpha: 0x88 },
  md: { blur: '0.55rem', blurPx: 8.8, alpha: 0xaa },
  lg: { blur: '0.85rem', blurPx: 13.6, alpha: 0xcc },
}

/** Share-of-whole thresholds → glow level (charts, progress). */
const IMPACT_GLOW_THRESHOLDS: { min: number; level: GlowLevel }[] = [
  { min: 0.55, level: 'lg' },
  { min: 0.32, level: 'md' },
  { min: 0.14, level: 'sm' },
  { min: 0.02, level: 'xs' },
]

const FALLBACK_HEX = '#60a5fa'

export type MoodTheme = {
  raw: string
  intensity: MoodIntensity

  /** Alias of surface100 — default soft wash. */
  wash: string
  surface50: string
  surface100: string
  surface200: string
  surface300: string

  /** Near-raw accent for buttons / progress / chart emphasis. */
  accent: string
  /** Soft outline / focus tint (~35% alpha). */
  outline: string
  /** Selected fill (~10% alpha), e.g. score picker. */
  subtle: string
  /** Soft colored elevation shadow. */
  shadow: string

  text: string
  muted: string
  /** Solid chart / bar fill — raw mood color. */
  chart: string

  glow: Record<GlowLevel, string>
  glowBox: Record<GlowLevel, string>

  /**
   * CSS custom properties for soft chrome (audio player, future mood surfaces).
   * Ready to spread onto a style object.
   */
  cssVars: {
    '--mood-raw': string
    '--mood-surface': string
    '--mood-surface-edge': string
    '--mood-accent': string
    '--mood-ink': string
    '--mood-muted': string
    '--mood-track': string
  }
}

export type BuildMoodThemeOptions = {
  intensity?: MoodIntensity
  /** Fallback when hex is invalid. */
  fallback?: string
}

function applyIntensity(step: WashStep, intensity: MoodIntensity): WashStep {
  const adj = INTENSITY[intensity]
  return {
    washStrength: Math.min(1, Math.max(0, step.washStrength + adj.washDelta)),
    chromaScale: Math.max(0, step.chromaScale * adj.chromaScale),
  }
}

function washHex(lab: Oklab, step: WashStep, intensity: MoodIntensity): string {
  const tuned = applyIntensity(step, intensity)
  return oklabToHex(washOklab(lab, tuned.washStrength, tuned.chromaScale))
}

function scaledGlowAlpha(baseAlpha: number, intensity: MoodIntensity): number {
  const scale = INTENSITY[intensity].glowAlphaScale
  return Math.min(255, Math.round(baseAlpha * scale))
}

function buildGlowFilters(raw: string, intensity: MoodIntensity): Record<GlowLevel, string> {
  const result = {} as Record<GlowLevel, string>
  for (const level of Object.keys(GLOW_LEVELS) as GlowLevel[]) {
    const { blur, alpha } = GLOW_LEVELS[level]
    result[level] = `drop-shadow(0 0 ${blur} ${withHexAlpha(raw, scaledGlowAlpha(alpha, intensity))})`
  }
  return result
}

function buildGlowBoxShadows(raw: string, intensity: MoodIntensity): Record<GlowLevel, string> {
  const result = {} as Record<GlowLevel, string>
  for (const level of Object.keys(GLOW_LEVELS) as GlowLevel[]) {
    const { blur, alpha } = GLOW_LEVELS[level]
    const soft = scaledGlowAlpha(Math.round(alpha * 0.55), intensity)
    const bloom = scaledGlowAlpha(alpha, intensity)
    result[level] =
      `0 1px 2px ${withHexAlpha(raw, soft)}, 0 0 ${blur} ${withHexAlpha(raw, bloom)}`
  }
  return result
}

function softShadow(accent: string): string {
  return `0 1px 2px ${withHexAlpha(accent, 0x59)}`
}

/**
 * Map a 0–1 impact share (e.g. emotion count / total, goal progress) to a glow level.
 * Returns null when impact is negligible — callers should skip glow.
 */
export function impactToGlowLevel(impact: number): GlowLevel | null {
  const t = clamp01(impact)
  if (t <= 0) {
    return null
  }
  for (const row of IMPACT_GLOW_THRESHOLDS) {
    if (t >= row.min) {
      return row.level
    }
  }
  return null
}

const themeCache = new Map<string, MoodTheme>()

function themeCacheKey(hex: string, intensity: MoodIntensity, fallback: string): string {
  return `${hex.trim()}|${intensity}|${fallback}`
}

/**
 * Build a full mood theme from a single user color.
 * All UI that “breathes” mood should consume this instead of ad-hoc wash math.
 */
export function buildMoodTheme(
  hex: string,
  options: BuildMoodThemeOptions = {},
): MoodTheme {
  const intensity = options.intensity ?? 'moderate'
  const fallback = options.fallback ?? FALLBACK_HEX
  const cacheKey = themeCacheKey(hex, intensity, fallback)
  const cached = themeCache.get(cacheKey)
  if (cached) {
    return cached
  }
  const raw = hexToOklab(hex) ? hex.trim() : fallback
  const lab = hexToOklab(raw) ?? hexToOklab(fallback)!

  const surface50 = washHex(lab, SURFACE_STEPS[50], intensity)
  const surface100 = washHex(lab, SURFACE_STEPS[100], intensity)
  const surface200 = washHex(lab, SURFACE_STEPS[200], intensity)
  const surface300 = washHex(lab, SURFACE_STEPS[300], intensity)
  const accent = washHex(lab, ACCENT_STEP, intensity)

  const text = oklabToHex({
    L: Math.min(0.42, lab.L * 0.55),
    a: lab.a * 0.55,
    b: lab.b * 0.55,
  })
  const muted = oklabToHex({
    L: Math.min(0.58, lab.L * 0.7 + 0.12),
    a: lab.a * 0.28,
    b: lab.b * 0.28,
  })
  const track = washHex(lab, { washStrength: 0.86, chromaScale: 0.28 }, intensity)

  const glow = buildGlowFilters(raw, intensity)
  const glowBox = buildGlowBoxShadows(raw, intensity)

  const theme: MoodTheme = {
    raw,
    intensity,
    wash: surface100,
    surface50,
    surface100,
    surface200,
    surface300,
    accent,
    outline: withHexAlpha(raw, 0x59),
    subtle: withHexAlpha(raw, 0x1a),
    shadow: softShadow(accent),
    text,
    muted,
    chart: raw,
    glow,
    glowBox,
    cssVars: {
      '--mood-raw': raw,
      '--mood-surface': surface50,
      '--mood-surface-edge': surface200,
      '--mood-accent': accent,
      '--mood-ink': text,
      '--mood-muted': muted,
      '--mood-track': track,
    },
  }
  themeCache.set(cacheKey, theme)
  return theme
}

/** Convenience: CSS `filter` for a mood/goal icon glow. Default = historical sm. */
export function moodGlowFilter(
  hex: string,
  level: GlowLevel = 'sm',
  intensity: MoodIntensity = 'moderate',
): string {
  return buildMoodTheme(hex, { intensity }).glow[level]
}

/**
 * Colored elevation + bloom for rectangular surfaces (buttons, bars, cards).
 * Prefer this over `filter: drop-shadow` when the element has a solid fill.
 */
export function moodGlowBoxShadow(
  hex: string,
  level: GlowLevel = 'sm',
  intensity: MoodIntensity = 'moderate',
): string {
  return buildMoodTheme(hex, { intensity }).glowBox[level]
}

/**
 * Glow for chart / progress fills driven by relative impact (0–1).
 * Returns undefined when impact is too small to glow.
 */
export function moodGlowForImpact(
  hex: string,
  impact: number,
  intensity: MoodIntensity = 'moderate',
): { filter: string; boxShadow: string; level: GlowLevel } | undefined {
  const level = impactToGlowLevel(impact)
  if (!level) {
    return undefined
  }
  const theme = buildMoodTheme(hex, { intensity })
  return {
    level,
    filter: theme.glow[level],
    boxShadow: theme.glowBox[level],
  }
}

/** Selected-option tint (`${color}1a` historically). */
export function moodSubtleFill(hex: string, intensity: MoodIntensity = 'moderate'): string {
  return buildMoodTheme(hex, { intensity }).subtle
}
