import { useEffect, useState } from 'react'

import { getColorScheme, subscribeColorScheme, type ColorScheme } from '../design/colorScheme'

export function useColorScheme(): ColorScheme {
  const [scheme, setScheme] = useState<ColorScheme>(getColorScheme)

  useEffect(() => {
    setScheme(getColorScheme())
    return subscribeColorScheme(() => setScheme(getColorScheme()))
  }, [])

  return scheme
}
