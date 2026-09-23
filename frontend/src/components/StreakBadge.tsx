import { useLocale } from '../context/LocaleContext'

export function StreakBadge({
  days,
  loggedToday,
}: {
  days: number
  loggedToday: boolean
}) {
  const { t, tp } = useLocale()
  const daysLabel = tp(days, {
    one: 'entries.streakOne',
    few: 'entries.streakFew',
    many: 'entries.streakMany',
  })
  const idle = days <= 0
  const stateClass = idle ? ' is-idle' : loggedToday ? ' is-active' : ''

  return (
    <span
      className={`streak-badge${stateClass}`}
      aria-label={t('entries.streakAria', { count: days })}
    >
      <span className="streak-badge-fire" aria-hidden="true">
        🔥
      </span>
      <span className="streak-badge-count">× {daysLabel}</span>
    </span>
  )
}
