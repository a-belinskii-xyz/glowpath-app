import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'

import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { moodGlowFilter } from '../design'
import { entriesListPathForInstant } from '../lib/datetime'
import { entryMoodColor, entryMoodStyle } from '../lib/moodScale'
import type { MoodEntryPublic } from '../types/mood'
import { EntryActionMenu } from './EntryActionMenu'
import { EntryAttachmentThumbs } from './EntryAttachmentThumbs'
import { EntryTagsCompact } from './EntryTagsCompact'
import { HeartIcon } from './HeartIcon'
import { MarkdownNote } from './MarkdownNote'
import { MoodScoreIcon } from './MoodScoreIcon'

type EntryRowProps = {
  entry: MoodEntryPublic
  timeLabel: string
  timeZone: string
  onDelete: (entryId: string) => void | Promise<void>
  onToggleFavorite: (entryId: string, isFavorite: boolean) => void
  /** Static row for mock entries (pack preview): no links, menus or attachment loads. */
  preview?: boolean
}

function isCompactEntry(entry: MoodEntryPublic): boolean {
  return (
    !entry.note?.trim() &&
    (entry.tags?.length ?? 0) === 0 &&
    (entry.goals?.length ?? 0) === 0 &&
    (entry.attachments?.length ?? 0) === 0
  )
}

export function EntryRow({
  entry,
  timeLabel,
  timeZone,
  onDelete,
  onToggleFavorite,
  preview = false,
}: EntryRowProps) {
  const { t } = useLocale()
  const { scores } = useMoodPreferences()
  const compact = isCompactEntry(entry)
  const moodColor = entryMoodColor(entry, scores)
  const moodStyle = entryMoodStyle(entry, scores)

  const body = (
    <>
      <div className="entry-row-main">
        <span className="entry-score">
          <span className="entry-score-badge">
            <span style={{ filter: moodGlowFilter(moodColor) }}>
              <MoodScoreIcon
                style={moodStyle}
                className="entry-score-icon"
                fallbackScore={entry.score}
              />
            </span>
            <span className="entry-score-label">{entry.score_label}</span>
          </span>
        </span>
        <div className="entry-row-meta">
          <span className="entry-time">{timeLabel}</span>
          {preview ? null : (
            <button
              type="button"
              className={`entry-favorite-mark${entry.is_favorite ? ' is-favorite' : ''}`}
              style={
                entry.is_favorite
                  ? ({ '--entry-favorite-color': moodColor } as CSSProperties)
                  : undefined
              }
              aria-pressed={entry.is_favorite}
              aria-label={
                entry.is_favorite ? t('entries.removeFavorite') : t('entries.addFavorite')
              }
              title={entry.is_favorite ? t('entries.removeFavorite') : t('entries.addFavorite')}
              onClick={(event) => {
                event.preventDefault()
                event.stopPropagation()
                void onToggleFavorite(entry.id, !entry.is_favorite)
              }}
            >
              <HeartIcon filled={entry.is_favorite} />
            </button>
          )}
        </div>
      </div>
      {!compact && entry.note?.trim() ? (
        <MarkdownNote content={entry.note} compact className="entry-note" />
      ) : null}
      {!compact ? <EntryTagsCompact tags={entry.tags} goals={entry.goals} /> : null}
    </>
  )

  return (
    <article
      className={`entry-row${compact ? ' is-compact' : ''}`}
      style={{ '--entry-mood-color': moodColor } as CSSProperties}
    >
      {preview ? (
        <div className="entry-row-link">{body}</div>
      ) : (
        <Link
          className="entry-row-link"
          to={`/entries/${entry.id}`}
          state={{ backTo: entriesListPathForInstant(entry.recorded_at, timeZone, entry.id) }}
        >
          {body}
        </Link>
      )}
      {!compact && !preview ? (
        <div className="entry-row-media">
          <EntryAttachmentThumbs entryId={entry.id} attachments={entry.attachments} />
        </div>
      ) : null}
      {preview ? null : (
        <div className="entry-row-actions">
          <EntryActionMenu
            entry={entry}
            onDelete={onDelete}
            onToggleFavorite={onToggleFavorite}
          />
        </div>
      )}
    </article>
  )
}
