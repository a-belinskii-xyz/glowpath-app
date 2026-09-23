/**
 * Ambient Glow — soft page-level radial wash for glowpath:\ chrome.
 * Consumes mood/goal/tag hexes through OKLab wash so the shell “breathes”
 * the same palette language as day washes and icon glows.
 */

import { chrome } from './chrome'
import { buildMoodTheme, type MoodIntensity } from './moodTheme'
import { hexToOklab, oklabToHex, withHexAlpha, type Oklab } from './oklab'

export type AmbientGlowColors = {
  /** Top-left bloom */
  c1: string
  /** Top-right bloom */
  c2: string
  /** Bottom-right bloom */
  c3: string
  /** Bottom-left bloom */
  c4: string
  /** Brand wordmark ink stops (contrast-safe, softly tinted). */
  brand1: string
  brand2: string
  brand3: string
}

export type AmbientGlowCssVars = {
  '--ambient-c1': string
  '--ambient-c2': string
  '--ambient-c3': string
  '--ambient-c4': string
  '--brand-ink-1': string
  '--brand-ink-2': string
  '--brand-ink-3': string
}

/**
 * Brand ink must stay readable on header (solid white) and sidebar glass
 * over ambient blooms. Target WCAG AA (4.5:1) with a little margin — high
 * enough to read, low enough that mood hue still reads as color (not black).
 */
const BRAND_MIN_CONTRAST = 5
const BRAND_L_MAX = 0.5
const BRAND_L_MIN = 0.28
/** Surfaces the wordmark sits on (worst-case light backgrounds). */
const BRAND_BACKGROUNDS = [chrome.surface.default, chrome.bg.app] as const

/** Soft chrome default — readable brand + gentle blue/rose shell blooms. */
export const DEFAULT_AMBIENT_GLOW: AmbientGlowColors = {
  c1: 'rgb(147 197 253 / 72%)',
  c2: 'rgb(252 165 165 / 52%)',
  c3: 'rgb(165 180 252 / 48%)',
  c4: 'rgb(103 232 249 / 42%)',
  brand1: '#334155',
  brand2: '#1d4ed8',
  brand3: '#9f1239',
}

/** Bloom alpha — visible wash over --chrome-bg-app without overpowering content. */
const BLOOM_ALPHA: Record<MoodIntensity, [number, number, number, number]> = {
  calm: [0x8c, 0x6e, 0x5c, 0x4e],
  moderate: [0xaa, 0x88, 0x72, 0x60],
  expressive: [0xc0, 0x9c, 0x84, 0x70],
}

function normalizeHexes(hexColors: string[]): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const raw of hexColors) {
    const hex = raw?.trim()
    if (!hex || seen.has(hex.toLowerCase())) {
      continue
    }
    seen.add(hex.toLowerCase())
    out.push(hex)
  }
  return out
}

function pick(colors: string[], index: number, fallback: string): string {
  if (colors.length === 0) {
    return fallback
  }
  return colors[index % colors.length]
}

function srgbChannelToLinear(c: number): number {
  const v = c / 255
  return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
}

function relativeLuminance(hex: string): number {
  const match = /^#([0-9A-Fa-f]{6})$/.exec(hex.trim())
  if (!match) {
    return 0
  }
  const n = Number.parseInt(match[1], 16)
  const r = srgbChannelToLinear((n >> 16) & 0xff)
  const g = srgbChannelToLinear((n >> 8) & 0xff)
  const b = srgbChannelToLinear(n & 0xff)
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function contrastRatio(foreground: string, background: string): number {
  const a = relativeLuminance(foreground)
  const b = relativeLuminance(background)
  const lighter = Math.max(a, b)
  const darker = Math.min(a, b)
  return (lighter + 0.05) / (darker + 0.05)
}

function meetsBrandContrast(ink: string, extraBackgrounds: string[] = []): boolean {
  const backgrounds = [...BRAND_BACKGROUNDS, ...extraBackgrounds]
  return backgrounds.every((bg) => contrastRatio(ink, bg) >= BRAND_MIN_CONTRAST)
}

/**
 * Approximate sidebar glass over a mood wash — wordmark can sit on this,
 * so ink must clear it too (not only solid white).
 */
function glassOverWash(moodHex: string): string {
  const wash = buildMoodTheme(moodHex).surface200
  const white = hexToOklab('#ffffff')!
  const surface = hexToOklab(wash) ?? white
  // Matches --chrome-surface-glass ≈ 72% white.
  return oklabToHex({
    L: white.L * 0.72 + surface.L * 0.28,
    a: white.a * 0.72 + surface.a * 0.28,
    b: white.b * 0.72 + surface.b * 0.28,
  })
}

/** Darken OKLab ink until contrast vs chrome (+ optional wash) surfaces is safe. */
function ensureReadableInk(lab: Oklab, extraBackgrounds: string[] = []): string {
  let L = Math.min(BRAND_L_MAX, Math.max(BRAND_L_MIN, lab.L))
  let a = lab.a
  let b = lab.b
  let ink = oklabToHex({ L, a, b })

  // Prefer darkening lightness — keep chroma so page-to-page hue shifts stay visible.
  for (let i = 0; i < 28 && !meetsBrandContrast(ink, extraBackgrounds); i += 1) {
    L = Math.max(BRAND_L_MIN, L - 0.012)
    ink = oklabToHex({ L, a, b })
  }

  // Last resort: gently desaturate if still short of contrast at L floor.
  for (let i = 0; i < 10 && !meetsBrandContrast(ink, extraBackgrounds); i += 1) {
    a *= 0.9
    b *= 0.9
    ink = oklabToHex({ L, a, b })
  }

  if (!meetsBrandContrast(ink, extraBackgrounds)) {
    return DEFAULT_AMBIENT_GLOW.brand1
  }
  return ink
}

/**
 * Mood-tinted ink for glowpath:\ — keep the mood hue readable (deep 700–800
 * feel), then clamp only as far as contrast requires.
 */
function brandInkFromHex(hex: string, lightness = 0.44, chromaBoost = 1): string {
  const lab = hexToOklab(hex.trim()) ?? hexToOklab(DEFAULT_AMBIENT_GLOW.brand1)!
  const chroma = Math.hypot(lab.a, lab.b)
  // Dark inks need enough chroma to read as blue/rose/green, not near-black.
  const targetChroma =
    chroma < 0.015 ? 0 : Math.min(0.14, Math.max(0.08, chroma * 0.95) * chromaBoost)
  const scale = chroma > 1e-6 ? targetChroma / chroma : 0
  return ensureReadableInk(
    {
      L: lightness,
      a: lab.a * scale,
      b: lab.b * scale,
    },
    [glassOverWash(hex)],
  )
}

function brandInksFromPalette(colors: string[]): Pick<AmbientGlowColors, 'brand1' | 'brand2' | 'brand3'> {
  if (colors.length === 0) {
    return {
      brand1: DEFAULT_AMBIENT_GLOW.brand1,
      brand2: DEFAULT_AMBIENT_GLOW.brand2,
      brand3: DEFAULT_AMBIENT_GLOW.brand3,
    }
  }
  if (colors.length === 1) {
    // Same hue, slight L/chroma drift — readable shimmer, not a rainbow.
    return {
      brand1: brandInkFromHex(colors[0], 0.4, 0.95),
      brand2: brandInkFromHex(colors[0], 0.46, 1.08),
      brand3: brandInkFromHex(colors[0], 0.36, 0.88),
    }
  }
  return {
    brand1: brandInkFromHex(pick(colors, 0, colors[0]), 0.42, 1),
    brand2: brandInkFromHex(pick(colors, 1, colors[0]), 0.45, 1.05),
    brand3: brandInkFromHex(pick(colors, colors.length - 1, colors[0]), 0.38, 0.95),
  }
}

/**
 * Build four soft ambient bloom colors from a palette.
 * Uses surface200 so the wash still carries readable chroma on the app chrome.
 */
export function buildAmbientGlowColors(
  hexColors: string[],
  intensity: MoodIntensity = 'moderate',
): AmbientGlowColors {
  const colors = normalizeHexes(hexColors)
  if (colors.length === 0) {
    return DEFAULT_AMBIENT_GLOW
  }

  const [a1, a2, a3, a4] = BLOOM_ALPHA[intensity]
  // surface300 keeps more chroma so day-to-day shifts read clearly on chrome.
  const surfaceOf = (hex: string) => buildMoodTheme(hex, { intensity }).surface300
  const brands = brandInksFromPalette(colors)

  if (colors.length === 1) {
    const s = surfaceOf(colors[0])
    return {
      c1: withHexAlpha(s, a1),
      c2: withHexAlpha(s, a2),
      c3: withHexAlpha(s, a3),
      c4: withHexAlpha(s, a4),
      ...brands,
    }
  }

  if (colors.length === 2) {
    const a = surfaceOf(colors[0])
    const b = surfaceOf(colors[1])
    return {
      c1: withHexAlpha(a, a1),
      c2: withHexAlpha(b, a2),
      c3: withHexAlpha(b, a3),
      c4: withHexAlpha(a, a4),
      ...brands,
    }
  }

  const s1 = surfaceOf(pick(colors, 0, colors[0]))
  const s2 = surfaceOf(pick(colors, 1, colors[0]))
  const s3 = surfaceOf(pick(colors, 2, colors[0]))
  const s4 = surfaceOf(pick(colors, colors.length - 1, colors[0]))

  return {
    c1: withHexAlpha(s1, a1),
    c2: withHexAlpha(s2, a2),
    c3: withHexAlpha(s3, a3),
    c4: withHexAlpha(s4, a4),
    ...brands,
  }
}

export function ambientGlowToCssVars(colors: AmbientGlowColors): AmbientGlowCssVars {
  return {
    '--ambient-c1': colors.c1,
    '--ambient-c2': colors.c2,
    '--ambient-c3': colors.c3,
    '--ambient-c4': colors.c4,
    '--brand-ink-1': colors.brand1,
    '--brand-ink-2': colors.brand2,
    '--brand-ink-3': colors.brand3,
  }
}

export function buildAmbientGlowCssVars(
  hexColors: string[],
  intensity: MoodIntensity = 'moderate',
): AmbientGlowCssVars {
  return ambientGlowToCssVars(buildAmbientGlowColors(hexColors, intensity))
}

/** Stable key for comparing palettes (avoids redundant React updates). */
export function ambientPaletteKey(hexColors: string[]): string {
  return normalizeHexes(hexColors).map((h) => h.toLowerCase()).join('|')
}
