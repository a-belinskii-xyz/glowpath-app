import { useEffect, useState } from 'react'

import { getBuiltinMoodIconPath } from '../lib/moodBuiltinIcons'
import { getCachedMoodIconObjectUrl, getMoodIconObjectUrl } from '../lib/moodIconBlobUrl'
import { useCatalogIconBlobUrl } from '../lib/useCatalogIconBlobUrl'
import type { MoodScoreStylePublic } from '../types/moodPreferences'

type MoodScoreIconProps = {
  style: MoodScoreStylePublic
  className?: string
  fallbackScore?: number
}

function useMoodIconBlobUrl(iconId: string | null): string | null {
  const [url, setUrl] = useState<string | null>(() =>
    iconId ? getCachedMoodIconObjectUrl(iconId) : null,
  )

  useEffect(() => {
    if (!iconId) {
      setUrl(null)
      return
    }

    const cached = getCachedMoodIconObjectUrl(iconId)
    if (cached) {
      setUrl(cached)
      return
    }

    let cancelled = false
    void getMoodIconObjectUrl(iconId)
      .then((objectUrl) => {
        if (!cancelled) {
          setUrl(objectUrl)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setUrl(null)
        }
      })

    return () => {
      cancelled = true
    }
  }, [iconId])

  return url
}

export function MoodScoreIcon({ style, className }: MoodScoreIconProps) {
  const uploadUrl = useMoodIconBlobUrl(style.icon_type === 'upload' ? style.icon : null)
  const catalogUrl = useCatalogIconBlobUrl(style.icon_type === 'catalog' ? style.icon : null)

  if (style.icon_type === 'builtin') {
    return (
      <span className={className} aria-hidden>
        <img
          src={getBuiltinMoodIconPath(style.icon)}
          alt=""
          loading="eager"
          decoding="async"
          draggable={false}
        />
      </span>
    )
  }

  if (style.icon_type === 'upload') {
    const uploadClassName = [className, 'mood-score-icon-upload'].filter(Boolean).join(' ')
    if (!uploadUrl) {
      return (
        <span className={uploadClassName} aria-hidden>
          <span className="mood-score-icon-placeholder" />
        </span>
      )
    }
    return (
      <span className={uploadClassName} aria-hidden>
        <img src={uploadUrl} alt="" loading="eager" decoding="async" draggable={false} />
      </span>
    )
  }

  if (style.icon_type === 'catalog') {
    const catalogClassName = [className, 'mood-score-icon-upload'].filter(Boolean).join(' ')
    if (!catalogUrl) {
      return (
        <span className={catalogClassName} aria-hidden>
          <span className="mood-score-icon-placeholder" />
        </span>
      )
    }
    return (
      <span className={catalogClassName} aria-hidden>
        <img src={catalogUrl} alt="" loading="eager" decoding="async" draggable={false} />
      </span>
    )
  }

  return <span className={className}>{style.icon}</span>
}
