import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { buildMoodTheme, moodGlowForImpact } from '../design'
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

      <p className="emotion-stats-indexes muted">{t('emotionStats.distributionHint')}</p>

      <div
        className="emotion-stats-chart"
        role="img"
        aria-label={t('emotionStats.chartAria')}
        style={{ gridTemplateColumns: `repeat(${Math.max(1, scores.length)}, minmax(0, 1fr))` }}
      >
        {scores.map((item) => {
          const percent = totalEntries === 0 ? 0 : Math.round((item.count / totalEntries) * 100)
          const heightPercent = totalEntries === 0 ? 0 : percent
          const scoreStyle = getScoreStyle(item.score)
          const color = getScoreColor(item.score)
          const theme = buildMoodTheme(color)
          const impact = totalEntries > 0 ? item.count / totalEntries : 0
          const glow = moodGlowForImpact(color, impact)

          return (
            <div key={item.score} className="emotion-stats-bar-col">
              <span className="emotion-stats-count" aria-hidden={item.count === 0}>
                {item.count > 0
                  ? t('emotionStats.countWithPercent', {
                      count: item.count,
                      percent,
                    })
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
            </div>
          )
        })}
      </div>
    </section>
  )
}
