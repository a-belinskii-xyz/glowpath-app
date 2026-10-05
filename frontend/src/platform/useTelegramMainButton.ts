import { useEffect } from 'react'

import { setTelegramMainButton } from './telegram'
import { useSoftKeyboardOpen } from './useSoftKeyboardOpen'

export function useTelegramMainButton({
  text,
  visible,
  enabled,
  progress = false,
  onClick,
}: {
  text: string
  visible: boolean
  enabled: boolean
  progress?: boolean
  onClick: () => void
}): void {
  // Telegram docks MainButton right above the keyboard, where it is easy to hit by accident.
  const keyboardOpen = useSoftKeyboardOpen(visible)
  useEffect(() => {
    return setTelegramMainButton({
      text,
      visible,
      enabled,
      progress,
      suspended: keyboardOpen,
      onClick,
    })
  }, [text, visible, enabled, progress, keyboardOpen, onClick])
}
