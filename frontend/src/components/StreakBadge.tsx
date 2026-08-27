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

  return (
    <span
      className={`streak-badge${loggedToday ? ' is-active' : ''}`}
      aria-label={t('entries.streakAria', { count: days })}
    >
      <span className="streak-badge-fire" aria-hidden="true">
        🔥
      </span>
      <span className="streak-badge-count">× {daysLabel}</span>
    </span>
  )
}
