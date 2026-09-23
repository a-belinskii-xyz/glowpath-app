import { useEffect, useRef } from 'react'

import { Alert } from './Alert'

type PageErrorAlertProps = {
  error: string | null
}

/** Page-level error that scrolls into view when the message changes. */
export function PageErrorAlert({ error }: PageErrorAlertProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!error) {
      return
    }
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [error])

  if (!error) {
    return null
  }

  return (
    <div ref={ref}>
      <Alert variant="error">{error}</Alert>
    </div>
  )
}
