/**
 * Motion System — shared timing / easing for UI transitions.
 * Prefer these over one-off durations in components and CSS.
 */

export const motion = {
  hover: {
    durationMs: 120,
    easing: 'ease',
  },
  selection: {
    durationMs: 180,
    easing: 'ease',
  },
  highlight: {
    /** Transition on the highlighted element itself. */
    durationMs: 350,
    easing: 'ease',
    /** How long the highlight class stays applied (JS). */
    holdMs: 1600,
  },
  reveal: {
    durationMs: 220,
    easing: 'ease',
  },
  press: {
    durationMs: 120,
    easing: 'ease',
  },
  /** Vertical entry reader: snap between notes. */
  pager: {
    durationMs: 340,
    easing: 'cubic-bezier(0.22, 1, 0.36, 1)',
    /** Ignore a new wheel/swipe commit for this long after a snap. */
    lockMs: 420,
  },
  /** Ambient shell glow color crossfade while scrolling moods. */
  ambient: {
    durationMs: 1100,
    easing: 'ease',
  },
  /** Brand wordmark hue drift — intentionally glacial. */
  brand: {
    durationMs: 72000,
    easing: 'ease-in-out',
  },
  /** Month recap: a glow planet, or a shareable poster, then a quiet stats reveal. */
  recap: {
    formMs: 880,
    orbitMs: 4200,
    revealMs: 780,
    easing: 'cubic-bezier(0.33, 0.05, 0.2, 1)',
  },
} as const

export type MotionTokens = typeof motion

export const motionCssVars = {
  hoverDuration: '--motion-hover-duration',
  hoverEasing: '--motion-hover-easing',
  selectionDuration: '--motion-selection-duration',
  selectionEasing: '--motion-selection-easing',
  highlightDuration: '--motion-highlight-duration',
  highlightEasing: '--motion-highlight-easing',
  revealDuration: '--motion-reveal-duration',
  revealEasing: '--motion-reveal-easing',
  pressDuration: '--motion-press-duration',
  pressEasing: '--motion-press-easing',
  ambientDuration: '--motion-ambient-duration',
  ambientEasing: '--motion-ambient-easing',
  brandDuration: '--motion-brand-duration',
  brandEasing: '--motion-brand-easing',
} as const

export function motionCss(durationMs: number, easing: string): string {
  return `${durationMs}ms ${easing}`
}
