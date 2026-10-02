import { fetchCatalogIconBlob } from '../api/marketplace'
import type { IconCrop } from '../types/marketplace'
import { loadImageElement } from './imageCrop'

/** Longest side of a cropped icon; vector icons are rasterized at this size. */
const CROPPED_ICON_MAX_SIDE = 512

const blobUrlCache = new Map<string, string>()
const blobUrlInflight = new Map<string, Promise<string>>()
const listeners = new Map<string, Set<() => void>>()

/**
 * Cut the crop frame out of the original file. Staff keep the full image on the
 * server, so every client crops the same way. Falls back to the original when
 * the browser cannot rasterize it (e.g. an SVG without intrinsic size).
 */
async function cropIconBlob(blob: Blob, crop: IconCrop): Promise<Blob> {
  const sourceUrl = URL.createObjectURL(blob)
  try {
    const image = await loadImageElement(sourceUrl)
    const { naturalWidth: width, naturalHeight: height } = image
    if (width < 1 || height < 1) return blob

    const sx = crop.x * width
    const sy = crop.y * height
    const sw = crop.w * width
    const sh = crop.h * height
    const isVector = blob.type === 'image/svg+xml'
    const longest = Math.max(sw, sh)
    const scale = isVector ? CROPPED_ICON_MAX_SIDE / longest : Math.min(1, CROPPED_ICON_MAX_SIDE / longest)

    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(sw * scale))
    canvas.height = Math.max(1, Math.round(sh * scale))
    const ctx = canvas.getContext('2d')
    if (!ctx) return blob
    ctx.imageSmoothingEnabled = true
    ctx.imageSmoothingQuality = 'high'
    ctx.drawImage(image, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height)

    const cropped = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/png'))
    return cropped ?? blob
  } catch {
    return blob
  } finally {
    URL.revokeObjectURL(sourceUrl)
  }
}

export function getCachedCatalogIconObjectUrl(iconId: string): string | null {
  return blobUrlCache.get(iconId) ?? null
}

/** Object URL of the icon as users see it (crop frame applied). */
export async function getCatalogIconObjectUrl(iconId: string): Promise<string> {
  const cached = blobUrlCache.get(iconId)
  if (cached) {
    return cached
  }

  const inflight = blobUrlInflight.get(iconId)
  if (inflight) {
    return inflight
  }

  const request = fetchCatalogIconBlob(iconId)
    .then(async ({ blob, crop }) => {
      const visible = crop ? await cropIconBlob(blob, crop) : blob
      const objectUrl = URL.createObjectURL(visible)
      blobUrlCache.set(iconId, objectUrl)
      blobUrlInflight.delete(iconId)
      return objectUrl
    })
    .catch((error) => {
      blobUrlInflight.delete(iconId)
      throw error
    })

  blobUrlInflight.set(iconId, request)
  return request
}

export function revokeCatalogIconObjectUrl(iconId: string): void {
  const cached = blobUrlCache.get(iconId)
  if (cached) {
    URL.revokeObjectURL(cached)
    blobUrlCache.delete(iconId)
  }
}

/** Drop the cached image after its file or crop changed, and let mounted icons reload. */
export function invalidateCatalogIcon(iconId: string): void {
  revokeCatalogIconObjectUrl(iconId)
  listeners.get(iconId)?.forEach((listener) => listener())
}

export function subscribeCatalogIcon(iconId: string, listener: () => void): () => void {
  const set = listeners.get(iconId) ?? new Set()
  set.add(listener)
  listeners.set(iconId, set)
  return () => {
    set.delete(listener)
    if (set.size === 0) listeners.delete(iconId)
  }
}
