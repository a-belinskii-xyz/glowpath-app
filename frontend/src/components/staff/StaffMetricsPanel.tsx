import { useEffect, useState } from 'react'

import { getStaffMetrics } from '../../api/staff'
import { useLocale } from '../../context/LocaleContext'
import { formatApiError } from '../../lib/errors'
import type { StaffMetricsResponse } from '../../types/staff'
import { PageErrorAlert } from '../PageErrorAlert'

export function StaffMetricsPanel() {
  const { t, locale } = useLocale()
  const [metrics, setMetrics] = useState<StaffMetricsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void getStaffMetrics()
      .then((response) => {
        if (!cancelled) setMetrics(response)
      })
      .catch((err) => {
        if (!cancelled) setError(formatApiError(err, t, 'errors.requestFailed'))
      })
    return () => {
      cancelled = true
    }
  }, [t])

  const dayFormat = new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : 'en-US', {
    day: '2-digit',
    month: '2-digit',
  })
  const formatPeriod = (startsAt: string, endsAt: string) =>
    `${dayFormat.format(new Date(startsAt))}–${dayFormat.format(new Date(endsAt))}`

  return (
    <div className="staff-panel">
      <PageErrorAlert error={error} />

      <section className="card staff-card" aria-labelledby="staff-metrics-weeks-title">
        <h2 id="staff-metrics-weeks-title" className="staff-card-title">
          {t('staff.metricsWeeksTitle')}
        </h2>
        <p className="muted staff-card-meta">
          {t('staff.metricsWeeksLead', { days: metrics?.regular_min_days ?? 3 })}
        </p>
        {metrics ? (
          <table className="staff-metrics-table">
            <thead>
              <tr>
                <th scope="col">{t('staff.metricsPeriod')}</th>
                <th scope="col">{t('staff.metricsSignups')}</th>
                <th scope="col">{t('staff.metricsActive')}</th>
                <th scope="col">{t('staff.metricsRegular')}</th>
              </tr>
            </thead>
            <tbody>
              {metrics.weeks.map((week) => (
                <tr key={week.starts_at}>
                  <th scope="row">{formatPeriod(week.starts_at, week.ends_at)}</th>
                  <td>{week.signups}</td>
                  <td>{week.active}</td>
                  <td>{week.regular}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </section>

      <section className="card staff-card" aria-labelledby="staff-metrics-sources-title">
        <h2 id="staff-metrics-sources-title" className="staff-card-title">
          {t('staff.metricsSourcesTitle')}
        </h2>
        <p className="muted staff-card-meta">{t('staff.metricsSourcesLead')}</p>
        {metrics && metrics.sources.length === 0 ? (
          <p className="muted staff-list-empty">{t('staff.metricsEmpty')}</p>
        ) : null}
        {metrics && metrics.sources.length > 0 ? (
          <table className="staff-metrics-table">
            <thead>
              <tr>
                <th scope="col">{t('staff.metricsSource')}</th>
                <th scope="col">{t('staff.metricsLast7')}</th>
                <th scope="col">{t('staff.metricsLast30')}</th>
                <th scope="col">{t('staff.metricsTotal')}</th>
              </tr>
            </thead>
            <tbody>
              {metrics.sources.map((row) => (
                <tr key={row.source}>
                  <th scope="row">{row.source}</th>
                  <td>{row.last_7_days}</td>
                  <td>{row.last_30_days}</td>
                  <td>{row.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </section>
    </div>
  )
}
