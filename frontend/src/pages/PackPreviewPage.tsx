import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { listGoals } from '../api/goals'
import { getMarketplacePack } from '../api/marketplace'
import { listTagGroups } from '../api/tagGroups'
import { EntryRow } from '../components/EntryRow'
import { EntryTagsCompact } from '../components/EntryTagsCompact'
import { ChevronLeftIcon } from '../components/icons'
import { MonthCalendar, type CalendarMode } from '../components/MonthCalendar'
import { MoodScoreIcon } from '../components/MoodScoreIcon'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { useLocale } from '../context/LocaleContext'
import { MoodPreferencesOverride, useMoodPreferences } from '../context/MoodPreferencesContext'
import { moodGlowFilter } from '../design'
import { intlLocale } from '../i18n/t'
import { formatDayHeading, formatMonthHeading, formatTime } from '../lib/datetime'
import { formatApiError } from '../lib/errors'
import { buildPreviewData, iconsForUsage, previewMoodScale } from '../lib/packPreview'
import type { PackDetailPublic } from '../types/marketplace'
import type { GoalPublic } from '../types/goal'
import type { MoodEntryGoal, MoodEntryTag } from '../types/mood'

/** Mock data is laid out in UTC so days never shift with the viewer's time zone. */
const PREVIEW_TIME_ZONE = 'UTC'
const SCORES = [1, 2, 3, 4, 5]

const noop = () => undefined

export function PackPreviewPage() {
  const { packId } = useParams<{ packId: string }>()
  const navigate = useNavigate()
  const { t, locale } = useLocale()
  const { scores: ownScale } = useMoodPreferences()
  const [pack, setPack] = useState<PackDetailPublic | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<CalendarMode>('moods')
  const [ownTags, setOwnTags] = useState<MoodEntryTag[]>([])
  const [ownGoals, setOwnGoals] = useState<GoalPublic[]>([])
  const dateLocale = intlLocale(locale)

  useEffect(() => {
    if (!packId) return
    let cancelled = false
    getMarketplacePack(packId)
      .then((detail) => {
        if (!cancelled) setPack(detail)
      })
      .catch((err) => {
        if (!cancelled) setError(formatApiError(err, t, 'packPreview.loadFailed'))
      })
    return () => {
      cancelled = true
    }
  }, [packId, t])

  // Fallback for packs without tag / goal icons; the preview still works without them.
  useEffect(() => {
    let cancelled = false
    listTagGroups()
      .then((response) => {
        if (cancelled) return
        setOwnTags(
          response.items.filter((group) => group.show_on_entry).flatMap((group) => group.tags),
        )
      })
      .catch(() => undefined)
    listGoals()
      .then((response) => {
        if (!cancelled) setOwnGoals(response.items.filter((goal) => goal.show_on_entry))
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [])

  const icons = useMemo(() => pack?.icons ?? [], [pack])
  const scale = useMemo(() => previewMoodScale(icons, ownScale), [icons, ownScale])
  const data = useMemo(
    () =>
      buildPreviewData({
        icons,
        scale,
        tagLabels: t('packPreview.tags').split('|'),
        goalLabels: t('packPreview.goals').split('|'),
        notes: t('packPreview.notes').split('|'),
        ownTags,
        ownGoals,
      }),
    [icons, scale, t, ownTags, ownGoals],
  )
  const goalsById = useMemo(() => new Map(data.goals.map((goal) => [goal.id, goal])), [data])
  const entryGoals: MoodEntryGoal[] = useMemo(
    () =>
      data.goals.map((goal) => ({
        id: goal.id,
        slug: goal.slug,
        label: goal.label,
        color: goal.color,
        icon_type: goal.icon_type,
        icon: goal.icon,
      })),
    [data],
  )
  const entriesByDay = useMemo(() => {
    const groups = new Map<string, typeof data.entries>()
    for (const entry of data.entries) {
      const key = entry.recorded_at.slice(0, 10)
      groups.set(key, [...(groups.get(key) ?? []), entry])
    }
    return [...groups.values()]
  }, [data])

  const back = () => {
    if (window.history.length > 1) navigate(-1)
    else navigate('/market')
  }

  const hasHints = icons.some((icon) => icon.suggested_usage.length > 0)
  const noMoodIcons = icons.length > 0 && iconsForUsage(icons, 'mood').length === 0
  const noTagIcons = iconsForUsage(icons, 'tag').length === 0
  const noGoalIcons = iconsForUsage(icons, 'goal').length === 0

  return (
    <section className="page page-pack-preview">
      <button type="button" className="settings-back-link" onClick={back}>
        <ChevronLeftIcon aria-hidden="true" />
        {t('packPreview.back')}
      </button>
      <PageErrorAlert error={error} />
      {pack ? (
        <MoodPreferencesOverride scores={scale}>
          <header className="pack-preview-header">
            <h1>{t('packPreview.title', { name: pack.name })}</h1>
            <p className="muted">{t('packPreview.lead')}</p>
            {hasHints ? null : <p className="form-hint">{t('packPreview.noHints')}</p>}
          </header>

          <div className="card pack-preview-card">
            <h2 className="pack-preview-subtitle">{t('packPreview.moodScale')}</h2>
            {noMoodIcons ? <p className="form-hint">{t('packPreview.notForMoods')}</p> : null}
            <ul className="pack-preview-scale">
              {SCORES.map((score) => {
                const style = scale[String(score)]
                return (
                  <li key={score} className="pack-preview-scale-item">
                    <span style={{ filter: moodGlowFilter(style.color) }}>
                      <MoodScoreIcon style={style} className="pack-preview-scale-icon" />
                    </span>
                    <span className="pack-preview-scale-label">{style.label}</span>
                  </li>
                )
              })}
            </ul>

            <h2 className="pack-preview-subtitle">{t('packPreview.tagsTitle')}</h2>
            {noTagIcons ? <p className="form-hint">{t('packPreview.notForTags')}</p> : null}
            <EntryTagsCompact tags={data.tags} />

            <h2 className="pack-preview-subtitle">{t('packPreview.goalsTitle')}</h2>
            {noGoalIcons ? <p className="form-hint">{t('packPreview.notForGoals')}</p> : null}
            <EntryTagsCompact goals={entryGoals} />
          </div>

          <div className="calendar-panel">
            <h2 className="pack-preview-subtitle">
              {t('packPreview.calendarTitle')} ·{' '}
              {formatMonthHeading(data.year, data.month, dateLocale)}
            </h2>
            <div
              className="segmented-control calendar-mode-tabs"
              role="group"
              aria-label={t('calendar.modeGroup')}
            >
              {(['moods', 'goals'] as const).map((value) => (
                <button
                  key={value}
                  type="button"
                  className={`segmented-control-option${mode === value ? ' is-active' : ''}`}
                  aria-pressed={mode === value}
                  onClick={() => setMode(value)}
                >
                  {value === 'moods' ? t('calendar.modeMoods') : t('calendar.modeGoals')}
                </button>
              ))}
            </div>
            <MonthCalendar
              year={data.year}
              month={data.month}
              timeZone={PREVIEW_TIME_ZONE}
              mode={mode}
              moodDays={data.moodDays}
              goalDays={data.goalDays}
              goalsById={goalsById}
              onDayWithEntries={noop}
              readOnly
            />
          </div>

          <h2 className="pack-preview-subtitle">{t('packPreview.entriesTitle')}</h2>
          <div className="entry-feed">
            {entriesByDay.map((dayEntries) => (
              <section
                key={dayEntries[0].id}
                className="day-section"
                style={{ '--entry-mood-color': dayEntries[0].score_color } as CSSProperties}
              >
                <h3 className="day-heading">
                  {formatDayHeading(dayEntries[0].recorded_at, PREVIEW_TIME_ZONE, dateLocale)}
                </h3>
                <ul className="entry-list">
                  {dayEntries.map((entry) => (
                    <li key={entry.id}>
                      <EntryRow
                        entry={entry}
                        timeLabel={formatTime(entry.recorded_at, PREVIEW_TIME_ZONE, dateLocale)}
                        timeZone={PREVIEW_TIME_ZONE}
                        onDelete={noop}
                        onToggleFavorite={noop}
                        preview
                      />
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        </MoodPreferencesOverride>
      ) : error ? null : (
        <p className="muted">{t('common.loadingMarket')}</p>
      )}
    </section>
  )
}
