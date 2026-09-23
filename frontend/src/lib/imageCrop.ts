export const MOOD_ICON_OUTPUT_SIZE = 256
export const MOOD_ICON_MAX_BYTES = 512 * 1024
/** Max size of the source file chosen for cropping (cropped result must still fit upload limit). */
export const MOOD_ICON_SOURCE_MAX_BYTES = 20 * 1024 * 1024
export const MOOD_ICON_MIN_DIMENSION = 256
export const MOOD_ICON_MAX_ZOOM = 5
export const MOOD_ICON_ALLOWED_MIME_TYPES = [
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/gif',
] as const

export type MoodIconAllowedMimeType = (typeof MOOD_ICON_ALLOWED_MIME_TYPES)[number]

export type CropShape = 'circle' | 'square'

export type CropTransform = {
  zoom: number
  offsetX: number
  offsetY: number
}

export type CropValidationError = 'type' | 'size' | 'tooSmall' | 'loadFailed'

export function isAllowedMoodIconMimeType(mimeType: string): mimeType is MoodIconAllowedMimeType {
  return (MOOD_ICON_ALLOWED_MIME_TYPES as readonly string[]).includes(mimeType)
}

export function validateMoodIconSourceFile(file: File): CropValidationError | null {
  if (!isAllowedMoodIconMimeType(file.type)) {
    return 'type'
  }
  if (file.size > MOOD_ICON_SOURCE_MAX_BYTES) {
    return 'size'
  }
  return null
}

export function getCoverScale(imageWidth: number, imageHeight: number, cropSize: number): number {
  return cropSize / Math.min(imageWidth, imageHeight)
}

export function getDisplayedSize(
  imageWidth: number,
  imageHeight: number,
  cropSize: number,
  zoom: number,
): { width: number; height: number } {
  const scale = getCoverScale(imageWidth, imageHeight, cropSize) * zoom
  return {
    width: imageWidth * scale,
    height: imageHeight * scale,
  }
}

export function clampCropOffset(
  offsetX: number,
  offsetY: number,
  displayedWidth: number,
  displayedHeight: number,
  cropSize: number,
): { offsetX: number; offsetY: number } {
  const minX = cropSize - displayedWidth
  const minY = cropSize - displayedHeight
  return {
    offsetX: Math.min(0, Math.max(minX, offsetX)),
    offsetY: Math.min(0, Math.max(minY, offsetY)),
  }
}

export function getCenteredCropOffset(
  displayedWidth: number,
  displayedHeight: number,
  cropSize: number,
): { offsetX: number; offsetY: number } {
  return clampCropOffset(
    (cropSize - displayedWidth) / 2,
    (cropSize - displayedHeight) / 2,
    displayedWidth,
    displayedHeight,
    cropSize,
  )
}

export function clampZoom(zoom: number, maxZoom = MOOD_ICON_MAX_ZOOM): number {
  return Math.min(maxZoom, Math.max(1, zoom))
}

/** Keep the crop-frame center fixed on the same image point while zooming. */
export function zoomCropTransform(
  transform: CropTransform,
  nextZoom: number,
  imageWidth: number,
  imageHeight: number,
  cropSize: number,
  maxZoom = MOOD_ICON_MAX_ZOOM,
): CropTransform {
  const zoom = clampZoom(nextZoom, maxZoom)
  if (zoom === transform.zoom) {
    return transform
  }

  const ratio = zoom / transform.zoom
  const center = cropSize / 2
  const offsetX = center - (center - transform.offsetX) * ratio
  const offsetY = center - (center - transform.offsetY) * ratio
  const { width, height } = getDisplayedSize(imageWidth, imageHeight, cropSize, zoom)

  return {
    zoom,
    ...clampCropOffset(offsetX, offsetY, width, height, cropSize),
  }
}

export function createInitialCropTransform(
  imageWidth: number,
  imageHeight: number,
  cropSize: number,
): CropTransform {
  const zoom = 1
  const { width, height } = getDisplayedSize(imageWidth, imageHeight, cropSize, zoom)
  return {
    zoom,
    ...getCenteredCropOffset(width, height, cropSize),
  }
}

export function loadImageElement(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('Failed to load image'))
    image.src = src
  })
}

export async function readMoodIconImage(
  file: File,
): Promise<{ image: HTMLImageElement; objectUrl: string } | { error: CropValidationError }> {
  const fileError = validateMoodIconSourceFile(file)
  if (fileError) {
    return { error: fileError }
  }

  const objectUrl = URL.createObjectURL(file)
  try {
    const image = await loadImageElement(objectUrl)
    if (
      image.naturalWidth < MOOD_ICON_MIN_DIMENSION ||
      image.naturalHeight < MOOD_ICON_MIN_DIMENSION
    ) {
      URL.revokeObjectURL(objectUrl)
      return { error: 'tooSmall' }
    }
    return { image, objectUrl }
  } catch {
    URL.revokeObjectURL(objectUrl)
    return { error: 'loadFailed' }
  }
}

/** Load an already-stored icon for re-cropping (skips source file size / min-resolution checks). */
export async function readMoodIconBlobForCrop(
  blob: Blob,
): Promise<{ image: HTMLImageElement; objectUrl: string } | { error: CropValidationError }> {
  if (blob.size === 0) {
    return { error: 'loadFailed' }
  }
  const objectUrl = URL.createObjectURL(blob)
  try {
    const image = await loadImageElement(objectUrl)
    if (image.naturalWidth < 1 || image.naturalHeight < 1) {
      URL.revokeObjectURL(objectUrl)
      return { error: 'loadFailed' }
    }
    return { image, objectUrl }
  } catch {
    URL.revokeObjectURL(objectUrl)
    return { error: 'loadFailed' }
  }
}

export function blobToNamedFile(blob: Blob, fileName: string): File {
  const type = blob.type || 'application/octet-stream'
  return new File([blob], fileName, { type })
}

function extensionForMime(mimeType: string): string {
  if (mimeType === 'image/jpeg') {
    return 'jpg'
  }
  if (mimeType === 'image/webp') {
    return 'webp'
  }
  return 'png'
}

function replaceFileExtension(fileName: string, extension: string): string {
  const base = fileName.replace(/\.[^.]+$/, '') || 'icon'
  return `${base}.${extension}`
}

export async function exportCroppedImage(options: {
  image: HTMLImageElement
  transform: CropTransform
  cropSize: number
  outputSize?: number
  shape?: CropShape
  fileName: string
}): Promise<File> {
  const {
    image,
    transform,
    cropSize,
    outputSize = MOOD_ICON_OUTPUT_SIZE,
    shape = 'circle',
    fileName,
  } = options

  const canvas = document.createElement('canvas')
  canvas.width = outputSize
  canvas.height = outputSize
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    throw new Error('Canvas is not available')
  }

  ctx.imageSmoothingEnabled = true
  ctx.imageSmoothingQuality = 'high'

  if (shape === 'circle') {
    ctx.beginPath()
    ctx.arc(outputSize / 2, outputSize / 2, outputSize / 2, 0, Math.PI * 2)
    ctx.closePath()
    ctx.clip()
  }

  const scale = getCoverScale(image.naturalWidth, image.naturalHeight, cropSize) * transform.zoom
  const sx = -transform.offsetX / scale
  const sy = -transform.offsetY / scale
  const sourceSize = cropSize / scale

  ctx.drawImage(image, sx, sy, sourceSize, sourceSize, 0, 0, outputSize, outputSize)

  const mimeType = shape === 'circle' ? 'image/png' : 'image/jpeg'
  const quality = mimeType === 'image/jpeg' ? 0.92 : undefined

  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (result) => {
        if (result) {
          resolve(result)
        } else {
          reject(new Error('Failed to encode cropped image'))
        }
      },
      mimeType,
      quality,
    )
  })

  return new File([blob], replaceFileExtension(fileName, extensionForMime(mimeType)), {
    type: mimeType,
    lastModified: Date.now(),
  })
}

export function assertMoodIconUploadSize(file: File): void {
  if (file.size > MOOD_ICON_MAX_BYTES) {
    throw new Error('Cropped icon exceeds the 512 KB upload limit')
  }
}
