import { useEffect } from 'react'

import { setTelegramMainButton } from './telegram'

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
  useEffect(() => {
    return setTelegramMainButton({
      text,
      visible,
      enabled,
      progress,
      onClick,
    })
  }, [text, visible, enabled, progress, onClick])
}
