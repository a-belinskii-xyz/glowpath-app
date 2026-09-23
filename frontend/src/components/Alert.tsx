import type { ReactNode } from 'react'

type AlertProps = {
  variant?: 'error' | 'success' | 'info' | 'warning'
  children: ReactNode
}

export function Alert({ variant = 'info', children }: AlertProps) {
  return <div className={`alert alert-${variant}`}>{children}</div>
}
