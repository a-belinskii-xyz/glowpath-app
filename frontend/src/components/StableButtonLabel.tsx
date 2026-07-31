type StableButtonLabelProps = {
  active: string
  /** All candidate labels; width matches the widest so the button does not jump. */
  labels: readonly string[]
}

export function StableButtonLabel({ active, labels }: StableButtonLabelProps) {
  const unique = [...new Set(labels.filter(Boolean))]
  return (
    <span className="button-stable-label">
      {unique.map((label) => (
        <span
          key={label}
          className={`button-stable-label-item${label === active ? ' is-active' : ''}`}
          aria-hidden={label !== active}
        >
          {label}
        </span>
      ))}
    </span>
  )
}
