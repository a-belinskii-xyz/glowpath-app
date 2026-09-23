import { useEffect, useState } from 'react'

import {
  getCachedCatalogIconObjectUrl,
  getCatalogIconObjectUrl,
} from './catalogIconBlobUrl'

export function useCatalogIconBlobUrl(iconId: string | null): string | null {
  const [url, setUrl] = useState<string | null>(() =>
    iconId ? getCachedCatalogIconObjectUrl(iconId) : null,
  )

  useEffect(() => {
    if (!iconId) {
      setUrl(null)
      return
    }

    const cached = getCachedCatalogIconObjectUrl(iconId)
    if (cached) {
      setUrl(cached)
      return
    }

    let cancelled = false
    void getCatalogIconObjectUrl(iconId)
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
