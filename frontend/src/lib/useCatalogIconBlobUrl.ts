import { useEffect, useState } from 'react'

import {
  getCachedCatalogIconObjectUrl,
  getCatalogIconObjectUrl,
  subscribeCatalogIcon,
} from './catalogIconBlobUrl'

export function useCatalogIconBlobUrl(iconId: string | null): string | null {
  const [url, setUrl] = useState<string | null>(() =>
    iconId ? getCachedCatalogIconObjectUrl(iconId) : null,
  )
  const [version, setVersion] = useState(0)

  useEffect(() => {
    if (!iconId) return undefined
    return subscribeCatalogIcon(iconId, () => setVersion((current) => current + 1))
  }, [iconId])

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
  }, [iconId, version])

  return url
}
