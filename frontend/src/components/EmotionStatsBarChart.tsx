import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import type { MoodEntryStatsResponse, MoodMonthComparisonPublic } from '../types/mood'
import { MoodScoreIcon } from './MoodScoreIcon'

type EmotionStatsBarChartProps = {
  stats: MoodEntryStatsResponse
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

export function EmotionStatsBarChart({ stats }: EmotionStatsBarChartProps) {
  const { t, tp } = useLocale()
  const { getScoreColor, getScoreStyle } = useMoodPreferences()
  const { scores, total_entries: totalEntries, month_index: monthIndex, comparison } = stats
  const maxCount = Math.max(1, ...scores.map((item) => item.count))
  const currentLabel = formatIndex(comparison.current_index ?? monthIndex)
  const previousLabel = formatIndex(comparison.previous_index)

  return (
    <section className="emotion-stats" aria-label={t('emotionStats.ariaLabel')}>
      <div className="emotion-stats-header">
        <h2 className="emotion-stats-title">{t('emotionStats.title')}</h2>
        <p className="emotion-stats-summary muted">
          {totalEntries === 0
            ? t('emotionStats.noEntries')
            : tp(totalEntries, {
                one: 'emotionStats.entryCountOne',
                few: 'emotionStats.entryCountFew',
                many: 'emotionStats.entryCountMany',
              })}
        </p>
      </div>

      <p className={comparisonClassName(comparison.verdict)}>{comparison.message}</p>
      {currentLabel && previousLabel && comparison.verdict !== 'insufficient_data' ? (
        <p className="emotion-stats-indexes muted">
          {t('emotionStats.monthIndex', { current: currentLabel, previous: previousLabel })}
          {comparison.delta !== null
            ? ` (${comparison.delta > 0 ? '+' : ''}${comparison.delta.toFixed(2)})`
            : null}
        </p>
      ) : null}

      <div className="emotion-stats-chart" role="img" aria-label={t('emotionStats.chartAria')}>
        {scores.map((item) => {
          const heightPercent = totalEntries === 0 ? 0 : (item.count / maxCount) * 100
          const scoreStyle = getScoreStyle(item.score)
          return (
            <div key={item.score} className="emotion-stats-bar-col">
              <span className="emotion-stats-count" aria-hidden={item.count === 0}>
                {item.count > 0 ? item.count : ''}
              </span>
              <div className="emotion-stats-bar-track">
                <div
                  className="emotion-stats-bar"
                  style={{
                    height: `${heightPercent}%`,
                    backgroundColor: getScoreColor(item.score),
                  }}
                  title={`${item.score_label}: ${item.count}`}
                />
              </div>
              <MoodScoreIcon
                style={scoreStyle}
                className="emotion-stats-emoji"
                fallbackScore={item.score}
              />
              <span className="emotion-stats-label">{item.score_label}</span>
              <span className="visually-hidden">
                {item.score_label}: {item.count}
              </span>
            </div>
          )
        })}
      </div>
    </section>
  )
}
