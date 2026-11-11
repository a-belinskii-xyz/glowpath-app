import { useLocale } from '../../context/LocaleContext'
import { intlLocale } from '../../i18n/t'
import type { StaffMetricsResponse, StaffRetention } from '../../types/staff'

const DAY_MS = 24 * 60 * 60 * 1000

type Props = {
  metrics: StaffMetricsResponse | null
}

/** Signup cohorts × weeks W1–W4 since signup (GP-68): the W4 checkpoint lives in the total row. */
export function StaffCohortsCard({ metrics }: Props) {
  const { t, locale } = useLocale()
  const tag = intlLocale(locale)
  // Cohort weeks start on Monday 00:00 UTC, so print them in UTC too.
  const dayFormat = new Intl.DateTimeFormat(tag, { day: '2-digit', month: '2-digit', timeZone: 'UTC' })
  const percentFormat = new Intl.NumberFormat(tag, { style: 'percent', maximumFractionDigits: 0 })
  const weekLabel = (weekStart: string) => {
    const start = new Date(weekStart)
    return `${dayFormat.format(start)}–${dayFormat.format(new Date(start.getTime() + 6 * DAY_MS))}`
  }
  const weekNumbers = metrics ? metrics.cohort_total.eligible.map((_, index) => index + 1) : []

  const retentionCells = (retention: StaffRetention) => (
    <>
      <td>{retention.size}</td>
      {weekNumbers.map((week, index) => {
        const eligible = retention.eligible[index] ?? 0
        const active = retention.active[index] ?? null
        const regular = retention.regular[index] ?? null
        if (active === null || regular === null || eligible === 0) {
          return (
            <td key={week} className="staff-cohort-cell is-empty" title={t('staff.cohortsNotYet')}>
              —
            </td>
          )
        }
        return (
          <td key={week} className="staff-cohort-cell">
            <span className="staff-cohort-main">
              {regular}/{eligible}
            </span>
            <span className="staff-cohort-percent">{percentFormat.format(regular / eligible)}</span>
            <span className="staff-cohort-any">{t('staff.cohortsAnyDay', { n: active })}</span>
          </td>
        )
      })}
    </>
  )

  return (
    <section className="card staff-card" aria-labelledby="staff-cohorts-title">
      <h2 id="staff-cohorts-title" className="staff-card-title">
        {t('staff.cohortsTitle')}
      </h2>
      <p className="muted staff-card-meta">
        {t('staff.cohortsLead', {
          weeks: metrics?.cohort_weeks ?? 8,
          days: metrics?.regular_min_days ?? 2,
        })}
      </p>
      {metrics && metrics.cohorts.length === 0 ? (
        <p className="muted staff-list-empty">
          {t('staff.cohortsEmpty', { weeks: metrics.cohort_weeks })}
        </p>
      ) : null}
      {metrics && metrics.cohorts.length > 0 ? (
        <div className="staff-table-scroll">
          <table className="staff-metrics-table staff-cohorts-table">
            <thead>
              <tr>
                <th scope="col">{t('staff.cohortsWeek')}</th>
                <th scope="col" className="staff-cohort-source">
                  {t('staff.metricsSource')}
                </th>
                <th scope="col">{t('staff.cohortsSize')}</th>
                {weekNumbers.map((week) => (
                  <th key={week} scope="col">
                    W{week}
                  </th>
                ))}
              </tr>
            </thead>
            {metrics.cohorts.map((cohort) => {
              const week = weekLabel(cohort.week_start)
              const [only] = cohort.sources
              if (cohort.sources.length === 1 && only) {
                return (
                  <tbody key={cohort.week_start}>
                    <tr>
                      <th scope="row">{week}</th>
                      <td className="staff-cohort-source">{only.source}</td>
                      {retentionCells(cohort.retention)}
                    </tr>
                  </tbody>
                )
              }
              return (
                <tbody key={cohort.week_start}>
                  <tr className="is-summary">
                    <th scope="row" rowSpan={cohort.sources.length + 1}>
                      {week}
                    </th>
                    <td className="staff-cohort-source">{t('staff.cohortsAllSources')}</td>
                    {retentionCells(cohort.retention)}
                  </tr>
                  {cohort.sources.map((row) => (
                    <tr key={row.source} className="is-source">
                      <td className="staff-cohort-source">{row.source}</td>
                      {retentionCells(row.retention)}
                    </tr>
                  ))}
                </tbody>
              )
            })}
            <tfoot>
              <tr className="is-summary">
                <th scope="row" colSpan={2}>
                  {t('staff.cohortsTotal')}
                </th>
                {retentionCells(metrics.cohort_total)}
              </tr>
            </tfoot>
          </table>
        </div>
      ) : null}
    </section>
  )
}
