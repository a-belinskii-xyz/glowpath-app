import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'

import {
  ambientGlowToCssVars,
  ambientPaletteKey,
  buildAmbientGlowColors,
  DEFAULT_AMBIENT_GLOW,
  type AmbientGlowCssVars,
  type MoodIntensity,
} from '../design'

type AmbientGlowContextValue = {
  /** Replace the shell ambient palette. Pass [] / null to restore the default chrome glow. */
  setAmbientPalette: (colors: string[] | null, intensity?: MoodIntensity) => void
  cssVars: AmbientGlowCssVars
}

const AmbientGlowContext = createContext<AmbientGlowContextValue | null>(null)

export function AmbientGlowProvider({ children }: { children: ReactNode }) {
  const [cssVars, setCssVars] = useState<AmbientGlowCssVars>(() =>
    ambientGlowToCssVars(DEFAULT_AMBIENT_GLOW),
  )
  const paletteKeyRef = useRef(ambientPaletteKey([]))
  const intensityRef = useRef<MoodIntensity>('moderate')

  const setAmbientPalette = useCallback(
    (colors: string[] | null, intensity: MoodIntensity = 'moderate') => {
      const next = colors?.filter(Boolean) ?? []
      const key = ambientPaletteKey(next)
      if (key === paletteKeyRef.current && intensity === intensityRef.current) {
        return
      }
      paletteKeyRef.current = key
      intensityRef.current = intensity
      setCssVars(
        ambientGlowToCssVars(
          next.length === 0 ? DEFAULT_AMBIENT_GLOW : buildAmbientGlowColors(next, intensity),
        ),
      )
    },
    [],
  )

  const value = useMemo(
    () => ({ setAmbientPalette, cssVars }),
    [setAmbientPalette, cssVars],
  )

  return (
    <AmbientGlowContext.Provider value={value}>{children}</AmbientGlowContext.Provider>
  )
}

export function useAmbientGlow(): AmbientGlowContextValue {
  const ctx = useContext(AmbientGlowContext)
  if (!ctx) {
    throw new Error('useAmbientGlow must be used within AmbientGlowProvider')
  }
  return ctx
}

/**
 * Drive shell ambient glow from a static palette while the component is mounted.
 * Restores the default chrome glow on unmount.
 */
export function usePageAmbientGlow(
  colors: string[] | null | undefined,
  intensity: MoodIntensity = 'moderate',
) {
  const { setAmbientPalette } = useAmbientGlow()
  const key = ambientPaletteKey(colors?.filter(Boolean) ?? [])

  useEffect(() => {
    setAmbientPalette(key ? key.split('|') : [], intensity)
    return () => setAmbientPalette(null)
  }, [key, intensity, setAmbientPalette])
}
