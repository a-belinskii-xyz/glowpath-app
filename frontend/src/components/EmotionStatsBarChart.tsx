import type { MoodEntryStatsResponse, MoodMonthComparisonPublic } from '../types/mood'

type EmotionStatsBarChartProps = {
  stats: MoodEntryStatsResponse
}

const BAR_COLORS: Record<number, string> = {
  1: '#64748b',
  2: '#94a3b8',
  3: '#60a5fa',
  4: '#34d399',
  5: '#f59e0b',
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
  const { scores, total_entries: totalEntries, month_index: monthIndex, comparison } = stats
  const maxCount = Math.max(1, ...scores.map((item) => item.count))
  const currentLabel = formatIndex(comparison.current_index ?? monthIndex)
  const previousLabel = formatIndex(comparison.previous_index)

  return (
    <section className="emotion-stats" aria-label="Emotion statistics for this month">
      <div className="emotion-stats-header">
        <h2 className="emotion-stats-title">Emotions this month</h2>
        <p className="emotion-stats-summary muted">
          {totalEntries === 0
            ? 'No entries yet'
            : `${totalEntries} entr${totalEntries === 1 ? 'y' : 'ies'}`}
        </p>
      </div>

      <p className={comparisonClassName(comparison.verdict)}>{comparison.message}</p>
      {currentLabel && previousLabel && comparison.verdict !== 'insufficient_data' ? (
        <p className="emotion-stats-indexes muted">
          Month index {currentLabel} vs {previousLabel} last month
          {comparison.delta !== null
            ? ` (${comparison.delta > 0 ? '+' : ''}${comparison.delta.toFixed(2)})`
            : null}
        </p>
      ) : null}

      <div className="emotion-stats-chart" role="img" aria-label="Bar chart of emotion counts">
        {scores.map((item) => {
          const heightPercent = totalEntries === 0 ? 0 : (item.count / maxCount) * 100
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
                    backgroundColor: BAR_COLORS[item.score] ?? '#94a3b8',
                  }}
                  title={`${item.score_emoji} ${item.score_label}: ${item.count}`}
                />
              </div>
              <span className="emotion-stats-emoji" aria-hidden>
                {item.score_emoji}
              </span>
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
