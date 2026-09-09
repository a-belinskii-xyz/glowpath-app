import { useEffect, useState, type CSSProperties } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'

import { deleteMoodEntry, getMoodInsights, patchMoodEntry } from '../api/moodEntries'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { EntryDetailCard } from '../components/EntryDetailCard'
import { EntryReaderPager } from '../components/EntryReaderPager'
import { HeartIcon } from '../components/HeartIcon'
import { IconButton, IconLinkButton } from '../components/IconButton'
import { ChevronLeftIcon, DeleteIcon, EditIcon } from '../components/icons'
import { PatternInsights } from '../components/PatternInsights'
import { useAuth } from '../context/AuthContext'
import { hasAppAccess } from '../lib/authAccess'
import { usePageAmbientGlow } from '../context/AmbientGlowContext'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { useEntryReaderFeed } from '../hooks/useEntryReaderFeed'
import { useMediaQuery } from '../hooks/useMediaQuery'
import { ApiError, formatApiError } from '../lib/errors'
import { entriesListPathForInstant } from '../lib/datetime'
import {
  entryReaderBackHref,
  type EntryReaderLocationState,
} from '../lib/entryReader'
import { entryMoodColor } from '../lib/moodScale'
import type { MoodEntryPublic, MoodInsightsResponse } from '../types/mood'

export function EntryDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuth()
  const { locale, t } = useLocale()
  const { scores } = useMoodPreferences()
  const timeZone = user?.timezone ?? 'UTC'
  const showDesktopControls = useMediaQuery('(hover: hover) and (pointer: fine)')
  const locationState = (location.state as EntryReaderLocationState | null) ?? null
  const from = locationState?.from

  const feed = useEntryReaderFeed(id, timeZone, locale)
  const entry = feed.active
  const [insights, setInsights] = useState<MoodInsightsResponse | null>(null)
  const [isInsightsLoading, setIsInsightsLoading] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [isTogglingFavorite, setIsTogglingFavorite] = useState(false)

  const ambientColors = entry
    ? [
        entryMoodColor(entry, scores),
        ...entry.tags.map((tag) => tag.color),
        ...entry.goals.map((goal) => goal.color),
      ]
    : Object.values(scores).map((style) => style.color)
  usePageAmbientGlow(ambientColors)

  useEffect(() => {
    if (!entry) {
      return
    }
    const backTo = entryReaderBackHref(entry, timeZone, from)
    if (
      location.pathname === `/entries/${entry.id}` &&
      locationState?.backTo === backTo
    ) {
      return
    }
    navigate(`/entries/${entry.id}`, {
      replace: true,
      state: { ...locationState, backTo, from },
    })
  }, [entry, from, location.pathname, locationState, navigate, timeZone])

  useEffect(() => {
    if (!entry?.id || !hasAppAccess(user)) {
      setInsights(null)
      return
    }
    let cancelled = false
    setIsInsightsLoading(true)
    void getMoodInsights({ limit: 1, focus_entry_id: entry.id })
      .then((response) => {
        if (!cancelled) {
          setInsights(response)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setInsights(null)
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsInsightsLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [entry?.id, locale, user])

  const handleDelete = async () => {
    if (!entry) {
      return
    }
    setIsDeleting(true)
    setActionError(null)
    try {
      await deleteMoodEntry(entry.id)
      setConfirmDelete(false)
      const next = feed.removeActive()
      if (next) {
        navigate(`/entries/${next.id}`, {
          replace: true,
          state: {
            ...locationState,
            backTo: entryReaderBackHref(next, timeZone, from),
            from,
          },
        })
      } else {
        navigate(entriesListPathForInstant(entry.recorded_at, timeZone))
      }
    } catch (err) {
      setActionError(formatApiError(err, t, 'errors.failedDeleteEntry'))
    } finally {
      setIsDeleting(false)
    }
  }

  const handleToggleFavorite = async () => {
    if (!entry || isTogglingFavorite) {
      return
    }
    const nextFavorite = !entry.is_favorite
    const previous = entry
    feed.replaceEntry({ ...entry, is_favorite: nextFavorite })
    setIsTogglingFavorite(true)
    setActionError(null)
    try {
      const updated = await patchMoodEntry(entry.id, { is_favorite: nextFavorite })
      feed.replaceEntry(updated)
    } catch (err) {
      feed.replaceEntry(previous)
      setActionError(formatApiError(err, t, 'errors.failedSaveEntry'))
    } finally {
      setIsTogglingFavorite(false)
    }
  }

  const loadError = !entry && !feed.isLoading
    ? feed.error instanceof ApiError && feed.error.status === 403
      ? t('errors.verifyToViewEntry')
      : id
        ? formatApiError(feed.error, t, 'errors.failedLoadEntry')
        : t('errors.entryIdMissing')
    : null
  const error = actionError ?? (confirmDelete ? null : loadError)
  const backHref = entry
    ? entryReaderBackHref(entry, timeZone, from)
    : locationState?.backTo ?? '/'
  const backLabel = from === '/gallery' ? t('gallery.back') : t('common.backToEntries')
  const prevEntry = feed.index > 0 ? feed.items[feed.index - 1] : null
  const nextEntry = feed.index < feed.items.length - 1 ? feed.items[feed.index + 1] : null
  const reachedStart = !prevEntry && !feed.canGoNewer
  const reachedEnd = !nextEntry && !feed.canGoOlder

  const renderSlide = (slide: MoodEntryPublic | null, active: boolean) => {
    if (!slide) {
      return null
    }
    return (
      <div className="entry-reader-slide-body" key={slide.id}>
        <EntryDetailCard entry={slide} timeZone={timeZone}>
          {active && hasAppAccess(user) ? (
            <PatternInsights insights={insights} isLoading={isInsightsLoading} compact />
          ) : null}
        </EntryDetailCard>
      </div>
    )
  }

  return (
    <section className="page page-entry-detail page-entry-reader">
      <EmailVerificationBanner />
      <header className="entry-reader-chrome">
        <IconLinkButton
          label={backLabel}
          to={backHref}
          replace
          variant="ghost"
          className="entry-reader-back"
        >
          <ChevronLeftIcon />
        </IconLinkButton>
        <h1 className="entry-reader-title">{t('entries.moodEntry')}</h1>
        {entry ? (
          <div
            className="entry-detail-header-actions"
            role="toolbar"
            aria-label={t('entryActions.ariaLabel')}
          >
            <IconButton
              label={
                entry.is_favorite ? t('entries.removeFavorite') : t('entries.addFavorite')
              }
              className={entry.is_favorite ? 'is-favorite' : undefined}
              variant="ghost"
              style={
                entry.is_favorite
                  ? ({
                      '--entry-favorite-color': entryMoodColor(entry, scores),
                    } as CSSProperties)
                  : undefined
              }
              onClick={() => void handleToggleFavorite()}
              disabled={isTogglingFavorite}
              aria-pressed={entry.is_favorite}
            >
              <HeartIcon filled={entry.is_favorite} />
            </IconButton>
            <IconLinkButton
              label={t('common.edit')}
              to={`/entries/${entry.id}/edit`}
              variant="ghost"
            >
              <EditIcon />
            </IconLinkButton>
            <IconButton
              label={isDeleting ? t('common.deleting') : t('common.delete')}
              variant="danger"
              disabled={isDeleting}
              onClick={() => setConfirmDelete(true)}
            >
              <DeleteIcon />
            </IconButton>
          </div>
        ) : (
          <span className="entry-reader-chrome-spacer" />
        )}
      </header>

      <PageErrorAlert error={confirmDelete ? null : error} />
      {confirmDelete && entry ? (
        <ConfirmDialog
          open
          title={t('confirm.deleteEntryTitle')}
          message={t('confirm.deleteEntry')}
          confirmLabel={t('common.delete')}
          isBusy={isDeleting}
          error={actionError}
          onCancel={() => {
            if (isDeleting) return
            setConfirmDelete(false)
            setActionError(null)
          }}
          onConfirm={() => void handleDelete()}
        />
      ) : null}

      {feed.isLoading && !entry ? <p className="muted">{t('common.loadingEntry')}</p> : null}

      {entry ? (
        <>
          <p className="visually-hidden">{t('entries.readerHint')}</p>
          <EntryReaderPager
            hasPrev={Boolean(prevEntry)}
            hasNext={Boolean(nextEntry)}
            reachedStart={reachedStart}
            reachedEnd={reachedEnd}
            onPrev={feed.goNewer}
            onNext={feed.goOlder}
            showDesktopControls={showDesktopControls}
            prev={renderSlide(prevEntry, false)}
            current={renderSlide(entry, true)}
            next={renderSlide(nextEntry, false)}
          />
        </>
      ) : null}
    </section>
  )
}
