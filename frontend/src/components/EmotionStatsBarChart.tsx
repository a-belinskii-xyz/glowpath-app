import { type CSSProperties } from 'react'
import { Link } from 'react-router-dom'

import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { buildMoodTheme, moodGlowForImpact } from '../design'
import type { MoodEntryStatsResponse, MoodMonthComparisonPublic } from '../types/mood'
import { MoodScoreIcon } from './MoodScoreIcon'

type EmotionStatsBarChartProps = {
  stats: MoodEntryStatsResponse
  /** YYYY-MM-DD — when set with canAddToday, mood columns open create for that day. */
  todayDate?: string
  canAddToday?: boolean
}

function comparisonClassName(verdict: MoodMonthComparisonPublic['verdict']): string {
  switch (verdict) {
    case 'much_better':
    case 'better':
      return 'emotion-stats-comparison emotion-stats-comparison-better'
    case 'much_worse':
    case 'worse':
      return 'emotion-stats-comparison emotion-stats-comparison-worse'
    case 'similar':
      return 'emotion-stats-comparison emotion-stats-comparison-similar'
    default:
      return 'emotion-stats-comparison emotion-stats-comparison-muted'
  }
}

function formatIndex(value: number | null): string | null {
  if (value === null) {
    return null
  }
  return value.toFixed(2)
}

function entryCreatePath(score: number, todayDate?: string): string {
  const params = new URLSearchParams({ score: String(score) })
  if (todayDate) {
    params.set('date', todayDate)
  }
  return `/entries/new?${params.toString()}`
}

export function EmotionStatsBarChart({
  stats,
  todayDate,
  canAddToday = false,
}: EmotionStatsBarChartProps) {
  const { t, tp } = useLocale()
  const { getScoreColor, getScoreStyle } = useMoodPreferences()
  const { scores, total_entries: totalEntries, month_index: monthIndex, comparison } = stats
  const maxCount = Math.max(1, ...scores.map((item) => item.count))
  const currentLabel = formatIndex(comparison.current_index ?? monthIndex)
  const previousLabel = formatIndex(comparison.previous_index)
  const isEmpty = totalEntries === 0
  const interactive = canAddToday && Boolean(todayDate)

  return (
    <section className="emotion-stats" aria-label={t('emotionStats.ariaLabel')}>
      <div className="emotion-stats-header">
        <h2 className="emotion-stats-title">{t('emotionStats.title')}</h2>
        <p className="emotion-stats-summary muted">
          {isEmpty
            ? t('emotionStats.noEntries')
            : tp(totalEntries, {
                one: 'emotionStats.entryCountOne',
                few: 'emotionStats.entryCountFew',
                many: 'emotionStats.entryCountMany',
              })}
        </p>
      </div>

      {isEmpty ? (
        <div className="emotion-stats-empty">
          <p className="emotion-stats-comparison emotion-stats-comparison-muted">
            {interactive ? t('emotionStats.emptyPrompt') : t('emotionStats.emptyPromptPast')}
          </p>
          {interactive ? (
            <div
              className="emotion-stats-chart emotion-stats-empty-pick"
              role="group"
              aria-label={t('emotionStats.emptyPickAria')}
              style={{
                gridTemplateColumns: `repeat(${Math.max(1, scores.length)}, minmax(0, 1fr))`,
              }}
            >
              {scores.map((item, index) => {
                const scoreStyle = getScoreStyle(item.score)
                const color = getScoreColor(item.score)
                const theme = buildMoodTheme(color)
                const previewGlow = moodGlowForImpact(color, 0.28)

                return (
                  <Link
                    key={item.score}
                    className="emotion-stats-empty-mood"
                    to={entryCreatePath(item.score, todayDate)}
                    style={
                      {
                        ['--emotion-empty-bar' as string]: theme.chart,
                        ['--emotion-empty-wash' as string]: theme.wash,
                        ['--emotion-empty-delay' as string]: `${index * 0.28}s`,
                        ['--emotion-empty-glow' as string]: previewGlow?.boxShadow ?? 'none',
                      } as CSSProperties
                    }
                    aria-label={t('emotionStats.emptyMoodAria', { label: item.score_label })}
                  >
                    <span className="emotion-stats-empty-cue" aria-hidden="true">
                      +
                    </span>
                    <div className="emotion-stats-bar-track emotion-stats-empty-track">
                      <div className="emotion-stats-bar emotion-stats-empty-bar" />
                    </div>
                    <span className="emotion-stats-emoji-wrap">
                      <MoodScoreIcon
                        style={scoreStyle}
                        className="emotion-stats-emoji"
                        fallbackScore={item.score}
                      />
                    </span>
                    <span className="emotion-stats-label">{item.score_label}</span>
                  </Link>
                )
              })}
            </div>
          ) : null}
        </div>
      ) : (
        <>
          <p className={comparisonClassName(comparison.verdict)}>{comparison.message}</p>
          {currentLabel && previousLabel && comparison.verdict !== 'insufficient_data' ? (
            <>
              <p className="emotion-stats-indexes muted">
                {t('emotionStats.monthIndex', { current: currentLabel, previous: previousLabel })}
                {comparison.delta !== null
                  ? ` (${comparison.delta > 0 ? '+' : ''}${comparison.delta.toFixed(2)})`
                  : null}
              </p>
              <p
                className="emotion-stats-indexes muted"
                title={t('emotionStats.scaleLegend')}
              >
                {t('emotionStats.scaleHint')}
              </p>
            </>
          ) : null}

          <p className="emotion-stats-indexes muted">
            {interactive ? t('emotionStats.distributionHintAdd') : t('emotionStats.distributionHint')}
          </p>

          <div
            className={`emotion-stats-chart${interactive ? ' emotion-stats-chart-interactive' : ''}`}
            role={interactive ? 'group' : 'img'}
            aria-label={
              interactive ? t('emotionStats.chartPickAria') : t('emotionStats.chartAria')
            }
            style={{ gridTemplateColumns: `repeat(${Math.max(1, scores.length)}, minmax(0, 1fr))` }}
          >
            {scores.map((item) => {
              const percent = Math.round((item.count / totalEntries) * 100)
              const heightPercent = (item.count / maxCount) * 100
              const scoreStyle = getScoreStyle(item.score)
              const color = getScoreColor(item.score)
              const theme = buildMoodTheme(color)
              const impact = item.count / totalEntries
              const glow = moodGlowForImpact(color, impact)
              const columnStyle = {
                ['--emotion-empty-bar' as string]: theme.chart,
                ['--emotion-empty-wash' as string]: theme.wash,
              } as CSSProperties

              const body = (
                <>
                  <span className="emotion-stats-count" aria-hidden={item.count === 0}>
                    {item.count > 0
                      ? t('emotionStats.countWithPercent', {
                          count: item.count,
                          percent,
                        })
                      : interactive
                        ? '+'
                        : ''}
                  </span>
                  <div className="emotion-stats-bar-track">
                    <div
                      className={`emotion-stats-bar${glow ? ' has-glow' : ''}`}
                      style={{
                        height: `${heightPercent}%`,
                        backgroundColor: theme.chart,
                        boxShadow: glow?.boxShadow,
                      }}
                      title={`${item.score_label}: ${item.count} (${percent}%)`}
                    />
                  </div>
                  <span
                    className="emotion-stats-emoji-wrap"
                    style={glow ? { filter: glow.filter } : undefined}
                  >
                    <MoodScoreIcon
                      style={scoreStyle}
                      className="emotion-stats-emoji"
                      fallbackScore={item.score}
                    />
                  </span>
                  <span className="emotion-stats-label">{item.score_label}</span>
                  <span className="visually-hidden">
                    {item.score_label}: {item.count} ({percent}%)
                  </span>
                </>
              )

              if (interactive) {
                return (
                  <Link
                    key={item.score}
                    className="emotion-stats-bar-col emotion-stats-bar-col-link"
                    to={entryCreatePath(item.score, todayDate)}
                    style={columnStyle}
                    aria-label={t('emotionStats.addTodayMoodAria', { label: item.score_label })}
                  >
                    {body}
                  </Link>
                )
              }

              return (
                <div key={item.score} className="emotion-stats-bar-col" style={columnStyle}>
                  {body}
                </div>
              )
            })}
          </div>
        </>
      )}
    </section>
  )
}
