import { useLocale } from '../context/LocaleContext'

function SkeletonStatus({ label }: { label: string }) {
  return <span className="visually-hidden">{label}</span>
}

export function CalendarSkeleton() {
  const { t } = useLocale()
  return (
    <div className="skeleton-calendar" aria-busy="true">
      <SkeletonStatus label={t('common.loadingCalendar')} />
      <div className="skeleton-calendar-weekdays">
        {Array.from({ length: 7 }, (_, index) => (
          <span key={index} className="skeleton-block skeleton-calendar-weekday" />
        ))}
      </div>
      <div className="skeleton-calendar-grid">
        {Array.from({ length: 35 }, (_, index) => (
          <span key={index} className="skeleton-block skeleton-calendar-dot" />
        ))}
      </div>
    </div>
  )
}

export function StatsSkeleton() {
  const { t } = useLocale()
  const heights = [42, 68, 36, 80, 54, 72, 48]
  return (
    <div className="skeleton-stats" aria-busy="true">
      <SkeletonStatus label={t('common.loadingStats')} />
      <span className="skeleton-block skeleton-stats-title" />
      <div className="skeleton-stats-bars">
        {heights.map((height, index) => (
          <span
            key={index}
            className="skeleton-block skeleton-stats-bar"
            style={{ height: `${height}%` }}
          />
        ))}
      </div>
    </div>
  )
}

export function GoalStatsSkeleton() {
  const { t } = useLocale()
  return (
    <div className="skeleton-goals" aria-busy="true">
      <SkeletonStatus label={t('common.loadingGoalStats')} />
      {Array.from({ length: 3 }, (_, index) => (
        <div key={index} className="skeleton-goal-row">
          <span className="skeleton-block skeleton-dot" />
          <span className="skeleton-block skeleton-line" />
        </div>
      ))}
    </div>
  )
}

export function EntriesSkeleton() {
  const { t } = useLocale()
  return (
    <div className="skeleton-entries" aria-busy="true">
      <SkeletonStatus label={t('common.loadingEntries')} />
      {Array.from({ length: 2 }, (_, day) => (
        <div key={day} className="skeleton-day">
          <span className="skeleton-block skeleton-day-title" />
          {Array.from({ length: 2 }, (_, row) => (
            <div key={row} className="skeleton-entry">
              <span className="skeleton-block skeleton-entry-time" />
              <span className="skeleton-block skeleton-entry-note" />
              <span className="skeleton-tags">
                <span className="skeleton-block skeleton-dot" />
                <span className="skeleton-block skeleton-dot" />
                <span className="skeleton-block skeleton-pill" />
              </span>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

export function InsightsSkeleton() {
  const { t } = useLocale()
  return (
    <div className="skeleton-insights" aria-busy="true">
      <SkeletonStatus label={t('common.loadingInsights')} />
      <span className="skeleton-block skeleton-insights-title" />
      <span className="skeleton-block skeleton-insights-body" />
    </div>
  )
}
