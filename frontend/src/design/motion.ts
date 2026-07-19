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
} as const

export function motionCss(durationMs: number, easing: string): string {
  return `${durationMs}ms ${easing}`
}
