/**
 * OKLab color math — perceptual conversions and wash/mix primitives.
 * Used by Mood Theme Builder and Gradient Engine.
 */

export type Oklab = { L: number; a: number; b: number }

function srgbChannelToLinear(c: number): number {
  const v = c / 255
  return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
}

function linearToSrgbChannel(c: number): number {
  const v = c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055
  return Math.min(255, Math.max(0, Math.round(v * 255)))
}

export function hexToOklab(hex: string): Oklab | null {
  const match = /^#([0-9A-Fa-f]{6})$/.exec(hex.trim())
  if (!match) {
    return null
  }
  const n = Number.parseInt(match[1], 16)
  const r = srgbChannelToLinear((n >> 16) & 0xff)
  const g = srgbChannelToLinear((n >> 8) & 0xff)
  const b = srgbChannelToLinear(n & 0xff)

  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)

  return {
    L: 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    a: 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    b: 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  }
}

export function oklabToHex({ L, a, b }: Oklab): string {
  const l_ = L + 0.3963377774 * a + 0.2158037573 * b
  const m_ = L - 0.1055613458 * a - 0.0638541728 * b
  const s_ = L - 0.0894841775 * a - 1.291485548 * b

  const l = l_ ** 3
  const m = m_ ** 3
  const s = s_ ** 3

  const r = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
  const g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
  const bl = -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s

  const toHex = (channel: number) => linearToSrgbChannel(channel).toString(16).padStart(2, '0')
  return `#${toHex(r)}${toHex(g)}${toHex(bl)}`
}

export function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value))
}

/**
 * Soft wash toward a surface lightness.
 * `targetL` 1 = pastel on light chrome; ~0.22 = tinted dark surface.
 */
export function washOklab(
  color: Oklab,
  washStrength: number,
  chromaScale: number,
  targetL = 1,
): Oklab {
  const t = clamp01(washStrength)
  const chroma = Math.max(0, chromaScale)
  const target = clamp01(targetL)
  return {
    L: color.L + (target - color.L) * t,
    a: color.a * chroma * (1 - t * 0.35),
    b: color.b * chroma * (1 - t * 0.35),
  }
}

export function mixOklab(colors: Oklab[], weights: number[]): Oklab {
  let sumW = 0
  let L = 0
  let a = 0
  let b = 0
  for (let i = 0; i < colors.length; i += 1) {
    const w = weights[i] ?? 0
    if (w <= 0) {
      continue
    }
    sumW += w
    L += colors[i].L * w
    a += colors[i].a * w
    b += colors[i].b * w
  }
  if (sumW <= 0) {
    return colors[0] ?? { L: 0.97, a: 0, b: 0 }
  }
  return { L: L / sumW, a: a / sumW, b: b / sumW }
}

export function earlyBiasWeights(count: number, orderPower: number): number[] {
  const p = Math.max(0.01, orderPower)
  return Array.from({ length: count }, (_, i) => (count - i) ** p)
}

export function lateBiasWeights(count: number, orderPower: number): number[] {
  const p = Math.max(0.01, orderPower)
  return Array.from({ length: count }, (_, i) => (i + 1) ** p)
}

export function equalWeights(count: number): number[] {
  return Array.from({ length: count }, () => 1)
}

export function withHexAlpha(hex: string, alphaByte: number): string {
  const match = /^#([0-9A-Fa-f]{6})$/.exec(hex.trim())
  if (!match) {
    return hex
  }
  const a = Math.min(255, Math.max(0, Math.round(alphaByte))).toString(16).padStart(2, '0')
  return `#${match[1]}${a}`
}
