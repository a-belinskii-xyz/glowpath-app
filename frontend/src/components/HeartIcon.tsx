type HeartIconProps = {
  filled?: boolean
}

export function HeartIcon({ filled = false }: HeartIconProps) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M12 21s-6.7-4.35-9.33-7.6C.5 10.9 1.1 7.2 3.9 5.55 6.05 4.3 8.55 4.85 10 6.5L12 8.7l2-2.2c1.45-1.65 3.95-2.2 6.1-.95 2.8 1.65 3.4 5.35 1.23 7.85C18.7 16.65 12 21 12 21z"
        fill={filled ? 'currentColor' : 'none'}
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinejoin="round"
      />
    </svg>
  )
}
