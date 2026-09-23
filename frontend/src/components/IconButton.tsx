import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { Link, type LinkProps } from 'react-router-dom'

type SharedProps = {
  label: string
  children: ReactNode
  variant?: 'default' | 'danger' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  isActive?: boolean
  className?: string
}

type ButtonProps = SharedProps &
  ButtonHTMLAttributes<HTMLButtonElement> & {
    to?: never
  }

type LinkButtonProps = SharedProps &
  Omit<LinkProps, 'className' | 'children'> & {
    to: LinkProps['to']
  }

function classNameFor({
  variant = 'default',
  size = 'md',
  isActive = false,
  className = '',
}: Pick<SharedProps, 'variant' | 'size' | 'isActive' | 'className'>) {
  return [
    'icon-button',
    `icon-button-${size}`,
    variant !== 'default' ? `icon-button-${variant}` : '',
    isActive ? 'is-active' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ')
}

export const IconButton = forwardRef<HTMLButtonElement, ButtonProps>(function IconButton(
  { label, children, variant, size, isActive, className, type = 'button', ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={classNameFor({ variant, size, isActive, className })}
      aria-label={label}
      title={label}
      {...props}
    >
      {children}
    </button>
  )
})

export function IconLinkButton({
  label,
  children,
  variant,
  size,
  isActive,
  className,
  ...props
}: LinkButtonProps) {
  return (
    <Link
      className={classNameFor({ variant, size, isActive, className })}
      aria-label={label}
      title={label}
      {...props}
    >
      {children}
    </Link>
  )
}
