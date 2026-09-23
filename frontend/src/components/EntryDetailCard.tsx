import type { ReactNode } from 'react'

import { AttachmentAudio } from './AttachmentAudio'
import { EntryAttachmentThumbs } from './EntryAttachmentThumbs'
import { GoalIcon } from './GoalIcon'
import { MarkdownNote } from './MarkdownNote'
import { MoodScoreIcon } from './MoodScoreIcon'
import { TagIcon } from './TagIcon'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { moodChipStyle, moodGlowFilter } from '../design'
import { useColorScheme } from '../hooks/useColorScheme'
import { intlLocale } from '../i18n/t'
import { formatDayHeading, formatTime } from '../lib/datetime'
import { entryMoodColor, entryMoodStyle } from '../lib/moodScale'
import type { MoodEntryPublic } from '../types/mood'

function isSameInstant(left: string, right: string, slackMs = 60_000) {
  return Math.abs(new Date(left).getTime() - new Date(right).getTime()) < slackMs
}

type EntryDetailCardProps = {
  entry: MoodEntryPublic
  timeZone: string
  children?: ReactNode
}

export function EntryDetailCard({ entry, timeZone, children }: EntryDetailCardProps) {
  const { locale, t } = useLocale()
  const { scores } = useMoodPreferences()
  const colorScheme = useColorScheme()
  const dateLocale = intlLocale(locale)
  const audioAttachment = entry.attachments.find((attachment) => attachment.kind === 'audio')
  const showCreated = !isSameInstant(entry.created_at, entry.recorded_at)
  const showUpdated =
    entry.updated_at !== entry.created_at && !isSameInstant(entry.updated_at, entry.recorded_at)

  return (
    <article className="entry-detail">
      <div className="entry-detail-main">
        <div className="entry-detail-block entry-detail-hero">
          <span
            className="entry-detail-emoji-glow"
            style={{
              filter: moodGlowFilter(entryMoodColor(entry, scores)),
            }}
          >
            <MoodScoreIcon
              style={entryMoodStyle(entry, scores)}
              className="entry-detail-emoji"
              fallbackScore={entry.score}
            />
          </span>
          <p className="entry-detail-heading">
            <span className="entry-detail-score">{entry.score_label}</span>
            <span className="muted entry-detail-recorded">
              {' '}
              — {formatDayHeading(entry.recorded_at, timeZone, dateLocale)} ·{' '}
              {formatTime(entry.recorded_at, timeZone, dateLocale)}
            </span>
          </p>
        </div>

        {entry.note || audioAttachment || entry.attachments.some((a) => a.kind === 'photo') ? (
          <div className="entry-detail-block entry-detail-body">
            {entry.note ? (
              <MarkdownNote content={entry.note} className="entry-detail-note" />
            ) : null}

            <EntryAttachmentThumbs
              entryId={entry.id}
              attachments={entry.attachments}
              showAudioCount={false}
              variant="collage"
            />

            {audioAttachment ? (
              <AttachmentAudio
                entryId={entry.id}
                attachment={audioAttachment}
                accentColor={entryMoodColor(entry, scores)}
              />
            ) : null}
          </div>
        ) : null}

        <div className="entry-detail-block entry-detail-footer">
          {entry.tags.length > 0 ? (
            <div className="entry-tags">
              {entry.tags.map((tag) => {
                const chip = moodChipStyle(tag.color, colorScheme)
                return (
                  <span key={tag.id} className="entry-tag" style={chip}>
                    <TagIcon
                      style={{
                        color: chip.color,
                        icon_type: tag.icon_type,
                        icon: tag.icon,
                      }}
                      className="entry-tag-icon"
                    />
                    {tag.label}
                  </span>
                )
              })}
            </div>
          ) : null}

          {entry.goals.length > 0 ? (
            <div className="entry-tags entry-goals">
              {entry.goals.map((goal) => {
                const chip = moodChipStyle(goal.color, colorScheme)
                return (
                  <span key={goal.id} className="entry-tag entry-goal" style={chip}>
                    <GoalIcon
                      style={{
                        color: chip.color,
                        icon_type: goal.icon_type,
                        icon: goal.icon,
                      }}
                      className="entry-goal-icon"
                    />
                    {goal.label}
                  </span>
                )
              })}
            </div>
          ) : null}

          {showCreated || showUpdated ? (
            <p className="muted entry-detail-meta">
              {showCreated
                ? t('entries.createdAt', {
                    date: `${formatDayHeading(entry.created_at, timeZone, dateLocale)} ${formatTime(entry.created_at, timeZone, dateLocale)}`,
                  })
                : null}
              {showCreated && showUpdated ? ' · ' : null}
              {showUpdated
                ? t('entries.updatedAt', {
                    date: `${formatDayHeading(entry.updated_at, timeZone, dateLocale)} ${formatTime(entry.updated_at, timeZone, dateLocale)}`,
                  })
                : null}
            </p>
          ) : null}
        </div>
        {children}
      </div>
    </article>
  )
}
