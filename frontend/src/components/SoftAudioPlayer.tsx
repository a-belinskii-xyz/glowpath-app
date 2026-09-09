import { useEffect, useId, useRef, useState, type CSSProperties, type ReactNode } from 'react'

import { useLocale } from '../context/LocaleContext'
import { buildMoodTheme, type ColorScheme } from '../design'
import { useColorScheme } from '../hooks/useColorScheme'
import { formatAudioClock } from '../lib/audioRecorder'

type SoftAudioPlayerProps = {
  src: string | null
  accentColor?: string
  title?: string
  className?: string
  children?: ReactNode
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

/** Maps Mood Theme Builder tokens onto the audio player CSS vars. */
function softAudioTheme(hex: string | undefined, scheme: ColorScheme): SoftAudioTheme {
  const theme = buildMoodTheme(hex || FALLBACK_ACCENT, { fallback: FALLBACK_ACCENT, scheme })
  return {
    '--audio-surface': theme.cssVars['--mood-surface'],
    '--audio-surface-edge': theme.cssVars['--mood-surface-edge'],
    '--audio-accent': theme.cssVars['--mood-accent'],
    '--audio-ink': theme.cssVars['--mood-ink'],
    '--audio-muted': theme.cssVars['--mood-muted'],
    '--audio-track': theme.cssVars['--mood-track'],
  }
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

export function SoftAudioPlayer({
  src,
  accentColor = FALLBACK_ACCENT,
  title,
  className,
  children,
}: SoftAudioPlayerProps) {
  const { t } = useLocale()
  const colorScheme = useColorScheme()
  const progressId = useId()
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)

  useEffect(() => {
    setIsPlaying(false)
    setCurrentTime(0)
    setDuration(0)
  }, [src])

  const theme = softAudioTheme(accentColor, colorScheme)
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
      title={title}
    >
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
            </div>

            <p className="entry-audio-time" aria-live="off">
              <span>{formatAudioClock(currentTime)}</span>
              <span aria-hidden="true">/</span>
              <span>{formatAudioClock(duration)}</span>
            </p>
          </div>
        </>
      ) : (
        <div className="entry-audio-skeleton" aria-hidden />
      )}

      {children}
    </div>
  )
}
