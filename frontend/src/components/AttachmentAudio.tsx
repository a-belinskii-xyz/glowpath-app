import { useEffect, useId, useRef, useState, type CSSProperties } from 'react'

import { useLocale } from '../context/LocaleContext'
import {
  getAttachmentObjectUrl,
  getCachedAttachmentObjectUrl,
} from '../lib/attachmentBlobUrl'
import { hexToOklab, oklabToHex, washOklab } from '../lib/dayMoodWash'
import type { AttachmentPublic } from '../types/mood'

type AttachmentAudioProps = {
  entryId: string
  attachment: AttachmentPublic
  /** Mood (or goal) hex used to tint the soft player chrome. */
  accentColor?: string
  className?: string
}

type SoftAudioTheme = {
  '--audio-surface': string
  '--audio-surface-edge': string
  '--audio-accent': string
  '--audio-ink': string
  '--audio-muted': string
  '--audio-track': string
}

const FALLBACK_ACCENT = '#60a5fa'

function softAudioTheme(hex: string): SoftAudioTheme {
  const lab = hexToOklab(hex) ?? hexToOklab(FALLBACK_ACCENT)
  if (!lab) {
    return {
      '--audio-surface': '#eff6ff',
      '--audio-surface-edge': '#dbeafe',
      '--audio-accent': '#3b82f6',
      '--audio-ink': '#1e3a5f',
      '--audio-muted': '#64748b',
      '--audio-track': '#e2e8f0',
    }
  }

  const surface = oklabToHex(
    washOklab(lab, {
      washStrength: 0.9,
      chromaScale: 0.42,
      orderPower: 1,
      angleDeg: 0,
      midStopMinColors: 99,
    }),
  )
  const surfaceEdge = oklabToHex(
    washOklab(lab, {
      washStrength: 0.78,
      chromaScale: 0.55,
      orderPower: 1,
      angleDeg: 0,
      midStopMinColors: 99,
    }),
  )
  const accent = oklabToHex(
    washOklab(lab, {
      washStrength: 0.22,
      chromaScale: 0.92,
      orderPower: 1,
      angleDeg: 0,
      midStopMinColors: 99,
    }),
  )
  const ink = oklabToHex({
    L: Math.min(0.42, lab.L * 0.55),
    a: lab.a * 0.55,
    b: lab.b * 0.55,
  })
  const muted = oklabToHex({
    L: Math.min(0.58, lab.L * 0.7 + 0.12),
    a: lab.a * 0.28,
    b: lab.b * 0.28,
  })
  const track = oklabToHex(
    washOklab(lab, {
      washStrength: 0.86,
      chromaScale: 0.28,
      orderPower: 1,
      angleDeg: 0,
      midStopMinColors: 99,
    }),
  )

  return {
    '--audio-surface': surface,
    '--audio-surface-edge': surfaceEdge,
    '--audio-accent': accent,
    '--audio-ink': ink,
    '--audio-muted': muted,
    '--audio-track': track,
  }
}

function formatAudioTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return '0:00'
  }
  const total = Math.floor(seconds)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

function PlayIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M8.5 5.8v12.4c0 .7.75 1.12 1.34.74l9.2-6.2a.9.9 0 0 0 0-1.48l-9.2-6.2A.9.9 0 0 0 8.5 5.8z" />
    </svg>
  )
}

function PauseIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <rect x="6.5" y="5.5" width="3.75" height="13" rx="1.2" />
      <rect x="13.75" y="5.5" width="3.75" height="13" rx="1.2" />
    </svg>
  )
}

export function AttachmentAudio({
  entryId,
  attachment,
  accentColor = FALLBACK_ACCENT,
  className,
}: AttachmentAudioProps) {
  const { t } = useLocale()
  const progressId = useId()
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [src, setSrc] = useState<string | null>(
    () => getCachedAttachmentObjectUrl(entryId, attachment.id),
  )
  const [failed, setFailed] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)

  useEffect(() => {
    let cancelled = false
    const cached = getCachedAttachmentObjectUrl(entryId, attachment.id)
    if (cached) {
      setSrc(cached)
      setFailed(false)
      return
    }

    setSrc(null)
    setFailed(false)

    void getAttachmentObjectUrl(entryId, attachment.id)
      .then((objectUrl) => {
        if (!cancelled) {
          setSrc(objectUrl)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setFailed(true)
        }
      })

    return () => {
      cancelled = true
    }
  }, [entryId, attachment.id])

  useEffect(() => {
    setIsPlaying(false)
    setCurrentTime(0)
    setDuration(0)
  }, [src])

  if (failed) {
    return (
      <p className={`entry-audio-error muted ${className ?? ''}`.trim()}>
        {t('media.audioLoadFailed', { name: attachment.original_name })}
      </p>
    )
  }

  const theme = softAudioTheme(accentColor)
  const progress = duration > 0 ? Math.min(100, (currentTime / duration) * 100) : 0

  const togglePlayback = () => {
    const el = audioRef.current
    if (!el) {
      return
    }
    if (el.paused) {
      void el.play().catch(() => {
        setIsPlaying(false)
      })
    } else {
      el.pause()
    }
  }

  const seekTo = (ratio: number) => {
    const el = audioRef.current
    if (!el || !Number.isFinite(el.duration) || el.duration <= 0) {
      return
    }
    const next = Math.min(1, Math.max(0, ratio)) * el.duration
    el.currentTime = next
    setCurrentTime(next)
  }

  return (
    <div
      className={`entry-audio-player ${className ?? ''}`.trim()}
      style={theme as CSSProperties}
    >
      <p className="entry-audio-name">{attachment.original_name}</p>

      {src ? (
        <>
          <audio
            ref={audioRef}
            preload="metadata"
            src={src}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onEnded={() => {
              setIsPlaying(false)
              setCurrentTime(0)
            }}
            onLoadedMetadata={(event) => {
              const el = event.currentTarget
              setDuration(Number.isFinite(el.duration) ? el.duration : 0)
            }}
            onTimeUpdate={(event) => {
              setCurrentTime(event.currentTarget.currentTime)
            }}
          >
            {t('media.audioUnsupported')}
          </audio>

          <div className="entry-audio-controls">
            <button
              type="button"
              className="entry-audio-play"
              onClick={togglePlayback}
              aria-label={isPlaying ? t('media.pauseAudio') : t('media.playAudio')}
            >
              {isPlaying ? <PauseIcon /> : <PlayIcon />}
            </button>

            <div className="entry-audio-timeline">
              <label className="visually-hidden" htmlFor={progressId}>
                {t('media.seekAudio')}
              </label>
              <input
                id={progressId}
                className="entry-audio-progress"
                type="range"
                min={0}
                max={100}
                step={0.1}
                value={progress}
                style={{ '--audio-progress': `${progress}%` } as CSSProperties}
                onChange={(event) => {
                  seekTo(Number(event.currentTarget.value) / 100)
                }}
              />
              <p className="entry-audio-time" aria-live="off">
                <span>{formatAudioTime(currentTime)}</span>
                <span aria-hidden="true"> / </span>
                <span>{formatAudioTime(duration)}</span>
              </p>
            </div>
          </div>
        </>
      ) : (
        <div className="entry-audio-skeleton" aria-hidden />
      )}

      {attachment.transcription ? (
        <p className="entry-audio-transcription">{attachment.transcription}</p>
      ) : null}
    </div>
  )
}
