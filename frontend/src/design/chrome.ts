/**
 * Chrome System — UI tokens independent of mood.
 * Components should prefer these names over raw hex.
 * CSS mirrors the same values as `--chrome-*` in index.css.
 */

export const chrome = {
  bg: {
    app: '#f3f4f6',
  },
  surface: {
    default: '#ffffff',
    elevated: '#ffffff',
    inset: '#f3f4f6',
  },
  text: {
    primary: '#1f2937',
    secondary: '#6b7280',
    inverse: '#ffffff',
  },
  border: {
    subtle: '#f3f4f6',
    default: '#e5e7eb',
    strong: '#d1d5db',
  },
  action: {
    primary: '#2563eb',
    primaryHover: '#1d4ed8',
    danger: '#dc2626',
    success: '#047857',
    warning: '#b45309',
  },
  focus: {
    ring: '#93c5fd',
    ringSoft: 'rgb(147 197 253 / 35%)',
  },
} as const

export type ChromeTokens = typeof chrome

/** CSS custom property names for the Chrome System. */
export const chromeCssVars = {
  bgApp: '--chrome-bg-app',
  surface: '--chrome-surface',
  surfaceElevated: '--chrome-surface-elevated',
  surfaceInset: '--chrome-surface-inset',
  textPrimary: '--chrome-text-primary',
  textSecondary: '--chrome-text-secondary',
  textInverse: '--chrome-text-inverse',
  borderSubtle: '--chrome-border-subtle',
  borderDefault: '--chrome-border-default',
  borderStrong: '--chrome-border-strong',
  actionPrimary: '--chrome-action-primary',
  actionPrimaryHover: '--chrome-action-primary-hover',
  actionDanger: '--chrome-action-danger',
  actionSuccess: '--chrome-action-success',
  actionWarning: '--chrome-action-warning',
  focusRing: '--chrome-focus-ring',
  focusRingSoft: '--chrome-focus-ring-soft',
} as const
