import {
  type FormEvent,
  type ReactNode,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
  type TouchEvent as ReactTouchEvent,
  type WheelEvent as ReactWheelEvent,
  useEffect,
  useId,
  useRef,
  useState,
} from 'react'
import { createPortal } from 'react-dom'

import { useLocale } from '../context/LocaleContext'
import type { IconCrop } from '../types/marketplace'
import {
  clampCropOffset,
  createInitialCropTransform,
  exportCroppedImage,
  assertMoodIconUploadSize,
  getDisplayedSize,
  MOOD_ICON_MAX_ZOOM,
  type CropShape,
  type CropTransform,
  cropRegionFromTransform,
  transformFromCropRegion,
  zoomCropTransform,
} from '../lib/imageCrop'
import { StableButtonLabel } from './StableButtonLabel'

const DEFAULT_CROP_SIZE = 280
const PREVIEW_SIZE = 96
const KEYBOARD_PAN_STEP = 8
const KEYBOARD_ZOOM_STEP = 0.1

type ImageCropModalProps = {
  image: HTMLImageElement
  imageUrl: string
  fileName: string
  shape?: CropShape
  cropSize?: number
  isSaving?: boolean
  onCancel: () => void
  /** Region mode: start from this frame and hand back fractions instead of a cropped file. */
  initialRegion?: IconCrop | null
  onSaveRegion?: (region: IconCrop) => void | Promise<void>
  onSave?: (file: File) => void | Promise<void>
  /** Optional extra action next to Cancel (e.g. drop a saved crop frame). */
  resetLabel?: string
  onReset?: () => void
  /** Header text instead of the default crop title and hint. */
  title?: string
  hint?: string
  /** Extra form fields under the crop area; submitted with the crop. */
  children?: ReactNode
}

type DragState = {
  pointerId: number
  startX: number
  startY: number
  originOffsetX: number
  originOffsetY: number
}

type PinchState = {
  startDistance: number
  startZoom: number
}

function touchDistance(
  a: { clientX: number; clientY: number },
  b: { clientX: number; clientY: number },
): number {
  const dx = a.clientX - b.clientX
  const dy = a.clientY - b.clientY
  return Math.hypot(dx, dy)
}

export function ImageCropModal({
  image,
  imageUrl,
  fileName,
  shape = 'circle',
  cropSize = DEFAULT_CROP_SIZE,
  isSaving = false,
  onCancel,
  initialRegion,
  onSaveRegion,
  onSave,
  resetLabel,
  onReset,
  title,
  hint,
  children,
}: ImageCropModalProps) {
  const { t } = useLocale()
  const titleId = useId()
  const viewportRef = useRef<HTMLDivElement>(null)
  const previewRef = useRef<HTMLCanvasElement>(null)
  const dragRef = useRef<DragState | null>(null)
  const pinchRef = useRef<PinchState | null>(null)
  const transformRef = useRef<CropTransform>(
    initialRegion
      ? transformFromCropRegion(initialRegion, image.naturalWidth, image.naturalHeight, cropSize)
      : createInitialCropTransform(image.naturalWidth, image.naturalHeight, cropSize),
  )

  const [transform, setTransform] = useState<CropTransform>(() => transformRef.current)
  const [isExporting, setIsExporting] = useState(false)

  const busy = isSaving || isExporting
  const displayed = getDisplayedSize(
    image.naturalWidth,
    image.naturalHeight,
    cropSize,
    transform.zoom,
  )

  const updateTransform = (next: CropTransform) => {
    transformRef.current = next
    setTransform(next)
  }

  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !busy) {
        event.preventDefault()
        event.stopImmediatePropagation()
        onCancel()
      }
    }

    document.addEventListener('keydown', handleKey, true)
    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', handleKey, true)
    }
  }, [busy, onCancel])

  useEffect(() => {
    const canvas = previewRef.current
    if (!canvas) {
      return
    }
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      return
    }

    const outputSize = PREVIEW_SIZE
    canvas.width = outputSize
    canvas.height = outputSize
    ctx.clearRect(0, 0, outputSize, outputSize)
    ctx.imageSmoothingEnabled = true
    ctx.imageSmoothingQuality = 'high'

    if (shape === 'circle') {
      ctx.beginPath()
      ctx.arc(outputSize / 2, outputSize / 2, outputSize / 2, 0, Math.PI * 2)
      ctx.closePath()
      ctx.clip()
    }

    const scale =
      (cropSize / Math.min(image.naturalWidth, image.naturalHeight)) * transform.zoom
    const sx = -transform.offsetX / scale
    const sy = -transform.offsetY / scale
    const sourceSize = cropSize / scale
    ctx.drawImage(image, sx, sy, sourceSize, sourceSize, 0, 0, outputSize, outputSize)
  }, [cropSize, image, shape, transform])

  const applyPan = (clientX: number, clientY: number, drag: DragState) => {
    const dx = clientX - drag.startX
    const dy = clientY - drag.startY
    const { width, height } = getDisplayedSize(
      image.naturalWidth,
      image.naturalHeight,
      cropSize,
      transformRef.current.zoom,
    )
    updateTransform({
      zoom: transformRef.current.zoom,
      ...clampCropOffset(
        drag.originOffsetX + dx,
        drag.originOffsetY + dy,
        width,
        height,
        cropSize,
      ),
    })
  }

  const handlePointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (busy || event.button !== 0) {
      return
    }
    event.preventDefault()
    viewportRef.current?.setPointerCapture(event.pointerId)
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originOffsetX: transformRef.current.offsetX,
      originOffsetY: transformRef.current.offsetY,
    }
  }

  const handlePointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current
    if (!drag || drag.pointerId !== event.pointerId || pinchRef.current) {
      return
    }
    applyPan(event.clientX, event.clientY, drag)
  }

  const endDrag = (pointerId: number) => {
    if (dragRef.current?.pointerId === pointerId) {
      dragRef.current = null
    }
  }

  const handleWheel = (event: ReactWheelEvent<HTMLDivElement>) => {
    if (busy) {
      return
    }
    event.preventDefault()
    const delta = event.deltaY > 0 ? -0.08 : 0.08
    updateTransform(
      zoomCropTransform(
        transformRef.current,
        transformRef.current.zoom + delta,
        image.naturalWidth,
        image.naturalHeight,
        cropSize,
      ),
    )
  }

  const handleTouchStart = (event: ReactTouchEvent<HTMLDivElement>) => {
    if (busy || event.touches.length !== 2) {
      return
    }
    dragRef.current = null
    pinchRef.current = {
      startDistance: touchDistance(event.touches[0], event.touches[1]),
      startZoom: transformRef.current.zoom,
    }
  }

  const handleTouchMove = (event: ReactTouchEvent<HTMLDivElement>) => {
    const pinch = pinchRef.current
    if (!pinch || event.touches.length !== 2) {
      return
    }
    event.preventDefault()
    const distance = touchDistance(event.touches[0], event.touches[1])
    if (pinch.startDistance <= 0) {
      return
    }
    const nextZoom = pinch.startZoom * (distance / pinch.startDistance)
    updateTransform(
      zoomCropTransform(
        transformRef.current,
        nextZoom,
        image.naturalWidth,
        image.naturalHeight,
        cropSize,
      ),
    )
  }

  const handleTouchEnd = (event: ReactTouchEvent<HTMLDivElement>) => {
    if (event.touches.length < 2) {
      pinchRef.current = null
    }
  }

  const handleZoomSlider = (value: number) => {
    if (busy) {
      return
    }
    updateTransform(
      zoomCropTransform(
        transformRef.current,
        value,
        image.naturalWidth,
        image.naturalHeight,
        cropSize,
      ),
    )
  }

  const nudgeTransform = (dx: number, dy: number) => {
    const { width, height } = getDisplayedSize(
      image.naturalWidth,
      image.naturalHeight,
      cropSize,
      transformRef.current.zoom,
    )
    updateTransform({
      zoom: transformRef.current.zoom,
      ...clampCropOffset(
        transformRef.current.offsetX + dx,
        transformRef.current.offsetY + dy,
        width,
        height,
        cropSize,
      ),
    })
  }

  const handleViewportKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (busy) {
      return
    }
    if (event.key === '+' || event.key === '=') {
      event.preventDefault()
      handleZoomSlider(transformRef.current.zoom + KEYBOARD_ZOOM_STEP)
      return
    }
    if (event.key === '-' || event.key === '_') {
      event.preventDefault()
      handleZoomSlider(transformRef.current.zoom - KEYBOARD_ZOOM_STEP)
      return
    }
    if (event.key === 'ArrowLeft') {
      event.preventDefault()
      nudgeTransform(KEYBOARD_PAN_STEP, 0)
      return
    }
    if (event.key === 'ArrowRight') {
      event.preventDefault()
      nudgeTransform(-KEYBOARD_PAN_STEP, 0)
      return
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      nudgeTransform(0, KEYBOARD_PAN_STEP)
      return
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      nudgeTransform(0, -KEYBOARD_PAN_STEP)
    }
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (busy) {
      return
    }
    setIsExporting(true)
    try {
      if (onSaveRegion) {
        await onSaveRegion(
          cropRegionFromTransform(
            transformRef.current,
            image.naturalWidth,
            image.naturalHeight,
            cropSize,
          ),
        )
        return
      }
      const file = await exportCroppedImage({
        image,
        transform: transformRef.current,
        cropSize,
        shape,
        fileName,
      })
      assertMoodIconUploadSize(file)
      await onSave?.(file)
    } catch {
      // Parent surfaces upload errors; export failures leave the dialog open.
    } finally {
      setIsExporting(false)
    }
  }

  const frameClass =
    shape === 'circle' ? 'image-crop-frame image-crop-frame-circle' : 'image-crop-frame'

  return createPortal(
    <div className="image-crop-backdrop" role="presentation" onClick={() => !busy && onCancel()}>
      <form
        className={`image-crop-dialog card${children ? ' image-crop-dialog-with-fields' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(event) => event.stopPropagation()}
        onSubmit={(event) => void handleSubmit(event)}
      >
        <header className="image-crop-header">
          <h2 id={titleId} className="image-crop-title">
            {title ?? t('moodPreferences.cropTitle')}
          </h2>
          <p className="image-crop-hint">{hint ?? t('moodPreferences.cropHint')}</p>
        </header>

        <div className="image-crop-body">
          <div className="image-crop-editor">
            <div
              ref={viewportRef}
              className="image-crop-viewport"
              style={{ width: cropSize, height: cropSize }}
              tabIndex={0}
              role="application"
              aria-label={t('moodPreferences.cropAreaLabel')}
              onPointerDown={handlePointerDown}
              onPointerMove={handlePointerMove}
              onPointerUp={(event) => endDrag(event.pointerId)}
              onPointerCancel={(event) => endDrag(event.pointerId)}
              onWheel={handleWheel}
              onTouchStart={handleTouchStart}
              onTouchMove={handleTouchMove}
              onTouchEnd={handleTouchEnd}
              onTouchCancel={handleTouchEnd}
              onKeyDown={handleViewportKeyDown}
            >
              <img
                src={imageUrl}
                alt=""
                draggable={false}
                className="image-crop-image"
                style={{
                  width: displayed.width,
                  height: displayed.height,
                  transform: `translate(${transform.offsetX}px, ${transform.offsetY}px)`,
                }}
              />
              <div className={frameClass} aria-hidden />
            </div>

            <label className="image-crop-zoom">
              <span className="form-label">{t('moodPreferences.cropZoom')}</span>
              <input
                type="range"
                min={1}
                max={MOOD_ICON_MAX_ZOOM}
                step={0.01}
                value={transform.zoom}
                disabled={busy}
                aria-valuemin={1}
                aria-valuemax={MOOD_ICON_MAX_ZOOM}
                aria-valuenow={Number(transform.zoom.toFixed(2))}
                aria-label={t('moodPreferences.cropZoom')}
                onChange={(event) => handleZoomSlider(Number(event.target.value))}
              />
            </label>
          </div>

          <div className="image-crop-preview-panel">
            <p className="form-label">{t('moodPreferences.cropPreview')}</p>
            <canvas
              ref={previewRef}
              className={`image-crop-preview${shape === 'circle' ? ' image-crop-preview-circle' : ''}`}
              width={PREVIEW_SIZE}
              height={PREVIEW_SIZE}
              aria-hidden
            />
          </div>
        </div>

        {children ? <div className="image-crop-fields">{children}</div> : null}

        <div className="button-row image-crop-actions">
          {resetLabel && onReset ? (
            <button
              type="button"
              className="button button-secondary"
              onClick={onReset}
              disabled={busy}
            >
              {resetLabel}
            </button>
          ) : null}
          <button
            type="button"
            className="button button-secondary"
            onClick={onCancel}
            disabled={busy}
            aria-label={t('common.cancel')}
          >
            {t('common.cancel')}
          </button>
          <button
            type="submit"
            className="button"
            disabled={busy}
            aria-label={t('common.save')}
          >
            <StableButtonLabel
              active={busy ? t('common.saving') : t('common.save')}
              labels={[t('common.save'), t('common.saving')]}
            />
          </button>
        </div>
      </form>
    </div>,
    document.body,
  )
}
