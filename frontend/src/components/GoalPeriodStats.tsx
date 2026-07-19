import { useMemo } from 'react'

import { useLocale } from '../context/LocaleContext'
import { moodGlowForImpact } from '../design'
import { todayKey } from '../lib/datetime'
import type { GoalPeriodStatPublic } from '../types/goal'
import { GoalIcon } from './GoalIcon'

export type GoalStatsPeriod = 'week' | 'month'

type GoalPeriodStatsProps = {
  items: GoalPeriodStatPublic[]
  period: GoalStatsPeriod
  periodDays: number
  timeZone: string
  isCurrentPeriod: boolean
  isRefreshing?: boolean
  weekLabel?: string
  canGoPreviousWeek?: boolean
  canGoNextWeek?: boolean
  onPreviousWeek?: () => void
  onNextWeek?: () => void
  onPeriodChange: (period: GoalStatsPeriod) => void
}

type GoalPeriodStatus = 'met' | 'on_track' | 'at_risk' | 'ended'

function daysLeftInPeriod(
  period: GoalStatsPeriod,
  _periodDays: number,
  timeZone: string,
  isCurrentPeriod: boolean,
): number {
  if (!isCurrentPeriod) {
    return 0
  }
  if (period === 'week') {
    const [year, month, day] = todayKey(timeZone).split('-').map(Number)
    const utcDay = new Date(Date.UTC(year, month - 1, day)).getUTCDay()
    const monday0 = (utcDay + 6) % 7
    return 7 - monday0
  }
  const today = todayKey(timeZone)
  const [year, month, day] = today.split('-').map(Number)
  const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate()
  return Math.max(0, daysInMonth - day + 1)
}

function goalStatus(
  item: GoalPeriodStatPublic,
  daysLeft: number,
  isCurrentPeriod: boolean,
): GoalPeriodStatus {
  const done = item.completed_in_period
  const target = item.period_target
  if (done >= target) {
    return 'met'
  }
  if (!isCurrentPeriod) {
    return 'ended'
  }
  if (target - done > daysLeft) {
    return 'at_risk'
  }
  return 'on_track'
}

function statusClassName(status: GoalPeriodStatus): string {
  switch (status) {
    case 'met':
      return 'goal-week-stats-status goal-week-stats-status-met'
    case 'at_risk':
      return 'goal-week-stats-status goal-week-stats-status-risk'
    case 'ended':
      return 'goal-week-stats-status goal-week-stats-status-ended'
    default:
      return 'goal-week-stats-status goal-week-stats-status-track'
  }
}

export function GoalPeriodStats({
  items,
  period,
  periodDays,
  timeZone,
  isCurrentPeriod,
  isRefreshing = false,
  weekLabel,
  canGoPreviousWeek = true,
  canGoNextWeek = true,
  onPreviousWeek,
  onNextWeek,
  onPeriodChange,
}: GoalPeriodStatsProps) {
  const { t } = useLocale()
  const daysLeft = daysLeftInPeriod(period, periodDays, timeZone, isCurrentPeriod)

  const sortedItems = useMemo(
    () => [...items].sort((a, b) => a.sort_order - b.sort_order || a.slug.localeCompare(b.slug)),
    [items],
  )

  const metCount = sortedItems.filter(
    (item) => item.completed_in_period >= item.period_target,
  ).length
  const doneTotal = sortedItems.reduce(
    (sum, item) => sum + Math.min(item.completed_in_period, item.period_target),
    0,
  )
  const targetTotal = sortedItems.reduce((sum, item) => sum + item.period_target, 0)

  const title = period === 'week' ? t('goalWeekStats.titleWeek') : t('goalWeekStats.titleMonth')
  const summary =
    sortedItems.length === 0
      ? t('goalWeekStats.noGoals')
      : metCount === sortedItems.length
        ? period === 'week'
          ? t('goalWeekStats.allMetWeek')
          : t('goalWeekStats.allMetMonth')
        : metCount === 0
          ? period === 'week'
            ? t('goalWeekStats.noneMetWeek')
            : t('goalWeekStats.noneMetMonth')
          : t('goalWeekStats.someMet', { met: metCount, total: sortedItems.length })

  const summaryClass =
    sortedItems.length === 0
      ? 'goal-week-stats-summary muted'
      : metCount === sortedItems.length
        ? 'goal-week-stats-summary goal-week-stats-summary-met'
        : metCount === 0
          ? 'goal-week-stats-summary goal-week-stats-summary-muted'
          : 'goal-week-stats-summary goal-week-stats-summary-progress'

  return (
    <section
      className={`goal-week-stats${isRefreshing ? ' is-refreshing' : ''}`}
      aria-busy={isRefreshing || undefined}
      aria-label={t('goalWeekStats.ariaLabel')}
    >
      <div className="goal-week-stats-header">
        <h2 className="goal-week-stats-title">{title}</h2>
        {sortedItems.length > 0 ? (
          <p className="goal-week-stats-totals muted">
            {t('goalWeekStats.completions', { done: doneTotal, target: targetTotal })}
          </p>
        ) : null}
      </div>

      <div className="goal-stats-period-toggle" role="group" aria-label={t('goalWeekStats.periodGroup')}>
        <button
          type="button"
          className={`button button-secondary button-small${period === 'week' ? ' is-active' : ''}`}
          aria-pressed={period === 'week'}
          onClick={() => onPeriodChange('week')}
        >
          {t('goalWeekStats.periodWeek')}
        </button>
        <button
          type="button"
          className={`button button-secondary button-small${period === 'month' ? ' is-active' : ''}`}
          aria-pressed={period === 'month'}
          onClick={() => onPeriodChange('month')}
        >
          {t('goalWeekStats.periodMonth')}
        </button>
      </div>

      {period === 'week' && weekLabel && onPreviousWeek && onNextWeek ? (
        <div className="goal-week-nav" aria-label={t('goalWeekStats.weekNav')}>
          <button
            type="button"
            className="button button-secondary button-small"
            onClick={onPreviousWeek}
            disabled={!canGoPreviousWeek}
          >
            {t('common.previous')}
          </button>
          <p className="goal-week-nav-label">{weekLabel}</p>
          <button
            type="button"
            className="button button-secondary button-small"
            onClick={onNextWeek}
            disabled={!canGoNextWeek}
          >
            {t('common.next')}
          </button>
        </div>
      ) : null}

      <p className={summaryClass}>{summary}</p>

      {sortedItems.length > 0 ? (
        <ul className="goal-week-stats-list" aria-label={t('goalWeekStats.chartAria')}>
          {sortedItems.map((item) => {
            const done = item.completed_in_period
            const target = item.period_target
            const status = goalStatus(item, daysLeft, isCurrentPeriod)
            const widthPercent = Math.min(100, (done / Math.max(1, target)) * 100)
            // Progress toward own target + share of period completions.
            const progressImpact = Math.min(1, done / Math.max(1, target))
            const shareImpact = doneTotal > 0 ? Math.min(done, target) / doneTotal : 0
            const impact = Math.max(progressImpact * 0.65, shareImpact)
            const glow = moodGlowForImpact(item.color, impact)
            const statusLabel =
              status === 'met'
                ? t('goalWeekStats.statusMet')
                : status === 'at_risk'
                  ? t('goalWeekStats.statusAtRisk')
                  : status === 'ended'
                    ? t('goalWeekStats.statusEnded')
                    : t('goalWeekStats.statusOnTrack')

            return (
              <li key={item.id} className="goal-week-stats-row">
                <div className="goal-week-stats-row-top">
                  <span className="goal-week-stats-label">
                    <span
                      className="goal-week-stats-icon-wrap"
                      style={glow ? { filter: glow.filter } : undefined}
                    >
                      <GoalIcon
                        style={{
                          color: item.color,
                          icon_type: item.icon_type,
                          icon: item.icon,
                        }}
                        className="goal-week-stats-icon"
                      />
                    </span>
                    <span className="goal-week-stats-name">{item.label}</span>
                  </span>
                  <span className="goal-week-stats-progress-text">
                    {t('goalsPage.weekProgress', { done, target })}
                  </span>
                </div>
                <div
                  className="goal-week-stats-track"
                  role="progressbar"
                  aria-valuenow={Math.min(done, target)}
                  aria-valuemin={0}
                  aria-valuemax={target}
                  aria-label={`${item.label}: ${done} / ${target}`}
                >
                  <div
                    className={`goal-week-stats-fill${glow ? ' has-glow' : ''}`}
                    style={{
                      width: `${widthPercent}%`,
                      backgroundColor: item.color,
                      boxShadow: glow?.boxShadow,
                    }}
                  />
                </div>
                <span className={statusClassName(status)}>{statusLabel}</span>
              </li>
            )
          })}
        </ul>
      ) : null}
    </section>
  )
}
