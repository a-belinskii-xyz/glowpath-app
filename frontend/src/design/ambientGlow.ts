/**
 * Ambient Glow — soft page-level radial wash for glowpath:\ chrome.
 * Consumes mood/goal/tag hexes through OKLab wash so the shell “breathes”
 * the same palette language as day washes and icon glows.
 */

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
  /** Brand wordmark ink stops (near-black, softly tinted). */
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

/** Soft chrome default — readable brand + gentle blue/rose shell blooms. */
export const DEFAULT_AMBIENT_GLOW: AmbientGlowColors = {
  c1: 'rgb(147 197 253 / 72%)',
  c2: 'rgb(252 165 165 / 52%)',
  c3: 'rgb(165 180 252 / 48%)',
  c4: 'rgb(103 232 249 / 42%)',
  brand1: '#1f2937',
  brand2: '#1e3a5f',
  brand3: '#3b2f45',
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

/** Near-black ink with a quiet mood tint — for the glowpath:\ wordmark. */
function brandInkFromHex(hex: string, lightness = 0.28): string {
  const theme = buildMoodTheme(hex)
  const lab = hexToOklab(theme.text) ?? hexToOklab('#1f2937')!
  const tinted: Oklab = {
    L: lightness,
    a: lab.a * 0.55,
    b: lab.b * 0.55,
  }
  return oklabToHex(tinted)
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
    return {
      brand1: brandInkFromHex(colors[0], 0.27),
      brand2: brandInkFromHex(colors[0], 0.32),
      brand3: brandInkFromHex(colors[0], 0.24),
    }
  }
  return {
    brand1: brandInkFromHex(pick(colors, 0, colors[0]), 0.27),
    brand2: brandInkFromHex(pick(colors, 1, colors[0]), 0.3),
    brand3: brandInkFromHex(pick(colors, colors.length - 1, colors[0]), 0.25),
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
