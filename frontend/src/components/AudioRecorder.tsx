import { useEffect, useRef, useState } from 'react'

import { useLocale } from '../context/LocaleContext'
import {
  formatAudioClock,
  isAudioRecordingSupported,
  MAX_AUDIO_BYTES,
  MAX_AUDIO_RECORDING_MS,
  pickAudioRecorderMimeType,
  recordingBlobToFile,
  stopMediaStream,
} from '../lib/audioRecorder'
import { MicIcon } from './icons'

type RecorderStatus = 'idle' | 'requesting' | 'recording'

type AudioRecorderProps = {
  disabled?: boolean
  onRecorded: (file: File) => void
  onError: (message: string) => void
  onBusyChange?: (busy: boolean) => void
}

function mediaErrorMessage(err: unknown, t: (key: string) => string): string {
  const name = err instanceof DOMException ? err.name : ''
  if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
    return t('errors.audioMicrophoneDenied')
  }
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
    return t('errors.audioMicrophoneNotFound')
  }
  if (name === 'SecurityError') {
    return t('errors.audioRecordingUnsupported')
  }
  return t('errors.audioRecordingFailed')
}

export function AudioRecorder({
  disabled = false,
  onRecorded,
  onError,
  onBusyChange,
}: AudioRecorderProps) {
  const { t } = useLocale()
  const [status, setStatus] = useState<RecorderStatus>('idle')
  const [elapsedMs, setElapsedMs] = useState(0)
  const supported = isAudioRecordingSupported()
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const startedAtRef = useRef(0)
  const discardOnStopRef = useRef(false)
  const unmountedRef = useRef(false)
  const onRecordedRef = useRef(onRecorded)
  const onErrorRef = useRef(onError)
  const onBusyChangeRef = useRef(onBusyChange)
  const busy = status === 'requesting' || status === 'recording'
  onRecordedRef.current = onRecorded
  onErrorRef.current = onError
  onBusyChangeRef.current = onBusyChange

  const setRecorderStatus = (next: RecorderStatus) => {
    setStatus(next)
    onBusyChangeRef.current?.(next === 'requesting' || next === 'recording')
  }

  const finishCleanup = () => {
    stopMediaStream(streamRef.current)
    streamRef.current = null
    recorderRef.current = null
    chunksRef.current = []
    if (!unmountedRef.current) {
      setRecorderStatus('idle')
      setElapsedMs(0)
    }
  }

  const stopRecording = (discard: boolean) => {
    discardOnStopRef.current = discard
    const recorder = recorderRef.current
    if (!recorder || recorder.state === 'inactive') {
      if (discard) {
        stopMediaStream(streamRef.current)
        streamRef.current = null
        if (!unmountedRef.current) {
          setRecorderStatus('idle')
          setElapsedMs(0)
        }
      }
      return
    }
    if (recorder.state === 'recording' || recorder.state === 'paused') {
      recorder.stop()
    }
  }

  useEffect(() => {
    unmountedRef.current = false
    return () => {
      unmountedRef.current = true
      discardOnStopRef.current = true
      onBusyChangeRef.current?.(false)
      const recorder = recorderRef.current
      if (recorder && recorder.state !== 'inactive') {
        recorder.stop()
      }
      stopMediaStream(streamRef.current)
      streamRef.current = null
      recorderRef.current = null
    }
  }, [])

  useEffect(() => {
    if (status !== 'recording') {
      return
    }
    const tick = () => {
      const elapsed = Date.now() - startedAtRef.current
      setElapsedMs(elapsed)
      if (elapsed >= MAX_AUDIO_RECORDING_MS) {
        const recorder = recorderRef.current
        if (recorder && (recorder.state === 'recording' || recorder.state === 'paused')) {
          discardOnStopRef.current = false
          recorder.stop()
        }
      }
    }
    tick()
    const timer = window.setInterval(tick, 200)
    return () => window.clearInterval(timer)
  }, [status])

  const startRecording = async () => {
    if (disabled || busy || !supported) {
      if (!supported) {
        onErrorRef.current(t('errors.audioRecordingUnsupported'))
      }
      return
    }
    setRecorderStatus('requesting')
    discardOnStopRef.current = false
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
        },
      })
      if (unmountedRef.current || discardOnStopRef.current) {
        stopMediaStream(stream)
        if (!unmountedRef.current) {
          setRecorderStatus('idle')
        }
        return
      }
      streamRef.current = stream
      const mimeType = pickAudioRecorderMimeType()
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream)
      recorderRef.current = recorder
      chunksRef.current = []
      startedAtRef.current = Date.now()

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data)
        }
        const total = chunksRef.current.reduce((sum, chunk) => sum + chunk.size, 0)
        if (total >= MAX_AUDIO_BYTES && recorder.state === 'recording') {
          discardOnStopRef.current = false
          recorder.stop()
        }
      }

      recorder.onerror = () => {
        if (unmountedRef.current) {
          return
        }
        finishCleanup()
        onErrorRef.current(t('errors.audioRecordingFailed'))
      }

      recorder.onstop = () => {
        const recordedType = recorder.mimeType || mimeType || 'audio/webm'
        const blob = new Blob(chunksRef.current, {
          type: recordedType.split(';')[0]?.trim() || 'audio/webm',
        })
        const discarded = discardOnStopRef.current
        finishCleanup()
        if (unmountedRef.current || discarded) {
          return
        }
        if (blob.size === 0) {
          onErrorRef.current(t('errors.audioRecordingEmpty'))
          return
        }
        if (blob.size > MAX_AUDIO_BYTES) {
          onErrorRef.current(t('errors.audioTooLarge'))
          return
        }
        onRecordedRef.current(recordingBlobToFile(blob, recordedType))
      }

      recorder.start(250)
      if (unmountedRef.current || discardOnStopRef.current) {
        if (recorder.state !== 'inactive') {
          recorder.stop()
        }
        return
      }
      setRecorderStatus('recording')
      setElapsedMs(0)
    } catch (err) {
      stopMediaStream(streamRef.current)
      streamRef.current = null
      if (unmountedRef.current || discardOnStopRef.current) {
        if (!unmountedRef.current) {
          setRecorderStatus('idle')
        }
        return
      }
      setRecorderStatus('idle')
      onErrorRef.current(mediaErrorMessage(err, t))
    }
  }

  if (!supported) {
    return null
  }

  if (status === 'recording' || status === 'requesting') {
    return (
      <div className="audio-recorder-live" aria-live="polite">
        <span className="audio-recorder-meter">
          <span className="audio-recorder-dot" aria-hidden="true" />
          <span className="audio-recorder-time">
            {status === 'requesting'
              ? t('entries.recordingStarting')
              : t('entries.recording', {
                  time: formatAudioClock(elapsedMs / 1000),
                })}
          </span>
        </span>
        <span className="audio-recorder-live-actions">
          <button
            type="button"
            className="button button-small"
            onClick={() => stopRecording(false)}
            disabled={status !== 'recording'}
          >
            {t('entries.stopRecording')}
          </button>
          <button
            type="button"
            className="button button-small button-secondary"
            onClick={() => stopRecording(true)}
          >
            {t('common.cancel')}
          </button>
        </span>
      </div>
    )
  }

  return (
    <button
      type="button"
      className="button button-small attachment-audio-action"
      onClick={() => void startRecording()}
      disabled={disabled}
    >
      <MicIcon />
      {t('entries.recordAudio')}
    </button>
  )
}
