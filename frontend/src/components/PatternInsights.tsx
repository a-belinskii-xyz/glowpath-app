import { moodSubtleFill } from '../design'
import { useLocale } from '../context/LocaleContext'
import type { MoodInsightPublic, MoodInsightsResponse } from '../types/mood'
import { TagIcon } from './TagIcon'

type PatternInsightsProps = {
  insights: MoodInsightsResponse | null
  isLoading: boolean
  highlightId?: string | null
  /** Single related card (entry detail). */
  compact?: boolean
}

export function PatternInsights({
  insights,
  isLoading,
  highlightId = null,
  compact = false,
}: PatternInsightsProps) {
  const { t } = useLocale()

  if (isLoading && !insights) {
    return <p className="muted">{t('common.loadingInsights')}</p>
  }

  if (!insights) {
    return null
  }

  const items = compact ? insights.items.slice(0, 1) : insights.items
  if (items.length === 0) {
    if (compact || insights.active_days < 8) {
      return null
    }
    return (
      <section className="pattern-insights" aria-label={t('patternInsights.ariaLabel')}>
        <div className="pattern-insights-header">
          <h2 className="pattern-insights-title">{t('patternInsights.title')}</h2>
        </div>
        <p className="muted pattern-insights-empty">{t('patternInsights.empty')}</p>
      </section>
    )
  }

  return (
    <section
      className={`pattern-insights${compact ? ' is-compact' : ''}`}
      aria-label={compact ? t('patternInsights.relatedAria') : t('patternInsights.ariaLabel')}
    >
      <div className="pattern-insights-header">
        <h2 className="pattern-insights-title">
          {compact ? t('patternInsights.relatedTitle') : t('patternInsights.title')}
        </h2>
      </div>
      <ul className="pattern-insights-list">
        {items.map((item) => (
          <li key={item.id}>
            <PatternInsightCard item={item} highlight={item.id === highlightId} />
          </li>
        ))}
      </ul>
    </section>
  )
}

function PatternInsightCard({
  item,
  highlight,
}: {
  item: MoodInsightPublic
  highlight: boolean
}) {
  const tag = item.subjects.find((subject) => subject.type === 'tag' && subject.color)
  const accent = tag?.color ?? null

  return (
    <article
      className={`pattern-insight-card is-${item.direction}${highlight ? ' is-fresh' : ''}${
        item.strength === 'strong' ? ' is-strong' : ''
      }`}
      style={accent ? { ['--pattern-accent' as string]: accent } : undefined}
    >
      {tag?.color && tag.icon_type && tag.icon ? (
        <span
          className="pattern-insight-tag"
          style={{
            background: moodSubtleFill(tag.color),
            color: tag.color,
          }}
        >
          <TagIcon
            style={{
              color: tag.color,
              icon_type: tag.icon_type,
              icon: tag.icon,
            }}
            className="pattern-insight-tag-icon"
          />
          {tag.label}
        </span>
      ) : null}
      <h3 className="pattern-insight-title">{item.title}</h3>
      <p className="pattern-insight-body">{item.body}</p>
      <p className="muted pattern-insight-sample">{item.sample}</p>
    </article>
  )
}
